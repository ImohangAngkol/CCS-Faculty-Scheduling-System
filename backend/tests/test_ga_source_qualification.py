"""U5C fictional projections/cache observations only. No database or GA execution."""
import copy
from datetime import datetime, timezone
import json
import random
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pandas as pd
from pydantic import ValidationError
import pytest
from sqlalchemy.engine import Engine

from main import app
from services import ga_source_qualification as source, ga_academic_context as academic
from services import ga_evaluation_v2 as projection, ga_result_compatibility as legacy
from services.preference_authorization import current_principal, PreferencePrincipal
from tests.test_ga_academic_context import context
from tests.test_ga_result_compatibility import identity

NOW = datetime(2026, 11, 4, tzinfo=timezone.utc)


def model(**changes):
    return source.ModelProjection(context=context(), engine_fingerprint="a"*64,
        scoring_policy="preference-policy-2", configuration_fingerprint="b"*64,
        components={key:"c"*64 for key in source.COMPONENTS}, **changes)


def declaration(expected=None, **changes):
    expected = expected or model()
    values = dict(context=expected.context, origin="FICTIONAL_FIXTURE", owner_reference="fictional-steward",
        effective_from="2026-01-01T00:00:00+00:00", effective_until="2027-01-01T00:00:00+00:00",
        manifest_sha256=expected.digest)
    return source.SourceDeclaration(**{**values, **changes})


@pytest.fixture(autouse=True)
def isolation(monkeypatch, tmp_path):
    from services import ga_history_service as history, ga_run_provenance as provenance
    monkeypatch.setattr(Engine, "connect", lambda *_a, **_k: pytest.fail("U5C attempted database access"))
    monkeypatch.setattr(history, "SNAPSHOTS_DIR", tmp_path/"history")
    monkeypatch.setattr(provenance, "PROVENANCE_DIR", tmp_path/"provenance")
    before = dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear(); app.dependency_overrides.update(before)


def test_matching_complete_projection_is_technical_only_and_deterministic():
    expected=model(); before=copy.deepcopy(expected.model_dump()); rng=random.getstate()
    result=source.compare_projection(declaration(expected), expected, expected, now=NOW)
    assert result["technical_projection"]=="MATCH" and result["changed_components"]==[]
    assert result["eligible_for_current"] is False
    assert "FICTIONAL_FIXTURE" in result["reasons"]
    assert source.ModelProjection.model_validate(dict(reversed(list(before.items())))).digest==expected.digest
    assert expected.model_dump()==before and random.getstate()==rng


@pytest.mark.parametrize("field,value",[("dataset_id","fictional-other"),("dataset_revision","fictional-revision.2"),
    ("term","FICTIONAL-OTHER-TERM"),("term_id","00000000-0000-4000-8000-000000000799"),
    ("department","Fictional Other Department"),("scope_id","00000000-0000-4000-8000-000000000798"),
    ("academic_year","FICTIONAL-OTHER-YEAR"),("input_fingerprint","f"*64)])
def test_context_or_source_drift_fails_closed(field,value):
    expected=model(); loaded=expected.model_copy(update={"context":context().model_copy(update={field:value})})
    result=source.compare_projection(declaration(),expected,loaded,now=NOW)
    assert result["technical_projection"]=="MISMATCH" and "ACADEMIC_CONTEXT_MISMATCH" in result["reasons"]
    assert result["eligible_for_current"] is False


@pytest.mark.parametrize("component",sorted(source.COMPONENTS))
def test_each_semantic_component_drift_including_preferences_offerings_and_configuration(component):
    expected=model(); loaded=expected.model_copy(update={"components":{**expected.components,component:"d"*64}})
    result=source.compare_projection(declaration(),expected,loaded,now=NOW)
    assert result["technical_projection"]=="MISMATCH" and result["changed_components"]==[component]
    assert not result["eligible_for_current"]


@pytest.mark.parametrize("field",["engine_fingerprint","configuration_fingerprint"])
def test_execution_identity_drift(field):
    expected=model(); loaded=expected.model_copy(update={field:"d"*64})
    assert source.compare_projection(declaration(),expected,loaded,now=NOW)["technical_projection"]=="MISMATCH"


@pytest.mark.parametrize("case",["missing","dict","bad_hash","missing_component","extra_component","wrong_policy","naive_time","expired","future","manifest"])
def test_missing_malformed_expired_and_unverifiable_metadata_cannot_qualify(case):
    expected=model(); supplied=declaration(); loaded=expected
    if case=="missing":supplied=None
    elif case=="dict":supplied=supplied.model_dump()
    elif case=="bad_hash":supplied=supplied.model_copy(update={"manifest_sha256":"invalid"})
    elif case=="missing_component":loaded=expected.model_copy(update={"components":{}})
    elif case=="extra_component":loaded=expected.model_copy(update={"components":{**expected.components,"unknown":"c"*64}})
    elif case=="wrong_policy":loaded=expected.model_copy(update={"scoring_policy":"other"})
    elif case=="naive_time":supplied=supplied.model_copy(update={"effective_until":"2027-01-01"})
    elif case=="expired":supplied=supplied.model_copy(update={"effective_until":"2026-01-02T00:00:00+00:00"})
    elif case=="future":supplied=supplied.model_copy(update={"effective_from":"2026-12-01T00:00:00+00:00"})
    else:supplied=supplied.model_copy(update={"manifest_sha256":"e"*64})
    result=source.compare_projection(supplied,expected,loaded,now=NOW)
    assert result["technical_projection"]!="MATCH" and result["eligible_for_current"] is False


