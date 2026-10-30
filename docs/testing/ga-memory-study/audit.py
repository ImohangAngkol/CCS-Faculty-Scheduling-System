"""Memory evidence privacy/hash/preservation audit; no DB or GA invocation."""
import ast
import csv
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'docs/testing/ga-memory-study'
REPORT='docs/ga-memory-study.md'
SOURCES={'backend/benchmarks/memory_study.py','backend/benchmarks/memory_graphs.py',
         'backend/benchmarks/memory_observer.py','backend/tests/performance/test_memory_study.py',REPORT}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for k,v in value.items():
            yield str(k)
            yield from strings(v)
    elif isinstance(value,list):
        for v in value:yield from strings(v)


def main():
    baseline=json.loads((BASE/'preservation-baseline.json').read_text())
    assert len(baseline)==1481 and all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in baseline.items()), 'BASELINE_MISMATCH_STOP_NO_REPAIR'
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()=='1423812e13a5791a550c893ef6b17bfef4b4ebfb'
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT).strip()
    changed=set(filter(None,subprocess.check_output(['git','diff','--name-only','-z'],cwd=ROOT).decode().split('\0')))
    assert changed=={'backend/data/faculty_preferences.json','backend/data/ga_settings.json'}
    untracked=set(filter(None,subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')))
    own=untracked-set(baseline)
    assert SOURCES<=own and all(p in SOURCES or p.startswith('docs/testing/ga-memory-study/') for p in own)
    sys.path.insert(0,str(ROOT/'backend'))
    from services.evidence_sanitization import ENCODED,URI,PEM,SENSITIVE
    patterns=[ENCODED,URI,PEM,re.compile(r'(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_=.-]+'),re.compile(r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}')]
    with (ROOT/'backend/data/Faculty.csv').open(encoding='utf-8-sig',newline='') as stream:
        names=[r['Faculty'].strip() for r in csv.DictReader(stream) if r.get('Faculty','').strip()]
    artifacts=[]; tests={}; summaries=[]; observers=[]; graphs=[]
    for relative in sorted(own-{'docs/testing/ga-memory-study/manifest.json'}):
        path=ROOT/relative; assert path.suffix in {'.py','.json','.md'}
        raw=path.read_text(encoding='utf-8'); assert all(line==line.rstrip() for line in raw.splitlines()),relative
        values=[raw]
        if path.suffix=='.py':ast.parse(raw)
        if path.suffix=='.json':
            data=json.loads(raw); values=list(strings(data))
            if path.name=='command.json':
                tests[data['selection']]={'path':relative,'exit_code':data['exit_code'],'stdout':data['stdout']}
                assert not any(SENSITIVE.search(line) for k in ('stdout','stderr') for line in data.get(k,'').splitlines())
            elif path.name=='summary.json':summaries.append((path,data))
            elif path.name=='observer.json':observers.append((path,data))
            elif 'actual-graphs' in path.parent.name:graphs.append((path,data))
        assert not any(p.search(v) for p in patterns for v in values), 'SENSITIVE_VALUE_WITHHELD'
        assert not any(re.search(r'(?<!\w)'+re.escape(n)+r'(?!\w)',raw,re.I) for n in names),'PRIVATE_NAME_WITHHELD'
        artifacts.append({'path':relative,'sha256':sha(path),'bytes':path.stat().st_size})
    for key,count in [('memory',12),('regressions',105)]:
        assert tests[key]['exit_code']==0 and re.search(r'\b'+str(count)+r' passed\b',tests[key]['stdout'])
        tests[key]={'path':tests[key]['path'],'passed':count,'failed':0}
    complete=[(p,d) for p,d in summaries if len(d['statuses'])==10]
    assert complete
    main_path,summary=complete[-1]
    assert all(s['status']=='SUCCESS' for s in summary['statuses'])
    for name in ('small','medium','large'):
        for mode in ('ram','alloc'):
            result=json.loads((main_path.parent/(mode+'-'+name+'.json')).read_text())['result']
            assert result['phase2_output_matches'] and result['hard_constraints'].startswith('PASS')
            assert result['representative_model_weakrefs_alive_after_gc']==0
            if mode=='alloc':
                assert result['engine_peak_point']['traced_peak_bytes_NOT_RSS']>0
                assert result['after_release_collection']['traced_current_bytes']<result['engine_peak_point']['traced_peak_bytes_NOT_RSS']
        focused=json.loads((main_path.parent/('focused-'+name+'.json')).read_text())['result']
        assert len(focused['operations'])==10 and focused['status']=='SUCCESS'
    retention=json.loads((main_path.parent/'retention-small.json').read_text())['result']
    assert len(retention['runs'])==5 and all(r['representative_model_weakrefs_alive_after_gc']==0 and r['phase2_output_matches'] for r in retention['runs'])
    assert len(graphs)==3 and {d['result']['scenario'] for _,d in graphs}=={'small','medium','large'}
    assert all(d['result']['status']=='SUCCESS' and d['result']['phase2_output_matches'] for _,d in graphs)
    assert observers
    for name,result in observers[-1][1]['results'].items():
        assert result['status']=='SUCCESS'
        off,on=result['cases']
        assert off['representative_clones_alive_after_gc_result_kept']==0 and on['representative_clones_alive_after_gc_result_kept']==3
        assert all(r['representative_clones_alive_after_clear_gc']==0 for r in (off,on))
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    record={'scope':'Isolated fictional Python memory investigation; no optimization or native implementation',
            'recorded_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),
            'main_study':main_path.relative_to(ROOT).as_posix(),'observer_followup':observers[-1][0].relative_to(ROOT).as_posix(),
            'actual_graph_records':[p.relative_to(ROOT).as_posix() for p,_ in graphs],
            'baseline_paths_preserved':1481,'original_baseline_paths_preserved':1454,'previous_Phase2_Phase3_files_preserved':27,
            'academic_files_preserved':23,'protected_preferences_and_settings_preserved':True,'Git_index_HEAD_preserved':True,
            'existing_files_modified':0,'new_file_inventory':sorted(own|{'docs/testing/ga-memory-study/manifest.json'}),
            'artifacts':artifacts,'test_evidence':tests,'fresh_tests_passed':117,
            'main_worker_results':summary['statuses'],'privacy_findings':0,'whitespace':'PASS',
            'production_symbols_replaced':0,'benchmark_database_or_publication_operations':0,
            'regression_database_scope':'Owned fictional SQLite/store fixtures only; no PostgreSQL or institutional publication',
            'dependencies_installed':0,
            'limitations':['Traced peaks are not RSS; private commit is not resident RAM',
                'Snapshots are net live allocations, not cumulative allocation churn',
                'One seed per scale and five repeated Small executions do not establish absence of all leaks',
                'Forced post-run GC and benchmark callback retention differ from an application server lifecycle'],
            'hash_scope':'Raw bytes, manifest excludes itself'}
    encoded=(json.dumps(record,indent=2)+'\n').encode(); assert not any(p.search(encoded.decode()) for p in patterns)
    (BASE/'manifest.json').write_bytes(encoded)
    print(json.dumps({'preserved':1481,'artifacts_hashed':len(artifacts),'new_files':len(record['new_file_inventory']),
                      'fresh_Python_tests_passed':117,'privacy_findings':0}))


if __name__=='__main__':main()
