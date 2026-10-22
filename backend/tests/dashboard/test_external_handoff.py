"""D5: real session authorization, complete fresh validation, no durable writes."""
import base64
import copy
import hashlib
import json
import random

import pytest
from fastapi import HTTPException

from schemas.external_schedule import ExternalRow, ReviewRequest, HANDOFF_LABEL
from services import external_schedule_service as intake, external_schedule_review_service as review
from services import external_schedule_handoff_service as handoff
from tests.dashboard.test_my_schedule import fixture, ORIGIN
from tests.dashboard.test_external_preview import CTX, ROW, csv_bytes, session
from tests.dashboard.readiness_support import bind_client_preview

PATH = "/api/external-schedules/handoff"


@pytest.fixture(autouse=True)
def synthetic_context(monkeypatch):
    monkeypatch.setattr(intake, "context", lambda: copy.deepcopy(CTX))


def preview(rows=None):
    return intake.validate([ExternalRow(**row) for row in (rows or [ROW])])


def request(source, mappings=None):
    return ReviewRequest(review_token=source.review_token, mappings=mappings or [])


def test_complete_file_handoff_retains_invalid_rows_hash_and_physical_row_references():
    raw=csv_bytes([{**ROW,"notes":"Fictional first line\nSecond line"},{**ROW,"start":"bad"},ROW])
    source=intake.parse_file(raw,"fictional.csv")
    value=handoff.prepare(request(source))
    assert value.label==HANDOFF_LABEL and not value.approved and not value.persisted and not value.activated
    assert value.review.source_sha256==hashlib.sha256(raw).hexdigest()
    assert [r.source_row for r in value.review.rows]==[2,4,5]
    assert [r.original for r in value.review.rows]==[r.input for r in source.rows]
    assert value.review.rows[1].status=="invalid" and not value.review.rows[1].calendar_supported
    assert {d.code for r in value.review.rows for d in r.discrepancies}>={"DUPLICATE_ENTRY","SECTION_OVERLAP","INVALID_TIME"}
    assert value.revalidated_at.utcoffset().total_seconds()==0


