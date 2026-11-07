"""U5G legacy checkpoint regression, copied from unchanged U5F qualification.

Never runs against the repository's academic input tree. No continuous engine
exists; these tests qualify preservation of existing fixed execution only.
"""
import copy
import importlib
import json
from pathlib import Path
import random
import tempfile
import threading
import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from main import app
from services import ga_service as engine,ga_checkpoint_service as checkpoints,chromosome_service,ga_control_service
from services.ga_control_service import RunControl,RunRegistry
from services.preference_authorization import current_principal,PreferencePrincipal
from genetic_algorithm.utils import Functions
from genetic_algorithm.operators import FitnessFunction
from tests.d10.support import templates,preferences
from tests.d10.test_v1_baseline import test_real_current_v1_creation_restore_and_continuation as original_continuation

router=importlib.import_module('routers.genetic_algorithm')

@pytest.fixture
def fictional(monkeypatch,tmp_path):
    backend=Path(engine.__file__).resolve().parents[1];snapshot=backend.parent;owner=snapshot.parent
    if snapshot.name!='repository' or owner.parent!=Path(tempfile.gettempdir()).resolve() or not owner.name.startswith('u5c-r1-snapshot-') or not (owner/'OWNED-SNAPSHOT.json').is_file():
        pytest.skip('Real fixed-engine qualification requires the owned fictional source snapshot tool')
    assert backend.is_relative_to(owner)
    monkeypatch.setattr(Engine,'connect',lambda *_a,**_k:pytest.fail('Database access forbidden'))
    pref=backend/'data/faculty_preferences.json';settings=backend/'data/ga_settings.json'
    pref.write_text('[]\n',encoding='utf-8');settings.write_text('{}\n',encoding='utf-8')
    for obj,name,path in [(engine,'FACULTY_PREFERENCES_FILE',pref),(engine,'GA_SETTINGS_FILE',settings),(FitnessFunction,'PREFERENCE_FILE',pref),(FitnessFunction,'GA_SETTINGS_FILE',settings)]:monkeypatch.setattr(obj,name,path)
    values=templates(compact=True)
    for name,value in zip(('list_subjects','list_faculty','lst_rooms'),values):monkeypatch.setattr(engine,name,value)
    monkeypatch.setattr(engine,'df_faculty_pref',preferences());monkeypatch.setattr(Functions,'list_faculty',values[1])
    monkeypatch.setattr(chromosome_service,'BEST_CHROMOSOME_PATH',tmp_path/'best.json')
    monkeypatch.setattr(router,'LATEST_RESULT_FILE',tmp_path/'latest.json')
    monkeypatch.setattr(ga_control_service,'STOPPED_RUNS_DIR',tmp_path/'stopped')
    monkeypatch.setattr(router,'_run_registry',RunRegistry())
    prior=dict(app.dependency_overrides);app.dependency_overrides[current_principal]=lambda:PreferencePrincipal('admin')
    rng=random.getstate();random.seed(710)
    yield values,pref,settings
    random.setstate(rng);app.dependency_overrides.clear();app.dependency_overrides.update(prior)
    assert not router._ga_execution_lock.locked(),'Owned worker did not relinquish admission'


@pytest.mark.parametrize('pause_generation',[0,1,2])
def test_actual_original_v1_continuation_and_rng_parity(fictional,pause_generation):
    original_continuation(fictional[0],pause_generation)


def pause_at_zero(monkeypatch,after_resume=None):
    original=router.run_genetic_algorithm
    def wrapped(**parameters):
        # Bound this fictional qualification fixture using the existing engine's
        # supported parameters. Restore uses these exact checkpoint parameters;
        # no operator, fingerprint, or production default is replaced.
        parameters.setdefault('mutation_attempts',1)
        parameters.setdefault('max_restarts',5)
        callback=parameters['progress_callback'];resuming=parameters.get('resume_state') is not None
        def progress(kind,data):
            callback(kind,data)
            if not resuming and data['generation']==0:parameters['run_control'].request_pause()
            if resuming and after_resume:after_resume(data)
        return original(**{**parameters,'progress_callback':progress})
    monkeypatch.setattr(router,'run_genetic_algorithm',wrapped)


def paused(client):
    response=client.post('/api/ga/run',params={'population_size':2,'generations':2,'fresh_chromosomes':0})
    assert response.status_code==200 and response.json()['run']['state']=='PAUSED'
    return response.json()['run']['run_id']


def finished(client,run,status):
    # The unchanged engine can perform 40 * 100 crossover attempts per
    # generation even for this two-offering fixture. Both retained failures
    # show eventual successful completion after the old 25-second assertion.
    # This is a bounded functional qualification, not a latency guarantee.
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        state=client.get('/api/ga/runs/'+run).json()
        if not state['execution_active'] and not router._ga_execution_lock.locked():assert state['state']==status;return state
        time.sleep(.01)
    pytest.fail('Owned fictional fixed worker did not finish')


