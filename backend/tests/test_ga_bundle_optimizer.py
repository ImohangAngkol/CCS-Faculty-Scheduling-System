"""Fictional actual optimizer execution through the versioned bundle boundary."""
import copy
import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import pytest
from sqlalchemy.engine import Engine
from services.ga_input_bundle import capture, BundleError, digest, canonical
from services.ga_bundle_optimizer import Session
from services import ga_bundle_checkpoint as checkpoint

RUN = "00000000-0000-4000-8000-000000000801"
OTHER = "00000000-0000-4000-8000-000000000802"


@pytest.fixture
def make_bundle(monkeypatch):
    from tests.d10.support import templates, preferences
    from genetic_algorithm.models.ga_setting import GASetting
    from services import ga_checkpoint_service as original
    monkeypatch.setattr(Engine, "connect", lambda *_a, **_k: pytest.fail("Database access forbidden"))
    def make(run_id=RUN, generations=1, code_offset=0):
        models = templates(compact=True)
        for faculty in models[1]:faculty.code += code_offset
        frame = preferences();frame["Faculty_Code"] += code_offset
        return capture(run_id=run_id, templates=models, fallback_templates=models, legacy_preferences=frame,
            scoring_context={"preference_scoring_version":2,"settings":GASetting().to_dict(),"preferences":{},
                "system_faculty":copy.deepcopy(models[1]),"input_fingerprint":"a"*64},
            configuration=dict(population_size=2,generations=generations,fresh_chromosomes=0,baseline_mode="fresh",mutation_attempts=1,max_restarts=5),
            source_identities=dict(dataset="a"*64,engine=original.engine_fingerprint(),loader="c"*64,transformation="d"*64))
    return make


def start(bundle):return Session(bundle,run_id=bundle.run_id,random_state=random.Random(710).getstate())


def paused(bundle, generation=0):
    session=start(bundle)
    def callback(_kind, data):
        if data['generation']==generation:session.control.request_pause()
    assert session.run(callback) is None and session.control.state=='PAUSED'
    return session


def restore(bundle, session, **changes):
    args=dict(run_id=bundle.run_id,expected_fingerprint=session.checkpoint_fingerprint,
        expected_sequence=session.sequence,expected_parent=session.parent_fingerprint)
    args.update(changes)
    return Session.restore(bundle,session.checkpoint,**args)


def test_actual_initialization_consumes_bundle_and_never_saves_best(make_bundle,monkeypatch):
    from services import chromosome_service,ga_checkpoint_service
    def forbidden(*_a,**_k):pytest.fail('Legacy persistence invoked')
    monkeypatch.setattr(chromosome_service,'save_best_if_better',forbidden)
    monkeypatch.setattr(ga_checkpoint_service,'save_checkpoint',forbidden)
    before=random.getstate();session=start(make_bundle(generations=0))
    assert session.receipt()['verification_status']=='UNVERIFIED'
    result=session.run()
    assert result['best_fitness']==0 and len(result['schedule'])==2 and result['generations_completed']==0
    assert result['saved_best_updated'] is False and result['saved_best_fitness'] is None
    assert random.getstate()==before
    receipt=session.receipt()
    assert receipt['verification_status']=='VERIFIED' and not receipt['eligible_for_current']
    assert receipt['institutional_authorization']=='NOT_ESTABLISHED' and receipt['function_calls']>0


def test_actual_generations_and_best_ever_are_monotone(make_bundle):
    session=start(make_bundle());result=session.run()
    assert result['generations_completed']==1 and result['best_fitness']==0
    scores=[r.get('best_ever_fitness',r.get('best_fitness')) for r in result['history']]
    assert scores==sorted(scores,reverse=True)
    assert any('create_child_by_faculty_swap' in k for k in session.runtime.calls)
    assert any('mutate_by_swapping' in k for k in session.runtime.calls)


def test_checkpoint_pause_resume_has_exact_rng_best_history_and_schedule_parity(make_bundle):
    bundle=make_bundle();full=start(bundle);expected=full.run();saved=paused(bundle)
    assert saved.receipt()['verification_status']=='VERIFIED'
    resumed=restore(bundle,saved)
    assert resumed.receipt()['verification_status']=='UNVERIFIED'
    actual=resumed.run()
    for key in ['schedule','best_fitness','history','fitness_breakdown','faculty_analysis']:
        assert actual[key]==expected[key]
    assert resumed.runtime.random.getstate()==full.runtime.random.getstate()
    assert resumed.receipt()['verification_status']=='VERIFIED'


