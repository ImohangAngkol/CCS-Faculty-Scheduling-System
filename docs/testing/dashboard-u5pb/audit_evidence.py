"""Read-only preservation/privacy/hash replay; --record creates NEW seals only."""
from datetime import datetime
import collections
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
HEAD='9c3f5c67c534f81a7b26bd6cb8535e5340ce5bf9'
REPORT='docs/dashboard-u5pb-trusted-context-research-bridge.md'
CODE=['backend/services/ga_research_context.py','backend/services/ga_research_ledger.py',
 'backend/services/ga_research_bridge.py','backend/routers/ga_research.py','backend/tests/test_research_bridge.py']
REQUIRED={'unit':30,'native':10,'http':11,'saved-best':48,'parity':5,'legacy':10,'consumption':39,
 'race':19,'worker':32,'recovery':40,'authority':49,'regressions':99,'storage-full':1}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),*args],cwd=ROOT,
    env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)
def new(path,obj):
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(obj,f,indent=2);f.write('\n')
def counts(row):
    out=row['stdout'];d={}
    for k,v in re.findall(r'(\d+) (passed|failed|errors?|skipped|deselected)',out):d[v]=int(k)
    for k,v in re.findall(r'\u2139 (tests|pass|fail|skipped) (\d+)',out):d[k]=int(v)
    return d


