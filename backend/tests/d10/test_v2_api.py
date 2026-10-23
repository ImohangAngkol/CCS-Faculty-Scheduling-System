"""Real FastAPI auth/D8/D9 transactions with fictional providers and owned SQLite.

No browser is used by these ASGI tests; they are not PostgreSQL acceptance.
"""
from concurrent.futures import ThreadPoolExecutor
import copy
from dataclasses import replace
import json
import random
import threading
import time
from uuid import UUID,uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from confirmation_models import ExternalRecord,ExternalRevision,ConfirmationEvent
from services import ga_v2_service as service,ga_v2_store as store,ga_v2_constraints as constraints
from services import external_confirmation_service as ledger,external_schedule_verification_service as evidence,confirmation_authority_service as confirmer
from schemas.ga_constrained import RunRequest,Parameters
from tests.dashboard.test_external_confirmations import setup,fixture,isolate,permit,proposal,decision,session,ORIGIN
from tests.d10.support import templates,preferences
from tests.d10.test_v2_engine import catalog_for

ENDPOINT="/api/ga/v2"


@pytest.fixture
def environment(setup,monkeypatch,tmp_path):
    f=setup;permit(monkeypatch)
    values=templates(compact=True)
    catalog=catalog_for(values).model_copy(update={"sections":(("synthetic-section-a","SYN-A"),("synthetic-section-b","SYN-B")),
        "faculty":(("synthetic-instructor-0","990001"),("fictional-instructor-1","990002")),"rooms":(("SYN LEC","Fictional Lecture Room"),)})
    authority=constraints.LedgerAuthority(lambda:Session(f.engine),catalog,values)
    deployment=service.Deployment(catalog,authority,values,preferences())
    monkeypatch.setattr(service,"institutional_deployment",lambda year,term:deployment)
    monkeypatch.setattr(store,"STORE",tmp_path/"v2")
    monkeypatch.setattr(service,"JOBS",{})
    headers=session(f);body=proposal(f,headers)
    assert decision(f,headers,body).status_code==200
    f.deployment=deployment;f.headers=headers;f.proposal=body
    yield f
    # A worker must finish before temporary engines/storage/overrides disappear.
    deadline=time.monotonic()+30
    while any(job.active for job in service.JOBS.values()) and time.monotonic()<deadline:time.sleep(.01)
    assert not any(job.active for job in service.JOBS.values())


def scope(f):
    response=f.client.get(ENDPOINT+"/constraints",params={"academic_year":f.deployment.catalog.academic_year,"term":f.deployment.catalog.term},headers=f.headers)
    assert response.status_code==200,response.status_code
    return response.json()


def request_for(f):
    return {"academic_year":f.deployment.catalog.academic_year,"term":f.deployment.catalog.term,"constraint_digest":scope(f)["constraint_digest"],
        "parameters":{"population_size":2,"generations":2,"fresh_chromosomes":0,"mutation_attempts":1,"crossover_attempts":1,"max_restarts":3,"candidate_attempts":3}}


def wait(f,run_id):
    end=time.monotonic()+30
    while True:
        response=f.client.get(ENDPOINT+"/runs/"+run_id,headers=f.headers)
        assert response.status_code==200,response.status_code
        result=response.json()
        if not result["execution_active"]:return result
        assert time.monotonic()<end
        time.sleep(.01)


def test_default_provider_blocks_before_database_or_storage_access(setup,monkeypatch,tmp_path):
    headers=session(setup)
    assert service.institutional_deployment("2026-2027","Term") is None
    monkeypatch.setattr(store,"STORE",tmp_path/"not-created")
    body={"academic_year":"2026-2027","term":"Term","constraint_digest":"a"*64}
    result=setup.client.post(ENDPOINT+"/runs",headers=headers,json=body)
    assert result.status_code==503 and result.json()["detail"]["code"]=="INSTITUTIONAL_AUTHORITY_UNAVAILABLE"
    assert not store.STORE.exists()


def test_auth_role_origin_csrf_and_client_authority_flags_fail_closed(environment):
    f=environment;f.client.cookies.clear()
    assert f.client.get(ENDPOINT+"/status").status_code==401
    faculty=session(f,"faculty")
    assert f.client.get(ENDPOINT+"/status",headers=faculty).status_code==403
    f.headers=session(f);body=request_for(f)
    for headers in [{"Origin":ORIGIN},{**f.headers,"Origin":"https://evil.invalid"}]:
        assert f.client.post(ENDPOINT+"/runs",headers=headers,json=body).status_code==403
    assert f.client.post(ENDPOINT+"/runs",headers=f.headers,json={**body,"authorized":True}).status_code==422
    assert not store.STORE.exists()


