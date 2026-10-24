"""Owned, durable request proposals. Never approves or writes a schedule."""
import json
from uuid import UUID, uuid4
from dataclasses import asdict
from fastapi import HTTPException
from sqlalchemy import select, update
from adjustment_models import AdjustmentRequest as Record, AdjustmentEvent as Event
from identity_models import User, now
from schemas.adjustments import Preview
from services import adjustment_schedule_service as source
from services.schedule_service import problem


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def verified_actor(db, user, identity):
    # Recheck the real account inside the writing transaction; this row lock
    # serializes approved account changes on PostgreSQL. SQLite fixture writes
    # retain optimistic version/unique constraints and bounded lock failures.
    current = db.scalar(select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True))
    if current is None or not current.is_active or current.role != 'faculty' or str(current.faculty_id) != identity.faculty_id:
        raise problem(403, 'REQUEST_BINDING_CHANGED', 'The account binding changed. Sign in again before continuing.')


def owner(db, request_id, user, identity, lock=False):
    query = select(Record).where(Record.id == request_id, Record.owner_id == user.id,
                                          Record.faculty_id == UUID(identity.faculty_id))
    if lock: query = query.with_for_update().execution_options(populate_existing=True)
    record = db.scalar(query)
    if record is None:
        raise problem(404, 'REQUEST_NOT_FOUND', 'No request is available to your account.')
    verify(db, record)
    return record


def verify(db, record):
    if source.digest(json.loads(record.content_json)) != record.content_digest:
        raise problem(503, 'REQUEST_INTEGRITY_FAILED', 'Request integrity could not be verified.')
    events = db.scalars(select(Event).where(Event.request_id == record.id).order_by(Event.sequence)).all()
    previous = None
    for index, event in enumerate(events, 1):
        payload = json.loads(event.payload_json)
        if (event.sequence != index or event.previous_digest != previous or event.actor_id != record.owner_id
                or source.digest(payload) != event.event_digest or payload['request_id'] != str(record.id)
                or payload['sequence'] != index or payload['action'] != event.action
                or payload['actor_id'] != str(event.actor_id) or payload['previous_digest'] != previous
                or payload['operation_id'] != str(event.operation_id) or payload['content_digest'] != record.content_digest):
            raise problem(503, 'REQUEST_INTEGRITY_FAILED', 'Request history integrity could not be verified.')
        previous = event.event_digest
    actions = [e.action for e in events]
    legal = {'DRAFT': [['CREATED']], 'SUBMITTED': [['CREATED', 'SUBMITTED']],
             'WITHDRAWN': [['CREATED', 'WITHDRAWN'], ['CREATED', 'SUBMITTED', 'WITHDRAWN']]}
    if record.version != len(events) or actions not in legal.get(record.status, []):
        raise problem(503, 'REQUEST_INTEGRITY_FAILED', 'Request lifecycle integrity could not be verified.')
    return events


def event(db, record, actor, operation_id, command_digest, action, findings):
    previous = db.scalar(select(Event.event_digest).where(Event.request_id == record.id).order_by(Event.sequence.desc()).limit(1))
    timestamp = now()
    payload = {'request_id': str(record.id), 'sequence': record.version, 'action': action,
               'actor_id': str(actor.id), 'operation_id': str(operation_id), 'previous_digest': previous,
               'content_digest': record.content_digest, 'created_at': timestamp.isoformat(), 'validation': findings}
    db.add(Event(id=uuid4(), request_id=record.id, actor_id=actor.id, operation_id=operation_id,
                 command_digest=command_digest, sequence=record.version, action=action,
                 previous_digest=previous, payload_json=canonical(payload), event_digest=source.digest(payload), created_at=timestamp))


def freshness(record, identity):
    content = json.loads(record.content_json)
    try:
        with source.current_source() as current:
            result = source.validate(current, identity, Preview.model_validate(content['input']))
            current.check_current()
            if result['constraint_digest'] != content['review']['constraint_digest']:
                return {'state': 'STALE', 'code': 'GEC_CONSTRAINT_SET_CHANGED', 'validation': result['validation']}
            return {'state': 'CURRENT', 'code': None, 'validation': result['validation']}
    except HTTPException as error:
        return {'state': 'UNAVAILABLE' if error.status_code == 503 else 'STALE',
                'code': error.detail['code'] if isinstance(error.detail, dict) else 'SOURCE_UNAVAILABLE', 'validation': None}


def detail(db, record, identity):
    events = verify(db, record)
    from services.chair_decision_projection import decision_for
    decision = decision_for(db, record)
    result = {'id': str(record.id), 'status': decision['status'] if decision else record.status, 'version': record.version,
            'created_at': record.created_at.isoformat(), 'updated_at': record.updated_at.isoformat(),
            'submitted_at': record.submitted_at.isoformat() if record.submitted_at else None,
            'withdrawn_at': record.withdrawn_at.isoformat() if record.withdrawn_at else None,
            'content_digest': record.content_digest, 'content': json.loads(record.content_json),
            'freshness': freshness(record, identity), 'history': [json.loads(e.payload_json) for e in events],
            'schedule_changed': False, 'approval': decision['status'] if decision else 'NOT_IMPLEMENTED_D11'}
    if decision: result.update(decision=decision, base_status=record.status)
    if decision:
        from services.schedule_version_store import application_for
        application = application_for(db, record)
        if application: result.update(application=application, status='APPLIED', schedule_changed=True)
    return result


def assignments(identity):
    with source.current_source() as current:
        current.check_current()
        return {'schedule_id': current.schedule_id, 'revision': current.revision, 'academic_year': current.academic_year,
                'term': current.term, 'constraint_digest': current.constraint_digest,
                'assignments': [source.public_meeting(m) for m in source.owned(current, identity)],
                'rooms': [asdict(r) for r in current.rooms], 'label': 'GA-generated proposal; adjustments require future Chair approval'}


