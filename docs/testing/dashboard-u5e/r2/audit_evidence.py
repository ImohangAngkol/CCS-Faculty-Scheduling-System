"""Versioned continuation audit. Prior U5E evidence is never rewritten."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
BASE=Path(__file__).resolve().parent
OLD=runpy.run_path(str(BASE.parent/'audit_evidence.py'))
git=OLD['git'];sha=OLD['sha'];png=OLD['png'];counts=OLD['counts']
HEAD=OLD['HEAD']
COMPONENT='frontend/src/components/ga/AdvancedAnalysis.tsx'
REPORT='docs/dashboard-u5e-advanced-ga-analysis.md'
CHANGED={COMPONENT,REPORT}
NEW={'frontend/src/services/analysisChartPresentation.ts','frontend/tests/advancedAnalysisInteraction.test.mjs','frontend/tests/advancedAnalysisInteraction.browser.test.mjs'}

def inspect(record=False):
    assert git('rev-parse','HEAD').decode().strip()==HEAD and git('branch','--show-current').decode().strip()=='main'
    assert not git('diff','--cached','--name-only').strip()
    baseline=json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'))
    assert len(baseline)==3414
    for name,digest in baseline.items():
        if name not in CHANGED:assert (ROOT/name).is_file() and sha(ROOT/name)==digest,'PRESERVATION_STOP: '+name
    for root in ['backend/data','backend/run_checkpoints','backend/saved_chromosomes','backend/run_input_receipts_v1','backend/run_provenance_v1','backend/constrained_runs_v2']:
        assert not {p.relative_to(ROOT).as_posix() for p in (ROOT/root).rglob('*') if p.is_file()}-set(baseline),'NEW_RUNTIME_FILE_STOP: '+root
    old=json.loads((BASE.parent/'manifest.json').read_text(encoding='utf-8'))
    for name,digest in old['artifact_sha256'].items():
        path=BASE/'entry'/Path(name).name if name in CHANGED else ROOT/name
        assert sha(path)==digest,'PRIOR_U5E_EVIDENCE_STOP: '+name
    assert set(git('diff','--name-only').decode().splitlines())==set(old['preexisting_tracked_modifications'])|set(old['modified_from_entry'])
    git('diff','--check','--',*old['modified_from_entry'])
    inventory=sorted(set(old['exact_checkpoint_inventory'])|NEW|{p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file()}|{'docs/testing/dashboard-u5e/r2/manifest.json','docs/testing/dashboard-u5e/r2/staging-plan.json'})
    untracked=set(git('ls-files','--others','--exclude-standard','-z').decode().split('\0'))-{''}
    assert not untracked-set(baseline)-set(inventory),'UNRELATED_NEW_PATH_STOP'
    assert not any(p.startswith('backend/data/') or p.startswith('backend/run_') or Path(p).name.startswith('.env') for p in inventory)
    helper=runpy.run_path(str(BASE.parent/'checkpoint_snapshot.py'))
    page=helper['PAGE'];proposed=helper['integration'](git('show',HEAD+':'+page))
    git('apply','--check','--cached',str(BASE.parent/'fitness-analysis-integration.patch'))
    proofs=sorted(BASE.glob('*snapshot/snapshot-proof.json'));proof=json.loads(proofs[-1].read_text(encoding='utf-8'))
    assert proof['complete'] and proof['no_u5d_dependency']
    for name,digest in proof['source_sha256'].items():
        content=proposed if name==page else (ROOT/name).read_bytes()
        assert hashlib.sha256(content).hexdigest()==digest,'SNAPSHOT_DRIFT_STOP: '+name
        assert git('hash-object','--stdin',input=content).decode().strip()==proof['blob_oids'][name]
    attempts=[]
    for path in sorted(BASE.glob('*/command.json')):
        row=json.loads(path.read_text(encoding='utf-8'));attempts.append(dict(path=path.relative_to(ROOT).as_posix(),selection=row['selection'],exit_code=row['exit_code'],counts=counts(row)))
    final={r['selection']:r for r in attempts}
    for key,total,field in [('backend',56,'passed'),('focused',30,'pass'),('regressions',166,'pass'),('browser',21,'pass')]:
        assert final[key]['exit_code']==0 and final[key]['counts'][field]==total
    for key in ['build','bundle','lint','integrity']:assert final[key]['exit_code']==0
    snapshot=[]
    for path in sorted(proofs[-1].parent.glob('*-command.json')):
        row=json.loads(path.read_text(encoding='utf-8'));assert row['exit_code']==0
        snapshot.append(dict(path=path.relative_to(ROOT).as_posix(),selection=row['selection'],counts=counts(row)))
    assert len(snapshot)==7
    registry=json.loads((ROOT/'backend/data/faculty_identities.json').read_text(encoding='utf-8'))['faculty']
    names={re.sub(r'\s+',' ',s.strip().upper()) for row in registry for s in [row['name'],*row.get('aliases',[])] if len(s.strip())>=8}
    patterns=[r'eyJ[A-Za-z0-9_=-]{16,}',r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}',r'(?i)\b(?:postgresql|postgres|mysql)(?:\+\w+)?://[^\s]+',r'-----BEGIN [A-Z ]*PRIVATE KEY-----',r'(?i)https?://[^\s/]+:[^\s/@]+@',r'(?i)(?<![\w])(?:set-cookie|authorization)\s*:\s*[^\s]{16,}']
    plan=dict(head=HEAD,exact_checkpoint_inventory=inventory,whole_file_paths=[p for p in inventory if p!=page],
        partial_only={'path':page,'patch':'docs/testing/dashboard-u5e/fitness-analysis-integration.patch','sha256':hashlib.sha256(proposed).hexdigest(),'proposed_blob_oid':git('hash-object','--stdin',input=proposed).decode().strip()},
        exclusions=['All U5D paths','Protected preferences/settings and academic datasets','Unrelated U4/Live/research','All seven runtime additions and any later application runtime output'],
        staging_performed=False,commit_push_authorized=False,
        messages=['feat(ga): add candidate-bound interactive faculty analysis','docs(testing): archive U5E analysis and interaction acceptance'],
        instructions=['Fresh upstream comparison and separate authorization before any checkpoint','Use explicit whole_file_paths, never add dot or add -A','Never stage FitnessAnalysis.tsx whole; use the reviewed cached patch only','Raw hashes and core.autocrlf=false apply to whole-file artifact bytes; partial page uses its proposed hash','Prior root staging-plan-final.json is historical; this R2 plan supersedes its inventory'])
    planpath=BASE/'staging-plan.json'
    if record:
        with planpath.open('x',encoding='utf-8') as f:f.write(json.dumps(plan,indent=2)+'\n')
    else:assert json.loads(planpath.read_text(encoding='utf-8'))==plan
    hashes={};blobs={};screens={}
    for name in inventory:
        if name=='docs/testing/dashboard-u5e/r2/manifest.json':continue
        path=ROOT/name;raw=path.read_bytes();hashes[name]=sha(path)
        if path.suffix=='.png':screens[name]=png(path)
        else:
            text=raw.decode('utf-8');assert text.endswith('\n')
            if path.suffix!='.patch':assert all(line==line.rstrip() for line in text.splitlines()),'WHITESPACE_STOP: '+name
            assert not any(re.search(p,text) for p in patterns),'SENSITIVE_PATTERN_STOP_WITHHELD'
            normalized=re.sub(r'\s+',' ',text.upper())
            assert not any(re.search(r'(?<!\w)'+re.escape(s)+r'(?!\w)',normalized) for s in names),'PRIVATE_NAME_STOP_WITHHELD'
        blob=proposed if name==page else raw
        blobs[name]=git('hash-object','--stdin',input=blob).decode().strip()
        assert blobs[name]==git('-c','core.autocrlf=false','hash-object','--path='+name,'--stdin',input=blob).decode().strip()
    for p in BASE.glob('*/browser-results.json'):
        doc=json.loads(p.read_text(encoding='utf-8'))
        for c in doc['captures']:
            n=(p.parent/c['file']).relative_to(ROOT).as_posix();assert all(screens[n][k]==c['viewport'][k] for k in ['width','height'])
    visual=json.loads((BASE/'screenshot-review.json').read_text(encoding='utf-8'))
    assert set(visual['reviewed_sha256'])=={sha(ROOT/n) for n in screens if n.startswith('docs/testing/dashboard-u5e/r2/')}
    assert visual['private_records_seen'] is False
    assert git('rev-parse','HEAD').decode().strip()==HEAD and sha(ROOT/'.git/index')==baseline['.git/index']
    return dict(milestone='U5E-R2',status='READ_ONLY_ADMIN_DASHBOARD_COMPLETE_WITH_RECORDED_LIMITATIONS',head=HEAD,
        exact_checkpoint_inventory=inventory,artifact_sha256=hashes,proposed_git_blob_oids=blobs,screenshots=screens,
        baseline_paths=3414,unchanged_baseline_paths=3412,modified_from_r2_entry=sorted(CHANGED),additional_application_test_paths=sorted(NEW),
        original_23_academic_files_ga_scoring_rng_fingerprints_migrations_saved_best_checkpoints_history='UNCHANGED',
        protected_preferences_settings='BYTE_IDENTICAL_UNSTAGED_EXCLUDED',unrelated_runtime_additions_preserved_and_excluded=7,
        previous_manifest='docs/testing/dashboard-u5e/manifest.json',prior_artifacts_verified=140,
        historical_artifact_aliases={p:(BASE/'entry'/Path(p).name).relative_to(ROOT).as_posix() for p in CHANGED},
        attempts=attempts,final_checks=final,snapshot_checks=snapshot,final_snapshot=proofs[-1].relative_to(ROOT).as_posix(),
        snapshot_attempts=[dict(path=p.relative_to(ROOT).as_posix(),**json.loads(p.read_text(encoding='utf-8'))) for p in proofs],
        fresh_tests={'backend':56,'frontend_focused':30,'frontend_regressions':166,'browser_scenarios':20,'browser_parent_harness':1},
        previous_verified_not_rerun={'backend_reporting_history_provenance':145,'v1_v2_engine':34,'u5a_u5b_u5c_browser_scenarios':39},
        browser_scope='Actual Edge/React DOM, CDP-intercepted fictional HTTP; not live FastAPI/database acceptance',
        backend_scope='Fictional temporary model/store and TestClient/owned loopback U5D tests; no real sessions or institutional database',
        privacy='PASS text patterns, private-name comparison, PNG CRC/metadata and original screenshot visual review',whitespace='PASS',index_head='UNCHANGED',staged_files=[],
        limitations=['Scoped Chair access blocked pending verified run-to-department authorization','V1 recorded analysis only; V2/transient candidates unchanged',
            'Missing historical preferences/observations remain unavailable; no optimizer-consumption verification','No source provider activation or Saved Best promotion','Prior failed tests, temporary-folder failure and selector/synchronization diagnostics retained'])

if __name__=='__main__':
    record=sys.argv[1:]==['--record'];result=inspect(record);path=BASE/'manifest.json'
    if record:
        result['recorded_at']=datetime.now().astimezone().isoformat()
        with path.open('x',encoding='utf-8') as f:f.write(json.dumps(result,indent=2)+'\n')
    else:
        old=json.loads(path.read_text(encoding='utf-8'))
        for k,v in result.items():assert old[k]==v,'MANIFEST_MISMATCH_STOP: '+k
    print(json.dumps({'status':'U5E_R2_AUDIT_PASSED','paths':len(result['exact_checkpoint_inventory']),'hashes':len(result['artifact_sha256']),'unchanged_baseline_paths':3412,'staged':False}))
