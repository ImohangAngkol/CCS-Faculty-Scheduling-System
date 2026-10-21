"""D4: signed preview provenance, real-session authorization and canonical review."""
import base64
import copy
import hashlib
import json
import random

import pytest
from fastapi import HTTPException

from tests.dashboard.test_my_schedule import fixture, ORIGIN
from tests.dashboard.test_external_preview import ROW, CTX, csv_bytes, session
from services import external_schedule_service as intake, external_schedule_review_service as review
from schemas.external_schedule import ExternalRow, ReviewRequest


@pytest.fixture(autouse=True)
def synthetic_context(monkeypatch):
    monkeypatch.setattr(intake, "context", lambda: copy.deepcopy(CTX))


def source(rows=None):
    return intake.validate([ExternalRow(**r) for r in (rows or [ROW])])


def project(preview, mappings=None):
    return review.project(ReviewRequest(review_token=preview.review_token, mappings=mappings or []))


def codes(row):
    return {d.code for d in row.discrepancies}


def test_receipt_and_reconciliation_preserve_file_hash_source_lines_originals():
    raw=csv_bytes([{**ROW,"notes":"Fictional first line\nFictional second line"},{**ROW,"days":["T"]}])
    preview=intake.parse_file(raw,"fictional.csv")
    result=project(preview,[{"source_row":4,"sections":[{"reference_index":0,"target_id":"synthetic-section-b"}]}])
    assert result.source_sha256==hashlib.sha256(raw).hexdigest() and result.source_name=="fictional.csv"
    assert [row.source_row for row in result.rows]==[2,4]
    assert [row.original for row in result.rows]==[row.input for row in preview.rows]
    assert result.rows[1].sections[0].id=="synthetic-section-b"
    assert result.preview_only and not result.persisted and not result.activated


@pytest.mark.parametrize("field,value", [("source_sha256","f"*64),("source_name","different.csv"),("rows",[])])
def test_tampered_receipt_cannot_replace_provenance(field,value):
    token=source().review_token; encoded,signature=token.split(".")
    data=json.loads(base64.urlsafe_b64decode(encoded));data[field]=value
    forged=base64.urlsafe_b64encode(json.dumps(data).encode()).decode()+"."+signature
    with pytest.raises(HTTPException) as error:
        review.project(ReviewRequest(review_token=forged))
    assert error.value.status_code==409 and error.value.detail["code"]=="PREVIEW_RECEIPT_INVALID"


def test_process_restart_invalidates_old_receipt(monkeypatch):
    preview=source();monkeypatch.setattr(review,"_PROCESS_KEY",b"other-process")
    with pytest.raises(HTTPException) as error:project(preview)
    assert error.value.status_code==409


def test_changed_reference_inventory_rejects_stale_mapping(monkeypatch):
    preview=source();ctx=copy.deepcopy(CTX);ctx["rooms"].append({"id":"new","label":"New"})
    monkeypatch.setattr(intake,"context",lambda:ctx)
    with pytest.raises(HTTPException) as error:project(preview)
    assert error.value.detail["code"]=="PREVIEW_REFERENCES_CHANGED"


def test_receipt_deterministic_and_reference_order_does_not_make_false_staleness(monkeypatch):
    first=source();second=source();assert first.review_token==second.review_token
    ctx=copy.deepcopy(CTX);ctx["sections"].reverse();monkeypatch.setattr(intake,"context",lambda:ctx)
    assert project(first).rows[0].sections[0].id=="synthetic-section-a"


def test_unique_instructor_name_requires_explicit_selection_not_a_generated_uuid():
    result=project(source()).rows[0]
    assert result.instructor.state=="unresolved" and result.instructor.id is None
    assert result.instructor.candidate_ids==["synthetic-instructor-0"]
    explicit=project(source(),[{"source_row":1,"instructor_id":"synthetic-instructor-0"}]).rows[0]
    assert explicit.instructor.id=="synthetic-instructor-0" and explicit.instructor.method=="explicit"
    assert explicit.original.instructor==ROW["instructor"]


def test_registered_instructor_alias_and_canonical_ids_resolve():
    for value in ["Synthetic Faculty 0","synthetic-instructor-0"]:
        match=project(source([{**ROW,"instructor":value}])).rows[0].instructor
        assert match.state=="resolved" and match.method=="recognized"


