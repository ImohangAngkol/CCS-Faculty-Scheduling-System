"""Read-only preservation/privacy replay; --record creates new final evidence.

No application imports, database connections, index writes or restoration.
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
HEAD='5d4d02c52f67b30b6dec13179d0389e5dc46daf5'
SOURCE=['backend/services/'+n+'.py' for n in ['ga_worker_contract','ga_worker_store','ga_worker_child','ga_bounded_worker']]
TESTS=['backend/tests/bounded_worker_support.py','backend/tests/test_bounded_worker.py']
REPORT='docs/dashboard-u5k-bounded-continuous-worker.md'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args):
    return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),*args],cwd=ROOT,
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
    baseline=json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'));assert len(baseline)==3856
    for path,value in baseline.items():assert sha(ROOT/path)==value,'PRESERVATION_STOP: '+path
    prior={}
    for key in ['u5g','u5h','u5i','u5j']:
        old=json.loads((BASE.parent/('dashboard-'+key)/'manifest.json').read_text(encoding='utf-8'))
        for path,value in old['artifact_sha256'].items():assert sha(ROOT/path)==value,'PREREQUISITE_HASH_STOP: '+path
        prior[key]=len(old['artifact_sha256'])
    entry=json.loads((BASE/'entry-review.json').read_text(encoding='utf-8'))
    assert set(git('diff','--name-only').decode().splitlines())==set(entry['tracked_modifications'])
    candidates=sorted(SOURCE+TESTS+[REPORT]+[p.relative_to(ROOT).as_posix() for p in BASE.rglob('*')
        if p.is_file() and p.name not in {'manifest.json','staging-plan.json'}])
    inventory=sorted(candidates+['docs/testing/dashboard-u5k/manifest.json','docs/testing/dashboard-u5k/staging-plan.json'])
    visible=set(git('ls-files','--cached','--others','--exclude-standard','-z').decode().split('\0'))-{''}
    assert not visible-set(baseline)-set(inventory),'UNAPPROVED_NEW_PATH_STOP'
    for folder in ['backend/data','backend/run_checkpoints','backend/saved_chromosomes','backend/run_input_receipts_v1','backend/run_provenance_v1','backend/constrained_runs_v2','backend/generation_snapshots','backend/stopped_runs']:
        assert not {p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file()}-set(baseline),'NEW_RUNTIME_FILE_STOP: '+folder
    assert sum(p.startswith('backend/data/') for p in baseline)==23
    attempts=[]
    for p in sorted(BASE.rglob('*command.json')):
        row=json.loads(p.read_text(encoding='utf-8'))
        attempts.append(dict(path=p.relative_to(ROOT).as_posix(),selection=row['selection'],exit_code=row['exit_code'],counts=counts(row)))
    required={'worker':32,'qualification':49,'admission':50,'consumption':39,'parity':5,'legacy':10,'bundle-tests':32,
        'receipts':36,'analysis':20,'readiness':20,'backend-regressions':99}
    for role,total in required.items():
        attempt=[r for r in attempts if r['selection']==role][-1]
        assert attempt['exit_code']==0 and attempt['counts']['passed']==total,'TEST_STATUS_STOP: '+role
        proof=json.loads((ROOT/attempt['path']).with_name('snapshot-proof.json').read_text(encoding='utf-8'))
        assert proof['complete'] and proof['no_actual_staging'] and proof['head']==HEAD
        if role=='worker':
            for path in SOURCE+TESTS:assert proof['source_sha256'][path]==sha(ROOT/path),'UNTESTED_SOURCE_STOP: '+path
    for role,total in [('frontend',210),('browser',17)]:
        attempt=[r for r in attempts if r['selection']==role][-1]
        assert attempt['exit_code']==0 and attempt['counts']['pass']==total
    for role in ['build','bundle','lint']:assert [r for r in attempts if r['selection']==role][-1]['exit_code']==0
    patterns=[r'eyJ[A-Za-z0-9_-]{18,}',r'(?i)postgres(?:ql)?(?:\+\w+)?://[^\s"\']+',
        r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'(?i)bearer\s+[A-Za-z0-9._~-]{20,}',
        r'(?i)(?:ccs_session|x-csrf-token)\s*[=:]\s*[A-Za-z0-9_-]{20,}',r'(?i)(?:password|secret)\s*[:=]\s*["\'][A-Za-z0-9+/=_-]{24,}']
    images={}
    for path in candidates:
        p=ROOT/path
        if p.suffix=='.png':images[path]=png(p);continue
        text=p.read_text(encoding='utf-8')
        assert not any(re.search(pattern,text) for pattern in patterns),'PRIVACY_STOP: '+path
        assert not any(line.rstrip()!=line for line in text.splitlines()),'WHITESPACE_STOP: '+path
        if p.suffix=='.py':compile(text,path,'exec')
    review=json.loads((BASE/'screenshot-review.json').read_text(encoding='utf-8'))
    assert len(images)==6 and review['privacy_reviewed']
    for path,value in review['files'].items():assert sha(ROOT/path)==value
    git('diff','--check');git('diff','--cached','--check')
    fsck=git('fsck','--no-reflogs').decode();assert all(line.startswith('dangling ') for line in fsck.splitlines())
    plan=dict(prerequisite_order=['U5G','U5H','U5I','U5J','U5K'],prerequisites_committed=True,baseline_head=HEAD,
        implementation_test_files=SOURCE+TESTS,existing_files_modified_by_u5k=[],mixed_existing_files_to_stage=[],
        documentation_tooling_evidence_files=sorted(set(inventory)-set(SOURCE+TESTS)),
        implementation_commit_message='feat(ga): add isolated bounded worker lifecycle and checkpoint ownership',
        evidence_commit_message='docs(testing): qualify U5K worker recovery and preservation',
        instruction='After separate authorization, stage only these exact new paths. Requalify HEAD, index, artifact hashes and isolated snapshot. Exclude all unrelated modified/untracked files. Production remains blocked; no actual staging performed.')
    data=dict(milestone='U5K',reviewed_at=datetime.now().astimezone().isoformat(),head=HEAD,
        status='ISOLATED_WINDOWS_WORKER_VERIFIED; PRODUCTION_ADMISSION_BLOCKED; CONTINUOUS_UI_DISABLED',
        exact_changed_and_new_file_inventory=inventory,new_files=len(inventory),existing_files_modified=[],
        preservation=dict(baseline_paths=3856,unchanged=3856,academic_data_files=23,protected_json_unchanged=True,
            original_engine_fingerprints_unchanged=True,index_unchanged=True,unrelated_tracked_modifications=len(entry['tracked_modifications']),
            prior_artifact_hash_references=prior,no_postgresql_operations=True),
        final_python_counts=required,unique_python_passes=sum(required.values()),frontend_contracts=210,browser_scenarios=16,
        browser_runner_count=17,attempts=attempts,nonzero_original_and_worker_fitness=455.0,
        authority='GENUINE_INSTITUTIONAL_PROVIDER_UNAVAILABLE',capture='QUALIFIED_PREPARED_FICTIONAL_INPUTS_ONLY',
        storage='NEW_OWNED_TEMP_SQLITE_ONLY; DEPLOYMENT_UNQUALIFIED',admission='UNCHANGED_UNAVAILABLE',continuous_ui='DISABLED',
        cpu_memory_quota_mode='UNAVAILABLE_FAIL_CLOSED',windows_job_scope='LOCAL_SESSION_RUN_AND_STORE_CAPS',
        privacy='PASS: fictional source-only fixtures; complete/truncated encoded receipt and credential/key/header patterns scanned. Six PNGs visually reviewed with CRC/no embedded metadata. No raw worker protocol/checkpoint/database files archived.',
        whitespace='PASS',git_integrity=dict(exit_code=0,dangling_objects=len(fsck.splitlines())),png_integrity=images,
        artifact_sha256={p:sha(ROOT/p) for p in candidates})
    if record:
        new(BASE/'staging-plan.json',plan)
        data['artifact_sha256']['docs/testing/dashboard-u5k/staging-plan.json']=sha(BASE/'staging-plan.json')
        new(BASE/'manifest.json',data)
    else:
        original=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
        for path,value in original['artifact_sha256'].items():assert sha(ROOT/path)==value,'ARTIFACT_HASH_STOP: '+path
        assert original['exact_changed_and_new_file_inventory']==inventory,'INVENTORY_STOP'
    print(json.dumps(dict(status='PASS',baseline_preserved=3856,inventory=len(inventory),artifact_hashes=len(inventory)-1,
        python_passes=sum(required.values()),production_admission='BLOCKED',continuous_ui='DISABLED')))

if __name__=='__main__':inspect('--record' in sys.argv)
