"""Python-only scaled fictional GA kernel benchmark. No API/DB/publication.

Run from the repository root with backend/benchmarks/scaled_python.py.
Each CLI trial has a fresh interpreter, deterministic hash seed and wall deadline.
Timing, tracemalloc and cProfile run in separate workers. No dependencies added.
"""
import argparse
from collections import Counter
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from contextvars import ContextVar
import cProfile
from datetime import datetime, timedelta, timezone
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import pstats
import random
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / 'backend'
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
from benchmarks.scenarios import SCENARIOS, build, snapshot

VERSION = 'scaled-fictional-python.1'
ZONE = timezone(timedelta(hours=8))
_active = ContextVar('benchmark_no_io', default=False)
_runtime = None


class BenchmarkSafetyError(RuntimeError):
    pass


def _audit(event, args):
    if not _active.get():
        return
    if event in {'socket.connect', 'socket.bind', 'sqlite3.connect'}:
        raise BenchmarkSafetyError('NETWORK_OR_DATABASE_ACCESS_REJECTED')
    if event == 'open':
        _, mode, flags = args
        if (isinstance(mode, str) and any(v in mode for v in 'wax+')) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
            raise BenchmarkSafetyError('BENCHMARK_KERNEL_WRITE_REJECTED')
    if event in {'os.mkdir', 'os.remove', 'os.rename', 'os.rmdir', 'os.truncate', 'os.chmod', 'os.link', 'os.symlink'}:
        raise BenchmarkSafetyError('BENCHMARK_KERNEL_WRITE_REJECTED')


sys.addaudithook(_audit)


@contextmanager
def no_io():
    import psycopg2
    token = _active.set(True)
    try:
        with patch.object(psycopg2, 'connect', side_effect=BenchmarkSafetyError('POSTGRESQL_ACCESS_REJECTED')):
            yield
    finally:
        _active.reset(token)


def runtime():
    global _runtime
    if _runtime is None:
        # Legacy imports read academic inputs; never export their stdout/rows.
        with open(os.devnull, 'w', encoding='utf-8') as sink, redirect_stdout(sink), redirect_stderr(sink):
            from services import ga_v2_engine as engine
            from genetic_algorithm.operators import FitnessFunction as fitness
            from genetic_algorithm.utils.FrozenInputs import scoring_inputs
            from genetic_algorithm.models.ga_setting import GASetting
            from services.ga_v2_store import engine_fingerprint
            from schemas.ga_constrained import Parameters
        _runtime = engine, fitness, scoring_inputs, GASetting, engine_fingerprint, Parameters
    return _runtime


@contextmanager
def synthetic_scoring(values, rows, settings):
    """Override data locations/universe only, restore them even on failure.

    The unmodified freeze()/fitness implementations read new owned hypothetical
    files through their original loaders. No scoring/RNG/operator function is
    replaced. Fingerprints stay genuine and are never spoofed for continuation.
    Single-threaded standalone use only; not a deployment configuration.
    """
    engine, fitness, *_ = runtime()
    with tempfile.TemporaryDirectory(prefix='ga-fictional-scoring-') as temporary:
        root = Path(temporary)
        pref, config = root / 'fictional-preferences.json', root / 'fictional-settings.json'
        pref.write_bytes(json.dumps(rows).encode())
        config.write_bytes(json.dumps(settings).encode())
        with patch.object(fitness, 'PREFERENCE_FILE', pref), patch.object(fitness, 'GA_SETTINGS_FILE', config), \
                patch.object(engine.schedule, 'list_faculty', values[1]):
            yield


def signature(candidate):
    """Only explicit fictional identifiers, never objects/default reprs."""
    result = []
    for s in candidate:
        components = []
        for kind in ('lecture', 'laboratory'):
            room = getattr(s, kind + '_room')
            blocks = sorted((str(day), b.start_time, b.end_time)
                            for day, b in getattr(s, kind + '_time_blocks'))
            components.append({'component': kind, 'room': room.name if room else None, 'blocks': blocks})
        result.append({'subject': s.number, 'section': s.section.code,
                       'faculty': s.assigned_faculty.code, 'credit_units': s.credit_units,
                       'components': components})
    return sorted(result, key=lambda s: (s['subject'], s['section']))


