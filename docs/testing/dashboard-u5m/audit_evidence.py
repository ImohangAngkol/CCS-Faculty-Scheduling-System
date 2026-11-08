"""Read-only U5M replay; --record creates new manifest/plan, never stages.

No application imports, database access, restoration or historical rewriting.
"""
from datetime import datetime
import ast
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
HEAD='b4c8da7942bddfec63564a1e1f8de31e1db3e491'
SOURCE='backend/services/ga_input_receipt.py'
TESTS=['backend/tests/test_receipt_concurrency_qualification.py','backend/tests/test_deployment_identity_qualification.py']
REPORT='docs/dashboard-u5m-reliability-deployment-qualification.md'
REQUIRED={'race':19,'identity':16,'receipts':36,'supervised':41,'native':12,'worker':32,
    'consumption':39,'bundle-tests':32,'admission':50,'qualification':49,'backend-regressions':99,
    'parity':5,'legacy':10,'analysis':20,'readiness':20,'chair':34,'chair-trust':6,'application-trust':5}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args,input=None):
    return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),*args],cwd=ROOT,input=input,
        env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)
def new(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,indent=2)+'\n')
def counts(row):
    out=row.get('stdout','')
    node={k:int(v) for k,v in re.findall(r'(?m)^\S+ (tests|pass|fail|skipped|cancelled) (\d+)\s*$',out)}
    return node or {k:int(v) for v,k in re.findall(r'(\d+) (passed|failed|skipped|warnings?|errors?)',out.split('short test summary info')[-1])}
def png(path):
    raw=path.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n';pos=8;chunks=[]
    while pos<len(raw):
        length=struct.unpack('>I',raw[pos:pos+4])[0];kind=raw[pos+4:pos+8];data=raw[pos+8:pos+8+length]
        assert zlib.crc32(kind+data)&0xffffffff==struct.unpack('>I',raw[pos+8+length:pos+12+length])[0]
        assert kind not in [b'tEXt',b'iTXt',b'zTXt',b'eXIf']
        chunks.append(kind.decode());pos+=length+12
    assert pos==len(raw) and chunks[-1]=='IEND'
    return chunks

