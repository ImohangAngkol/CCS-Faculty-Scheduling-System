"""Read-only replay; --record creates new U5PC seals, never stages Git."""
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

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
HEAD='1299d000a205287dbfc2d306decc427c98c2ee6e'
REPORT='docs/dashboard-u5pc-read-only-research-console.md'
MODIFIED=['backend/main.py','frontend/src/routes/AppRoutes.tsx','frontend/src/layouts/AdminLayout.tsx']
CODE=['backend/services/ga_research_observation.py','backend/routers/research_observations.py',
 'backend/tests/test_research_observations.py','backend/tests/test_research_console_live.py','backend/tests/research_console_support.py',
 'frontend/src/api/researchObservations.ts','frontend/src/pages/ResearchConsole.tsx',
 'frontend/tests/researchObservations.test.mjs','frontend/tests/researchObservations.fixtures.mjs',
 'frontend/tests/researchConsole.driver.mjs','frontend/tests/researchConsole.browser.test.mjs',
 'frontend/tests/researchConsole.live.mjs','frontend/tests/researchConsole.host.mjs']
REQUIRED={'observations':24,'live':2,'parity':5,'legacy':10,'regressions':99,'receipts':36,'consumption':39}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),*args],cwd=ROOT,
    env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)
def new(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
def counts(row):
    d={}
    for n,k in re.findall(r'(\d+) (passed|failed|errors?|skipped|deselected)',row['stdout']):d[k]=int(n)
    for k,n in re.findall(r'\u2139 (tests|pass|fail|skipped) (\d+)',row['stdout']):d[k]=int(n)
    return d


def inspect(record=False):
    assert git('rev-parse','HEAD').decode().strip()==HEAD and git('branch','--show-current').strip()==b'main'
    assert not git('diff','--cached','--name-only').strip()
    baseline=json.loads((BASE/'preservation-baseline.json').read_text());assert len(baseline)==5005
    changed=[p for p,h in baseline.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    assert set(changed)==set(MODIFIED),'UNEXPECTED_PRESERVATION_CHANGE: '+str(changed)
    entry=json.loads((BASE/'entry-review.json').read_text())
    assert len(entry['tracked_modifications'])==11 and len(entry['untracked_files'])==958
    assert sorted(git('diff','--name-only').decode().splitlines())==sorted(MODIFIED+entry['tracked_modifications'])
    # Invert only the five approved insertions in memory. This verifies all
    # original bytes, including existing whitespace/newlines, without edits.
    replacements={
      'backend/main.py':[(b'from routers import schedule_applications',b'from routers import schedule_applications\r\nfrom routers import research_observations'),(b'app.include_router(schedule_applications.router)',b'app.include_router(schedule_applications.router)\r\napp.include_router(research_observations.router)')],
      'frontend/src/routes/AppRoutes.tsx':[(b'import ScheduleApplications from "../pages/admin/ScheduleApplications";',b'import ScheduleApplications from "../pages/admin/ScheduleApplications";\r\nimport ResearchConsole from "../pages/ResearchConsole";'),(b'<Route path="/schedule-applications" element={<ScheduleApplications />} />',b'<Route path="/schedule-applications" element={<ScheduleApplications />} />\r\n        <Route path="/research/runs" element={<ResearchConsole />} />')],
      'frontend/src/layouts/AdminLayout.tsx':[(b'const adminItems = [',b'const adminItems = [\r\n  {label: "Research observations", path: "/research/runs"},')]}
    for name,pairs in replacements.items():
        raw=(ROOT/name).read_bytes()
        for old,added in pairs:assert raw.count(added)==1;raw=raw.replace(added,old)
        assert hashlib.sha256(raw).hexdigest()==baseline[name],'UNRELATED_INTEGRATION_EDIT_STOP: '+name
    academic=[p for p in baseline if p.startswith('backend/data/')];assert len(academic)==23
    for prefix in ['backend/data/','backend/saved_chromosomes/','backend/run_checkpoints/','backend/generation_snapshots/',
                   'backend/run_input_receipts_v1/','backend/run_provenance_v1/','backend/constrained_runs_v2/']:
        actual={p.relative_to(ROOT).as_posix() for p in (ROOT/prefix).rglob('*') if p.is_file()}
        assert actual=={p for p in baseline if p.startswith(prefix)},'PROTECTED_MEMBERSHIP_STOP: '+prefix
    references={}
    for key in ['u5g','u5h','u5i','u5j','u5k','u5l','u5m','u5n','u5o','u5pa','u5pb']:
        old=json.loads((BASE.parent/('dashboard-'+key)/'manifest.json').read_text())
        for p,h in old['artifact_sha256'].items():assert sha(ROOT/p)==h,'PRIOR_ARTIFACT_STOP: '+p
        references[key]=len(old['artifact_sha256'])
    assert sum(references.values())==1377
    seals=['docs/testing/dashboard-u5pc/manifest.json','docs/testing/dashboard-u5pc/staging-plan.json']
    content=sorted(MODIFIED+CODE+[REPORT]+[p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file() and p.name not in {'manifest.json','staging-plan.json'}])
    inventory=sorted(content+seals);assert len(inventory)==len(set(inventory))
    untracked=set(git('ls-files','--others','--exclude-standard','-z').decode().strip('\0').split('\0'))
    expected=set(inventory)-set(MODIFIED)-(set(seals) if record else set())
    assert untracked==set(entry['untracked_files'])|expected,'UNAPPROVED_UNTRACKED_PATH_STOP'
    attempts=[]
    for p in sorted(BASE.glob('*/command.json')):
        row=json.loads(p.read_text());attempts.append(dict(path=p.relative_to(ROOT).as_posix(),selection=row['selection'],exit_code=row['exit_code'],
            counts=counts(row),elapsed_seconds=row['elapsed_seconds']))
    latest={key:[r for r in attempts if r['selection']==key][-1] for key in REQUIRED}
    for key,total in REQUIRED.items():
        r=latest[key];assert r['exit_code']==0 and r['counts'].get('passed')==total,'FINAL_TEST_STOP: '+key
        source=json.loads((ROOT/r['path']).read_text())['source_sha256']
        # Backend regressions do not evaluate frontend/tooling. Final live test
        # independently covers the complete current API/page and handoff bytes.
        if key=='live':names=[n for n in source if n!='backend/tests/test_research_observations.py']
        elif key=='observations':names=[n for n in source if n in MODIFIED[:1]+CODE[:3]]
        else:names=[n for n in source if n in MODIFIED[:1]+CODE[:2]]
        # The live module imports the unchanged files() helper from the unit
        # module. Its newly added RNG assertions are exercised by the final
        # independent 24-case observation suite, not by GA regression selectors.
        for name in names:assert sha(ROOT/name)==source[name],'FINAL_SOURCE_STOP: '+key+' '+name
    bridge=[r for r in attempts if r['selection']=='bridge'][-1]
    assert bridge['exit_code']==1 and bridge['counts'].get('passed')==50 and bridge['counts'].get('failed')==1
    failure=json.loads((ROOT/bridge['path']).read_text())['stdout']
    assert 'test_original_http_and_production_providers_unmodified' in failure
    for key in ['contracts-all','build','bundle','lint','preview-browser']:
        row=[r for r in attempts if r['selection']==key][-1];assert row['exit_code']==0,'FINAL_FRONTEND_STOP: '+key
        proof=json.loads((ROOT/row['path']).read_text())
        for name,h in proof['ui_overlay_sha256'].items():
            if name.endswith(('.ts','.tsx')):assert sha(ROOT/name)==h,'FINAL_FRONTEND_SOURCE_STOP: '+name
    assert [r for r in attempts if r['selection']=='contracts-all'][-1]['counts']['pass']==361
    live=(ROOT/latest['live']['path']).parent
    observed=json.loads((live/'live-browser-results.json').read_text())
    assert len(observed['scenarios'])==9 and all(s['status']=='PASS' for s in observed['scenarios']) and not observed['HTTP_interception']
    assert observed['requests'] and all(r['method']=='GET' for r in observed['requests']) and not observed['runtime_errors']
    assert all(json.loads((live/'live-preservation.json').read_text())[k] for k in ['research_files_byte_identical','API_reconstruction_equal','auth_database_separate'])
    assert json.loads((live/'operator-handoff.json').read_text())['owned_stop_verified']
    intercepted=(ROOT/[r for r in attempts if r['selection']=='preview-browser'][-1]['path']).parent
    browser=json.loads((intercepted/'browser-results.json').read_text());assert len(browser['scenarios'])==12 and all(s['status']=='PASS' for s in browser['scenarios'])
    legacy=(ROOT/latest['legacy']['path']).parent;fixtures=[json.loads((legacy/f'fixture-{i}.json').read_text()) for i in range(3)]
    assert all(f['real_checkpoint_write_load_resume'] and f['RNG_and_schedule_equivalent'] for f in fixtures)
    old_engine=json.loads((BASE.parent/'dashboard-u5pa/manifest.json').read_text())['checkpoint']['current_fixture_engine']
    assert {f['engine_fingerprint'] for f in fixtures}=={old_engine}
    parity=json.loads(((ROOT/bridge['path']).parent/'U5K-nonzero-worker-parity.json').read_text())
    assert parity['original_fitness']==parity['worker_fitness']==455.0 and parity['global_rng_unchanged'] and parity['schedule_fitness_history_breakdown_faculty_and_rng_equal']
    with (ROOT/'backend/data/Faculty.csv').open(encoding='utf-8-sig',newline='') as f:
        names=[r['Faculty'].strip().casefold() for r in csv.DictReader(f) if len(r.get('Faculty','').strip())>=6]
    patterns=[r'eyJ[A-Za-z0-9_-]{18,}',r'[A-Za-z0-9_-]{80,}\.[A-Za-z0-9_-]{8,}',r'(?i)postgres(?:ql)?(?:\+\w+)?://[^\s"\']+',
        r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'(?i)bearer\s+[A-Za-z0-9._~-]{20,}',
        r'''(?i)['"]?(?:X-CSRF-Token|ccs_session|csrf_token|password)['"]?\s*[:=]\s*['"][A-Za-z0-9_-]{24,}''']
    png=runpy.run_path(str(ROOT/'docs/testing/dashboard-u5o/audit_evidence.py'))['png'];images={}
    for name in content:
        p=ROOT/name
        if p.suffix=='.png':images[name]=png(p);continue
        text=p.read_text(encoding='utf-8')
        if name=='frontend/tests/researchConsole.browser.test.mjs':text=text.replace("csrf_token:"+"'fictional-not-a-credential'","csrf_token:'[FICTIONAL_MARKER]'")
        assert not any(re.search(pattern,text) for pattern in patterns),'PRIVACY_STOP: '+name
        assert not any(n in text.casefold() for n in names),'PRIVATE_NAME_STOP: '+name
        if name not in MODIFIED:assert not any(line.rstrip()!=line for line in text.splitlines()),'WHITESPACE_STOP: '+name
        if p.suffix=='.py':compile(text,name,'exec')
    review=json.loads((BASE/'screenshot-review.json').read_text());assert review['privacy_reviewed'] and set(review['files'])==set(images)
    for name,h in review['files'].items():assert sha(ROOT/name)==h
    git('-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--check');git('-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check');integrity=git('fsck','--no-reflogs').decode()
    assert all(line.startswith('dangling ') for line in integrity.splitlines())
    blobs={p:hashlib.sha1(b'blob '+str((ROOT/p).stat().st_size).encode()+b'\0'+(ROOT/p).read_bytes()).hexdigest() for p in content}
    plan=dict(head=HEAD,exact_checkpoint_inventory=inventory,existing_modified_files=MODIFIED,new_files=len(inventory)-3,
        application_tests=MODIFIED+CODE,documentation_tooling_evidence=sorted(set(inventory)-set(MODIFIED+CODE)),
        proposed_blob_oids=blobs,excluded_tracked_modifications=entry['tracked_modifications'],excluded_untracked_files=entry['untracked_files'],
        core_autocrlf=False,partial_staging_required=False,
        instructions='PROPOSAL ONLY. No staging authorized in U5PC. These three modified files were clean at entry; whole-file selective staging excludes the original eleven user modifications and 958 unrelated untracked paths. Test current committed U5PB plus only this overlay, with original source-byte release recipe. Never stage broad directories. Preserve raw bytes and reverify blobs. Calculate plan/manifest blob IDs after sealing; no circular self-hash.',
        proposed_messages=['feat(ga): add read-only isolated research console (U5P-C)','docs(testing): archive U5P-C console and operator qualification'])
    manifest=dict(milestone='U5P-C',head=HEAD,recorded_at=datetime.now().astimezone().isoformat(),
        status='ISOLATED_READ_ONLY_CONSOLE_QUALIFIED_WITH_EXPLICIT_HISTORICAL_TEST_MISMATCH',
        exact_changed_and_new_file_inventory=inventory,existing_files_modified=MODIFIED,new_files=len(inventory)-3,
        final_python_counts=REQUIRED,bridge_regression=dict(passed=50,failed=1,reason='Frozen U5PB expectation of no research routes; new GET-only routes intentionally added. Original test preserved.'),
        selected_python_passes=sum(REQUIRED.values())+50,frontend_contracts=361,real_Edge_FastAPI_SQLite_scenarios=9,
        intercepted_HTTP_Edge_scenarios=12,operator_handoff='Actual separate host start and owned-stop passed',
        TypeScript='PASS',production_build='PASS',focused_lint='PASS',attempts=attempts,tests_freshly_executed=True,
        original_fitness=455.0,original_engine_fingerprint=old_engine,current_checkpoint_creation_load_continuation=True,
        preservation=dict(baseline_paths=5005,unchanged=5002,authorized_changes=3,academic_files=23,protected_JSON_unchanged=True,
            original_unrelated_tracked=11,original_unrelated_untracked=958,index_unchanged=True,prior_artifact_references=references),
        privacy='PASS; exact intercepted noncredential marker exception; no raw DB/bundle/checkpoint/key/receipt/password/cookie archived',
        screenshot_integrity=images,whitespace='PASS',git_integrity='PASS',
        production_admission='BLOCKED',institutional_saved_best_promotion='BLOCKED',continuous_UI='DISABLED',active_restore=False,seven_day='NO_GO',
        checkpoint_readiness='SELECTIVE_REVIEW_READY; NOT_A_PRODUCTION_ACTIVATION; NOT_REPOSITORY_WIDE_GREEN',
        artifact_sha256={p:sha(ROOT/p) for p in content})
    if record:
        new(BASE/'staging-plan.json',plan);manifest['artifact_sha256'][seals[1]]=sha(BASE/'staging-plan.json');new(BASE/'manifest.json',manifest)
    else:
        sealed=json.loads((BASE/'manifest.json').read_text());assert sealed['exact_changed_and_new_file_inventory']==inventory
        for p,h in sealed['artifact_sha256'].items():assert sha(ROOT/p)==h,'SEALED_HASH_STOP: '+p
    print(json.dumps(dict(status='PASS',baseline_unchanged=5002,intended_modified=3,inventory=len(inventory),artifact_hashes=len(inventory)-1,
        selected_python_passes=sum(REQUIRED.values())+50,historical_expectation_failures=1,frontend_contracts=361,prior_references=1377,production='BLOCKED')))


if __name__=='__main__':inspect('--record' in sys.argv)