def test_ambiguous_name_stays_ambiguous_until_explicit_selection(monkeypatch):
    ctx=copy.deepcopy(CTX);ctx["instructors"].append({"id":"other-instructor","label":ROW["instructor"]})
    monkeypatch.setattr(intake,"context",lambda:ctx);preview=source()
    value=project(preview).rows[0].instructor
    assert value.state=="ambiguous" and value.id is None
    assert set(value.candidate_ids)=={"other-instructor","synthetic-instructor-0"}
    assert project(preview,[{"source_row":1,"instructor_id":"other-instructor"}]).rows[0].instructor.id=="other-instructor"


def test_ambiguous_section_alias_is_not_first_match(monkeypatch):
    ctx=copy.deepcopy(CTX);ctx["sections"][1]["label"]="SYN-A"
    monkeypatch.setattr(intake,"context",lambda:ctx);preview=source()
    assert project(preview).rows[0].sections[0].state=="ambiguous"
    assert project(preview,[{"source_row":1,"sections":[{"reference_index":0,"target_id":"synthetic-section-b"}]}]).rows[0].sections[0].id=="synthetic-section-b"


def test_missing_optional_and_unsupported_resource_are_distinct(monkeypatch):
    ctx=copy.deepcopy(CTX);ctx["rooms"]=[];monkeypatch.setattr(intake,"context",lambda:ctx)
    rows=project(source([{**ROW,"room":"","instructor":""},{**ROW,"room":"Unknown","instructor":""}])).rows
    assert rows[0].room.state=="missing_optional" and rows[0].instructor.state=="missing_optional"
    assert rows[1].room.state=="unsupported" and rows[1].room.id is None


def test_explicit_section_and_optional_room_mapping_only_uses_existing_ids():
    preview=source([{**ROW,"sections":["Imported unknown"],"room":""}])
    original=preview.model_dump()
    mapped=project(preview,[{"source_row":1,"sections":[{"reference_index":0,"target_id":"synthetic-section-b"}],"room_id":"SYN LEC"}]).rows[0]
    assert mapped.sections[0].id=="synthetic-section-b" and mapped.room.id=="SYN LEC"
    assert mapped.original.sections==["Imported unknown"] and mapped.original.room==""
    assert preview.model_dump()==original
    assert project(preview).rows[0].sections[0].state=="unresolved"


@pytest.mark.parametrize("mapping,code", [
    ({"source_row":2},"INVALID_ROW_MAPPING"),
    ({"source_row":1,"room_id":"invented"},"INVALID_RESOURCE_MAPPING"),
    ({"source_row":1,"instructor_id":"invented"},"INVALID_RESOURCE_MAPPING"),
    ({"source_row":1,"sections":[{"reference_index":0,"target_id":"invented"}]},"INVALID_RESOURCE_MAPPING"),
    ({"source_row":1,"sections":[{"reference_index":1,"target_id":"synthetic-section-a"}]},"INVALID_SECTION_MAPPING"),
    ({"source_row":1,"sections":[{"reference_index":0,"target_id":"synthetic-section-a"},{"reference_index":0,"target_id":"synthetic-section-b"}]},"INVALID_SECTION_MAPPING"),
])
def test_invalid_mappings_reject_entire_request(mapping,code):
    with pytest.raises(HTTPException) as error:project(source(),[mapping])
    assert error.value.status_code==422 and error.value.detail["code"]==code


def test_duplicate_mapping_rows_rejected():
    with pytest.raises(HTTPException) as error:project(source(),[{"source_row":1},{"source_row":1}])
    assert error.value.detail["code"]=="INVALID_ROW_MAPPING"


def test_canonical_ids_detect_section_room_and_instructor_overlap_across_different_labels():
    preview=source([ROW,{**ROW,"subject_code":"SYN-OTHER","sections":["Imported unknown"],"instructor":"Another unknown"}])
    result=project(preview,[{"source_row":1,"instructor_id":"synthetic-instructor-0"},
                           {"source_row":2,"sections":[{"reference_index":0,"target_id":"synthetic-section-a"}],"instructor_id":"synthetic-instructor-0"}])
    for row in result.rows:
        assert {"SECTION_OVERLAP","ROOM_OVERLAP","INSTRUCTOR_OVERLAP"}<=codes(row)
        assert row.status=="invalid" and row.calendar_supported


def test_adjacent_intervals_keep_original_rows_and_do_not_overlap():
    result=project(source([ROW,{**ROW,"start":"10:00","end":"11:00"}]))
    assert len(result.rows)==2 and all(not any("OVERLAP" in c for c in codes(row)) for row in result.rows)


