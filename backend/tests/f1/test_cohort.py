"""F1 fictional adapter evidence; production source integration is BLOCKED."""
import ast
import copy
from dataclasses import replace
import inspect
import json
import os
from pathlib import Path
import random
from types import SimpleNamespace
from uuid import UUID,uuid4

import pandas as pd
import pytest
from benchmarks.retention_runtime import runtime,data_guard
from benchmarks import scaled_python as bench
from tests.f1.cohort_adapter import Term,Entry,FictionalRoster,Profile,Submission,CohortError,build
from tests.d10.support import templates
from tests.d10.test_v2_engine import snapshot_for,FictionalAuthority
from tests.audit.test_thesis_correctness import independent_conflicts
from schemas.faculty_preference import FacultyPreferenceUpdate
from services import ga_v2_constraints as constraints,ga_v2_store as store,ga_checkpoint_service as codec
from genetic_algorithm.models.Faculty import Faculty

engine,fitness,scoring_inputs,Setting,_,Parameters=runtime()
TERM=Term('fictional-ccs','2026-2027','Fictional first term')
OTHER=replace(TERM,term='Fictional second term')
IDS=tuple(str(UUID(int=990001+i)) for i in range(5))


@pytest.fixture(autouse=True)
def rng():
    before=random.getstate();yield;random.setstate(before)


def fixture():
    subjects,members,rooms=templates(compact=True)
    third=copy.deepcopy(members[0]);third.code=990003;third.eligible_subjects=set()
    entries=tuple(Entry(TERM,IDS[i],990001+i) for i in range(3))
    entries+=(Entry(OTHER,IDS[3],990004),Entry(TERM,IDS[4],990005,False,'FICTIONAL_TERM_LEAVE'))
    profiles=tuple(Profile(TERM,IDS[i],member,1) for i,member in enumerate([*members,third]))
    preference=Submission(TERM,IDS[0],990001,FacultyPreferenceUpdate(
        preferred_subjects=['SYN101'],subject_importance=1,use_subject_preference=True,
        preferred_days=['M'],day_importance=1,use_day_preference=True,
        preferred_start_time='07:30',preferred_end_time='09:30',time_importance=1,use_time_preference=True))
    return FictionalRoster(TERM,'fictional-roster.1',entries),profiles,(preference,),subjects,rooms


def write_observation(name,value):
    directory=Path(os.environ['F1_OBSERVATIONS']).resolve()
    assert directory.is_relative_to(Path(__file__).resolve().parents[3]/'docs/testing/faculty-cohort-f1')
    with (directory/(name+'.json')).open('x',encoding='utf-8') as out:json.dump(value,out,indent=2);out.write('\n')


def pinned(values):
    snap=snapshot_for(values,faculty=None,room=None,start=570,end=630)
    mappings=tuple(('fictional-faculty-'+str(i),str(f.code)) for i,f in enumerate(values[1]))
    return snap.model_copy(update={'catalog':snap.catalog.model_copy(update={'faculty':mappings})})


def legacy_pool(profiles):
    """Execute the original legacy AST loop with only fictional dictionaries."""
    source=inspect.getsource(engine.schedule);tree=ast.parse(source)
    loop=next(n for n in tree.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name)
              and n.target.id=='faculty_code' and ast.unparse(n.iter)=='dct_fac_subj.keys()')
    namespace=dict(vars(engine.schedule));namespace.update(list_faculty=[],dct_fac_subj={990001:[]},
        dct_fac_preferences={},dct_fac_name={p.faculty.code:'FICTIONAL-'+str(p.faculty.code) for p in profiles},
        dct_fac_loads={'FICTIONAL-'+str(p.faculty.code):dict(admin_load=22,research_load=0,extension_load=0,max_teaching_load=0) for p in profiles},
        dct_fac_prio={p.faculty.code:1 for p in profiles},dct_fac_specializations={},
        dct_fac_eligible_subjects={p.faculty.code:p.faculty.eligible_subjects for p in profiles},
        resolve_faculty_identity=lambda code:SimpleNamespace(faculty_id=IDS[code-990001],display_code='FICTIONAL',name='Fictional faculty'))
    with bench.no_io():exec(compile(ast.Module(body=[loop],type_ignores=[]),'f1-original-legacy-loop','exec'),namespace)
    return namespace['list_faculty']


