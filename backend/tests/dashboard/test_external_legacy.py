"""D6: fictional CSVs, real session checks, no institutional reads or persistence."""
import base64
import copy
import csv
import hashlib
import io
import json
import random

import pytest
from fastapi import HTTPException

from schemas.external_schedule import LegacyMetadata, ReviewRequest
from services import external_schedule_service as intake, external_schedule_review_service as review
from services.external_schedule_legacy_service import parse_schedule, HEADERS
from services.external_schedule_handoff_service import prepare
from tests.dashboard.test_my_schedule import fixture, ORIGIN
from tests.dashboard.test_external_preview import CTX, ROW, session, csv_bytes


@pytest.fixture(autouse=True)
def synthetic_context(monkeypatch):
    monkeypatch.setattr(intake, "context", lambda: copy.deepcopy(CTX))


def csv_data(schedules=None, sections=None):
    out=io.StringIO(newline=""); writer=csv.writer(out); writer.writerow(HEADERS)
    for index,value in enumerate(schedules or ["7:30AM - 9:00AM MTH"]):
        writer.writerow(["1", (sections or ["SYN-A"])[index % len(sections or ["SYN-A"])], "FICTIONAL-GEC", value])
    return out.getvalue().encode()


def legacy(raw=None, metadata=None):
    return intake.parse_file(raw or csv_data(), "fictional-legacy.csv", "legacy_gec", metadata)


def projected(source, mappings=None):
    return review.project(ReviewRequest(review_token=source.review_token, mappings=mappings or []))


@pytest.mark.parametrize("token,days", [("M",["M"]),("T",["T"]),("W",["W"]),("TH",["TH"]),("F",["F"]),("S",["S"]),("SAT",["S"]),("MTH",["M","TH"]),("TTH",["T","TH"]),("TF",["T","F"]),("MW",["M","W"])])
def test_supported_day_notation(token,days):
    actual=parse_schedule("7:30AM - 9:00AM "+token)
    assert actual[:4]==(days,"07:30","09:00","parsed")


@pytest.mark.parametrize("value,state,code", [
    ("garbage","invalid","LEGACY_INVALID_SCHEDULE"),
    ("7:30 - 9:00 M","ambiguous","LEGACY_AMBIGUOUS_SCHEDULE"),
    ("7:30AM - 9:00 M","ambiguous","LEGACY_AMBIGUOUS_SCHEDULE"),
    ("13:00AM - 2:00PM M","invalid","LEGACY_INVALID_TIME"),
    ("9:00PM - 7:30AM M","invalid","LEGACY_INVALID_INTERVAL"),
    ("9:00AM - 9:00AM M","invalid","LEGACY_INVALID_INTERVAL"),
    ("7:30AM - 9:00AM SUN","unsupported","LEGACY_UNSUPPORTED_DAY"),
    ("7:30AM - 9:00AM TTF","ambiguous","LEGACY_AMBIGUOUS_DAYS"),
    ("7:45AM - 9:00AM M","unsupported","LEGACY_UNSUPPORTED_GRID"),
    ("6:30AM - 7:30AM M","unsupported","LEGACY_UNSUPPORTED_GRID"),
    ("9:00PM - 10:30PM M","unsupported","LEGACY_UNSUPPORTED_GRID"),
    ("7:30AM - 9:00AM M; 10:00AM - 11:00AM T","invalid","LEGACY_INVALID_SCHEDULE"),
])
def test_nonparsed_rows_preserved_never_calendar_ready(value,state,code):
    source=legacy(csv_data([value]));item=source.legacy.rows[0]
    assert item.schedule==value and item.parse_state==state
    assert code in {d.code for d in item.discrepancies}
    result=projected(source);assert not result.rows[0].calendar_supported
    assert code in {d.code for d in result.rows[0].discrepancies}


def test_noon_midnight_order_and_grid_boundaries():
    assert parse_schedule("12:00PM - 1:00PM M")[1:4]==("12:00","13:00","parsed")
    assert parse_schedule("9:00PM - 10:00PM S")[1:4]==("21:00","22:00","parsed")
    assert parse_schedule("12:00AM - 1:00AM M")[1:4]==("00:00","01:00","unsupported")


@pytest.mark.parametrize("raw", [b"", b"Year Level,Section,Course Number,Wrong\n1,A,X,x\n", b"Year Level,Section,Course Number,Schedule,Extra\n", b"Year Level,Section,Section,Schedule\n", b"Year Level,Section,Course Number,Schedule\n1,A,X\n", b'Year Level,Section,Course Number,Schedule\n"unterminated', b"PK\x03\x04notcsv", b"\xff\xfe"])
def test_bad_file_structure_rejects_whole_upload(raw):
    with pytest.raises(HTTPException): intake.parse_file(raw,"fictional.csv","legacy_gec")


def test_explicit_format_canonical_regression_and_limits():
    with pytest.raises(HTTPException) as error: intake.parse_file(csv_data(),"fictional.csv")
    assert error.value.detail["code"]=="INVALID_COLUMNS"
    assert intake.parse_file(csv_bytes([ROW]),"fictional.csv").legacy is None
    for raw,name in [(csv_data(["7:30AM - 9:00AM M"]*201),"fictional.csv"),(b'x'*(intake.MAX_BYTES+1),"fictional.csv"),(b'PK',"fictional.xlsx")]:
        with pytest.raises(HTTPException):intake.parse_file(raw,name,"legacy_gec")
    for cell in ["=formula", "a"*1001, "bad\x01"]:
        with pytest.raises(HTTPException):legacy(csv_data(sections=[cell]))


