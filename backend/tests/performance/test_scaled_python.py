"""Fictional benchmark correctness/safety, not institutional acceptance."""
import copy
import json
import random
import sqlite3
import socket

import pytest
from benchmarks import scaled_python as bench
from benchmarks.scenarios import SCENARIOS, build


def parameters():
    return bench.runtime()[-1](population_size=2, generations=1, fresh_chromosomes=0,
                              crossover_attempts=1, mutation_attempts=1,
                              max_restarts=2, candidate_attempts=2)


@pytest.mark.parametrize('name', SCENARIOS)
def test_explicit_synthetic_generator_is_reproducible_and_load_policy_unchanged(name):
    before = random.getstate()
    values, legacy, prefs, settings, meta = build(name)
    assert meta == build(name)[-1] and random.getstate() == before
    assert len(values[0]) > 2 and len(values[0]) == SCENARIOS[name].offerings
    assert meta['total_offered_units'] < meta['total_target_units']
    assert len({tuple(p['preferred_days']) for p in prefs}) == 3
    assert all(f.required_teaching_load == max(0, 24-f.admin_load-f.research_load-f.extension_load)
               and f.absolute_max_teaching_load == 40 and f.overload_warning_threshold == 30 for f in values[1])
    assert all(any(s.number in f.eligible_subjects for f in values[1]) for s in values[0])
    assert all(s.number.startswith('BENCH') and s.section.code.startswith('BENCH-SEC-') for s in values[0])


def test_same_seed_matches_history_assignments_and_diagnostics_and_restores_rng():
    before = random.getstate()
    a = bench.measure('small', 714, parameters())
    assert random.getstate() == before
    b = bench.measure('small', 714, parameters())
    assert random.getstate() == before
    assert a['status'] == b['status'] == 'SUCCESS'
    for key in ('history', 'workload', 'diagnostics', 'best_assignment_sha256', 'fitness_breakdown'):
        assert a[key] == b[key]
    assert a['final_fitness'] > 0 and a['workload']['zero_assignment_count'] >= 1
    assert 'profile_top_cumulative' not in a and 'peak_python_allocated_bytes_NOT_RSS' not in a


@pytest.mark.parametrize('name', SCENARIOS)
def test_actual_generated_schedules_cover_inputs_and_pass_original_hard_gate(name):
    result = bench.measure(name, 715, parameters())
    assert result['status'] == 'SUCCESS', result['status']
    assert result['best_ever_monotone'] and result['subject_coverage'] == 'EXACT'
    assert result['faculty_eligibility'] == 'PASS' and result['hard_constraints'].startswith('PASS')
    assert len(result['best_assignments']) == SCENARIOS[name].offerings
    assert sum(result['fitness_breakdown'].values()) == result['final_fitness']
    assert result['workload']['total_teaching_units'] == 3*SCENARIOS[name].offerings
    assert all(s['subject'].startswith('BENCH') and s['faculty'] >= 990100 for s in result['best_assignments'])


def test_private_scoring_sources_are_not_used_or_serialized_and_aliases_restore(monkeypatch, tmp_path):
    engine, fitness, *_ = bench.runtime()
    poisoned = tmp_path/'unrelated-preferences.json'
    poisoned.write_text('[{"faculty_code":1,"preferred_subjects":["PRIVATE_SENTINEL_DO_NOT_EXPORT"]}]')
    monkeypatch.setattr(fitness, 'PREFERENCE_FILE', poisoned)
    settings = tmp_path/'unrelated-settings.json'
    settings.write_text('{"underload_penalty":999999}')
    monkeypatch.setattr(fitness, 'GA_SETTINGS_FILE', settings)
    original_members = engine.schedule.list_faculty
    result = bench.measure('small', 716, parameters())
    assert result['status'] == 'SUCCESS'
    assert result['configuration']['settings']['underload_penalty'] == 25
    assert 'PRIVATE_SENTINEL' not in json.dumps(result) and '999999' not in json.dumps(result)
    assert fitness.PREFERENCE_FILE == poisoned and fitness.GA_SETTINGS_FILE == settings
    assert engine.schedule.list_faculty is original_members


