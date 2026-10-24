"""Read-only final-decision projection and D11 withdrawal guard."""
import json
from sqlalchemy import select
from chair_models import ChairDecision
from adjustment_models import AdjustmentEvent
from services.adjustment_schedule_service import digest
from services.schedule_service import problem


def decision_for(db, record):
    value = db.scalar(select(ChairDecision).where(ChairDecision.request_id == record.id))
    if value is None: return None
    try:
        payload = json.loads(value.payload_json)
        head = db.scalar(select(AdjustmentEvent.event_digest).where(AdjustmentEvent.request_id == record.id).order_by(AdjustmentEvent.sequence.desc()).limit(1))
        if (digest(payload) != value.payload_digest or payload['request_id'] != str(record.id)
                or payload['request_version'] != record.version or value.request_version != record.version
                or payload['content_digest'] != record.content_digest or record.status != 'SUBMITTED'
                or payload['actor_id'] != str(value.actor_id) or payload['action'] != value.action
                or payload['department_id'] != str(value.department_id)
                or payload['operation_id'] != str(value.operation_id)
                or payload['command_digest'] != value.command_digest
                or payload['provenance']['D11_history_head'] != head
                or value.action not in {'APPROVE','REJECT'}): raise ValueError()
        status = 'APPROVED_PENDING_APPLICATION' if value.action == 'APPROVE' else 'REJECTED'
        return {'id': str(value.id), 'status': status, 'action': value.action, 'actor_id': str(value.actor_id),
                'department_id': str(value.department_id), 'explanation': payload['explanation'],
                'decided_at': payload['created_at'], 'request_version': value.request_version,
                'schedule_revision': payload['schedule_revision'], 'constraint_digest': payload['constraint_digest'],
                'validation': payload['validation'], 'provenance': payload['provenance'],
                'payload_digest': value.payload_digest, 'schedule_changed': False}
    except (ValueError, KeyError, TypeError):
        raise problem(503, 'CHAIR_DECISION_INTEGRITY', 'The retained decision could not be verified.') from None


def ensure_undecided(db, record):
    if decision_for(db, record) is not None:
        raise problem(409, 'REQUEST_ALREADY_DECIDED', 'This request has a final Chair decision. No withdrawal or replacement decision is permitted.')