def test_approval_claims_and_historical_metadata_are_not_authority():
    for origin in ("INSTITUTIONAL_DECLARATION","UNVERIFIED_HISTORY"):
        result=source.compare_projection(declaration(origin=origin,authority_reference="fictional-claimed-authority",
            approval_reference="fictional-claimed-approval",approval_status="CLAIMED_APPROVED"),model(),model(),now=NOW)
        assert result["technical_projection"]=="MATCH" and not result["eligible_for_current"]
        assert "INSTITUTIONAL_AUTHORITY_NOT_CONNECTED" in result["reasons"]


def test_metadata_rejects_unknown_client_authority_fields_and_is_frozen():
    with pytest.raises(ValidationError):source.SourceDeclaration.model_validate({**declaration().model_dump(),"client_approved":True})
    with pytest.raises(ValidationError):declaration().owner_reference="other"


def test_table_comparison_detects_stale_cache_without_changing_objects(tmp_path):
    path=tmp_path/"fictional.csv"; path.write_text("subject,units\nFIC-A,2\n",encoding="utf-8")
    cached=pd.read_csv(path); before=cached.copy(deep=True)
    assert source.inspect_table(path,cached)["status"]=="MATCH"
    path.write_text("subject,units\nFIC-B,2\n",encoding="utf-8")
    result=source.inspect_table(path,cached)
    assert result["status"]=="STALE_OR_DIFFERENT_CACHE" and cached.equals(before)
    assert "FIC-" not in json.dumps(result) and str(tmp_path) not in json.dumps(result)


@pytest.mark.parametrize("raw",["subject,subject\nFIC-A,FIC-B\n","subject,units\nFIC-A,2,3,4\nFIC-B,1\n"])
def test_ambiguous_or_malformed_tables_fail_closed(tmp_path,raw):
    path=tmp_path/"fictional.csv";path.write_text(raw,encoding="utf-8")
    assert source.inspect_table(path,pd.DataFrame())["status"]=="UNVERIFIABLE"


def test_cell_representation_retains_numeric_precision_type_and_order():
    frame=pd.DataFrame({"fictional":[1.0000000000000002,float("nan")]})
    changed=frame.copy();changed.iloc[0,0]=1.0
    assert source.table_digest(frame)!=source.table_digest(changed)
    assert source.table_digest(frame)!=source.table_digest(frame.iloc[::-1])
    assert source.table_digest(pd.DataFrame({"fictional":[1]}))!=source.table_digest(pd.DataFrame({"fictional":["1"]}))


def fictional_status(monkeypatch,tmp_path):
    from services import ga_progress_service
    monkeypatch.setattr(source,"ROOT",tmp_path)
    monkeypatch.setattr(source,"TABLES",(("offerings_source","fictional.csv","fictional_frame"),))
    (tmp_path/"data").mkdir(exist_ok=True)
    path=tmp_path/"data/fictional.csv";path.write_text("code,units\nFIC-A,2\n",encoding="utf-8")
    monkeypatch.setitem(source.sys.modules,"genetic_algorithm.utils.Functions",SimpleNamespace(fictional_frame=pd.read_csv(path)))
    monkeypatch.setattr(ga_progress_service,"input_fingerprint",lambda:"c"*64)


def test_status_reports_only_digests_and_codes_no_rows_paths_or_authority(monkeypatch,tmp_path):
    fictional_status(monkeypatch,tmp_path);rng=random.getstate();before=(tmp_path/"data/fictional.csv").read_bytes()
    result=source.status();raw=json.dumps(result)
    assert result["qualification"]=="BLOCKED" and not result["eligible_for_current"]
    assert result["cached_tables"][0]["status"]=="MATCH" and result["source_metadata"] is None
    assert "FIC-A" not in raw and str(tmp_path) not in raw
    assert random.getstate()==rng and (tmp_path/"data/fictional.csv").read_bytes()==before


def test_file_set_drift_is_reported_not_qualified(monkeypatch,tmp_path):
    from services import ga_progress_service
    fictional_status(monkeypatch,tmp_path);values=iter(["c"*64,"d"*64])
    monkeypatch.setattr(ga_progress_service,"input_fingerprint",lambda:next(values))
    result=source.status()
    assert not result["file_set_stable_during_inspection"] and "SOURCE_SET_UNSTABLE_OR_UNREADABLE" in result["reasons"]
    assert not result["eligible_for_current"]


def test_unconfigured_context_stays_unknown_even_with_matching_projection(monkeypatch):
    monkeypatch.setattr(legacy,"current_identity",identity)
    assert academic.verification_for(identity()) is None
    assert not source.compare_projection(declaration(),model(),model(),now=NOW)["eligible_for_current"]
    result=projection.evaluation()
    assert result["current_runs"]==0 and result["best"] is None
    assert result["current_identity"]["context_verification"]=="UNAVAILABLE"


def test_admin_read_only_endpoint_rejects_unauthorized_access_and_client_overrides(monkeypatch,tmp_path):
    fictional_status(monkeypatch,tmp_path)
    with TestClient(app) as client:
        def absent():raise HTTPException(401,"Fictional missing session")
        app.dependency_overrides[current_principal]=absent
        assert client.get('/api/ga/source-qualification').status_code==401
        for role in ("faculty","chair"):
            app.dependency_overrides[current_principal]=lambda role=role:PreferencePrincipal(role)
            assert client.get('/api/ga/source-qualification').status_code==403
        app.dependency_overrides[current_principal]=lambda:PreferencePrincipal("admin")
        value=client.get('/api/ga/source-qualification?approved=true&term=UNTRUSTED&dataset_id=UNTRUSTED').json()
        assert value["source_metadata"] is None and not value["eligible_for_current"]
        assert client.post('/api/ga/source-qualification',json={"approved":True}).status_code==405
