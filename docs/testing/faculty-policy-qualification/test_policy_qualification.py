"""Fictional policy qualification, not approved production corrections."""
import copy
import json
import os
from pathlib import Path
import random
from fractions import Fraction

import pytest
from policy_experiments import CASES, measures, serial
from tests.audit.test_thesis_correctness import values24, arranged, score, independent_conflicts
from benchmarks.retention_runtime import runtime, data_guard
from benchmarks import scaled_python as bench
from services.ga_publication_service import validate_publication
from services import ga_v2_constraints as constraints
from tests.d10.test_v2_engine import snapshot_for

engine,fitness,scoring_inputs,*_=runtime()


def record(name, value):
    path=Path(os.environ['POLICY_QUALIFICATION_OUTPUT']).resolve()
    assert path.is_relative_to(Path(__file__).resolve().parent)
    with (path/(name+'.json')).open('x',encoding='utf-8') as out:
        json.dump(value,out,indent=2);out.write('\n')


@pytest.fixture(autouse=True)
def restore_rng():
    state=random.getstate();yield;random.setstate(state)


def test_exact_eight_component_fairness_breakdown_and_original_admission():
    values=values24();snap=snapshot_for(values,faculty=None,room=None,start=570,end=630)
    reduced=constraints.reduced_templates(snap,values)
    rows=[]
    for name, concentrated, expected in [('balanced',False,500),('concentrated',True,475)]:
        candidate=arranged(reduced,concentrated);engine.admit(candidate,snap,reduced)
        total,components=score(candidate,values)
        assert len(components)==8 and total==sum(components.values())==expected
        assert all(v==0 for k,v in components.items() if k!='teaching_load_balance')
        assert independent_conflicts(candidate)==dict(faculty=0,room=0,section=0)
        rows.append(dict(name=name,units=[4,0] if concentrated else [2,2],targets=[24,24],
                         total=total,components=components,original_admitted=True,independent_conflicts=independent_conflicts(candidate)))
    record('fairness-exact-breakdown',{'settings':'Fictional GASetting defaults; no local settings parsed',
        'preferences':'No submitted preferences; disabled/missing contributions remain zero',
        'schedules':rows,'policy_approval':'UNAPPROVED'})


@pytest.mark.parametrize('name',list(CASES))
def test_analytical_allocation_controls(name):
    loads,targets=CASES[name];result=measures(loads,targets)
    assert result['teaching_ceiling_valid']==(name!='invalid_above_ceiling')
    assert result['zero_assignments']==loads.count(0)
    if name=='targets_met':assert result['squared_relative']==0
    record('allocation-'+name,dict(name=name,loads=loads,targets=targets,**serial(result)))


def test_linear_debanding_ties_but_two_other_proposals_reverse_counterexample():
    balanced=measures([2,2],[24,24]);concentrated=measures([4,0],[24,24])
    assert balanced['linear_relative']==concentrated['linear_relative']==Fraction(1375,3)
    assert balanced['squared_relative']==Fraction(15125,36)
    assert concentrated['squared_relative']==Fraction(7625,18)
    assert balanced['squared_relative']<concentrated['squared_relative']
    assert balanced['overload_shortage_spread']<concentrated['overload_shortage_spread']


def test_different_target_fairness_definitions_can_disagree():
    equal=measures([6,6],[12,24]);proportional=measures([4,8],[12,24])
    assert equal['squared_relative']<proportional['squared_relative']
    assert proportional['overload_shortage_spread']<equal['overload_shortage_spread']
    assert measures([0,0],[0,0])['overload_shortage_spread']==(0,0,0)


@pytest.mark.parametrize('loads,targets',[([],[]),([1],[1,2]),([-1],[24]),([1.5],[24]),([True],[24])])
def test_proposed_math_rejects_unsupported_inputs(loads,targets):
    with pytest.raises(ValueError):measures(loads,targets)


def test_eligibility_forces_imperfect_allocation_and_soft_proposals_cannot_override_it():
    values=values24();values[1][1].eligible_subjects=set()
    concentrated=arranged(values,True);validate_publication(concentrated,*values)
    assert independent_conflicts(concentrated)==dict(faculty=0,room=0,section=0)
    # Construct an adversarial payload-shaped schedule from eligible control;
    # original authoritative templates still forbid the second instructor.
    balanced=arranged(values24())
    with pytest.raises(ValueError):validate_publication(balanced,*values)
    assert measures([2,2],[24,24])['squared_relative']<measures([4,0],[24,24])['squared_relative']
    record('eligibility-forced-concentration',{'eligible_instructors_for_both_offerings':1,'cohort_members':2,
        'hard_valid_units':[4,0],'balanced_candidate_rejected':True,'eligible_candidate_conflicts':dict(faculty=0,room=0,section=0),
        'meaning':'A lower proposed soft score never authorizes an ineligible assignment; unavoidable shortage remains visible'})


def test_availability_reset_scope_and_new_run_clone():
    values=values24()
    for r in [values[1][0],values[2][0],values[0][0].section]:
        r.time_blocks_monday[0].is_available=False;r.time_blocks_monday[0].fixed_schedule=True
    cloned=copy.deepcopy(values);engine.schedule.reset_complete_schedule(cloned[1],cloned[0],cloned[2])
    assert cloned[1][0].time_blocks_monday[0].is_available
    assert cloned[2][0].time_blocks_monday[0].is_available
    assert not cloned[0][0].section.time_blocks_monday[0].is_available
    assert not values[1][0].time_blocks_monday[0].is_available
    record('availability-lifecycle',{'original_template_unchanged':True,'cloned_faculty_boolean_reopened':True,
        'cloned_room_boolean_reopened':True,'cloned_section_boolean_reopened':False,
        'conclusion':'Boolean closure flags cannot encode persistent faculty/room restrictions across reset; V2 removed slots tested separately'})


def test_option_b_vs_teaching_only_is_a_real_policy_change():
    released=values24(admin=4,research=3,extension=1)
    zero=values24()
    assert [f.required_teaching_load for f in released[1]]==[16,16]
    assert [f.required_teaching_load for f in zero[1]]==[24,24]
    a=score(arranged(released),released);b=score(arranged(zero),zero)
    record('scope-comparison',{'units':[2,2],'fictional_allowances_each':{'admin':4,'research':3,'extension':1},
        'option_b_targets':[16,16],'teaching_only_assumption_targets':[24,24],
        'original_option_b_components':a[1],'zero_allowance_control_components':b[1],
        'warning': 'Zero-allowance control is not a production teaching-only implementation or an approved target policy'})


def test_specialization_metadata_does_not_change_existing_eligibility_or_score():
    values=values24();candidate=arranged(values);before=score(candidate,values)
    values[0][0].primary_domain='fictional-domain-a'
    values[1][0].specializations=['fictional-domain-b']
    assert engine.schedule.faculty_is_explicitly_eligible_for_subject(values[1][0],values[0][0])
    assert score(candidate,values)==before
    values[1][1].specializations=['fictional-domain-a'];values[1][1].eligible_subjects=set()
    assert not engine.schedule.faculty_is_explicitly_eligible_for_subject(values[1][1],values[0][0])