def test_fresh_complete_head_provenance_and_actual_async_api_generation(environment):
    f=environment;body=request_for(f)
    rng=random.getstate()
    response=f.client.post(ENDPOINT+"/runs",headers=f.headers,json=body)
    assert response.status_code==202
    final=wait(f,response.json()["run_id"])
    assert final["status"]=="COMPLETED",final.get("error")
    result=final["result"]
    assert result["source"]=="GA-generated proposal" and not result["approved"]
    assert result["constraint_digest"]==body["constraint_digest"]
    assert result["revisions"][0]["revision_id"]==f.proposal["revision_id"]
    assert result["commitments"][0]["source_row"]==1 and len(result["schedule"])==2
    assert all(not (r["section"]=="SYN-A" and r["day"]=="M" and constraints.overlap(constraints.minutes(r["start"]),constraints.minutes(r["end"]),540,600)) for r in result["schedule"])
    assert not any("graph" in key for key in final)
    assert random.getstate()==rng


@pytest.mark.parametrize("loss",["evidence","issuer","confirmer","provider_exception"])
def test_fresh_authority_loss_rejects_without_writes(environment,monkeypatch,loss):
    f=environment
    if loss=="evidence":monkeypatch.setattr(evidence,"verification_for",lambda *a,**k:None)
    if loss=="issuer":monkeypatch.setattr(evidence,"authority_policy_for",lambda *a:None)
    if loss=="confirmer":monkeypatch.setattr(confirmer,"authorization_for",lambda *a:None)
    if loss=="provider_exception":
        def unavailable(*a,**k):raise RuntimeError("fictional provider failure")
        monkeypatch.setattr(evidence,"verification_for",unavailable)
    result=f.client.get(ENDPOINT+"/constraints",params={"academic_year":f.deployment.catalog.academic_year,"term":f.deployment.catalog.term},headers=f.headers)
    assert result.status_code==503 and not store.STORE.exists()


def test_incorrect_term_and_reviewed_digest_cannot_start(environment):
    f=environment;body=request_for(f)
    for changed in [{**body,"term":"Wrong term"},{**body,"constraint_digest":"0"*64}]:
        assert f.client.post(ENDPOINT+"/runs",headers=f.headers,json=changed).status_code==409
    assert not store.STORE.exists()


def test_revoked_record_blocks_complete_term_and_published_read(environment):
    f=environment;body=request_for(f)
    response=f.client.post(ENDPOINT+"/runs",headers=f.headers,json=body);run_id=response.json()["run_id"]
    assert wait(f,run_id)["status"]=="COMPLETED"
    before=store.path_for(run_id).read_bytes()
    revoke={"operation_id":str(uuid4()),"expected_version":1,"reason":"Fictional revocation"}
    assert f.client.post("/api/external-confirmations/records/"+f.proposal["record_id"]+"/revoke",headers=f.headers,json=revoke).status_code==200
    denied=f.client.get(ENDPOINT+"/runs/"+run_id,headers=f.headers)
    assert denied.status_code==409 and denied.json()["detail"]["code"]=="CONFIRMATION_NOT_CURRENT"
    assert store.path_for(run_id).read_bytes()==before


def test_superseded_current_head_rejects_pinned_snapshot(environment):
    f=environment
    with f.deployment.authority.pinned() as pinned:pass
    second=proposal(f,f.headers,f.proposal["record_id"],1)
    assert decision(f,f.headers,second).status_code==200
    with pytest.raises(constraints.ConstraintError) as caught:
        with f.deployment.authority.pinned(pinned):pass
    assert caught.value.code=="CONSTRAINT_SET_CHANGED"


def test_membership_change_is_not_a_paginated_or_partial_success(environment):
    f=environment
    with f.deployment.authority.pinned() as pinned:pass
    # A newly proposed applicable record is not silently ignored.
    proposal(f,f.headers)
    with pytest.raises(constraints.ConstraintError):
        with f.deployment.authority.pinned(pinned):pass


def test_concurrent_confirmations_block_during_guarded_boundary(environment):
    f=environment;entered=threading.Event();release=threading.Event();completed=threading.Event()
    second=proposal(f,f.headers,f.proposal["record_id"],1)
    def guarded():
        with f.deployment.authority.pinned():
            entered.set();assert release.wait(10)
    with ThreadPoolExecutor(max_workers=2) as pool:
        held=pool.submit(guarded);assert entered.wait(10)
        def change():
            result=decision(f,f.headers,second);completed.set();return result.status_code
        pending=pool.submit(change)
        try:
            assert not completed.wait(.1)
        finally:release.set()
        held.result();assert pending.result()==200


def test_wrong_catalog_mapping_rejects(environment):
    f=environment
    wrong=f.deployment.catalog.model_copy(update={"sections":(("unrelated","SYN-A"),("synthetic-section-b","SYN-B"))})
    authority=constraints.LedgerAuthority(lambda:Session(f.engine),wrong,f.deployment.templates)
    with pytest.raises(constraints.ConstraintError) as caught:
        with authority.pinned():pass
    assert caught.value.code=="RESOURCE_MAPPING_REQUIRED"


