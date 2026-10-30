"""Read-only F2B boundary characterization, NOT integrated fairness acceptance."""
import copy
import inspect
import json
import os
from pathlib import Path
import random
from fractions import Fraction

import pytest
from benchmarks.retention_runtime import runtime,data_guard
from benchmarks import scaled_python as bench
from tests.audit.test_thesis_correctness import values24,arranged
from services import ga_checkpoint_service as codec,ga_v2_engine as engine,ga_v2_store as store
from services.preference_scoring_policy import legacy_source,scoring_version
from schemas.ga_constrained import Parameters

_,fitness,inputs,Setting,*_=runtime()
ROOT=Path(__file__).resolve().parents[3]


def record(name,value):
    directory=Path(os.environ['F2B_OUTPUT']).resolve()
    assert directory.is_relative_to(Path(__file__).resolve().parent)
    with (directory/(name+'.json')).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')


@pytest.fixture(autouse=True)
def rng():
    before=random.getstate();yield;random.setstate(before)


def test_existing_default_counterexample_and_ignored_unrecognized_context_field():
    values=values24();a,b=arranged(values),arranged(values,True)
    with bench.synthetic_scoring(values,[],Setting().to_dict()),data_guard(),bench.no_io():
        frozen=engine.freeze(values);score_pairs=[]
        for field in (None,'workload_scoring_mode'):
            supplied=copy.deepcopy(frozen)
            if field:supplied[field]='target_weighted_squared_v1'
            token=inputs.set(supplied)
            try:
                left=fitness.faculty_preference_fitness(a,return_breakdown=True)
                right=fitness.faculty_preference_fitness(b,return_breakdown=True)
            finally:inputs.reset(token)
            assert (left[0],right[0])==(500,475)
            score_pairs.append(dict(unrecognized_field_supplied=field is not None,balanced=left[0],concentrated=right[0]))
    record('no_activation_hook',dict(observations=score_pairs,
        meaning='Extra context field is ignored by current scorer, not a supported experimental mode; no persistent context modified'))


def test_existing_request_and_settings_do_not_expose_supported_mode():
    with pytest.raises(ValueError):Parameters.model_validate(dict(workload_scoring_mode='target_weighted_squared_v1'))
    settings=Setting.from_dict(dict(workload_scoring_mode='target_weighted_squared_v1'))
    assert 'workload_scoring_mode' not in settings.to_dict()
    assert 'fitness' not in inspect.signature(engine.run).parameters
    record('configuration_boundary',dict(request_extra_field_rejected=True,unknown_settings_field_not_retained=True,
        engine_has_fitness_callback=False,default_setting_snapshot=Setting().to_dict()))


@pytest.mark.parametrize('version',[3,'experimental',True])
def test_existing_policy_version_rejects_unsupported_values(version):
    with pytest.raises(ValueError):scoring_version(dict(preference_scoring_version=version))


def test_hypothetical_dispatch_change_is_rejected_by_exact_source_bridge():
    relative='genetic_algorithm/operators/FitnessFunction.py';current=(ROOT/'backend'/relative).read_bytes()
    original=legacy_source(relative,current);assert original
    altered=current+b'\n# Hypothetical F2B dispatch, IN MEMORY ONLY\n'
    with pytest.raises(ValueError,match='verified legacy-compatible release'):legacy_source(relative,altered)
    assert (ROOT/'backend'/relative).read_bytes()==current
    record('legacy_bridge_boundary',dict(original_source_verified=True,hypothetical_changed_source_rejected=True,
        source_file_written=False,fingerprint_bypass=False,meaning='Bridge requires an explicitly verified source-compatibility extension; existing bridge is not changed'))


def test_operator_and_engine_aliases_use_the_same_current_scorer():
    from genetic_algorithm.operators import Swap,mutation
    assert Swap.faculty_preference_fitness is fitness.faculty_preference_fitness
    assert mutation.faculty_preference_fitness is fitness.faculty_preference_fitness
    assert engine.faculty_preference_fitness is fitness.faculty_preference_fitness
    source=inspect.getsource(engine.run)
    assert 'faculty_preference_fitness(candidate, preferences)' in source
    assert 'engine_fingerprint()' in inspect.getsource(store.read)
    record('shared_scorer_boundary',dict(current_aliases_identical=True,internal_operator_improvement_uses_original=True,
        current_engine_fingerprint=codec.engine_fingerprint(),current_V2_fingerprint=store.engine_fingerprint(),
        meaning='A post-hoc component replacement cannot change original operator decisions and checkpoint validation coherently'))


def test_original_zero_target_policy_is_overload_not_normal_fulfillment():
    values=values24(admin=24);candidate=arranged(values)
    with bench.synthetic_scoring(values,[],Setting().to_dict()),data_guard(),bench.no_io():
        token=inputs.set(engine.freeze(values))
        try:
            empty=fitness.faculty_preference_fitness([],return_breakdown=True)
            actual=fitness.faculty_preference_fitness(candidate,return_breakdown=True)
        finally:inputs.reset(token)
    assert empty[1]['teaching_load_balance']==0 and actual[1]['teaching_load_balance']==20
    assert all(f.required_teaching_load==0 and f.absolute_max_teaching_load==40 for f in values[1])
    record('zero_target_boundary',dict(targets=[0,0],assigned=[2,2],legacy_workload=20,zero_assigned_workload=0,
        current_hard_ceiling=40,new_deviation_formula='UNDEFINED_AT_TARGET_ZERO',
        new_mode_zero_target_positive='REQUIRES_EXPLICIT_SCORING_CONVENTION; no new hard prohibition invented'))


def test_frozen_context_and_report_have_no_workload_policy_identity():
    from services.fitness_reporting_service import capture_context
    from tests.d10.support import preferences
    values=values24()
    with bench.synthetic_scoring(values,[],Setting().to_dict()),data_guard(),bench.no_io():
        frozen=engine.freeze(values);token=inputs.set(frozen)
        try:context=capture_context(frozen,preferences())
        finally:inputs.reset(token)
    assert not any('workload' in k for k in frozen)
    assert not any('workload' in k for k in context)
    record('provenance_boundary',dict(current_frozen_keys=sorted(frozen),current_report_keys=sorted(context),
        workload_mode_identity_present=False,meaning='Preference policy version is not a new workload policy version; default capture still unchanged'))


def test_exact_rational_prototype_requires_an_explicit_storage_numeric_contract():
    from services.fitness_reporting_service import finite
    value=Fraction(121,3)
    with pytest.raises(codec.CheckpointError,match='Unsupported checkpoint value: Fraction'):codec.encode_graph(dict(score=value))
    with pytest.raises(ValueError):finite(value)
    record('numeric_boundary',dict(exact_oracle_type='Fraction',current_checkpoint_rejects_type=True,current_report_rejects_type=True,
        meaning='No implicit lossy conversion or silent storage-format extension attempted; future float/fixed/exact representation needs ranking and provenance tests'))