def test_total_workload_counts_credits_once_and_includes_zero_assignment_underload():
    values, legacy, prefs, settings, metadata = build('small')
    subjects, faculty, _ = values
    candidate = copy.deepcopy(subjects[:2])
    for s in candidate:
        s.assigned_faculty = faculty[0]
    result = bench.workload(candidate, faculty)
    assert result['total_teaching_units'] == 6  # Lab contact hours are not extra credit units.
    assert result['zero_assignment_count'] == 5
    assert result['underload_units'] == sum(f.required_teaching_load for f in faculty)-6
    assert all(r['total_workload_units'] == r['teaching_units']+r['admin']+r['research']+r['extension']
               for r in result['faculty'])
    engine, fitness, scoring_inputs, *_ = bench.runtime()
    with bench.synthetic_scoring(values, prefs, settings):
        token = scoring_inputs.set(engine.freeze(values))
        try:
            total, detail = fitness.faculty_preference_fitness([], legacy, return_breakdown=True)
        finally:
            scoring_inputs.reset(token)
    assert detail['teaching_load_balance'] == 6*10*25
    assert total == detail['teaching_load_balance']


def test_search_exhaustion_is_bounded_not_infeasibility_and_has_no_partial_result(monkeypatch):
    engine = bench.runtime()[0]
    calls = []
    def exhausted(*args):
        calls.append(1)
        raise engine.ConstraintError('SEARCH_EXHAUSTED', 'Fictional bounded exhaustion')
    monkeypatch.setattr(engine, 'construct', exhausted)
    before = random.getstate()
    result = bench.measure('small', 1, parameters(), witness=False)
    assert result['status'] == 'SEARCH_EXHAUSTED' and len(calls) == 4
    assert not result['history'] and 'final_fitness' not in result
    assert result['diagnostics']['construction:SEARCH_EXHAUSTED'] == 4
    assert result['operator_call_attempts']['construction_calls'] == 4
    assert random.getstate() == before


@pytest.mark.parametrize('kind', ['file', 'sqlite', 'postgres', 'network'])
def test_kernel_guard_rejects_writes_and_all_database_network_access(kind, tmp_path):
    import psycopg2
    target = tmp_path/'forbidden-store'
    with pytest.raises(bench.BenchmarkSafetyError), bench.no_io():
        if kind == 'file':
            target.write_bytes(b'never written')
        elif kind == 'sqlite':
            sqlite3.connect(':memory:')
        elif kind == 'postgres':
            psycopg2.connect()
        else:
            with socket.socket() as stream:
                stream.connect(('127.0.0.1', 9))
    assert not target.exists()


def test_wall_limit_is_reported_and_failed_trials_are_not_averaged_as_fast_success():
    result = bench.run_worker('large', 714, parameters().model_dump(), 'timing', .001)
    assert result['status'] == 'WALL_DEADLINE_EXCEEDED'
    summary = bench.aggregate([{'mode':'timing','status':'SUCCESS','engine_seconds':2.0}, result])
    assert summary['attempted_trials'] == 2 and summary['failed_trials'] == 1
    assert summary['mean_seconds'] == 2.0 and summary['sample_standard_deviation_seconds'] is None


@pytest.mark.parametrize('mode', ['memory', 'profile'])
def test_measurement_modes_are_separate_and_restore_instrumentation(mode):
    import tracemalloc
    before = random.getstate()
    result = bench.measure('small', 714, parameters(), mode, witness=False)
    assert result['status'] == 'SUCCESS' and random.getstate() == before
    assert not tracemalloc.is_tracing()
    if mode == 'memory':
        assert result['peak_python_allocated_bytes_NOT_RSS'] > 0
        assert 'profile_top_cumulative' not in result
    else:
        assert result['profile_top_cumulative']
        assert 'peak_python_allocated_bytes_NOT_RSS' not in result


@pytest.mark.parametrize('release,target', [(0, 24), (24, 0), (30, 0)])
def test_option_b_target_is_clamped_and_non_teaching_remains_fixed(release, target):
    from genetic_algorithm.models.Faculty import Faculty
    member = Faculty(990999, 1, admin_load=release, eligible_subjects=set())
    record = bench.workload([], [member])['faculty'][0]
    assert record['target'] == target and record['non_teaching_fixed_units'] == release
    assert record['total_workload_units'] == release and record['teaching_units'] == 0


def test_original_capacity_rejection_is_distinct_from_bounded_search_exhaustion():
    engine = bench.runtime()[0]
    values = build('small')[0]
    values[0][0].credit_units = 40*len(values[1])+1
    before = random.getstate()
    with pytest.raises(engine.ConstraintError) as caught, bench.no_io():
        engine.construct(values, 1)
    assert caught.value.code == 'INPUT_CAPACITY_REJECTED'
    assert random.getstate() == before
