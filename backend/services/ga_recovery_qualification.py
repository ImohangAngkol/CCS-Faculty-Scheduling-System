"""U5N isolated recovery authority, independent of optimization/Chair roles.

No installed provider, HTTP DTO, production root or worker activation switch.
"""
from contextlib import contextmanager,ExitStack
from dataclasses import dataclass,asdict
import time
from services.ga_run_authority import RunError,digest,uuid
from services.ga_qualification_authority import attest,hash_value,valid_window

VERSION='ga-recovery-qualification-v1'

@dataclass(frozen=True)
class RecoveryContext:
    actor_id:str
    department_id:str
    run_id:str
    request_id:str
    package_hash:str
    epoch:int
    target_store:str
    action:str='restore_quarantine'

@dataclass(frozen=True)
class RecoveryMandate:
    record_id:str
    revision:str
    actor_id:str
    department_id:str
    run_id:str
    source_id:str
    state:str
    effective_from:float
    effective_until:float
    capability:str='checkpoint_quarantine_recovery'
    actions:tuple[str,...]=('restore_quarantine','inspect_quarantine')

class RecoveryAuthority:
    def __init__(self,directory,verifier,*,clock=time.time):
        self.directory=directory;self.verifier=verifier;self.clock=clock

    @contextmanager
    def authorized(self,context):
        for value in [context.actor_id,context.department_id,context.run_id,context.request_id,context.target_store]:uuid(value)
        hash_value(context.package_hash)
        if type(context.epoch) is not int or context.epoch<1:raise RunError('GA_RECOVERY_EPOCH_INVALID')
        if self.directory is None or self.verifier is None:raise RunError('GA_RECOVERY_AUTHORITY_UNAVAILABLE',503)
        with ExitStack() as stack:
            try:
                stack.enter_context(self.directory.guard());stack.enter_context(self.verifier.guard())
                records=self.directory.records_for(context.actor_id,context.department_id)
                if type(records) is not tuple or len(records)!=1 or type(records[0]) is not RecoveryMandate:raise ValueError()
                r=records[0];uuid(r.record_id);hash_value(r.source_id)
                if ((r.actor_id,r.department_id,r.run_id)!=(context.actor_id,context.department_id,context.run_id)
                        or r.capability!='checkpoint_quarantine_recovery' or r.state!='ACTIVE'
                        or type(r.revision) is not str or not 1<=len(r.revision)<=64
                        or type(r.actions) is not tuple or len(set(r.actions))!=len(r.actions)
                        or not set(r.actions)<={'restore_quarantine','inspect_quarantine'} or context.action not in r.actions
                        or not valid_window(r.effective_from,r.effective_until,self.clock())):raise ValueError()
                binding=digest(asdict(r));proof=attest(self.verifier,'recovery-mandate',binding,r.source_id,self.clock)
            except Exception:raise RunError('GA_INDEPENDENT_RECOVERY_AUTHORITY_REQUIRED',403) from None
            # Keep both provider guards held through the operation and its commit.
            yield dict(actor_id=r.actor_id,authorized_role='RECOVERY_OPERATOR',department_id=r.department_id,
                target_run=r.run_id,action=context.action,decision='AUTHORIZED',time=self.clock(),
                mandate_digest=binding,record_id=r.record_id,revision=r.revision,source_id=r.source_id,
                evidence_digest=proof.evidence_digest,context_digest=digest(asdict(context)),
                expires_at=min(r.effective_until,proof.expires_at),institutional_authority=False)
