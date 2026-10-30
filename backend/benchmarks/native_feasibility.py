"""Phase 3 Python feasibility analysis; native build is explicitly BLOCKED.

No production symbol replacement, compiler installation, database or publication.
An existing Phase 2 reporting helper is temporarily extended to retain all stats.
"""
from datetime import datetime, timedelta, timezone
import argparse
import hashlib
import json
from pathlib import Path
import platform
import pstats
import random
import shutil
import statistics
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
from benchmarks import scaled_python as bench

BASE = ROOT/'docs/testing/ga-performance-phase3'
PHASE2 = ROOT/'docs/testing/ga-performance-phase2/20261028T113836085281+0800/results.json'
ZONE = timezone(timedelta(hours=8))


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_entry():
    baseline = json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'))
    if not all((ROOT/p).is_file() and fingerprint(ROOT/p) == value for p, value in baseline.items()):
        raise RuntimeError('BASELINE_MISMATCH_STOP_NO_REPAIR')
    return len(baseline)


def toolchain_inventory():
    names = {name: shutil.which(name) for name in ('cl', 'clang++', 'g++', 'cmake')}
    known = (
        Path('C:/Program Files/LLVM/bin/clang++.exe'), Path('C:/msys64/ucrt64/bin/g++.exe'),
        Path('C:/msys64/mingw64/bin/g++.exe'), Path('C:/mingw64/bin/g++.exe'),
        Path('C:/Program Files/Microsoft Visual Studio'),
        Path('C:/Program Files (x86)/Microsoft Visual Studio'),
        Path('C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe'),
    )
    return {'PATH_tools': names, 'known_locations': {str(p): p.exists() for p in known},
            'user_confirmation': 'No compiler available; document blocker',
            'native_build': 'NOT_RUN_NO_COMPILER', 'native_parity': 'NOT_RUN',
            'native_timings_and_binding_overhead': 'NOT_MEASURED', 'dependencies_installed': 0,
            'proposed_binding_if_later_authorized': 'C ABI DLL with Python stdlib ctypes; no pybind11 required'}


def all_profile_rows(profiler):
    rows = []
    for (filename, line, function), (primitive, calls, own, cumulative, callers) in pstats.Stats(profiler).stats.items():
        path = Path(filename)
        display = path.relative_to(ROOT).as_posix() if path.is_absolute() and path.is_relative_to(ROOT) else path.name
        rows.append({'file': display, 'line': line, 'function': function, 'primitive_calls': primitive,
                     'total_calls': calls, 'self_seconds': own, 'cumulative_seconds': cumulative})
    return sorted(rows, key=lambda r: r['cumulative_seconds'], reverse=True)


def selected_costs(result):
    rows = result['profile_top_cumulative']  # Full table in this experiment, not just Phase 2 top 30.
    selected = [('copy.py', 'deepcopy'), ('backend/services/chromosome_service.py', '_validate_baseline_components'),
                ('backend/services/chromosome_service.py', 'time_to_minutes'),
                ('backend/services/ga_v2_constraints.py', 'minutes'),
                ('backend/services/ga_v2_constraints.py', 'overlap'),
                ('backend/services/ga_v2_constraints.py', 'external_conflict'),
                ('backend/services/ga_publication_service.py', 'validate_publication')]
    output = []
    for file, function in selected:
        matching = [r for r in rows if r['file'] == file and r['function'] == function]
        if not matching:
            output.append({'file': file, 'function': function, 'status': 'NOT_CALLED'})
            continue
        row = dict(matching[0])
        fraction = row['self_seconds']/result['engine_seconds']
        row.update(profiled_self_fraction=fraction,
                   conditional_speedup_if_self_cost_vanished=1/(1-fraction),
                   interpretation='Profile-based optimistic bound only; not uninstrumented engine speedup')
        output.append(row)
    return output


def oracle():
    bench.runtime()  # Suppress legacy import output before importing the actual oracle.
    from services.ga_v2_constraints import overlap
    return overlap


def numeric_rows(assignments):
    """Explicit conversion boundary, using original strict time parser.

    Pair each saved meeting slot with the fictional 09:00-10:00 reservation.
    Days/resource equality are NOT removed from production validation: this is
    only a controlled predicate workload, not an external-conflict replacement.
    """
    bench.runtime()
    from services.ga_v2_constraints import minutes
    return [(minutes(start), minutes(end), 540, 600)
            for subject in assignments for component in subject['components']
            for day, start, end in component['blocks']]


def batch_oracle(rows):
    fn = oracle()
    return [fn(a, b, c, d) for a, b, c, d in rows]


def summary(samples):
    return {'samples_seconds': samples, 'mean_seconds': statistics.mean(samples),
            'median_seconds': statistics.median(samples), 'min_seconds': min(samples),
            'max_seconds': max(samples), 'sample_sd_seconds': statistics.stdev(samples) if len(samples) > 1 else None}


