"""Fictional U5D observation tests. No DB; every new store under tmp_path."""
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import importlib
import json
import random
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
from sqlalchemy.engine import Engine

from main import app
from services import ga_input_receipt as receipt,ga_service as engine,ga_checkpoint_service as checkpoint
from services import ga_history_service as history,ga_run_provenance as provenance,ga_result_compatibility as compatibility,ga_evaluation_v2
from services.preference_authorization import current_principal,PreferencePrincipal
from genetic_algorithm.utils.FrozenInputs import scoring_inputs
from tests.d10.support import templates,preferences
from tests.d10.test_v1_baseline import baseline

PARAMETERS=dict(population_size=2,generations=2,fresh_chromosomes=0,baseline_mode="fresh",mutation_attempts=1,max_restarts=5)


def control():
    return SimpleNamespace(run_id=str(uuid4()),started_at=datetime.now(timezone.utc).isoformat(),latest_completed_generation=None)


@pytest.fixture(autouse=True)
def isolated(monkeypatch,tmp_path):
    from genetic_algorithm.operators import FitnessFunction as fitness
    from genetic_algorithm.utils import Functions
    monkeypatch.setattr(Engine,"connect",lambda *_a,**_k:pytest.fail("U5D database access forbidden"))
    monkeypatch.setattr(provenance,"PROVENANCE_DIR",tmp_path/"provenance")
    pref=tmp_path/"fictional-preferences.json";pref.write_text("[]\n",encoding="utf-8")
    settings=tmp_path/"fictional-settings.json";settings.write_text("{}\n",encoding="utf-8")
    monkeypatch.setattr(fitness,"PREFERENCE_FILE",pref);monkeypatch.setattr(fitness,"GA_SETTINGS_FILE",settings)
    monkeypatch.setattr(engine,"FACULTY_PREFERENCES_FILE",pref);monkeypatch.setattr(engine,"GA_SETTINGS_FILE",settings)
    resources=templates(compact=True)
    for name,value in zip(("list_subjects","list_faculty","lst_rooms"),resources):monkeypatch.setattr(engine,name,value)
    monkeypatch.setattr(engine,"df_faculty_pref",preferences())
    monkeypatch.setattr(Functions,"list_faculty",resources[1])
    previous=dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear();app.dependency_overrides.update(previous)


def event(observer,generation=0,**changes):
    from services.ga_run_provenance import configuration_fingerprint
    return {"generation":generation,"input_fingerprint":observer.start.dataset_fingerprint,
        "configuration_fingerprint":configuration_fingerprint(observer.start.dataset_fingerprint,PARAMETERS),**changes}


def frozen(observer,**changes):
    return {"input_fingerprint":observer.start.dataset_fingerprint,"settings":{},"preferences":[],
        "system_faculty":[],"preference_scoring_version":2,**changes}


def test_matching_observations_never_claim_full_consumption_or_current():
    c=control();rng=random.getstate();before=receipt.runtime_digest()
    observer=receipt.begin(c,PARAMETERS)
    token=scoring_inputs.set(frozen(observer))
    try:observer.progress("initial_population_ready",event(observer))
    finally:scoring_inputs.reset(token)
    assert observer.finish("CALL_RETURNED")
    result=receipt.read(c.run_id)
    assert result["start"]["loaded_model_fingerprint"]==before
    assert result["end"]["generation_observations"]==1
    assert result["verification_status"]=="UNVERIFIED" and not result["eligible_for_current"]
    assert random.getstate()==rng and receipt.runtime_digest()==before


@pytest.mark.parametrize("kind",["faculty","subject","section","room","eligibility"])
def test_runtime_model_drift_changes_the_observed_fingerprint(kind):
    before=receipt.runtime_digest()
    if kind=="faculty":engine.list_faculty[0].admin_load+=1
    elif kind=="subject":engine.list_subjects[0].credit_units+=1
    elif kind=="section":engine.list_subjects[0].section.code="FIC-CHANGED"
    elif kind=="room":engine.lst_rooms[0].name="Fictional changed room"
    else:engine.list_faculty[0].eligible_subjects={"FIC-CHANGED"}
    assert receipt.runtime_digest()!=before
    observer=receipt.begin(control(),PARAMETERS)
    assert observer.start.verification_status=="UNVERIFIED"


