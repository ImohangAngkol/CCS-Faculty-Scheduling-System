"""Fictional U5A classification, read-only HTTP and unchanged-engine regressions."""
import copy
import hashlib
import importlib
import json
import random
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import app
from services import ga_result_compatibility as service, ga_history_service as history
from services.preference_authorization import current_principal, PreferencePrincipal
from tests.d10.test_v1_baseline import baseline

RUN = "00000000-0000-4000-8000-000000000601"


def identity():
    return {"engine_family": "V1", "engine_version": "ga-continuation-v1", "engine_fingerprint": "a"*64,
            "fitness_policy": "preference-policy-2", "preference_scoring_version": 2,
            "scorer_sha256": "b"*64, "constraint_policy": "v1-source-bound-publication-gate",
            "input_fingerprint": "c"*64, "result_schema_version": 1,
            "academic_context": {"kind": "verified-recorded-context", "academic_year": "FICTIONAL-YEAR", "term": "FICTIONAL-TERM"}}


def documents(run_id=RUN, fitness=12.3456789):
    metric = dict(generation=0, generation_limit=2, population_requested=2, population_actual=2,
        generation_best_fitness=fitness, best_ever_fitness=fitness, average_fitness=fitness,
        accepted_new_chromosomes_total=2, input_fingerprint="c"*64, configuration_fingerprint="d"*64,
        validation_status="passed", metrics_comparable=True)
    payload = dict(schedule=[], subject_keys=[], best_fitness=fitness)
    cid = history.candidate_id(payload)
    row = dict(generation=0, timestamp="2026-11-04T00:00:00+08:00", metrics=metric,
        generation_best_id=cid, best_ever_id=cid, capture_elapsed_ms=0, validation_elapsed_ms=0, snapshot_bytes=1)
    index = dict(schema_version=1, run_id=run_id, created_at=row["timestamp"], state="COMPLETED",
        configuration={"generations": 2}, input_fingerprint="c"*64, engine_fingerprint="a"*64,
        retention=dict(interval=1, max_run_bytes=100000, automatic_deletion=False),
        generations=[row], errors=[], skipped_generations=[], bytes_written=1)
    validation = dict(status="passed",gate="phase-3b-publication",validated_at=row["timestamp"],
        conflicts=0,eligibility_violations=0,overload_violations=0,fixed_schedule_violations=0,
        preassignment_violations=0,component_duration_violations=0)
    snapshot = dict(schema_version=1, run_id=run_id, generation=0, timestamp=row["timestamp"], metrics=metric,
        engine_fingerprint="a"*64, ga_configuration=index["configuration"], fitness_configuration={},
        generation_best=dict(chromosome_id=cid,payload=payload,workload=[]),
        best_ever=dict(chromosome_id=cid,payload=payload,workload=[]),fitness_breakdown=None,
        breakdown_unavailable_reason="Fictional observation only.",capture_elapsed_ms=0,validation_elapsed_ms=0,
        validation=validation, academic_context=identity()["academic_context"], reporting_context=dict(version=1,preference_scoring_version=2,
            engine_fingerprint="a"*64,input_fingerprint="c"*64,scorer_sha256="b"*64,settings={}))
    return index, snapshot


def store(index, snapshot):
    root = history.directory(index["run_id"])
    history.write_document(root/"index.json", index)
    history.write_document(root/"generation-000000.json", snapshot)


def test_current_exact_zero_and_no_input_mutation():
    for fitness in [0,12.3456789,-1.23456789]:
        index, snapshot = documents(fitness=fitness)
        before = copy.deepcopy((index,snapshot))
        assert service.classify(index,snapshot,identity())["classification"] == service.CURRENT
        assert (index,snapshot) == before


