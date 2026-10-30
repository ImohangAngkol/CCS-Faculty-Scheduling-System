"""Memory probes validate measurements/isolation, not an optimization."""
import copy
import gc
import random
import time
import tracemalloc
import weakref

import pytest
from benchmarks import memory_study as study
from benchmarks import scaled_python as bench
from benchmarks.scenarios import build,snapshot


def test_windows_counters_distinguish_ram_lifetime_peak_and_private_commit():
    result=study.ProcessMemory().read()
    assert result['working_set_bytes']>0
    assert result['process_lifetime_peak_working_set_bytes']>=result['working_set_bytes']
    assert result['private_commit_bytes_NOT_RSS']>0


def test_sampler_does_not_retain_each_poll_and_thread_is_stopped():
    sampler=study.Sampler(study.ProcessMemory(),interval=.005)
    with sampler:
        time.sleep(.03)
    result=sampler.result()
    assert result['sample_count']>=2 and result['sampled_interval_peak_working_set_bytes']>0
    assert not sampler.thread.is_alive() and not hasattr(sampler,'samples')


def test_graph_summary_counts_cycles_once_without_global_module_traversal():
    cyclic=[]; cyclic.append(cyclic)
    result=study.graph_summary(cyclic)
    assert result['unique_objects']==1 and result['object_type_counts']=={'list':1}
    assert result['estimated_unique_shallow_bytes_NOT_RSS']>0


def test_graph_summary_does_not_follow_module_or_class_referents():
    import sys
    result=study.graph_summary([sys,dict])
    assert result['unique_objects']==3
    assert result['object_type_counts']['module']==1


def test_snapshot_summaries_measure_net_live_memory_without_source_values():
    tracemalloc.start(4)
    try:
        before=tracemalloc.take_snapshot()
        data=[bytearray(10000) for _ in range(5)]
        after=tracemalloc.take_snapshot()
        result=study.allocation_rows(after,before)
        assert result['positive_net_bytes']>=50000
        assert all(set(f)=={'file','line'} for r in result['top'] for f in r['traceback'])
        assert 'NET LIVE' in result['scope']
        del data,after,before
    finally:tracemalloc.stop()


def test_focused_probe_records_peak_separately_from_live_and_restores_tracer():
    result=study.probe_operation('fictional_list_copy',lambda:copy.deepcopy([list(range(100)) for _ in range(10)]),study.ProcessMemory())
    assert result['incremental_traced_peak_bytes']>=result['incremental_traced_live_bytes']>0
    assert not tracemalloc.is_tracing()
    assert result['result_scalar'] is None


@pytest.fixture(scope='module')
def fictional():
    engine=bench.runtime()[0]
    rng=random.getstate()
    try:
        values,legacy,rows,settings,metadata=build('small')
        pinned=snapshot(values,metadata)
        random.seed(10101)
        working=engine.reduced_templates(pinned,values)
        candidate=engine.construct(working,5)
        engine.admit(candidate,pinned,working)
        yield values,legacy,rows,settings,pinned,working,candidate
    finally:random.setstate(rng)


def test_deepcopy_has_same_signature_and_hard_constraints_and_is_not_an_optimization(fictional):
    values,legacy,rows,settings,pinned,working,candidate=fictional
    engine=bench.runtime()[0]
    before=bench.signature(candidate)
    with bench.no_io():
        cloned=copy.deepcopy(candidate)
        engine.admit(cloned,pinned,working)
    assert bench.signature(cloned)==before and cloned[0] is not candidate[0]
    original=study.graph_summary(candidate); copied=study.graph_summary(cloned)
    assert original['object_type_counts']==copied['object_type_counts']
    assert copied['unassigned_TimeBlocks']>0
    assert copied['reachable_nonroot_Subject_objects']==0


def test_effective_preferences_are_fresh_equal_objects_and_fitness_remains_identical(fictional):
    values,legacy,rows,settings,pinned,working,candidate=fictional
    engine,fitness,scoring_inputs,*_=bench.runtime()
    before=random.getstate(); old_path=fitness.PREFERENCE_FILE
    with bench.synthetic_scoring(values,rows,settings):
        token=scoring_inputs.set(engine.freeze(values))
        try:
            with bench.no_io():
                a=fitness._build_effective_preferences(legacy)
                b=fitness._build_effective_preferences(legacy)
                assert a==b and a is not b
                expected=fitness.faculty_preference_fitness(candidate,legacy)
                assert all(fitness.faculty_preference_fitness(candidate,legacy)==expected for _ in range(10))
        finally:scoring_inputs.reset(token)
    assert fitness.PREFERENCE_FILE==old_path and random.getstate()==before


@pytest.mark.parametrize('enabled',[False,True])
def test_optional_score_observer_strong_reference_lifecycle_is_explicit(fictional,enabled):
    values,legacy,rows,settings,pinned,working,candidate=fictional
    engine,fitness,scoring_inputs,*_=bench.runtime()
    from genetic_algorithm.utils.FitnessObservation import observed_scores
    with bench.synthetic_scoring(values,rows,settings):
        token=scoring_inputs.set(engine.freeze(values)); scores={} if enabled else None
        scope=observed_scores.set(scores)
        try:
            cloned=copy.deepcopy(candidate); reference=weakref.ref(cloned[0])
            fitness.faculty_preference_fitness(cloned,legacy); del cloned; gc.collect()
            assert (reference() is not None)==enabled
            if enabled:
                assert len(scores)==1
                scores.clear(); gc.collect()
                assert reference() is None
        finally:observed_scores.reset(scope); scoring_inputs.reset(token)
    assert observed_scores.get() is None


def test_original_engine_ram_probe_matches_baseline_and_releases_models_and_rng():
    rng=random.getstate()
    result=study.full_run('small','ram')
    assert result['status']=='SUCCESS' and result['phase2_output_matches']
    assert result['engine_peak_point'] is None
    assert result['representative_model_weakrefs_alive_after_gc']==0
    assert random.getstate()==rng and not tracemalloc.is_tracing()
    assert result['process_sampling']['sample_count']>0


def test_database_and_store_writes_remain_blocked_with_process_memory_reads(tmp_path):
    with bench.no_io():
        assert study.ProcessMemory().read()['working_set_bytes']>0
        with pytest.raises(bench.BenchmarkSafetyError):
            (tmp_path/'forbidden-store').write_bytes(b'not written')
