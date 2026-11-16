"""Fresh-process PRIVATE-store reader, never a GA execution worker.

Only accepts a bounded pin on stdin inside an owned empty-import source snapshot.
Fresh fictional authority providers come from reviewed server fixture code.
No Session.run(), process supervision, checkpoint creation or API launch.
"""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'backend'))
from services.ga_worker_contract import fictional_source
fictional_source()  # Fails BEFORE any fixture/model imports in a real checkout.

with redirect_stdout(io.StringIO()):
    from services.prototype_recovery_bootstrap import Pin, reopen
    from services.prototype_continuation_supervisor import checkpoint_audit
    from tests.test_prototype_cycle import WorkflowDirectory
    from tests.test_prototype_inputs import Directory
    from tests.test_prototype_workload import PRINCIPAL, FictionalGrants
    from services.prototype_cycle import identity

raw = sys.stdin.buffer.read(16385)
assert len(raw) <= 16384
request = json.loads(raw)
assert set(request) == {'pin', 'nonce'}
identity(request['nonce'])
pin = Pin(**request['pin'])
before = random.getstate()
cycle = reopen(pin, PRINCIPAL, workload_authority=FictionalGrants(),
               input_directory=Directory(), workflow_directory=WorkflowDirectory())
assert cycle.offline_qualification is False
proof = checkpoint_audit(cycle, PRINCIPAL, pin.run_id)
assert random.getstate() == before
print(json.dumps(dict(nonce=request['nonce'], checkpoint=proof,
    classification='FRESH_PROCESS_READ_ONLY_BOOTSTRAP_METADATA',
    native_workers=0, GA_executions=0, Session_run_calls=0, browsers=0,
    physical_resource_supervision=False, institutional_authority=False)))