@pytest.mark.parametrize("field,value,expected", [
    ("policy",1,"LEGACY_INCOMPATIBLE"),("policy",3,"UNKNOWN_COMPATIBILITY"),
    ("engine","e"*64,"LEGACY_INCOMPATIBLE"),("input","e"*64,"LEGACY_INCOMPATIBLE"),
    ("context",None,"UNKNOWN_COMPATIBILITY"),("policy",None,"UNKNOWN_COMPATIBILITY"),
    ("config",None,"UNKNOWN_COMPATIBILITY"),("comparable",False,"UNKNOWN_COMPATIBILITY"),
    ("penalty",float("nan"),"UNKNOWN_COMPATIBILITY"),("schema",2,"UNKNOWN_COMPATIBILITY"),
])
def test_explicit_differences_and_missing_metadata(field,value,expected):
    index,snapshot=documents()
    if field=="policy":snapshot["reporting_context"]["preference_scoring_version"]=value
    elif field=="engine":
        index["engine_fingerprint"]=snapshot["engine_fingerprint"]=snapshot["reporting_context"]["engine_fingerprint"]=value
    elif field=="input":
        index["input_fingerprint"]=snapshot["metrics"]["input_fingerprint"]=snapshot["reporting_context"]["input_fingerprint"]=value
    elif field=="context":snapshot["reporting_context"]=value
    elif field=="config":snapshot["metrics"]["configuration_fingerprint"]=value
    elif field=="comparable":snapshot["metrics"]["metrics_comparable"]=value
    elif field=="penalty":snapshot["metrics"]["best_ever_fitness"]=value
    elif field=="schema":snapshot["schema_version"]=value
    assert service.classify(index,snapshot,identity())["classification"]==expected


def test_history_identity_policy_and_monotonicity_are_not_guessed():
    for key in ["engine_fingerprint","input_fingerprint","settings","scorer_sha256"]:
        index,snapshot=documents();snapshot["reporting_context"].pop(key)
        assert service.classify(index,snapshot,identity())["classification"]==service.UNKNOWN
    index,snapshot=documents();snapshot["run_id"]="00000000-0000-4000-8000-000000000602"
    assert service.classify(index,snapshot,identity())["classification"]==service.UNKNOWN


def test_missing_academic_context_is_not_replaced_by_input_hash():
    index,snapshot=documents()
    current=identity();current["academic_context"]={"kind":"legacy-input-file-set","academic_year":None,"term":None}
    assert service.classify(index,snapshot,current)["reason"]=="ACADEMIC_CONTEXT_NOT_ESTABLISHED"
    snapshot.pop("academic_context")
    assert service.classify(index,snapshot,identity())["reason"]=="ACADEMIC_CONTEXT_NOT_CAPTURED_OR_MISMATCHED"


def test_distinct_configurations_have_no_cross_configuration_best(monkeypatch):
    monkeypatch.setattr(service,"current_identity",identity)
    for suffix in [601,602]:
        index,snapshot=documents(run_id=f"00000000-0000-4000-8000-{suffix:012d}",fitness=suffix)
        snapshot["metrics"]["configuration_fingerprint"]=("d" if suffix==601 else "f")*64
        store(index,snapshot)
    result=service.evaluation()
    assert result["current_runs"]==2 and result["best"] is None
    assert result["issues"]==["INCOMPARABLE_CONFIGURATIONS"]
    index,snapshot=documents();index["generations"].append(copy.deepcopy(index["generations"][0]))
    assert service.classify(index,snapshot,identity())["classification"]==service.UNKNOWN


def test_best_selection_filters_history_and_never_promotes_saved_best(monkeypatch):
    monkeypatch.setattr(service,"current_identity",identity)
    for suffix,fitness,policy,state in [(601,12.3456789,2,"COMPLETED"),(602,0,1,"COMPLETED"),(603,1,2,"FAILED")]:
        index,snapshot=documents(run_id=f"00000000-0000-4000-8000-{suffix:012d}",fitness=fitness)
        index["state"]=state;snapshot["reporting_context"]["preference_scoring_version"]=policy;store(index,snapshot)
    before={p:p.read_bytes() for p in history.SNAPSHOTS_DIR.rglob('*') if p.is_file()}
    rng=random.getstate()
    monkeypatch.setattr(history.checkpoints,"atomic_write",lambda *_:pytest.fail("Read attempted a write"))
    result=service.evaluation()
    assert result["current_runs"]==2 and result["best"]["fitness"]==12.3456789
    assert result["best"]["run_id"]==RUN
    assert result["saved_chromosome"]["baseline_eligible"] is False
    assert result["institutional_authorization"]=="NOT_ESTABLISHED"
    assert {p:p.read_bytes() for p in before}==before and random.getstate()==rng
    # A fresh reader (restart) resolves existing source identity, not a timestamp cache.
    importlib.reload(service)
    monkeypatch.setattr(service,"current_identity",identity)
    assert service.evaluation()==result


