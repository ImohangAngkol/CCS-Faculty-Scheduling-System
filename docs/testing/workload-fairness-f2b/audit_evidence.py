"""Verify F2B stop evidence and all baseline bytes; write only own manifest."""
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
REPORT='docs/workload-fairness-f2b-implementation.md'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for k,v in value.items():yield str(k);yield from strings(v)
    elif isinstance(value,list):
        for v in value:yield from strings(v)


def main():
    baseline=json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'));assert len(baseline)==1845
    def preserved():
        assert all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in baseline.items()),'PRESERVATION_MISMATCH_STOP_NO_REPAIR'
    preserved();assert sum(p.startswith('backend/data/') for p in baseline)==23
    env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,env=env,text=True).strip()
    assert git('branch','--show-current')=='main' and git('rev-parse','HEAD')=='1423812e13a5791a550c893ef6b17bfef4b4ebfb'
    assert not git('diff','--cached','--name-only')
    assert set(git('diff','--name-only').splitlines())=={'backend/data/faculty_preferences.json','backend/data/ga_settings.json'}
    own=set(git('ls-files','--others','--exclude-standard').splitlines())-set(baseline)
    assert REPORT in own and all(p==REPORT or p.startswith('docs/testing/workload-fairness-f2b/') for p in own),'UNAPPROVED_PATH_STOP'
    sys.path.insert(0,str(ROOT/'backend'))
    from services.evidence_sanitization import ENCODED,URI,PEM,SENSITIVE
    patterns=[ENCODED,URI,PEM,re.compile(r'(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_=.-]+'),re.compile(r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}')]
    artifacts=[];attempts=[];latest={};v1=None;v1_path=None
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
                assert data['exit_code']==0
                attempts.append(dict(path=relative,selection=data['selection'],exit_code=0))
                if data['selection']=='v1-mirror':v1=data;v1_path=relative
                else:latest[data['selection']]=(relative,data)
        assert not any(p.search(v) for p in patterns for v in values),'PRIVACY_FINDING_WITHHELD'
        artifacts.append(dict(path=relative,sha256=sha(path),bytes=path.stat().st_size))
    assert set(latest)=={'backend','frontend'} and v1
    assert re.search(r'\b40 passed\b',latest['backend'][1]['stdout'])
    assert re.search(r'\bpass 42\b',latest['frontend'][1]['stdout']) and re.search(r'\bfail 0\b',latest['frontend'][1]['stdout'])
    assert re.search(r'\b4 passed\b',v1['stdout']) and v1['verified_fictional_checkpoint_archives']==3
    assert v1['source_files_byte_identical']==133 and v1['engine_fingerprint_matches_original_current_release']
    assert not v1['original_academic_access_permitted'] and not v1['fingerprint_functions_replaced']
    backend=(ROOT/latest['backend'][0]).parent
    read=lambda name:json.loads((backend/(name+'.json')).read_text(encoding='utf-8'))
    assert read('legacy_bridge_boundary')['hypothetical_changed_source_rejected']
    assert read('numeric_boundary')['current_checkpoint_rejects_type'] and read('numeric_boundary')['current_report_rejects_type']
    assert read('shared_scorer_boundary')['current_engine_fingerprint']==v1['engine_fingerprint']
    assert read('zero_target_boundary')['legacy_workload']==20
    assert all((r['balanced'],r['concentrated'])==(500,475) for r in read('no_activation_hook')['observations'])
    algebra=json.loads((BASE/'calibration-algebra.json').read_text(encoding='utf-8'));assert len(algebra['rows'])==42
    for row in algebra['rows']:
        diff=Fraction(row['extra_penalty'])-Fraction(row['coefficient'])/3
        assert str(diff)==row['total_balanced_minus_concentrated']
        assert row['preferred']==('balanced' if diff<0 else 'tie' if diff==0 else 'concentrated')
    for link in re.findall(r'\]\(([^)]+)\)',(ROOT/REPORT).read_text(encoding='utf-8')):
        if not link.startswith(('http:','https:','#')):
            destination=((ROOT/REPORT).parent/link.split('#')[0]).resolve();assert destination==manifest or destination.is_file(),link
    historical=0
    for name in ('ga-performance-phase2','ga-performance-phase3','ga-memory-study','ga-retention-phase5','ga-reconstruction-phase6',
                 'dashboard-d15','thesis-functional-audit','faculty-policy-qualification','faculty-cohort-f1','faculty-cohort-f1-5','workload-fairness-f2a'):
        previous=json.loads((ROOT/'docs/testing'/name/'manifest.json').read_text(encoding='utf-8'))
        for entry in previous['artifacts']:
            assert sha(ROOT/entry['path'])==entry['sha256'],'HISTORICAL_ARTIFACT_MISMATCH'
            historical+=1
    for args in [('diff','--check'),('diff','--cached','--check')]:subprocess.run(['git',*args],cwd=ROOT,env=env,check=True)
    preserved();inventory=sorted(own|{manifest_relative})
    record=dict(milestone='F2B controlled fairness integration compatibility stop',recorded_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),
        source_HEAD=git('rev-parse','HEAD'),python=sys.version,platform=platform.platform(),
        status='BLOCKED_BEFORE_APPLICATION_IMPLEMENTATION',F2B_complete=False,recommendation='NO_GO_PENDING_VERSIONED_DISPATCH_CONTINUATION_REPORTING_CONTRACT',
        authority_scope='IT prototype; institutional activation and production F1 remain BLOCKED',
        policy_approval='Developer-approved direction per user; no invented adviser documentation',
        application_files_modified=0,scoring_mode_implemented=False,default_behavior_unchanged=True,
        new_file_inventory=inventory,new_file_type_counts=dict(Counter(Path(p).suffix for p in inventory)),artifacts=artifacts,
        preserved_existing_paths=1845,protected_academic_files_preserved=23,existing_files_modified=0,
        protected_preferences_settings_unchanged=True,Git_index_HEAD_preserved=True,
        tests=dict(final_boundary_and_default_V2_path=latest['backend'][0],boundary_passed=10,current_default_V2_passed=30,
                   current_default_V1_path=v1_path,current_default_V1_passed=4,verified_fictional_V1_checkpoint_archives=3,
                   source_byte_identical_mirror_files=133,backend_total_passed=44,
                   frontend_path=latest['frontend'][0],frontend_contracts_passed=42,failed=0,skipped=0),
        all_attempts_preserved=attempts,calibration='42 exact algebra cells only; no actual integrated calibration trials',
        experimental_multigeneration_runs='NOT_RUN_NO_SUPPORTED_MODE',experimental_checkpoint_acceptance='BLOCKED_NOT_IMPLEMENTED',
        experimental_GA_performance_memory_quality='NOT_RUN_NOT_FABRICATED',
        historical_artifact_entries_verified=historical,privacy_findings=0,
        privacy_scope='Fictional structural/numeric results only. Credential URIs, keys, complete/partial encoded token patterns and sensitive logs scanned; no raw faculty data, private contexts, sessions or checkpoints archived.',
        database_operations=0,dependencies_installed=0,staged_files=0,commits_pushes=0,
        actual_browser='NOT_RUN_NO_NEW_UI',production_build_lint='NOT_RUN_NO_APPLICATION_EDIT',
        limitations=['No integrated experimental workload mode',
            'Changing scorer without a reviewed source-compatibility strategy would invalidate current default continuation identity',
            'No workload-policy identity/weight/numeric convention captured in current requests, frozen state or reports',
            'Positive teaching at zero target needs an explicit new deviation convention or unsupported-case block',
            'No candidate-mode GA, memory, quality or performance claim'],
        hash_convention='Raw bytes; manifest excludes itself; all previous artifacts and unsuccessful historical evidence retained')
    body=json.dumps(record,indent=2)+'\n';assert not any(p.search(body) for p in patterns)
    manifest.write_text(body,encoding='utf-8',newline='\n')
    print(json.dumps(dict(preserved_paths=1845,academic_files_preserved=23,new_files=len(inventory),artifacts_hashed=len(artifacts),
        backend_passed=44,frontend_contracts_passed=42,historical_artifacts_verified=historical,privacy_findings=0,
        F2B_complete=False,recommendation='NO_GO_APPLICATION_INTEGRATION')))


if __name__=='__main__':main()