def workload(candidate, faculty):
    loads = {f.code: 0 for f in faculty}
    for subject in candidate:
        loads[subject.assigned_faculty.code] += subject.credit_units
    rows = []
    for f in faculty:
        teaching = loads[f.code]
        target = max(0, 24-f.admin_load-f.research_load-f.extension_load)
        assert f.required_teaching_load == target and f.absolute_max_teaching_load == 40
        assert f.overload_warning_threshold == 30 and 0 <= teaching <= 40
        non_teaching = f.admin_load+f.research_load+f.extension_load
        rows.append({'faculty': f.code, 'teaching_units': teaching, 'target': target,
                     'admin': f.admin_load, 'research': f.research_load, 'extension': f.extension_load,
                     'non_teaching_fixed_units': non_teaching, 'total_workload_units': teaching+non_teaching,
                     'underload': max(0, target-teaching), 'overload': max(0, teaching-target),
                     'above_30_warning': teaching > 30,
                     'target_fulfillment': teaching/target if target else None})
    fractions = [r['target_fulfillment'] for r in rows if r['target_fulfillment'] is not None]
    return {'faculty': rows, 'total_teaching_units': sum(loads.values()),
            'total_target_units': sum(r['target'] for r in rows),
            'underload_units': sum(r['underload'] for r in rows),
            'overload_units': sum(r['overload'] for r in rows),
            'zero_assignment_count': sum(r['teaching_units'] == 0 for r in rows),
            'target_fulfillment_population_stdev': statistics.pstdev(fractions) if fractions else None}


def profile_rows(profiler):
    entries = []
    for (filename, line, name), (primitive, calls, own, cumulative, _) in pstats.Stats(profiler).stats.items():
        path = Path(filename)
        display = path.relative_to(ROOT).as_posix() if path.is_absolute() and path.is_relative_to(ROOT) else path.name
        entries.append({'file': display, 'line': line, 'function': name, 'primitive_calls': primitive,
                        'total_calls': calls, 'self_seconds': own, 'cumulative_seconds': cumulative})
    return sorted(entries, key=lambda r: r['cumulative_seconds'], reverse=True)[:30]


def measure(name, seed, parameters, mode='timing', *, witness=True):
    """No normal trial cProfile/tracemalloc. Caller RNG and contexts restored."""
    if mode not in {'timing', 'memory', 'profile'} or tracemalloc.is_tracing():
        raise ValueError('Choose one measurement mode; caller tracemalloc must be off')
    prior_rng = random.getstate()
    prior_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    result = {'scenario': name, 'seed': seed, 'mode': mode, 'status': 'NOT_STARTED',
              'history': [], 'persistence': 'NONE; no callback writes', 'persistence_seconds': None}
    profiler = None
    try:
        engine, fitness, scoring_inputs, _, engine_identity, _ = runtime()
        started = time.perf_counter()
        values, legacy, rows, settings, metadata = build(name)
        pinned = snapshot(values, metadata)
        result.update(configuration=metadata, parameters=parameters.model_dump(),
                      engine_version=engine.ENGINE_VERSION, engine_sha256=engine_identity(),
                      repository_input_sha256=pinned.catalog.input_fingerprint,
                      static_snapshot_sha256=pinned.digest)
        last = None
        calls = Counter()
        def factory(templates, restarts):
            calls['construction_calls'] += 1
            return engine.construct(templates, restarts)
        def crossover(**kwargs):
            calls['crossover_calls'] += 1
            return engine.create_child_by_faculty_swap(**kwargs)
        def mutation(**kwargs):
            calls['mutation_calls'] += 1
            return engine.mutate_by_swapping_faculty_subjects(**kwargs)
        def boundary(state):
            nonlocal last
            last = state
            result['history'].append(dict(state['history'][-1]))
            return None
        with synthetic_scoring(values, rows, settings), open(os.devnull, 'w', encoding='utf-8') as sink, \
                redirect_stdout(sink), redirect_stderr(sink), no_io():
            reduced = engine.reduced_templates(pinned, values)
            if witness:
                random.seed(10101)  # Separate deterministic constructive feasibility witness.
                proof = engine.construct(reduced, 5)
                engine.admit(proof, pinned, reduced)
                result['feasibility'] = 'CONSTRUCTIVE_WITNESS_VALIDATED; not used as a search seed'
                del proof
            else:
                result['feasibility'] = 'NOT_ESTABLISHED; witness disabled for negative test'
            result['preprocessing_seconds'] = time.perf_counter()-started
            random.seed(seed)
            gc.collect()
            if mode == 'memory':
                tracemalloc.start()
            if mode == 'profile':
                profiler = cProfile.Profile()
                profiler.enable()
            tick = time.perf_counter()
            try:
                outcome = engine.run(values, pinned, parameters, legacy, boundary,
                                     factory=factory, crossover=crossover, mutation=mutation)
            except engine.ConstraintError as error:
                result.update(status=error.code, diagnostics=dict(getattr(error, 'diagnostics', {})))
                outcome = None
            finally:
                result['engine_seconds'] = time.perf_counter()-tick
                if profiler:
                    profiler.disable()
                if mode == 'memory':
                    result['peak_python_allocated_bytes_NOT_RSS'] = tracemalloc.get_traced_memory()[1]
                    tracemalloc.stop()
            result['operator_call_attempts'] = dict(calls)
            if profiler:
                result['profile_top_cumulative'] = profile_rows(profiler)
            if outcome != 'complete':
                return result
            validation = time.perf_counter()
            assert last is not None and len(result['history']) == parameters.generations+1
            for candidate in [*last['population'], last['best']]:
                engine.admit(candidate, pinned, reduced)
                assert Counter((s.number, s.section.code) for s in candidate) == Counter((s.number, s.section.code) for s in values[0])
                assert all(s.number in s.assigned_faculty.eligible_subjects for s in candidate)
            token = scoring_inputs.set(last['scoring_inputs'])
            try:
                total, breakdown = fitness.faculty_preference_fitness(last['best'], legacy, return_breakdown=True)
            finally:
                scoring_inputs.reset(token)
            assert total == last['best_fitness'] == result['history'][-1]['best_ever_fitness']
            monotone = all(b['best_ever_fitness'] <= a['best_ever_fitness']
                           for a, b in zip(result['history'], result['history'][1:]))
            assert monotone
            assignments = signature(last['best'])
            result.update(status='SUCCESS', final_fitness=total, fitness_breakdown=breakdown,
                          best_ever_monotone=monotone, diagnostics=last['diagnostics'],
                          workload=workload(last['best'], values[1]),
                          hard_constraints='PASS: original admit/reconstruction, external conflicts, every final population member and best',
                          subject_coverage='EXACT', faculty_eligibility='PASS',
                          best_assignment_sha256=hashlib.sha256(json.dumps(assignments, sort_keys=True).encode()).hexdigest(),
                          best_assignments=assignments,
                          validation_and_breakdown_seconds=time.perf_counter()-validation)
            accepted = sum(v for k, v in last['diagnostics'].items() if k.endswith(':ACCEPTED'))
            rejected = sum(v for k, v in last['diagnostics'].items() if not k.endswith(':ACCEPTED'))
            result['admission_observations'] = {'accepted': accepted, 'rejected_or_no_candidate': rejected,
                'construction_search_failures': last['diagnostics'].get('construction:SEARCH_EXHAUSTED', 0),
                'semantics': 'Admission events, not unique candidates; survivor checks can repeat. Operator internal attempts are not instrumented.'}
    except BenchmarkSafetyError:
        raise
    except Exception as error:
        # Never serialize arbitrary exception text, object reprs, preferences or SQL.
        code = getattr(error, 'code', 'BENCHMARK_ERROR')
        result.update(status=code if isinstance(code, str) else 'BENCHMARK_ERROR', exception_type=type(error).__name__)
    finally:
        if profiler:
            profiler.disable()
        if mode == 'memory' and tracemalloc.is_tracing():
            tracemalloc.stop()
        random.setstate(prior_rng)
        sys.dont_write_bytecode = prior_bytecode
    return result


