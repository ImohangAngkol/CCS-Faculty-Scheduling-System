"""Preservation/privacy/hash audit only; --record creates new U5PD seals.

No application imports, database connections, Git index changes or deployment.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
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
HEAD='3719af0734e395bf2b905a13ab6ccc1ca7dda5f9'
REPORT='docs/dashboard-u5pd-observation-continuity.md'
MODIFIED=['frontend/src/api/researchObservations.ts','frontend/src/pages/ResearchConsole.tsx']
CODE=['backend/services/ga_observation_freshness.py','backend/services/ga_research_continuity.py',
 'backend/tests/test_observation_continuity.py','backend/tests/test_observation_continuity_live.py',
 'frontend/src/services/researchFreshness.ts','frontend/tests/observationContinuity.test.mjs',
 'frontend/tests/observationContinuity.fixtures.mjs','frontend/tests/observationContinuity.browser.test.mjs',
 'frontend/tests/observationContinuity.live.mjs']
REQUIRED={'continuity':32,'observations':24,'parity':5,'legacy':10,'live':2,'regressions':99,'receipts':36,'consumption':39}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-c','core.autocrlf=false',*args],cwd=ROOT,
    env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)
def new(p,obj):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(obj,f,indent=2);f.write('\n')
def counts(row):
    d={}
    for n,k in re.findall(r'(\d+) (passed|failed|errors?|skipped|deselected)',row['stdout']):d[k]=int(n)
    for k,n in re.findall(r'\u2139 (tests|pass|fail|skipped) (\d+)',row['stdout']):d[k]=int(n)
    return d


def inspect(record=False,record_blocked=False):
    assert git('rev-parse','HEAD').decode().strip()==HEAD and git('branch','--show-current').strip()==b'main'
    assert not git('diff','--cached','--name-only').strip()
    baseline=json.loads((BASE/'preservation-baseline.json').read_text());entry=json.loads((BASE/'entry-review.json').read_text())
    assert len(baseline)==5121 and len(entry['academic_paths'])==23
    changed=[p for p,h in baseline.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    assert set(changed)==set(MODIFIED),'UNEXPECTED_PRESERVATION_CHANGE: '+str(changed)
    assert len(entry['tracked_modifications'])==11 and len(entry['untracked_files'])==958
    # Entry status used the repository's working-tree conversion. Raw-byte
    # preservation above separately includes the inherited mixed-CRLF AppRoutes.
    names=subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,
        env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)
    assert set(names.decode().splitlines())==set(entry['tracked_modifications'])|set(MODIFIED)
    gap=json.loads((BASE/'preservation-coverage-gap.json').read_text())
    assert gap['status']=='BLOCKED_PRESERVATION_COVERAGE'
    omitted=gap['omitted_ignored_artifacts'];assert len(omitted)==8
    for name,item in omitted.items():assert name not in baseline and sha(ROOT/name)==item['current_sha256']
    extras=set()
    for prefix in ['backend/data/','backend/saved_chromosomes/','backend/run_checkpoints/','backend/generation_snapshots/',
                   'backend/run_input_receipts_v1/','backend/run_provenance_v1/','backend/constrained_runs_v2/']:
        actual={p.relative_to(ROOT).as_posix() for p in (ROOT/prefix).rglob('*') if p.is_file()}
        expected={p for p in baseline if p.startswith(prefix)}
        assert not expected-actual,'PROTECTED_MEMBER_MISSING: '+prefix
        extras.update(actual-expected)
    assert extras==set(omitted),'ADDITIONAL_PROTECTED_MEMBERSHIP_STOP'
    # Do not convert missing before-hashes into a passing preservation claim.
    # Only an explicitly blocked evidence seal is permitted for this finding.
    if record:assert record_blocked,'FULL_PRESERVATION_UNPROVEN; --record-blocked only'
    references=0;resolved=[]
    for key,total in entry['prior_artifacts'].items():
        old=json.loads((BASE.parent/('dashboard-'+key)/'manifest.json').read_text());assert len(old['artifact_sha256'])==total
        for name,h in old['artifact_sha256'].items():
            if sha(ROOT/name)!=h:
                assert key=='u5pc' and name in MODIFIED+['frontend/src/routes/AppRoutes.tsx']
                assert hashlib.sha256(git('show',HEAD+':'+name)).hexdigest()==h,'PRIOR_COMMITTED_SOURCE_STOP: '+name
                resolved.append(name)
            else:assert sha(ROOT/name)==h
        references+=total
    assert references==1495
    seals=['docs/testing/dashboard-u5pd/manifest.json','docs/testing/dashboard-u5pd/staging-plan.json']
    content=sorted(MODIFIED+CODE+[REPORT]+[p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file() and p.name not in {'manifest.json','staging-plan.json'}])
    inventory=sorted(content+seals);assert len(inventory)==len(set(inventory))
    untracked=set(git('ls-files','--others','--exclude-standard','-z').decode().strip('\0').split('\0'))-{''}
    expected=set(inventory)-set(MODIFIED)-(set(seals) if record else set())
    assert untracked==set(entry['untracked_files'])|expected,'UNAPPROVED_PATH_STOP'
    attempts=[]
    for p in sorted(BASE.glob('*/command.json')):
        row=json.loads(p.read_text());attempts.append(dict(path=p.relative_to(ROOT).as_posix(),selection=row['selection'],exit_code=row['exit_code'],counts=counts(row),elapsed_seconds=row['elapsed_seconds']))
    latest={k:[a for a in attempts if a['selection']==k][-1] for k in REQUIRED}
    for key,total in REQUIRED.items():
        a=latest[key];assert a['exit_code']==0 and a['counts'].get('passed')==total,'FINAL_TEST_STOP: '+key
        row=json.loads((ROOT/a['path']).read_text())
        relevant=list(row['source_sha256']) if key=='live' else CODE[:3] if key=='continuity' else CODE[:2]
        for name in relevant:assert sha(ROOT/name)==row['source_sha256'][name],'FINAL_SOURCE_STOP: '+key+' '+name
    bridge=[a for a in attempts if a['selection']=='bridge'][-1]
    assert bridge['exit_code']==1 and bridge['counts'].get('passed')==50 and bridge['counts'].get('failed')==1
    assert 'test_original_http_and_production_providers_unmodified' in json.loads((ROOT/bridge['path']).read_text())['stdout']
    for key in ['contracts-all','build','bundle','lint','preview-browser','legacy-browser']:
        a=[v for v in attempts if v['selection']==key][-1];assert a['exit_code']==0,'FRONTEND_STOP: '+key
        row=json.loads((ROOT/a['path']).read_text())
        for name,h in row['ui_overlay_sha256'].items():assert sha(ROOT/name)==h,'FINAL_UI_SOURCE_STOP: '+name
    assert [a for a in attempts if a['selection']=='contracts-all'][-1]['counts']['pass']==391
    live=(ROOT/latest['live']['path']).parent
    proof=json.loads((live/'real-api-offline-reconstruction.json').read_text())
    assert all(proof[k] for k in ['actual_TCP_FastAPI','actual_sessions','actual_SQLite','actual_native_optimizer','worker_completed_without_API','durable_observations_equal','read_only_research_bytes_identical'])
    live_browser=json.loads((live/'live-browser-results.json').read_text());assert len(live_browser['scenarios'])==9 and all(s['status']=='PASS' for s in live_browser['scenarios']) and not live_browser['HTTP_interception']
    assert json.loads((live/'live-preservation.json').read_text())['research_files_byte_identical']
    new_browser=(ROOT/[a for a in attempts if a['selection']=='preview-browser'][-1]['path']).parent
    browser=json.loads((new_browser/'browser-results.json').read_text());assert len(browser['scenarios'])==16 and all(s['status']=='PASS' for s in browser['scenarios']) and not browser['runtime_errors']
    assert all(r['method']=='GET' for r in browser['requests']) and len(browser['memory_samples'])==4
    old_browser=(ROOT/[a for a in attempts if a['selection']=='legacy-browser'][-1]['path']).parent
    assert all(s['status']=='PASS' for s in json.loads((old_browser/'browser-results.json').read_text())['scenarios'])
    parity=json.loads(((ROOT/bridge['path']).parent/'U5K-nonzero-worker-parity.json').read_text())
    assert parity['original_fitness']==parity['worker_fitness']==455.0 and parity['global_rng_unchanged'] and parity['schedule_fitness_history_breakdown_faculty_and_rng_equal']
    native=json.loads(((ROOT/bridge['path']).parent/'native-parent-interruption.json').read_text());assert native['parent_exit']==23 and native['post_restart_state']=='INTERRUPTED'
    legacy=(ROOT/latest['legacy']['path']).parent;fixtures=[json.loads((legacy/f'fixture-{i}.json').read_text()) for i in range(3)]
    assert all(f['real_checkpoint_write_load_resume'] and f['RNG_and_schedule_equivalent'] for f in fixtures)
    engine=json.loads((BASE.parent/'dashboard-u5pc/manifest.json').read_text())['original_engine_fingerprint']
    assert {f['engine_fingerprint'] for f in fixtures}=={engine}
    with (ROOT/'backend/data/Faculty.csv').open(encoding='utf-8-sig',newline='') as f:
        names=[r['Faculty'].strip().casefold() for r in csv.DictReader(f) if len(r.get('Faculty','').strip())>=6]
    patterns=[r'eyJ[A-Za-z0-9_-]{18,}',r'[A-Za-z0-9_-]{80,}\.[A-Za-z0-9_-]{8,}',r'(?i)postgres(?:ql)?(?:\+\w+)?://[^\s"\']+',
        r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'(?i)bearer\s+[A-Za-z0-9._~-]{20,}',
        r'''(?i)['"]?(?:X-CSRF-Token|ccs_session|csrf_token|password)['"]?\s*[:=]\s*['"][A-Za-z0-9_-]{24,}''']
    png=runpy.run_path(str(ROOT/'docs/testing/dashboard-u5o/audit_evidence.py'))['png'];images={}
    for name in content:
        path=ROOT/name
        if path.suffix=='.png':images[name]=png(path);continue
        text=path.read_text(encoding='utf-8')
        assert not any(re.search(p,text) for p in patterns),'PRIVACY_STOP: '+name
        assert not any(n in text.casefold() for n in names),'PRIVATE_NAME_STOP: '+name
        assert all(line.rstrip()==line for line in text.splitlines()),'WHITESPACE_STOP: '+name
        if name.endswith('.py'):compile(text,name,'exec')
    review=json.loads((BASE/'screenshot-review.json').read_text());assert review['privacy_reviewed'] and set(review['files'])==set(images)
    for name,h in review['files'].items():assert sha(ROOT/name)==h
    assert (ROOT/MODIFIED[1]).read_bytes().isascii(),'PAGE_ENCODING_STOP'
    git('-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--check','--',*MODIFIED)
    git('diff','--cached','--check');fsck=git('fsck','--no-reflogs').decode();assert all(s.startswith('dangling ') for s in fsck.splitlines())
    blobs={n:hashlib.sha1(b'blob '+str((ROOT/n).stat().st_size).encode()+b'\0'+(ROOT/n).read_bytes()).hexdigest() for n in content}
    plan=dict(head=HEAD,exact_checkpoint_inventory=inventory,existing_modified_files=MODIFIED,new_files=len(inventory)-2,
        checkpoint_status='BLOCKED_PRESERVATION_COVERAGE',staging_authorized=False,blocker='Eight pre-existing ignored artifacts lack entry hashes; review preservation scope separately.',
        application_tests=MODIFIED+CODE,documentation_tooling_evidence=sorted(set(inventory)-set(MODIFIED+CODE)),proposed_blob_oids=blobs,
        partial_staging_required=False,core_autocrlf=False,excluded_tracked_modifications=entry['tracked_modifications'],excluded_untracked_files=entry['untracked_files'],
        instructions='PROPOSAL ONLY; no staging. Explicit literal paths only, raw-byte hash verification and CRLF-aware checks. Only two clean-at-entry frontend files changed. Do not stage AppRoutes or the 11 original tracked modifications/958 unrelated untracked files. Preserve source hashes and all failed attempts. Compute the two seal blob identities separately after sealing.',
        proposed_messages=['feat(ga): qualify read-only observation freshness and continuity (U5P-D)','docs(testing): archive U5P-D continuity and resource findings'])
    manifest=dict(milestone='U5P-D',head=HEAD,recorded_at=datetime.now(ZoneInfo('Asia/Manila')).isoformat(),
        status='FUNCTIONAL_CHECKS_COMPLETE; CHECKPOINT_BLOCKED_PRESERVATION_COVERAGE; PRODUCTION_BLOCKED',
        exact_changed_and_new_file_inventory=inventory,existing_files_modified=MODIFIED,new_files=len(inventory)-2,
        final_python_counts=REQUIRED,selected_python_passes=sum(REQUIRED.values())+50,historical_bridge_assertion=dict(passed=50,failed=1,test_unchanged=True),
        frontend_contracts=391,actual_Edge_FastAPI_SQLite_scenarios=9,intercepted_new_browser_scenarios=16,intercepted_legacy_browser_scenarios=12,
        TypeScript='PASS',production_build='PASS',focused_lint='PASS',attempts=attempts,results_are_final_distinct_selections_not_sum_of_reruns=True,
        original_fitness=455.0,original_engine_fingerprint=engine,current_V1_checkpoint_creation_load_continuation=True,
        freshness=dict(contract='research-freshness-v1',response_contract='research-observation-v2',threshold_seconds=30,tolerated_future_skew_seconds=2,
            worker_health='NOT_ESTABLISHED_BY_OBSERVATION_HTTP',legacy_v1='UNKNOWN freshness, observations retained',terminal='Bound durable state/lifecycle event/cleanup evidence, never silence'),
        real_worker_completed_with_API_listener_off=True,API_reconstructed_durable_equal=True,GET_store_bytes_preserved=True,
        preservation=dict(baseline_paths=5121,unchanged=5119,authorized_frontend_changes=2,academic_files=23,original_unrelated_tracked=11,original_unrelated_untracked=958,
            index_and_HEAD_unchanged=True,prior_references=references,prior_source_hashes_resolved_from_committed_baseline=resolved,
            full_preservation_signoff=False,omitted_ignored_paths=8,omitted_bytes_before_after='UNVERIFIABLE; current hashes only; filesystem timestamps predate entry'),
        privacy='PASS; no authentication artifacts/signed receipts/raw datasets/store/checkpoint contents; all PNGs visually and structurally reviewed',
        screenshot_integrity=images,whitespace='PASS',git_integrity='PASS',
        browser_memory=dict(scope='CDP JS heap and DOM only; not process RSS/private commit or long-duration retention proof',samples=browser['memory_samples']),
        evidence_file_bytes_excluding_seals=sum((ROOT/n).stat().st_size for n in content),
        production_admission='BLOCKED',institutional_saved_best_promotion='BLOCKED',continuous_UI='DISABLED',active_restore=False,seven_day='NO_GO',
        checkpoint_readiness='BLOCKED_PRESERVATION_COVERAGE; proposed inventory only, no staging authorization',artifact_sha256={n:sha(ROOT/n) for n in content})
    if record:
        new(BASE/'staging-plan.json',plan);manifest['artifact_sha256'][seals[1]]=sha(BASE/'staging-plan.json');new(BASE/'manifest.json',manifest)
    else:
        sealed=json.loads((BASE/'manifest.json').read_text());assert sealed['exact_changed_and_new_file_inventory']==inventory
        for name,h in sealed['artifact_sha256'].items():assert sha(ROOT/name)==h,'SEALED_HASH_STOP: '+name
    assert git('rev-parse','HEAD').decode().strip()==HEAD and sha(ROOT/'.git/index')==baseline['.git/index']
    print(json.dumps(dict(status='BLOCKED_PRESERVATION_COVERAGE',other_checks='PASS',omitted_entry_hashes=8,inventory=len(inventory),new_files=len(inventory)-2,artifact_hashes=len(inventory)-1,baseline_unchanged=5119,
        selected_python_passes=sum(REQUIRED.values())+50,historical_assertion_failures=1,frontend_contracts=391,live_browser_scenarios=9,new_browser_scenarios=16,
        legacy_browser_scenarios=12,prior_references=1495,production='BLOCKED')))


if __name__=='__main__':
    inspect('--record' in sys.argv or '--record-blocked' in sys.argv,'--record-blocked' in sys.argv)
    raise SystemExit(2)  # Full preservation qualification remains blocked.
