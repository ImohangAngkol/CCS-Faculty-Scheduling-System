"""Pure-policy fictional decision evidence; no GA/application/database import."""
from datetime import datetime
import json
import random
from pathlib import Path
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'backend'))
from tests.test_saved_best_context import FictionalVerifier,inputs,payload
from services import saved_best_policy as policy


def main():
    started=datetime.now().astimezone().isoformat();tick=time.perf_counter();rng=random.getstate()
    owned=Path(tempfile.mkdtemp(prefix='u5pa-decisions-')).resolve()
    assert owned.parent==Path(tempfile.gettempdir()).resolve()
    (owned/'OWNED.txt').write_text('Fictional Saved Best policy evidence; no institutional authority')
    path=owned/'best.json';verifier=FictionalVerifier();rows=[]
    def trial(name,candidate,provider,expected):
        before=path.read_bytes() if path.exists() else None
        result=policy.consider(path,candidate,provider)
        after=path.read_bytes() if path.exists() else None
        assert result.classification==expected
        rows.append(dict(name=name,classification=result.classification,reason=result.reason,
            updated=result.updated,archive_bytes_unchanged=before==after,
            retained_fitness=None if after is None else json.loads(after)['best_fitness']))
    trial('unverified candidate, empty store',payload(0),None,'UNVERIFIED')
    trial('verified first candidate',payload(100),verifier,'ELIGIBLE')
    trial('same-context smaller penalty improves',payload(90),verifier,'ELIGIBLE')
    trial('same-context larger penalty does not improve',payload(110),verifier,'ELIGIBLE')
    trial('same-context equal penalty preserves bytes',payload(90),verifier,'ELIGIBLE')
    trial('different preferences, smaller penalty',payload(0),FictionalVerifier(inputs(preferences_fingerprint='b'*64)),'INCOMPATIBLE')
    trial('different department, smaller penalty',payload(0),FictionalVerifier(inputs(department_id='fictional-other')),'INCOMPATIBLE')
    trial('different offerings',dict(payload(0),subject_keys=['FIC202::FIC-B']),verifier,'INCOMPATIBLE')
    trial('same-context exact zero improves',payload(0),verifier,'ELIGIBLE')
    trial('exact zero cannot regress',payload(1),verifier,'ELIGIBLE')
    # A historical record is preserved as-is, never silently stamped or migrated.
    path.write_bytes(policy.canonical(payload(475)))
    trial('missing historical provenance',payload(0),verifier,'UNVERIFIED')
    assert random.getstate()==rng
    target=BASE/(datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')+'-decisions');target.mkdir(exist_ok=False)
    result=dict(scope='Pure policy with an explicit fictional verifier and owned temporary files; not institutional approval, actual optimizer consumption or HTTP acceptance',
        started_at=started,ended_at=datetime.now().astimezone().isoformat(),elapsed_seconds=time.perf_counter()-tick,
        passed=len(rows),failed=0,global_rng_unchanged=True,rows=rows,raw_payloads_or_attestations_archived=False)
    with (target/'decision-evidence.json').open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',fictional_decisions=len(rows),evidence=target.relative_to(ROOT).as_posix())))


if __name__=='__main__':main()