def preview(identity, body):
    with source.current_source() as current:
        result = source.validate(current, identity, body)
        current.check_current()
        return result


def create(db, user, identity, body):
    command = body.model_dump(mode='json'); command_hash = source.digest(command)
    # A recorded operation can be retried without changing historical content,
    # including after the source later becomes stale/unavailable.
    with db.begin():
        verified_actor(db, user, identity)
        prior = db.scalar(select(Event).where(Event.actor_id == user.id, Event.operation_id == body.operation_id))
        if prior:
            if prior.command_digest != command_hash or prior.action != 'CREATED':
                raise problem(409, 'IDEMPOTENCY_MISMATCH', 'This operation identifier was already used for different content.')
            record = owner(db, prior.request_id, user, identity)
        else:
            record = None
    if record is not None:
        return detail(db, record, identity)
    with source.current_source() as current:
        reviewed = source.validate(current, identity, body)
        content = {'input': body.model_dump(mode='json', exclude={'operation_id'}), 'review': reviewed}
        key = source.digest({'faculty': identity.faculty_id, 'schedule': body.revision,
                             'assignment': body.assignment_id, 'proposal': body.proposal.model_dump()})
        with db.begin():
            verified_actor(db, user, identity)
            if db.scalar(select(Record.id).where(Record.active_key == key)):
                raise problem(409, 'DUPLICATE_ACTIVE_REQUEST', 'An identical active proposal already exists. Open that request instead.')
            record = Record(id=uuid4(), owner_id=user.id, faculty_id=UUID(identity.faculty_id),
                create_operation=body.operation_id, command_digest=command_hash, content_json=canonical(content),
                content_digest=source.digest(content), active_key=key, status='DRAFT', version=1)
            db.add(record); db.flush()
            event(db, record, user, body.operation_id, command_hash, 'CREATED', reviewed['validation'])
            db.flush(); current.check_current()
    return detail(db, record, identity)


def transition(db, user, identity, request_id, action, body):
    command_hash = source.digest({'request_id': str(request_id), 'action': action, **body.model_dump(mode='json')})
    replay = None
    with db.begin():
        verified_actor(db, user, identity)
        record = owner(db, request_id, user, identity)
        prior = db.scalar(select(Event).where(Event.actor_id == user.id, Event.operation_id == body.operation_id))
        if prior:
            if prior.request_id != record.id or prior.command_digest != command_hash:
                raise problem(409, 'IDEMPOTENCY_MISMATCH', 'This operation identifier was already used for another command.')
            replay = record
    if replay is not None:
        # Release the account row lock before acquiring a source/authority guard.
        return detail(db, replay, identity)
    # Withdrawals must remain possible while the original source is unavailable.
    from contextlib import nullcontext
    with (source.current_source() if action == 'submit' else nullcontext(None)) as current:
        with db.begin():
            verified_actor(db, user, identity)
            record = owner(db, request_id, user, identity, lock=True)
            prior = db.scalar(select(Event).where(Event.actor_id == user.id, Event.operation_id == body.operation_id))
            if prior:
                if prior.request_id != record.id or prior.command_digest != command_hash:
                    raise problem(409, 'IDEMPOTENCY_MISMATCH', 'This operation identifier was already used for another command.')
            else:
                from services.chair_decision_projection import ensure_undecided
                ensure_undecided(db, record)
                if record.version != body.expected_version:
                    raise problem(409, 'REQUEST_VERSION_CHANGED', 'The request changed in another session. Reload before retrying.')
                if (action == 'submit' and record.status != 'DRAFT') or (action == 'withdraw' and record.status not in {'DRAFT', 'SUBMITTED'}):
                    raise problem(409, 'INVALID_REQUEST_TRANSITION', 'This action is not eligible for the current request status.')
                content = json.loads(record.content_json)
                findings = None
                if action == 'submit':
                    reviewed = source.validate(current, identity, Preview.model_validate(content['input']))
                    if reviewed['constraint_digest'] != content['review']['constraint_digest']:
                        raise problem(409, 'GEC_CONSTRAINT_SET_CHANGED', 'The fixed commitment revision changed. Create a new proposal after review.')
                    findings = reviewed['validation']
                stamp = now(); status = 'SUBMITTED' if action == 'submit' else 'WITHDRAWN'
                values = {'version': record.version + 1, 'status': status, 'updated_at': stamp,
                          'submitted_at' if action == 'submit' else 'withdrawn_at': stamp}
                if action == 'withdraw': values['active_key'] = None
                changed = db.execute(update(Record).where(Record.id == record.id, Record.version == body.expected_version,
                    Record.status == record.status).values(**values).execution_options(synchronize_session=False))
                if changed.rowcount != 1:
                    raise problem(409, 'REQUEST_VERSION_CHANGED', 'Another update won the transaction. Reload before retrying.')
                db.expire(record); db.refresh(record)
                event(db, record, user, body.operation_id, command_hash, 'SUBMITTED' if action == 'submit' else 'WITHDRAWN', findings)
                db.flush()
                if current: current.check_current()
    return detail(db, record, identity)


def listing(db, user, identity, before=None):
    query = select(Record).where(Record.owner_id == user.id, Record.faculty_id == UUID(identity.faculty_id))
    if before: query = query.where(Record.id < before)
    rows = db.scalars(query.order_by(Record.id.desc()).limit(26)).all()
    return {'items': [detail(db, r, identity) for r in rows[:25]], 'next_cursor': str(rows[24].id) if len(rows) > 25 else None}