def test_raw_originals_multiline_hash_metadata_and_handoff_provenance():
    raw=csv_data(["7:30AM - 9:00AM M", "9:00AM - 10:00AM M"], [" Imported\nsection "])
    metadata=LegacyMetadata(supplier="Fictional College",source_reference="Fictional letter",academic_term="Unverified example",status="tentative")
    source=legacy(raw,metadata);result=projected(source,[{"source_row":2,"sections":[{"reference_index":0,"target_id":"synthetic-section-a"}]}])
    value=prepare(ReviewRequest(review_token=source.review_token))
    assert [r.source_row for r in source.rows]==[2,4]
    assert source.source_sha256==result.source_sha256==hashlib.sha256(raw).hexdigest()
    assert result.legacy==source.legacy==value.review.legacy
    assert source.legacy.rows[0].section==" Imported\nsection "
    assert source.rows[0].input.title==source.rows[0].input.room==source.rows[0].input.instructor==""
    assert result.rows[0].sections[0].id=="synthetic-section-a"
    assert result.rows[0].room.state==result.rows[0].instructor.state=="missing_optional"
    assert "TERM_UNVERIFIED" in {d.code for d in result.rows[0].discrepancies}
    assert not value.approved and not value.activated and not value.persisted


def test_missing_metadata_never_ready_and_no_identity_from_year():
    source=legacy(csv_data(sections=["Unknown"]));result=projected(source).rows[0]
    assert result.sections[0].id is None and result.sections[0].state=="unresolved"
    assert {d.code for d in result.discrepancies}>={"REQUIRED_FIELD","TERM_UNKNOWN","LEGACY_INCOMPLETE_METADATA"}
    assert result.original.title=="" and result.status=="invalid"


def test_ambiguous_section_requires_explicit_existing_id(monkeypatch):
    ctx=copy.deepcopy(CTX);ctx["sections"].append({"id":"another-section","label":"SYN-A"})
    monkeypatch.setattr(intake,"context",lambda:ctx);source=legacy()
    assert projected(source).rows[0].sections[0].state=="ambiguous"
    mapped=projected(source,[{"source_row":2,"sections":[{"reference_index":0,"target_id":"another-section"}]}])
    assert mapped.rows[0].sections[0].id=="another-section"
    with pytest.raises(HTTPException): projected(source,[{"source_row":2,"sections":[{"reference_index":0,"target_id":"invented"}]}])


def test_duplicate_overlap_and_adjacent_intervals():
    result=projected(legacy(csv_data(["7:30AM - 9:00AM M","7:30AM - 9:00AM M","8:00AM - 9:30AM M","9:30AM - 10:00AM M"])))
    assert {d.code for d in result.rows[0].discrepancies}>={"DUPLICATE_ENTRY","SECTION_OVERLAP"}
    assert not any(d.code=="SECTION_OVERLAP" for d in result.rows[-1].discrepancies)


def test_tampered_legacy_provenance_and_changed_references_fail_closed(monkeypatch):
    source=legacy();encoded,signature=source.review_token.split('.');data=json.loads(base64.urlsafe_b64decode(encoded))
    data['legacy']['rows'][0]['schedule']='forged'
    forged=base64.urlsafe_b64encode(json.dumps(data).encode()).decode()+'.'+signature
    with pytest.raises(HTTPException) as error: review.project(ReviewRequest(review_token=forged))
    assert error.value.status_code==409
    monkeypatch.setattr(intake,"context",lambda:{**copy.deepcopy(CTX),"rooms":[]})
    with pytest.raises(HTTPException) as error:projected(source)
    assert error.value.status_code==409


def test_real_auth_role_csrf_origin_bounds_and_no_write(fixture):
    path='/api/external-schedules/preview-file?filename=fictional.csv&import_format=legacy_gec'
    body={'content_base64':base64.b64encode(csv_data()).decode(),'metadata':LegacyMetadata().model_dump()}
    assert fixture.client.post(path,json=body).status_code==401
    assert fixture.client.post(path,json=body,headers={**session(fixture,'faculty'),'X-Role':'admin'}).status_code==403
    headers=session(fixture)
    assert fixture.client.post(path,json=body,headers={'Origin':ORIGIN}).status_code==403
    assert fixture.client.post(path,json=body,headers={**headers,'Origin':'https://evil.invalid'}).status_code==403
    before={p:p.read_bytes() for p in fixture.path.parent.iterdir() if p.is_file()};rng=random.getstate()
    response=fixture.client.post(path,json=body,headers=headers)
    assert response.status_code==200 and response.headers['cache-control']=='no-store'
    source=response.json();assert source['legacy']['rows'][0]['source_row']==2
    for endpoint in ['review','handoff']:
        assert fixture.client.post('/api/external-schedules/'+endpoint,json={'review_token':source['review_token']},headers=headers).status_code==200
    assert all(p.read_bytes()==v for p,v in before.items()) and random.getstate()==rng
    for extra in [{'content_base64':'***'},{'metadata':{'status':'confirmed'}},{'rows':[]}]:
        assert fixture.client.post(path,json={**body,**extra},headers=headers).status_code==422
    assert fixture.client.post(path,content=b' '*(2*intake.MAX_BYTES+1),headers={**headers,'Content-Type':'application/json'}).status_code==413
    assert fixture.client.post(path,content=b'raw',headers={**headers,'Content-Type':'text/plain'}).status_code==415