def test_roster_includes_missing_preferences_and_reports_term_exclusions():
    roster,profiles,submitted,_,_=fixture();cohort=build(roster,profiles,submitted)
    assert [f.code for f in cohort.faculty]==[990001,990002,990003]
    assert [d['preferences'] for d in cohort.diagnostics if d['included']]==['SUBMITTED','MISSING_NEUTRAL','MISSING_NEUTRAL']
    assert [d['reason'] for d in cohort.diagnostics if not d['included']]==['OUTSIDE_REQUESTED_TERM','FICTIONAL_TERM_LEAVE']
    assert len(cohort.submissions)==1 and cohort.submissions[0]['faculty_code']==990001


def test_missing_preferences_are_absent_and_original_scoring_is_neutral():
    roster,profiles,_,subjects,rooms=fixture();cohort=build(roster,profiles)
    assert cohort.submissions==[]
    assert all(not f.preferred_subjects and not f.preferred_day and not f.preferred_time for f in cohort.faculty)
    values=(subjects,cohort.faculty,rooms)
    with bench.synthetic_scoring(values,[],Setting().to_dict()),data_guard(),bench.no_io():
        token=scoring_inputs.set(engine.freeze(values))
        try:
            effective=fitness._build_effective_preferences(pd.DataFrame(cohort.priority_rows))
            assert all(not p['use_subject_preference'] and p['subject_importance']==0 and p['preferred_days']==[] for p in effective.values())
            _,components=fitness.faculty_preference_fitness([],pd.DataFrame(cohort.priority_rows),return_breakdown=True)
        finally:scoring_inputs.reset(token)
    assert all(components[k]==0 for k in ('subject_preference','time_preference','day_preference','schedule_style','lecture_lab_preference'))
    assert components['teaching_load_balance']==750  # All three supplied targets2, zero assignments.


def test_submitted_time_day_and_subject_preferences_reach_original_scorer_unchanged():
    roster,profiles,submitted,subjects,rooms=fixture();cohort=build(roster,profiles,submitted)
    before=submitted[0].payload.model_dump(exclude_unset=True)
    assert cohort.submissions[0]==dict(before,faculty_code=990001)
    with bench.synthetic_scoring((subjects,cohort.faculty,rooms),cohort.submissions,Setting().to_dict()),data_guard(),bench.no_io():
        effective=fitness._build_effective_preferences(pd.DataFrame(cohort.priority_rows))
    assert effective[990001]['preferred_days']==['M'] and effective[990001]['preferred_start_time']=='07:30'
    assert effective[990001]['preferred_subjects']==['SYN101']
    assert all(effective[990001]['use_'+kind+'_preference'] for kind in ('subject','day','time'))
    assert before==submitted[0].payload.model_dump(exclude_unset=True)


@pytest.mark.parametrize('change,code',[
    ('duplicate_entry','DUPLICATE_ROSTER_IDENTITY'),('conflicting_id','IDENTITY_CODE_CONFLICT'),
    ('conflicting_code','IDENTITY_CODE_CONFLICT'),('duplicate_profile','DUPLICATE_PROFILE'),
    ('missing_profile','REQUIRED_PROFILE_MISSING'),('duplicate_submission','DUPLICATE_SUBMISSION'),
    ('wrong_submission_code','SUBMISSION_BINDING_INVALID'),('account_only_submission','SUBMISSION_BINDING_INVALID'),
    ('wrong_profile_id','PROFILE_BINDING_INVALID'),('nonfictional','FICTIONAL_SOURCE_REQUIRED'),
    ('unknown_term','TERM_NOT_PRESENT'),('blank_revision','REVISION_REQUIRED'),
    ('missing_exclusion_reason','EXCLUSION_REASON_INVALID'),('bad_id','IDENTITY_INVALID'),
    ('bool_code','CODE_INVALID'),('dirty_profile','PROFILE_NOT_NEUTRAL_OR_PRISTINE'),
    ('changed_target','WORKLOAD_POLICY_MISMATCH'),('invalid_eligibility','ELIGIBILITY_METADATA_INVALID')])
