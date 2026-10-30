"""Fictional requirement probes. Gap characterizations are not requirement passes."""
from collections import Counter
import ast
import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import random
from types import SimpleNamespace

import pytest
from benchmarks.retention_runtime import runtime,data_guard
from benchmarks import scaled_python as bench
from tests.d10.support import templates,preferences
from tests.d10.test_v2_engine import snapshot_for
from services import ga_v2_constraints as constraints,ga_checkpoint_service as codec
from genetic_algorithm.models.Faculty import Faculty

engine,fitness,scoring_inputs,*_=runtime()


def observation(name,values):
    target=os.environ.get('THESIS_AUDIT_OBSERVATIONS')
    if not target:return
    directory=Path(target).resolve();root=Path(__file__).resolve().parents[3]/'docs/testing/thesis-functional-audit'
    assert directory.is_relative_to(root.resolve())
    directory.mkdir(exist_ok=True)
    with (directory/(name+'.json')).open('x',encoding='utf-8') as out:json.dump(values,out,indent=2)


@pytest.fixture(autouse=True)
def restore_rng():
    before=random.getstate();yield;random.setstate(before)


def values24(admin=0,research=0,extension=0):
    subjects,_,rooms=templates(compact=True)
    members=[Faculty(990001+i,1,admin_load=admin,research_load=research,extension_load=extension,
                     eligible_subjects={'SYN101','SYN102'}) for i in range(2)]
    for member in members:
        for index,day in enumerate(('monday','tuesday','wednesday','thursday','friday','saturday')):
            setattr(member,'time_blocks_'+day,getattr(member,'time_blocks_'+day)[:8] if index<2 else [])
    return subjects,members,rooms


def arranged(values,concentrated=False):
    subjects,members,rooms=copy.deepcopy(values)
    for index,subject in enumerate(subjects):
        assert engine.schedule.assign_schedule_to_faculty(members[0 if concentrated else index],subject,
            ('7:30 - 9:30','M' if index==0 else 'T'),'Lecture',room_list=rooms,list_subjects=subjects)
    return subjects


def score(candidate,values,legacy=None):
    with bench.synthetic_scoring(values,[],bench.runtime()[3]().to_dict()),data_guard(),bench.no_io():
        token=scoring_inputs.set(engine.freeze(values))
        try:return fitness.faculty_preference_fitness(candidate,legacy,return_breakdown=True)
        finally:scoring_inputs.reset(token)


def independent_conflicts(candidate):
    slots=[]
    for subject in candidate:
        for component in ('lecture','laboratory'):
            room=getattr(subject,component+'_room')
            for day,block in getattr(subject,component+'_time_blocks'):
                # Independent numeric conversion, not the application's overlap helper.
                start,end=([int(v) for v in text.split(':')] for text in (block.start_time,block.end_time))
                slots.append((day,start[0]*60+start[1],end[0]*60+end[1],str(subject.assigned_faculty.code),room.name,subject.section.code))
    return {kind:sum(a[0]==b[0] and a[i]==b[i] and max(a[1],b[1])<min(a[2],b[2])
                      for n,a in enumerate(slots) for b in slots[n+1:]) for kind,i in [('faculty',3),('room',4),('section',5)]}


def test_equal_target_fairness_counterexample_is_hard_valid_but_lower_penalty_for_concentration():
    values=values24();pinned=snapshot_for(values,faculty=None,room=None,start=570,end=630)
    reduced=constraints.reduced_templates(pinned,values)
    balanced=arranged(reduced);concentrated=arranged(reduced,True)
    for candidate in (balanced,concentrated):
        engine.admit(candidate,pinned,reduced)
        assert independent_conflicts(candidate)=={'faculty':0,'room':0,'section':0}
    a=score(balanced,values);b=score(concentrated,values)
    assert a[1]['teaching_load_balance']==500 and b[1]['teaching_load_balance']==475
    assert b[0]<a[0]
    observation('fairness-counterexample',{'finding':'CHARACTERIZED_GAP_NOT_FAIRNESS_ACCEPTANCE','target_units_each':24,
        'balanced_units':[2,2],'concentrated_units':[4,0],'workload_penalty_balanced':500,'workload_penalty_concentrated':475,
        'overall_balanced':a[0],'overall_concentrated':b[0],'both_original_admitted':True,'independent_conflicts_each':{'faculty':0,'room':0,'section':0}})


