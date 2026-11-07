"""Scoped optimization authority, independent of account role/Chair reviews.

No deployment provider or environment activation switch is installed. Synthetic
providers belong exclusively to isolated tests. A grant is not publication.
"""
from dataclasses import dataclass, asdict
import hashlib
import json
import time
from uuid import UUID


class RunError(ValueError):
    def __init__(self, code, status=409):
        self.code=code;self.status=status
        super().__init__(code)  # No provider messages, records, URLs or credentials.


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def uuid(value):
    try:
        if type(value) is not str or str(UUID(value))!=value:raise ValueError()
    except (ValueError,TypeError,AttributeError):raise RunError('GA_RUN_IDENTITY_INVALID',422) from None
    return value


@dataclass(frozen=True)
class Context:
    actor_id:str
    department_id:str
    action:str
    run_id:str|None=None
    bundle_fingerprint:str|None=None
    configuration_fingerprint:str|None=None
    catalog_reference:str|None=None


@dataclass(frozen=True)
class Grant:
    context_digest:str
    actor_id:str
    department_id:str
    action:str
    capability:str
    policy_digest:str
    issued_at:float
    expires_at:float


def verify(provider,context,clock=time.time):
    uuid(context.actor_id);uuid(context.department_id)
    if provider is None:raise RunError('GA_OPTIMIZATION_AUTHORITY_UNAVAILABLE',503)
    try:
        value=provider.authorize(context)
        now=clock()
        valid=(type(value) is Grant and value.context_digest==digest(asdict(context))
            and (value.actor_id,value.department_id,value.action)==(context.actor_id,context.department_id,context.action)
            and value.capability=='department_optimization_control' and value.issued_at<=now<value.expires_at
            and 0<value.expires_at-value.issued_at<=300 and len(value.policy_digest)==64
            and all(c in '0123456789abcdef' for c in value.policy_digest))
        if not valid:raise ValueError()
        return value
    except Exception:raise RunError('GA_OPTIMIZATION_AUTHORITY_REQUIRED',403) from None