def test_identical_session_resume_and_checkpoint_lineage(make_bundle):
    bundle=make_bundle(generations=2);session=paused(bundle)
    first=session.checkpoint_fingerprint
    def again(_kind,data):
        if data['generation']==1:session.control.request_pause()
    assert session.run(again) is None
    assert session.sequence==2 and session.parent_fingerprint==first
    resumed=restore(bundle,session);assert resumed.run()['generations_completed']==2


@pytest.mark.parametrize('change',['pin','sequence','parent','bundle','run','bytes','version'])
def test_wrong_checkpoint_binding_and_corruption_fail_closed(make_bundle,change):
    bundle=make_bundle(generations=0);saved=paused(bundle)
    if change=='pin':kwargs={'expected_fingerprint':'b'*64}
    elif change=='sequence':kwargs={'expected_sequence':saved.sequence+1}
    elif change=='parent':kwargs={'expected_parent':'c'*64}
    elif change=='run':kwargs={'run_id':OTHER}
    elif change=='bundle':
        with pytest.raises(BundleError):restore(make_bundle(generations=1),saved)
        return
    elif change=='bytes':saved.checkpoint=saved.checkpoint[:-1];kwargs={}
    else:
        doc=json.loads(saved.checkpoint);doc['optimizer_version']='unsupported'
        saved.checkpoint=canonical(doc);saved.checkpoint_fingerprint=digest(saved.checkpoint);kwargs={}
    with pytest.raises(BundleError):restore(bundle,saved,**kwargs)


def test_cached_globals_and_dynamic_source_loaders_cannot_change_active_run(make_bundle,monkeypatch):
    from services import ga_service,ga_progress_service
    from genetic_algorithm.utils import Functions
    from genetic_algorithm.operators import FitnessFunction
    bundle=make_bundle();reference=start(bundle).run();session=start(bundle)
    def forbidden(*_a,**_k):raise AssertionError('External loader consulted')
    def mutate(_kind,data):
        if data['generation']==0:
            for owner in [ga_service,Functions]:
                for name in ['list_subjects','list_faculty','lst_rooms']:monkeypatch.setattr(owner,name,[])
            monkeypatch.setattr(FitnessFunction,'_load_ga_settings',forbidden)
            monkeypatch.setattr(FitnessFunction,'_load_dashboard_preferences',forbidden)
            monkeypatch.setattr(ga_progress_service,'input_fingerprint',forbidden)
    result=session.run(mutate)
    for key in ['schedule','history','best_fitness','fitness_breakdown']:assert result[key]==reference[key]
    assert session.receipt()['verification_status']=='VERIFIED'


def test_two_concurrent_runs_own_models_rng_and_receipts(make_bundle):
    first=start(make_bundle(generations=0));second=start(make_bundle(OTHER,generations=0,code_offset=10))
    before=random.getstate()
    with ThreadPoolExecutor(max_workers=2) as pool:
        outputs=list(pool.map(lambda s:s.run(),[first,second]))
    assert outputs[0]['schedule']!=outputs[1]['schedule'] and random.getstate()==before
    assert first.working['templates'][1][0] is not second.working['templates'][1][0]
    assert first.receipt()['run_id']!=second.receipt()['run_id']


def test_interrupted_callback_is_not_verified(make_bundle):
    session=start(make_bundle(generations=0))
    def fail(*_):raise RuntimeError('Fictional injected interruption')
    with pytest.raises(RuntimeError):session.run(fail)
    assert session.receipt()['verification_status']=='UNVERIFIED' and session.control.state=='FAILED'


def test_early_stop_without_consumption_is_not_verified(make_bundle):
    session=start(make_bundle());session.control.request_stop();assert session.run() is None
    assert session.control.state=='STOPPED' and session.receipt()['verification_status']=='UNVERIFIED'


def repack(bundle, change):
    working=bundle.materialize(bundle.run_id);doc=json.loads(bundle._raw);change(working)
    return capture(run_id=bundle.run_id,templates=working['templates'],fallback_templates=working['fallback_templates'],
        legacy_preferences=working['legacy_preferences'],scoring_context=working['scoring_context'],configuration=working['configuration'],
        source_identities=doc['source_identities'],seed=working['seed'])


@pytest.mark.parametrize('change',[
    lambda w:w['configuration'].update(generations=7),
    lambda w:setattr(w['templates'][1][0],'admin_load',0),
])
def test_admitted_workspace_or_configuration_drift_is_rejected(make_bundle,change):
    session=start(make_bundle(generations=0));change(session.working)
    with pytest.raises(BundleError):session.run()
    assert session.receipt()['verification_status']=='UNVERIFIED'


