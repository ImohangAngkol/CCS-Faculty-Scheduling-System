"""Read-only checkpoint replay; --seal refreshes explicitly authorized metadata.

Never stages, commits, connects to a database, or modifies application files.
"""
from datetime import datetime
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4];BASE=Path(__file__).resolve().parent;PARENT=BASE.parent
HEAD='1299d000a205287dbfc2d306decc427c98c2ee6e'
ROUTE='frontend/src/routes/AppRoutes.tsx'
SEALS=['docs/testing/dashboard-u5pc/manifest.json','docs/testing/dashboard-u5pc/staging-plan.json']


def git(*args):return subprocess.check_output(['git','-c','core.autocrlf=false',*args],cwd=ROOT,
    env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')


def inspect(seal=False,committed=False):
    before=git('rev-parse','HEAD').decode().strip()
    assert git('branch','--show-current').strip()==b'main'
    assert (git('rev-parse','HEAD^').decode().strip()==HEAD if committed else before==HEAD)
    old=load(BASE/'original-manifest.json');plan0=load(BASE/'original-staging-plan.json');r=load(BASE/'reconciliation.json')
    entry=load(PARENT/'entry-review.json');baseline=load(PARENT/'preservation-baseline.json')
    source=load(BASE/'source-byte-snapshots.json')
    parent=bytes.fromhex(source['snapshots']['HEAD-AppRoutes.tsx']['bytes_hex'])
    original=bytes.fromhex(source['snapshots']['original-staged-AppRoutes.tsx']['bytes_hex'])
    replacement=bytes.fromhex(source['snapshots']['replacement-AppRoutes.tsx']['bytes_hex'])
    assert git('show',HEAD+':'+ROUTE)==parent and original.replace(b'\r\n',b'\n')==replacement
    assert original.count(b'\r\n')==240 and b'\r' not in replacement
    assert blob(parent)==r['original_HEAD_blob'] and blob(original)==r['original_staged_blob'] and blob(replacement)==r['replacement_staged_blob']
    assert sha((ROOT/ROUTE).read_bytes())==r['working_tree_sha256_before']==r['working_tree_sha256_after_required']
    assert sha(parent)==r['original_HEAD_sha256'] and sha(replacement)==r['replacement_sha256']
    for key,value in source['snapshots'].items():assert sha(bytes.fromhex(value['bytes_hex']))==value['sha256']
    archived_patch=bytes.fromhex(source['original_reviewed_patch']['bytes_hex'])
    assert sha(archived_patch)==source['original_reviewed_patch']['sha256']==load(BASE/'repair-verification.json')['patch_sha256']
    for a in r['HEAD_patch_additions']:assert replacement.decode().splitlines()[a['line']-1]==a['text']
    assert parent.decode().splitlines()[125].endswith(' ') and replacement.decode().splitlines()[127].endswith(' ')
    # Every original artifact remains intact. The old plan resolves to its exact
    # archive; the old route hash resolves to the untouched working-tree bytes.
    for name,h in old['artifact_sha256'].items():
        raw=(BASE/'original-staging-plan.json').read_bytes() if name==SEALS[1] else (ROOT/name).read_bytes()
        assert sha(raw)==h,'HISTORICAL_ARTIFACT_STOP: '+name
    assert blob((BASE/'original-manifest.json').read_bytes())==r['original_other_98_staged_blobs'][SEALS[0]]
    assert blob((BASE/'original-staging-plan.json').read_bytes())==r['original_other_98_staged_blobs'][SEALS[1]]
    assert len(baseline)==5005
    for name,h in baseline.items():
        if name=='.git/index':continue
        assert sha((ROOT/name).read_bytes())==old['artifact_sha256'].get(name,h),'PRESERVATION_STOP: '+name
    for prefix in ['backend/data/','backend/saved_chromosomes/','backend/run_checkpoints/','backend/generation_snapshots/',
                   'backend/run_input_receipts_v1/','backend/run_provenance_v1/','backend/constrained_runs_v2/']:
        assert {p.relative_to(ROOT).as_posix() for p in (ROOT/prefix).rglob('*') if p.is_file()}=={p for p in baseline if p.startswith(prefix)}
    prior=0
    for key,total in old['preservation']['prior_artifact_references'].items():
        record=load(PARENT.parent/('dashboard-'+key)/'manifest.json');assert len(record['artifact_sha256'])==total
        for name,h in record['artifact_sha256'].items():assert sha((ROOT/name).read_bytes())==h,'PRIOR_REFERENCE_STOP: '+name
        prior+=total
    assert prior==1377
    added=sorted(p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file())
    inventory=sorted(plan0['exact_checkpoint_inventory']+added);assert len(set(inventory))==len(inventory)
    assert not any(n.startswith('backend/data/') for n in inventory)
    def intended(name):return replacement if name==ROUTE else (ROOT/name).read_bytes()
    for name,expected in r['original_other_98_staged_blobs'].items():
        if name not in SEALS:assert blob(intended(name))==expected,'OTHER_STAGED_CONTENT_STOP: '+name
    attempts=[]
    for p in sorted(BASE.glob('*/command.json')):
        row=load(p);assert row['exit_code']==0 and row['route_staged_blob']==r['replacement_staged_blob']
        assert row['route_sha256']==sha(replacement)
        for name,oid in row['exact_index_frontend_blobs'].items():
            raw=git('show',('HEAD:' if committed else ':')+name);assert blob(raw)==oid,'TESTED_INDEX_SOURCE_STOP: '+name
        attempts.append(dict(path=p.relative_to(ROOT).as_posix(),selection=row['selection'],exit_code=row['exit_code']))
    assert {a['selection'] for a in attempts}=={'contracts-all','build','bundle','lint','preview-browser'}
    contract=load(ROOT/next(a['path'] for a in attempts if a['selection']=='contracts-all'))
    assert re.search(r'\u2139 pass 361\b',contract['stdout']) and re.search(r'\u2139 fail 0\b',contract['stdout'])
    browser=ROOT/next(a['path'] for a in attempts if a['selection']=='preview-browser')
    results=load(browser.with_name('browser-results.json'))
    assert len(results['scenarios'])==12 and all(v['status']=='PASS' for v in results['scenarios'])
    assert not results['runtime_errors'] and all(v['method']=='GET' for v in results['requests'])
    with (ROOT/'backend/data/Faculty.csv').open(encoding='utf-8-sig',newline='') as f:
        names=[v['Faculty'].strip().casefold() for v in csv.DictReader(f) if len(v.get('Faculty','').strip())>=6]
    patterns=[r'eyJ[A-Za-z0-9_-]{18,}',r'[A-Za-z0-9_-]{80,}\.[A-Za-z0-9_-]{8,}',r'(?i)postgres(?:ql)?(?:\+\w+)?://[^\s"\']+',
        r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'(?i)bearer\s+[A-Za-z0-9._~-]{20,}',
        r'''(?i)['"]?(?:X-CSRF-Token|ccs_session|csrf_token|password)['"]?\s*[:=]\s*['"][A-Za-z0-9_-]{24,}''']
    png=runpy.run_path(str(ROOT/'docs/testing/dashboard-u5o/audit_evidence.py'))['png'];images={}
    for name in inventory:
        raw=intended(name)
        if name.endswith('.png'):images[name]=png(ROOT/name);continue
        text=raw.decode('utf-8')
        if name=='frontend/tests/researchConsole.browser.test.mjs':text=text.replace('csrf_token:'+"'fictional-not-a-credential'","csrf_token:'[FICTIONAL_MARKER]'")
        assert not any(re.search(p,text) for p in patterns),'PRIVACY_STOP: '+name
        assert not any(n in text.casefold() for n in names),'PRIVATE_NAME_STOP: '+name
        if name in added:assert all(l.rstrip()==l for l in text.splitlines()),'NEW_EVIDENCE_WHITESPACE_STOP: '+name
        if name.endswith('.py'):compile(text,name,'exec')
    review=load(BASE/'screenshot-review.json')
    assert review['privacy_reviewed'] and set(review['files'])=={p.relative_to(ROOT).as_posix() for p in BASE.rglob('*.png')}
    for name,h in review['files'].items():assert sha((ROOT/name).read_bytes())==h
    for n,v in source['snapshots'].items():
        decoded=bytes.fromhex(v['bytes_hex']).decode();assert not any(re.search(p,decoded) for p in patterns) and not any(s in decoded.casefold() for s in names)
    git('-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check')
    fsck=git('fsck','--no-reflogs').decode();assert all(l.startswith('dangling ') for l in fsck.splitlines())
    visible=set(git('ls-files','--others','--exclude-standard','-z').decode().strip('\0').split('\0'))-{''}
    staged=set(git('diff','--cached','--name-only','-z').decode().strip('\0').split('\0'))-{''}
    if seal:
        assert staged==set(plan0['exact_checkpoint_inventory']) and visible==set(entry['untracked_files'])|set(added)
        assert (PARENT/'manifest.json').read_bytes()==(BASE/'original-manifest.json').read_bytes()
        assert (PARENT/'staging-plan.json').read_bytes()==(BASE/'original-staging-plan.json').read_bytes()
        plan=dict(plan0);plan.update(exact_checkpoint_inventory=inventory,new_files=len(inventory)-3,
            documentation_tooling_evidence=sorted(set(inventory)-set(plan0['application_tests'])),partial_staging_required=True,
            index_only_overrides={ROUTE:dict(original_staged_blob=r['original_staged_blob'],replacement_staged_blob=r['replacement_staged_blob'],working_tree_sha256=r['working_tree_sha256_before'])},
            proposed_blob_oids={n:blob(intended(n)) for n in inventory if n not in SEALS},
            instructions='Authorized reconciled U5PC checkpoint. Keep the staged AppRoutes replacement; NEVER git add that working-tree file. Stage only new reconciliation files and refreshed manifest/plan. Original other 96 content blobs must remain identical; original manifest/plan are archived. Verify all current staged blobs and whitespace. No broad staging or automatic working-tree normalization.',
            proposed_messages=['feat(ga): add read-only fictional research console (U5P-C)'])
        write(PARENT/'staging-plan.json',plan)
        manifest=dict(old);manifest.update(exact_changed_and_new_file_inventory=inventory,new_files=len(inventory)-3,
            checkpoint_reconciliation=dict(recorded_at=datetime.now().astimezone().isoformat(),original_inventory=99,current_inventory=len(inventory),additional_evidence_files=len(added),
                original_manifest='docs/testing/dashboard-u5pc/checkpoint-reconciliation/original-manifest.json',original_plan='docs/testing/dashboard-u5pc/checkpoint-reconciliation/original-staging-plan.json',
                report='docs/testing/dashboard-u5pc/checkpoint-reconciliation/README.md',original_staged_blob=r['original_staged_blob'],replacement_staged_blob=r['replacement_staged_blob'],
                patch_sha256=sha((BASE/'AppRoutes.index-only.patch').read_bytes()),other_98_identical_during_repair=True,subsequent_metadata_refreshes=SEALS,
                working_tree_sha256=r['working_tree_sha256_before'],current_staged_frontend_tests=attempts,frontend_contracts=361,intercepted_browser_scenarios=12,
                backend_and_live_FastAPI_tests='Original byte-matched evidence reviewed; not freshly rerun for LF-only frontend change',privacy='PASS',whitespace='PASS',git_integrity='PASS'),
            working_tree_sha256_exceptions={ROUTE:r['working_tree_sha256_before']},artifact_hash_semantics='Intended committed bytes. AppRoutes staged LF differs from unchanged working-tree bytes by CR before LF only; recorded exception must not be restaged.',
            artifact_sha256={n:sha(intended(n)) for n in inventory if n!=SEALS[0]})
        manifest['preservation']={**old['preservation'],'index_unchanged':False,'index_change_scope':'Authorized exact U5PC checkpoint and AppRoutes LF reconciliation only; original implementation baseline remains archived'}
        write(PARENT/'manifest.json',manifest)
    else:
        manifest=load(PARENT/'manifest.json');plan=load(PARENT/'staging-plan.json')
        assert manifest['exact_changed_and_new_file_inventory']==plan['exact_checkpoint_inventory']==inventory
        for n,h in manifest['artifact_sha256'].items():assert sha(intended(n))==h,'SEALED_HASH_STOP: '+n
        for n,h in plan['proposed_blob_oids'].items():assert blob(intended(n))==h,'SEALED_BLOB_STOP: '+n
        assert visible==set(entry['untracked_files'])
        if committed:
            assert not staged and sorted(git('diff-tree','--no-commit-id','--name-only','-r','HEAD').decode().splitlines())==inventory
        else:assert staged==set(inventory)
        for n in inventory:assert git('show',('HEAD:' if committed else ':')+n)==intended(n),'ACTUAL_BLOB_STOP: '+n
    raw_unstaged=set(git('diff','--name-only').decode().splitlines())
    assert raw_unstaged==set(entry['tracked_modifications'])|{ROUTE}|(set(SEALS) if seal else set())
    assert git('rev-parse','HEAD').decode().strip()==before
    print(json.dumps(dict(status='PASS',mode='sealed' if seal else 'committed' if committed else 'staged',inventory=len(inventory),new_files=len(inventory)-3,artifact_hashes=len(inventory)-1,
        original_baseline_preserved=5002,prior_artifact_references=prior,working_tree_AppRoutes_unchanged=True,other_original_content_blobs_unchanged=96,
        frontend_contracts=361,intercepted_Edge_scenarios=12,unrelated_tracked=11,unrelated_untracked=958,production='BLOCKED')))


if __name__=='__main__':inspect('--seal' in sys.argv,'--committed' in sys.argv)