def test_stale_cached_models_do_not_become_verified_when_disk_digest_changes(monkeypatch):
    from services import ga_progress_service
    cached=receipt.runtime_digest();observer=receipt.begin(control(),PARAMETERS)
    monkeypatch.setattr(ga_progress_service,"input_fingerprint",lambda:"f"*64)
    assert observer.finish("CALL_RETURNED")
    result=receipt.read(observer.start.run_id)
    assert result["start"]["loaded_model_fingerprint"]==cached and "DATASET_CHANGED" in result["reasons"]
    assert not result["eligible_for_current"]


@pytest.mark.parametrize("key,value",[("preferences",[{"faculty_code":9001,"style":"fictional-change"}]),("settings",{"fictional_penalty":2}),
    ("system_faculty",["fictional-changed-cohort"])])
def test_active_scoring_context_drift_is_reported_without_scoring(key,value):
    observer=receipt.begin(control(),PARAMETERS);state=frozen(observer);token=scoring_inputs.set(state)
    try:
        observer.progress("initial_population_ready",event(observer));state[key]=value
        observer.progress("generation_completed",event(observer,1))
    finally:scoring_inputs.reset(token)
    assert observer.finish("CALL_RETURNED")
    result=receipt.read(observer.start.run_id)
    assert "SCORING_CONTEXT_CHANGED" in result["reasons"] and not result["eligible_for_current"]


def test_configuration_and_cross_run_event_drift_fail_closed():
    observer=receipt.begin(control(),PARAMETERS);token=scoring_inputs.set(frozen(observer))
    try:
        observer.progress("initial_population_ready",event(observer,run_id=str(uuid4())))
        observer.progress("initial_population_ready",event(observer,configuration_fingerprint="e"*64))
    finally:scoring_inputs.reset(token)
    assert observer.finish("CALL_RETURNED")
    assert {"CROSS_RUN_EVENT","CONFIGURATION_DRIFT"}<=set(receipt.read(observer.start.run_id)["reasons"])


def test_effective_configuration_and_callback_absence_are_explicit():
    a=receipt.begin(control(),PARAMETERS)
    b=receipt.begin(control(),{**PARAMETERS,"population_size":3})
    assert a.start.configuration_fingerprint!=b.start.configuration_fingerprint
    assert a.start.loaded_model_fingerprint==b.start.loaded_model_fingerprint
    assert a.finish("CALL_RETURNED")
    assert "SCORING_CONTEXT_NOT_OBSERVED" in receipt.read(a.start.run_id)["reasons"]


def test_saved_seed_is_not_read_or_attributed_to_the_template_observation():
    observer=receipt.begin(control(),{**PARAMETERS,"baseline_mode":"saved"})
    assert "SEED_INPUT_NOT_BOUND" in observer.start.reasons
    assert observer.start.observer_source_fingerprint==__import__('hashlib').sha256(__import__('pathlib').Path(receipt.__file__).read_bytes()).hexdigest()


def test_unsupported_model_capture_is_an_explicit_failure_reason(monkeypatch):
    monkeypatch.setattr(receipt,"runtime_digest",lambda:(_ for _ in ()).throw(ValueError("Fictional unsupported model")))
    observer=receipt.begin(control(),PARAMETERS)
    assert observer.start.loaded_model_fingerprint is None and "MODEL_OBSERVATION_UNAVAILABLE" in observer.start.reasons


def test_receipt_storage_failure_prevents_a_new_record_not_a_fake_success(monkeypatch):
    monkeypatch.setattr(receipt.os,"link",lambda *_:(_ for _ in ()).throw(OSError("Fictional denied receipt storage")))
    with pytest.raises(history.HistoryError) as failure:receipt.begin(control(),PARAMETERS)
    assert failure.value.status==503 and not list(receipt.RECEIPTS_DIR.rglob('start.json'))


