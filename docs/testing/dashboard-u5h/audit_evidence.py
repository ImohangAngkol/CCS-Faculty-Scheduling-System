"""Non-writing replay of U5H preservation, privacy and qualification integrity.

--record creates new manifest/plan files only, refusing historical replacement.
No algorithm imports, database calls, index writes or source restoration.
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
HEAD='d6db077793da52b7559351a5d0f8e6d54608cb77'
SDK=['backend/services/ga_bundle_runtime.py','backend/services/ga_bundle_checkpoint.py','backend/services/ga_bundle_optimizer.py']
TESTS=['backend/tests/test_ga_bundle_optimizer.py','backend/tests/test_ga_bundle_parity.py']
PREREQUISITES=['backend/services/ga_input_bundle.py','backend/tests/test_ga_input_bundle.py','backend/tests/test_ga_input_bundle_checkpoint_qualification.py']
REPORT='docs/dashboard-u5h-optimizer-consumption-boundary.md'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args,input=None):return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),*args],cwd=ROOT,input=input,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)
def write_new(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(value,indent=2)+'\n')
def counts(row):
    out=row.get('stdout','')
    found={k:int(v) for k,v in re.findall(r'(?m)^\S+ (tests|pass|fail|skipped|cancelled) (\d+)\s*$',out)}
    return found or {k:int(v) for v,k in re.findall(r'(\d+) (passed|failed|skipped|warnings?|errors?)',out.split('short test summary info')[-1])}
def png(path):
    raw=path.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n';pos=8;chunks=[];size=None
    while pos<len(raw):
        length=struct.unpack('>I',raw[pos:pos+4])[0];kind=raw[pos+4:pos+8];data=raw[pos+8:pos+8+length]
        crc=struct.unpack('>I',raw[pos+8+length:pos+12+length])[0]
        assert zlib.crc32(kind+data)&0xffffffff==crc and kind not in [b'tEXt',b'iTXt',b'zTXt',b'eXIf']
        if kind==b'IHDR':size=struct.unpack('>II',data[:8])
        chunks.append(kind.decode());pos+=length+12
    assert pos==len(raw) and chunks[-1]=='IEND' and size
    return dict(width=size[0],height=size[1],chunks=sorted(set(chunks)))

def inspect(record=False):
    assert git('rev-parse','HEAD').decode().strip()==HEAD and git('branch','--show-current').decode().strip()=='main','HEAD_CHANGED_STOP'
    assert not git('diff','--cached','--name-only').strip(),'STAGED_CONTENT_STOP'
    baseline=json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'));assert len(baseline)==3653
    for name,digest in baseline.items():assert (ROOT/name).is_file() and sha(ROOT/name)==digest,'PRESERVATION_STOP: '+name
    assert sum(n.startswith('backend/data/') for n in baseline)==23
    entry=json.loads((BASE/'entry-review.json').read_text(encoding='utf-8'))
    assert set(git('diff','--name-only').decode().splitlines())==set(entry['preexisting_tracked_modifications'])
    for folder in ['backend/data','backend/run_checkpoints','backend/saved_chromosomes','backend/run_input_receipts_v1','backend/run_provenance_v1','backend/constrained_runs_v2','backend/generation_snapshots','backend/stopped_runs']:
        assert not {p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file()}-set(baseline),'NEW_RUNTIME_FILE_STOP: '+folder
    previous=json.loads((BASE.parent/'dashboard-u5g/manifest.json').read_text(encoding='utf-8'))
    for name,digest in previous['artifact_sha256'].items():assert sha(ROOT/name)==digest
    for source in json.loads((BASE/'source-map.json').read_text(encoding='utf-8'))['source_map']:assert sha(ROOT/source['path'])==source['sha256']
    attempts=[]
    for path in sorted(BASE.rglob('*command.json')):
        row=json.loads(path.read_text(encoding='utf-8'))
        attempts.append(dict(path=path.relative_to(ROOT).as_posix(),selection=row['selection'],exit_code=row['exit_code'],counts=counts(row)))
    for key,total,field in [('backend-regressions',99,'passed'),('receipts',36,'passed'),('analysis',20,'passed'),('backend',20,'passed'),('frontend',210,'pass'),('browser',17,'pass')]:
        row=[r for r in attempts if r['selection']==key][-1];assert row['exit_code']==0 and row['counts'][field]==total
    for key in ['build','bundle','lint','integrity']:assert [r for r in attempts if r['selection']==key][-1]['exit_code']==0
    roles={}
    for path in sorted(BASE.glob('*snapshot/snapshot-proof.json')):
        proof=json.loads(path.read_text(encoding='utf-8'))
        assert proof['complete'] and proof['no_actual_staging'] and proof['no_u5d_u5e_u5f_app_dependency']
        for row in proof['results']:
            assert row['exit_code']==0
            roles[row['selection']]=(path,proof)
    qualified=[]
    for role,total,names in [('consumption',39,SDK+[TESTS[0]]+PREREQUISITES),('parity',5,SDK+[TESTS[1]]+PREREQUISITES),
                             ('legacy',10,PREREQUISITES),('bundle-tests',32,PREREQUISITES)]:
        path,proof=roles[role]
        for name in names:
            assert sha(ROOT/name)==proof['source_sha256'][name],'QUALIFIED_SOURCE_DRIFT_STOP: '+name
            assert git('hash-object','--stdin',input=(ROOT/name).read_bytes()).decode().strip()==proof['proposed_blob_oids'][name]
        row=json.loads((path.parent/(role+'-command.json')).read_text(encoding='utf-8'))
        assert row['exit_code']==0 and counts(row)['passed']==total
        qualified.append(dict(selection=role,path=path.relative_to(ROOT).as_posix(),passed=total,relevant_source_paths=names))
    final_parity=roles['parity'][0].parent
    for path in final_parity.glob('parity-*.json'):
        if not re.fullmatch(r'parity-\d+-\d+\.json',path.name):continue
        doc=json.loads(path.read_text(encoding='utf-8'));q=doc['receipt']
        assert doc['schedule_fitness_history_and_rng_equal'] and q['verification_status']=='VERIFIED' and not q['eligible_for_current'] and q['institutional_authorization']=='NOT_ESTABLISHED'
    child=json.loads((final_parity/'fresh-process.json').read_text(encoding='utf-8'));assert child['result']=='PASS' and child['receipt']['verification_status']=='VERIFIED'
    positive=json.loads((final_parity/'nonzero-parity.json').read_text(encoding='utf-8'));assert positive['best_fitness']==455 and positive['schedule_fitness_history_rng_equal']
    inventory=sorted(set(SDK+TESTS+[REPORT,'docs/testing/dashboard-u5h/manifest.json','docs/testing/dashboard-u5h/staging-plan.json'])|{p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file()})
    assert not any(n in baseline or n.startswith('backend/data/') or Path(n).name.startswith('.env') for n in inventory)
    untracked=set(git('ls-files','--others','--exclude-standard','-z').decode().split('\0'))-{''}
    assert not untracked-set(baseline)-set(inventory),'UNAPPROVED_NEW_PATH_STOP'
    plan=dict(head=HEAD,exact_checkpoint_inventory=inventory,whole_file_paths=inventory,partial_only=[],modified_existing_files=[],
        required_uncommitted_prerequisites=PREREQUISITES,prerequisite_policy='Qualify/checkpoint U5G separately first, or obtain explicit combined-inventory authorization. Never silently stage prerequisites as U5H.',
        excluded_tracked_paths=entry['preexisting_tracked_modifications'],actual_staging=False,commit_push_authorized=False,
        readiness='CONDITIONAL_PREREQUISITES_AND_RETAINED_LEGACY_WARNING',
        recommended_messages=['feat(ga): bind fixed optimization to immutable run bundles','docs(testing): archive U5H consumption and checkpoint qualification'],
        instructions=['Separate authorization and fresh upstream/inventory review before checkpoint.',
            'Only literal whole_file_paths are eligible; never add dot or add -A.',
            'No existing/partial paths; protected JSON and unrelated U5D-U5G/UI/research work stay excluded.',
            'SDK qualification uses byte-identical U5G prerequisites. Working-tree UI regression commands additionally require their U5D-U5F files.',
            'Use core.autocrlf=false for evidence bytes and compare staged blob OIDs with proposed_git_blob_oids.',
            'New entry is internal/synchronous, not HTTP activation or a continuous worker.'])
    if record and not (BASE/'staging-plan.json').exists():write_new(BASE/'staging-plan.json',plan)
    else:assert json.loads((BASE/'staging-plan.json').read_text(encoding='utf-8'))==plan
    registry=json.loads((ROOT/'backend/data/faculty_identities.json').read_text(encoding='utf-8'))['faculty']
    names={re.sub(r'\s+',' ',s.strip().upper()) for row in registry for s in [row['name'],*row.get('aliases',[])] if len(s.strip())>=8}
    patterns=[r'eyJ[A-Za-z0-9_=-]{16,}',r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}',r'(?i)\b(?:postgresql|postgres|mysql)(?:\+\w+)?://[^\s]+',r'-----BEGIN [A-Z ]*PRIVATE KEY-----',r'(?i)https?://[^\s/]+:[^\s/@]+@',r'(?i)(?<![\w])(?:set-cookie|authorization)\s*:\s*[^\s]{16,}']
    hashes={};oids={};screens={}
    for name in inventory:
        if name=='docs/testing/dashboard-u5h/manifest.json':continue
        path=ROOT/name;raw=path.read_bytes();hashes[name]=sha(path)
        if path.suffix=='.png':screens[name]=png(path)
        else:
            content=raw.decode('utf-8');assert content.endswith('\n') and all(line==line.rstrip() for line in content.splitlines()),'WHITESPACE_STOP: '+name
            upper=re.sub(r'\s+',' ',content.upper())
            assert not any(re.search(r'(?<!\w)'+re.escape(s)+r'(?!\w)',upper) for s in names),'PRIVATE_NAME_STOP_WITHHELD'
            assert not any(re.search(p,content) for p in patterns),'SENSITIVE_PATTERN_STOP_WITHHELD'
        oids[name]=git('hash-object','--stdin',input=raw).decode().strip()
        assert oids[name]==git('-c','core.autocrlf=false','hash-object','--path='+name,'--stdin',input=raw).decode().strip()
    visual=json.loads((BASE/'screenshot-review.json').read_text(encoding='utf-8'))
    assert not visual['private_records_seen'] and set(visual['reviewed_sha256'])=={sha(ROOT/n) for n in screens}
    for path in BASE.rglob('browser-results.json'):
        for c in json.loads(path.read_text(encoding='utf-8'))['captures']:
            n=(path.parent/c['file']).relative_to(ROOT).as_posix();assert all(screens[n][k]==c['viewport'][k] for k in ['width','height'])
    git('diff','--cached','--check');assert git('rev-parse','HEAD').decode().strip()==HEAD and sha(ROOT/'.git/index')==baseline['.git/index']
    return dict(milestone='U5H',status='INTERNAL_VERSIONED_CONSUMPTION_AND_CHECKPOINT_BINDING_VERIFIED_LEGACY_HTTP_UNCHANGED',head=HEAD,
        exact_checkpoint_inventory=inventory,new_paths=inventory,modified_existing_files=[],baseline_paths=3653,unchanged_baseline_paths=3653,protected_academic_paths=23,
        preexisting_tracked_modifications=entry['preexisting_tracked_modifications'],prior_u5g_artifact_hashes_verified=33,
        artifact_sha256=hashes,proposed_git_blob_oids=oids,attempts=attempts,qualified_role_proofs=qualified,screenshots=screens,
        unique_python_cases_passed=261,frontend_contracts_passed=210,browser_scenarios_passed=16,
        nonzero_parity_fitness=455.0,legacy_receipt_warning='One retained directory guard failure; isolated and full reruns passed; exact intermittent cause UNCONFIRMED; guard unchanged.',
        privacy='PASS complete/partial encoded fragments, credential/header/URL patterns, private-name comparison, PNG CRC/metadata and visual review',whitespace='PASS',
        protected_preferences_settings='BYTE_IDENTICAL_UNSTAGED_EXCLUDED',ga_legacy_scoring_rng_fingerprints_migrations_checkpoints_saved_best_history='UNCHANGED',
        git_index_head='UNCHANGED',staged_files=[],internal_consumption_verified=True,bundle_checkpoint_binding_verified=True,
        legacy_http_consumption='UNVERIFIED_UNCHANGED',institutional_authorization='BLOCKED',continuous_executable=False,
        checkpoint_readiness='CONDITIONAL_ON_U5G_PREREQUISITE_ORDER_AND_REVIEW_OF_LEGACY_WARNING')

if __name__=='__main__':
    result=inspect('--record' in sys.argv)
    if '--record' in sys.argv:write_new(BASE/'manifest.json',dict(result,recorded_at=datetime.now().astimezone().isoformat()))
    else:assert {k:v for k,v in json.loads((BASE/'manifest.json').read_text(encoding='utf-8')).items() if k!='recorded_at'}==result
    print(json.dumps(dict(status='AUDIT_PASSED',inventory=len(result['exact_checkpoint_inventory']),artifact_hashes=len(result['artifact_sha256']),baseline_preserved=3653,consumption_scope='NEW_INTERNAL_CONTRACT_ONLY')))