def test_fail_closed_input_contract(change,code):
    roster,profiles,submitted,_,_=fixture()
    if change=='duplicate_entry':roster=replace(roster,entries=roster.entries+(roster.entries[0],))
    if change=='conflicting_id':roster=replace(roster,entries=roster.entries+(replace(roster.entries[0],faculty_code=990099),))
    if change=='conflicting_code':roster=replace(roster,entries=roster.entries+(replace(roster.entries[0],faculty_id=IDS[4]),))
    if change=='duplicate_profile':profiles+=profiles[:1]
    if change=='missing_profile':profiles=profiles[:1]
    if change=='duplicate_submission':submitted+=submitted
    if change=='wrong_submission_code':submitted=(replace(submitted[0],faculty_code=990002),)
    if change=='account_only_submission':submitted=(replace(submitted[0],faculty_id=str(UUID(int=999999)),faculty_code=999999),)
    if change=='wrong_profile_id':profiles=(replace(profiles[0],faculty_id=IDS[4]),)+profiles[1:]
    if change=='nonfictional':roster=replace(roster,source_kind='INSTITUTIONAL')
    if change=='unknown_term':roster=replace(roster,term=replace(TERM,term='Fictional unknown term'))
    if change=='blank_revision':roster=replace(roster,revision='')
    if change=='missing_exclusion_reason':roster=replace(roster,entries=roster.entries[:-1]+(replace(roster.entries[-1],exclusion_reason=None),))
    if change=='bad_id':roster=replace(roster,entries=(replace(roster.entries[0],faculty_id='not-a-uuid'),)+roster.entries[1:])
    if change=='bool_code':roster=replace(roster,entries=(replace(roster.entries[0],faculty_code=True),)+roster.entries[1:])
    if change=='dirty_profile':profiles[0].faculty.preferred_subjects=['SYN101']
    if change=='changed_target':profiles[0].faculty.required_teaching_load=99
    if change=='invalid_eligibility':profiles[0].faculty.eligible_subjects=None
    with pytest.raises(CohortError) as caught:build(roster,profiles,submitted)
    assert caught.value.code==code and str(caught.value)==code


def test_missing_eligibility_is_deny_all_not_a_membership_filter():
    roster,profiles,_,subjects,_=fixture();profiles=(replace(profiles[0],eligibility_known=False),)+profiles[1:]
    cohort=build(roster,profiles)
    assert len(cohort.faculty)==3 and cohort.faculty[0].eligible_subjects==set()
    assert not engine.schedule.faculty_is_explicitly_eligible_for_subject(cohort.faculty[0],subjects[0])
    assert cohort.diagnostics[0]['eligibility']=='MISSING_DENY_ALL'


def test_option_b_specializations_and_calendars_are_detached_and_preserved():
    roster,profiles,_,_,_=fixture();source=profiles[0].faculty
    source.specializations=['fictional-domain'];source.time_blocks_tuesday[0].is_available=False
    source.admin_load=4;source.research_load=3;source.extension_load=1;source.required_teaching_load=16;source.min_teaching_load=16;source.non_teaching_load=8
    before=codec.canonical(codec.encode_graph(source));cohort=build(roster,profiles);member=cohort.faculty[0]
    assert (member.admin_load,member.research_load,member.extension_load,member.required_teaching_load)==(4,3,1,16)
    assert member.absolute_max_teaching_load==40 and member.overload_warning_threshold==30
    assert member.specializations==source.specializations and not member.time_blocks_tuesday[0].is_available
    member.specializations.append('fictional-new');member.time_blocks_tuesday[0].is_available=True
    assert codec.canonical(codec.encode_graph(source))==before


