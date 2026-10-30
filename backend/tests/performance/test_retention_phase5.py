"""Phase 5 fictional retention/copy ownership contracts, not production changes."""
import gc
import io
import json
from pathlib import Path
import random
import weakref

import pandas as pd
import pytest
from benchmarks import retention_phase5 as study
from benchmarks import retention_ownership as ownership
from benchmarks.retention_runtime import runtime,data_guard,BOOTSTRAP,DATA


def test_schema_only_import_uses_no_parsed_academic_rows():
    engine=runtime()[0]
    assert BOOTSTRAP=={'used':True,'csv_reads_substituted':7,'json_reads_substituted':2}
    assert not engine.schedule.list_subjects and not engine.schedule.list_faculty


@pytest.mark.parametrize('kind',['csv','text'])
def test_data_guard_rejects_academic_parsing_before_reading_values(kind):
    with data_guard(),pytest.raises(RuntimeError,match='PARSE_REJECTED'):
        if kind=='csv':pd.read_csv(DATA/'Faculty.csv')
        else:(DATA/'faculty_preferences.json').read_text()


def test_gc_census_ignores_non_string_module_descriptors():
    class Odd:
        __module__=property(lambda self:'not a module string')
    value=Odd()
    result=study.model_counts()
    assert set(result)==study.MODEL_TYPES and all(n>=0 for n in result.values())
    assert value is not None


def test_chromosome_lists_are_not_weakrefable_and_proxy_is_explicitly_labeled():
    chromosome=[]
    with pytest.raises(TypeError):weakref.ref(chromosome)
    lease=study.Lease({'population':[chromosome]});ref=weakref.ref(lease)
    del lease;gc.collect()
    assert ref() is None


@pytest.mark.parametrize('failure',[False,True])
def test_worker_memory_guard_fails_closed_without_adjusting_gc_or_allocator(monkeypatch,failure):
    class StopWorker(Exception):pass
    class FakeProcess:
        def read(self):
            if failure:raise RuntimeError('unavailable')
            return {'working_set_bytes':10,'private_commit_bytes_NOT_RSS':10}
    stream=io.StringIO();guard=study.MemoryLimit(FakeProcess(),stream,working=1,private=1)
    monkeypatch.setattr(guard.stop,'wait',lambda timeout:False)
    codes=[]
    def terminate(code):codes.append(code);raise StopWorker()
    monkeypatch.setattr(study.os,'_exit',terminate)
    with pytest.raises(StopWorker):guard.run()
    assert codes==[89 if failure else 88]
    event=json.loads(stream.getvalue())
    assert event['event']==('MEMORY_GUARD_QUERY_FAILED' if failure else 'MEMORY_LIMIT_EXCEEDED')


def test_matrix_is_bounded_and_has_replicates_warmups_varied_seeds_and_large_limits():
    jobs=study.matrix('retention')
    assert len(jobs)==12
    for name in ('small','medium'):
        ram=[j for j in jobs if j['name'].startswith('ram-'+name)]
        assert len(ram)==2 and all(len(j['seeds'])==12 and len(j['warmup'])==2 for j in ram)
        assert all(j['seeds'][:6]==[714]*6 and len(set(j['seeds'][6:]))==4 for j in ram)
    assert all(len(j['seeds'])<=2 for j in jobs if j['scenario']=='large')


def test_real_small_series_releases_roots_and_matches_identical_seed_without_rng_changes():
    before=random.getstate();thresholds=gc.get_threshold();enabled=gc.isenabled();stream=io.StringIO()
    config=dict(name='unit-small',scenario='small',seeds=[714,714],warmup=[715],trace=False)
    study.run_series(config,stream)
    assert random.getstate()==before
    assert gc.get_threshold()==thresholds and gc.isenabled()==enabled
    events=[json.loads(line) for line in stream.getvalue().splitlines()]
    summary=events[-1];records=[e['record'] for e in events if e['event']=='run']
    assert summary['status']=='SUCCESS'
    assert records[1]['history']==records[2]['history']
    assert records[1]['best_assignment_sha256']==records[2]['best_assignment_sha256']
    assert all(r['released_roots']=={'sampled_models_alive':{},'sampled_model_count_alive':0,'reporting_leases_alive':0} for r in records)
    assert all(r['after_release_gc']['model_counts']==summary['post_warmup_baseline']['model_counts'] for r in records)


def test_copy_independence_original_checkpoint_resume_and_fingerprint_rejection():
    before=random.getstate();result=ownership.verify('small')
    assert random.getstate()==before
    assert result['status']=='SUCCESS' and result['mutable_original_clone_intersection']==0
    assert result['mutable_best_population_intersection']==0
    assert result['mutation_isolation'] and result['copy_internal_subject_faculty_aliases_preserved']
    assert result['checkpoint_files_written']==0 and result['production_checkpoints_opened']==0
    assert result['fingerprint_tampering'].startswith('REJECTED')


def test_minimal_callback_prototype_preserves_assignments_history_and_rng():
    engine=runtime()[0];process=study.memory.ProcessMemory();rng=random.getstate()
    values,legacy,rows,settings,meta=study.build('small');pinned=study.snapshot(values,meta)
    params=runtime()[-1](**study.PARAMETERS)
    try:
        with study.memory.bench.synthetic_scoring(values,rows,settings),data_guard(),study.memory.bench.no_io():
            a,_,_=study.execute(values,pinned,legacy,params,714,process,'retain_last')
            b,_,_=study.execute(values,pinned,legacy,params,714,process,'final_only')
        for key in ('history','best_assignment_sha256','final_fitness','final_rng_sha256'):assert a[key]==b[key]
    finally:random.setstate(rng)