def microbench(entry, repetitions=9, loops=200):
    fn = oracle()
    assignments = entry['trials'][0]['best_assignments']
    tick = time.perf_counter_ns()
    rows = numeric_rows(assignments)
    first_conversion = (time.perf_counter_ns()-tick)/1e9
    tick = time.perf_counter_ns()
    first_value = fn(*rows[0])
    first_scalar = (time.perf_counter_ns()-tick)/1e9
    expected = [fn(*row) for row in rows]
    scalar, batch, conversion = [], [], []
    # Timing-only: no profiler, tracemalloc, DB or concurrent worker.
    for _ in range(repetitions):
        tick = time.perf_counter_ns()
        for repeat in range(loops):
            for row in rows:
                fn(*row)
        scalar.append((time.perf_counter_ns()-tick)/1e9/(loops*len(rows)))
        tick = time.perf_counter_ns()
        for repeat in range(loops):
            actual = [fn(a,b,c,d) for a,b,c,d in rows]
        assert actual == expected
        batch.append((time.perf_counter_ns()-tick)/1e9/loops)
        tick = time.perf_counter_ns()
        for repeat in range(loops):
            converted = numeric_rows(assignments)
        assert converted == rows
        conversion.append((time.perf_counter_ns()-tick)/1e9/loops)
    return {'row_count': len(rows), 'loops_per_repetition': loops, 'repetitions': repetitions,
            'row_sha256': hashlib.sha256(json.dumps(rows).encode()).hexdigest(),
            'first_observed_conversion_seconds': first_conversion,
            'first_observed_scalar_seconds': first_scalar,
            'first_scalar_value': first_value,
            'cold_scope': 'First observed predicate/conversion after runtime imports; NOT fresh-process cold start',
            'warmed_python_scalar_seconds_per_pair': summary(scalar),
            'warmed_python_batch_seconds_per_batch': summary(batch),
            'original_text_to_numeric_seconds_per_batch': summary(conversion),
            'native_scalar': 'NOT_MEASURED', 'native_batch': 'NOT_MEASURED',
            'native_conversion_or_binding_cost': 'NOT_MEASURED',
            'scope': 'Python reference calls and conversion only, NOT a complete resource validator or GA acceleration'}


def prior_bound(phase2):
    answer = {}
    for name, entry in phase2['results'].items():
        result = entry['separate_instrumented_runs']['profile']
        row = next(r for r in result['profile_top_cumulative'] if r['function'] == '_validate_baseline_components')
        f = row['cumulative_seconds']/result['engine_seconds']
        answer[name] = {'entire_component_cumulative_fraction': f,
                        'optimistic_ceiling_if_entire_component_function_free': 1/(1-f),
                        'self_fraction': row['self_seconds']/result['engine_seconds'],
                        'warning': 'Entire component removal is impossible for a tiny numeric predicate; nested parsing/allocation remain. Instrumented fractions do not prove uninstrumented share.'}
    return answer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=['all', 'small', 'medium', 'large'], default='all')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    verify_entry()
    source = json.loads(PHASE2.read_text(encoding='utf-8'))
    if args.worker:
        assert args.scenario != 'all'
        Parameters = bench.runtime()[-1]
        with patch.object(bench, 'profile_rows', all_profile_rows):
            result = bench.measure(args.scenario, 714, Parameters(**source['parameters']), 'profile')
        result['exclusive_cost_analysis'] = selected_costs(result) if result['status'] == 'SUCCESS' else []
        print(json.dumps(result, allow_nan=False))
        return 0 if result['status'] == 'SUCCESS' else 1
    started = datetime.now(ZONE)
    directory = BASE/started.strftime('%Y%m%dT%H%M%S%f+0800')
    directory.mkdir(exist_ok=False)
    inventory = toolchain_inventory()
    names = list(source['results']) if args.scenario == 'all' else [args.scenario]
    results = {}
    allowed = {'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA',
               'PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','PATHEXT'}
    import os
    env = {k:v for k,v in os.environ.items() if k.upper() in allowed}
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED='0', PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    for name in names:
        command = [sys.executable, '-B', str(Path(__file__).resolve()), '--worker', '--scenario', name]
        try:
            reply = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True,
                                   encoding='utf-8', timeout=240)
            result = json.loads(reply.stdout) if reply.returncode == 0 else {'status':'WORKER_FAILED','raw_error_withheld':True}
        except subprocess.TimeoutExpired:
            result = {'status':'WALL_DEADLINE_EXCEEDED','deadline_seconds':240}
        if result['status'] == 'SUCCESS':
            reference = source['results'][name]['trials'][0]
            assert result['history'] == reference['history']
            assert result['best_assignment_sha256'] == reference['best_assignment_sha256']
            result['phase2_seed714_output_matches'] = True
        results[name] = result
        print(json.dumps({'scenario':name,'status':result['status']}), file=sys.stderr, flush=True)
    # Microbench after profile workers, not concurrent; fresh wall observations.
    measurements = {name:microbench(source['results'][name]) for name in names}
    record = {'scope':'Python feasibility profiling only; compiler unavailable, no native implementation or parity claim',
              'started_at':started.isoformat(), 'finished_at':datetime.now(ZONE).isoformat(),
              'python':sys.version, 'platform':platform.platform(), 'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
              'phase2_source':PHASE2.relative_to(ROOT).as_posix(), 'phase2_sha256':fingerprint(PHASE2),
              'pre_implementation_upper_bound':prior_bound(source), 'toolchain':inventory,
              'native_build_seconds':None, 'native_parity_cases':None,
              'profiles':results, 'python_reference_measurements':measurements,
              'preserved_entry_paths':verify_entry(), 'database_operations':0,
              'actual_accelerated_engine_executions':0, 'compiler_or_binding_installations':0}
    (directory/'study.json').write_bytes((json.dumps(record,indent=2,allow_nan=False)+'\n').encode('utf-8'))
    print(json.dumps({'evidence':directory.relative_to(ROOT).as_posix(),'native_status':'NOT_RUN_NO_COMPILER'}))
    return 0 if all(r['status']=='SUCCESS' for r in results.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
