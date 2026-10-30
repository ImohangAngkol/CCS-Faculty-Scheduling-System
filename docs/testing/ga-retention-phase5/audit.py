"""Phase 5 privacy/integrity audit: fingerprints only, no academic parsing."""
import ast
from collections import Counter
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'docs/testing/ga-retention-phase5'
SOURCES={'backend/benchmarks/retention_runtime.py','backend/benchmarks/retention_phase5.py',
         'backend/benchmarks/retention_ownership.py','backend/benchmarks/retention_child.py',
         'backend/tests/performance/test_retention_phase5.py','docs/ga-retention-phase5.md'}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for k,v in value.items():
            yield str(k);yield from strings(v)
    elif isinstance(value,list):
        for v in value:yield from strings(v)


def main():
    baseline=json.loads((BASE/'preservation-baseline.json').read_text())
    assert len(baseline)==1509 and all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in baseline.items()),'BASELINE_MISMATCH_STOP_NO_REPAIR'
    assert sum(p.startswith('backend/data/') for p in baseline)==23
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()=='1423812e13a5791a550c893ef6b17bfef4b4ebfb'
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT).strip()
    changed=set(filter(None,subprocess.check_output(['git','diff','--name-only','-z'],cwd=ROOT).decode().split('\0')))
    assert changed=={'backend/data/faculty_preferences.json','backend/data/ga_settings.json'}
    untracked=set(filter(None,subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')))
    own=untracked-set(baseline)
    assert SOURCES<=own and all(p in SOURCES or p.startswith('docs/testing/ga-retention-phase5/') for p in own)
    sys.path.insert(0,str(ROOT/'backend'))
    from services.evidence_sanitization import ENCODED,URI,PEM,SENSITIVE
    patterns=[ENCODED,URI,PEM,re.compile(r'(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_=.-]+'),re.compile(r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}')]
    artifacts=[];jobs=[];tests={};checkpoints=[];summaries=[]
    for relative in sorted(own-{'docs/testing/ga-retention-phase5/manifest.json'}):
        path=ROOT/relative;assert path.suffix in {'.py','.md','.json'}
        text=path.read_text(encoding='utf-8');assert all(line==line.rstrip() for line in text.splitlines()),relative
        values=[text]
        if path.suffix=='.py':ast.parse(text)
        if path.suffix=='.json':
            data=json.loads(text);values=list(strings(data))
            if path.name=='command.json':
                tests[data['selection']]={'path':relative,'exit_code':data['exit_code'],'stdout':data['stdout']}
                assert not any(SENSITIVE.search(line) for key in ('stdout','stderr') for line in data.get(key,'').splitlines())
            elif 'config' in data and 'events' in data:jobs.append((relative,data))
            elif 'checkpoint-ownership' in path.parent.name:checkpoints.append((relative,data))
            elif path.name=='summary.json':summaries.append((relative,data))
            elif path.name=='analysis.json':
                assert all(sha(ROOT/entry['path'])==entry['sha256'] for entry in data['inputs'])
        assert not any(p.search(v) for p in patterns for v in values),'SENSITIVE_VALUE_WITHHELD'
        artifacts.append({'path':relative,'sha256':sha(path),'bytes':path.stat().st_size})
    for key,count in [('phase5',11),('regressions',81)]:
        assert tests[key]['exit_code']==0 and re.search(r'\b'+str(count)+r' passed\b',tests[key]['stdout'])
        tests[key]={'path':tests[key]['path'],'passed':count,'failed':0}
    success=[(p,d) for p,d in jobs if d['status']=='SUCCESS']
    failures=[{'path':p,'status':d['status'],'exit_code':d['exit_code']} for p,d in jobs if d['status']!='SUCCESS']
    assert len(failures)==1 and failures[0]['exit_code']==1
    required={'reference-small','reference-medium','reference-large','ram-small-A','ram-small-B','ram-medium-A','ram-medium-B',
              'trace-small','trace-medium','observer-small','observer-medium','ram-large','trace-large','light-small','light-medium',
              'ownership-small-retain_last','ownership-small-final_only','ownership-medium-retain_last','ownership-medium-final_only'}
    assert {d['config']['name'] for _,d in success}==required
    outputs={};measured=0;warmups=0;roots_live=0
    for path,job in success:
        summary=job['events'][-1];config=job['config']
        assert summary['status']=='SUCCESS' and summary['bootstrap']=={'used':True,'csv_reads_substituted':7,'json_reads_substituted':2}
        for event in job['events']:
            if event['event']!='run':continue
            record=event['record'];measured+=record['label']=='measured';warmups+=record['label']=='warmup'
            assert record['hard_constraints'].startswith('PASS')
            roots_live+=record['released_roots']['sampled_model_count_alive']+record['released_roots']['reporting_leases_alive']
            assert record['after_release_gc']['model_counts']==summary['post_warmup_baseline']['model_counts']
            key=(config['scenario'],json.dumps(summary['parameters'],sort_keys=True),record['seed'])
            fingerprint=(record['best_assignment_sha256'],record['history'],record['final_rng_sha256'])
            if key in outputs:assert outputs[key]==fingerprint
            outputs[key]=fingerprint
        if config.get('drop_reports'):
            assert summary['report_buffer_release']['released_worker_run_records']==len(config['warmup'])+len(config['seeds'])
    assert roots_live==0
    assert len(checkpoints)==2 and {d['result']['scenario'] for _,d in checkpoints}=={'small','medium'}
    for _,data in checkpoints:
        result=data['result'];assert result['status']=='SUCCESS'
        assert result['mutable_original_clone_intersection']==result['mutable_best_population_intersection']==0
        assert result['mutation_isolation'] and result['checkpoint_files_written']==0
        assert result['fingerprint_tampering'].startswith('REJECTED')
        assert result['encoded_callback_released_paused_model_roots']
        assert result['in_memory_checkpoint_continuation'].startswith('EXACT')
    assert '<!--' not in (ROOT/'docs/ga-retention-phase5.md').read_text()
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    report={'phase':'Phase 5 retention/copy ownership investigation','recorded_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),
            'baseline_paths_preserved':1509,'academic_files_preserved':23,'existing_files_modified':0,
            'original_GA_scoring_RNG_workload_checkpoints_preserved':True,'protected_preferences_and_settings_preserved':True,
            'Git_index_HEAD_preserved':True,'new_file_inventory':sorted(own|{'docs/testing/ga-retention-phase5/manifest.json'}),
            'artifacts':artifacts,'tests':tests,'fresh_tests_passed':92,
            'successful_jobs':[{'path':p,'name':d['config']['name']} for p,d in success],
            'historical_failed_jobs':failures,'measured_engine_runs':measured,'warmup_engine_runs':warmups,
            'all_released_sampled_roots_alive':roots_live,'all_post_release_model_counts_match_prepared_baseline':True,
            'cross_worker_seed_assignment_history_rng_parity':True,'checkpoint_ownership_records':[p for p,_ in checkpoints],
            'privacy_findings':0,'privacy_scope':'Structural fictional inputs, sanitized logs and secret/receipt patterns; institutional names/rows are not parsed by the audit',
            'benchmark_database_or_publication_operations':0,'regression_scope':'Owned fictional SQLite/checkpoint fixtures; no PostgreSQL',
            'production_GC_allocator_settings_changed':False,'dependencies_installed':0,'production_optimization':False,
            'limits':'900-second series workers; 768 MiB sampled working set and 1536 MiB private commit; 300-second checkpoint workers. Polling may overshoot.',
            'hash_scope':'Raw bytes; manifest excludes itself'}
    encoded=(json.dumps(report,indent=2)+'\n').encode();assert not any(p.search(encoded.decode()) for p in patterns)
    (BASE/'manifest.json').write_bytes(encoded)
    print(json.dumps({'preserved_paths':1509,'artifacts_hashed':len(artifacts),'new_files':len(report['new_file_inventory']),
                      'fresh_tests_passed':92,'measured_engine_runs':measured,'warmup_engine_runs':warmups,'privacy_findings':0}))


if __name__=='__main__':main()