def test_cross_run_record_copy_rejected_without_overwriting_original():
    first=receipt.begin(control(),PARAMETERS);assert first.finish("CALL_RETURNED")
    other=str(uuid4());target=receipt.directory(other);target.mkdir()
    for name in ["start.json","end.json"]:(target/name).write_bytes((receipt.directory(first.start.run_id)/name).read_bytes())
    with pytest.raises(history.HistoryError):receipt.read(other)
    assert receipt.read(first.start.run_id)["record_state"]=="RECORDED"


@pytest.mark.parametrize("case",["hash","schema","missing_schema","missing_scope","unknown_field","verified","wrong_binding","duplicate","oversized"])
def test_corrupt_or_forged_receipts_are_rejected_even_when_rehashed(case):
    observer=receipt.begin(control(),PARAMETERS);observer.finish("CALL_RETURNED")
    name="end.json" if case=="wrong_binding" else "start.json";path=receipt.directory(observer.start.run_id)/name
    document=json.loads(path.read_bytes())
    if case=="hash":document["sha256"]="f"*64
    else:
        data=document["data"]
        if case=="schema":data["schema_version"]=True
        elif case=="missing_schema":data.pop("schema_version")
        elif case=="missing_scope":data.pop("fingerprint_scope")
        elif case=="unknown_field":data["client_approved"]=True
        elif case=="verified":data["verification_status"]="VERIFIED"
        elif case=="wrong_binding":data["start_receipt_sha256"]="f"*64
        document["sha256"]=receipt.digest(data)
    raw=receipt.canonical(document)
    if case=="duplicate":raw=raw.replace(b'"schema_version":1',b'"schema_version":1,"schema_version":1')
    if case=="oversized":raw=b" "*(receipt.MAX_BYTES+1)
    path.write_bytes(raw)
    with pytest.raises(history.HistoryError):receipt.read(observer.start.run_id)


def test_missing_legacy_and_resumed_receipts_are_not_backfilled():
    c=control();assert receipt.read(c.run_id)["record_state"]=="MISSING"
    assert receipt.begin(c,{**PARAMETERS,"resume_state":{"fictional":True}}) is None
    history.directory(c.run_id).mkdir(parents=True)
    marker=history.directory(c.run_id)/"index.json";marker.write_text('{"fictional":"legacy"}',encoding="utf-8");before=marker.read_bytes()
    assert receipt.begin(c,PARAMETERS) is None and marker.read_bytes()==before
    assert receipt.read(c.run_id)["record_state"]=="MISSING"


def test_academic_reference_is_server_record_bound_but_never_approval(monkeypatch):
    from services import ga_academic_context as academic
    from tests.test_ga_academic_context import context,verification
    technical=compatibility.current_identity()
    monkeypatch.setattr(academic,"verification_for",lambda _:verification(context(technical["input_fingerprint"])))
    c=control();record=provenance.begin(c,PARAMETERS)
    observer=receipt.begin(c,PARAMETERS)
    assert observer.start.academic_context_reference=={"provenance_sha256":receipt.digest(record),"academic_context_sha256":record["context_sha256"]}
    assert observer.start.institutional_authorization=="NOT_ESTABLISHED" and observer.start.verification_status=="UNVERIFIED"


def test_incomplete_interrupted_and_failed_final_record_are_never_success_claims(monkeypatch):
    observer=receipt.begin(control(),PARAMETERS)
    assert receipt.read(observer.start.run_id)["record_state"]=="INCOMPLETE"
    assert observer.finish("CALL_INTERRUPTED")
    assert "CALL_INTERRUPTED" in receipt.read(observer.start.run_id)["reasons"]
    second=receipt.begin(control(),PARAMETERS)
    monkeypatch.setattr(receipt,"write",lambda *_:(_ for _ in ()).throw(OSError("Fictional storage unavailable")))
    assert second.finish("CALL_RETURNED") is False
    assert receipt.read(second.start.run_id)["record_state"]=="INCOMPLETE"


