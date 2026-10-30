"""F1.5 preservation/privacy/hash audit. No application/GA/database imports."""
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
REPORT='docs/faculty-cohort-f1-5-it-qualification.md'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for key,item in value.items():yield str(key);yield from strings(item)
    elif isinstance(value,list):
        for item in value:yield from strings(item)


def main():
    baseline=json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'))
    assert len(baseline)==1790
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
    assert REPORT in own and all(p==REPORT or p.startswith('docs/testing/faculty-cohort-f1-5/') for p in own),'UNAPPROVED_PATH_STOP'
    sys.path.insert(0,str(ROOT/'backend'))
    from services.evidence_sanitization import ENCODED,URI,PEM,SENSITIVE
    patterns=[ENCODED,URI,PEM,re.compile(r'(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_=.-]+'),re.compile(r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}')]
    registry=json.loads((ROOT/'backend/data/faculty_identities.json').read_text(encoding='utf-8'))['faculty']
    # Private labels remain local to this scan; no labels or derived IDs saved.
    labels={re.sub(r'\s+',' ',s.strip()) for row in registry for s in (row['name'],*row.get('aliases',[])) if len(s.strip())>=4}
    private=[re.compile(r'(?<![A-Za-z])'+re.escape(s)+r'(?![A-Za-z])',re.I) for s in labels]
    artifacts=[];summaries=[];tests=[];extractions=[]
    manifest=BASE/'manifest.json';manifest_relative=manifest.relative_to(ROOT).as_posix()
    for relative in sorted(own-{manifest_relative}):
        path=ROOT/relative;text=path.read_text(encoding='utf-8')
        assert path.suffix in {'.py','.md','.json'}
        assert all(line==line.rstrip() for line in text.splitlines()),relative
        values=[text]
        if path.suffix=='.py':ast.parse(text)
        if path.suffix=='.json':
            data=json.loads(text);values=list(strings(data))
            if path.name=='summary.json':summaries.append((relative,data))
            if path.name=='command.json':
                assert not any(SENSITIVE.search(line) for key in ('stdout','stderr') for line in data.get(key,'').splitlines()),'SENSITIVE_LOG_WITHHELD'
                assert data['exit_code']==0
                if 'stdout' in data:tests.append((relative,data))
                else:
                    assert data['summary_sha256']==sha(path.with_name('summary.json'))
                    extractions.append(relative)
        assert not any(p.search(v) for p in [*patterns,*private] for v in values),'PRIVACY_FINDING_WITHHELD'
        artifacts.append(dict(path=relative,sha256=sha(path),bytes=path.stat().st_size))
    assert summaries and tests
    latest_summary,summary=summaries[-1];latest_tests,results=tests[-1]
    assert re.search(r'\b18 passed\b',results['stdout']) and not re.search(r'\b[1-9]\d* (failed|errors?|skipped)\b',results['stdout'])
    assert summary['registry']['identities']==11 and summary['protected_preferences_and_settings_parsed'] is False
    assert len(summary['csv_inventory'])==17 and len(summary['workbooks'])==2
    assert summary['faculty_source_coverage']['Faculty Admin, Research and Extension.csv']['registry_members_not_represented']==2
    loads=summary['workload_source_comparison']
    assert loads['comparable_numeric_vectors']==3 and loads['different_numeric_allowance_vectors']==1 and loads['unknown_numeric_vectors']==5
    assert summary['course_eligibility_coverage']['first_without_normal_eligibility_but_preassigned']==1
    assert all(w['runtime_rooms_with_both_section_styles']==5 and w['counts']['faculty_labeled_sheets_with_both_styles']==7 for w in summary['workbooks'])
    for link in re.findall(r'\]\(([^)]+)\)',(ROOT/REPORT).read_text(encoding='utf-8')):
        if not link.startswith(('http:','https:','#')):
            destination=((ROOT/REPORT).parent/link.split('#')[0]).resolve()
            assert destination==manifest or destination.is_file(),link
    previous=0
    for name in ('ga-performance-phase2','ga-performance-phase3','ga-memory-study','ga-retention-phase5','ga-reconstruction-phase6',
                 'dashboard-d15','thesis-functional-audit','faculty-policy-qualification','faculty-cohort-f1'):
        earlier=json.loads((ROOT/'docs/testing'/name/'manifest.json').read_text(encoding='utf-8'))
        for entry in earlier['artifacts']:
            assert sha(ROOT/entry['path'])==entry['sha256'],'HISTORICAL_ARTIFACT_MISMATCH'
            previous+=1
    for args in [('diff','--check'),('diff','--cached','--check')]:subprocess.run(['git',*args],cwd=ROOT,env=env,check=True)
    preservation();inventory=sorted(own|{manifest_relative})
    record=dict(milestone='F1.5 IT prototype cohort and cross-department qualification',
        recorded_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),source_HEAD=git('rev-parse','HEAD'),python=sys.version,platform=platform.platform(),
        intended_population='IT_ONLY_USER_REPORTED; no IS or full CCS evaluation claim',
        source_authority='NOT_INSTITUTIONALLY_VERIFIED',production_cohort_integration='BLOCKED',
        source_qualification='COMPLETE_WITH_DOCUMENTED_GAPS',formal_thesis_alignment='UNVERIFIED',
        new_file_inventory=inventory,new_file_type_counts=dict(Counter(Path(p).suffix for p in inventory)),artifacts=artifacts,
        baseline_files_preserved=1790,academic_files_preserved=23,existing_files_modified=0,
        protected_preferences_and_existing_settings_unchanged=True,Git_index_HEAD_preserved=True,
        latest_source_summary=latest_summary,read_only_extraction_attempts=extractions,
        latest_test_command=latest_tests,new_fictional_tests=dict(passed=18,failed=0,skipped=0),
        earlier_test_attempts_preserved=[p for p,_ in tests[:-1]],historical_artifact_entries_reverified=previous,
        analysis_refinement='Initial raw text disagreement retained; final finite numeric/unknown/format distinctions verified',
        private_record_exported=False,private_label_scan='PASS_NO_LABELS_OR_LABEL_DERIVATIVES_RECORDED',privacy_findings=0,
        private_source_scope='CSV and two XLSX read locally; aggregate schema/counts only. Protected preference JSON and settings not parsed.',
        GA_runs=0,production_code_or_policy_changes=0,database_operations=0,dependencies_installed=0,
        actual_browser='NOT_RUN_READ_ONLY_QUALIFICATION',frontend_build_lint='NOT_RUN_NO_PRODUCTION_CHANGES',
        staged_files=0,commits_pushes=0,
        limitations=['No independently complete approved IT semester roster',
            'Qualification/eligibility/load applicability and authority require owner reconciliation',
            'Cross-department row/sheet indicators are not confirmed meetings or an IS roster',
            'No workbook formula execution or verified fresh calculated totals',
            'Shared teaching-credit accounting and scoped production providers remain unqualified'],
        hash_convention='Raw bytes; manifest excludes itself; all prior evidence retained')
    body=json.dumps(record,indent=2)+'\n';assert not any(p.search(body) for p in [*patterns,*private])
    manifest.write_text(body,encoding='utf-8',newline='\n')
    print(json.dumps(dict(baseline_preserved=1790,academic_files_preserved=23,new_files=len(inventory),artifacts_hashed=len(artifacts),
        new_tests_passed=18,privacy_findings=0,historical_artifact_entries_verified=previous,
        evaluation_scope='IT_ONLY',institutional_activation='BLOCKED')))


if __name__=='__main__':main()
