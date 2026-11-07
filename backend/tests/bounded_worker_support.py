"""Explicit fictional J-qualified dependencies; no application registration."""
import time
from dataclasses import asdict
from services.ga_qualification_authority import ScopedAuthority,OptimizationMandate,ACTIONS
from services.ga_qualified_capture import CaptureAdapter,PreparedSnapshot,identity
from services.ga_input_bundle import digest,canonical
from services.ga_run_authority import digest as object_digest
from tests.test_qualified_execution import FictionalDirectory,FictionalVerifier,FictionalCatalog
from tests.trusted_run_support import ACTOR,DEPT,CATALOG,FictionalSource

TEMPLATE='00000000-0000-4000-8000-000000000971'

def dependencies(generations=0,prepared=None):
    mandate=OptimizationMandate('00000000-0000-4000-8000-000000000972','FICTIONAL-WORKER-v1',ACTOR,DEPT,
        'department_optimization_control',tuple(sorted(ACTIONS)),'a'*64,'ACTIVE',0.0,float(2**40))
    directory=FictionalDirectory((mandate,));verifier=FictionalVerifier(time.time)
    verifier.approved[('optimization-mandate',object_digest(asdict(mandate)))]=mandate.source_id
    bundle=prepared or FictionalSource(generations).capture(TEMPLATE,ACTOR,DEPT,CATALOG).bundle
    record=PreparedSnapshot(DEPT,CATALOG,'FICTIONAL-WORKER-SOURCE-v1','b'*64,bundle,0.0,float(2**40))
    catalog=FictionalCatalog(record)
    verifier.approved[('prepared-input-snapshot',digest(canonical(identity(record))))]=record.source_id
    return ScopedAuthority(directory,verifier),CaptureAdapter(catalog,verifier),verifier
