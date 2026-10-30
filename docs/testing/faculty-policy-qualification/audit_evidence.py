"""Audit own new artifacts; never repair or rewrite baseline paths."""
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
REPORTS={'docs/faculty-policy-qualification.md','docs/faculty-policy-decision-matrix.md'}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for key,item in value.items():yield str(key);yield from strings(item)
    elif isinstance(value,list):
        for item in value:yield from strings(item)


def main():
    baseline=json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'))
    assert len(baseline)==1739
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
    assert REPORTS<=own and all(p in REPORTS or p.startswith('docs/testing/faculty-policy-qualification/') for p in own),'UNAPPROVED_PATH_STOP'
    sys.path.insert(0,str(ROOT/'backend'))
    from services.evidence_sanitization import ENCODED,URI,PEM,SENSITIVE
    patterns=[ENCODED,URI,PEM,re.compile(r'(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_=.-]+'),re.compile(r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}')]
    artifacts=[];attempts=[]
    manifest_relative=(BASE/'manifest.json').relative_to(ROOT).as_posix()
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
                attempts.append({'path':relative,'exit_code':data['exit_code'],'output':data['stdout']})
        assert not any(p.search(v) for p in patterns for v in values),'PRIVACY_FINDING_WITHHELD'
        artifacts.append(dict(path=relative,sha256=sha(path),bytes=path.stat().st_size))
    assert attempts
    latest=attempts[-1]
    assert latest['exit_code']==0 and re.search(r'\b88 passed\b',latest['output'])
    assert not re.search(r'\b[1-9]\d* (failed|errors?|skipped)\b',latest['output'])
    output=ROOT/latest['path'];output=output.parent
    data=json.loads((output/'fairness-exact-breakdown.json').read_text())
    assert [r['total'] for r in data['schedules']]==[500,475]
    for row in data['schedules']:
        assert len(row['components'])==8 and row['components']['teaching_load_balance']==row['total']
        assert row['original_admitted'] and all(x==0 for x in row['independent_conflicts'].values())
    assert len(list(output.glob('allocation-*.json')))==13
    assert json.loads((output/'eligibility-forced-concentration.json').read_text())['balanced_candidate_rejected']
    matrix=json.loads((BASE/'decisions.json').read_text(encoding='utf-8'))
    assert len(matrix['rows'])==12 and all(not r['approved'] and r['formal_thesis_alignment']=='UNVERIFIED' for r in matrix['rows'])
    for report in REPORTS:
        for link in re.findall(r'\]\(([^)]+)\)',(ROOT/report).read_text(encoding='utf-8')):
            if not link.startswith(('http:','https:','#')):
                destination=((ROOT/report).parent/link.split('#')[0]).resolve()
                # The manifest is this verifier's output; verify after writing.
                assert destination==BASE/'manifest.json' or destination.is_file(),link
    historical=0
    for name in ('ga-performance-phase2','ga-performance-phase3','ga-memory-study','ga-retention-phase5','ga-reconstruction-phase6','dashboard-d15','thesis-functional-audit'):
        previous=json.loads((ROOT/'docs/testing'/name/'manifest.json').read_text(encoding='utf-8'))
        for entry in previous['artifacts']:
            assert sha(ROOT/entry['path'])==entry['sha256'],'HISTORICAL_ARTIFACT_MISMATCH'
            historical+=1
    for args in [('diff','--check'),('diff','--cached','--check')]:
        subprocess.run(['git',*args],cwd=ROOT,env=env,check=True)
    preservation()
    inventory=sorted(own|{manifest_relative})
    record=dict(milestone='Faculty Cohort, Workload Scope and Evaluation-Policy Qualification',
        recorded_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),source_HEAD=git('rev-parse','HEAD'),
        python=sys.version,platform=platform.platform(),formal_thesis_alignment='UNVERIFIED',institutional_activation='BLOCKED',
        policy_decisions_approved=0,functional_corrections_implemented=0,production_scoring_changes=0,
        new_file_inventory=inventory,new_file_type_counts=dict(Counter(Path(p).suffix for p in inventory)),artifacts=artifacts,
        baseline_files_preserved=len(baseline),academic_files_preserved=23,existing_files_modified=0,
        protected_preferences_and_existing_settings_unchanged=True,Git_index_HEAD_preserved=True,
        preexisting_tracked_modifications=['backend/data/faculty_preferences.json','backend/data/ga_settings.json'],
        tests=dict(latest_command=latest['path'],passed=88,failed=0,skipped=0,new_policy_cases=25,existing_audit_cases=33,existing_D10_cases=30,warnings=1),
        attempts=[dict(path=a['path'],exit_code=a['exit_code']) for a in attempts],historical_artifact_entries_reverified=historical,
        preserved_verifier_diagnostic='docs/testing/faculty-policy-qualification/audit-attempt-01.json',
        verifier_correction='Own manifest link creation order only; no preservation or policy test failure',
        privacy_findings=0,privacy_scope='Fictional numerical records only; no institutional rows parsed. Credential/key/complete and truncated encoded patterns and log sensitivity scanned; no auth/session evidence or screenshots created.',
        actual_browser='NOT_RUN_POLICY_QUALIFICATION_ONLY',frontend_build_lint='NOT_RUN_NO_FRONTEND_CHANGES',
        database_operations=0,dependencies_installed=0,staged_files=0,commits_pushes=0,
        limitations=['Formal manuscript unavailable; all choices pending approval',
            '13 allocation controls are analytical, not generated hard-valid schedules',
            'No alternative scorer integrated or GA-quality/convergence comparison performed',
            'No actual institutional cohort reconciliation or persistent closure inventory',
            'D10 authority is fictional; no live HTTP/PostgreSQL or institutional validation'],
        hash_convention='Raw bytes; manifest excludes itself; previous evidence unchanged')
    body=json.dumps(record,indent=2)+'\n'
    assert not any(p.search(body) for p in patterns)
    # Rerunning this verifier refreshes only this new milestone manifest.
    (BASE/'manifest.json').write_text(body,encoding='utf-8',newline='\n')
    assert (BASE/'manifest.json').is_file()
    print(json.dumps(dict(existing_paths_preserved=len(baseline),academic_files_preserved=23,new_files=len(inventory),
        artifacts_hashed=len(artifacts),passed=88,privacy_findings=0,historical_entries_verified=historical,
        formal_thesis_alignment='UNVERIFIED',institutional_activation='BLOCKED')))


if __name__=='__main__':main()
