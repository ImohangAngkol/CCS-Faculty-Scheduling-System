"""Select actual completed records; never execute tests or hide later failures."""
from pathlib import Path
import hashlib
import json
import re
import runpy

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]


def main():
    records=[(p,json.loads(p.read_text(encoding='utf-8'))) for p in sorted(BASE.glob('*/command.json'))]
    def latest(selection):
        p,d=next((p,d) for p,d in reversed(records) if d.get('selection')==selection)
        assert d['exit_code']==0,'LATEST_SELECTION_FAILED: '+str(p)
        return p,d
    back={}
    for selection in ['operator','physical','native','bridge','parity','legacy','continuity','receipts','live']:
        p,d=latest(selection)
        count=re.search(r'\b(\d+) passed\b',d['stdout']);assert count
        assert not re.search(r'\b[1-9]\d* (?:failed|errors?)\b',d['stdout'])
        back[selection]=dict(path=p.relative_to(ROOT).as_posix(),passed=int(count[1]))
    front={}
    for selection in ['contracts-all','build','bundle','lint']:
        p,d=latest(selection);front[selection]=dict(path=p.relative_to(ROOT).as_posix())
        if selection=='contracts-all':
            count=re.search(r'\u2139 pass (\d+)\n',d['stdout']);assert count and '\u2139 fail 0\n' in d['stdout']
            front[selection]['passed']=int(count[1])
    p,_=latest('handoff-probe')
    code=runpy.run_path(str(BASE/'audit_evidence.py'))['CODE']
    summary=dict(status='QUALIFIED_ISOLATED_FICTIONAL_CONTROLS_ONLY',backend=back,
        backend_total_passed=sum(x['passed'] for x in back.values()),frontend=front,
        browser=dict(total=15,real_HTTP_scenarios=13,injected_error_scenarios=2,mocked_success_responses=0,
            nested_in_live_pytest_count=True),handoff_probe=p.relative_to(ROOT).as_posix(),
        human_handoff='NOT_PERFORMED',qualified_source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in code},
        selection_policy='Most recent record of each selection must pass; earlier failed attempts remain independently archived. Unchanged engine/worker regressions were not repeated after UI/read-only lookup additions.',
        production_admission='BLOCKED',institutional_saved_best_promotion='BLOCKED',continuous_optimization='DISABLED',active_restore='BLOCKED',seven_day='NO_GO')
    with (BASE/'qualification-summary.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(summary,f,indent=2);f.write('\n')
    print(json.dumps(dict(backend_passed=summary['backend_total_passed'],frontend_passed=front['contracts-all']['passed'],status=summary['status'])))


if __name__=='__main__':main()