def test_real_pause_restart_discovery_and_checkpoint_resume(fictional,monkeypatch):
    pause_at_zero(monkeypatch)
    with TestClient(app) as client:
        run=paused(client);before={p:p.read_bytes() for p in checkpoints.run_directory(run).iterdir() if p.name.endswith('.gz')}
        assert client.post(f'/api/ga/runs/{run}/pause').json()['already_requested']
        monkeypatch.setattr(router,'_run_registry',RunRegistry())
        assert client.get(f'/api/ga/runs/{run}/checkpoint-status').json()['resumable']
        assert client.post(f'/api/ga/runs/{run}/resume').status_code==200
        finished(client,run,'COMPLETED')
        assert {p:p.read_bytes() for p in before}==before
        assert router.LATEST_RESULT_FILE.exists()


@pytest.mark.parametrize('change',['preferences','weights'])
def test_original_strict_checkpoint_rejects_actual_fictional_input_drift(fictional,monkeypatch,change):
    pause_at_zero(monkeypatch)
    with TestClient(app) as client:
        run=paused(client)
        if change=='preferences':fictional[1].write_text('[ ]\n',encoding='utf-8')
        else:fictional[2].write_text(json.dumps({'underload_penalty':26}),encoding='utf-8')
        status=client.get(f'/api/ga/runs/{run}/checkpoint-status').json()
        assert not status['resumable']
        response=client.post(f'/api/ga/runs/{run}/resume')
        assert response.status_code==409 and response.json()['detail']['code']=='GA_CHECKPOINT_INPUT_CHANGED'
        assert not router.LATEST_RESULT_FILE.exists()


def test_concurrent_resume_start_and_stop_use_one_actual_fixed_worker(fictional,monkeypatch):
    entered=threading.Event();release=threading.Event();observed=[]
    def boundary(data):
        if data['generation']==1:
            observed.append(1);entered.set();assert release.wait(15)
    pause_at_zero(monkeypatch,boundary)
    with TestClient(app) as client:
        run=paused(client)
        try:
            assert client.post(f'/api/ga/runs/{run}/resume').status_code==200
            assert entered.wait(15)
            assert client.post(f'/api/ga/runs/{run}/resume').json()['already_requested']
            assert client.post('/api/ga/run').status_code==409
            first=client.post(f'/api/ga/runs/{run}/stop').json()
            assert first['state']=='STOP_REQUESTED' and client.post(f'/api/ga/runs/{run}/stop').json()['already_requested']
        finally:release.set()
        finished(client,run,'STOPPED');assert len(observed)==1


def test_pre_initialization_cancellation_has_no_scoring_or_saved_result(fictional,monkeypatch):
    def forbidden(*_a,**_k):pytest.fail('Cancelled initialization executed GA work')
    monkeypatch.setattr(engine,'generate_population',forbidden);monkeypatch.setattr(engine,'faculty_preference_fitness',forbidden)
    c=RunControl();c.request_stop();c.start()
    assert engine.run_genetic_algorithm(2,2,0,run_control=c) is None
    assert not chromosome_service.BEST_CHROMOSOME_PATH.exists() and not router.LATEST_RESULT_FILE.exists()


def test_fixed_worker_failure_releases_admission_without_success_claim(fictional,monkeypatch):
    def failed(**_):raise ValueError('Fictional injected worker failure')
    monkeypatch.setattr(router,'run_genetic_algorithm',failed)
    with TestClient(app) as client:
        assert client.post('/api/ga/run',params={'population_size':2,'generations':2,'fresh_chromosomes':0}).status_code==500
        assert not router._ga_execution_lock.locked() and not router.LATEST_RESULT_FILE.exists()
        assert all(c.state=='FAILED' for c in router._run_registry.runs.values())


def test_captured_copy_preserves_original_scoring_and_publication_oracle(fictional):
    # The original engine still runs its original global-input path. This tests
    # copied-template scoring/reconstruction only, NOT bundle consumption by GA.
    from services import ga_input_bundle as bundle
    from genetic_algorithm.utils.FrozenInputs import capture_inputs, scoring_inputs
    from services.ga_publication_service import validate_publication
    source_identity = checkpoints.input_fingerprint()
    captured = bundle.capture(run_id='00000000-0000-4000-8000-000000000703',
        templates=fictional[0], fallback_templates=fictional[0], legacy_preferences=engine.df_faculty_pref,
        scoring_context=capture_inputs(), configuration=dict(population_size=2,generations=2,fresh_chromosomes=0,baseline_mode='fresh',mutation_attempts=1,max_restarts=5),
        source_identities=dict(dataset=source_identity,engine=checkpoints.engine_fingerprint(),loader='c'*64,transformation='d'*64))
    working = captured.materialize(captured.run_id)
    result = engine.run_genetic_algorithm(**working['configuration'])
    state = random.getstate()
    candidate = chromosome_service.payload_to_chromosome(result,*working['templates'])
    validate_publication(candidate,*working['templates'])
    token = scoring_inputs.set(working['scoring_context'])
    try:
        score,breakdown = FitnessFunction.faculty_preference_fitness(candidate,working['legacy_preferences'],return_breakdown=True)
    finally:scoring_inputs.reset(token)
    assert score == result['best_fitness'] and breakdown == result['fitness_breakdown']
    assert random.getstate() == state
    assert captured.qualification(captured.run_id)['verification_status']=='UNVERIFIED'