@pytest.mark.parametrize('change',[
    lambda w:w.update(fallback_templates=copy.deepcopy(w['templates'])),
    lambda w:w['scoring_context'].update(system_faculty=w['templates'][1]),
    lambda w:w['scoring_context']['system_faculty'].pop(),
    lambda w:setattr(w['scoring_context']['system_faculty'][0],'admin_load',0),
    lambda w:w['templates'][1].append(w['templates'][1][0]),
    lambda w:w['templates'][2].append(w['templates'][2][0]),
])
def test_inconsistent_cached_profile_alias_or_identity_is_rejected(make_bundle,change):
    bad=repack(make_bundle(generations=0),change)
    with pytest.raises(BundleError):start(bad)


@pytest.mark.parametrize('mode',['saved','uploaded'])
def test_pinned_seed_is_used_without_reading_application_stores(make_bundle,mode):
    bundle=make_bundle(generations=0);reference=start(bundle).run()
    def seed(w):w['configuration']['baseline_mode']=mode;w['seed']=reference
    result=start(repack(bundle,seed)).run()
    assert result['baseline_source']==mode and result['starting_baseline_fitness']==reference['best_fitness']
    assert result['saved_best_updated'] is False


def test_real_temporary_preference_and_weight_changes_do_not_change_resume(make_bundle,monkeypatch,tmp_path):
    from genetic_algorithm.operators import FitnessFunction
    from services import ga_service
    pref=tmp_path/'fictional-preferences.json';settings=tmp_path/'fictional-settings.json'
    pref.write_text('[]');settings.write_text('{}')
    for owner,name,path in [(FitnessFunction,'PREFERENCE_FILE',pref),(FitnessFunction,'GA_SETTINGS_FILE',settings),
                            (ga_service,'FACULTY_PREFERENCES_FILE',pref),(ga_service,'GA_SETTINGS_FILE',settings)]:monkeypatch.setattr(owner,name,path)
    bundle=make_bundle();full=start(bundle);reference=full.run();saved=paused(bundle)
    pref.write_text(json.dumps([{'faculty_code':990001,'preferred_subjects':['SYN102'],'faculty_priority':100}]))
    settings.write_text(json.dumps({'underload_penalty':999,'subject_penalty':999}))
    resumed=restore(bundle,saved);result=resumed.run()
    for key in ['schedule','history','best_fitness','fitness_breakdown']:assert result[key]==reference[key]
    assert resumed.runtime.random.getstate()==full.runtime.random.getstate()
    assert resumed.receipt()['verification_status']=='VERIFIED'


def test_active_scoring_context_mutation_is_not_verified(make_bundle):
    session=start(make_bundle(generations=0))
    def drift(*_):session.working['scoring_context']['settings']['underload_penalty']=888
    with pytest.raises(BundleError):session.run(drift)
    assert session.receipt()['verification_status']=='UNVERIFIED'


def test_missing_legacy_and_cross_run_checkpoint_are_not_adopted(make_bundle):
    bundle=make_bundle(generations=0);saved=paused(bundle)
    other=make_bundle(OTHER,generations=0)
    with pytest.raises(BundleError):restore(other,saved,run_id=OTHER)
    for raw in [None,canonical({'schema_version':1,'engine_version':'ga-continuation-v1'})]:
        with pytest.raises(BundleError):Session.restore(bundle,raw,run_id=RUN,expected_fingerprint='a'*64,expected_sequence=1,expected_parent=None)


def test_duplicate_inflight_execution_does_not_spawn_a_second_run(make_bundle):
    import threading
    session=start(make_bundle(generations=0));entered=threading.Event();release=threading.Event()
    def hold(*_):entered.set();assert release.wait(10)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(session.run,hold)
        try:
            assert entered.wait(10)
            with pytest.raises(BundleError,match='EXECUTION_ACTIVE'):session.run()
        finally:release.set()
        assert future.result(timeout=10)['generations_completed']==0
    assert session.receipt()['verification_status']=='VERIFIED'


def test_binder_rejects_unlisted_mutable_input_and_dynamic_import(make_bundle):
    runtime=start(make_bundle(generations=0)).runtime
    with pytest.raises(BundleError):runtime.bind_value({'fictional-derived-data':1})
    with pytest.raises(BundleError):runtime._import('services.identity_service',fromlist=('resolve_faculty_identity',))


