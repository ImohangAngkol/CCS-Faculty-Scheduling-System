"""Application mandates are independent of administrator and Chair privileges."""
from contextlib import contextmanager, ExitStack
from datetime import datetime, timezone
from uuid import UUID
from services.chair_authority_service import Mandate, ScopeBinding, scope
from services.schedule_service import problem


def institutional_application_directory(): return None


def mandate(directory,actor):
    try:
        value=directory.application_mandate_for(str(actor.id));stamp=datetime.now(timezone.utc)
        if not (isinstance(value,Mandate) and value.actor_id==actor.id and value.role=='schedule_application'
            and value.state=='ACTIVE' and value.issued_at.tzinfo and value.expires_at.tzinfo
            and value.issued_at<=stamp<value.expires_at and 0<(value.expires_at-value.issued_at).total_seconds()<=300
            and value.reference and len(value.policy_digest)==64 and value.departments
            and len(set(d[0] for d in value.departments))==len(value.departments)
            and all(str(UUID(id))==id and label for id,label in value.departments)):raise ValueError()
        return value
    except Exception:raise problem(403,'APPLICATION_AUTHORITY_REQUIRED','A current independent schedule application mandate is required.') from None


@contextmanager
def authorized(actor):
    with ExitStack() as stack:
        try:
            provider=institutional_application_directory()
            if provider is None:raise ValueError()
            directory=stack.enter_context(provider)
        except Exception:raise problem(503,'APPLICATION_AUTHORITY_UNAVAILABLE','Production schedule application is blocked: verified application authority is unavailable.') from None
        grant=mandate(directory,actor)
        yield directory,grant


def recheck(directory,grant,actor,record=None,binding=None):
    fresh=mandate(directory,actor)
    if any(getattr(fresh,k)!=getattr(grant,k) for k in ('actor_id','role','state','departments','reference','policy_digest')):
        raise problem(409,'APPLICATION_AUTHORITY_CHANGED','Application authority changed. Reload before applying.')
    if record is not None and scope(directory,fresh,record)!=binding:
        raise problem(409,'APPLICATION_SCOPE_CHANGED','The department binding changed. Reload before applying.')