def test_missing_preferences_do_not_remove_eligible_faculty_or_zero_assignment_underload():
    values=values24();candidates=engine.schedule.get_ranked_faculty_candidates(values[0][0],values[1])
    assert {m.code for m in candidates}=={990001,990002}
    total,breakdown=score([],values)
    assert breakdown['teaching_load_balance']==500 and total>=500
    observation('faculty-universe',{'eligible_without_preference_count':2,'unassigned_faculty_count':2,
        'zero_assignment_workload_penalty':breakdown['teaching_load_balance'],'meaning':'No guarantee of an assignment when supply, eligibility or calendars prevent it'})


def test_original_legacy_roster_loop_omits_registered_faculty_absent_from_preference_rows():
    import pandas as pd
    from services.identity_service import build_legacy_faculty_codes
    registry=[SimpleNamespace(name='FICTIONAL FACULTY A',aliases=(),faculty_code=990001),
              SimpleNamespace(name='FICTIONAL FACULTY B',aliases=(),faculty_code=990002)]
    assert len(build_legacy_faculty_codes(['FICTIONAL FACULTY A'],registry))==1
    source=inspect.getsource(engine.schedule);tree=ast.parse(source)
    roster=[n for n in tree.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='faculty_code'
            and ast.unparse(n.iter)=='dct_fac_subj.keys()']
    assert len(roster)==1
    namespace=dict(vars(engine.schedule));namespace.update(list_faculty=[],dct_fac_subj={990001:[]},
        dct_fac_preferences={},dct_fac_name={990001:'FICTIONAL FACULTY A',990002:'FICTIONAL FACULTY B'},
        dct_fac_loads={name:{'admin_load':0,'research_load':0,'extension_load':0,'max_teaching_load':24} for name in ('FICTIONAL FACULTY A','FICTIONAL FACULTY B')},
        dct_fac_prio={990001:1,990002:1},dct_fac_specializations={},dct_fac_eligible_subjects={990001:{'SYN101'},990002:{'SYN102'}},
        resolve_faculty_identity=lambda code:SimpleNamespace(faculty_id='fictional-roster-'+str(code),display_code='SYN',name='Fictional faculty'))
    with bench.no_io():exec(compile(ast.Module(body=roster,type_ignores=[]),'audit-original-roster-loop','exec'),namespace)
    assert [m.code for m in namespace['list_faculty']]==[990001]
    observation('legacy-roster-coverage',{'registry_entries':2,'preference_source_members':1,'runtime_members_from_original_loop':1,
        'registered_missing_member_count':1,'source_line':roster[0].lineno,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
        'scope':'Original AST roster loop with explicit fictional dictionaries and test-only metadata resolver; no real roster parsed',
        'meaning':'Missing dashboard preferences differs from absence in legacy preference-derived runtime roster'})


@pytest.mark.parametrize('same_specialization,eligible,expected',[(True,False,False),(False,True,True),(True,True,True)])
def test_specialization_is_not_hard_eligibility_or_a_scorer_term(same_specialization,eligible,expected):
    subjects,members,_=values24();member=members[0];subject=subjects[0]
    member.specializations=['fictional-domain-a' if same_specialization else 'fictional-domain-b'];subject.primary_domain='fictional-domain-a'
    member.eligible_subjects={subject.number} if eligible else set()
    assert engine.schedule.faculty_is_explicitly_eligible_for_subject(member,subject) is expected


def test_specialization_changes_alone_do_not_change_fitness():
    values=values24();candidate=arranged(values);first=score(candidate,values)
    for member in values[1]:member.specializations=['fictional-other-domain']
    for subject in candidate:subject.assigned_faculty.specializations=['fictional-other-domain']
    assert score(candidate,values)==first
    observation('specialization',{'hard_rule':'EXPLICIT_COURSE_ELIGIBILITY','specialization_only_changes_fitness':False,
        'specialization_component_present':any('specializ' in k for k in first[1]),'strict_specialization_fallback':'NO_AUTOMATIC_ELIGIBILITY_RELAXATION'})


def test_no_eligible_instructor_is_not_detected_by_aggregate_capacity_preflight():
    values=values24()
    for member in values[1]:member.eligible_subjects=set()
    assert engine.schedule.check_minimum_load_feasibility(values[1],values[0])
    assert engine.schedule.get_ranked_faculty_candidates(values[0][0],values[1])==[]
    with pytest.raises(constraints.ConstraintError) as caught:engine.construct(values,1)
    assert caught.value.code=='SEARCH_EXHAUSTED'
    observation('coverage-preflight',{'aggregate_capacity_passed':True,'eligible_instructors_per_offering':0,
        'construction_error':caught.value.code,'gap':'Per-offering qualification impossibility is not separately diagnosed by aggregate preflight'})


