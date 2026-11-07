"""U5F replayable preservation/privacy audit; no GA imports or index writes.

--record creates a new manifest and staging plan, refusing replacement.
Existing U5D/U5E evidence is verified using its archived entry bytes where U5F
adds a router to an already mixed file. No historical artifact is rewritten.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
from integration import main as integrate_main,generate

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
HEAD='d6db077793da52b7559351a5d0f8e6d54608cb77'
MIXED={'backend/main.py':integrate_main,'frontend/src/pages/admin/GenerateSchedule.tsx':generate}
NEW=['backend/services/continuous_readiness.py','backend/routers/continuous_optimization.py',
     'backend/tests/test_continuous_readiness.py','backend/tests/test_continuous_fixed_qualification.py',
     'frontend/src/services/continuousOptimization.ts','frontend/src/components/ga/OptimizationMode.tsx',
     'frontend/tests/continuousOptimization.test.mjs','frontend/tests/continuousOptimization.browser.test.mjs',
     'frontend/tests/continuousOptimization.fixtures.mjs','frontend/tests/continuousOptimizationRun.fixtures.mjs',
     'frontend/tests/continuousOptimization.scenarios.mjs']
REPORT='docs/dashboard-u5f-controlled-continuous-optimization.md'
helpers=runpy.run_path(str(BASE.parent/'dashboard-u5e/audit_evidence.py'))
png=helpers['png'];counts=helpers['counts']

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args,input=None):return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),*args],cwd=ROOT,input=input,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)
def write_new(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(value,indent=2)+'\n')

def inspect(record=False):
    assert git('rev-parse','HEAD').decode().strip()==HEAD and git('branch','--show-current').decode().strip()=='main','HEAD_OR_BRANCH_CHANGED_STOP'
    assert not git('diff','--cached','--name-only').strip(),'STAGED_CONTENT_STOP'
    baseline=json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'))
    assert len(baseline)==3541 and sum(n.startswith('backend/data/') for n in baseline)==23
    for name,digest in baseline.items():
        if name not in MIXED:assert (ROOT/name).is_file() and sha(ROOT/name)==digest,'BASELINE_CHANGED_STOP: '+name
    proposed={}
    for name,transform in MIXED.items():
        assert transform((BASE/'entry'/Path(name).name).read_bytes())==(ROOT/name).read_bytes(),'MIXED_INSERTION_CHANGED_STOP: '+name
        proposed[name]=transform(git('show',HEAD+':'+name))
        git('apply','--check','--cached',str(BASE/(Path(name).stem+'-integration.patch')))
    entry=json.loads((BASE/'entry-review.json').read_text(encoding='utf-8'))
    assert set(git('diff','--name-only').decode().splitlines())==set(entry['preexisting_tracked_modifications']),'UNEXPECTED_TRACKED_CHANGE_STOP'
    for folder in ['backend/data','backend/run_checkpoints','backend/saved_chromosomes','backend/run_input_receipts_v1','backend/run_provenance_v1','backend/constrained_runs_v2','backend/generation_snapshots','backend/stopped_runs']:
        assert not {p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file()}-set(baseline),'NEW_RUNTIME_FILE_STOP: '+folder
    prior_hashes={}
    for milestone in ['dashboard-u5d','dashboard-u5e/r2']:
        prior=json.loads((BASE.parent/milestone/'manifest.json').read_text(encoding='utf-8'))
        for name,digest in prior['artifact_sha256'].items():
            path=BASE/'entry/main.py' if name=='backend/main.py' else ROOT/name
            assert sha(path)==digest,'PRIOR_EVIDENCE_CHANGED_STOP: '+name
        prior_hashes[milestone]=len(prior['artifact_sha256'])
    proofs=sorted(BASE.glob('*snapshot/snapshot-proof.json'))
    proof=json.loads(proofs[-1].read_text(encoding='utf-8'))
    assert proof['complete'] and proof['no_actual_staging'] and proof['no_u5d_u5e_or_live_center_dependency'],'SNAPSHOT_NOT_COMPLETE_STOP'
    for name,digest in proof['source_sha256'].items():
        raw=proposed.get(name,(ROOT/name).read_bytes())
        assert hashlib.sha256(raw).hexdigest()==digest,'SNAPSHOT_SOURCE_DRIFT_STOP: '+name
        assert git('hash-object','--stdin',input=raw).decode().strip()==proof['proposed_blob_oids'][name]
    inventory=sorted(set(MIXED)|set(NEW)|{REPORT,'docs/testing/dashboard-u5f/manifest.json','docs/testing/dashboard-u5f/staging-plan.json'}|{p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file()})
    assert not any(n.startswith('backend/data/') or Path(n).name.startswith('.env') for n in inventory)
    untracked=set(git('ls-files','--others','--exclude-standard','-z').decode().split('\0'))-{''}
    assert not untracked-set(baseline)-set(inventory),'UNAPPROVED_NEW_PATH_STOP'
    git('diff','--check','--',*MIXED);git('diff','--cached','--check')
    partial={name:{'patch':(BASE/(Path(name).stem+'-integration.patch')).relative_to(ROOT).as_posix(),
        'proposed_sha256':hashlib.sha256(raw).hexdigest(),'proposed_blob_oid':git('hash-object','--stdin',input=raw).decode().strip()} for name,raw in proposed.items()}
    plan=dict(head=HEAD,exact_checkpoint_inventory=inventory,whole_file_paths=[n for n in inventory if n not in MIXED],partial_only=partial,
        excluded_tracked_paths=sorted(set(entry['preexisting_tracked_modifications'])-set(MIXED)),
        actual_staging=False,commit_push_authorized=False,
        recommended_messages=['feat(ga): add blocked continuous-mode readiness foundation','docs(testing): archive U5F foundation and fixed lifecycle qualification'],
        instructions=['Separate authorization and fresh upstream/inventory verification required before a checkpoint.',
            'Add only literal whole_file_paths; both main.py and GenerateSchedule.tsx require partial patches.',
            'Future authorized partial command: git apply --cached <each exact patch listed in partial_only>.',
            'Verify staged blob OIDs against proposed_git_blob_oids. Use core.autocrlf=false for artifact byte preservation.',
            'Do not stage U5D/U5E, U4/Live Center, protected JSON or unrelated research. No add dot or add -A.',
            'Independent proposed source snapshot already passes; this is not permission to stage.'])
    if record and not (BASE/'staging-plan.json').exists():write_new(BASE/'staging-plan.json',plan)
    else:assert json.loads((BASE/'staging-plan.json').read_text(encoding='utf-8'))==plan
    attempts=[]
    for path in sorted(BASE.rglob('*command.json')):
        row=json.loads(path.read_text(encoding='utf-8'));attempts.append(dict(path=path.relative_to(ROOT).as_posix(),selection=row['selection'],exit_code=row['exit_code'],counts=counts(row)))
    snapshot=[]
    for path in sorted(proofs[-1].parent.glob('*-command.json')):
        row=json.loads(path.read_text(encoding='utf-8'));assert row['exit_code']==0
        snapshot.append(dict(selection=row['selection'],counts=counts(row),path=path.relative_to(ROOT).as_posix()))
    assert len(snapshot)==8
    for key,total,field in [('backend',20,'passed'),('fixed',9,'passed'),('focused',14,'pass'),('regressions',166,'pass'),('browser',17,'pass')]:
        assert next(r for r in snapshot if r['selection']==key)['counts'][field]==total
    for key,total,field in [('receipts',36,'passed'),('backend-regressions',99,'passed'),('u5e-contracts',30,'pass')]:
        final=[r for r in attempts if r['selection']==key][-1]
        assert final['exit_code']==0 and final['counts'][field]==total
    assert [r for r in attempts if r['selection']=='integrity'][-1]['exit_code']==0
    # Private records stay in memory solely for comparison; they are never emitted.
    registry=json.loads((ROOT/'backend/data/faculty_identities.json').read_text(encoding='utf-8'))['faculty']
    names={re.sub(r'\s+',' ',s.strip().upper()) for row in registry for s in [row['name'],*row.get('aliases',[])] if len(s.strip())>=8}
    patterns=[r'eyJ[A-Za-z0-9_=-]{16,}',r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}',r'(?i)\b(?:postgresql|postgres|mysql)(?:\+\w+)?://[^\s]+',r'-----BEGIN [A-Z ]*PRIVATE KEY-----',r'(?i)https?://[^\s/]+:[^\s/@]+@',r'(?i)(?<![\w])(?:set-cookie|authorization)\s*:\s*[^\s]{16,}']
    hashes={};oids={};screens={}
    for name in inventory:
        if name=='docs/testing/dashboard-u5f/manifest.json':continue
        path=ROOT/name;raw=path.read_bytes();hashes[name]=sha(path)
        if path.suffix=='.png':screens[name]=png(path)
        else:
            content=raw.decode('utf-8');assert content.endswith('\n'),'MISSING_NEWLINE_STOP: '+name
            if path.suffix!='.patch':assert all(line==line.rstrip() for line in content.splitlines()),'WHITESPACE_STOP: '+name
            upper=re.sub(r'\s+',' ',content.upper())
            assert not any(re.search(r'(?<!\w)'+re.escape(s)+r'(?!\w)',upper) for s in names),'PRIVATE_NAME_STOP_WITHHELD'
            assert not any(re.search(p,content) for p in patterns),'SENSITIVE_PATTERN_STOP_WITHHELD'
        raw=proposed.get(name,raw);oids[name]=git('hash-object','--stdin',input=raw).decode().strip()
        assert oids[name]==git('-c','core.autocrlf=false','hash-object','--path='+name,'--stdin',input=raw).decode().strip()
    visual=json.loads((BASE/'screenshot-review.json').read_text(encoding='utf-8'))
    assert set(visual['reviewed_sha256'])=={sha(ROOT/n) for n in screens} and visual['private_records_seen'] is False,'UNREVIEWED_SCREENSHOT_STOP'
    for path in BASE.rglob('browser-results.json'):
        row=json.loads(path.read_text(encoding='utf-8'))
        for c in row['captures']:
            n=(path.parent/c['file']).relative_to(ROOT).as_posix()
            assert all(screens[n][d]==c['viewport'][d] for d in ['width','height']),'VIEWPORT_MISMATCH_STOP'
    assert git('rev-parse','HEAD').decode().strip()==HEAD and sha(ROOT/'.git/index')==baseline['.git/index']
    return dict(milestone='U5F',status='UI_AND_READINESS_FOUNDATION_ONLY_CONTINUOUS_EXECUTION_BLOCKED',head=HEAD,
        exact_checkpoint_inventory=inventory,modified_from_entry=list(MIXED),new_paths=[n for n in inventory if n not in MIXED],
        preexisting_tracked_modifications=entry['preexisting_tracked_modifications'],baseline_paths=3541,unchanged_baseline_paths=3539,protected_academic_paths=23,
        prior_artifact_hashes_verified=prior_hashes,protected_preferences_settings='BYTE_IDENTICAL_UNSTAGED_EXCLUDED',
        ga_scoring_operators_rng_engine_fingerprints_migrations_checkpoints_saved_best_history='UNCHANGED',
        artifact_sha256=hashes,proposed_git_blob_oids=oids,screenshots=screens,attempts=attempts,isolated_snapshot_checks=snapshot,
        privacy='PASS: encoded complete/truncated fragments, credentials/headers, private-name comparison, PNG metadata/CRC and visual review',
        whitespace='PASS',git_index_head='UNCHANGED',staged_files=[],continuous_datasets=[],continuous_executable=False,
        limitations=['No continuous worker, checkpoint version, immutable model bundle, scoped Chair mandate or resource enforcement.',
            'Browser responses intercepted; no live browser-to-GA or institutional database acceptance.',
            'Fixed cancellation is cooperative at boundaries, not an interrupt within fitness evaluation.',
            'Historical failures retained; no institutional approval or provider activation.'])

if __name__=='__main__':
    value=inspect('--record' in sys.argv)
    if '--record' in sys.argv:write_new(BASE/'manifest.json',dict(value,recorded_at=datetime.now().astimezone().isoformat()))
    else:
        recorded=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'));assert {k:v for k,v in recorded.items() if k!='recorded_at'}==value
    print(json.dumps(dict(status='AUDIT_PASSED',inventory=len(value['exact_checkpoint_inventory']),artifact_hashes=len(value['artifact_sha256']),baseline_unchanged=value['unchanged_baseline_paths'],continuous_executable=False)))
