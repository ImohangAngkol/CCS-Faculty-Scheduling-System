"""Read-only U5N preservation/hash/privacy replay; --record seals new evidence.

No application imports, database connections, cleanup or actual Git staging.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import zlib

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
HEAD='ed35d620111490d3021567ba7dcc6b26ec93d212'
SOURCE=['backend/services/ga_recovery_qualification.py','backend/services/ga_recovery_vault.py']
TESTS=['backend/tests/test_recovery_qualification.py','backend/tests/test_parent_containment_qualification.py','backend/tests/test_preference_scope_qualification.py']
REPORT='docs/dashboard-u5n-institutional-authority-deployment-recovery.md'
REQUIRED={'recovery':40,'parent':7,'preference-scope':3,'race':19,'identity':16,'receipts':36,
    'supervised':41,'native':12,'worker':32,'consumption':39,'bundle-tests':32,'admission':50,
    'qualification':49,'backend-regressions':99,'parity':5,'legacy':10,'analysis':20,'readiness':20,
    'chair':34,'chair-trust':6,'application-trust':5}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),*args],cwd=ROOT,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)
def new(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,indent=2)+'\n')
def counts(row):
    out=row.get('stdout','')
    node={k:int(v) for k,v in re.findall(r'(?m)^\S+ (tests|pass|fail|skipped|cancelled) (\d+)\s*$',out)}
    return node or {k:int(v) for v,k in re.findall(r'(\d+) (passed|failed|skipped|warnings?|errors?)',out.split('short test summary info')[-1])}
def png(p):
    raw=p.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n';pos=8;chunks=[]
    while pos<len(raw):
        n=struct.unpack('>I',raw[pos:pos+4])[0];kind=raw[pos+4:pos+8];data=raw[pos+8:pos+8+n]
        assert zlib.crc32(kind+data)&0xffffffff==struct.unpack('>I',raw[pos+8+n:pos+12+n])[0]
        assert kind not in [b'tEXt',b'iTXt',b'zTXt',b'eXIf'];chunks.append(kind.decode());pos+=n+12
    assert pos==len(raw) and chunks[-1]=='IEND';return chunks

def inspect(record=False):
    assert git('rev-parse','HEAD').decode().strip()==git('rev-parse','origin/main').decode().strip()==HEAD,'HEAD_OR_LAST_FETCHED_REF_CHANGED_STOP'
    assert git('branch','--show-current').strip()==b'main' and not git('diff','--cached','--name-only').strip()
    baseline=json.loads((BASE/'preservation-baseline.json').read_text());assert len(baseline)==4271
    for path,value in baseline.items():assert sha(ROOT/path)==value,'BASELINE_CHANGED_STOP: '+path
    prior={}
    for name in ['u5g','u5h','u5i','u5j','u5k','u5l','u5m']:
        old=json.loads((BASE.parent/('dashboard-'+name)/'manifest.json').read_text())
        for path,value in old['artifact_sha256'].items():assert sha(ROOT/path)==value,'PRIOR_ARTIFACT_CHANGED_STOP: '+path
        prior[name]=len(old['artifact_sha256'])
    entry=json.loads((BASE/'entry-review.json').read_text());assert len(entry['tracked_modifications'])==11 and len(entry['untracked_files'])==958
    assert sorted(git('diff','--name-only').decode().splitlines())==sorted(entry['tracked_modifications'])
    candidates=sorted(SOURCE+TESTS+[REPORT]+[p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file() and p.name not in {'manifest.json','staging-plan.json'}])
    inventory=sorted(candidates+['docs/testing/dashboard-u5n/manifest.json','docs/testing/dashboard-u5n/staging-plan.json'])
    visible=set(git('ls-files','--cached','--others','--exclude-standard','-z').decode().split('\0'))-{''}
    assert not visible-set(baseline)-set(inventory),'UNAPPROVED_NEW_PATH_STOP'
    assert set(entry['untracked_files'])<=visible
    assert not set(inventory)&set(git('ls-files','-z').decode().split('\0')),'EXISTING_PATH_IN_NEW_CHECKPOINT_STOP'
    assert sum(p.startswith('backend/data/') for p in baseline)==23
    for folder in ['backend/data','backend/saved_chromosomes','backend/run_checkpoints','backend/generation_snapshots','backend/stopped_runs','backend/run_input_receipts_v1','backend/run_provenance_v1','backend/constrained_runs_v2']:
        assert not {p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file()}-set(baseline),'NEW_RUNTIME_FILE_STOP'
    attempts=[]
    for path in sorted(BASE.rglob('*command.json')):
        row=json.loads(path.read_text());attempts.append(dict(path=path.relative_to(ROOT).as_posix(),selection=row['selection'],exit_code=row['exit_code'],counts=counts(row)))
    latest={k:[a for a in attempts if a['selection']==k][-1] for k in REQUIRED}
    for role,total in REQUIRED.items():
        r=latest[role];assert r['exit_code']==0 and r['counts'].get('passed')==total,'FINAL_TEST_STATUS_STOP: '+role
        proof=json.loads((ROOT/r['path']).with_name('snapshot-proof.json').read_text());assert proof['head']==HEAD and proof['complete'] and proof['no_actual_staging']
        tested=SOURCE+[TESTS[0]] if role=='recovery' else ([TESTS[1]] if role=='parent' else ([TESTS[2]] if role=='preference-scope' else []))
        for p in tested:assert proof['source_sha256'][p]==sha(ROOT/p),'UNTESTED_SOURCE_STOP: '+p
    failures=[r for r in attempts if r['exit_code']!=0];assert len(failures)==8
    for role,total in [('frontend',210),('browser',17)]:
        r=[a for a in attempts if a['selection']==role][-1];assert r['exit_code']==0 and r['counts']['pass']==total
    for role in ['build','bundle','lint']:assert [a for a in attempts if a['selection']==role][-1]['exit_code']==0
    patterns=[r'eyJ[A-Za-z0-9_-]{18,}',r'[A-Za-z0-9_-]{80,}\.[A-Za-z0-9_-]{8,}',
        r'(?i)postgres(?:ql)?(?:\+\w+)?://[^\s"\']+',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        r'(?i)bearer\s+[A-Za-z0-9._~-]{20,}',r'''(?i)['"]?(?:X-CSRF-Token|ccs_session|csrf_token|password)['"]?\s*[:=]\s*['"][A-Za-z0-9_-]{24,}''']
    images={}
    for name in candidates:
        p=ROOT/name
        if p.suffix=='.png':images[name]=png(p);continue
        text=p.read_text(encoding='utf-8');assert not any(re.search(pattern,text) for pattern in patterns),'PRIVACY_STOP: '+name
        assert not any(line.rstrip()!=line for line in text.splitlines()),'WHITESPACE_STOP: '+name
        if p.suffix=='.py':compile(text,name,'exec')
    redaction=json.loads((BASE/'privacy-redaction.json').read_text());assert len(redaction['changes'])==1
    for row in redaction['changes']:
        assert sha(ROOT/row['path'])==row['sanitized_sha256']
        assert row['original_sha256']!=row['sanitized_sha256']
        old=json.loads((ROOT/row['path']).read_text());assert old['exit_code']==1 and '[REDACTED_SESSION_TOKEN]' in old['stdout']
    review=json.loads((BASE/'screenshot-review.json').read_text());assert len(images)==6 and review['privacy_reviewed']
    for path,value in review['files'].items():assert sha(ROOT/path)==value
    git('diff','--check');git('diff','--cached','--check');fsck=git('fsck','--no-reflogs').decode();assert all(s.startswith('dangling ') for s in fsck.splitlines())
    parent_path=(ROOT/latest['parent']['path']).parent
    for name in ['parent-tree','parent-memory','parent-cpu','parent-checkpoint-recovery','redirector-process-slots','parent-import-boundary']:assert (parent_path/('U5N-'+name+'.json')).is_file()
    actual_recovery=json.loads((parent_path/'U5N-parent-checkpoint-recovery.json').read_text());assert actual_recovery['stale_owner_fenced'] and not actual_recovery['backup_restore']
    blobs={}
    for p in candidates:
        raw=(ROOT/p).read_bytes();blobs[p]=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    plan=dict(baseline_head=HEAD,prerequisite_order=['U5G','U5H','U5I','U5J','U5K','U5L','U5M','U5N'],
        implementation_test_paths=SOURCE+TESTS,documentation_tooling_evidence_paths=sorted(set(inventory)-set(SOURCE+TESTS)),
        exact_checkpoint_inventory=inventory,existing_files_modified=[],mixed_files_to_stage=[],
        excluded_preexisting_tracked_modifications=entry['tracked_modifications'],excluded_preexisting_untracked_files=958,
        proposed_blob_oids=blobs,core_autocrlf=False,literal_pathspecs=True,cr_at_eol_whitespace=True,
        commit_messages=['feat(ga): qualify isolated recovery authority and checkpoint quarantine (U5N)','docs(testing): archive U5N containment and readiness evidence'],
        instructions='PROPOSAL ONLY. Obtain separate checkpoint authorization; reverify live remote, HEAD, index, hashes and isolated snapshot. Stage only exact listed paths using literal NUL-delimited pathspecs with core.autocrlf=false. No partial staging needed: all U5N files are new. Exclude all eleven unrelated tracked modifications and 958 prior untracked files. Verify raw blobs; plan/manifest blob identities must be calculated after sealing rather than self-referentially embedded. Do not activate worker recovery, institutional authority or continuous execution.')
    manifest=dict(milestone='U5N',head=HEAD,reviewed_at=datetime.now().astimezone().isoformat(),
        status='ISOLATED_AUTHORITY_STORAGE_AND_QUARANTINE_QUALIFIED; NATIVE_PARENT_PROBES_PASS; PRODUCTION_BLOCKED',
        exact_changed_and_new_file_inventory=inventory,new_files=len(inventory),existing_files_modified=[],
        preservation=dict(baseline_paths=4271,unchanged=4271,academic_data_files=23,protected_json_unchanged=True,
            index_unchanged=True,unrelated_tracked_modifications=11,unrelated_untracked_files=958,prior_artifact_hash_references=prior,
            original_ga_migrations_checkpoints_saved_best_and_evidence_unchanged=True,no_postgresql_operations=True),
        final_python_counts=REQUIRED,final_selected_python_cases=sum(REQUIRED.values()),frontend_contracts=210,browser_scenarios=16,browser_runner_count=17,
        attempts=attempts,failed_attempts_retained=len(failures),nonzero_original_and_worker_fitness=455.0,
        institutional_authority='UNQUALIFIED',production_admission='BLOCKED',continuous_execution_ui='DISABLED',
        restore='WRITABLE_VALIDATED_QUARANTINE_ONLY; EXISTING_WORKER_ACTIVATION_BLOCKED',
        parent='ISOLATED_NATIVE_TOPOLOGY_VERIFIED; NO_DEPLOYED_PARENT_SERVICE_OR_AGGREGATE_HOST_QUOTA',
        prototype='FICTIONAL_COMPONENT_AND_FIXED_UI_DEMONSTRATION; CONTINUOUS_HTTP_UI_INTEGRATION_MISSING',
        privacy='PASS after explicit full-value redaction of fictional CSRF exposure in one new failed test record; original/sanitized hashes and failure outcome retained. No pre-existing evidence rewritten. Six PNGs visually reviewed, CRC and metadata checked; no raw checkpoint/package/database archived.',
        whitespace='PASS',git_integrity=dict(exit_code=0,dangling_objects=len(fsck.splitlines())),png_integrity=images,
        checkpoint_readiness='READY_FOR_SELECTIVE_REVIEW_WITH_EXPLICIT_PARTIAL_RESTORE_AND_DEPLOYMENT_BLOCKERS',
        artifact_sha256={p:sha(ROOT/p) for p in candidates})
    if record:
        new(BASE/'staging-plan.json',plan);manifest['artifact_sha256']['docs/testing/dashboard-u5n/staging-plan.json']=sha(BASE/'staging-plan.json');new(BASE/'manifest.json',manifest)
    else:
        old=json.loads((BASE/'manifest.json').read_text());assert old['exact_changed_and_new_file_inventory']==inventory
        for path,value in old['artifact_sha256'].items():assert sha(ROOT/path)==value,'ARTIFACT_CHANGED_STOP: '+path
    print(json.dumps(dict(status='PASS',baseline_preserved=4271,new_files=len(inventory),existing_files_modified=0,artifact_hashes=len(inventory)-1,
        python_passes=sum(REQUIRED.values()),failed_attempts_preserved=len(failures),production_admission='BLOCKED',continuous_ui='DISABLED')))

if __name__=='__main__':inspect('--record' in sys.argv)