def test_room_and_faculty_boolean_closures_reopen_at_reset_but_section_closure_remains():
    subjects,members,rooms=values24();room=rooms[0];member=members[0]
    for resource in (room,member,subjects[0].section):
        resource.time_blocks_monday[0].is_available=False;resource.time_blocks_monday[0].fixed_schedule=True
    engine.schedule.reset_complete_schedule(members,subjects,rooms)
    assert room.time_blocks_monday[0].is_available and member.time_blocks_monday[0].is_available
    assert not subjects[0].section.time_blocks_monday[0].is_available
    observation('availability-reset',{'room_boolean_reopened':True,'faculty_boolean_reopened':True,'section_boolean_reopened':False,
        'meaning':'Characterization of ordinary availability flags, not a bypass of V2 reduced-calendar or fixed-section enforcement'})


def test_closed_room_slot_can_be_assigned_after_original_reset():
    subjects,members,rooms=values24()
    for block in rooms[0].time_blocks_monday[:4]:block.is_available=False
    engine.schedule.reset_complete_schedule(members,subjects,rooms)
    assert engine.schedule.assign_schedule_to_faculty(members[0],subjects[0],('7:30 - 9:30','M'),'Lecture',room_list=rooms,list_subjects=subjects)
    assert subjects[0].lecture_room is rooms[0]


def test_removed_calendar_slots_and_V2_fixed_commitments_survive_restarts():
    values=values24();pinned=snapshot_for(values);reduced=constraints.reduced_templates(pinned,values)
    for _ in range(2):
        engine.schedule.reset_complete_schedule(reduced[1],reduced[0],reduced[2])
        for resource in (reduced[1][0],reduced[2][0]):
            assert all(not constraints.overlap(540,600,constraints.minutes(b.start_time),constraints.minutes(b.end_time))
                       for b in constraints.calendar(resource,'M'))


@pytest.mark.parametrize('releases,target',[(0,24),(5,19),(24,0),(30,0)])
def test_workload_policy_uses_fixed_hypothetical_release_inputs(releases,target):
    member=Faculty(990099,1,admin_load=releases)
    assert member.required_teaching_load==target and member.absolute_max_teaching_load==40 and member.overload_warning_threshold==30


@pytest.mark.parametrize('load,valid',[(0,True),(24,True),(30,True),(40,True),(41,False)])
def test_underload_is_soft_and_model_hard_ceiling_is_exact(load,valid):
    member=Faculty(990099,1);member.current_teaching_load=load
    assert engine.schedule.validate_minimum_teaching_load([member],raise_error=False) is valid


def test_general_settings_do_not_reconfigure_model_workload_limits():
    configured=bench.runtime()[3].from_dict({'total_workload_target':18,'absolute_max_teaching_load':20,'overload_warning_threshold':25})
    member=Faculty(990099,1)
    assert configured.total_workload_target==18 and configured.absolute_max_teaching_load==20
    assert member.required_teaching_load==24 and member.absolute_max_teaching_load==40 and member.overload_warning_threshold==30
    observation('workload-configuration',{'fictional_requested_target':18,'fictional_requested_ceiling':20,
        'actual_model_target':24,'actual_model_ceiling':40,'settings_file_read_or_changed':False,
        'meaning':'Settings fields are not authority to replace Faculty model constants'})


@pytest.mark.parametrize('kind',['admin','research','extension'])
def test_each_non_teaching_release_is_an_active_fitness_input_despite_working_thesis_exclusion(kind):
    base=values24();released=values24(**{kind:22})
    before=score(arranged(base),base);after=score(arranged(released),released)
    assert before[1]['teaching_load_balance']==500 and after[1]['teaching_load_balance']==0
    assert all(m.required_teaching_load==2 for m in released[1])
    observation('nonteaching-'+kind,{'release_kind':kind,'hypothetical_release_units_each':22,'teaching_units_each':2,
        'target_without_release':24,'target_with_release':2,'workload_penalty_without_release':500,'workload_penalty_with_release':0,
        'active_fixed_input':True,'scheduled_non_teaching_activity':False,'scope_alignment':'CONFLICT_WITH_WORKING_EXCLUSION_UNLESS_FIXED_RELEASE_INPUTS_ARE_EXPLICITLY_ALLOWED',
        'formal_adviser_alignment':'UNVERIFIED'})


