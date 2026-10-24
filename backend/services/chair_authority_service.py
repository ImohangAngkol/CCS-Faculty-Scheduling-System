"""Independent, current institutional Chair mandate and department binding.

Existing admin/faculty roles do not grant this capability. No client or env
switch can install a directory. Fictional directories exist only in tests.
"""
from contextlib import contextmanager, ExitStack
from datetime import datetime, timezone
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from services.schedule_service import problem


class Mandate(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)
    actor_id: UUID
    role: str
    state: str
    departments: tuple[tuple[str, str], ...]  # authoritative scope ID / permitted label
    reference: str
    policy_digest: str
    issued_at: datetime
    expires_at: datetime


class ScopeBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)
    department_id: str
    faculty_id: str
    subject_id: str
    section_id: str
    academic_year: str
    term: str
    reference: str


def institutional_chair_directory():
    """Return a coherent, guarded directory context, or None. Deployment blocked."""
    return None


def mandate(directory, actor):
    try:
        value = directory.mandate_for(str(actor.id))
        now = datetime.now(timezone.utc)
        valid = (isinstance(value, Mandate) and value.actor_id == actor.id
            and value.role == 'department_chair' and value.state == 'ACTIVE'
            and value.issued_at.tzinfo is not None and value.expires_at.tzinfo is not None
            and value.issued_at <= now < value.expires_at
            and 0 < (value.expires_at-value.issued_at).total_seconds() <= 300
            and value.reference and len(value.policy_digest) == 64 and value.departments
            and len({d[0] for d in value.departments}) == len(value.departments)
            and all(str(UUID(id)) == id and label for id, label in value.departments))
        if not valid: raise ValueError()
        return value
    except Exception:
        raise problem(403, 'CHAIR_AUTHORITY_REQUIRED', 'A current, independently verified Department Chair mandate is required.') from None


@contextmanager
def authorized(actor):
    # Sanitize provider acquisition failures without disguising transaction
    # exceptions raised by the operation inside this context.
    with ExitStack() as stack:
        try:
            provider = institutional_chair_directory()
            if provider is None: raise ValueError()
            directory = stack.enter_context(provider)
        except Exception:
            raise problem(503, 'CHAIR_AUTHORITY_UNAVAILABLE', 'Production Chair review and decisions are blocked: a verified institutional Chair directory is unavailable.') from None
        grant = mandate(directory, actor)
        yield directory, grant


def scope(directory, grant, record):
    import json
    try:
        content = json.loads(record.content_json)
        original = content['review']['original']; labels = content['input']
        binding = directory.department_for(str(record.faculty_id), original['subject_id'], original['section_id'], labels['academic_year'], labels['term'])
        expected = (str(record.faculty_id), original['subject_id'], original['section_id'], labels['academic_year'], labels['term'])
        if (not isinstance(binding, ScopeBinding) or not binding.reference
                or (binding.faculty_id, binding.subject_id, binding.section_id, binding.academic_year, binding.term) != expected
                or binding.department_id not in {id for id, _ in grant.departments}): raise ValueError()
        return binding
    except Exception:
        raise problem(404, 'CHAIR_REQUEST_NOT_FOUND', 'No request is available within your verified department scope.') from None


def recheck(directory, grant, actor, record=None, binding=None):
    fresh = mandate(directory, actor)
    fields = ('actor_id', 'role', 'state', 'departments', 'reference', 'policy_digest')
    if any(getattr(fresh, k) != getattr(grant, k) for k in fields):
        raise problem(409, 'CHAIR_AUTHORITY_CHANGED', 'Chair authority changed during review. Reload before deciding.')
    if record is not None and scope(directory, fresh, record) != binding:
        raise problem(409, 'DEPARTMENT_SCOPE_CHANGED', 'The verified department assignment changed. Reload before deciding.')