def inspect(record=False):
    assert git('rev-parse','HEAD').decode().strip()==HEAD and git('branch','--show-current').strip()==b'main'
    assert not git('diff','--cached','--name-only').strip()
    baseline=json.loads((BASE/'preservation-baseline.json').read_text());assert len(baseline)==4930
    mismatches=[p for p,h in baseline.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    assert not mismatches,'PRESERVATION_STOP: '+str(mismatches)
    entry=json.loads((BASE/'entry-review.json').read_text())
    assert len(entry['tracked_modifications'])==11 and len(entry['untracked_files'])==958
    assert sorted(git('diff','--name-only').decode().splitlines())==sorted(entry['tracked_modifications'])
    assert len(entry['academic_paths'])==23
    for prefix in ['backend/data/','backend/saved_chromosomes/','backend/run_checkpoints/','backend/generation_snapshots/',
                   'backend/run_input_receipts_v1/','backend/run_provenance_v1/','backend/constrained_runs_v2/']:
        actual={p.relative_to(ROOT).as_posix() for p in (ROOT/prefix).rglob('*') if p.is_file()}
        assert actual=={p for p in baseline if p.startswith(prefix)},'PROTECTED_MEMBERSHIP_STOP: '+prefix
    references=0
    for key,total in entry['prior_artifacts'].items():
        old=json.loads((BASE.parent/('dashboard-'+key)/'manifest.json').read_text());assert len(old['artifact_sha256'])==total
        for p,h in old['artifact_sha256'].items():assert sha(ROOT/p)==h,'PRIOR_ARTIFACT_STOP: '+p
        references+=total
    assert references==1303
    inventory=sorted(CODE+[REPORT]+[p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file()
        and p.name not in {'manifest.json','staging-plan.json'}]+['docs/testing/dashboard-u5pb/manifest.json','docs/testing/dashboard-u5pb/staging-plan.json'])
    assert len(inventory)==len(set(inventory))
    untracked=set(git('ls-files','--others','--exclude-standard','-z').decode().strip('\0').split('\0'))
    expected=set(inventory)-{'docs/testing/dashboard-u5pb/manifest.json','docs/testing/dashboard-u5pb/staging-plan.json'}
    if not record:expected=set(inventory)
    assert untracked==set(entry['untracked_files'])|expected,'UNAPPROVED_PATH_STOP'
    rows=[]
    for p in sorted(BASE.glob('*/command.json')):
        d=json.loads(p.read_text());rows.append(dict(path=p.relative_to(ROOT).as_posix(),selection=d['selection'],
            exit_code=d['exit_code'],counts=counts(d),source_sha256=d.get('source_sha256'),elapsed_seconds=d['elapsed_seconds']))
    latest={key:[r for r in rows if r['selection']==key][-1] for key in REQUIRED}
    for key,total in REQUIRED.items():
        row=latest[key];assert row['exit_code']==0 and row['counts'].get('passed')==total,'FINAL_TEST_STOP: '+key
        for p,h in row['source_sha256'].items():assert sha(ROOT/p)==h,'FINAL_SOURCE_STOP: '+key+' '+p
    for key in ['contracts-all','build','bundle','lint','demo']:
        row=[r for r in rows if r['selection']==key][-1];assert row['exit_code']==0,'FINAL_SELECTION_STOP: '+key
    front=[r for r in rows if r['selection']=='contracts-all'][-1];assert front['counts']['pass']==342
    native=(ROOT/latest['native']['path']).parent
    parity=json.loads((native/'U5K-nonzero-worker-parity.json').read_text())
    assert parity['original_fitness']==parity['worker_fitness']==455.0 and parity['global_rng_unchanged']
    assert parity['schedule_fitness_history_breakdown_faculty_and_rng_equal']
    real=json.loads((native/'native-real-worker.json').read_text())
    assert real['durable_restart_equal'] and real['research_best_tie_bytes_preserved'] and real['RNG_unchanged']
    assert real['best_values']==sorted(real['best_values'],reverse=True)
    assert all(p['active_processes']==0 and p['creation_time_job_binding'] and p['peak_private_commit_bytes']<=p['enforced']['private_commit_bytes'] for p in real['physical_observations'])
    interrupt=json.loads((native/'native-parent-interruption.json').read_text());assert interrupt['parent_exit']==23 and interrupt['post_restart_state']=='INTERRUPTED' and not interrupt['active_restore']
    http=(ROOT/latest['http']['path']).parent;http_proof=json.loads((http/'real-http-worker-restart.json').read_text())
    assert http_proof['actual_TCP_HTTP'] and http_proof['actual_FastAPI_auth_CSRF'] and http_proof['actual_Windows_worker'] and http_proof['telemetry_equal_after_API_reconstruction']
    legacy=(ROOT/latest['legacy']['path']).parent;fixtures=[json.loads((legacy/f'fixture-{i}.json').read_text()) for i in range(3)]
    assert all(f['real_checkpoint_write_load_resume'] and f['RNG_and_schedule_equivalent'] for f in fixtures)
    old_engine=json.loads((BASE.parent/'dashboard-u5pa/manifest.json').read_text())['checkpoint']['current_fixture_engine']
    assert {f['engine_fingerprint'] for f in fixtures}=={old_engine},'ORIGINAL_ENGINE_IDENTITY_STOP'
    # All text/code/evidence inspected locally; actual names never exported.
    with (ROOT/'backend/data/Faculty.csv').open(encoding='utf-8-sig',newline='') as f:
        names=[r['Faculty'].strip().casefold() for r in csv.DictReader(f) if len(r.get('Faculty','').strip())>=6]
    patterns=[r'eyJ[A-Za-z0-9_-]{18,}',r'[A-Za-z0-9_-]{80,}\.[A-Za-z0-9_-]{8,}',
        r'(?i)postgres(?:ql)?(?:\+\w+)?://[^\s"\']+',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        r'(?i)bearer\s+[A-Za-z0-9._~-]{20,}',r'''(?i)['"]?(?:X-CSRF-Token|ccs_session|csrf_token|password)['"]?\s*[:=]\s*['"][A-Za-z0-9_-]{24,}''']
    for name in expected:
        text=(ROOT/name).read_text(encoding='utf-8')
        assert not any(re.search(pattern,text) for pattern in patterns),'PRIVACY_STOP: '+name
        assert not any(n in text.casefold() for n in names),'PRIVATE_NAME_STOP: '+name
        assert not any(line.rstrip()!=line for line in text.splitlines()),'WHITESPACE_STOP: '+name
        if name.endswith('.py'):compile(text,name,'exec')
    git('diff','--check');git('diff','--cached','--check');integrity=git('fsck','--no-reflogs').decode()
    assert all(line.startswith('dangling ') for line in integrity.splitlines())
    content_files=sorted(set(inventory)-{'docs/testing/dashboard-u5pb/manifest.json','docs/testing/dashboard-u5pb/staging-plan.json'})
    blobs={p:hashlib.sha1(b'blob '+str((ROOT/p).stat().st_size).encode()+b'\0'+(ROOT/p).read_bytes()).hexdigest() for p in content_files}
    plan=dict(head=HEAD,exact_checkpoint_inventory=inventory,existing_modified_files=[],new_files=len(inventory),
        application_tests=CODE,documentation_tooling_evidence=sorted(set(inventory)-set(CODE)),proposed_blob_oids=blobs,
        excluded_tracked_modifications=entry['tracked_modifications'],excluded_untracked_files=entry['untracked_files'],
        core_autocrlf=False,partial_staging_required=False,instructions='PROPOSAL ONLY; no staging. Explicit exact literal paths only. Preserve original eleven tracked modifications and 958 unrelated untracked files. Verify all raw Git blobs and SHA-256. Calculate manifest/plan blob identities after sealing; no self-referential identity claims.',
        proposed_messages=['feat(ga): add isolated trusted fictional research bridge (U5P-B)','docs(testing): archive U5P-B research qualification'])
    manifest=dict(milestone='U5P-B',head=HEAD,recorded_at=datetime.now().astimezone().isoformat(),
        status='ISOLATED_FICTIONAL_CONTEXT_WORKER_HTTP_AND_TELEMETRY_QUALIFIED; PRODUCTION_BLOCKED',
        exact_changed_and_new_file_inventory=inventory,existing_files_modified=[],new_files=len(inventory),
        final_python_counts=REQUIRED,selected_python_passes=sum(REQUIRED.values()),frontend_contracts=342,
        TypeScript='PASS',production_build='PASS',focused_lint='PASS',tests_freshly_executed=True,attempts=rows,
        original_fitness=455.0,original_assignments_history_breakdown_rng_equal=True,
        original_engine_fingerprint=old_engine,current_V1_checkpoint_creation_load_continuation=True,
        real_loopback_HTTP_auth_worker_SQLite=True,API_reconstruction_telemetry_equal=True,real_parent_interruption_exit=23,
        source_changes_in_existing_files=False,
        preservation=dict(baseline_paths=4930,unchanged=4930,academic_files=23,protected_JSON_unchanged=True,index_unchanged=True,
            prior_artifact_references=references,original_unrelated_tracked=11,original_unrelated_untracked=958),
        privacy='PASS; no raw bundle/checkpoint/DB/cookie/key/provider payload or signed receipt archived',
        whitespace='PASS',git_integrity='PASS',screenshots='NOT_CAPTURED; no frontend feature added',browser_acceptance='NOT_RUN; real TCP HTTP and native Windows acceptance instead',
        limitations=['API app/server reconstruction tested in one host process; separate actual supervisor-process crash tested, not institutional service failover',
            'No pause/resume/recovery activation route; expired ownership requires quarantine review',
            'Per-process CPU/private-commit and existing SQLite page limits preserved; host-wide and filesystem/journal quota qualification absent',
            'HMAC protects against accidental corruption/tail loss within private owned stores, not malicious OS owner or rollback of all trusted storage',
            'Background execution revalidates scoped mandate/source; account sessions separately revalidated for every HTTP request',
            'Historic U5O expectation mismatch and U5PA browser failures preserved; no claim of whole-repository green tests'],
        production_admission='BLOCKED',institutional_saved_best_promotion='BLOCKED',continuous_UI='DISABLED',seven_day='NO_GO',active_restore=False,
        checkpoint_readiness='SELECTIVE_REVIEW_READY_FOR_ISOLATED_RESEARCH_SCOPE_ONLY',
        artifact_sha256={p:sha(ROOT/p) for p in content_files})
    if record:
        new(BASE/'staging-plan.json',plan)
        manifest['artifact_sha256']['docs/testing/dashboard-u5pb/staging-plan.json']=sha(BASE/'staging-plan.json')
        new(BASE/'manifest.json',manifest)
    else:
        sealed=json.loads((BASE/'manifest.json').read_text());assert sealed['exact_changed_and_new_file_inventory']==inventory
        for p,h in sealed['artifact_sha256'].items():assert sha(ROOT/p)==h,'SEALED_HASH_STOP: '+p
    print(json.dumps(dict(status='PASS',baseline_unchanged=4930,new_files=len(inventory),artifact_hashes=len(inventory)-1,
        selected_python_passes=sum(REQUIRED.values()),frontend_contracts=342,prior_references=1303,production='BLOCKED')))


if __name__=='__main__':inspect('--record' in sys.argv)