def test_immutable_start_collision_stops_before_replacement():
    c=control();receipt.begin(c,PARAMETERS);path=receipt.directory(c.run_id)/"start.json";before=path.read_bytes()
    with pytest.raises(history.HistoryError,match="already exists"):receipt.begin(c,PARAMETERS)
    assert path.read_bytes()==before and not list(path.parent.glob('*.tmp'))


def test_distinct_thread_observations_are_isolated_not_a_concurrent_engine_claim():
    def observe(_):
        observer=receipt.begin(control(),PARAMETERS);token=scoring_inputs.set(frozen(observer,preferences=[{"fictional_index":_}]))
        try:observer.progress("initial_population_ready",event(observer))
        finally:scoring_inputs.reset(token)
        assert observer.finish("CALL_RETURNED")
        return receipt.read(observer.start.run_id)
    with ThreadPoolExecutor(max_workers=2) as pool:a,b=list(pool.map(observe,[1,2]))
    assert a["run_id"]!=b["run_id"] and a["end"]["scoring_context_first"]!=b["end"]["scoring_context_first"]
    assert scoring_inputs.get() is None


def test_observation_limit_and_missing_scoring_context_remain_unverified():
    observer=receipt.begin(control(),PARAMETERS)
    observer.progress("initial_population_ready",event(observer))
    token=scoring_inputs.set(frozen(observer))
    try:
        for generation in range(34):observer.progress("generation_completed",event(observer,generation))
    finally:scoring_inputs.reset(token)
    assert observer.finish("CALL_RETURNED")
    assert {"SCORING_CONTEXT_UNAVAILABLE","OBSERVATION_LIMIT_REACHED"}<=set(receipt.read(observer.start.run_id)["reasons"])


def test_admin_only_get_does_not_accept_client_receipts():
    c=control();receipt.begin(c,PARAMETERS)
    with TestClient(app) as client:
        def absent():raise HTTPException(401,"Fictional authentication required")
        app.dependency_overrides[current_principal]=absent
        assert client.get(f'/api/ga/runs/{c.run_id}/input-receipt').status_code==401
        for role in ["faculty","chair"]:
            app.dependency_overrides[current_principal]=lambda role=role:PreferencePrincipal(role)
            assert client.get(f'/api/ga/runs/{c.run_id}/input-receipt').status_code==403
        app.dependency_overrides[current_principal]=lambda:PreferencePrincipal("admin")
        assert client.get(f'/api/ga/runs/{c.run_id}/input-receipt?verified=true').json()["verification_status"]=="UNVERIFIED"
        assert client.post(f'/api/ga/runs/{c.run_id}/input-receipt',json={"verified":True}).status_code==405
        assert client.get('/api/ga/runs/invalid/input-receipt').status_code==404


def test_owned_loopback_http_read_uses_fictional_principals_and_temporary_receipts():
    import socket
    import threading
    import time
    from urllib.request import urlopen
    from urllib.error import HTTPError
    from fastapi import FastAPI
    import uvicorn
    from routers.ga_evaluation import router
    observer=receipt.begin(control(),PARAMETERS);assert observer.finish("CALL_RETURNED")
    before={p:p.read_bytes() for p in receipt.directory(observer.start.run_id).glob('*.json')}
    isolated_app=FastAPI();isolated_app.include_router(router)
    isolated_app.dependency_overrides[current_principal]=lambda:PreferencePrincipal("admin")
    listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM);listener.bind(('127.0.0.1',0))
    port=listener.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(isolated_app,host='127.0.0.1',port=port,lifespan='off',access_log=False,log_level='critical'))
    thread=threading.Thread(target=lambda:server.run(sockets=[listener]),daemon=True);thread.start()
    try:
        deadline=time.monotonic()+5
        while not server.started and thread.is_alive() and time.monotonic()<deadline:time.sleep(.02)
        assert server.started,"Owned fictional loopback fixture failed to start"
        url=f'http://127.0.0.1:{port}/api/ga/runs/{observer.start.run_id}/input-receipt'
        with urlopen(url,timeout=3) as response:body=json.load(response)
        assert body['run_id']==observer.start.run_id and body['verification_status']=='UNVERIFIED'
        isolated_app.dependency_overrides[current_principal]=lambda:PreferencePrincipal("faculty")
        with pytest.raises(HTTPError) as denied:urlopen(url,timeout=3)
        assert denied.value.code==403
        assert {p:p.read_bytes() for p in before}==before
    finally:
        server.should_exit=True;thread.join(timeout=5);listener.close()
        assert not thread.is_alive(),"Owned fictional HTTP server did not shut down"


