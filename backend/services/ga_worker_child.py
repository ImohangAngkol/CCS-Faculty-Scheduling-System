"""Single bounded batch process. No authority, database or storage credentials.

Only one bounded JSON request/response; protocol never printed to logs/evidence.
All original import/progress stdout is discarded. No persistent checkpoint sink.
"""
import base64
from contextlib import redirect_stdout,redirect_stderr
import json
import sys
from services.ga_worker_contract import VERSION,fictional_source,implementation
from services.ga_input_bundle import InputBundle,canonical,digest

MAX_MESSAGE=64*1024*1024

class Discard:
    def write(self,value):return len(value)
    def flush(self):pass

def batch(request):
    fictional_source()
    from services.ga_bundle_optimizer import Session
    from services.ga_checkpoint_service import rng_from_json,rng_to_json
    if request['contract']!=VERSION or request['implementation']!=implementation():raise ValueError()
    bundle=InputBundle.from_bytes(base64.b64decode(request['bundle'],validate=True),request['run'],request['bundle_hash'])
    if request['checkpoint'] is None:
        session=Session(bundle,run_id=bundle.run_id,random_state=rng_from_json(request['rng']))
    else:
        session=Session.restore(bundle,base64.b64decode(request['checkpoint'],validate=True),run_id=bundle.run_id,
            expected_fingerprint=request['inner_hash'],expected_sequence=request['sequence'],expected_parent=request['inner_parent'])
    target=request['target']
    if type(target) is not int or not 0<=target<=session.working['configuration']['generations']:raise ValueError()
    def boundary(kind,data):
        if data['generation']>=target:session.control.request_pause()
    if session.run(boundary) is not None or session.checkpoint is None:raise ValueError()
    state=session.resume_state
    if state['generation_completed']!=target:raise ValueError()
    # Original fixed engine finalization, with stop requested before the next
    # draw: produces the exact saved-best projection without advancing again.
    projection=Session.restore(bundle,session.checkpoint,run_id=bundle.run_id,
        expected_fingerprint=session.checkpoint_fingerprint,expected_sequence=session.sequence,expected_parent=session.parent_fingerprint)
    projection.control.request_stop();before=state['random_state'];result=projection.run()
    if projection.runtime.random.getstate()!=before:raise ValueError()
    return dict(contract=VERSION,implementation=implementation(),run=bundle.run_id,
        inner=base64.b64encode(session.checkpoint).decode(),inner_hash=session.checkpoint_fingerprint,
        sequence=session.sequence,inner_parent=session.parent_fingerprint,projection=result,
        rng_hash=digest(canonical(rng_to_json(before))),receipt=session.receipt())

def main():
    wire=sys.stdout.buffer
    try:
        raw=sys.stdin.buffer.readline(MAX_MESSAGE+1)
        if len(raw)>MAX_MESSAGE or not raw.endswith(b'\n'):raise ValueError()
        with redirect_stdout(Discard()),redirect_stderr(Discard()):result=batch(json.loads(raw))
        output=canonical(result)+b'\n'
        if len(output)>MAX_MESSAGE:raise ValueError()
        wire.write(output);wire.flush();return 0
    except BaseException:
        wire.write(canonical({'error':'GA_WORKER_CHILD_REJECTED'})+b'\n');wire.flush();return 1

if __name__=='__main__':raise SystemExit(main())