def test_identity_is_complete_content_fingerprint_not_timestamp_or_secret():
    source=preview();first=handoff.prepare(request(source));second=handoff.prepare(request(source))
    expected=hashlib.sha256(json.dumps(first.review.model_dump(),sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
    assert first.preview_id==second.preview_id=="d5-"+expected
    assert first.revalidated_at<=second.revalidated_at
    assert source.review_token not in first.model_dump_json()
    assert "review_token" not in first.model_dump_json()
    changed=handoff.prepare(request(source,[{"source_row":1,"instructor_id":"synthetic-instructor-0"}]))
    assert first.preview_id!=changed.preview_id


def test_explicit_and_unresolved_resources_and_original_labels_remain_separate(monkeypatch):
    ctx=copy.deepcopy(CTX);ctx["instructors"].append({"id":"other","label":ROW["instructor"]})
    monkeypatch.setattr(intake,"context",lambda:ctx)
    source=preview([{**ROW,"sections":["Unknown"],"room":""}])
    original=source.model_dump()
    result=handoff.prepare(request(source)).review.rows[0]
    assert result.sections[0].state=="unresolved" and result.room.state=="missing_optional"
    assert result.instructor.state=="ambiguous" and len(result.instructor.candidate_ids)==2
    result=handoff.prepare(request(source,[{"source_row":1,"sections":[{"reference_index":0,"target_id":"synthetic-section-b"}]}])).review.rows[0]
    assert result.sections[0].method=="explicit" and result.sections[0].id=="synthetic-section-b"
    assert result.original.sections==["Unknown"] and source.model_dump()==original


def test_every_handoff_revalidates_and_changed_references_fail_instead_of_returning_cached_output(monkeypatch):
    calls=[];actual=handoff.project
    def counted(payload):calls.append(payload);return actual(payload)
    monkeypatch.setattr(handoff,"project",counted)
    source=preview();handoff.prepare(request(source));handoff.prepare(request(source));assert len(calls)==2
    ctx=copy.deepcopy(CTX);ctx["fixed"]=[dict(section="SYN-A",day="M",start="09:00",end="10:00")]
    monkeypatch.setattr(intake,"context",lambda:ctx)
    with pytest.raises(HTTPException) as error:handoff.prepare(request(source))
    assert error.value.status_code==409 and error.value.detail["code"]=="PREVIEW_REFERENCES_CHANGED"


@pytest.mark.parametrize("mutation", ["hash","subset","restart"])
def test_forged_and_expired_source_references_cannot_produce_handoff(mutation,monkeypatch):
    source=preview();token=source.review_token
    if mutation=="restart":monkeypatch.setattr(review,"_PROCESS_KEY",b"different-process")
    else:
        encoded,signature=token.split(".");data=json.loads(base64.urlsafe_b64decode(encoded))
        if mutation=="hash":data["source_sha256"]="a"*64
        else:data["rows"]=[]
        source.review_token=base64.urlsafe_b64encode(json.dumps(data).encode()).decode()+"."+signature
    with pytest.raises(HTTPException) as error:handoff.prepare(request(source))
    assert error.value.detail["code"]=="PREVIEW_RECEIPT_INVALID"


def test_invalid_mapping_rejects_whole_handoff():
    with pytest.raises(HTTPException) as error:
        handoff.prepare(request(preview([ROW,{**ROW,"start":"bad"}]),[{"source_row":1,"room_id":"invented"}]))
    assert error.value.detail["code"]=="INVALID_RESOURCE_MAPPING"


def test_endpoint_real_session_admin_origin_csrf_and_no_client_role_override(fixture):
    body=request(preview()).model_dump()
    assert fixture.client.post(PATH,json=body).status_code==401
    faculty=session(fixture,"faculty")
    assert fixture.client.post(PATH,json=body,headers={**faculty,"X-Role":"admin"}).status_code==403
    admin=session(fixture)
    body["review_token"]=bind_client_preview(preview(),fixture).review_token
    assert fixture.client.post(PATH,json=body,headers={"Origin":ORIGIN}).status_code==403
    assert fixture.client.post(PATH,json=body,headers={**admin,"Origin":"https://evil.invalid"}).status_code==403
    result=fixture.client.post(PATH,json=body,headers=admin)
    assert result.status_code==200 and result.headers["cache-control"]=="no-store"
    assert result.headers["x-content-type-options"]=="nosniff"
    assert result.json()["label"]==HANDOFF_LABEL and "review_token" not in result.text


@pytest.mark.parametrize("field,value", [("rows",[]),("approved",True),("projection",{}),("source_sha256","forged")])
def test_client_projection_filter_approval_and_provenance_fields_rejected(fixture,field,value):
    headers=session(fixture);body={**request(preview()).model_dump(),field:value}
    assert fixture.client.post(PATH,headers=headers,json=body).status_code==422


def test_endpoint_caps_duplicate_keys_media_type_and_stale_reference_errors(fixture,monkeypatch):
    headers={**session(fixture),"Content-Type":"application/json"};source=bind_client_preview(preview(),fixture)
    assert fixture.client.post(PATH,headers=headers,content=b" "*(2*intake.MAX_BYTES+1)).status_code==413
    assert fixture.client.post(PATH,headers={**headers,"Content-Type":"text/plain"},content=b"{}").status_code==415
    raw='{"review_token":'+json.dumps(source.review_token)+',"mappings":[],"mappings":[]}'
    assert fixture.client.post(PATH,headers=headers,content=raw).status_code==422
    monkeypatch.setattr(intake,"context",lambda:{**copy.deepcopy(CTX),"rooms":[]})
    response=fixture.client.post(PATH,headers=headers,json=request(source).model_dump())
    assert response.status_code==409 and "review" not in response.json()


def test_imported_markup_is_json_text_and_endpoint_does_not_write_or_change_rng(fixture):
    headers=session(fixture);markup='<script>window.bad=true</script><img src=x onerror="alert(1)">'
    source=bind_client_preview(preview([{**ROW,"title":markup,"notes":"Fictional caf\u00e9 \U0001f9ea\n"+markup}]),fixture)
    before={p:p.read_bytes() for p in fixture.path.parent.iterdir() if p.is_file()};rng=random.getstate()
    with fixture.engine.connect() as c:sessions=repr(c.exec_driver_sql("SELECT * FROM login_sessions").all())
    response=fixture.client.post(PATH,headers=headers,json=request(source).model_dump())
    assert response.status_code==200 and response.headers['content-type'].startswith('application/json')
    assert response.json()["review"]["rows"][0]["original"]["title"]==markup
    with fixture.engine.connect() as c:assert repr(c.exec_driver_sql("SELECT * FROM login_sessions").all())==sessions
    assert random.getstate()==rng and all(p.read_bytes()==b for p,b in before.items())
    assert set(fixture.path.parent.iterdir())==set(before)
