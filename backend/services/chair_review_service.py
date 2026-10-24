"""Scoped Chair review and immutable decisions; never schedule application."""
from contextlib import contextmanager
import json
from types import SimpleNamespace
from uuid import UUID, uuid4
from fastapi import HTTPException
from sqlalchemy import select, text
from identity_models import User, now
from adjustment_models import AdjustmentRequest, AdjustmentEvent
from chair_models import ChairDecision
from schemas.adjustments import Preview
from services import adjustment_service as requests, adjustment_schedule_service as schedules
from services import chair_authority_service as authority, chair_decision_projection as projection
from services.schedule_service import problem
from services import ga_v2_service, ga_v2_constraints


def transaction(db):
    # SQLite needs one writer-owned transaction, including the ledger read.
    # Opening D10's separate BEGIN IMMEDIATE session would deadlock SQLite.
    if db.get_bind().dialect.name == 'sqlite': db.connection().exec_driver_sql('BEGIN IMMEDIATE')
    elif db.get_bind().dialect.name == 'postgresql':
        db.execute(text("SET LOCAL lock_timeout = '2s'")); db.execute(text("SET LOCAL statement_timeout = '10s'"))
    else: raise problem(503, 'CHAIR_STORAGE_UNSUPPORTED', 'No transactional decision implementation supports this database.')


def trusted_snapshot(db, source):
    """Reuse actual D10/D8/D9 checks in this transaction, not cached findings."""
    try:
        deployment = ga_v2_service.deployment_for(source.academic_year, source.term)
        with deployment.authority.session_factory() as expected_db:
            if expected_db.get_bind().url != db.get_bind().url: raise ValueError('Different ledger target')
        if db.get_bind().dialect.name == 'postgresql':
            db.execute(text('LOCK TABLE public.gec_records, public.gec_revisions, public.gec_events IN SHARE MODE'))
        snapshot = ga_v2_constraints._read_snapshot(db, deployment.catalog, deployment.templates)
        if snapshot.digest != source.constraint_digest:
            raise problem(409, 'GEC_CONSTRAINT_SET_CHANGED', 'The current confirmed constraint set differs from the schedule review source.')
        return snapshot
    except HTTPException: raise
    except (ga_v2_constraints.ConstraintError, ValueError):
        raise problem(503, 'CHAIR_TRUST_UNAVAILABLE', 'Current D8 evidence, D9 confirmations, D10 applicability or the trusted term catalog could not be verified. Approval is blocked.') from None


def record_for(db, id, directory, grant, lock=False):
    query = select(AdjustmentRequest).where(AdjustmentRequest.id == id)
    record = db.scalar(query)
    if record is None: raise problem(404, 'CHAIR_REQUEST_NOT_FOUND', 'No request is available within your verified department scope.')
    binding = authority.scope(directory, grant, record)
    if lock:
        # Same owner-before-request lock order as D11 withdrawal.
        db.scalar(select(User).where(User.id == record.owner_id).with_for_update())
        record = db.scalar(query.with_for_update().execution_options(populate_existing=True))
        binding = authority.scope(directory, grant, record)
    requests.verify(db, record)
    return record, binding


def validation(db, record, source):
    owner = db.scalar(select(User).where(User.id == record.owner_id).with_for_update().execution_options(populate_existing=True))
    if owner is None or not owner.is_active or owner.role != 'faculty' or owner.faculty_id != record.faculty_id:
        raise problem(409, 'CHAIR_OWNER_BINDING_CHANGED', 'The faculty account binding is no longer valid for this request. Approval is blocked.')
    content = json.loads(record.content_json)
    result = schedules.validate(source, SimpleNamespace(faculty_id=str(record.faculty_id)), Preview.model_validate(content['input']))
    if result['constraint_digest'] != content['review']['constraint_digest']:
        raise problem(409, 'GEC_CONSTRAINT_SET_CHANGED', 'The GEC revision changed after faculty submission; a new proposal is required.')
    snapshot = trusted_snapshot(db, source)
    if not result['validation']['conflict_free']:
        raise problem(409, 'CHAIR_SCHEDULING_CONFLICT', 'The proposal has current scheduling or resource findings and cannot be approved.')
    return result, snapshot


def pending(db, actor, department_id=None, include_decided=False):
    with authority.authorized(actor) as (directory, grant):
        if department_id and department_id not in {id for id, _ in grant.departments}:
            raise problem(403, 'CHAIR_DEPARTMENT_DENIED', 'This filter is outside your verified department mandate.')
        rows = db.scalars(select(AdjustmentRequest).where(AdjustmentRequest.status == 'SUBMITTED').order_by(AdjustmentRequest.id).limit(1001)).all()
        if len(rows) > 1000: raise problem(503, 'CHAIR_QUEUE_LIMIT', 'The review queue exceeds the supported bound; no partial queue is presented.')
        items = []
        for record in rows:
            try: binding = authority.scope(directory, grant, record)
            except HTTPException as e:
                if e.status_code == 404: continue
                raise
            if department_id and binding.department_id != department_id: continue
            requests.verify(db, record); final = projection.decision_for(db, record)
            if final and not include_decided: continue
            content = json.loads(record.content_json)
            items.append({'id':str(record.id), 'version':record.version, 'faculty_id':str(record.faculty_id),
                'department_id':binding.department_id, 'subject':content['review']['original']['subject'],
                'section':content['review']['original']['section'], 'submitted_at':record.submitted_at.isoformat(),
                'status':final['status'] if final else 'SUBMITTED'})
        authority.recheck(directory, grant, actor)
        return {'items':items}


