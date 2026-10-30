"""F2A tests of offline formulas and original hard-valid fictional controls."""
import copy
from fractions import Fraction
import itertools
import json
import os
from pathlib import Path
import random

import pytest
from fairness_models import FUNCTIONS,absolute,squared,person_relative,target_relative,original_workload,metrics,serial
from fictional_schedules import SCENARIOS,evaluate,templates,snapshot,arrange
from benchmarks.retention_runtime import runtime,data_guard
from benchmarks import scaled_python as bench
from services import ga_v2_constraints as constraints

engine,*_=runtime()


@pytest.fixture(autouse=True)
def restore_rng():
    before=random.getstate();yield;random.setstate(before)


def save(name,data):
    folder=Path(os.environ['F2A_OUTPUT']).resolve()
    assert folder.is_relative_to(Path(__file__).resolve().parent)
    with (folder/(name+'.json')).open('x',encoding='utf-8') as f:json.dump(serial(data),f,indent=2);f.write('\n')


@pytest.mark.parametrize('scenario',SCENARIOS,ids=lambda s:s.name)
def test_original_hard_valid_exhaustive_fixed_geometry_scenarios(scenario):
    before=random.getstate();result=evaluate(scenario)
    assert random.getstate()==before and result['all_seven_other_components_zero']
    assert result['all_original_hard_valid'] and all(r['unassigned_offerings']==0 for r in result['rows'])
    if scenario.name=='equal_shortage':
        rows={tuple(r['actual']):r for r in result['rows']}
        assert rows[(2,2)]['original_total']==500 and rows[(4,0)]['original_total']==475
        assert result['winners']['target_relative']==[[2,2]]
    if scenario.name=='unequal_shortage':
        assert result['winners']['target_relative']==[[4,8]]
        assert result['winners']['squared']==[[0,12]]
        assert result['winners']['person_relative']==[[8,4]]
    if scenario.name=='allowance_shortage':assert result['winners']['target_relative']==[[2,4]]
    if scenario.name=='above_combined_targets':assert result['winners']['target_relative']==[[6,10]]
    if scenario.name=='no_eligible_member':
        assert result['winners']['target_relative']==[[4,8,0]]
        assert all(r['actual'][2]==0 and r['metrics']['no_eligible_offering_count']==1 for r in result['rows'])
    if scenario.name=='limited_eligibility':assert result['winners']['target_relative']==[[8,4]]
    if scenario.name=='indivisible_zero_assignment':assert result['winners']['target_relative']==[[0,2]]
    save('scenario-'+scenario.name,result)


def test_exact_counterexample_candidate_values_and_linear_tie():
    a,b=[2,2],[4,0];t=[24,24]
    assert (original_workload(a,t),original_workload(b,t))==(500,475)
    assert absolute(a,t)==absolute(b,t)==44
    assert (squared(a,t),squared(b,t))==(968,976)
    assert (person_relative(a,t),person_relative(b,t))==(Fraction(121,72),Fraction(61,36))
    assert (target_relative(a,t),target_relative(b,t))==(Fraction(121,3),Fraction(122,3))
    assert sum(Fraction(x-y,x) for x,y in zip(t,a))==sum(Fraction(x-y,x) for x,y in zip(t,b))


@pytest.mark.parametrize('targets,total', [((24,24),4),((12,24),12),((4,8),6),((4,8),16)])
def test_target_weighted_relative_score_minimizes_equal_fulfillment_when_exactly_reachable(targets,total):
    # Continuous/rational control only, not a fractional-credit production input.
    expected=[Fraction(total*t,sum(targets)) for t in targets]
    for allocation in range(0,total+1,2):
        d=[Fraction(allocation)-expected[0],Fraction(total-allocation)-expected[1]]
        excess=sum(dv*dv/t for dv,t in zip(d,targets))
        score=target_relative([allocation,total-allocation],list(targets))
        minimum=sum((a-t)**2/t for a,t in zip(expected,targets))
        assert score-minimum==excess


@pytest.mark.parametrize('actual,targets',[
    ([],[]),([2],[24,24]),([-1],[24]),([2.0],[24]),([True],[24]),([2],[-1]),([41],[24]),([2],[25])])
def test_candidates_fail_closed_for_unsupported_arithmetic_inputs(actual,targets):
    for function in FUNCTIONS.values():
        with pytest.raises(ValueError):function(actual,targets)


def test_zero_targets_no_division_by_zero_no_implied_hard_permission():
    assert target_relative([0,2],[0,4])==1
    assert target_relative([2,0],[0,4])==8
    assert person_relative([0,0],[0,0])==0
    row=metrics([0,2],[0,4]);assert row['fulfillment'][0] is None and row['zero_assignment_count']==1
    save('zero-target-convention',dict(denominator_for_zero_target=1,units='one fictional teaching credit',policy='UNAPPROVED_CONVENTION',
        zero_target_assignment_allowed_by_existing_hard_policy=True,zero_target_fulfillment=None))


def test_zero_assignment_in_unqualified_member_remains_visible_not_a_qualification_grant():
    row=metrics([4,8,0],[12,24,6],[True,True,False])
    assert row['total_underload']==30 and row['zero_assignment_count']==1
    assert row['positive_target_eligible_zero_count']==0 and row['no_eligible_offering_count']==1


def test_softly_better_ineligible_allocation_is_rejected_by_original_admission():
    scenario=next(s for s in SCENARIOS if s.name=='limited_eligibility')
    values=templates(scenario);pinned=snapshot(values);reduced=engine.reduced_templates(pinned,values)
    assert target_relative([4,8],[12,24])<target_relative([8,4],[12,24])
    with data_guard(),bench.no_io():
        candidate=arrange(reduced,(1,1,0,0,1,1))
        with pytest.raises(constraints.ConstraintError) as caught:engine.admit(candidate,pinned,reduced)
    assert caught.value.code=='INVALID_CANDIDATE'


@pytest.mark.parametrize('actual,expected',[(24,0),(30,20),(31,45),(40,120)])
def test_original_overload_bands_stay_explicit_in_sensitivity(actual,expected):
    from fairness_models import overload,relative_with_original_overload
    assert overload([actual],[24])==expected
    assert relative_with_original_overload([actual],[24])==Fraction(250,24)*target_relative([actual],[24])+expected


def test_permutation_invariance_and_no_rng_or_input_mutation():
    a,t=[2,4,0],[4,8,6];before=random.getstate();copies=copy.deepcopy((a,t))
    for function in FUNCTIONS.values():
        assert function(a,t)==function(list(reversed(a)),list(reversed(t)))
    assert random.getstate()==before and (a,t)==copies


def test_equal_target_balancing_transfer_never_worsens_convex_candidates():
    for total in range(0,25,2):
        for a in range(total//2+1,total+1):
            before=[a,total-a];after=[a-1,total-a+1]
            for fn in (squared,person_relative,target_relative):assert fn(after,[24,24])<=fn(before,[24,24])


def test_relative_policy_and_equal_person_weighting_are_distinct():
    assert person_relative([8,4],[12,24])<person_relative([4,8],[12,24])
    assert target_relative([4,8],[12,24])<target_relative([8,4],[12,24])