def test_primary_engine_failure_is_not_overwritten_by_observer_teardown(monkeypatch):
    router=importlib.import_module('routers.genetic_algorithm');c=control()
    monkeypatch.setattr(router,"validate_ga_inputs",lambda:None)
    monkeypatch.setattr(router,"run_genetic_algorithm",lambda **_:(_ for _ in ()).throw(RuntimeError("Fictional primary failure")))
    monkeypatch.setattr(receipt.Observation,"finish",lambda *_:False)
    with pytest.raises(RuntimeError,match="Fictional primary failure"):router._execute_with_history(c,**PARAMETERS)
    assert receipt.read(c.run_id)["record_state"]=="INCOMPLETE"


def test_real_engine_wrapped_observations_preserve_results_scores_history_rng_and_fingerprints(baseline,monkeypatch):
    from services.ga_control_service import RunControl
    from genetic_algorithm.utils import Functions
    router=importlib.import_module('routers.genetic_algorithm');monkeypatch.setattr(router,"validate_ga_inputs",lambda:None)
    original=copy.deepcopy(baseline);rng=random.getstate();fingerprint=checkpoint.engine_fingerprint()
    try:
        random.seed(710);plain=engine.run_genetic_algorithm(**PARAMETERS);expected=random.getstate()
        for name,value in zip(("list_subjects","list_faculty","lst_rooms"),copy.deepcopy(original)):monkeypatch.setattr(engine,name,value)
        monkeypatch.setattr(Functions,"list_faculty",engine.list_faculty)
        c=RunControl(configuration=PARAMETERS);c.start();random.seed(710)
        observed=router._execute_with_history(c,**PARAMETERS,run_control=c,progress_callback=c.capture_progress)
        assert random.getstate()==expected
        for key in ["schedule","history","best_fitness","fitness_breakdown","faculty_analysis"]:assert observed[key]==plain[key]
        assert checkpoint.engine_fingerprint()==fingerprint
        data=receipt.read(c.run_id)
        assert data["end"]["generation_observations"]>0 and data["end"]["outcome"]=="CALL_RETURNED"
        assert not data["eligible_for_current"]
        assert ga_evaluation_v2.evaluation()["best"] is None
    finally:random.setstate(rng)


def test_actual_pause_resume_keeps_receipt_immutable_and_checkpoint_validation_strict(baseline,monkeypatch):
    from services.ga_control_service import RunControl
    router=importlib.import_module('routers.genetic_algorithm');monkeypatch.setattr(router,"validate_ga_inputs",lambda:None)
    c=RunControl(configuration=PARAMETERS);c.start();rng=random.getstate()
    def callback(kind,data):
        c.capture_progress(kind,data)
        if data["generation"]==0:c.request_pause()
    try:
        random.seed(710)
        paused=router._execute_with_history(c,**PARAMETERS,run_control=c,progress_callback=callback)
        assert isinstance(paused,checkpoint.PausedRun)
        assert receipt.read(c.run_id)["end"]["outcome"]=="PAUSED"
        paths=list(receipt.directory(c.run_id).glob('*.json'));before={p:p.read_bytes() for p in paths}
        state=checkpoint.load_checkpoint(c.run_id,copy.deepcopy(baseline))
        c.execution_active=False;c.begin_resume()
        result=router._execute_with_history(c,**state["parameters"],resume_state=state,run_control=c,progress_callback=c.capture_progress)
        assert isinstance(result,dict) and {p:p.read_bytes() for p in paths}==before
    finally:random.setstate(rng)
