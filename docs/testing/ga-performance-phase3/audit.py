"""Phase 3 local file/privacy/hash audit. No DB, GA execution or Git mutation."""
import ast
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'docs/testing/ga-performance-phase3'
MANIFEST=BASE/'manifest.json'
SOURCES={'backend/benchmarks/native_feasibility.py','backend/tests/performance/test_native_feasibility.py',
         'docs/ga-performance-phase3.md'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strings(value):
    if isinstance(value,str):
        yield value
    elif isinstance(value,dict):
        for k,v in value.items():
            yield str(k)
            yield from strings(v)
    elif isinstance(value,list):
        for v in value:
            yield from strings(v)


def main():
    baseline=json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'))
    assert len(baseline)==1471
    assert all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in baseline.items()), 'BASELINE_MISMATCH_STOP_NO_REPAIR'
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()=='1423812e13a5791a550c893ef6b17bfef4b4ebfb'
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT).strip()
    changed=set(filter(None,subprocess.check_output(['git','diff','--name-only','-z'],cwd=ROOT).decode().split('\0')))
    assert changed=={'backend/data/faculty_preferences.json','backend/data/ga_settings.json'}
    untracked=set(filter(None,subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')))
    own=untracked-set(baseline)
    assert all(p in SOURCES or p.startswith('docs/testing/ga-performance-phase3/') for p in own), 'UNRELATED_NEW_PATH'
    assert SOURCES<=own
    sys.path.insert(0,str(ROOT/'backend'))
    from services.evidence_sanitization import ENCODED,URI,PEM,SENSITIVE
    patterns=[ENCODED,URI,PEM,re.compile(r'(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_=.-]+'),re.compile(r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}')]
    with (ROOT/'backend/data/Faculty.csv').open(encoding='utf-8-sig',newline='') as stream:
        names=[r['Faculty'].strip() for r in csv.DictReader(stream) if r.get('Faculty','').strip()]
    artifacts=[]; tests={}; studies=[]
    for relative in sorted(own-{'docs/testing/ga-performance-phase3/manifest.json'}):
        path=ROOT/relative
        assert path.suffix in {'.py','.md','.json'}
        raw=path.read_text(encoding='utf-8')
        assert all(line==line.rstrip() for line in raw.splitlines()), relative
        values=[raw]
        if path.suffix=='.py':
            ast.parse(raw)
        if path.suffix=='.json':
            data=json.loads(raw); values=list(strings(data))
            if path.name=='command.json':
                tests[data['selection']]={'path':relative,'exit_code':data['exit_code'],'stdout':data['stdout']}
                assert not any(SENSITIVE.search(line) for k in ('stdout','stderr') for line in data.get(k,'').splitlines())
            elif path.name=='study.json':
                studies.append((relative,data))
        assert not any(p.search(v) for p in patterns for v in values), 'SENSITIVE_PATTERN_VALUE_WITHHELD'
        assert not any(re.search(r'(?<!\w)'+re.escape(n)+r'(?!\w)',raw,re.I) for n in names), 'PRIVATE_NAME_VALUE_WITHHELD'
        artifacts.append({'path':relative,'sha256':sha(path),'bytes':path.stat().st_size})
    for key,count in [('oracle',46),('regressions',105)]:
        assert tests[key]['exit_code']==0 and re.search(r'\b'+str(count)+r' passed\b',tests[key]['stdout'])
        tests[key]={'path':tests[key]['path'],'passed':count,'failed':0,'native_parity':False}
    assert studies
    study_path,study=studies[-1]
    assert set(study['profiles'])=={'small','medium','large'}
    for result in study['profiles'].values():
        assert result['status']=='SUCCESS' and result['phase2_seed714_output_matches']
        assert result['best_ever_monotone'] and result['hard_constraints'].startswith('PASS')
        assert any(r['function']=='overlap' and r['file']=='backend/services/ga_v2_constraints.py' for r in result['profile_top_cumulative'])
    assert study['native_parity_cases'] is None and study['actual_accelerated_engine_executions']==0
    assert study['toolchain']['native_build']=='NOT_RUN_NO_COMPILER'
    assert not any(study['toolchain']['PATH_tools'].values())
    assert not any(study['toolchain']['known_locations'].values())
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    record={'phase':'Phase 3 C++ feasibility: Python analysis complete, native portion BLOCKED',
            'recorded_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),
            'source_commit':'1423812e13a5791a550c893ef6b17bfef4b4ebfb',
            'baseline_paths_preserved':1471,'original_phase2_baseline_preserved':1454,'phase2_files_preserved':17,
            'academic_files_preserved':23,'protected_preferences_and_user_settings_unchanged':True,
            'Git_index_HEAD_unchanged':True,'existing_files_modified':0,'new_file_inventory':sorted(own|{'docs/testing/ga-performance-phase3/manifest.json'}),
            'study':study_path,'test_evidence':tests,'new_python_oracle_cases':46,'existing_regressions':105,
            'profiled_unmodified_engine_runs':3,'native_parity_cases_executed':0,'native_builds':0,
            'native_or_accelerated_engine_timings':'NOT_MEASURED_NO_COMPILER',
            'production_integration':False,'database_or_publication_operations':0,'dependencies_installed':0,
            'privacy_findings':0,'whitespace_check':'PASS','artifacts':artifacts,
            'hash_scope':'Raw bytes; manifest excludes itself. Original and Phase 2 files verified, not rewritten.'}
    encoded=(json.dumps(record,indent=2)+'\n').encode()
    assert not any(p.search(encoded.decode()) for p in patterns)
    MANIFEST.write_bytes(encoded)
    print(json.dumps({'preserved':1471,'artifacts_hashed':len(artifacts),'new_files':len(record['new_file_inventory']),
                      'Python_tests_passed':151,'native_parity':'NOT_RUN','privacy_findings':0}))


if __name__=='__main__':
    main()