def test_shared_v1_lock_prevents_concurrent_start(environment):
    f=environment;body=request_for(f);lock=service.execution_lock()
    assert lock.acquire(False)
    try:
        result=f.client.post(ENDPOINT+"/runs",headers=f.headers,json=body)
        assert result.status_code==409 and result.json()["detail"]["code"]=="GA_EXECUTION_BUSY"
    finally:lock.release()


def test_pause_restart_discovery_and_real_resume_without_v1_storage(environment,monkeypatch):
    f=environment;entered=threading.Event();release=threading.Event()
    original=service.engine.run;factory=service.engine.construct;first=[True]
    def held(values,restarts):
        if first[0]:
            first[0]=False;entered.set();assert release.wait(10)
        return factory(values,restarts)
    def run(*args,**kwargs):return original(*args,**kwargs,factory=held)
    monkeypatch.setattr(service.engine,"run",run)
    reply=f.client.post(ENDPOINT+"/runs",headers=f.headers,json=request_for(f));run_id=reply.json()["run_id"]
    try:
        assert entered.wait(10)
        assert f.client.post(ENDPOINT+"/runs/"+run_id+"/control",headers=f.headers,json={"action":"pause"}).status_code==200
    finally:release.set()
    assert wait(f,run_id)["status"]=="PAUSED"
    before=store.path_for(run_id).read_bytes()
    service.JOBS.clear()  # No in-memory population/control record is used to resume.
    response=f.client.post(ENDPOINT+"/runs/"+run_id+"/control",headers=f.headers,json={"action":"resume"})
    assert response.status_code==200
    final=wait(f,run_id);assert final["status"]=="COMPLETED",final.get("error")
    assert store.path_for(run_id).read_bytes()!=before


def test_invalid_explicit_seed_has_no_fresh_fallback(environment,monkeypatch):
    f=environment;body={**request_for(f),"seed":"saved"}
    monkeypatch.setattr(service,"load_saved_best_payload",lambda:None)
    response=f.client.post(ENDPOINT+"/runs",headers=f.headers,json=body)
    assert response.status_code==503 and response.json()["detail"]["code"]=="REQUESTED_SEED_UNAVAILABLE"
    assert not store.STORE.exists()


def test_applicable_faculty_and_room_ids_come_from_confirmed_resource_mappings(environment):
    from tests.dashboard.test_external_preview import ROW
    from tests.dashboard.test_external_readiness import metadata
    f=environment
    preview=f.client.post("/api/external-schedules/preview",headers=f.headers,json={"rows":[{**ROW,"sections":["SYN-B"],"days":["M"]}]}).json()
    meta=metadata();meta["rows"][0].update(room_applicability="applicable",instructor_applicability="applicable")
    review={"review_token":preview["review_token"],"metadata":meta,"mappings":[{"source_row":1,"sections":[],"room_id":"SYN LEC","instructor_id":"synthetic-instructor-0"}]}
    assessed=f.client.post("/api/external-schedules/readiness",headers=f.headers,json=review).json()
    assert assessed["status"]=="READY",[item["code"] for item in assessed["findings"] if item["severity"]=="blocker"]
    review["assessment_receipt"]=assessed["assessment_receipt"]
    body={"record_id":str(uuid4()),"revision_id":str(uuid4()),"expected_version":0,"reason":"Fictional applicable resources","review":review}
    assert f.client.post("/api/external-confirmations/revisions",headers=f.headers,json=body).status_code==200
    assert decision(f,f.headers,body).status_code==200
    with f.deployment.authority.pinned() as snapshot:
        assert len(snapshot.heads)==2
        mapped=next(c for c in snapshot.commitments if c.record_id==body["record_id"])
        assert mapped.faculty=="synthetic-instructor-0" and mapped.room=="SYN LEC" and mapped.sections==("synthetic-section-b",)
    response=f.client.post(ENDPOINT+"/runs",headers=f.headers,json=request_for(f))
    assert response.status_code==202
    final=wait(f,response.json()["run_id"])
    assert final["status"]=="COMPLETED",final.get("error")
    assert len(final["result"]["revisions"])==2
    assert all(not (row["day"]=="M" and constraints.overlap(constraints.minutes(row["start"]),constraints.minutes(row["end"]),540,600)) for row in final["result"]["schedule"])


def test_corrupt_durable_revision_fails_without_exporting_content(environment):
    from sqlalchemy import update
    f=environment
    # Deliberately corrupt ONLY this newly owned SQLite fixture, never application
    # data or retained ledgers. Production guard implementation is untouched.
    with f.engine.begin() as db:
        db.exec_driver_sql("DROP TRIGGER gec_revisions_update")
        db.execute(update(ExternalRevision).where(ExternalRevision.id==UUID(f.proposal["revision_id"])).values(content_digest="0"*64))
    response=f.client.get(ENDPOINT+"/constraints",headers=f.headers,params={"academic_year":f.deployment.catalog.academic_year,"term":f.deployment.catalog.term})
    assert response.status_code==503 and "content_json" not in response.text and not store.STORE.exists()
