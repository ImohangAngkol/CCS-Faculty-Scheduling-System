"""F2A preservation, numerical reconciliation, privacy and artifact audit."""
import ast
from collections import Counter
from datetime import datetime,timedelta,timezone
from fractions import Fraction
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
REPORT='docs/workload-fairness-f2a-prototype.md'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def exact(value):return Fraction(value['exact']) if isinstance(value,dict) else Fraction(value)


def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for key,item in value.items():yield str(key);yield from strings(item)
    elif isinstance(value,list):
        for item in value:yield from strings(item)


def main():
    baseline=json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'));assert len(baseline)==1806
    def preservation():
        assert all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in baseline.items()),'BASELINE_MISMATCH_STOP_NO_REPAIR'
    preservation();assert sum(p.startswith('backend/data/') for p in baseline)==23
    env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,env=env,text=True).strip()
    assert git('rev-parse','HEAD')=='1423812e13a5791a550c893ef6b17bfef4b4ebfb'
    assert git('branch','--show-current')=='main' and not git('diff','--cached','--name-only')
    assert set(git('diff','--name-only').splitlines())=={'backend/data/faculty_preferences.json','backend/data/ga_settings.json'}
    own=set(git('ls-files','--others','--exclude-standard').splitlines())-set(baseline)
    assert REPORT in own and all(p==REPORT or p.startswith('docs/testing/workload-fairness-f2a/') for p in own),'UNAPPROVED_PATH_STOP'
    sys.path.insert(0,str(ROOT/'backend'))
    from services.evidence_sanitization import ENCODED,URI,PEM,SENSITIVE
    from fairness_models import FUNCTIONS
    patterns=[ENCODED,URI,PEM,re.compile(r'(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_=.-]+'),re.compile(r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}')]
    artifacts=[];attempts=[];latest={};analyses=[];timings=[];original=[]
    manifest=BASE/'manifest.json';manifest_relative=manifest.relative_to(ROOT).as_posix()
    for relative in sorted(own-{manifest_relative}):
        path=ROOT/relative;text=path.read_text(encoding='utf-8');assert path.suffix in {'.py','.md','.json'}
        assert all(line==line.rstrip() for line in text.splitlines()),relative
        values=[text]
        if path.suffix=='.py':ast.parse(text)
        if path.suffix=='.json':
            data=json.loads(text);values=list(strings(data))
            if path.name=='command.json':
                assert not any(SENSITIVE.search(line) for key in ('stdout','stderr') for line in data.get(key,'').splitlines()),'SENSITIVE_LOG_WITHHELD'
                item=dict(path=relative,selection=data['selection'],exit_code=data['exit_code'],output=data['stdout'])
                attempts.append(item);latest[item['selection']]=item
            if path.name=='analysis.json':analyses.append((relative,data))
            if path.name=='timing.json':timings.append((relative,data))
            if path.name=='original-fitness-timing.json':original.append((relative,data))
        assert not any(p.search(v) for p in patterns for v in values),'PRIVACY_FINDING_WITHHELD'
        artifacts.append(dict(path=relative,sha256=sha(path),bytes=path.stat().st_size))
    assert set(latest)=={'backend','frontend'}
    assert latest['backend']['exit_code']==0 and re.search(r'\b118 passed\b',latest['backend']['output'])
    assert latest['frontend']['exit_code']==0 and re.search(r'\bpass 42\b',latest['frontend']['output']) and re.search(r'\bfail 0\b',latest['frontend']['output'])
    failed=[a for a in attempts if a['exit_code']!=0];assert len(failed)==1 and '1 failed, 117 passed' in failed[0]['output']
    analysis_path,analysis=analyses[-1]
    assert analysis['total_hard_valid_fixed_geometry_assignments']==470 and analysis['total_unique_workload_vectors']==45
    assert len(analysis['scenarios'])==9
    checked=0
    for entry in analysis['source_artifact_hashes']:
        path=BASE/entry['path'];assert sha(path)==entry['sha256'];data=json.loads(path.read_text(encoding='utf-8'))
        assert data['all_original_hard_valid'] and data['all_seven_other_components_zero']
        for row in data['rows']:
            assert row['original_total']==row['original_components']['teaching_load_balance']
            assert sum(row['original_components'].values())==row['original_total']
            assert all(v==0 for v in row['hard_conflicts'].values()) and row['unassigned_offerings']==0
            for name,fn in FUNCTIONS.items():assert exact(row['scores'][name])==fn(row['actual'],data['targets'])
            checked+=1
    assert checked==45
    timing_path,timing=timings[-1];assert len(timing['results'])==18 and timing['global_rng_unchanged']
    assert all(r['repetitions']==7 and len(r['us_per_call'])==7 and 0<r['min_us']<=r['median_us']<=r['max_us'] for r in timing['results'])
    original_path,full=original[-1];assert full['original_total']==500 and len(full['components'])==8 and full['global_rng_restored']
    for link in re.findall(r'\]\(([^)]+)\)',(ROOT/REPORT).read_text(encoding='utf-8')):
        if not link.startswith(('http:','https:','#')):
            destination=((ROOT/REPORT).parent/link.split('#')[0]).resolve();assert destination==manifest or destination.is_file(),link
    previous=0
    for name in ('ga-performance-phase2','ga-performance-phase3','ga-memory-study','ga-retention-phase5','ga-reconstruction-phase6',
                 'dashboard-d15','thesis-functional-audit','faculty-policy-qualification','faculty-cohort-f1','faculty-cohort-f1-5'):
        earlier=json.loads((ROOT/'docs/testing'/name/'manifest.json').read_text(encoding='utf-8'))
        for entry in earlier['artifacts']:
            assert sha(ROOT/entry['path'])==entry['sha256'],'HISTORICAL_ARTIFACT_MISMATCH'
            previous+=1
    for args in [('diff','--check'),('diff','--cached','--check')]:subprocess.run(['git',*args],cwd=ROOT,env=env,check=True)
    preservation();inventory=sorted(own|{manifest_relative})
    record=dict(milestone='F2A workload fairness correction prototype',recorded_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),
        source_HEAD=git('rev-parse','HEAD'),python=sys.version,platform=platform.platform(),
        scope='Fictional IT-intended prototype; no institutional population, no IS/full CCS claim',
        policy='USER_REPORTED target-relative fairness and Option B approval; exact function/weight/conventions remain unapproved',
        recommendation='target_relative suitable for conditional F2 consideration, not production integration',
        institutional_activation='BLOCKED',F1_production_roster='BLOCKED_UNCHANGED',production_integration=False,
        new_file_inventory=inventory,new_file_type_counts=dict(Counter(Path(p).suffix for p in inventory)),artifacts=artifacts,
        baseline_files_preserved=1806,academic_files_preserved=23,existing_files_modified=0,protected_preferences_settings_unchanged=True,
        Git_index_HEAD_preserved=True,preexisting_tracked_modifications=['backend/data/faculty_preferences.json','backend/data/ga_settings.json'],
        tests=dict(backend_command=latest['backend']['path'],backend_passed=118,new_F2A_cases=32,existing_audit=33,existing_D10=30,existing_reporting=23,
                   frontend_command=latest['frontend']['path'],frontend_contracts_passed=42,final_failed=0,final_skipped=0),
        attempts=[dict(path=a['path'],selection=a['selection'],exit_code=a['exit_code']) for a in attempts],
        retained_unsuccessful_attempts=[a['path'] for a in failed],failure_diagnosis='New test corrected to assert qualification at original admission gate, not resource assignment helper',
        analysis_path=analysis_path,hard_valid_fixed_geometry_assignments=470,unique_vectors=45,reconciled_candidate_score_rows=checked,
        arithmetic_timing=timing_path,full_original_scorer_timing=original_path,
        historical_artifact_entries_verified=previous,privacy_findings=0,
        privacy_scope='Only fictional numeric/structural findings; credential URI/key/token/complete and truncated receipt patterns plus sensitive logs scanned; no private rows/preferences/sessions archived',
        candidate_policy_GA_runs=0,original_GA_regressions='Actual D10 engine and checkpoint continuation on fictional fixtures',
        database_operations=0,dependencies_installed=0,staged_files=0,commits_pushes=0,
        actual_browser='NOT_RUN_NO_UI_INTEGRATION',frontend_build_lint='NOT_RUN_NO_PRODUCTION_EDIT',
        limitations=['Fixed geometry enumeration, not a full GA quality campaign',
            'Exact weights, overload/zero-target/coverage tradeoffs pending explicit policy specification',
            'Pure arithmetic and full original scorer timing scopes differ; no measured integrated/engine speedup',
            'No new-policy checkpoint/report/operator integration; current behavior preserved',
            'No formal manuscript or institutional IT source authorization established'],
        hash_convention='Raw bytes; manifest excludes itself; all historical artifacts retained')
    body=json.dumps(record,indent=2)+'\n';assert not any(p.search(body) for p in patterns)
    manifest.write_text(body,encoding='utf-8',newline='\n')
    print(json.dumps(dict(preserved_paths=1806,academic_files_preserved=23,new_files=len(inventory),artifacts_hashed=len(artifacts),
        backend_passed=118,frontend_contracts_passed=42,hard_valid_assignments=470,historical_artifacts_verified=previous,
        privacy_findings=0,production_integration=False)))


if __name__=='__main__':main()
