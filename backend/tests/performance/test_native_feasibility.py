"""Python oracle characterization only. No native parity or speedup claim."""
import copy
import random

import pytest
from benchmarks import native_feasibility as study
from benchmarks import scaled_python as bench


@pytest.fixture(scope='module')
def original():
    bench.runtime()
    from services import ga_v2_constraints as constraints
    return constraints


@pytest.mark.parametrize('row,expected', [
    ((450,480,480,510),False), ((480,510,450,480),False),
    ((450,510,480,540),True), ((450,480,450,480),True),
    ((450,540,480,510),True), ((0,30,60,90),False),
    ((1290,1320,1320,1350),False), ((450,450,420,480),True),
    ((480,450,420,510),True), ((-30,0,-15,15),True),
])
def test_original_half_open_predicate_including_unvalidated_degenerate_ranges(original,row,expected):
    # The primitive does not itself validate positive duration or calendar range.
    assert original.overlap(*row) is expected
    assert study.batch_oracle([row]) == [expected]


def test_random_numeric_and_every_30_minute_adjacency_use_original_oracle_without_rng_changes(original):
    rng = random.Random(714)
    before = random.getstate()
    rows = [tuple(rng.randint(-60,1500) for _ in range(4)) for _ in range(20000)]
    expected = [max(a,c) < min(b,d) if a < b and c < d else a < d and c < b for a,b,c,d in rows]
    assert study.batch_oracle(rows) == expected
    for boundary in range(450,1321,30):
        assert not original.overlap(boundary-30,boundary,boundary,boundary+30)
    assert random.getstate() == before


@pytest.mark.parametrize('value,expected', [('0:00',0),('00:00',0),('7:30',450),('07:30',450),('22:00',1320),('23:59',1439)])
def test_original_strict_time_parser_exact_values(original,value,expected):
    assert original.minutes(value) == expected


@pytest.mark.parametrize('value', ['24:00','07:60','7:3',' 07:30','07:30 ','07:30:00','','abc','-1:00','07.30'])
def test_malformed_times_preserve_original_error_code(original,value):
    with pytest.raises(original.ConstraintError) as caught:
        original.minutes(value)
    assert caught.value.code == 'INVALID_TIME'


@pytest.mark.parametrize('value',[None,450,[],{}])
def test_wrong_time_types_are_not_coerced(original,value):
    with pytest.raises(TypeError):
        original.minutes(value)


def test_three_original_time_helpers_have_different_contracts_and_cannot_be_silently_unified(original):
    from services.chromosome_service import time_to_minutes
    schedule = bench.runtime()[0].schedule
    assert time_to_minutes(' 24:00 ') == 1440  # Existing permissive parser, not changed.
    with pytest.raises(original.ConstraintError):
        original.minutes('24:00')
    assert schedule.convert_time_to_minutes(' 7:3 ') == 423
    with pytest.raises(original.ConstraintError):
        original.minutes('7:3')
    with pytest.raises(ValueError):
        schedule.convert_time_to_minutes('24:00')


@pytest.mark.parametrize('kind', ['SECTION','FACULTY','ROOM'])
@pytest.mark.parametrize('day,expected_overlap', [('M',True),('T',False)])
def test_resource_and_day_rules_remain_outside_numeric_predicate(original,kind,day,expected_overlap):
    from tests.d10.support import templates
    from tests.d10.test_v2_engine import arranged, snapshot_for
    values = templates(compact=True)
    options = {'sections':('section-a',) if kind == 'SECTION' else ('section-b',),
               'faculty':'faculty-a' if kind == 'FACULTY' else None,
               'room':'room-a' if kind == 'ROOM' else None, 'day':day}
    pinned = snapshot_for(values,**options)
    candidate = arranged(values)
    assert original.external_conflict(candidate[:1],pinned) == ('EXTERNAL_'+kind+'_CONFLICT' if expected_overlap else None)


@pytest.mark.parametrize('update', [dict(start=540,end=540),dict(start=570,end=540),dict(start=555),dict(end=605),dict(day='SUN')])
def test_fixed_commitment_validation_rejects_invalid_ranges_and_off_grid_values(original,update):
    from tests.d10.support import templates
    from tests.d10.test_v2_engine import snapshot_for
    values=templates(compact=True)
    with pytest.raises(original.ConstraintError) as caught, bench.no_io():
        original.validate_snapshot(snapshot_for(values,**update),values)
    assert caught.value.code == 'INVALID_COMMITMENT'


def test_reference_rows_are_nonmutating_and_native_results_are_explicitly_unmeasured():
    source = {'trials':[{'best_assignments':[{'components':[{'blocks':[['M','07:30','08:00'],['T','09:00','09:30']]}]}]}]}
    before = copy.deepcopy(source)
    result = study.microbench(source,repetitions=2,loops=2)
    assert source == before and result['row_count'] == 2
    assert result['native_scalar'] == result['native_batch'] == 'NOT_MEASURED'
    assert result['native_conversion_or_binding_cost'] == 'NOT_MEASURED'
    assert result['warmed_python_scalar_seconds_per_pair']['sample_sd_seconds'] is not None


def test_empty_batch_and_wrong_comparison_types_match_python(original):
    assert study.batch_oracle([]) == []
    with pytest.raises(TypeError):
        original.overlap(None,30,0,30)
    with pytest.raises(TypeError):
        study.batch_oracle([(None,30,0,30)])


def test_inventory_does_not_claim_native_parity_or_installation():
    result = study.toolchain_inventory()
    assert result['native_build'] == 'NOT_RUN_NO_COMPILER'
    assert result['native_parity'] == 'NOT_RUN'
    assert result['native_timings_and_binding_overhead'] == 'NOT_MEASURED'
    assert result['dependencies_installed'] == 0