def test_cohort_digest_binds_term_revision_roster_order_and_optional_submission():
    roster,profiles,submitted,_,_=fixture();a=build(roster,profiles,submitted)
    assert a.digest==build(roster,profiles,submitted).digest
    assert a.digest!=build(replace(roster,revision='fictional-roster.2'),profiles,submitted).digest
    assert a.digest!=build(roster,profiles).digest
    assert a.digest!=build(replace(roster,entries=tuple(reversed(roster.entries))),profiles,submitted).digest


def test_original_legacy_coverage_counterexample_and_adapter_before_after():
    roster,profiles,submitted,subjects,rooms=fixture();old=legacy_pool(profiles);cohort=build(roster,profiles,submitted)
    old_values=(copy.deepcopy(subjects),old,copy.deepcopy(rooms))
    old_candidate=copy.deepcopy(old_values)
    for i,s in enumerate(old_candidate[0]):
        assert engine.schedule.assign_schedule_to_faculty(old_candidate[1][0],s,('7:30 - 9:30','M' if i==0 else 'T'),'Lecture',room_list=old_candidate[2],list_subjects=old_candidate[0])
    engine.admit(old_candidate[0],pinned(old_values),old_values)
    values=(subjects,cohort.faculty,rooms);snap=pinned(values);reduced=constraints.reduced_templates(snap,values)
    random.seed(714)
    with data_guard(),bench.no_io():candidate=engine.construct(reduced,3);engine.admit(candidate,snap,reduced)
    codes={s.assigned_faculty.code for s in candidate}
    assert codes=={990001,990002} and len(old)==1
    assert independent_conflicts(candidate)==dict(faculty=0,room=0,section=0)
    write_observation('coverage-before-after',dict(scope='Original legacy AST loop versus FICTIONAL adapter; no production source activation',
        approved_policy='USER_REPORTED; no documentary approval supplied',active_roster_members=3,
        eligible_for_at_least_one_offering=2,legacy_runtime_members=1,legacy_eligible_members_included=1,
        adapter_runtime_members=3,adapter_eligible_members_included=2,excluded=[d for d in cohort.diagnostics if not d['included']],
        adapter_excluded_count=2,legacy_excluded_active_members=[dict(faculty_code=c,reason='ABSENT_LEGACY_PREFERENCE_KEY') for c in (990002,990003)],
        missing_preferences_in_legacy_runtime=0,missing_preferences_in_adapter=2,
        legacy_zero_assignments=0,adapter_zero_assignments=1,zero_assignment_reason='One included member has no explicit eligible offerings',
        legacy_unassigned_offerings=0,adapter_unassigned_offerings=0,
        hard_conflicts_before=independent_conflicts(old_candidate[0]),hard_conflicts_after=independent_conflicts(candidate),
        inclusion_guarantees_assignment=False))


def test_no_eligible_offerings_has_bounded_truthful_failure():
    roster,profiles,_,subjects,rooms=fixture()
    for p in profiles:p.faculty.eligible_subjects=set()
    cohort=build(roster,profiles)
    assert len(cohort.faculty)==3
    with data_guard(),bench.no_io(),pytest.raises(constraints.ConstraintError) as caught:
        engine.construct((subjects,cohort.faculty,rooms),1)
    assert caught.value.code=='SEARCH_EXHAUSTED'


