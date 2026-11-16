"""Complete-entry preservation and evidence seal, never application execution."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import csv
import hashlib
import json
import os
import re
import subprocess
import struct
import sys

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
HEAD='0dcc3e942d0b79c0e6358aa151208c014b307300'
REPORT='docs/dashboard-u5pf-research-experiment-exports.md'
CODE=['backend/services/ga_research_experiments.py', 'backend/routers/research_experiments.py', 'backend/tests/test_research_experiments.py', 'backend/tests/test_research_experiments_live.py', 'frontend/src/researchExperiments/panel.html', 'frontend/src/researchExperiments/console.mjs', 'frontend/src/researchExperiments/model.mjs', 'frontend/tests/researchExperiments.test.mjs', 'frontend/tests/researchExperiments.live.mjs']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def new(p,obj):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(obj,f,indent=2);f.write('\n')
def inspect(record=False):
    entry=read(BASE/'entry.json');baseline=read(BASE/'preservation-baseline.json')
    assert git('rev-parse','HEAD').decode().strip()==HEAD and git('branch','--show-current').strip()==b'main'
    assert not git('diff','--cached','--name-only').strip()
    bad=[n for n,h in baseline.items() if not (ROOT/n).is_file() or sha(ROOT/n)!=h]
    assert not bad,'PRESERVATION_STOP: '+str(bad)
    assert len(baseline)==5594 and len(entry['academic_paths'])==23
    assert set(git('diff','--name-only').decode().splitlines())==set(entry['tracked_modifications'])
    for n,h in entry['historical_eight'].items():assert baseline[n]==sha(ROOT/n)==h
    ignored=read(BASE/'ignored-runtime-inventory.json')
    assert ignored['ignored_file_count']==len(entry['ignored_paths'])
    assert sorted(n for files in ignored['directories'].values() for n in files)==sorted(entry['ignored_paths'])
    assert ignored['ignored_sha256']=={n:baseline[n] for n in entry['ignored_paths']}
    seals=['docs/testing/dashboard-u5pf/manifest.json','docs/testing/dashboard-u5pf/staging-plan.json']
    content=sorted(CODE+[REPORT]+[p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file() and p.name not in {'manifest.json','staging-plan.json'}])
    inventory=sorted(content+seals);assert len(inventory)==len(set(inventory))
    untracked=set(git('ls-files','--others','--exclude-standard','-z').decode().strip('\0').split('\0'))-{''}
    assert untracked==set(entry['untracked_files'])|(set(inventory)-(set(seals) if record else set())),'UNREVIEWED_UNTRACKED_STOP'
    actual=set()
    for parent,dirs,files in os.walk(ROOT,followlinks=False):
        keep=[]
        for d in dirs:
            p=Path(parent)/d;n=p.relative_to(ROOT).as_posix()
            if n in entry['excluded_roots']:continue
            assert not p.is_symlink() and not p.is_junction(),'NEW_LINK_STOP: '+n
            keep.append(d)
        dirs[:]=keep
        actual.update((Path(parent)/n).relative_to(ROOT).as_posix() for n in files)
    expected=(set(baseline)-{n for n in baseline if n.startswith('.git/')})|set(content)|(set(seals) if not record else set())
    assert actual==expected,'FULL_WORKSPACE_MEMBERSHIP_STOP: '+str(sorted(actual^expected))
    prior=entry['prior_artifacts'];refs=0
    for key,total in prior.items():
        m=read(BASE.parent/('dashboard-'+key)/'manifest.json');assert len(m['artifact_sha256'])==total
        for n,h in m['artifact_sha256'].items():
            if sha(ROOT/n)!=h:
                assert key=='u5pc' and n in ['frontend/src/api/researchObservations.ts','frontend/src/pages/ResearchConsole.tsx','frontend/src/routes/AppRoutes.tsx']
                assert hashlib.sha256(git('show','3719af0734e395bf2b905a13ab6ccc1ca7dda5f9:'+n)).hexdigest()==h
        refs+=total
    assert refs==1793
    with (ROOT/'backend/data/Faculty.csv').open(encoding='utf-8-sig',newline='') as f:
        private=[x['Faculty'].strip().casefold() for x in csv.DictReader(f) if len(x.get('Faculty','').strip())>=6]
    patterns=[r'eyJ[A-Za-z0-9_-]{18,}',r'[A-Za-z0-9_-]{80,}\.[A-Za-z0-9_-]{8,}',r'(?i)postgres(?:ql)?(?:\+\w+)?://[^\s"\']+',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'(?i)bearer\s+[A-Za-z0-9._~-]{20,}',r'''(?i)['"]?(?:X-CSRF-Token|ccs_session|csrf_token|password)['"]?\s*[:=]\s*['"][A-Za-z0-9_-]{24,}''']
    images={}
    for n in content:
        p=ROOT/n
        if p.suffix=='.png':
            raw=p.read_bytes();assert raw.startswith(b'\x89PNG\r\n\x1a\n');offset=8;chunks=[]
            while offset<len(raw):
                size=struct.unpack('>I',raw[offset:offset+4])[0];kind=raw[offset+4:offset+8];chunks.append(kind)
                assert kind in {b'IHDR',b'IDAT',b'IEND',b'sRGB',b'gAMA',b'cHRM',b'pHYs'},'PNG_METADATA_STOP: '+n
                offset+=size+12
            assert offset==len(raw) and chunks[-1]==b'IEND'
            images[n]=sha(p);continue
        text=p.read_text(encoding='utf-8');assert not any(re.search(x,text) for x in patterns),'PRIVACY_STOP: '+n
        assert not any(x in text.casefold() for x in private),'PRIVATE_NAME_STOP: '+n
        assert all(x.rstrip()==x for x in text.splitlines()),'WHITESPACE_STOP: '+n
        if p.suffix=='.py':compile(text,n,'exec')
    if images:
        reviewed={}
        for review in BASE.glob('screenshot-review*.json'):
            for n,h in read(review)['files'].items():
                assert n not in reviewed or reviewed[n]==h
                reviewed[n]=h
        assert reviewed==images
    git('diff','--cached','--check');fsck=git('fsck','--no-reflogs').decode();assert all(x.startswith('dangling ') for x in fsck.splitlines())
    attempts=[]
    for p in sorted(BASE.glob('*/command.json')):
        d=read(p);counts={k:int(n) for n,k in re.findall(r'(\d+) (passed|failed|errors?|skipped)',d.get('stdout',''))}
        counts.update({k:int(n) for k,n in re.findall(r'\u2139 (tests|pass|fail|skipped) (\d+)',d.get('stdout',''))})
        attempts.append(dict(path=p.relative_to(ROOT).as_posix(),selection=d.get('selection',p.parent.name.split('-')[-1]),exit_code=d['exit_code'],counts=counts,elapsed_seconds=d['elapsed_seconds']))
    # Current source qualification is explicit; failed/old snapshots remain in
    # attempts and are never counted as current acceptance.
    summary=read(BASE/'qualification-summary.json')
    assert set(summary['reviewed_source_sha256'])==set(CODE)
    for n,h in summary['reviewed_source_sha256'].items():assert sha(ROOT/n)==h,'REVIEWED_SOURCE_CHANGED: '+n
    complete=summary['status']=='PASS_SHORT_FICTIONAL_WORKFLOW'
    assert complete or summary['status']=='PARTIAL_RESOURCE_BLOCKED'
    assert summary['checkpoint_ready']==complete
    if not complete:assert summary['remaining_unverified'] and 'live' not in summary['backend']
    total=0
    for selection,item in summary['backend'].items():
        row=read(ROOT/item['path'])
        assert row['selection']==selection and row['exit_code']==0
        assert re.search(r'\b'+str(item['passed'])+r' passed\b',row['stdout'])
        assert not re.search(r'\b[1-9]\d* (?:failed|errors?)\b',row['stdout'])
        if selection in {'experiments','native-export','offline','live'}:
            for n,h in row['source_sha256'].items():
                # The operator unit suite does not execute the live-only host/
                # browser diagnostics. Those bytes are qualified by live below.
                if selection in {'experiments','native-export','offline'} and n not in CODE[:3]+['docs/testing/dashboard-u5pf/verify_export.py']:continue
                assert sha(ROOT/n)==h,'FINAL_BACKEND_SOURCE_CHANGED: '+n
        total+=item['passed']
    assert total==summary['backend_total_passed']
    for selection,item in summary['frontend'].items():
        row=read(ROOT/item['path']);assert row['selection']==selection and row['exit_code']==0
        for n,h in row['ui_overlay_sha256'].items():
            # Live scripts are excluded from node contracts and TS/Vite builds;
            # only focused lint and actual live execution qualify their changes.
            if selection!='lint' and n.endswith('.live.mjs'):continue
            assert sha(ROOT/n)==h,'FINAL_FRONTEND_SOURCE_CHANGED: '+n
        if selection=='contracts-all':assert '\u2139 pass '+str(item['passed'])+'\n' in row['stdout'] and '\u2139 fail 0\n' in row['stdout']
    if complete:
        assert 'experiments' in summary['backend'] and 'live' in summary['backend']
        live=Path(summary['backend']['live']['path']).parent
        browser=read(ROOT/live/'browser-results.json')
        assert len(browser['scenarios'])==11 and all(x['status']=='PASS' for x in browser['scenarios']) and browser['errors']==[]
        assert browser['injected_error_scenarios']==['F07'] and browser['mocked_success_responses']==0
        process=read(ROOT/live/'live-acceptance.json');assert process['runs']==2 and process['all_process_exits_verified'] and process['export_record_hash_verified']
        cleanup=read(ROOT/live/'browser-cleanup.json');assert cleanup['root_process_exit_verified']
        recovery=read(ROOT/live/'real-API-reconstruction.json');assert recovery['request_replayed_without_new_worker'] and recovery['active_restore'] is False
        recovered=read(ROOT/live/'experiment-API-reconstruction.json');assert recovered['actual_TCP_restart'] and recovered['stable_experiment_identity'] and recovered['stable_record_hash'] and recovered['no_worker_relaunch'] and recovered['active_restore'] is False
    if summary.get('handoff_probe'):
        probe=read(ROOT/summary['handoff_probe']);assert probe['exit_code']==0 and '"private_login_removed": true' in probe['stdout']
    plan=dict(head=HEAD,exact_checkpoint_inventory=inventory,new_files=len(inventory),existing_modified_files=[],
        proposed_blob_oids={n:hashlib.sha1(b'blob '+str((ROOT/n).stat().st_size).encode()+b'\0'+(ROOT/n).read_bytes()).hexdigest() for n in content},
        excluded_tracked_modifications=entry['tracked_modifications'],excluded_untracked_files=entry['untracked_files'],
        core_autocrlf=False,staging_authorized=False,partial_staging_required=False,checkpoint_ready=complete,
        remaining_blockers=summary['remaining_unverified'],
        instructions='PROPOSAL ONLY. All U5PF files are new; exact literal paths only after separate owner authorization. No blanket directory staging. Preserve prior failures, all original unrelated files and every ignored runtime artifact.',
        recommended_message='feat(ga): add fictional experiment evidence exports (U5P-F)')
    manifest=dict(milestone='U5P-F',head=HEAD,recorded_at=datetime.now(ZoneInfo('Asia/Manila')).isoformat(),exact_changed_and_new_file_inventory=inventory,
        existing_files_modified=[],new_files=len(inventory),qualification=summary,attempts=attempts,
        preservation=dict(entry_paths=len(baseline),unchanged=len(baseline),ignored_entry_files=len(entry['ignored_paths']),academic_files=23,
            original_tracked=len(entry['tracked_modifications']),original_untracked=len(entry['untracked_files']),historical_eight_captured_before_tests_and_unchanged=True,
            previous_U5PD_historical_uncertainty_not_retroactively_resolved=True,previous_exception_not_applied=True,complete_workspace_membership_verified=True,
            dependency_exclusions=entry['excluded_roots'],Git_index_HEAD_config_unchanged=True,prior_artifact_references=refs),
        privacy='PASS',whitespace='PASS',git_integrity='PASS',screenshot_sha256=images,artifact_sha256={n:sha(ROOT/n) for n in content},
        evidence_bytes_excluding_seals=sum((ROOT/n).stat().st_size for n in content),production_admission='BLOCKED',institutional_saved_best_promotion='BLOCKED',continuous_optimization='DISABLED',active_restore='BLOCKED',seven_day='NO_GO')
    if record:
        new(BASE/'staging-plan.json',plan);manifest['artifact_sha256'][seals[1]]=sha(BASE/'staging-plan.json');new(BASE/'manifest.json',manifest)
    else:
        m=read(BASE/'manifest.json');assert m['exact_changed_and_new_file_inventory']==inventory
        for n,h in m['artifact_sha256'].items():assert sha(ROOT/n)==h,'SEALED_HASH_STOP: '+n
        assert read(BASE/'staging-plan.json')['proposed_blob_oids']==plan['proposed_blob_oids']
    assert git('rev-parse','HEAD').decode().strip()==HEAD and sha(ROOT/'.git/index')==baseline['.git/index']
    print(json.dumps(dict(preservation='PASS',entry_paths=len(baseline),inventory=len(inventory),artifact_hashes=len(inventory)-1,prior_references=refs,
        privacy='PASS',Git_index_unchanged=True,qualification=summary['status'],production='BLOCKED')))

if __name__=='__main__':inspect('--record' in sys.argv)
