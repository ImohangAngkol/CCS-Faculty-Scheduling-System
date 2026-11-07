"""Internal authority bridge; no installed institutional directory or verifier.

Directories/verifiers must be independently trusted server dependencies. Neither
records nor proofs are HTTP DTOs. Account roles and Chair-review mandates alone
cannot supply the optimization capability. Guards must serialize revocation.
"""
from contextlib import contextmanager,ExitStack
from contextvars import ContextVar
from dataclasses import asdict,dataclass
import hashlib
import math
from pathlib import Path
import time
from services.ga_run_authority import RunError,Grant,digest,uuid

VERSION='ga-scoped-optimization-qualification-v1'
ACTIONS=frozenset({'admit','status','execute','resume','pause','stop','checkpoint','checkpoint_write','result'})

def hash_value(value):
    if type(value) is not str or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
        raise RunError('GA_QUALIFICATION_IDENTITY_INVALID')
    return value

def valid_window(start,end,now):
    return (all(type(v) in (int,float) and math.isfinite(v) for v in (start,end,now))
            and start<=now<end)

@dataclass(frozen=True)
class Attestation:
    binding_digest:str
    source_id:str
    evidence_digest:str
    issued_at:float
    expires_at:float

def attest(verifier,kind,binding,source_id,clock):
    if verifier is None:raise RunError('GA_INDEPENDENT_VERIFIER_UNAVAILABLE',503)
    try:
        value=verifier.verify(kind,binding,source_id)
        if (type(value) is not Attestation or value.binding_digest!=binding or value.source_id!=source_id
                or not valid_window(value.issued_at,value.expires_at,clock())):raise ValueError()
        hash_value(value.evidence_digest);hash_value(value.source_id)
        return value
    except Exception:raise RunError('GA_SOURCE_ATTESTATION_REQUIRED',403) from None

@dataclass(frozen=True)
class OptimizationMandate:
    record_id:str
    revision:str
    actor_id:str
    department_id:str
    capability:str
    actions:tuple[str,...]
    source_id:str
    state:str
    effective_from:float
    effective_until:float

class ScopedAuthority:
    def __init__(self,directory,verifier,*,clock=time.time):
        self.directory=directory;self.verifier=verifier;self.clock=clock
        self._scope=ContextVar('qualified-optimization-scope',default=None)

    @contextmanager
    def guard(self,context):
        if self.directory is None or self.verifier is None:raise RunError('GA_SCOPED_DIRECTORY_UNAVAILABLE',503)
        with ExitStack() as stack:
            try:
                stack.enter_context(self.directory.guard())
                stack.enter_context(self.verifier.guard())
            except Exception:raise RunError('GA_SCOPED_DIRECTORY_UNAVAILABLE',503) from None
            token=self._scope.set((context.actor_id,context.department_id,context.catalog_reference))
            try:yield
            finally:self._scope.reset(token)

    def _qualified(self,context):
        if self._scope.get()!=(context.actor_id,context.department_id,context.catalog_reference):
            raise RunError('GA_AUTHORITY_GUARD_REQUIRED',403)
        uuid(context.actor_id);uuid(context.department_id)
        if context.action not in ACTIONS:raise RunError('GA_OPTIMIZATION_ACTION_UNSUPPORTED',403)
        try:
            records=self.directory.records_for(context.actor_id,context.department_id)
            if type(records) is not tuple or len(records)!=1:raise ValueError()
            record=records[0]
            if type(record) is not OptimizationMandate:raise ValueError()
            uuid(record.record_id);hash_value(record.source_id)
            if ((record.actor_id,record.department_id)!=(context.actor_id,context.department_id)
                    or record.capability!='department_optimization_control' or record.state!='ACTIVE'
                    or not isinstance(record.revision,str) or not 1<=len(record.revision)<=64
                    or type(record.actions) is not tuple or not record.actions
                    or len(set(record.actions))!=len(record.actions) or not set(record.actions)<=ACTIONS
                    or context.action not in record.actions
                    or not valid_window(record.effective_from,record.effective_until,self.clock())):raise ValueError()
            binding=digest(asdict(record))
            proof=attest(self.verifier,'optimization-mandate',binding,record.source_id,self.clock)
            return record,proof,binding
        except Exception:raise RunError('GA_SCOPED_OPTIMIZATION_MANDATE_REQUIRED',403) from None

    def authorize(self,context):
        record,proof,binding=self._qualified(context);now=self.clock()
        policy=digest({'contract':VERSION,'implementation':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'mandate':binding,'evidence':proof.evidence_digest})
        return Grant(digest(asdict(context)),record.actor_id,record.department_id,context.action,
            record.capability,policy,now,min(now+60,record.effective_until,proof.expires_at))

    def audit(self,context):
        record,proof,binding=self._qualified(context)
        return {'contract':VERSION,'context_digest':digest(asdict(context)),'record_id':record.record_id,
            'implementation_fingerprint':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'record_revision':record.revision,'mandate_digest':binding,'source_id':record.source_id,
            'evidence_digest':proof.evidence_digest,'action':context.action,'department_id':record.department_id,
            'qualification_scope':'SERVER_PROVIDER_CONTRACT_ONLY','publication_authority':False}
