"""Phase 6 raw-byte preservation, privacy and evidence integrity audit."""
import ast
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import re
import os
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
SOURCES={'backend/benchmarks/reconstruction_phase6.py','backend/benchmarks/reconstruction_benchmark.py',
         'backend/benchmarks/reconstruction_operations.py','backend/tests/performance/test_reconstruction_phase6.py',
         'docs/ga-reconstruction-phase6.md'}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for k,v in value.items():yield str(k);yield from strings(v)
    elif isinstance(value,list):
        for v in value:yield from strings(v)


def main():
    baseline=json.loads((BASE/'preservation-baseline.json').read_text())
    assert len(baseline)==1550 and all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in baseline.items()),'BASELINE_MISMATCH_STOP_NO_REPAIR'
    assert sum(p.startswith('backend/data/') for p in baseline)==23
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()=='1423812e13a5791a550c893ef6b17bfef4b4ebfb'
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT).strip()
    changed=set(filter(None,subprocess.check_output(['git','diff','--name-only','-z'],cwd=ROOT).decode().split('\0')))
    assert changed=={'backend/data/faculty_preferences.json','backend/data/ga_settings.json'}
    untracked=set(filter(None,subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')))
    own=untracked-set(baseline)
    assert SOURCES<=own and all(p in SOURCES or p.startswith('docs/testing/ga-reconstruction-phase6/') for p in own),'UNEXPECTED_NEW_PATH_STOP'
    sys.path.insert(0,str(ROOT/'backend'))
    from services.evidence_sanitization import ENCODED,URI,PEM,SENSITIVE
    patterns=[ENCODED,URI,PEM,re.compile(r'(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_=.-]+'),re.compile(r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}')]
    artifacts=[];tests=[];summaries=[];invalid=[];mirror_records=[]
    for relative in sorted(own-{'docs/testing/ga-reconstruction-phase6/manifest.json'}):
        path=ROOT/relative;assert path.suffix in {'.py','.md','.json'}
        text=path.read_text(encoding='utf-8');assert all(line==line.rstrip() for line in text.splitlines()),relative
        values=[text]
        if path.suffix=='.py':ast.parse(text)
        if path.suffix=='.json':
            data=json.loads(text);values=list(strings(data))
            if path.name=='command.json':
                assert not any(SENSITIVE.search(line) for key in ('stdout','stderr') for line in data.get(key,'').splitlines()),'SENSITIVE_LOG_WITHHELD'
                tests.append({'path':relative,'selection':data['selection'],'exit_code':data['exit_code'],
                              'pytest_summary':data['stdout'].splitlines()[-1] if data['stdout'].splitlines() else ''})
                if data['selection']=='v1':
                    assert data['exit_code']==1 and '3 failed, 1 passed' in data['stdout'] and 'INSTITUTIONAL_TEXT_PARSE_REJECTED' in data['stdout']
                if data['selection']=='v1-mirror':mirror_records.append(data)
            elif path.name=='summary.json':summaries.append({'path':relative,'record':data})
            elif path.name=='validity.json':invalid.append({'path':relative,'record':data})
            elif path.name=='analysis.json':
                assert all(sha(ROOT/p)==h for p,h in data['input_sha256'].items())
        assert not any(p.search(v) for p in patterns for v in values),'SENSITIVE_VALUE_WITHHELD'
        artifacts.append({'path':relative,'sha256':sha(path),'bytes':path.stat().st_size})
    successful_tests={};latest_tests={}
    for record in tests:
        latest_tests[record['selection']]=record
    for key,record in latest_tests.items():
        if key=='v1':continue  # preserved direct-archive privacy rejection, not relabeled a pass
        assert record['exit_code']==0,'LATEST_TEST_ATTEMPT_NOT_SUCCESSFUL'
        match=re.search(r'(\d+) passed',record['pytest_summary']);assert match
        successful_tests[key]={'path':record['path'],'passed':int(match[1])}
    assert set(successful_tests)>={'phase6','regressions','phase5','v1-mirror'}
    assert successful_tests['regressions']['passed']==81 and successful_tests['phase5']['passed']==11
    assert successful_tests['v1-mirror']['passed']==4
    mirrored=mirror_records[-1]
    assert mirrored['verified_fictional_checkpoint_archives']==3 and mirrored['engine_fingerprint_matches_original_current_release']
    assert mirrored['actual_owned_input_fingerprint_verified'] and not mirrored['fingerprint_functions_replaced'] and not mirrored['original_academic_access_permitted']
    counts={}
    for part,expected in [('reference',9),('profile',9),('timing',54),('memory',27),('operations',9)]:
        selected=[r for r in summaries if r['record'].get('part')==part and '-baseline-profile/' not in r['path']]
        assert selected,part
        records=selected[-1]['record']['results'];assert len(records)==expected and all(r['status']=='SUCCESS' for r in records)
        counts[part]=expected
    assert len(invalid)==1
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    report={'phase':'Phase 6 isolated reconstruction/copying feasibility','recorded_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),
            'python':sys.version,'platform':platform.platform(),'processor':platform.processor(),'logical_processors':os.cpu_count(),
            'baseline_paths_preserved':1550,'academic_files_preserved':23,'existing_files_modified':0,
            'original_GA_scoring_RNG_workload_migrations_checkpoints_schedules_prior_evidence_preserved':True,
            'protected_preferences_and_settings_preserved':True,'Git_index_HEAD_preserved':True,
            'new_file_inventory':sorted(own|{'docs/testing/ga-reconstruction-phase6/manifest.json'}),'artifacts':artifacts,
            'all_test_attempts':tests,'final_successful_tests':successful_tests,
            'direct_workspace_V1_archive_block':'Three direct V1 tests failed closed before academic text access; unchanged tests separately pass in fully fictional source-byte-identical mirror. Original guard never relaxed.',
            'fictional_V1_mirror':{k:mirrored[k] for k in ('verified_fictional_checkpoint_archives','source_files_byte_identical',
                'engine_fingerprint_matches_original_current_release','actual_owned_input_fingerprint_verified','fingerprint_functions_replaced')},
            'fresh_final_tests_passed':sum(r['passed'] for r in successful_tests.values()),'completed_experiment_workers':counts,
            'all_experiment_summaries_preserved':[r['path'] for r in summaries],
            'invalid_preliminary_profile_evidence_preserved':invalid,
            'privacy_findings':0,'privacy_scope':'Structural fictional fixtures, sanitized logs, complete/truncated encoded receipts and credential patterns. No institutional rows/names parsed.',
            'production_optimization':False,'production_symbols_replaced':False,'production_GC_allocator_settings_changed':False,
            'PostgreSQL_operations':0,'dependencies_installed':0,'staging_commit_push_operations':0,
            'hash_scope':'Raw bytes; manifest excludes itself. Existing 1550 files independently compared before creation.'}
    encoded=(json.dumps(report,indent=2)+'\n').encode();assert not any(p.search(encoded.decode()) for p in patterns)
    (BASE/'manifest.json').write_bytes(encoded)
    print(json.dumps({'preserved_paths':1550,'artifacts_hashed':len(artifacts),'new_files':len(report['new_file_inventory']),
                      'fresh_final_tests_passed':report['fresh_final_tests_passed'],'privacy_findings':0}))


if __name__=='__main__':main()
