"""Non-writing integrity replay; --record creates a new manifest/plan only.

No GA imports, database access, Git index writes, source restoration or cleanup.
"""
from datetime import datetime
import difflib
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
HEAD='d6db077793da52b7559351a5d0f8e6d54608cb77'
SOURCE=['backend/services/ga_owned_store.py','backend/services/ga_run_authority.py','backend/services/ga_trusted_runs.py','backend/routers/ga_trusted_runs.py']
TESTS=['backend/tests/test_trusted_runs.py','backend/tests/trusted_run_support.py']
REPORT='docs/dashboard-u5i-trusted-run-admission.md'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args,input=None):
    return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),*args],cwd=ROOT,input=input,
        env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)
def write_new(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,indent=2)+'\n')
def counts(row):
    text=row.get('stdout','')
    node={k:int(v) for k,v in re.findall(r'(?m)^\S+ (tests|pass|fail|skipped|cancelled) (\d+)\s*$',text)}
    return node or {k:int(v) for v,k in re.findall(r'(\d+) (passed|failed|skipped|warnings?|errors?)',text.split('short test summary info')[-1])}
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
    assert git('branch','--show-current').decode().strip()=='main'
    assert not git('diff','--cached','--name-only').strip(),'STAGED_CONTENT_STOP'
    baseline=json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'));assert len(baseline)==3730
    for path,value in baseline.items():
        if path!='backend/main.py':assert sha(ROOT/path)==value,'PRESERVATION_STOP: '+path
    entry=(BASE/'entry/main.py').read_bytes();actual=(ROOT/'backend/main.py').read_bytes()
    assert hashlib.sha256(entry).hexdigest()==baseline['backend/main.py']
    assert actual.replace(b'from routers import ga_trusted_runs\r\n',b'').replace(b'app.include_router(ga_trusted_runs.router)\r\n',b'')==entry,'MIXED_MAIN_STOP'
    previous=json.loads((BASE.parent/'dashboard-u5h/manifest.json').read_text(encoding='utf-8'))
    for path,value in previous['artifact_sha256'].items():assert sha(ROOT/path)==value,'U5H_ARTIFACT_STOP: '+path
    tracked=json.loads((BASE/'entry-review.json').read_text(encoding='utf-8'))['preexisting_tracked_modifications']
    assert set(git('diff','--name-only').decode().splitlines())==set(tracked),'TRACKED_INVENTORY_STOP'
    candidates=SOURCE+TESTS+[REPORT]+[p.relative_to(ROOT).as_posix() for p in sorted(BASE.rglob('*')) if p.is_file() and p.name not in {'manifest.json','staging-plan.json'}]
    candidates=sorted(set(candidates));assert all((ROOT/p).is_file() for p in candidates)
    known=set(baseline)|set(candidates)|{'docs/testing/dashboard-u5i/manifest.json','docs/testing/dashboard-u5i/staging-plan.json'}
    visible=set(git('ls-files','--cached','--others','--exclude-standard','-z').decode().split('\0'))-{''}
    assert not visible-known,'UNAPPROVED_NEW_PATH_STOP: '+str(sorted(visible-known))
    for folder in ['backend/data','backend/run_checkpoints','backend/saved_chromosomes','backend/run_input_receipts_v1','backend/run_provenance_v1','backend/constrained_runs_v2','backend/generation_snapshots','backend/stopped_runs']:
        assert not {p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file()}-set(baseline),'NEW_RUNTIME_FILE_STOP: '+folder
    assert sum(p.startswith('backend/data/') for p in baseline)==23
    attempts=[]
    for path in sorted(BASE.rglob('*command.json')):
        row=json.loads(path.read_text(encoding='utf-8'))
        attempts.append(dict(path=path.relative_to(ROOT).as_posix(),selection=row['selection'],exit_code=row['exit_code'],counts=counts(row)))
    required={'admission':50,'consumption':39,'parity':5,'legacy':10,'bundle-tests':32,'receipts':36,'receipt-isolation':1,'analysis':20,'readiness':20,'backend-regressions':99}
    proofs=[]
    for role,total in required.items():
        attempt=[r for r in attempts if r['selection']==role][-1]
        assert attempt['exit_code']==0 and attempt['counts']['passed']==total,'TEST_STATUS_STOP: '+role
        proof_path=ROOT/attempt['path'];proof=json.loads((proof_path.parent/'snapshot-proof.json').read_text(encoding='utf-8'))
        assert proof['complete'] and proof['no_actual_staging']
        if role=='admission':
            for p in SOURCE+TESTS:assert proof['source_sha256'][p]==sha(ROOT/p),'UNTESTED_SOURCE_STOP: '+p
        proofs.append(dict(role=role,artifact=proof_path.relative_to(ROOT).as_posix(),tests=total))
    for role,total in [('frontend',210),('browser',17)]:
        attempt=[r for r in attempts if r['selection']==role][-1];assert attempt['exit_code']==0 and attempt['counts']['pass']==total
    for role in ['build','bundle','lint','integrity']:assert [r for r in attempts if r['selection']==role][-1]['exit_code']==0
    # Complete/truncated encoded receipt patterns, credential-bearing URIs,
    # key blocks and actual bearer/cookie assignments. Never emit a match.
    patterns=[r'eyJ[A-Za-z0-9_-]{18,}',r'(?i)postgres(?:ql)?(?:\+\w+)?://[^\s"\']+',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        r'(?i)bearer\s+[A-Za-z0-9._~-]{20,}',r'(?i)(?:ccs_session|x-csrf-token)\s*[=:]\s*[A-Za-z0-9_-]{20,}']
    images={}
    for path in candidates:
        p=ROOT/path
        if p.suffix=='.png':images[path]=png(p);continue
        text=p.read_text(encoding='utf-8')
        assert not any(re.search(pattern,text) for pattern in patterns),'PRIVACY_STOP: '+path
        if p.suffix in {'.py','.json','.md','.patch'}:
            assert not any(line.rstrip()!=line for line in text.splitlines()),'WHITESPACE_STOP: '+path
        if p.suffix=='.py':compile(text,path,'exec')
    git('diff','--check');git('diff','--cached','--check')
    # No whole-file staging of mixed main. Build an independent HEAD-only hunk.
    old=git('show',HEAD+':backend/main.py').decode();new=old.replace('from routers import ga_evaluation\n','from routers import ga_evaluation\nfrom routers import ga_trusted_runs\n').replace('app.include_router(ga_evaluation.router)\n','app.include_router(ga_evaluation.router)\napp.include_router(ga_trusted_runs.router)\n')
    patch='diff --git a/backend/main.py b/backend/main.py\n'+''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/backend/main.py',tofile='b/backend/main.py'))
    plan=dict(prerequisite_order=['U5G','U5H','U5I'],prerequisites_still_uncommitted=True,
        implementation_new_files=SOURCE+TESTS,mixed_file='backend/main.py',main_strategy='Select ONLY the two ga_trusted_runs import/include lines. Never stage this entire mixed file.',
        head_only_patch_reference=patch,head_only_main_blob=git('hash-object','--stdin',input=new.encode()).decode().strip(),
        documentation_files=sorted(set(candidates)-set(SOURCE+TESTS))+['docs/testing/dashboard-u5i/staging-plan.json','docs/testing/dashboard-u5i/manifest.json'],
        actual_staging_performed=False,recheck_after_prerequisite_commits=True)
    inventory=sorted(set(candidates+['backend/main.py','docs/testing/dashboard-u5i/staging-plan.json','docs/testing/dashboard-u5i/manifest.json']))
    data=dict(milestone='U5I',reviewed_at=datetime.now().astimezone().isoformat(),head=HEAD,
        status='ISOLATED_FOUNDATION_VERIFIED; PRODUCTION_AUTHORITY_AND_STORAGE_BLOCKED',
        exact_changed_and_new_file_inventory=inventory,modified_existing=['backend/main.py'],
        new_files=len(inventory)-1,baseline_paths=3730,unchanged_baseline_paths=3729,academic_files_preserved=23,
        protected_json_unchanged=True,git_index_unchanged=True,main_other_bytes_preserved=True,prior_u5h_hashes_verified=len(previous['artifact_sha256']),
        selected_test_proofs=proofs,unique_python_tests=sum(v for k,v in required.items() if k!='receipt-isolation'),
        frontend_contracts=210,browser_scenarios=16,browser_test_runner_counts=17,
        browser_scope='Real Edge with fictional intercepted HTTP; not live optimizer authorization. New U5I HTTP is tested with real session/CSRF/SQLite and owned loopback; no U5I browser UI added.',
        attempts=attempts,python_source_compilation=True,png_integrity=images,
        privacy='PASS: textual complete/partial receipt, credentials and key-pattern scan; fictional source snapshots; reviewed screenshots without embedded text/EXIF metadata.',
        whitespace='PASS',no_postgresql_operations=True,production_authority='BLOCKED',continuous_worker=False,
        outstanding=['Institutional scoped optimization issuer and source catalog not configured','Production storage/lifecycle/retention not installed','Historical U5D concurrency root cause remains unconfirmed','No live PostgreSQL acceptance','No continuous worker or new frontend'],
        artifact_sha256={p:sha(ROOT/p) for p in candidates})
    if record:
        write_new(BASE/'staging-plan.json',plan);data['artifact_sha256']['docs/testing/dashboard-u5i/staging-plan.json']=sha(BASE/'staging-plan.json')
        write_new(BASE/'manifest.json',data)
    else:
        original=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
        for p,h in original['artifact_sha256'].items():assert sha(ROOT/p)==h,'ARTIFACT_HASH_STOP: '+p
        assert original['exact_changed_and_new_file_inventory']==inventory,'CHECKPOINT_INVENTORY_STOP'
    print(json.dumps(dict(status='PASS',baseline_preserved=3729,mixed_main_preserved=True,inventory=len(inventory),artifact_hashes=len(data['artifact_sha256'])+(0 if record else 1),python_tests=data['unique_python_tests'],production='BLOCKED')))

if __name__=='__main__':inspect('--record' in sys.argv)
