"""Fictional authorization and existing lifecycle contracts; no continuous GA."""
import copy
import inspect
from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.engine import Engine
from main import app
from services import continuous_readiness as foundation
from services.preference_authorization import current_principal,PreferencePrincipal
from services.ga_control_service import RunControl


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setattr(Engine,'connect',lambda *_a,**_k:pytest.fail('Readiness attempted database access'))
    previous=copy.copy(app.dependency_overrides)
    app.dependency_overrides[current_principal]=lambda:PreferencePrincipal('admin')
    yield
    app.dependency_overrides.clear();app.dependency_overrides.update(previous)


def test_server_contract_has_no_executable_dataset_or_verified_consumption():
    v=foundation.readiness()
    assert v['executable'] is False and v['availability']=='BLOCKED' and v['supported_datasets']==[]
    assert v['receipt_capability']=='UNVERIFIED_ONLY' and v['input_consumption']=='NOT_ESTABLISHED'
    assert v['lifecycle']['commands']=='UNAVAILABLE' and v['safeguards']['enforcement']=='NOT_IMPLEMENTED'
    assert len(v['requirements'])==5 and len({r['code'] for r in v['requirements']})==5
    assert v['lifecycle']['states']==list(foundation.STATES)


def test_each_read_builds_fresh_values_without_shared_mutable_flags():
    first=foundation.readiness();first['executable']=True;first['lifecycle']['states'].clear();first['requirements'].clear()
    second=foundation.readiness();assert second['executable'] is False and len(second['lifecycle']['states'])==11 and len(second['requirements'])==5


@pytest.mark.parametrize('role',['faculty','chair'])
def test_role_does_not_grant_continuous_capability(role):
    app.dependency_overrides[current_principal]=lambda:PreferencePrincipal(role)
    with TestClient(app) as client:assert client.get('/api/ga/continuous/readiness').status_code==403


def test_unauthenticated_request_is_rejected():
    def absent():raise HTTPException(401,'Fictional sign-in required')
    app.dependency_overrides[current_principal]=absent
    with TestClient(app) as client:assert client.get('/api/ga/continuous/readiness').status_code==401


@pytest.mark.parametrize('query',['enabled=true','mode=continuous','faculty=other','dataset=fictional','receipt=fictional-unverified'])
def test_client_activation_and_context_inputs_fail_closed(query):
    with TestClient(app) as client:assert client.get('/api/ga/continuous/readiness?'+query).status_code==422


@pytest.mark.parametrize('path',['readiness','runs','start','pause','resume','stop'])
def test_no_continuous_execution_or_control_routes_exist(path):
    with TestClient(app) as client:assert client.post('/api/ga/continuous/'+path,json={'enabled':True}).status_code in (404,405)


def test_get_body_is_not_accepted_as_configuration():
    with TestClient(app) as client:assert client.request('GET','/api/ga/continuous/readiness',json={'enabled':True}).status_code==422


def test_repeated_concurrent_reads_never_admit_discover_or_write(monkeypatch):
    import importlib
    from concurrent.futures import ThreadPoolExecutor
    from services import ga_checkpoint_service,ga_history_service,chromosome_service
    router=importlib.import_module('routers.genetic_algorithm')
    def forbidden(*_a,**_k):pytest.fail('Read-only foundation attempted lifecycle or persistence')
    for obj,name in [(router,'_admit_execution'),(router,'_execute_with_history'),(router._run_registry,'discover'),(router._run_registry,'register'),
        (ga_checkpoint_service,'write_marker'),(ga_history_service,'write_document'),(chromosome_service,'save_best_if_better')]:monkeypatch.setattr(obj,name,forbidden)
    with TestClient(app) as client:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda _:client.get('/api/ga/continuous/readiness'),range(12)))
    assert all(r.status_code==200 and r.json()['executable'] is False for r in results)


def test_existing_fixed_lifecycle_requests_are_idempotent_and_do_not_optimistically_pause(monkeypatch):
    # State-unit characterization only; real checkpoint creation/restoration uses
    # the unchanged existing pause/resume suites, not this marker stand-in.
    from services import ga_checkpoint_service
    markers=[];monkeypatch.setattr(ga_checkpoint_service,'write_marker',lambda *a,**k:markers.append(k))
    c=RunControl();c.start();c.boundary(0,10)
    assert c.request_pause()['state']=='PAUSE_REQUESTED' and c.request_pause()['already_requested']
    assert c.state!='PAUSED';assert c.begin_pause();assert c.finish_pause('fictional-unit-checkpoint')
    c.execution_active=False;c.begin_resume();c.resumed();assert c.state=='RUNNING'
    assert c.request_stop()['state']=='STOP_REQUESTED' and c.request_stop()['already_requested']
    assert c.state!='STOPPED';assert c.acknowledge_stop();c.finish('STOPPED');assert c.state=='STOPPED'


def test_fixed_signature_and_protected_engine_boundary_are_not_extended():
    from services.ga_service import run_genetic_algorithm
    signature=inspect.signature(run_genetic_algorithm)
    assert 'generations' in signature.parameters and 'optimization_mode' not in signature.parameters
    assert not hasattr(foundation,'start') and not hasattr(foundation,'resume')
