"""U5B fictional context/capture/projection tests. All writes use fresh tmp_path stores."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import json
import random
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
from sqlalchemy.engine import Engine

from main import app
from services import ga_academic_context as academic, ga_run_provenance as provenance
from services import ga_evaluation_v2 as projection, ga_result_compatibility as legacy, ga_history_service as history
from services.preference_authorization import current_principal, PreferencePrincipal
from tests.test_ga_result_compatibility import identity, documents, store, RUN
from tests.d10.test_v1_baseline import baseline


def context(inputs="c"*64, **changes):
    return academic.AcademicContext(academic_year_id="00000000-0000-4000-8000-000000000701",
        term_id="00000000-0000-4000-8000-000000000702",scope_id="00000000-0000-4000-8000-000000000703",
        academic_year="FICTIONAL-YEAR",term="FICTIONAL-TERM",department="Fictional Department",
        dataset_id="fictional-dataset",dataset_revision="fictional-revision.1",input_fingerprint=inputs,**changes)


def verification(value=None, **changes):
    now=datetime.now(timezone.utc)
    data=dict(context=value or context(),state="VERIFIED",verification_reference="fictional-verification.1",
        issued_at=(now-timedelta(minutes=1)).isoformat(),expires_at=(now+timedelta(minutes=10)).isoformat())
    return academic.ContextVerification(**{**data,**changes})


@pytest.fixture(autouse=True)
def isolation(monkeypatch,tmp_path):
    monkeypatch.setattr(provenance,"PROVENANCE_DIR",tmp_path/"provenance")
    monkeypatch.setattr(Engine,"connect",lambda *_a,**_k:pytest.fail("U5B attempted database access"))
    # Restore the complete override dictionary, not only the last role override.
    before=dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear();app.dependency_overrides.update(before)


@pytest.fixture
def trusted(monkeypatch):
    monkeypatch.setattr(legacy,"current_identity",identity)
    monkeypatch.setattr(provenance,"current_identity",identity)
    monkeypatch.setattr(academic,"verification_for",lambda _:verification())


def started(run=RUN):
    return SimpleNamespace(run_id=run,started_at=datetime.now(timezone.utc).isoformat(),latest_completed_generation=None)


def captured(trusted, fitness=0):
    control=started()
    parameters=dict(population_size=2,generations=2,fresh_chromosomes=0,baseline_mode="fresh",mutation_attempts=1,max_restarts=5)
    record=provenance.begin(control,parameters)
    index,snapshot=documents(fitness=fitness)
    index["started_at"]=control.started_at
    index["configuration"]=snapshot["ga_configuration"]=parameters
    snapshot["metrics"]["configuration_fingerprint"]=record["configuration_fingerprint"]
    snapshot.pop("academic_context")  # Original history format remains unchanged.
    store(index,snapshot)
    return control,record,index,snapshot


@pytest.mark.parametrize("field,value",[("academic_year",""),("term"," "),("department","Fictional\nDepartment"),
    ("scope_id","not-an-id"),("dataset_id",""),("dataset_revision"," "),("input_fingerprint","not-a-hash")])
def test_context_requires_explicit_canonical_data(field,value):
    values=context().model_dump();values[field]=value
    with pytest.raises(ValidationError):academic.AcademicContext.model_validate(values)


def test_context_is_frozen_and_digest_is_deterministic():
    original=context()
    assert original.digest==academic.AcademicContext.model_validate(dict(reversed(list(original.model_dump().items())))).digest
    with pytest.raises(ValidationError):original.term="Other"
    with pytest.raises(ValidationError):academic.AcademicContext.model_validate({**original.model_dump(),"approved_by_client":True})


@pytest.mark.parametrize("case",["plain_dict","expired","future","naive","wrong_inputs","unsupported"])
def test_unverifiable_provider_values_are_rejected_before_writes(monkeypatch,case):
    supplied=verification()
    if case=="plain_dict":supplied=supplied.model_dump()
    elif case=="expired":supplied=supplied.model_copy(update={"expires_at":"2000-01-01T00:00:00+00:00"})
    elif case=="future":supplied=supplied.model_copy(update={"issued_at":"2099-01-01T00:00:00+00:00"})
    elif case=="naive":supplied=supplied.model_copy(update={"issued_at":"2000-01-01T00:00:00"})
    elif case=="wrong_inputs":supplied=verification(context("f"*64))
    else:supplied=supplied.model_copy(update={"state":"UNVERIFIED"})
    monkeypatch.setattr(academic,"verification_for",lambda _:supplied)
    with pytest.raises(history.HistoryError,match="verification is unavailable"):academic.verified_context(identity())
    assert not provenance.PROVENANCE_DIR.exists()


def test_default_missing_provider_never_creates_a_record_or_infers_a_term(monkeypatch):
    assert academic.verification_for(identity()) is None
    monkeypatch.setattr(provenance,"current_identity",identity)
    assert provenance.begin(started(),{}) is None and not provenance.PROVENANCE_DIR.exists()
    monkeypatch.setattr(legacy,"current_identity",identity)
    result=projection.evaluation()
    assert result["schema_version"]==2 and result["current_runs"]==0 and result["best"] is None
    assert result["current_identity"]["context_verification"]=="UNAVAILABLE"


def test_record_is_complete_immutable_and_not_rewritten_on_repeat(trusted):
    control=started();record=provenance.begin(control,{})
    before=provenance.path_for(RUN).read_bytes()
    assert provenance.read(RUN)==record
    with pytest.raises(history.HistoryError,match="already exists"):provenance.begin(control,{})
    assert provenance.path_for(RUN).read_bytes()==before
    assert not list(provenance.PROVENANCE_DIR.glob('*.tmp'))


def test_capture_never_backfills_history_or_creates_on_resume(trusted):
    control=started()
    history.write_document(history.directory(RUN)/"index.json",{"schema_version":1,"fictional":True})
    with pytest.raises(history.HistoryError,match="existing run"):provenance.begin(control,{})
    assert provenance.begin(control,{"resume_state":{"fictional":True}}) is None
    assert not provenance.PROVENANCE_DIR.exists()


@pytest.mark.parametrize("mode",["saved","uploaded"])
def test_saved_best_contract_is_not_extended_by_context_capture(trusted,mode):
    with pytest.raises(history.HistoryError,match="fresh runs only"):provenance.begin(started(),{"baseline_mode":mode})
    assert not provenance.PROVENANCE_DIR.exists()


def test_atomic_failure_and_provider_drift_do_not_publish_records(trusted,monkeypatch):
    monkeypatch.setattr(provenance.os,"link",lambda *_:(_ for _ in ()).throw(OSError("Fictional storage unavailable")))
    with pytest.raises(history.HistoryError,match="storage is unavailable"):provenance.begin(started(),{})
    assert not list(provenance.PROVENANCE_DIR.iterdir())
    values=iter([verification(),None]);monkeypatch.setattr(academic,"verification_for",lambda _:next(values))
    with pytest.raises(history.HistoryError,match="context changed"):provenance.begin(started(),{})
    assert not provenance.path_for(RUN).exists()


def test_input_drift_before_commit_rejects_provenance(trusted,monkeypatch):
    changed={**identity(),"input_fingerprint":"f"*64}
    values=iter([identity(),changed]);monkeypatch.setattr(provenance,"current_identity",lambda:next(values))
    with pytest.raises(history.HistoryError,match="inputs changed before"):provenance.begin(started(),{})
    assert not provenance.PROVENANCE_DIR.exists()


def test_current_projection_preserves_zero_precision_and_original_bytes(trusted):
    _,record,index,snapshot=captured(trusted)
    paths=[*history.SNAPSHOTS_DIR.rglob('*.json'),provenance.path_for(RUN)]
    before={path:path.read_bytes() for path in paths};rng=random.getstate()
    result=projection.evaluation()
    assert result["best"]["classification"]=="CURRENT" and result["best"]["fitness"]==0
    assert result["best"]["provenance"]["context_sha256"]==record["context_sha256"]
    assert result["current_identity"]["academic_context"]["dataset_id"]=="fictional-dataset"
    assert {path:path.read_bytes() for path in paths}==before and random.getstate()==rng
    assert "academic_context" not in history.get_generation(RUN,0)
    # A new module reader (restart) uses existing records, not a mutable cache.
    assert importlib.reload(projection).evaluation()==result


@pytest.mark.parametrize("kind",["missing","tampered","configuration","run_id"])
def test_missing_or_tampered_run_start_cannot_be_current(trusted,kind):
    captured(trusted)
    path=provenance.path_for(RUN)
    if kind=="missing":path.rename(path.with_suffix('.withheld'))
    else:
        document=json.loads(path.read_bytes())
        if kind=="tampered":document["data"]["academic_context"]["term"]="Fictional tamper"
        elif kind=="configuration":document["data"]["configuration"]["generations"]=3
        else:document["data"]["run_id"]="00000000-0000-4000-8000-000000000999"
        path.write_bytes(academic.canonical(document))
    result=projection.evaluation()
    assert result["current_runs"]==0 and result["best"] is None
    assert result["runs"][0]["classification"]=="UNKNOWN_COMPATIBILITY"


def test_context_revision_change_and_revocation_invalidate_current(trusted,monkeypatch):
    captured(trusted)
    changed=context().model_copy(update={"dataset_revision":"fictional-revision.2"})
    monkeypatch.setattr(academic,"verification_for",lambda _:verification(changed))
    assert projection.evaluation()["runs"][0]["reason"]=="ACADEMIC_CONTEXT_CHANGED"
    monkeypatch.setattr(academic,"verification_for",lambda _:None)
    result=projection.evaluation()
    assert result["runs"][0]["classification"]=="UNKNOWN_COMPATIBILITY" and result["best"] is None


def test_history_labels_alone_never_manufacture_run_start_proof(trusted):
    index,snapshot=documents();store(index,snapshot)
    result=projection.evaluation()
    assert result['best'] is None and result['runs'][0]['reason']=='RUN_START_PROVENANCE_NOT_CAPTURED'


@pytest.mark.parametrize('field',['started_at','generation_limit','configuration_fingerprint'])
def test_rehashed_but_semantically_mismatched_metadata_is_not_current(trusted,field):
    _,_,index,snapshot=captured(trusted)
    if field=='started_at':index.pop('started_at')
    elif field=='generation_limit':snapshot['metrics'][field]=3
    else:snapshot['metrics'][field]='f'*64
    store(index,snapshot)
    result=projection.evaluation()
    assert result['best'] is None and result['runs'][0]['reason']=='RUN_START_PROVENANCE_MISMATCH'


def test_invalid_configured_context_stops_before_any_ga_function(trusted,monkeypatch):
    router=importlib.import_module('routers.genetic_algorithm')
    monkeypatch.setattr(router,'validate_ga_inputs',lambda:None)
    monkeypatch.setattr(academic,'verification_for',lambda _:verification(expires_at='2000-01-01T00:00:00+00:00'))
    monkeypatch.setattr(router,'run_genetic_algorithm',lambda **_:pytest.fail('Unverifiable context started GA'))
    with pytest.raises(history.HistoryError):router._execute_with_history(started())
    assert not provenance.PROVENANCE_DIR.exists()


def test_query_parameters_cannot_override_server_context_and_auth_is_required(trusted):
    captured(trusted)
    with TestClient(app) as client:
        app.dependency_overrides[current_principal]=lambda:PreferencePrincipal("faculty")
        assert client.get('/api/ga/current-evaluation').status_code==403
        def absent():raise HTTPException(401,"Fictional missing session")
        app.dependency_overrides[current_principal]=absent
        assert client.get('/api/ga/current-evaluation').status_code==401
        app.dependency_overrides[current_principal]=lambda:PreferencePrincipal("admin")
        response=client.get('/api/ga/current-evaluation?academic_year=UNTRUSTED&term=UNTRUSTED&dataset_id=UNTRUSTED').json()
        assert response["best"]["classification"]=="CURRENT"
        assert response["current_identity"]["academic_context"]["term"]=="FICTIONAL-TERM"
        assert client.post('/api/ga/current-evaluation').status_code==405


def test_real_fictional_execution_hook_preserves_schedule_scores_and_rng(baseline,monkeypatch):
    from services import ga_service as engine, ga_checkpoint_service as checkpoints
    from services.ga_control_service import RunControl
    from genetic_algorithm.utils import Functions
    router=importlib.import_module('routers.genetic_algorithm')
    monkeypatch.setattr(router,'validate_ga_inputs',lambda:None)  # Fictional templates, not institutional loader admission.
    parameters=dict(population_size=2,generations=2,fresh_chromosomes=0,baseline_mode='fresh',mutation_attempts=1,max_restarts=5)
    initial=copy.deepcopy(baseline);original_rng=random.getstate();fingerprint=checkpoints.engine_fingerprint()
    try:
        random.seed(710);plain=engine.run_genetic_algorithm(**parameters);expected_rng=random.getstate()
        for name,value in zip(('list_subjects','list_faculty','lst_rooms'),copy.deepcopy(initial)):monkeypatch.setattr(engine,name,value)
        monkeypatch.setattr(Functions,'list_faculty',engine.list_faculty)
        technical=legacy.current_identity()
        monkeypatch.setattr(academic,'verification_for',lambda _:verification(context(technical['input_fingerprint'])))
        control=RunControl(configuration=parameters);control.start();random.seed(710)
        observed=router._execute_with_history(control,**parameters,run_control=control,progress_callback=control.capture_progress)
        assert random.getstate()==expected_rng
        for key in ('schedule','history','best_fitness','fitness_breakdown','faculty_analysis'):assert observed[key]==plain[key]
        control.finish('COMPLETED');history.update_lifecycle(control)
        result=projection.evaluation()
        assert result['best']['fitness']==observed['best_fitness']
        assert result['best']['classification']=='CURRENT'
        assert checkpoints.engine_fingerprint()==fingerprint
    finally:random.setstate(original_rng)