def aggregate(trials):
    complete = [t for t in trials if t['mode'] == 'timing' and t['status'] == 'SUCCESS']
    values = [t['engine_seconds'] for t in complete]
    return {'attempted_trials': len(trials), 'completed_trials': len(values),
            'failed_trials': len(trials)-len(values),
            'mean_seconds': statistics.mean(values) if values else None,
            'median_seconds': statistics.median(values) if values else None,
            'min_seconds': min(values) if values else None, 'max_seconds': max(values) if values else None,
            'sample_standard_deviation_seconds': statistics.stdev(values) if len(values) > 1 else None,
            'population_cv': statistics.pstdev(values)/statistics.mean(values) if values else None,
            'scope': 'Successful uninstrumented engine.run calls only; failed/time-limited trials retained separately. Includes internal validation, fingerprint reads and lightweight counters; not pure operator CPU time.'}


def run_worker(name, seed, parameters, mode, timeout):
    command = [sys.executable, '-B', str(Path(__file__).resolve()), '--worker', '--scenario', name,
               '--seeds', str(seed), '--mode', mode, '--population', str(parameters['population_size']),
               '--generations', str(parameters['generations']), '--fresh', str(parameters['fresh_chromosomes']),
               '--operator-attempts', str(parameters['crossover_attempts']), '--restarts', str(parameters['max_restarts']),
               '--candidate-attempts', str(parameters['candidate_attempts'])]
    allowed = {'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP', 'USERPROFILE', 'APPDATA',
               'LOCALAPPDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMDATA', 'SYSTEMDRIVE', 'PATHEXT'}
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED='0', PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    tick = time.perf_counter()
    try:
        reply = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', timeout=timeout)
    except subprocess.TimeoutExpired:
        return {'scenario': name, 'seed': seed, 'mode': mode, 'status': 'WALL_DEADLINE_EXCEEDED',
                'deadline_seconds': timeout, 'end_to_end_worker_seconds': time.perf_counter()-tick,
                'classification': 'Resource/runtime bound, not mathematical infeasibility; incomplete output withheld'}
    if reply.returncode != 0:
        return {'scenario': name, 'seed': seed, 'mode': mode, 'status': 'WORKER_FAILED',
                'exit_code': reply.returncode, 'raw_error_withheld': True}
    result = json.loads(reply.stdout)
    result['end_to_end_worker_seconds'] = time.perf_counter()-tick
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=[*SCENARIOS, 'all'], default='all')
    parser.add_argument('--seeds', default='714,715,716')
    parser.add_argument('--repetitions', type=int, default=1)
    parser.add_argument('--population', type=int, default=6)
    parser.add_argument('--generations', type=int, default=5)
    parser.add_argument('--fresh', type=int, default=1)
    parser.add_argument('--operator-attempts', type=int, default=3)
    parser.add_argument('--restarts', type=int, default=5)
    parser.add_argument('--candidate-attempts', type=int, default=3)
    parser.add_argument('--trial-timeout', type=int, default=120)
    parser.add_argument('--profile', action='store_true')
    parser.add_argument('--memory', action='store_true')
    parser.add_argument('--output-directory', type=Path)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--mode', choices=['timing', 'memory', 'profile'], default='timing', help=argparse.SUPPRESS)
    args = parser.parse_args()
    seeds = [int(s) for s in args.seeds.split(',')]
    if not 1 <= len(seeds) <= 20 or not 1 <= args.repetitions <= 10 or not 5 <= args.trial_timeout <= 600:
        parser.error('Use 1-20 seeds, 1-10 repetitions and a 5-600 second worker limit')
    _, _, _, _, _, Parameters = runtime()
    parameters = Parameters(population_size=args.population, generations=args.generations, fresh_chromosomes=args.fresh,
                            crossover_attempts=args.operator_attempts, mutation_attempts=args.operator_attempts,
                            max_restarts=args.restarts, candidate_attempts=args.candidate_attempts)
    if args.worker:
        if args.scenario == 'all' or len(seeds) != 1:
            parser.error('A worker requires one scenario and seed')
        print(json.dumps(measure(args.scenario, seeds[0], parameters, args.mode), allow_nan=False))
        return 0
    directory = args.output_directory or ROOT/'docs/testing/ga-performance-phase2'/datetime.now(ZONE).strftime('%Y%m%dT%H%M%S%f+0800')
    directory = directory.resolve()
    if not directory.is_relative_to((ROOT/'docs/testing/ga-performance-phase2').resolve()):
        parser.error('Evidence directory must be beneath docs/testing/ga-performance-phase2')
    directory.mkdir(parents=True, exist_ok=False)
    started = datetime.now(ZONE).isoformat()
    results = {}
    for name in SCENARIOS if args.scenario == 'all' else [args.scenario]:
        # Fresh-worker warm-up is reported, not pooled with timing trials.
        warmup = run_worker(name, seeds[0], parameters.model_dump(), 'timing', args.trial_timeout)
        trials = []
        for repetition in range(args.repetitions):
            for seed in seeds:
                result = run_worker(name, seed, parameters.model_dump(), 'timing', args.trial_timeout)
                result['repetition'] = repetition+1
                trials.append(result)
                print(json.dumps({'scenario': name, 'seed': seed, 'status': result['status'],
                                  'engine_seconds': result.get('engine_seconds')}), file=sys.stderr, flush=True)
        extra = {mode: run_worker(name, seeds[0], parameters.model_dump(), mode, args.trial_timeout)
                 for mode in ['memory', 'profile'] if getattr(args, mode)}
        results[name] = {'warmup_excluded': warmup, 'trials': trials, 'summary': aggregate(trials),
                         'separate_instrumented_runs': extra}
    document = {'version': VERSION, 'scope': 'Entirely fictional, non-publishing kernel experiment; no institutional acceptance or C++',
                'started_at': started, 'finished_at': datetime.now(ZONE).isoformat(),
                'python': sys.version, 'platform': platform.platform(), 'machine': platform.machine(),
                'logical_cpus': os.cpu_count(), 'hash_seed': '0 in each worker',
                'parameters': parameters.model_dump(), 'seeds': seeds, 'repetitions': args.repetitions,
                'wall_deadline_seconds_per_worker': args.trial_timeout, 'command': sys.argv,
                'import_time_excluded_from_engine_seconds': True, 'results': results}
    output = directory/'results.json'
    output.write_bytes((json.dumps(document, indent=2, allow_nan=False)+'\n').encode('utf-8'))
    print(json.dumps({'evidence': output.relative_to(ROOT).as_posix(),
                      'summaries': {k: v['summary'] for k, v in results.items()}}, indent=2))
    return 0 if all(r['summary']['failed_trials'] == 0 for r in results.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
