"""U5O read-only evidence/preservation replay. --record seals new audit artifacts.

No application imports, database connections, Git staging or cleanup.
"""
from datetime import datetime
import csv
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
HEAD='30af999939146dbf818b9d86caa66646da46c5cf'
REPORT='docs/dashboard-u5o-full-system-functional-audit.md'
TEST='backend/tests/test_full_system_audit.py'
REQUIRED={'u5o-audit':3,'dashboard-all':458,'resource-fictional':8,'v2-engine':30,'v2-api':18,
    'backend-regressions':99,'race':19,'receipts':36,'consumption':39,'bundle-tests':32,
    'admission':50,'qualification':49,'identity':16,'preference-scope':3,'analysis':20,
    'readiness':20,'native':12,'supervised':41,'worker':32,'parity':5,'legacy':10,
    'recovery':40,'parent':7,'d16-live':1}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),*args],cwd=ROOT,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)
def new(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,indent=2)+'\n')
def counts(row):
    out=row.get('stdout','')
    node={k:int(v) for k,v in re.findall(r'(?m)^\S+ (tests|pass|fail|skipped|cancelled) (\d+)\s*$',out)}
    return node or {k:int(v) for v,k in re.findall(r'(\d+) (passed|failed|skipped|deselected|warnings?|errors?)',out.split('short test summary info')[-1])}
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
    baseline=json.loads((BASE/'preservation-baseline.json').read_text());assert len(baseline)==4447
    for path,value in baseline.items():assert sha(ROOT/path)==value,'BASELINE_CHANGED_STOP: '+path
    prior={}
    for name in ['u5g','u5h','u5i','u5j','u5k','u5l','u5m','u5n']:
        old=json.loads((BASE.parent/('dashboard-'+name)/'manifest.json').read_text())
        for path,value in old['artifact_sha256'].items():assert sha(ROOT/path)==value,'PRIOR_ARTIFACT_CHANGED_STOP: '+path
        prior[name]=len(old['artifact_sha256'])
    entry=json.loads((BASE/'entry-review.json').read_text());assert len(entry['tracked_modifications'])==11 and len(entry['untracked_files'])==958
    assert sorted(git('diff','--name-only').decode().splitlines())==sorted(entry['tracked_modifications'])
    candidates=sorted([TEST,REPORT]+[p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file() and p.name not in {'manifest.json','staging-plan.json'}])
    inventory=sorted(candidates+['docs/testing/dashboard-u5o/manifest.json','docs/testing/dashboard-u5o/staging-plan.json'])
    visible=set(git('ls-files','--cached','--others','--exclude-standard','-z').decode().split('\0'))-{''}
    assert not visible-set(baseline)-set(inventory),'UNAPPROVED_NEW_PATH_STOP'
    assert set(entry['untracked_files'])<=visible
    assert not set(inventory)&set(git('ls-files','-z').decode().split('\0')),'EXISTING_PATH_IN_NEW_CHECKPOINT_STOP'
    assert sum(p.startswith('backend/data/') for p in baseline)==23
    attempts=[]
    for path in sorted(BASE.rglob('*command.json')):
        row=json.loads(path.read_text());attempts.append(dict(path=path.relative_to(ROOT).as_posix(),selection=row['selection'],exit_code=row['exit_code'],counts=counts(row)))
    latest={k:[a for a in attempts if a['selection']==k][-1] for k in REQUIRED}
    for role,total in REQUIRED.items():
        r=latest[role];assert r['exit_code']==0 and r['counts'].get('passed')==total,'FINAL_TEST_STATUS_STOP: '+role
        proof=json.loads((ROOT/r['path']).with_name('snapshot-proof.json').read_text());assert proof['head']==HEAD and proof['complete'] and proof['no_actual_staging']
        assert proof['source_sha256'][TEST]==sha(ROOT/TEST),'AUDIT_TEST_SOURCE_CHANGED_STOP'
        for p,value in proof['ui_overlay_sha256'].items():assert sha(ROOT/p)==value,'UI_OVERLAY_CHANGED_STOP: '+p
    failures=[r for r in attempts if r['exit_code']!=0];assert len(failures)==4,'UNRECONCILED_FAILURE_COUNT_STOP'
    for role,total in [('contracts-all',385),('browser',17)]:
        r=[a for a in attempts if a['selection']==role][-1];assert r['exit_code']==0 and r['counts']['pass']==total
        source=json.loads((ROOT/r['path']).read_text());assert source['ui_mode']=='working-tree'
        for p,value in source['ui_overlay_sha256'].items():assert sha(ROOT/p)==value
    for role in ['build','bundle','lint']:assert [a for a in attempts if a['selection']==role][-1]['exit_code']==0
    live=(ROOT/latest['d16-live']['path']).parent/'captures';live_result=json.loads((live/'browser-results.json').read_text())
    assert len(live_result['scenarios'])==23 and not live_result['runtime_errors']
    assert len(json.loads((live/'route-survey.json').read_text())['rows'])==20
    protected_names=set()
    # Compare locally; never export actual academic names or protected values.
    with (ROOT/'backend/data/Faculty.csv').open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            name=(row.get('Faculty') or '').strip()
            if len(name)>=6:protected_names.add(name.casefold())
    patterns=[r'eyJ[A-Za-z0-9_-]{18,}',r'[A-Za-z0-9_-]{80,}\.[A-Za-z0-9_-]{8,}',
        r'(?i)postgres(?:ql)?(?:\+\w+)?://[^\s"\']+',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        r'(?i)bearer\s+[A-Za-z0-9._~-]{20,}',r'''(?i)['"]?(?:X-CSRF-Token|ccs_session|csrf_token|password)['"]?\s*[:=]\s*['"][A-Za-z0-9_-]{24,}''']
    images={}
    for name in candidates:
        p=ROOT/name
        if p.suffix=='.png':images[name]=png(p);continue
        text=p.read_text(encoding='utf-8');assert not any(re.search(pattern,text) for pattern in patterns),'PRIVACY_STOP: '+name
        assert not any(n in text.casefold() for n in protected_names),'PRIVATE_NAME_STOP: '+name
        assert not any(line.rstrip()!=line for line in text.splitlines()),'WHITESPACE_STOP: '+name
        if p.suffix=='.py':compile(text,name,'exec')
    review=json.loads((BASE/'screenshot-review.json').read_text());assert len(images)==36 and review['privacy_reviewed']
    assert set(images)==set(review['files'])
    for path,value in review['files'].items():assert sha(ROOT/path)==value
    parity_paths=sorted(BASE.glob('*/U5K-nonzero-worker-parity.json'));assert parity_paths
    parity=json.loads(parity_paths[-1].read_text());assert parity['original_fitness']==parity['worker_fitness']==455.0
    assert parity['schedule_fitness_history_breakdown_faculty_and_rng_equal'] and parity['global_rng_unchanged'] and not parity['saved_best_promotion']
    git('diff','--check');git('diff','--cached','--check');fsck=git('fsck','--no-reflogs').decode();assert all(s.startswith('dangling ') for s in fsck.splitlines())
    blobs={}
    for p in candidates:
        raw=(ROOT/p).read_bytes();blobs[p]=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    tools=sorted({TEST,*[p for p in candidates if p.endswith(('.py','.mjs'))]})
    plan=dict(baseline_head=HEAD,prerequisite_order=['U5G','U5H','U5I','U5J','U5K','U5L','U5M','U5N','U5O'],
        test_and_audit_tooling_paths=tools,documentation_evidence_paths=sorted(set(inventory)-set(tools)),exact_checkpoint_inventory=inventory,
        existing_files_modified=[],mixed_files_to_stage=[],excluded_preexisting_tracked_modifications=entry['tracked_modifications'],excluded_preexisting_untracked_files=958,
        proposed_blob_oids=blobs,core_autocrlf=False,literal_pathspecs=True,cr_at_eol_whitespace=True,
        commit_messages=['test(audit): characterize system boundaries and fictional workflows (U5O)','docs(audit): archive functional findings and seven-day readiness (U5O)'],
        instructions='PROPOSAL ONLY. Separate authorization and fresh remote verification required. All listed U5O paths are new; no partial index patch. Never stage whole frontend files from the working UI overlay. Stage exact literal NUL-delimited approved paths with core.autocrlf=false; verify raw blobs. Calculate plan/manifest blob identities after sealing; they cannot contain their own hash. Test snapshots deliberately include baseline working UI: they do not independently qualify a committed U5O-only checkout with different UI. Recheck that distinction at checkpoint. Exclude all eleven tracked and 958 pre-existing untracked paths. Do not activate providers, worker, recovery or continuous UI.')
    manifest=dict(milestone='U5O',head=HEAD,reviewed_at=datetime.now().astimezone().isoformat(),status='AUDIT_COMPLETE_WITH_FINDINGS; SEVEN_DAY_NO_GO; NO_PRODUCTION_FIXES',
        exact_changed_and_new_file_inventory=inventory,new_files=len(inventory),existing_files_modified=[],
        preservation=dict(baseline_paths=4447,unchanged=4447,academic_data_files=23,protected_json_unchanged=True,index_unchanged=True,
            unrelated_tracked_modifications=11,unrelated_untracked_files=958,prior_artifact_hash_references=prior,
            original_ga_migrations_checkpoints_saved_best_and_evidence_unchanged=True,no_postgresql_operations=True),
        final_python_counts=REQUIRED,final_selected_python_cases=sum(REQUIRED.values()),frontend_contracts=385,
        real_browser_original_journeys=21,real_browser_defect_characterizations=1,real_browser_route_surveys=1,
        intercepted_browser_scenarios=16,intercepted_node_runner_count=17,attempts=attempts,failed_attempts_retained=len(failures),
        parity=dict(original_and_worker_fitness=455.0,assignments_history_breakdown_faculty_rng_equal=True,global_rng_preserved=True),
        production_admission='BLOCKED',continuous_execution_ui='DISABLED',active_restore='BLOCKED',seven_day='NO_GO; ALL_FOUR_DURATION_GATES_NOT_RUN',
        native_cpu_quota='One unchanged native suite failed at 5.109375 user seconds against <5; unchanged isolated rerun passed at 2.3125. No strict one-second bound established; further resource qualification required.',
        privacy='PASS: text scans for complete/truncated encoded tokens, credential URIs, keys/header/session patterns and private faculty names; all 31 distinct PNG byte sequences visually reviewed, 36 PNGs CRC/metadata checked. No HAR/raw database/checkpoint/package archived.',
        whitespace='PASS',git_integrity=dict(exit_code=0,dangling_objects=len(fsck.splitlines())),png_integrity=images,
        checkpoint_readiness='READY_FOR_SELECTIVE_AUDIT_REVIEW; NOT_A_PRODUCTION_OR_LONG_EXPERIMENT_RELEASE; WORKING_UI_OVERLAY_IS_NOT_INCLUDED',
        artifact_sha256={p:sha(ROOT/p) for p in candidates})
    if record:
        new(BASE/'staging-plan.json',plan);manifest['artifact_sha256']['docs/testing/dashboard-u5o/staging-plan.json']=sha(BASE/'staging-plan.json');new(BASE/'manifest.json',manifest)
    else:
        old=json.loads((BASE/'manifest.json').read_text());assert old['exact_changed_and_new_file_inventory']==inventory
        for path,value in old['artifact_sha256'].items():assert sha(ROOT/path)==value,'ARTIFACT_CHANGED_STOP: '+path
    print(json.dumps(dict(status='PASS',baseline_preserved=4447,new_files=len(inventory),existing_files_modified=0,artifact_hashes=len(inventory)-1,
        python_passes=sum(REQUIRED.values()),failed_attempts_preserved=len(failures),production_admission='BLOCKED',continuous_ui='DISABLED',seven_day='NO_GO')))

if __name__=='__main__':inspect('--record' in sys.argv)