def inspect(record=False):
    assert git('rev-parse','HEAD').decode().strip()==HEAD,'HEAD_CHANGED_STOP'
    assert git('rev-parse','origin/main').decode().strip()==HEAD,'LAST_FETCHED_REF_CHANGED_STOP'
    assert git('branch','--show-current').decode().strip()=='main'
    assert not git('diff','--cached','--name-only').strip(),'STAGED_CONTENT_STOP'
    baseline=json.loads((BASE/'preservation-baseline.json').read_text());assert len(baseline)==4139
    for path,value in baseline.items():
        if path!=SOURCE:assert sha(ROOT/path)==value,'PRESERVATION_STOP: '+path
    scope=json.loads((BASE/'repair-scope-review.json').read_text())
    assert sha(ROOT/SOURCE)==scope['current_source_sha256'] and baseline[SOURCE]==scope['baseline_source_sha256']
    before=ast.parse(git('show',HEAD+':'+SOURCE).decode());after=ast.parse((ROOT/SOURCE).read_text())
    nodekey=lambda n:(type(n).__name__,getattr(n,'name',getattr(n,'lineno',None)))
    # Compare all non-function nodes in order too; changing line positions is irrelevant.
    assert len(before.body)==len(after.body)
    changed=[a.name for a,b in zip(before.body,after.body) if ast.dump(a)!=ast.dump(b) and isinstance(a,ast.FunctionDef)]
    assert changed==['directory','write']
    assert all(ast.dump(a)==ast.dump(b) for a,b in zip(before.body,after.body) if not isinstance(a,ast.FunctionDef))
    assert len(scope['original_engine_fingerprint_source_inputs_unchanged'])==33
    for path,value in scope['original_engine_fingerprint_source_inputs_unchanged'].items():assert sha(ROOT/path)==value==baseline[path]
    prior={}
    for key in ['u5g','u5h','u5i','u5j','u5k','u5l']:
        old=json.loads((BASE.parent/('dashboard-'+key)/'manifest.json').read_text())
        for path,value in old['artifact_sha256'].items():assert sha(ROOT/path)==value,'PREREQUISITE_HASH_STOP: '+path
        prior[key]=len(old['artifact_sha256'])
    entry=json.loads((BASE/'entry-review.json').read_text());assert len(entry['tracked_modifications'])==11 and len(entry['untracked_files'])==958
    assert set(git('diff','--name-only').decode().splitlines())==set(entry['tracked_modifications']+[SOURCE])
    candidates=sorted([SOURCE,*TESTS,REPORT]+[p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file() and p.name not in {'manifest.json','staging-plan.json'}])
    inventory=sorted(candidates+['docs/testing/dashboard-u5m/manifest.json','docs/testing/dashboard-u5m/staging-plan.json'])
    visible=set(git('ls-files','--cached','--others','--exclude-standard','-z').decode().split('\0'))-{''}
    assert not visible-set(baseline)-set(inventory),'UNAPPROVED_NEW_PATH_STOP'
    assert set(entry['untracked_files'])<=visible
    for folder in ['backend/data','backend/run_checkpoints','backend/saved_chromosomes','backend/run_input_receipts_v1','backend/run_provenance_v1','backend/constrained_runs_v2','backend/generation_snapshots','backend/stopped_runs']:
        assert not {p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file()}-set(baseline),'NEW_RUNTIME_FILE_STOP: '+folder
    assert sum(p.startswith('backend/data/') for p in baseline)==23
    attempts=[]
    for p in sorted(BASE.rglob('*command.json')):
        row=json.loads(p.read_text());attempts.append(dict(path=p.relative_to(ROOT).as_posix(),selection=row['selection'],exit_code=row['exit_code'],counts=counts(row)))
    latest={role:[r for r in attempts if r['selection']==role][-1] for role in REQUIRED}
    for role,total in REQUIRED.items():
        attempt=latest[role];assert attempt['exit_code']==0 and attempt['counts']['passed']==total,'TEST_STATUS_STOP: '+role
        proof=json.loads((ROOT/attempt['path']).with_name('snapshot-proof.json').read_text())
        assert proof['complete'] and proof['no_actual_staging'] and proof['head']==HEAD
        assert proof['source_sha256'][SOURCE]==sha(ROOT/SOURCE),'UNTESTED_REPAIR_STOP'
        if role in ['race','identity']:
            path=TESTS[0 if role=='race' else 1];assert proof['source_sha256'][path]==sha(ROOT/path),'UNTESTED_CASES_STOP'
    for role,total in [('frontend',210),('browser',17)]:
        attempt=[r for r in attempts if r['selection']==role][-1];assert attempt['exit_code']==0 and attempt['counts']['pass']==total
    for role in ['build','bundle','lint']:assert [r for r in attempts if r['selection']==role][-1]['exit_code']==0
    assert sum(r['exit_code']!=0 for r in attempts)==3,'FAILED_DIAGNOSTIC_INVENTORY_CHANGED'
    final_trace=json.loads((ROOT/latest['race']['path']).with_name('U5M-receipt-guard-trace.json').read_text())
    assert final_trace['path_checks']==6000 and final_trace['failures']==0 and final_trace['source_sha256']==sha(ROOT/SOURCE)
    observer=json.loads((ROOT/latest['race']['path']).with_name('U5M-full-observer-stress.json').read_text());assert observer['completed_observers']==200
    patterns=[r'eyJ[A-Za-z0-9_-]{18,}',r'(?i)postgres(?:ql)?(?:\+\w+)?://[^\s"\']+',
        r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'(?i)bearer\s+[A-Za-z0-9._~-]{20,}',
        r'(?i)(?:ccs_session|x-csrf-token)\s*[=:]\s*[A-Za-z0-9_-]{20,}',r'(?i)(?:password|secret)\s*[:=]\s*["\'][A-Za-z0-9+/=_-]{24,}',
        r'[A-Za-z0-9_-]{80,}\.[A-Za-z0-9_-]{8,}']
    images={}
    for path in candidates:
        p=ROOT/path
        if p.suffix=='.png':images[path]=png(p);continue
        text=p.read_text(encoding='utf-8')
        assert not any(re.search(pattern,text) for pattern in patterns),'PRIVACY_STOP: '+path
        assert not any(line.rstrip()!=line for line in text.splitlines()),'WHITESPACE_STOP: '+path
        if p.suffix=='.py':compile(text,path,'exec')
    review=json.loads((BASE/'screenshot-review.json').read_text());assert len(images)==6 and review['privacy_reviewed']
    for path,value in review['files'].items():assert sha(ROOT/path)==value
    git('diff','--check');git('diff','--cached','--check')
    fsck=git('fsck','--no-reflogs').decode();assert all(line.startswith('dangling ') for line in fsck.splitlines())
    observations=[]
    for path in (ROOT/latest['supervised']['path']).parent.glob('U5L-test*.json'):
        for observed in json.loads(path.read_text()).get('observations',[]):
            assert observed['active_processes']==0,'PROCESS_CLEANUP_STOP'
            assert observed['peak_private_commit_bytes']<=observed['enforced']['private_commit_bytes'],'PRIVATE_COMMIT_LIMIT_STOP'
            observations.append(observed)
    assert len(observations)==31
    plan=dict(baseline_head=HEAD,prerequisite_order=['U5G','U5H','U5I','U5J','U5K','U5L','U5M'],
        existing_files_modified_by_u5m=[SOURCE],new_implementation_test_files=TESTS,mixed_existing_files_to_stage=[],
        implementation_paths=[SOURCE,*TESTS],documentation_tooling_evidence_paths=sorted(set(inventory)-{SOURCE,*TESTS}),
        excluded_preexisting_tracked_modifications=entry['tracked_modifications'],excluded_preexisting_untracked_count=958,
        exact_checkpoint_inventory=inventory,
        implementation_message='fix(ga): stabilize concurrent receipt directory identity (U5M)',
        evidence_message='docs(testing): qualify U5M reliability and deployment boundaries',
        required_git_settings=dict(core_autocrlf=False,literal_pathspecs=True,cr_at_eol_whitespace=True),
        instructions='PROPOSAL ONLY. Requalify HEAD, fetched remote, index, hashes and snapshot after separate authorization. Stage only exact implementation_paths then documentation_tooling_evidence_paths using literal NUL-delimited pathspecs and core.autocrlf=false; verify index names, raw Git blobs and CRLF-aware whitespace each time. No partial staging needed for U5M receipt file: clean at entry, only the two reviewed functions changed. Exclude all eleven unrelated mixed/protected modifications and all 958 prior untracked files. No actual staging performed.')
    data=dict(milestone='U5M',reviewed_at=datetime.now().astimezone().isoformat(),head=HEAD,
        status='RECEIPT_RACE_REPRODUCED_AND_REPAIRED; ISOLATED_QUALIFICATION_PASS; PRODUCTION_BLOCKED',
        exact_changed_and_new_file_inventory=inventory,existing_files_modified=[SOURCE],new_files=len(inventory)-1,
        preservation=dict(baseline_paths=4139,unchanged=4138,intended_modified=1,academic_data_files=23,
            protected_json_unchanged=True,index_unchanged=True,original_engine_source_inputs_unchanged=33,
            unrelated_tracked_modifications=11,unrelated_untracked_files_preserved=958,prior_artifact_hash_references=prior,
            no_postgresql_operations=True,no_historical_evidence_rewrites=True),
        final_python_counts=REQUIRED,final_selected_python_cases=sum(REQUIRED.values()),frontend_contracts=210,browser_scenarios=16,
        browser_runner_count=17,attempts=attempts,nonzero_original_and_worker_fitness=455.0,
        receipt=dict(original_false_rejections=54,original_checks=6000,first_incomplete_repair_false_rejections=3,
            final_writer_checks=6000,final_false_rejections=0,full_observers=200,status='V1_UNVERIFIED; NOT_CURRENT'),
        identity='OPAQUE_SESSION_AND_SERVER_DB_BINDING_VERIFIED_IN_DISPOSABLE_SQLITE; INSTITUTIONAL_SCOPE_UNAVAILABLE',
        admission='BLOCKED',continuous_ui='DISABLED',chair='INDEPENDENT_PROVIDER_UNAVAILABLE',
        containment='CHILD_PRIVATE_COMMIT_USER_CPU_AND_JOB_CLEANUP_QUALIFIED; PARENT_HOST_RATE_RSS_UNQUALIFIED',
        storage='OWNED_TEMP_SQLITE_ONLY; WRITABLE_BACKUP_RESTORE_AND_RETENTION_DELETION_DISABLED',
        final_supervised_process_observations=len(observations),all_observed_ended_children_reaped=True,
        checkpoint_readiness='READY_FOR_SELECTIVE_REVIEW_WITH_EXPLICIT_DEPLOYMENT_BLOCKERS; NO_STAGING_AUTHORIZED',
        privacy='PASS: fictional source provenance, encoded complete/truncated receipt and credential/key/header patterns; six visually reviewed PNGs with valid CRC and no text/EXIF metadata. No raw database, signed receipt, cookie, worker protocol, checkpoint or institutional row archived.',
        whitespace='PASS',git_integrity=dict(exit_code=0,dangling_objects=len(fsck.splitlines())),png_integrity=images,
        artifact_sha256={p:sha(ROOT/p) for p in candidates})
    if record:
        new(BASE/'staging-plan.json',plan);data['artifact_sha256']['docs/testing/dashboard-u5m/staging-plan.json']=sha(BASE/'staging-plan.json')
        new(BASE/'manifest.json',data)
    else:
        original=json.loads((BASE/'manifest.json').read_text())
        for path,value in original['artifact_sha256'].items():assert sha(ROOT/path)==value,'ARTIFACT_HASH_STOP: '+path
        assert original['exact_changed_and_new_file_inventory']==inventory,'INVENTORY_STOP'
    print(json.dumps(dict(status='PASS',baseline_unchanged=4138,intended_modified=1,inventory=len(inventory),
        new_files=len(inventory)-1,artifact_hashes=len(inventory)-1,python_passes=sum(REQUIRED.values()),
        production_admission='BLOCKED',continuous_ui='DISABLED')))

if __name__=='__main__':inspect('--record' in sys.argv)
