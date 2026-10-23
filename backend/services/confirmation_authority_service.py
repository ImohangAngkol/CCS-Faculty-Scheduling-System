"""Independent institutional confirmation authorization, unavailable by default.

Neither admin role nor verified evidence grants this capability. A future
institutional adapter must authenticate its own policy/actor/scope independently.
"""
from dataclasses import dataclass
from datetime import datetime,timezone
import hashlib
import json
from pydantic import BaseModel,ConfigDict,Field
from services.external_schedule_verification_service import instant


@dataclass(frozen=True)
class ConfirmationContext:
    actor_id: str
    action: str
    operation_id: str
    record_id: str
    revision_id: str
    expected_version: int
    academic_year: str
    term: str
    supplier: str
    content_digest: str
    evidence_digest: str


class Authorization(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,frozen=True)
    context_digest: str=Field(pattern=r'^[a-f0-9]{64}$')
    policy_reference: str=Field(pattern=r'^[a-z][a-z0-9_.-]{0,119}$')
    policy_digest: str=Field(pattern=r'^[a-f0-9]{64}$')
    actor_id: str
    action: str
    state: str
    issued_at: str
    expires_at: str


def digest(context):
    return hashlib.sha256(json.dumps(vars(context),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def authorization_for(context: ConfirmationContext) -> Authorization | None:
    return None


def require_authority(context):
    try:
        grant=authorization_for(context)
        if not isinstance(grant,Authorization):return None
        grant=Authorization.model_validate(grant.__dict__)
        issued,expires=instant(grant.issued_at),instant(grant.expires_at)
        now=datetime.now(timezone.utc)
        if (grant.state!='AUTHORIZED' or grant.actor_id!=context.actor_id or grant.action!=context.action
            or grant.context_digest!=digest(context) or not issued<=now<expires or (expires-issued).total_seconds()>300):return None
        return grant
    except Exception:
        return None  # Never log a provider exception or raw response.