def test_lecture_laboratory_rooms_and_complete_components_use_bound_resources(make_bundle):
    from genetic_algorithm.models.Subject import Subject
    from genetic_algorithm.models.Section import Section
    from genetic_algorithm.models.Room import Room
    from genetic_algorithm.models.Faculty import Faculty
    def mixed(w):
        faculty=[Faculty(990001,1,admin_load=21,eligible_subjects={'SYNLAB'})]
        subjects=[Subject('SYNLAB','Fictional mixed component',3,2,3,Section('SYN-LAB'))]
        rooms=[Room('Fictional lecture','Lecture'),Room('Fictional laboratory','Laboratory')]
        for resource in [*faculty,*rooms,subjects[0].section]:
            for index,day in enumerate(['monday','tuesday','wednesday','thursday','friday','saturday']):
                attr='time_blocks_'+day;setattr(resource,attr,getattr(resource,attr)[:16] if index<2 else [])
        w['templates']=(subjects,faculty,rooms);w['fallback_templates']=w['templates']
        w['scoring_context']['system_faculty']=copy.deepcopy(faculty)
    session=start(repack(make_bundle(generations=0),mixed));result=session.run()
    assert {row['type'] for row in result['schedule']}=={'Lecture','Laboratory'}
    assert {row['room'] for row in result['schedule']}=={'Fictional lecture','Fictional laboratory'}
    assert session.receipt()['verification_status']=='VERIFIED'


def test_fixed_section_commitment_is_not_reopened(make_bundle):
    def closure(w):
        for block in w['templates'][0][0].section.time_blocks_monday[:2]:
            block.is_available=False;block.fixed_schedule=True;block.fixed_course='Fictional external commitment'
    result=start(repack(make_bundle(generations=0),closure)).run()
    for row in result['schedule']:
        if row['subject']=='SYN101' and row['day']=='M':assert row['start'] not in ['7:30','07:30','8:00','08:00']


def test_preassigned_external_resource_declaration_is_preserved(make_bundle):
    from genetic_algorithm.models.PreassignedAssignment import PreassignedAssignment,ExternalInstructor
    def declared(w):
        subject=w['templates'][0][0]
        teacher=ExternalInstructor('external:fictional-bound','Fictional external instructor')
        subject.preassigned_instructor=teacher
        subject.preassigned_assignment=PreassignedAssignment(teacher.code,teacher.name,w['templates'][2][0].name)
    result=start(repack(make_bundle(generations=0),declared)).run()
    rows=[row for row in result['schedule'] if row['subject']=='SYN101']
    assert rows and all(row['faculty']=='external:fictional-bound' and row['room']=='Fictional Lecture Room' for row in rows)


def test_unknown_global_model_and_live_file_path_are_not_consumed(make_bundle,tmp_path):
    from genetic_algorithm.models.Faculty import Faculty
    runtime=start(make_bundle(generations=0)).runtime
    with pytest.raises(BundleError):runtime.bind_value(Faculty(990099,1))
    path=runtime.bind_value(tmp_path/'fictional-input.json')
    with pytest.raises(BundleError):path.read_bytes()


def test_active_resource_profile_mutation_is_not_verified(make_bundle):
    session=start(make_bundle(generations=0))
    def drift(*_):session.working['templates'][1][0].eligible_subjects.clear()
    with pytest.raises(BundleError,match='RESOURCE_PROFILE_CHANGED'):session.run(drift)
    assert session.receipt()['verification_status']=='UNVERIFIED'


def test_loaded_function_default_drift_invalidates_checkpoint(make_bundle,monkeypatch):
    from genetic_algorithm.utils import Functions
    bundle=make_bundle(generations=0);saved=paused(bundle)
    original=Functions.assign_random_two_hour_schedule.__defaults__
    monkeypatch.setattr(Functions.assign_random_two_hour_schedule,'__defaults__',(original[0]+1,*original[1:]))
    with pytest.raises(BundleError):restore(bundle,saved)


def test_loader_contract_fingerprint_mismatch_is_rejected(make_bundle):
    from services.ga_input_bundle import InputBundle
    original=make_bundle(generations=0);doc=json.loads(original._raw)
    doc['capture_implementation_fingerprint']='a'*64;raw=canonical(doc)
    with pytest.raises(BundleError,match='LOADER_VERSION_MISMATCH'):
        start(InputBundle.from_bytes(raw,original.run_id,digest(raw)))


def test_stale_checkpoint_rejected_against_trusted_latest_tip(make_bundle):
    bundle=make_bundle();session=paused(bundle);older=session.checkpoint
    session.run(lambda _kind,data:session.control.request_pause() if data['generation']==1 else None)
    assert session.sequence==2
    with pytest.raises(BundleError):Session.restore(bundle,older,run_id=bundle.run_id,
        expected_fingerprint=session.checkpoint_fingerprint,expected_sequence=session.sequence,expected_parent=session.parent_fingerprint)


def test_repeated_terminal_execution_does_not_rewrite_successful_receipt(make_bundle):
    session=start(make_bundle(generations=0));session.run();before=session.receipt()
    with pytest.raises(BundleError,match='EXECUTION_STATE'):session.run()
    assert session.receipt()==before and session.control.state=='COMPLETED'
