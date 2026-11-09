"""Read-only preservation/privacy replay. --record seals new plan and manifest.

No application import, institutional connection, staging or evidence rewriting.
"""
from datetime import datetime
import ast
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
HEAD='ec21a67efed82f085d5e2134ef6002cf5ac69eed'
REPORT='docs/dashboard-u5pa-saved-best-preview-repairs.md'
MODIFIED=['backend/services/chromosome_service.py','frontend/src/api/scheduleApplications.ts','frontend/src/pages/admin/ScheduleApplications.tsx']
NEW_CODE=['backend/services/saved_best_policy.py','backend/tests/test_saved_best_context.py',
    'frontend/tests/savedBestPreviewRepair.test.mjs','frontend/tests/savedBestPreview.browser.test.mjs']
REQUIRED={'saved-best':48,'dashboard-all':458,'backend-regressions':99,'race':19,'receipts':36,
    'consumption':39,'bundle-tests':32,'admission':50,'qualification':49,'identity':16,'preference-scope':3,
    'analysis':20,'readiness':20,'supervised-smoke':1,'worker':32,'parity':5,'legacy':10,
    'recovery':40,'parent':7,'v2-engine':30,'v2-api':18,'repair-live':1}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),*args],cwd=ROOT,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)
def new(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(value,indent=2)+'\n')