@pytest.mark.parametrize('kind',['Faculty','Room','Section'])
def test_adapter_profiles_do_not_weaken_original_resource_conflict_checks(kind):
    from genetic_algorithm.models.Room import Room
    from services.chromosome_service import chromosome_to_payload,payload_to_chromosome
    roster,profiles,_,subjects,rooms=fixture();cohort=build(roster,profiles)
    rooms.append(Room('Fictional second lecture room','Lecture'))
    if kind=='Section':subjects[1].section=subjects[0].section
    values=(subjects,cohort.faculty,rooms);candidate=copy.deepcopy(values)
    for i,subject in enumerate(candidate[0]):
        assert engine.schedule.assign_schedule_to_faculty(candidate[1][i],subject,('7:30 - 9:30','M' if i==0 else 'T'),
            'Lecture',room_list=candidate[2],list_subjects=candidate[0])
    payload=chromosome_to_payload(candidate[0],0)
    first_room=next(row['room'] for row in payload['schedule'] if row['subject']=='SYN101')
    other_room=next(room.name for room in rooms if room.name!=first_room)
    for row in payload['schedule']:
        if row['subject']=='SYN102':
            row['day']='M'
            row['room']=first_room if kind=='Room' else other_room
            if kind=='Faculty':row['faculty']=990001
    with data_guard(),bench.no_io(),pytest.raises(ValueError) as caught:payload_to_chromosome(payload,*values)
    assert kind.lower()+' conflict' in str(caught.value).lower()
    write_observation('conflict-control-'+kind.lower(),dict(target=kind,original_reconstruction_rejected=True,
        control_room_source='Actual first assignment room; never infer from room-list order',
        requested_overlap='Monday 07:30-09:30',error_resource=kind))


def test_adapter_cohort_actual_engine_reproducibility_checkpoint_best_and_mutation_isolation(monkeypatch,tmp_path):
    roster,profiles,submitted,subjects,rooms=fixture();cohort=build(roster,profiles,submitted)
    values=(subjects,cohort.faculty,rooms);snap=pinned(values);authority=FictionalAuthority(snap)
    params=Parameters(population_size=2,generations=2,fresh_chromosomes=1,mutation_attempts=1,crossover_attempts=1,max_restarts=3,candidate_attempts=3)
    monkeypatch.setattr(store,'STORE',tmp_path/'fictional-f1')
    frame=pd.DataFrame(cohort.priority_rows)
    def execute(run_id,pause_at=None,state=None):
        def boundary(current):
            from services.ga_v2_service import result_for
            status='PAUSED' if current['generation']==pause_at else 'COMPLETED' if current['generation']==2 else 'RUNNING'
            store.write(run_id,current,snap,authority,values,status,result_for(current,snap,status))
            return 'pause' if status=='PAUSED' else None
        return engine.run(values,snap,params,frame,boundary,state=state)
    with bench.synthetic_scoring(values,cohort.submissions,Setting().to_dict()),data_guard():
        full,paused=str(uuid4()),str(uuid4())
        random.seed(714);assert execute(full)=='complete';expected_rng=random.getstate()
        left,_,_=store.read(full)
        random.seed(714);assert execute(paused,pause_at=1)=='pause'
        _,_,state=store.read(paused)
        random.seed(999);assert execute(paused,state=state)=='complete'
        right,_,state=store.read(paused)
        assert random.getstate()==expected_rng and left['result']==right['result']
        scores=[row['best_ever_fitness'] for row in state['history']]
        assert all(b<=a for a,b in zip(scores,scores[1:]))
        assert independent_conflicts(state['best'])==dict(faculty=0,room=0,section=0)
        assert state['best'] is not state['population'][0]
        state['population'][0][0].title='Fictional mutation control'
        assert state['best'][0].title!='Fictional mutation control'
    write_observation('adapter-engine-continuation',dict(original_engine=engine.ENGINE_VERSION,adapter_source='FICTIONAL_TEST_ONLY',
        same_seed_and_resumed_results_equal=True,final_rng_equal=True,original_checkpoint_read_write=True,
        best_ever_history=scores,best_graph_independent=True,hard_conflicts=dict(faculty=0,room=0,section=0)))
