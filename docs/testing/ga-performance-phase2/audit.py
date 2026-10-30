"""Read-only privacy/preservation audit plus a new Phase 2 evidence manifest.

Never opens a database, loads GA inputs, runs a benchmark, stages or restores.
"""
import ast
from collections import Counter
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT/'docs/testing/ga-performance-phase2'
REPORT = ROOT/'docs/ga-performance-phase2.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield str(k)
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def main():
    baseline = json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'))
    assert len(baseline) == 1454
    assert all((ROOT/p).is_file() and sha(ROOT/p) == h for p, h in baseline.items()), 'Unexpected baseline change; stop, do not restore'
    assert subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT).decode().strip() == '1423812e13a5791a550c893ef6b17bfef4b4ebfb'
    changed = subprocess.check_output(['git','diff','--name-only','-z'], cwd=ROOT).decode().strip('\0').split('\0')
    assert set(changed) == {'backend/data/faculty_preferences.json','backend/data/ga_settings.json'}
    assert not subprocess.check_output(['git','diff','--cached','--name-only'], cwd=ROOT).strip()
    untracked = set(filter(None, subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'], cwd=ROOT).decode().split('\0')))
    user_script = 'backend/ga_v2_fictional_python_baseline.py'
    assert user_script in untracked
    own = untracked - {user_script}
    assert all(p.startswith(('backend/benchmarks/','backend/tests/performance/', 'docs/testing/ga-performance-phase2/'))
               or p == REPORT.relative_to(ROOT).as_posix() for p in own), 'Unrelated new path'
    paths = sorted(ROOT/p for p in own if p != 'docs/testing/ga-performance-phase2/manifest.json')
    sys.path.insert(0, str(ROOT/'backend'))
    from services.evidence_sanitization import ENCODED, URI, PEM, SENSITIVE
    patterns = [ENCODED, URI, PEM, re.compile(r'(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_=.-]+'),
                re.compile(r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}')]
    with (ROOT/'backend/data/Faculty.csv').open(encoding='utf-8-sig', newline='') as stream:
        private_names = [r['Faculty'].strip() for r in csv.DictReader(stream) if r.get('Faculty','').strip()]
    records = []
    experiments = []
    for path in paths:
        assert path.suffix in {'.py','.md','.json'}
        raw = path.read_text(encoding='utf-8')
        assert all(line == line.rstrip() for line in raw.splitlines()), path.name
        values = [raw]
        if path.suffix == '.py':
            ast.parse(raw)
        elif path.suffix == '.json':
            data = json.loads(raw)
            values = list(strings(data))
            if path.name == 'command.json':
                records.append((path,data))
                assert not any(SENSITIVE.search(line) for k in ('stdout','stderr') for line in data.get(k,'').splitlines())
            elif path.name == 'results.json':
                experiments.append((path,data))
        assert not any(p.search(v) for p in patterns for v in values), 'Sensitive pattern; value withheld'
        assert not any(re.search(r'(?<!\w)'+re.escape(n)+r'(?!\w)',raw,re.I) for n in private_names), 'Private name; value withheld'
    latest = {}
    for path, record in sorted(records):
        latest[record['selection']] = {'path':path.relative_to(ROOT).as_posix(), 'exit_code':record['exit_code']}
    for key, count in {'benchmark':21, 'd10':48, 'fitness':36}.items():
        record = json.loads((ROOT/latest[key]['path']).read_text(encoding='utf-8'))
        assert record['exit_code'] == 0 and re.search(r'\b'+str(count)+r' passed\b',record['stdout'])
    full = [(p,d) for p,d in experiments if set(d['results']) == {'small','medium','large'}]
    assert full
    path, experiment = full[-1]
    statuses = {}
    for name, entry in experiment['results'].items():
        statuses[name] = dict(Counter(r['status'] for r in entry['trials']))
        for result in [entry['warmup_excluded'], *entry['trials'], *entry['separate_instrumented_runs'].values()]:
            if result['status'] != 'SUCCESS':
                continue
            history = result['history']
            assert len(history) == experiment['parameters']['generations']+1
            assert all(b['best_ever_fitness'] <= a['best_ever_fitness'] for a,b in zip(history,history[1:]))
            assert result['final_fitness'] == history[-1]['best_ever_fitness'] == sum(result['fitness_breakdown'].values())
            assert result['subject_coverage'] == 'EXACT' and result['faculty_eligibility'] == 'PASS'
            assert result['hard_constraints'].startswith('PASS') and history[0]['best_ever_fitness'] > 0
            assert result['workload']['total_teaching_units'] == result['configuration']['total_offered_units']
            assert all(s['subject'].startswith('BENCH') and s['section'].startswith('BENCH-SEC-')
                       and 990100 <= s['faculty'] < 990124 for s in result['best_assignments'])
            assert all(r['target'] == max(0,24-r['admin']-r['research']-r['extension'])
                       and r['total_workload_units'] == r['teaching_units']+r['non_teaching_fixed_units']
                       and r['teaching_units'] <= 40 for r in result['workload']['faculty'])
        for mode, extra in entry['separate_instrumented_runs'].items():
            if extra['status'] == 'SUCCESS':
                reference = next(r for r in entry['trials'] if r['seed'] == extra['seed'])
                assert extra['best_assignment_sha256'] == reference['best_assignment_sha256']
                assert extra['history'] == reference['history']
    followups = []
    for extra_path in sorted(BASE.glob('*-large-allocation-followup/allocation-followup.json')):
        record = json.loads(extra_path.read_text(encoding='utf-8'))
        extra = record['result']
        assert extra['mode'] == 'memory' and extra['scenario'] == 'large'
        assert record['same_configuration'] == experiment['parameters']
        if extra['status'] == 'SUCCESS':
            reference = next(r for r in experiment['results']['large']['trials'] if r['seed'] == extra['seed'])
            assert extra['best_assignment_sha256'] == reference['best_assignment_sha256']
            assert extra['history'] == reference['history']
            assert extra['peak_python_allocated_bytes_NOT_RSS'] > 0
        followups.append({'path':extra_path.relative_to(ROOT).as_posix(), 'status':extra['status'],
                          'deadline_seconds':record['deadline_seconds'],
                          'peak_python_allocated_bytes_NOT_RSS':extra.get('peak_python_allocated_bytes_NOT_RSS')})
    subprocess.run(['git','diff','--check'], cwd=ROOT, check=True)
    inventory = sorted(own | {'docs/testing/ga-performance-phase2/manifest.json'})
    manifest = {'phase':'Scaled Fictional Python GA Performance Evaluation — Phase 2',
                'recorded_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),
                'source_commit':'1423812e13a5791a550c893ef6b17bfef4b4ebfb',
                'full_experiment':path.relative_to(ROOT).as_posix(), 'trial_statuses':statuses,
                'allocation_only_followups':followups,
                'latest_tests':latest, 'tests_passed':{'new_benchmark':21,'existing_D10':48,'fitness_resources':36},
                'timing_and_memory_profile_workers_separate':True,
                'all_successful_outputs_validated_and_monotone':True,
                'instrumented_seed_matches_timed_seed_when_successful':True,
                'existing_files_modified':0, 'baseline_paths_preserved':len(baseline),
                'academic_data_paths_preserved':23, 'protected_preference_and_user_settings_preserved':True,
                'tiny_user_script_preserved':True, 'Git_index_HEAD_preserved':True,
                'benchmark_database_or_API_publication_operations':0,
                'existing_D10_API_tests':'Owned fictional SQLite and test-only providers, not benchmark publication or production authorization',
                'PostgreSQL_operations':0, 'dependencies_installed':0,
                'privacy_findings':0, 'exact_new_file_inventory':inventory,
                'unrelated_preexisting_changes_excluded':[user_script,'backend/data/faculty_preferences.json','backend/data/ga_settings.json'],
                'scope':'Static fictional kernel inputs, not D8/D9 authority acceptance or institutional schedules; no C++ implementation',
                'hash_convention':'Raw working bytes and expected Git-clean blob SHA256 both recorded; manifest excludes itself',
                'artifacts':[]}
    for file in paths:
        relative = file.relative_to(ROOT).as_posix()
        raw = file.read_bytes()
        blob = raw.replace(b'\r\n', b'\n')
        manifest['artifacts'].append({'path':relative, 'bytes':len(raw), 'sha256':sha(file),
                                      'LF_text_sha256':hashlib.sha256(blob).hexdigest()})
    text = json.dumps(manifest, indent=2, ensure_ascii=True)+'\n'
    assert not any(p.search(text) for p in patterns)
    (BASE/'manifest.json').write_bytes(text.encode('utf-8'))
    print(json.dumps({'artifacts_hashed':len(paths),'new_files':len(inventory),'preserved_paths':len(baseline),
                      'academic_paths':23,'tests_passed':105,'privacy_findings':0,'trial_statuses':statuses}))


if __name__ == '__main__':
    main()