def inspect(record=False):
    assert git('branch','--show-current').strip()==b'main'
    assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('diff','--cached','--name-only').strip()
    baseline=json.loads((BASE/'preservation-baseline.json').read_text());assert len(baseline)==4658
    changed=[p for p,v in baseline.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=v]
    assert set(changed)==set(MODIFIED),'UNEXPECTED_BASELINE_CHANGE_STOP: '+str(changed)
    entry=json.loads((BASE/'entry-review.json').read_text())
    assert len(entry['tracked_modifications'])==11 and len(entry['untracked_files'])==958
    assert sorted(git('diff','--name-only').decode().splitlines())==sorted(MODIFIED+entry['tracked_modifications'])
    for prefix in ['backend/data/','backend/run_checkpoints/','backend/saved_chromosomes/','backend/run_input_receipts_v1/','backend/run_provenance_v1/','backend/constrained_runs_v2/']:
        expected={p for p in baseline if p.startswith(prefix)}
        actual={p.relative_to(ROOT).as_posix() for p in (ROOT/prefix).rglob('*') if p.is_file()}
        assert actual==expected,'PROTECTED_TREE_MEMBERSHIP_STOP: '+prefix
    prior={}
    for name in ['u5g','u5h','u5i','u5j','u5k','u5l','u5m','u5n','u5o']:
        old=json.loads((BASE.parent/('dashboard-'+name)/'manifest.json').read_text())
        for p,v in old['artifact_sha256'].items():assert sha(ROOT/p)==v,'PRIOR_ARTIFACT_STOP: '+p
        prior[name]=len(old['artifact_sha256'])
    assert sum(prior.values())==1029
    newfiles=sorted(NEW_CODE+[REPORT]+[p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file() and p.name not in {'manifest.json','staging-plan.json'}])
    inventory=sorted(MODIFIED+newfiles+['docs/testing/dashboard-u5pa/manifest.json','docs/testing/dashboard-u5pa/staging-plan.json'])
    visible=set(git('ls-files','--cached','--others','--exclude-standard','-z').decode().split('\0'))-{''}
    assert not visible-set(baseline)-set(inventory),'UNAPPROVED_NEW_PATH_STOP'
    assert set(entry['untracked_files'])<=visible
    assert not set(newfiles)&set(git('ls-files','-z').decode().split('\0')),'PREEXISTING_NEW_FILE_STOP'
    caller=(ROOT/MODIFIED[0]).read_text();helper=sha(ROOT/NEW_CODE[0]);assert helper in caller
    checkpoint=(ROOT/'backend/services/ga_checkpoint_service.py').read_text()
    assert '"chromosome_service.py"' in checkpoint and 'GA_CHECKPOINT_INPUT_CHANGED' in checkpoint
    assert sha(ROOT/'backend/services/ga_checkpoint_service.py')==baseline['backend/services/ga_checkpoint_service.py']
    # The only legacy helper function changed is automatic persistence.
    before=git('show',HEAD+':'+MODIFIED[0]).decode();after=(ROOT/MODIFIED[0]).read_text()
    def without_save(text):
        tree=ast.parse(text);function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='save_best_if_better')
        lines=text.splitlines();return lines[:function.lineno-1]+lines[function.end_lineno:]
    assert without_save(before)==without_save(after),'UNRELATED_CHROMOSOME_EDIT_STOP'
    old=runpy.run_path(str(ROOT/'docs/testing/dashboard-u5o/audit_evidence.py'))
    attempts=[]
    for path in sorted(BASE.rglob('*command.json')):
        row=json.loads(path.read_text());attempts.append(dict(path=path.relative_to(ROOT).as_posix(),selection=row['selection'],mode=row.get('ui_mode'),exit_code=row['exit_code'],counts=old['counts'](row)))
    latest={k:[r for r in attempts if r['selection']==k][-1] for k in REQUIRED}
    for key,total in REQUIRED.items():
        row=latest[key];assert row['exit_code']==0 and row['counts'].get('passed')==total,'FINAL_TEST_STOP: '+key
        proof=json.loads((ROOT/row['path']).with_name('snapshot-proof.json').read_text());assert proof['complete'] and proof['head']==HEAD and proof['no_actual_staging']
    # The final affected boundaries must carry the exact final source hashes.
    for key in ['saved-best','parity','legacy','consumption','repair-live']:
        proof=json.loads((ROOT/latest[key]['path']).with_name('snapshot-proof.json').read_text())
        for p in ['backend/services/chromosome_service.py','backend/services/saved_best_policy.py']:
            assert proof['source_sha256'][p]==sha(ROOT/p),'FINAL_SOURCE_NOT_TESTED_STOP: '+key+' '+p
    for mode,total in [('working-tree',388),('committed-plus-u5pa',342)]:
        row=[r for r in attempts if r['selection']=='contracts-all' and r['mode']==mode][-1]
        assert row['exit_code']==0 and row['counts']['pass']==total
        for key in ['build','bundle','lint']:
            assert [r for r in attempts if r['selection']==key and r['mode']==mode][-1]['exit_code']==0
    for mode in ['working-tree','committed-plus-u5pa']:
        row=[r for r in attempts if r['selection']=='preview-browser' and r['mode']==mode][-1]
        assert row['exit_code']==0 and row['counts']['pass']==11
    assert [r for r in attempts if r['selection']=='browser'][-1]['counts']['pass']==17
    archive=[r for r in attempts if r['selection']=='u5o-baseline'][-1]
    assert archive['exit_code']==0 and archive['counts']['passed']==3
    frozen=[r for r in attempts if r['selection']=='u5o-audit'][-1]
    assert frozen['exit_code']==1 and frozen['counts']['failed']==1 and frozen['counts']['passed']==2
    assert 'test_characterize_legacy_saved_best_comparison_without_provenance_gate' in json.loads((ROOT/frozen['path']).read_text())['stdout']
    live=(ROOT/latest['repair-live']['path']).parent/'captures';live_data=json.loads((live/'browser-results.json').read_text())
    assert len(live_data['scenarios'])==22 and all(s['result']=='PASS' for s in live_data['scenarios']) and not live_data['runtime_errors']
    assert (live.parent/'cache-isolation.json').is_file()
    legacy=(ROOT/latest['legacy']['path']).parent;fixtures=[json.loads((legacy/f'fixture-{i}.json').read_text()) for i in range(3)]
    assert all(r['real_checkpoint_write_load_resume'] and r['RNG_and_schedule_equivalent'] for r in fixtures)
    assert len({r['engine_fingerprint'] for r in fixtures})==1
    parity=json.loads(sorted(BASE.glob('*/U5K-nonzero-worker-parity.json'))[-1].read_text())
    assert parity['original_fitness']==parity['worker_fitness']==455.0 and parity['global_rng_unchanged']
    assert parity['schedule_fitness_history_breakdown_faculty_and_rng_equal']
    protected_names=[]
    with (ROOT/'backend/data/Faculty.csv').open(encoding='utf-8-sig',newline='') as stream:
        protected_names=[r['Faculty'].strip().casefold() for r in csv.DictReader(stream) if len(r.get('Faculty','').strip())>=6]
    patterns=[r'eyJ[A-Za-z0-9_-]{18,}',r'[A-Za-z0-9_-]{80,}\.[A-Za-z0-9_-]{8,}',r'(?i)postgres(?:ql)?(?:\+\w+)?://[^\s"\']+',
        r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'(?i)bearer\s+[A-Za-z0-9._~-]{20,}',
        r'''(?i)['"]?(?:X-CSRF-Token|ccs_session|csrf_token|password)['"]?\s*[:=]\s*['"][A-Za-z0-9_-]{24,}''']
    images={}
    for name in MODIFIED+newfiles:
        path=ROOT/name
        if path.suffix=='.png':images[name]=old['png'](path);continue
        text=path.read_text(encoding='utf-8')
        if name=='frontend/tests/savedBestPreview.browser.test.mjs':
            # Exact non-authenticating intercepted fixture constant, never sent
            # to any live server. No general token-pattern exemption.
            text=text.replace('csrf_token:' + "'fictional-not-a-credential'","csrf_token:'[FICTIONAL_MARKER]'")
        assert not any(re.search(pattern,text) for pattern in patterns),'PRIVACY_STOP: '+name
        assert not any(n in text.casefold() for n in protected_names),'PRIVATE_NAME_STOP: '+name
        if name not in MODIFIED:assert not any(l.rstrip()!=l for l in text.splitlines()),'WHITESPACE_STOP: '+name
        if path.suffix=='.py':compile(text,name,'exec')
    review=json.loads((BASE/'screenshot-review-final.json').read_text());assert review['privacy_reviewed'] and set(images)==set(review['files'])
    for name,value in review['files'].items():assert sha(ROOT/name)==value
    git('diff','--check');git('diff','--cached','--check');fsck=git('fsck','--no-reflogs').decode();assert all(s.startswith('dangling ') for s in fsck.splitlines())
    blobs={p:hashlib.sha1(b'blob '+str((ROOT/p).stat().st_size).encode()+b'\0'+(ROOT/p).read_bytes()).hexdigest() for p in MODIFIED+newfiles}
    plan=dict(baseline_head=HEAD,exact_checkpoint_inventory=inventory,existing_files_modified=MODIFIED,new_files=len(inventory)-3,mixed_files_to_stage=[],
        source_and_tests=MODIFIED+NEW_CODE,documentation_tooling_evidence=sorted(set(inventory)-set(MODIFIED+NEW_CODE)),
        proposed_blob_oids=blobs,excluded_preexisting_tracked_modifications=entry['tracked_modifications'],excluded_preexisting_untracked_files=958,
        core_autocrlf=False,cr_at_eol_whitespace=True,literal_pathspecs=True,
        messages=['fix(ga): reject unverified Saved Best replacements (U5P-A)','fix(dashboard): isolate application previews from history errors (U5P-A)','docs(testing): archive U5P-A repair qualification'],
        instructions='PROPOSAL ONLY; do not stage automatically. All three modified files were clean at entry, so whole-file selective staging is possible without including user edits. Exclude the original eleven modifications and 958 prior untracked files. Use exact literal paths and verify raw blobs with core.autocrlf=false; source-byte fingerprints require the tested bytes, including line endings. Review application diff with CRLF-aware whitespace/ignore-space-at-eol. Normalizing application bytes instead requires a fresh release/snapshot qualification, not reuse of a historical fingerprint. Calculate manifest/plan blob identities after sealing. The proposed frontend snapshot was independently qualified without unrelated UI overlays. No institutional promotion, active restore or continuous execution is authorized.')
    manifest=dict(milestone='U5P-A',head=HEAD,reviewed_at=datetime.now().astimezone().isoformat(),status='SCOPED_REPAIRS_QUALIFIED; TRUSTED_FIXED_HTTP_PROMOTION_UNAVAILABLE',
        exact_changed_and_new_file_inventory=inventory,new_files=len(inventory)-3,existing_files_modified=MODIFIED,
        preservation=dict(baseline_paths=4658,unchanged=4655,authorized_changes=3,academic_paths=23,protected_json_and_original_eleven_unchanged=True,index_unchanged=True,
            original_ga_math_rng_migrations_saved_best_checkpoints_history_unchanged=True,prior_artifact_references=prior,no_institutional_postgresql_operations=True),
        required_python_counts=REQUIRED,selected_python_passes=sum(REQUIRED.values()),historical_frozen_test_on_current_code=dict(passed=2,failed=1,assessment='Expected obsolete defect assertion, not silently weakened'),
        original_baseline_reproduction=dict(passed=3,scope='Pinned U5O committed source, no U5PA overlay'),
        frontend_contracts=dict(working_tree=388,checkpoint_snapshot=342),focused_browser_scenarios=10,legacy_intercepted_browser_scenarios=16,
        final_real_http_scenarios=22,prior_working_ui_real_http_observations=23,attempts=attempts,
        saved_best=dict(comparison='MINIMIZE; exact ties preserve incumbent',default_verifier='NONE; UNVERIFIED; NO_ARCHIVE_IO',helper_sha256=helper,
            cross_capture='Guarded complete evaluation-input equivalence proof required; bundle IDs/loaded hashes retained as provenance',production_promotion='BLOCKED_PENDING_TRUSTED_INPUT_SCOPE_AND_VERIFIER'),
        checkpoint=dict(current_fixture_engine=fixtures[0]['engine_fingerprint'],actual_creation_load_continuation=True,original_codec_source_unchanged=True,pre_release_resume='Strict fingerprint rejection; no migration, spoof or compatibility bypass'),
        parity=dict(original_and_worker_fitness=455.0,assignments_history_breakdown_faculty_rng_equal=True),
        privacy='PASS; exact noncredential intercepted-fixture literal exception documented in auditor; no live token/header/URL/raw store archived; genuine PNG visual/CRC/metadata checks',
        png_integrity=images,whitespace='PASS',git_integrity=dict(exit_code=0,dangling_objects=len(fsck.splitlines())),
        production_admission='BLOCKED',continuous_ui='DISABLED',active_restore='BLOCKED',seven_day='NO_GO',
        checkpoint_readiness='SELECTIVE_REVIEW_READY_WITH_EXPLICIT_PROVIDER_AND_HISTORICAL_TEST_LIMITS; NOT_A_PRODUCTION_ACTIVATION',
        artifact_sha256={p:sha(ROOT/p) for p in MODIFIED+newfiles})
    if record:
        new(BASE/'staging-plan.json',plan);manifest['artifact_sha256']['docs/testing/dashboard-u5pa/staging-plan.json']=sha(BASE/'staging-plan.json');new(BASE/'manifest.json',manifest)
    else:
        sealed=json.loads((BASE/'manifest.json').read_text());assert sealed['exact_changed_and_new_file_inventory']==inventory
        for p,value in sealed['artifact_sha256'].items():assert sha(ROOT/p)==value,'SEALED_HASH_STOP: '+p
    print(json.dumps(dict(status='PASS',baseline_unchanged=4655,expected_modified=3,new_files=len(inventory)-3,inventory=len(inventory),artifact_hashes=len(inventory)-1,
        selected_python_passes=sum(REQUIRED.values()),current_historical_assertion_failures=1,working_frontend=388,checkpoint_frontend=342,production_admission='BLOCKED')))


if __name__=='__main__':inspect('--record' in sys.argv)
