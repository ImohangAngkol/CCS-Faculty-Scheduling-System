"""Replay U5G new-file-only preservation/privacy/checkpoint-readiness audit.

No GA imports, database operations, index writes or historical evidence edits.
--record creates new manifest/plan and refuses manifest replacement.
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

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
HEAD='d6db077793da52b7559351a5d0f8e6d54608cb77'
NEW=['backend/services/ga_input_bundle.py','backend/tests/test_ga_input_bundle.py','backend/tests/test_ga_input_bundle_checkpoint_qualification.py']
REPORT='docs/dashboard-u5g-immutable-ga-input-bundle.md'
HELPER=runpy.run_path(str(BASE.parent/'dashboard-u5e/audit_evidence.py'))
png=HELPER['png'];counts=HELPER['counts']

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args,input=None):return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),*args],cwd=ROOT,input=input,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)
def write_new(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(value,indent=2)+'\n')

def inspect(record=False):
    assert git('rev-parse','HEAD').decode().strip()==HEAD and git('branch','--show-current').decode().strip()=='main','HEAD_CHANGED_STOP'
    assert not git('diff','--cached','--name-only').strip(),'STAGED_CONTENT_STOP'
    baseline=json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'))
    assert len(baseline)==3619 and sum(n.startswith('backend/data/') for n in baseline)==23
    for name,digest in baseline.items():assert (ROOT/name).is_file() and sha(ROOT/name)==digest,'PRESERVATION_STOP: '+name
    entry=json.loads((BASE/'entry-review.json').read_text(encoding='utf-8'))
    assert set(git('diff','--name-only').decode().splitlines())==set(entry['preexisting_tracked_modifications']),'TRACKED_CHANGE_STOP'
    for folder in ['backend/data','backend/run_checkpoints','backend/saved_chromosomes','backend/run_input_receipts_v1','backend/run_provenance_v1','backend/constrained_runs_v2','backend/generation_snapshots','backend/stopped_runs']:
        assert not {p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file()}-set(baseline),'NEW_RUNTIME_FILE_STOP: '+folder
    prior=json.loads((BASE.parent/'dashboard-u5f/manifest.json').read_text(encoding='utf-8'))
    assert len(prior['artifact_sha256'])==79
    for name,digest in prior['artifact_sha256'].items():assert sha(ROOT/name)==digest,'U5F_EVIDENCE_CHANGED_STOP'
    for source in json.loads((BASE/'source-map.json').read_text(encoding='utf-8'))['source_map']:
        assert sha(ROOT/source['path'])==source['sha256'],'DEPENDENCY_SOURCE_CHANGED_STOP'
    proof_path=sorted(BASE.glob('*snapshot/snapshot-proof.json'))[-1]
    proof=json.loads(proof_path.read_text(encoding='utf-8'))
    assert proof['complete'] and proof['no_actual_staging'] and proof['no_u5d_u5e_u5f_app_dependency'] and proof['consumption_verified'] is False
    for name in NEW:
        assert sha(ROOT/name)==proof['source_sha256'][name],'SNAPSHOT_SOURCE_DRIFT_STOP'
        assert git('hash-object','--stdin',input=(ROOT/name).read_bytes()).decode().strip()==proof['proposed_blob_oids'][name]
    inventory=sorted(set(NEW)|{REPORT,'docs/testing/dashboard-u5g/manifest.json','docs/testing/dashboard-u5g/staging-plan.json'}|{p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file()})
    assert not any(n in baseline or n.startswith('backend/data/') or Path(n).name.startswith('.env') for n in inventory)
    untracked=set(git('ls-files','--others','--exclude-standard','-z').decode().split('\0'))-{''}
    assert not untracked-set(baseline)-set(inventory),'UNAPPROVED_NEW_PATH_STOP'
    plan=dict(head=HEAD,exact_checkpoint_inventory=inventory,whole_file_paths=inventory,partial_only=[],modified_existing_files=[],
        excluded_tracked_paths=entry['preexisting_tracked_modifications'],actual_staging=False,commit_push_authorized=False,
        recommended_messages=['feat(ga): add immutable captured-input bundle foundation','docs(testing): archive U5G capture and legacy parity evidence'],
        instructions=['Separate authorization and fresh upstream/inventory review are required before a checkpoint.',
            'Only literal whole_file_paths are eligible. No existing or partial paths; never add dot or add -A.',
            'Keep every U5D/U5E/U5F and unrelated change outside this checkpoint.',
            'Use core.autocrlf=false to preserve evidence bytes; verify staged blob OIDs against proposed_git_blob_oids.',
            'HEAD plus only the three U5G source/test files passes independent fictional snapshot tests.',
            'Checkpoint label must say captured-input foundation; actual optimizer consumption is blocked.'])
    if record and not (BASE/'staging-plan.json').exists():write_new(BASE/'staging-plan.json',plan)
    else:assert json.loads((BASE/'staging-plan.json').read_text(encoding='utf-8'))==plan
    attempts=[]
    for path in sorted(BASE.rglob('*command.json')):
        row=json.loads(path.read_text(encoding='utf-8'));attempts.append(dict(path=path.relative_to(ROOT).as_posix(),selection=row['selection'],exit_code=row['exit_code'],counts=counts(row)))
        assert row['exit_code']==0,'FAILED_COMMAND_REQUIRES_REVIEW'
    for key,total,field in [('backend-regressions',99,'passed'),('receipts',36,'passed'),('analysis',20,'passed'),('backend',20,'passed'),('frontend',210,'pass'),('browser',17,'pass')]:
        assert [r for r in attempts if r['selection']==key][-1]['counts'][field]==total
    for key,total in [('bundle-tests',32),('fixed',10)]:
        row=json.loads((proof_path.parent/(key+'-command.json')).read_text(encoding='utf-8'))
        assert counts(row)['passed']==total and row['exit_code']==0
    for key in ['build','lint','integrity']:assert [r for r in attempts if r['selection']==key][-1]['exit_code']==0
    assert 'vite' in json.loads((ROOT/[r for r in attempts if r['selection']=='bundle'][-1]['path']).read_text(encoding='utf-8'))['stdout']
    registry=json.loads((ROOT/'backend/data/faculty_identities.json').read_text(encoding='utf-8'))['faculty']
    names={re.sub(r'\s+',' ',s.strip().upper()) for row in registry for s in [row['name'],*row.get('aliases',[])] if len(s.strip())>=8}
    patterns=[r'eyJ[A-Za-z0-9_=-]{16,}',r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}',r'(?i)\b(?:postgresql|postgres|mysql)(?:\+\w+)?://[^\s]+',r'-----BEGIN [A-Z ]*PRIVATE KEY-----',r'(?i)https?://[^\s/]+:[^\s/@]+@',r'(?i)(?<![\w])(?:set-cookie|authorization)\s*:\s*[^\s]{16,}']
    hashes={};oids={};screens={}
    for name in inventory:
        if name=='docs/testing/dashboard-u5g/manifest.json':continue
        path=ROOT/name;raw=path.read_bytes();hashes[name]=sha(path)
        if path.suffix=='.png':screens[name]=png(path)
        else:
            content=raw.decode('utf-8');assert content.endswith('\n') and all(line==line.rstrip() for line in content.splitlines()),'WHITESPACE_STOP: '+name
            upper=re.sub(r'\s+',' ',content.upper())
            assert not any(re.search(r'(?<!\w)'+re.escape(s)+r'(?!\w)',upper) for s in names),'PRIVATE_NAME_STOP_WITHHELD'
            assert not any(re.search(pattern,content) for pattern in patterns),'SENSITIVE_PATTERN_STOP_WITHHELD'
        oids[name]=git('hash-object','--stdin',input=raw).decode().strip()
        assert oids[name]==git('-c','core.autocrlf=false','hash-object','--path='+name,'--stdin',input=raw).decode().strip()
    visual=json.loads((BASE/'screenshot-review.json').read_text(encoding='utf-8'))
    assert set(visual['reviewed_sha256'])=={sha(ROOT/name) for name in screens} and not visual['private_records_seen']
    for path in BASE.rglob('browser-results.json'):
        for capture in json.loads(path.read_text(encoding='utf-8'))['captures']:
            name=(path.parent/capture['file']).relative_to(ROOT).as_posix()
            assert all(screens[name][k]==capture['viewport'][k] for k in ['width','height'])
    git('diff','--cached','--check');assert git('rev-parse','HEAD').decode().strip()==HEAD and sha(ROOT/'.git/index')==baseline['.git/index']
    return dict(milestone='U5G',status='CAPTURE_FOUNDATION_IMPLEMENTED_OPTIMIZER_CONSUMPTION_BLOCKED',head=HEAD,
        exact_checkpoint_inventory=inventory,modified_existing_files=[],new_paths=inventory,baseline_paths=3619,unchanged_baseline_paths=3619,protected_academic_paths=23,
        preexisting_tracked_modifications=entry['preexisting_tracked_modifications'],prior_u5f_artifact_hashes_verified=79,
        artifact_sha256=hashes,proposed_git_blob_oids=oids,attempts=attempts,screenshots=screens,
        unique_python_cases_passed=217,frontend_contracts_passed=210,browser_scenarios_passed=16,
        privacy='PASS patterns, partial encoded fragments, private-name comparison, PNG metadata/CRC and visual review',whitespace='PASS',
        protected_preferences_settings='BYTE_IDENTICAL_UNSTAGED_EXCLUDED',ga_scoring_rng_fingerprints_migrations_checkpoints_saved_best_history='UNCHANGED',
        git_index_head='UNCHANGED',staged_files=[],consumption_verified=False,continuous_executable=False,
        limitations=['No installed V1 consumer, atomic source loader, exclusive run pin registry or bundle checkpoint version.',
            'Capture/materialization isolation and scoring-copy parity do not prove optimizer consumption.',
            'UNVERIFIED only; no CURRENT, institutional authority or continuous activation.',
            'No PostgreSQL acceptance or live browser-to-GA journey; browser HTTP is fictional.'])

if __name__=='__main__':
    result=inspect('--record' in sys.argv)
    if '--record' in sys.argv:write_new(BASE/'manifest.json',dict(result,recorded_at=datetime.now().astimezone().isoformat()))
    else:assert {k:v for k,v in json.loads((BASE/'manifest.json').read_text(encoding='utf-8')).items() if k!='recorded_at'}==result
    print(json.dumps(dict(status='AUDIT_PASSED',inventory=len(result['exact_checkpoint_inventory']),artifact_hashes=len(result['artifact_sha256']),baseline_preserved=3619,optimizer_consumption_verified=False)))