def review(db, actor, id):
    with authority.authorized(actor) as (directory, grant), db.begin():
        transaction(db)
        record, binding = record_for(db, id, directory, grant)
        detail = requests.detail(db, record, SimpleNamespace(faculty_id=str(record.faculty_id)))
        final = projection.decision_for(db, record)
        fresh = None; block = None
        try:
            with schedules.current_source() as source:
                fresh = schedules.validate(source, SimpleNamespace(faculty_id=str(record.faculty_id)), Preview.model_validate(detail['content']['input']))
                trusted_snapshot(db, source)
                if fresh['constraint_digest'] != detail['content']['review']['constraint_digest']:
                    raise problem(409, 'GEC_CONSTRAINT_SET_CHANGED', 'The pinned GEC revision changed after submission.')
                source.check_current()
        except HTTPException as error:
            block = error.detail if isinstance(error.detail, dict) else {'code':'CHAIR_VALIDATION_UNAVAILABLE','message':'Current validation is unavailable.'}
        eligible = (record.status == 'SUBMITTED' and not final and record.owner_id != actor.id
                    and (actor.faculty_id is None or actor.faculty_id != record.faculty_id))
        authority.recheck(directory, grant, actor, record, binding)
        return {'request':detail, 'faculty_id':str(record.faculty_id), 'department_id':binding.department_id,
                'current_review':fresh, 'approval_block':block, 'can_approve':bool(eligible and not block and fresh and fresh['validation']['conflict_free']),
                'can_reject':bool(eligible), 'decision_history':[final] if final else [], 'schedule_changed':False}


def decide(db, actor, id, action, body):
    command = {'request_id':str(id), 'action':action, **body.model_dump(mode='json')}
    command_digest = schedules.digest(command)
    from contextlib import nullcontext
    with authority.authorized(actor) as (directory, grant), (schedules.current_source() if action == 'APPROVE' else nullcontext(None)) as source, db.begin():
        transaction(db)
        current_actor = db.scalar(select(User).where(User.id == actor.id).with_for_update().execution_options(populate_existing=True))
        if current_actor is None or not current_actor.is_active: raise problem(403, 'CHAIR_ACCOUNT_UNAVAILABLE', 'The authenticated account is no longer active.')
        record, binding = record_for(db, id, directory, grant, lock=True)
        prior = db.scalar(select(ChairDecision).where(ChairDecision.actor_id == actor.id, ChairDecision.operation_id == body.operation_id))
        if prior:
            if prior.request_id != id or prior.command_digest != command_digest:
                raise problem(409, 'CHAIR_IDEMPOTENCY_MISMATCH', 'This operation identifier was already used for different decision content.')
            authority.recheck(directory, grant, actor, record, binding)
            return projection.decision_for(db, record)
        projection.ensure_undecided(db, record)
        if current_actor.id == record.owner_id or (current_actor.faculty_id is not None and current_actor.faculty_id == record.faculty_id):
            raise problem(403, 'CHAIR_SELF_DECISION_DENIED', 'An independent authorized Chair must decide this request.')
        if record.status != 'SUBMITTED': raise problem(409, 'CHAIR_REQUEST_NOT_SUBMITTED', 'Only an eligible submitted request can receive a final decision.')
        content = json.loads(record.content_json)
        if (record.version != body.expected_version or record.content_digest != body.content_digest
                or content['input']['revision'] != body.schedule_revision
                or content['review']['constraint_digest'] != body.constraint_digest):
            raise problem(409, 'CHAIR_REVIEW_CHANGED', 'The reviewed request/version references differ. Reload before deciding.')
        fresh = None; snapshot = None
        if action == 'APPROVE': fresh, snapshot = validation(db, record, source)
        timestamp = now()
        head = db.scalar(select(AdjustmentEvent.event_digest).where(AdjustmentEvent.request_id == id).order_by(AdjustmentEvent.sequence.desc()).limit(1))
        payload = {'request_id':str(id), 'request_version':record.version, 'content_digest':record.content_digest,
            'actor_id':str(actor.id), 'department_id':binding.department_id, 'action':action, 'explanation':body.explanation,
            'operation_id':str(body.operation_id), 'command_digest':command_digest, 'created_at':timestamp.isoformat(),
            'schedule_revision':body.schedule_revision, 'constraint_digest':body.constraint_digest,
            'validation':fresh['validation'] if fresh else None,
            'provenance':{'mandate_reference':grant.reference, 'policy_digest':grant.policy_digest,
                'scope_reference':binding.reference, 'D11_history_head':head,
                'constraint_heads':[h.model_dump(mode='json') for h in snapshot.heads] if snapshot else [],
                'trust_status':'FRESH_D8_D9_D10' if snapshot else 'NOT_REQUIRED_FOR_REJECTION', 'schedule_changed':False}}
        db.add(ChairDecision(id=uuid4(), request_id=id, request_version=record.version, actor_id=actor.id,
            department_id=UUID(binding.department_id), operation_id=body.operation_id, action=action,
            command_digest=command_digest, payload_json=requests.canonical(payload), payload_digest=schedules.digest(payload), created_at=timestamp))
        db.flush()
        if source:
            source.check_current()
            if trusted_snapshot(db, source).digest != snapshot.digest: raise problem(409, 'CHAIR_TRUST_CHANGED', 'Institutional trust changed before decision commit.')
        authority.recheck(directory, grant, actor, record, binding)
        result = projection.decision_for(db, record)
    return result