def test_empty_missing_corrupt_and_bounded_history_fail_closed(monkeypatch):
    monkeypatch.setattr(service,"current_identity",identity)
    result=service.evaluation();assert result["current_runs"]==0 and result["best"] is None
    index,snapshot=documents();store(index,snapshot)
    path=history.directory(RUN)/"generation-000000.json";path.write_text('{}')
    result=service.evaluation();assert result["current_runs"] is None and result["best"] is None
    assert result["issues"]==["ARCHIVED_RECORD_UNREADABLE"]
    store(index,snapshot);monkeypatch.setattr(service,"MAX_RUNS",0)
    result=service.evaluation();assert not result["coverage_complete"] and result["best"] is None


def test_input_drift_is_rejected_without_storage_change(monkeypatch):
    values=iter([identity(),{**identity(),"input_fingerprint":"e"*64}]);monkeypatch.setattr(service,"current_identity",lambda:next(values))
    with pytest.raises(history.HistoryError,match="changed during review"):service.evaluation()


def test_http_admin_only_and_no_query_override(monkeypatch):
    monkeypatch.setattr(service,"current_identity",identity)
    with TestClient(app) as client:
        app.dependency_overrides[current_principal]=lambda:PreferencePrincipal("faculty",faculty_id="fictional-only")
        assert client.get('/api/ga/current-evaluation').status_code==403
        def absent():raise HTTPException(401,"Authentication required")
        app.dependency_overrides[current_principal]=absent
        assert client.get('/api/ga/current-evaluation').status_code==401
        app.dependency_overrides[current_principal]=lambda:PreferencePrincipal("admin")
        response=client.get('/api/ga/current-evaluation?fitness_policy=1&compatible=true')
        assert response.status_code==200 and response.json()["current_identity"]["preference_scoring_version"]==2
        assert client.post('/api/ga/current-evaluation').status_code==405


def test_actual_engine_fingerprint_scope_is_unchanged():
    from services import ga_checkpoint_service as checkpoints, ga_v2_store
    first=(checkpoints.engine_fingerprint(),checkpoints.engine_fingerprint(1),ga_v2_store.engine_fingerprint())
    # Projection imports/calls neither rewrite nor spoof legacy fingerprint implementation.
    assert service.current_identity()["engine_fingerprint"]==first[0]
    assert first==(checkpoints.engine_fingerprint(),checkpoints.engine_fingerprint(1),ga_v2_store.engine_fingerprint())


def test_actual_fictional_v1_history_does_not_invent_academic_context(baseline, monkeypatch):
    from services import ga_service as engine
    from services.ga_control_service import RunControl
    parameters=dict(population_size=2,generations=2,fresh_chromosomes=0,mutation_attempts=1,max_restarts=5)
    configuration={**parameters,"baseline_mode":"fresh"}
    control=RunControl(configuration=configuration);control.start()
    before=random.getstate()
    try:
        random.seed(710)
        with history.capture_history(control,baseline) as recorder:
            result=engine.run_genetic_algorithm(**parameters,run_control=control,progress_callback=control.capture_progress)
            recorder.record_result(result)
            control.finish("COMPLETED")
        # An actual reader must not call the scorer or reconstruct/admit a seed.
        monkeypatch.setattr(engine,"faculty_preference_fitness",lambda *_:pytest.fail("Projection re-scored"))
        observed=service.evaluation()
        assert observed["current_runs"]==0 and observed["best"] is None
        assert observed["runs"][0]["reason"]=="ACADEMIC_CONTEXT_NOT_ESTABLISHED"
        assert result["best_fitness"] is not None
    finally:
        random.setstate(before)
