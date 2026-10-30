"""F1 evidence audit; only its new manifest is written, no baseline repair."""
import ast
from collections import Counter
from datetime import datetime,timedelta,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
REPORT='docs/faculty-cohort-f1-implementation.md'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for key,item in value.items():yield str(key);yield from strings(item)
    elif isinstance(value,list):
        for item in value:yield from strings(item)


def main():
    baseline=json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'))
    assert len(baseline)==1767
    def preservation():
        assert all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in baseline.items()),'BASELINE_MISMATCH_STOP_NO_REPAIR'
    preservation()
    assert sum(p.startswith('backend/data/') for p in baseline)==23
    env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,env=env,text=True).strip()
    assert git('rev-parse','HEAD')=='1423812e13a5791a550c893ef6b17bfef4b4ebfb'
    assert git('branch','--show-current')=='main' and not git('diff','--cached','--name-only')
    assert set(git('diff','--name-only').splitlines())=={'backend/data/faculty_preferences.json','backend/data/ga_settings.json'}
    own=set(git('ls-files','--others','--exclude-standard').splitlines())-set(baseline)
    assert REPORT in own and all(p==REPORT or p.startswith(('backend/tests/f1/','docs/testing/faculty-cohort-f1/')) for p in own),'UNAPPROVED_PATH_STOP'
    sys.path.insert(0,str(ROOT/'backend'))
    from services.evidence_sanitization import ENCODED,URI,PEM,SENSITIVE
    patterns=[ENCODED,URI,PEM,re.compile(r'(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_=.-]+'),re.compile(r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}')]
    artifacts=[];attempts=[];latest={}
    manifest_path=BASE/'manifest.json';manifest_relative=manifest_path.relative_to(ROOT).as_posix()
    for relative in sorted(own-{manifest_relative}):
        path=ROOT/relative;assert path.suffix in {'.py','.md','.json'}
        text=path.read_text(encoding='utf-8')
        assert all(line==line.rstrip() for line in text.splitlines()),relative
        values=[text]
        if path.suffix=='.py':ast.parse(text)
        if path.suffix=='.json':
            data=json.loads(text);values=list(strings(data))
            if path.name=='command.json':
                assert not any(SENSITIVE.search(line) for key in ('stdout','stderr') for line in data.get(key,'').splitlines()),'SENSITIVE_LOG_WITHHELD'
                item=dict(path=relative,selection=data['selection'],exit_code=data['exit_code'],output=data['stdout'])
                attempts.append(item);latest[item['selection']]=item
        assert not any(p.search(v) for p in patterns for v in values),'PRIVACY_FINDING_WITHHELD'
        artifacts.append(dict(path=relative,sha256=sha(path),bytes=path.stat().st_size))
    assert set(latest)=={'cohort','workflow','frontend'}
    for selection,count in [('cohort',93),('workflow',48)]:
        row=latest[selection]
        assert row['exit_code']==0 and re.search(r'\b'+str(count)+r' passed\b',row['output'])
        assert not re.search(r'\b[1-9]\d* (failed|errors?|skipped)\b',row['output'])
    assert latest['frontend']['exit_code']==0 and re.search(r'\bpass 99\b',latest['frontend']['output']) and re.search(r'\bfail 0\b',latest['frontend']['output'])
    failures=[a for a in attempts if a['exit_code']!=0]
    assert len(failures)==1 and '2 failed, 91 passed' in failures[0]['output']
    output=(ROOT/latest['cohort']['path']).parent
    coverage=json.loads((output/'coverage-before-after.json').read_text())
    assert (coverage['legacy_runtime_members'],coverage['adapter_runtime_members'])==(1,3)
    assert coverage['adapter_eligible_members_included']==2 and coverage['adapter_zero_assignments']==1 and coverage['adapter_unassigned_offerings']==0
    assert coverage['adapter_excluded_count']==2 and len(coverage['legacy_excluded_active_members'])==2
    assert all(v==0 for v in coverage['hard_conflicts_after'].values()) and not coverage['inclusion_guarantees_assignment']
    continuation=json.loads((output/'adapter-engine-continuation.json').read_text())
    assert continuation['same_seed_and_resumed_results_equal'] and continuation['original_checkpoint_read_write'] and continuation['final_rng_equal']
    assert continuation['best_ever_history']==[250,250,250] and continuation['best_graph_independent']
    assert all(json.loads((output/('conflict-control-'+kind+'.json')).read_text())['original_reconstruction_rejected'] for kind in ('faculty','room','section'))
    for link in re.findall(r'\]\(([^)]+)\)',(ROOT/REPORT).read_text(encoding='utf-8')):
        if not link.startswith(('http:','https:','#')):
            destination=((ROOT/REPORT).parent/link.split('#')[0]).resolve()
            assert destination==manifest_path or destination.is_file(),link
    historical=0
    for name in ('ga-performance-phase2','ga-performance-phase3','ga-memory-study','ga-retention-phase5','ga-reconstruction-phase6',
                 'dashboard-d15','thesis-functional-audit','faculty-policy-qualification'):
        previous=json.loads((ROOT/'docs/testing'/name/'manifest.json').read_text(encoding='utf-8'))
        for entry in previous['artifacts']:
            assert sha(ROOT/entry['path'])==entry['sha256'],'HISTORICAL_ARTIFACT_MISMATCH'
            historical+=1
    for args in [('diff','--check'),('diff','--cached','--check')]:
        subprocess.run(['git',*args],cwd=ROOT,env=env,check=True)
    preservation()
    inventory=sorted(own|{manifest_relative})
    record=dict(milestone='F1 faculty cohort correction',recorded_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),
        source_HEAD=git('rev-parse','HEAD'),python=sys.version,platform=platform.platform(),
        policy_approval='USER_REPORTED_ADVISER_DEPARTMENT_ROSTER_FIRST_PRINCIPLE; no documentary approval evidence supplied',
        institutional_activation='BLOCKED',production_cohort_correction='BLOCKED_NO_TRUSTWORTHY_TERM_ROSTER_PROFILE_PROVIDER',
        fictional_adapter_review='READY',production_files_modified=0,existing_files_modified=0,
        new_file_inventory=inventory,new_file_type_counts=dict(Counter(Path(p).suffix for p in inventory)),artifacts=artifacts,
        baseline_files_preserved=len(baseline),academic_files_preserved=23,protected_preferences_and_existing_settings_unchanged=True,
        Git_index_HEAD_preserved=True,preexisting_tracked_modifications=['backend/data/faculty_preferences.json','backend/data/ga_settings.json'],
        tests=dict(latest_cohort_command=latest['cohort']['path'],new_F1_passed=30,existing_audit_passed=33,existing_D10_engine_passed=30,
                   latest_workflow_command=latest['workflow']['path'],workflow_passed=48,backend_total_passed=141,
                   latest_frontend_command=latest['frontend']['path'],frontend_contracts_passed=99,final_failed=0,final_skipped=0),
        attempts=[dict(path=a['path'],selection=a['selection'],exit_code=a['exit_code']) for a in attempts],
        unsuccessful_attempts_preserved=[a['path'] for a in failures],
        failure_diagnosis='New conflict fixture assumed assigned room from list position; original scheduler shuffles. Corrected by reading actual first assigned room; no application edit.',
        historical_artifact_entries_reverified=historical,privacy_findings=0,
        privacy_scope='Fictional records only; credential/key/complete and partial encoded receipt patterns plus sensitive log fields checked. No private faculty data, request/session payload or checkpoint archived.',
        PostgreSQL_operations=0,SQLite_scope='Owned isolated workflow fixtures only; no existing database accessed',
        actual_browser='NOT_RUN_NO_PRODUCTION_INTEGRATION',frontend_build_lint='NOT_RUN_NO_FRONTEND_EDIT',
        dependencies_installed=0,staged_files=0,commits_pushes=0,
        limitations=['No trustworthy institutional semester roster/profile source configured',
            'Fictional adapter is not imported by application; current legacy membership remains unchanged',
            'Preference business validation, authorization and term applicability still require trusted metadata integration',
            'Cohort digest is not yet installed in production run/checkpoint provenance',
            'No genuine institutional authority or full formal thesis compliance established'],
        hash_convention='Raw bytes; manifest excludes itself; old evidence and artifacts unchanged')
    body=json.dumps(record,indent=2)+'\n';assert not any(p.search(body) for p in patterns)
    manifest_path.write_text(body,encoding='utf-8',newline='\n')
    assert manifest_path.is_file()
    print(json.dumps(dict(existing_paths_preserved=len(baseline),academic_files_preserved=23,new_files=len(inventory),
        artifacts_hashed=len(artifacts),backend_passed=141,frontend_contracts_passed=99,privacy_findings=0,
        historical_entries_verified=historical,fictional_adapter='READY_FOR_REVIEW',production_cohort='BLOCKED')))


if __name__=='__main__':main()
