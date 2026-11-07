"""Isolated prepared-input delivery adapter. No raw academic CSV transformer.

The trusted catalog owns a guarded immutable prepared snapshot. An independent
verifier must attest its complete identity. No cached Functions globals, file
fallback, client fingerprints, deployment registration or source writes.
"""
from contextlib import contextmanager,ExitStack
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
import random
import time
from services.ga_input_bundle import InputBundle,capture,digest,canonical
from services.ga_bundle_optimizer import Session
from services.ga_trusted_runs import Capture
from services.ga_run_authority import RunError,uuid
from services.ga_qualification_authority import attest,hash_value,valid_window

VERSION='ga-prepared-input-delivery-v1'

@dataclass(frozen=True)
class PreparedSnapshot:
    department_id:str
    reference:str
    revision:str
    source_id:str
    prepared_bundle:InputBundle
    effective_from:float
    effective_until:float

def identity(record):
    return {'contract':VERSION,'department_id':record.department_id,'reference':record.reference,
        'revision':record.revision,'source_id':record.source_id,'bundle':record.prepared_bundle.fingerprint,
        'effective_from':record.effective_from,'effective_until':record.effective_until}

class CaptureAdapter:
    def __init__(self,catalog,verifier,*,clock=time.time):
        self.catalog=catalog;self.verifier=verifier;self.clock=clock
        self._active=ContextVar('prepared-input-source-guard',default=None)

    @contextmanager
    def guard(self,actor,department,reference):
        uuid(actor);uuid(department)
        if self.catalog is None or self.verifier is None:raise RunError('GA_TRUSTED_CATALOG_UNAVAILABLE',503)
        with ExitStack() as stack:
            try:
                stack.enter_context(self.verifier.guard())
                stack.enter_context(self.catalog.guard())
                record=self.catalog.snapshot(department,reference)
                if (type(record) is not PreparedSnapshot or record.department_id!=department or record.reference!=reference
                        or not isinstance(record.revision,str) or not 1<=len(record.revision)<=64
                        or type(record.prepared_bundle) is not InputBundle
                        or not valid_window(record.effective_from,record.effective_until,self.clock())):raise ValueError()
                hash_value(record.source_id)
                InputBundle.from_bytes(record.prepared_bundle._raw,record.prepared_bundle.run_id,record.prepared_bundle.fingerprint)
                binding=digest(canonical(identity(record)))
                attest(self.verifier,'prepared-input-snapshot',binding,record.source_id,self.clock)
            except Exception:raise RunError('GA_PREPARED_SOURCE_UNQUALIFIED',503) from None
            token=self._active.set((actor,department,reference,record,binding))
            try:yield self
            finally:self._active.reset(token)

    def capture(self,run_id,actor,department,reference):
        uuid(run_id);active=self._active.get()
        if active is None or active[:3]!=(actor,department,reference):raise RunError('GA_CAPTURE_GUARD_REQUIRED')
        _,_,_,record,binding=active
        try:
            before=self.catalog.snapshot(department,reference)
            if type(before) is not PreparedSnapshot or digest(canonical(identity(before)))!=binding:raise ValueError()
            InputBundle.from_bytes(before.prepared_bundle._raw,before.prepared_bundle.run_id,before.prepared_bundle.fingerprint)
            prepared=record.prepared_bundle;working=prepared.materialize(prepared.run_id)
            import json
            doc=json.loads(prepared._raw)
            sources=dict(doc['source_identities'])
            proof=attest(self.verifier,'prepared-input-snapshot',binding,record.source_id,self.clock)
            sources.update(prepared=prepared.fingerprint,captureadapter=digest(Path(__file__).read_bytes()),
                catalogbinding=binding,sourceattestation=proof.evidence_digest)
            bundle=capture(run_id=run_id,templates=working['templates'],fallback_templates=working['fallback_templates'],
                legacy_preferences=working['legacy_preferences'],scoring_context=working['scoring_context'],
                configuration=working['configuration'],source_identities=sources,seed=working['seed'],
                academic_context_reference=doc['academic_context_reference'])
            # Construction performs full U5H model/engine/config/alias preflight,
            # but executes zero optimizer generations and performs no persistence.
            Session(bundle,run_id=run_id,random_state=random.Random(0).getstate())
            after=self.catalog.snapshot(department,reference)
            if type(after) is not PreparedSnapshot or digest(canonical(identity(after)))!=binding:raise ValueError()
            InputBundle.from_bytes(after.prepared_bundle._raw,after.prepared_bundle.run_id,after.prepared_bundle.fingerprint)
            if not valid_window(record.effective_from,record.effective_until,self.clock()):raise ValueError()
            if attest(self.verifier,'prepared-input-snapshot',binding,record.source_id,self.clock).evidence_digest!=proof.evidence_digest:raise ValueError()
            return Capture(bundle,department,reference)
        except Exception:raise RunError('GA_PREPARED_SOURCE_CHANGED_OR_INVALID') from None