def test_proportional_fulfillment_ranking_not_preference_submission_controls_coverage():
    subjects,members,_=values24();members[0].required_teaching_load=12;members[0].current_teaching_load=0
    members[1].current_teaching_load=12
    assert engine.schedule.get_ranked_faculty_candidates(subjects[0],members)[0] is members[0]


@pytest.mark.parametrize('change',['missing','duplicate','invalid_time','wrong_room','ineligible','hard_overload'])
def test_original_publication_rejects_incomplete_or_invalid_candidates(change):
    from services.ga_publication_service import validate_publication
    values=values24();candidate=arranged(values)
    if change=='missing':candidate.pop()
    if change=='duplicate':candidate.append(copy.deepcopy(candidate[0]))
    if change=='invalid_time':candidate[0].lecture_time_blocks[0][1].start_time='07:45'
    if change=='wrong_room':candidate[0].lecture_room.type='Laboratory'
    if change=='ineligible':
        for member in values[1]:member.eligible_subjects=set()
    if change=='hard_overload':values[0][0].credit_units=41;candidate[0].credit_units=41
    with pytest.raises((ValueError,RuntimeError)):validate_publication(candidate,*values)


def test_actual_improving_mutation_changes_faculty_but_not_meeting_geometry():
    from genetic_algorithm.operators.mutation import mutate_by_swapping_faculty_subjects
    from services.ga_publication_service import validate_publication
    values=values24();parent=arranged(values)
    geometry=lambda candidate:[(s.number,s.section.code,component,getattr(s,component+'_room').name if getattr(s,component+'_room') else None,
        tuple((d,b.start_time,b.end_time) for d,b in getattr(s,component+'_time_blocks'))) for s in candidate for component in ('lecture','laboratory')]
    before=codec.canonical(codec.encode_graph(parent));slots=geometry(parent)
    rows=[{'faculty_code':990001,'faculty_priority':1,'preferred_subjects':['SYN102'],'use_subject_preference':True,'subject_importance':1},
          {'faculty_code':990002,'faculty_priority':1,'preferred_subjects':['SYN101'],'use_subject_preference':True,'subject_importance':1}]
    with bench.synthetic_scoring(values,rows,runtime()[3]().to_dict()),data_guard(),bench.no_io():
        token=scoring_inputs.set(engine.freeze(values))
        try:
            old=fitness.faculty_preference_fitness(parent)
            random.seed(704);child=mutate_by_swapping_faculty_subjects([parent],None,max_attempts=1,verbose=False)
            assert child is not None
            new=fitness.faculty_preference_fitness(child)
        finally:scoring_inputs.reset(token)
    validate_publication(child,*values)
    assert new<old and geometry(child)==slots and codec.canonical(codec.encode_graph(parent))==before
    assert independent_conflicts(child)=={'faculty':0,'room':0,'section':0}
    observation('operator-search-space',{'actual_improved_child':True,'fitness_before':old,'fitness_after':new,
        'subject_section_day_time_room_geometry_unchanged':True,'parent_unchanged':True,'original_publication_passed':True,
        'meaning':'Original mutation swaps faculty, not times/rooms; fresh constructors supply new timetable geometry'})


def test_independent_conflict_and_completeness_metrics_have_explicit_denominators():
    values=values24();candidate=arranged(values)
    assert independent_conflicts(candidate)=={'faculty':0,'room':0,'section':0}
    required=Counter((s.number,s.section.code) for s in values[0]);actual=Counter((s.number,s.section.code) for s in candidate)
    assert required==actual and sum((required-actual).values())==0
    # A deliberately duplicated half-hour produces one conflicting slot pair
    # per shared resource. It is an invalid metric control, not a GA result.
    candidate[0].lecture_time_blocks.append(candidate[0].lecture_time_blocks[0])
    assert independent_conflicts(candidate)=={'faculty':1,'room':1,'section':1}
    observation('metric-controls',{'valid_schedule_conflicting_slot_pairs':{'faculty':0,'room':0,'section':0},
        'valid_unassigned_offerings':0,'required_offerings':2,'invalid_duplicate_control_pairs':{'faculty':1,'room':1,'section':1},
        'denominator':'Unordered same-resource/day half-hour slot pairs; not a unique-meeting conflict percentage'})
