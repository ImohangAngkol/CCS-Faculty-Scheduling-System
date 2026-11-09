"""Short explicit fictional research operator, executable ONLY in owned snapshot.

The fixture issuer/catalog are independently scoped synthetic test records,
not institutional mandates. No deployment, UI switch or long-running server.
"""
from contextlib import redirect_stdout,redirect_stderr
from pathlib import Path
import json
import os
import sys
import time
from uuid import uuid4


def main():
    if sys.argv[1:]!=['--fictional-only']:raise SystemExit('Explicit --fictional-only required')
    root=Path(__file__).resolve().parents[3];sys.path.insert(0,str(root/'backend'))
    from services.ga_worker_contract import fictional_source,Limits
    fictional_source()
    class Discard:
        def write(self,value):return len(value)
        def flush(self):pass
    wire=sys.stdout
    with redirect_stdout(Discard()),redirect_stderr(Discard()):
        from services.ga_research_bridge import ResearchBridge,ResearchWorker
        from services.ga_research_context import ResearchPermit
        from services.ga_owned_store import Store
        from services.ga_trusted_runs import Coordinator
        from tests.bounded_worker_support import dependencies
        from tests.trusted_run_support import ACTOR,DEPT,CATALOG,PRINCIPAL
        authority,catalog,_=dependencies(generations=1)
        prepared=catalog.catalog.record.prepared_bundle
        permit=ResearchPermit(ACTOR,DEPT,CATALOG,prepared.fingerprint,'FICTIONAL-YEAR','FICTIONAL-TERM','FICTIONAL-DATASET')
        worker=ResearchWorker(Coordinator(Store.create(max_runs=4),authority,catalog),initialize=True)
        bridge=ResearchBridge(worker,permit,initialize=True)
        try:
            run=bridge.admit(PRINCIPAL,str(uuid4()),Limits(wall_seconds=120))['run_id']
            bridge.start(PRINCIPAL,run);end=time.monotonic()+130
            while time.monotonic()<end:
                status=bridge.observe(PRINCIPAL,run)
                if status['state'] in {'COMPLETED','FAILED','RESOURCE_LIMITED','INTERRUPTED','RECOVERY_REQUIRED'}:break
                time.sleep(.1)
            else:raise RuntimeError('RESEARCH_DEMO_BOUND_EXCEEDED')
            observations=bridge.telemetry(PRINCIPAL,run)
            result=dict(scope='FICTIONAL_DISPOSABLE_ONLY',run_id=run,state=status['state'],
                generations=status['generation'],best_so_far_fitness=status['best_so_far_fitness'],
                context_qualification=status['context_qualification'],context_id=status['context_id'],
                telemetry_events=len(observations),checkpoint_sequence=status['checkpoint_sequence'],
                production_admission='BLOCKED',continuous_ui='DISABLED',seven_day='NO_GO',
                active_restore=False,storage_scope='NEW_OWNED_OS_TEMP',
                note='Tiny fictional demonstration; zero fitness is not convergence evidence.')
        finally:
            result_cleanup=worker.close(PRINCIPAL,timeout=10)
            if not result_cleanup['quiescent']:raise RuntimeError('RESEARCH_CLEANUP_UNVERIFIED')
        result['cleanup_verified']=True
    if os.environ.get('U5PB_EVIDENCE'):
        with (Path(os.environ['U5PB_EVIDENCE'])/'research-demo.json').open('x',encoding='utf-8') as f:
            json.dump(result,f,indent=2);f.write('\n')
    wire.write(json.dumps(result)+'\n');wire.flush()
    return 0 if result['state']=='COMPLETED' else 1


if __name__=='__main__':raise SystemExit(main())
