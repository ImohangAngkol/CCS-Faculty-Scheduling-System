"""Replay U5E preservation, privacy, source-snapshot and selective-checkpoint audit.

No index writes, imports of GA code, database operations or fixture execution.
--record creates a new manifest and staging plan, refusing replacement.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import struct
import subprocess
import sys
import zlib

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
HEAD="d6db077793da52b7559351a5d0f8e6d54608cb77"
MODIFIED=['backend/main.py','frontend/src/pages/admin/FitnessAnalysis.tsx']
NEW=['backend/routers/advanced_ga_analysis.py','backend/services/advanced_ga_analysis.py','backend/tests/test_advanced_ga_analysis.py',
    'frontend/src/components/ga/AdvancedAnalysis.tsx','frontend/src/services/advancedAnalysis.ts',
    'frontend/tests/advancedAnalysis.fixtures.mjs','frontend/tests/advancedAnalysis.test.mjs','frontend/tests/advancedAnalysis.browser.test.mjs']
REPORT='docs/dashboard-u5e-advanced-ga-analysis.md'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args,input=None):
    return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),*args],cwd=ROOT,input=input,
        env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)


def png(path):
    raw=path.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n'
    position=8;chunks=[];size=None
    while position<len(raw):
        length=struct.unpack('>I',raw[position:position+4])[0]
        kind=raw[position+4:position+8];data=raw[position+8:position+8+length]
        crc=struct.unpack('>I',raw[position+8+length:position+12+length])[0]
        assert zlib.crc32(kind+data)&0xffffffff==crc
        assert kind not in [b'tEXt',b'iTXt',b'zTXt',b'eXIf'],'Screenshot contains metadata requiring review'
        chunks.append(kind.decode());position+=length+12
        if kind==b'IHDR':size=struct.unpack('>II',data[:8])
    assert position==len(raw) and chunks[-1]=='IEND' and size
    return {'width':size[0],'height':size[1],'chunks':sorted(set(chunks))}


def counts(row):
    output=row.get('stdout','')
    found={k:int(v) for k,v in re.findall(r'(?m)^\S+ (tests|pass|fail|skipped|cancelled) (\d+)\s*$',output)}
    if not found:
        found={k:int(v) for v,k in re.findall(r'(\d+) (passed|failed|skipped|warnings?|errors?)',output.split('short test summary info')[-1])}
    return found


def inspect(record=False):
    assert git('rev-parse','HEAD').decode().strip()==HEAD,'HEAD_CHANGED_STOP'
    assert git('branch','--show-current').decode().strip()=='main'
    assert not git('diff','--cached','--name-only').strip(),'STAGED_CONTENT_STOP'
    baseline=json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'))
    assert len(baseline)==3268 and sum(p.startswith('backend/data/') for p in baseline)==23
    for name,digest in baseline.items():
        if name not in MODIFIED:assert (ROOT/name).is_file() and sha(ROOT/name)==digest,'PRESERVATION_STOP: '+name
    for folder in ['backend/data','backend/run_checkpoints','backend/saved_chromosomes','backend/run_input_receipts_v1','backend/run_provenance_v1','backend/constrained_runs_v2']:
        assert not {p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file()}-set(baseline),'UNEXPECTED_RUNTIME_FILE_STOP: '+folder
    previous=json.loads((ROOT/'docs/testing/dashboard-u5d/manifest.json').read_text(encoding='utf-8'))
    assert len(previous['exact_checkpoint_inventory'])==24
    for name,digest in previous['artifact_sha256'].items():assert sha(ROOT/name)==digest,'U5D_ARTIFACT_CHANGED_STOP: '+name
    entry=set(previous['preexisting_tracked_modifications'])|set(previous['modified_from_entry'])
    assert set(git('diff','--name-only').decode().splitlines())==entry|set(MODIFIED),'UNEXPECTED_TRACKED_CHANGE_STOP'
    git('diff','--check','--',*MODIFIED)
    helper=runpy.run_path(str(BASE/'checkpoint_snapshot.py'))
    page=helper['PAGE'];raw=(ROOT/page).read_bytes();eol=b'\r\n' if b'\r\n' in raw else b'\n'
    restored=raw.replace(helper['IMPORT'].encode().replace(b'\n',eol),b'').replace(helper['NEW'].encode().replace(b'\n',eol),helper['OLD'].encode())
    assert hashlib.sha256(restored).hexdigest()==baseline[page],'MIXED_PAGE_CHANGED_STOP'
    patch=BASE/'fitness-analysis-integration.patch';git('apply','--check','--cached',str(patch))
    expected_page=helper['integration'](git('show',HEAD+':'+page))
    proofs=sorted(BASE.glob('*snapshot/snapshot-proof.json'));proof=json.loads(proofs[-1].read_text(encoding='utf-8'))
    assert proof['complete'] and proof['no_actual_staging'] and proof['no_u5d_dependency']
    for name,digest in proof['source_sha256'].items():
        content=expected_page if name==page else (ROOT/name).read_bytes()
        assert hashlib.sha256(content).hexdigest()==digest,'SNAPSHOT_SOURCE_DRIFT_STOP: '+name
        assert git('hash-object','--stdin',input=content).decode().strip()==proof['blob_oids'][name]
    evidence_files={p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file()}
    inventory=sorted(set(MODIFIED+NEW+[REPORT,'docs/testing/dashboard-u5e/manifest.json','docs/testing/dashboard-u5e/staging-plan-final.json'])|evidence_files)
    assert not any(n.startswith('backend/data/') or Path(n).name.startswith('.env') for n in inventory)
    untracked=set(git('ls-files','--others','--exclude-standard','-z').decode().split('\0'))-{''}
    assert not untracked-set(baseline)-set(inventory),'UNAPPROVED_NEW_PATH_STOP'
    plan={'base_head':HEAD,'exact_checkpoint_inventory':inventory,'whole_file_paths':[n for n in inventory if n!=page],
        'partial_only':{'path':page,'patch':patch.relative_to(ROOT).as_posix(),'proposed_sha256':hashlib.sha256(expected_page).hexdigest(),
            'proposed_blob_oid':git('hash-object','--stdin',input=expected_page).decode().strip(),
            'future_authorized_command':['git','apply','--cached',str(patch.relative_to(ROOT))]},
        'excluded_tracked_paths':sorted(entry-{page}),'u5d_files_excluded':previous['exact_checkpoint_inventory'],
        'actual_staging':False,'commit_push_authorized':False,
        'recommended_messages':['feat(ga): add candidate-bound advanced faculty analysis','docs(testing): archive U5E analysis validation'],
        'instructions':['Fresh upstream comparison and separate authorization before checkpoint',
            'Use explicit literal paths from whole_file_paths; never add the complete mixed FitnessAnalysis.tsx',
            'After staging, verify every blob against artifact_sha256 except the partial page, which uses its proposed SHA-256',
            'Use core.autocrlf=false for artifact byte preservation; no add dot or add -A',
            'U5D, protected JSON, unfinished U4/Live and unrelated research must stay outside the checkpoint']}
    planpath=BASE/'staging-plan-final.json'
    if record:
        with planpath.open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(plan,indent=2)+'\n')
    else:assert json.loads(planpath.read_text(encoding='utf-8'))==plan
    attempts=[]
    for path in sorted(BASE.glob('*/command.json')):
        row=json.loads(path.read_text(encoding='utf-8'))
        attempts.append({'path':path.relative_to(ROOT).as_posix(),'selection':row['selection'],'exit_code':row['exit_code'],'counts':counts(row),'timed_out':row.get('timed_out',False)})
    final={r['selection']:r for r in attempts}
    for name,total in [('backend',20),('backend-regressions',145),('backend-engine',34)]:
        assert final[name]['exit_code']==0 and final[name]['counts']['passed']==total
    for name,total in [('regressions',166),('browser',17),('u5a-browser',15),('u5b-browser',18),('u5c-browser',9)]:
        assert final[name]['exit_code']==0 and final[name]['counts']['pass']==total
    snapshot_checks=[]
    for path in sorted(proofs[-1].parent.glob('*-command.json')):
        row=json.loads(path.read_text(encoding='utf-8'));assert row['exit_code']==0
        snapshot_checks.append({'selection':row['selection'],'path':path.relative_to(ROOT).as_posix(),'counts':counts(row)})
    assert len(snapshot_checks)==7
    assert next(r for r in snapshot_checks if r['selection']=='focused')['counts']['pass']==17
    for name in ['build','bundle','lint','integrity']:assert final[name]['exit_code']==0
    names_registry=json.loads((ROOT/'backend/data/faculty_identities.json').read_text(encoding='utf-8'))['faculty']
    names={re.sub(r'\s+',' ',s.strip().upper()) for row in names_registry for s in [row['name'],*row.get('aliases',[])] if len(s.strip())>=8}
    patterns=[r'eyJ[A-Za-z0-9_=-]{16,}',r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}',r'(?i)\b(?:postgresql|postgres|mysql)(?:\+\w+)?://[^\s]+',
        r'-----BEGIN [A-Z ]*PRIVATE KEY-----',r'(?i)https?://[^\s/]+:[^\s/@]+@',r'(?i)(?<![\w])(?:set-cookie|authorization)\s*:\s*[^\s]{16,}']
    hashes={};oids={};screens={}
    for name in inventory:
        if name.endswith('/manifest.json') and name=='docs/testing/dashboard-u5e/manifest.json':continue
        path=ROOT/name;raw=path.read_bytes();hashes[name]=sha(path)
        if path.suffix=='.png':screens[name]=png(path)
        else:
            content=raw.decode('utf-8');assert content.endswith('\n'),'MISSING_NEWLINE_STOP: '+name
            # Unified patch context prefixes intentionally contain one space.
            if path.suffix!='.patch':assert all(line==line.rstrip() for line in content.splitlines()),'WHITESPACE_STOP: '+name
            upper=re.sub(r'\s+',' ',content.upper())
            assert not any(re.search(r'(?<!\w)'+re.escape(s)+r'(?!\w)',upper) for s in names),'PRIVATE_NAME_STOP_WITHHELD'
            assert not any(re.search(p,content) for p in patterns),'SENSITIVE_PATTERN_STOP_WITHHELD'
        blob=expected_page if name==page else raw
        oids[name]=git('hash-object','--stdin',input=blob).decode().strip()
        assert oids[name]==git('-c','core.autocrlf=false','hash-object','--path='+name,'--stdin',input=blob).decode().strip()
    corrections=json.loads((BASE/'capture-metadata-addendum.json').read_text(encoding='utf-8'))
    expected_corrections=[]
    for path in BASE.glob('*/browser-results.json'):
        doc=json.loads(path.read_text(encoding='utf-8'))
        for capture in doc['captures']:
            p=(path.parent/capture['file']).relative_to(ROOT).as_posix()
            if not all(screens[p][d]==capture['viewport'][d] for d in ['width','height']):
                expected_corrections.append({'record':path.relative_to(ROOT).as_posix(),'file':capture['file'],'reported':capture['viewport'],
                    'png_pixels':{d:screens[p][d] for d in ['width','height']},'record_sha256':sha(path),'png_sha256':sha(ROOT/p)})
    assert sorted(expected_corrections,key=lambda r:(r['record'],r['file']))==corrections['corrections'] and len(expected_corrections)==5,'UNREVIEWED_CAPTURE_METADATA_STOP'
    visual=json.loads((BASE/'screenshot-review-final.json').read_text(encoding='utf-8'))
    assert set(visual['reviewed_sha256'])=={sha(ROOT/n) for n in screens} and visual['private_records_seen'] is False
    assert git('rev-parse','HEAD').decode().strip()==HEAD and sha(ROOT/'.git/index')==baseline['.git/index']
    return {'milestone':'U5E','head':HEAD,'status':'READ_ONLY_ADMIN_ANALYSIS_IMPLEMENTED_WITH_DOCUMENTED_LIMITS',
        'exact_checkpoint_inventory':inventory,'modified_from_entry':MODIFIED,'new_paths':[n for n in inventory if n not in MODIFIED],
        'preexisting_tracked_modifications':sorted(entry),'baseline_paths':3268,'unchanged_baseline_paths':3266,'protected_academic_paths':23,
        'u5d_inventory_preserved':24,'protected_preferences_settings':'BYTE_IDENTICAL_UNSTAGED_EXCLUDED',
        'ga_scoring_operators_rng_fingerprints_migrations_checkpoints_saved_best_history':'UNCHANGED',
        'artifact_sha256':hashes,'proposed_git_blob_oids':oids,'screenshots':screens,'privacy':'PASS patterns, private-name comparison and visual review',
        'whitespace':'PASS','git_index_head':'UNCHANGED','staged_files':[],
        'attempts':attempts,'snapshot_attempts':[{'path':p.relative_to(ROOT).as_posix(),'complete':json.loads(p.read_text(encoding='utf-8'))['complete'],
            'results':json.loads(p.read_text(encoding='utf-8'))['results']} for p in proofs],
        'final_worktree_checks':final,'final_snapshot':proofs[-1].relative_to(ROOT).as_posix(),'snapshot_checks':snapshot_checks,
        'focused_backend':20,'backend_regressions':145,'engine_regressions':34,'frontend_focused':17,'frontend_regressions':166,
        'u5e_browser_scenarios':16,'u5a_u5b_u5c_browser_scenarios':39,
        'browser_scope':'Actual Edge/React with CDP-intercepted fictional HTTP; no live FastAPI/database browser journey',
        'backend_scope':'Actual FastAPI ASGI TestClient with fictional principals, temporary history stores and forbidden Engine.connect; no real sessions',
        'authority':'Production institutional activation and Chair analysis access remain BLOCKED; no CURRENT eligibility granted',
        'limits':['V1 recorded snapshots only; no V2 or transient loaded candidate analysis', 'No institutional cohort completeness or current optimizer consumption proof',
            'Progress has explicit gaps; comparison restricted to same-run matching policy/context/configuration',
            'Bounded 200 run directories, 500 faculty, 50 observations per window; no performance claim or full accessibility audit',
            'Historical failed build/lint/browser/snapshot attempts and combined-suite timeout retained; final split suites passed',
            'No PostgreSQL operation, staging, commit or push; partial staging required for mixed FitnessAnalysis page']}


if __name__=='__main__':
    record=sys.argv[1:]==['--record'];finding=inspect(record);path=BASE/'manifest.json'
    if record:
        finding['recorded_at']=datetime.now().astimezone().isoformat()
        with path.open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(finding,indent=2)+'\n')
    else:
        old=json.loads(path.read_text(encoding='utf-8'))
        for k,v in finding.items():assert old[k]==v,'MANIFEST_MISMATCH_STOP: '+k
    print(json.dumps({'status':'U5E_AUDIT_PASSED','paths':len(finding['exact_checkpoint_inventory']),'hashes':len(finding['artifact_sha256']),
        'baseline_unchanged':3266,'screenshots':len(finding['screenshots']),'staged':False}))