def test_explicit_distinct_sections_do_not_inherit_false_raw_label_conflicts(monkeypatch):
    ctx=copy.deepcopy(CTX);ctx["sections"][1]["label"]="SYN-A";monkeypatch.setattr(intake,"context",lambda:ctx)
    preview=source([{**ROW,"room":"","instructor":""},{**ROW,"subject_code":"OTHER","room":"","instructor":""}])
    result=project(preview,[{"source_row":1,"sections":[{"reference_index":0,"target_id":"synthetic-section-a"}]},
                           {"source_row":2,"sections":[{"reference_index":0,"target_id":"synthetic-section-b"}]}])
    assert all("SECTION_OVERLAP" not in codes(row) for row in result.rows)


def test_unresolved_text_conflict_is_possible_not_a_fabricated_identity():
    result=project(source([{**ROW,"sections":["Unknown"]},{**ROW,"subject_code":"OTHER","sections":["Unknown"]}]))
    for row in result.rows:
        assert "POSSIBLE_UNRESOLVED_SECTION_OVERLAP" in codes(row) and "SECTION_OVERLAP" not in codes(row)
        assert row.sections[0].id is None


@pytest.mark.parametrize("change,supported", [({"start":"bad"},False),({"end":"08:00"},False),({"days":["SU"]},False),({"start":"09:10"},True)])
def test_invalid_patterns_not_plotted_and_off_grid_times_preserved(change,supported):
    result=project(source([{**ROW,**change}])).rows[0]
    assert result.calendar_supported is supported
    if supported:assert result.original.start=="09:10" and "UNSUPPORTED_TIME_GRID" in codes(result)


def test_mapped_section_comparison_preserves_fixed_input_intervals(monkeypatch):
    ctx=copy.deepcopy(CTX);ctx["fixed"]=[dict(section="SYN-B",day="M",start="09:30",end="10:30")]
    monkeypatch.setattr(intake,"context",lambda:ctx);before=copy.deepcopy(ctx)
    row=project(source(),[{"source_row":1,"sections":[{"reference_index":0,"target_id":"synthetic-section-b"}]}]).rows[0]
    assert "EXISTING_FIXED_SECTION_OVERLAP" in codes(row) and ctx==before


def test_real_auth_origin_csrf_role_and_client_field_denial(fixture):
    token=source().review_token;body={"review_token":token,"mappings":[]};path="/api/external-schedules/review"
    assert fixture.client.post(path,json=body).status_code==401
    faculty=session(fixture,"faculty")
    assert fixture.client.post(path,json=body,headers={**faculty,"X-Role":"admin"}).status_code==403
    admin=session(fixture)
    assert fixture.client.post(path,json=body,headers={"Origin":ORIGIN}).status_code==403
    assert fixture.client.post(path,json=body,headers={**admin,"Origin":"https://evil.invalid"}).status_code==403
    assert fixture.client.post(path,json={**body,"source_sha256":"forged"},headers=admin).status_code==422
    response=fixture.client.post(path,json=body,headers=admin)
    assert response.status_code==200 and response.headers["cache-control"]=="no-store"
    assert "review_token" not in response.json()


def test_review_read_preserves_storage_sessions_and_rng(fixture):
    headers=session(fixture);preview=source();before={p:p.read_bytes() for p in fixture.path.parent.iterdir() if p.is_file()}
    with fixture.engine.connect() as db:rows=repr(db.exec_driver_sql("SELECT * FROM login_sessions").all())
    rng=random.getstate()
    for _ in range(2):
        assert fixture.client.post("/api/external-schedules/review",headers=headers,json={"review_token":preview.review_token,"mappings":[]}).status_code==200
    with fixture.engine.connect() as db:assert repr(db.exec_driver_sql("SELECT * FROM login_sessions").all())==rows
    assert random.getstate()==rng and all(p.read_bytes()==value for p,value in before.items())
    assert set(fixture.path.parent.iterdir())==set(before)


def test_review_request_byte_limits_and_duplicate_json_are_atomic(fixture):
    headers={**session(fixture),"Content-Type":"application/json"}
    path="/api/external-schedules/review"
    assert fixture.client.post(path,headers=headers,content=b" "*(2*intake.MAX_BYTES+1)).status_code==413
    token=json.dumps(source().review_token)
    raw='{"review_token":'+token+',"mappings":[],"mappings":[]}'
    assert fixture.client.post(path,headers=headers,content=raw).status_code==422
