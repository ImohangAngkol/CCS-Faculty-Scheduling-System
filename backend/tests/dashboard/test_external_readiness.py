"""D7 policy and actual API security. Fictional verification is explicitly injected."""
import base64
import copy
import random
import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from schemas.external_schedule import ExternalRow, ReviewRequest
from schemas.external_readiness import AssessmentRequest, CompletionMetadata, AssessedHandoffRequest
from services import external_schedule_service as intake, external_schedule_review_service as review
from services import external_schedule_readiness_service as ready, external_schedule_preview_lifecycle as life
from services import external_schedule_verification_service as authority
from tests.dashboard.test_my_schedule import fixture, ORIGIN
from tests.dashboard.test_external_preview import ROW, CTX, session, csv_bytes, xlsx_bytes
from tests.dashboard.test_external_legacy import csv_data
from tests.dashboard.readiness_support import bind_client_preview
from identity_models import User


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    monkeypatch.setattr(intake,"context",lambda:copy.deepcopy(CTX))
    monkeypatch.setattr(life,"_heads",life.OrderedDict())


def metadata(lines=(1,)):
    return dict(supplier=ROW['supplier'],source_reference=ROW['source_reference'],source_revision='Fictional revision 1',evidence_reference='Fictional source evidence',academic_year='2026-2027',term='Fictional first term',effective_start='2026-08-03',effective_end='2026-12-18',timezone='Asia/Manila',recurrence='weekly',exceptions='none_reported',exception_notes='',rows=[dict(source_row=line,title='Fictional Seminar',component='external_meeting',section_ids=[],shared='single_section',room_applicability='not_applicable',instructor_applicability='not_applicable',evidence_reference='Fictional row evidence',proposed_meeting=None) for line in lines])


def source(rows=None):
    return intake.validate([ExternalRow(**r) for r in (rows or [{**ROW,'room':'','instructor':''}])])


def payload(preview=None, meta=None, mappings=None):
    preview=preview or source()
    return AssessmentRequest(review_token=preview.review_token,mappings=mappings or [],metadata=meta or metadata([r.source_row for r in preview.rows]))


def evaluate(preview=None,meta=None,mappings=None):
    return ready.evaluate(payload(preview,meta,mappings))[1]


def trusted(monkeypatch):
    from tests.dashboard.evidence_support import install_fictional
    install_fictional(monkeypatch)


def codes(result):return {f.code for f in result.findings if f.severity=='blocker'}


def test_complete_but_administrator_provided_is_blocked_without_trusted_provider():
    result=evaluate()
    assert result.status=='BLOCKED' and 'AUTHORITATIVE_VERIFICATION_REQUIRED' in codes(result)
    assert result.metadata_origin=='administrator_provided' and result.verification_status=='unavailable'
    assert not result.approved and not result.activated and not result.persisted


def test_fully_fictional_verified_example_ready_is_not_approval(monkeypatch):
    trusted(monkeypatch);first=evaluate();second=evaluate()
    assert first.status=='READY' and first.blocker_count==0 and first.assessment_fingerprint==second.assessment_fingerprint
    assert first.verification_status=='verified_for_readiness' and not first.approved and not first.activated


@pytest.mark.parametrize('field,value,code',[
 ('source_reference','','MISSING_SOURCE_REFERENCE'),('evidence_reference','','MISSING_EVIDENCE_REFERENCE'),('term','','MISSING_TERM'),('academic_year','','MISSING_ACADEMIC_YEAR'),('academic_year','2026-2029','INVALID_ACADEMIC_YEAR'),('effective_start','','INVALID_EFFECTIVE_DATES'),('effective_end','2026-01-01','INVALID_EFFECTIVE_DATES'),('effective_end','2028-01-01','INVALID_EFFECTIVE_DATES'),('timezone','','MISSING_TIMEZONE'),('timezone','UTC','UNSUPPORTED_TIMEZONE'),('recurrence','unknown','RECURRENCE_UNRESOLVED'),('recurrence','unsupported','RECURRENCE_UNRESOLVED'),('exceptions','unknown','CALENDAR_EXCEPTIONS_UNRESOLVED'),('exceptions','listed_unsupported','CALENDAR_EXCEPTIONS_UNRESOLVED'),('exception_notes','Fictional holiday exception','CALENDAR_EXCEPTIONS_UNRESOLVED')])
def test_missing_unsupported_or_inconsistent_global_metadata_blocks(monkeypatch,field,value,code):
    trusted(monkeypatch);meta=metadata();meta[field]=value
    assert code in codes(evaluate(meta=meta))


@pytest.mark.parametrize('change,code', [({'start':'11:00','end':'10:00'},'INVALID_TIME'),({'days':['T','T','F']},'INVALID_DAY'),({'start':'09:15'},'UNSUPPORTED_TIME_GRID'),({'sections':['Unknown']},'SECTION_UNRESOLVED'),({'sections':[]},'SECTION_UNRESOLVED')])
def test_meeting_and_section_errors_block(monkeypatch,change,code):
    trusted(monkeypatch);assert code in codes(evaluate(source([{**ROW,'room':'','instructor':'',**change}])))


@pytest.mark.parametrize('field,value,code',[('component','unknown','COMPONENT_UNRESOLVED'),('shared','unknown','SHARING_UNRESOLVED'),('room_applicability','unknown','RESOURCE_APPLICABILITY_UNKNOWN'),('instructor_applicability','applicable','APPLICABLE_RESOURCE_UNRESOLVED'),('evidence_reference','','ROW_EVIDENCE_MISSING')])
def test_row_metadata_and_unknown_applicability_never_mean_absent(monkeypatch,field,value,code):
    trusted(monkeypatch);meta=metadata();meta['rows'][0][field]=value;assert code in codes(evaluate(meta=meta))


def test_not_applicable_cannot_override_a_supplied_resource(monkeypatch):
    trusted(monkeypatch);assert 'RESOURCE_APPLICABILITY_CONTRADICTION' in codes(evaluate(source([{**ROW,'instructor':''}])))


def test_applicable_resources_require_recognized_ids(monkeypatch):
    trusted(monkeypatch);meta=metadata();meta['rows'][0].update(room_applicability='applicable',instructor_applicability='applicable')
    result=evaluate(source(),meta,[{'source_row':1,'room_id':'SYN LEC','instructor_id':'synthetic-instructor-0'}])
    assert result.status=='READY'
    with pytest.raises(HTTPException):evaluate(source(),meta,[{'source_row':1,'room_id':'invented'}])


def test_duplicate_overlap_adjacent_and_shared_sections(monkeypatch):
    trusted(monkeypatch);preview=source([{**ROW,'room':'','instructor':''}]*2)
    assert {'DUPLICATE_ENTRY','SECTION_OVERLAP'}<=codes(evaluate(preview))
    preview=source([{**ROW,'room':'','instructor':''},{**ROW,'room':'','instructor':'','start':'10:00','end':'11:00','subject_code':'SYN-OTHER'}])
    assert evaluate(preview).status=='READY'
    meta=metadata();meta['rows'][0]['section_ids']=['synthetic-section-a','synthetic-section-b']
    assert 'SHARING_UNRESOLVED' in codes(evaluate(meta=meta))
    meta['rows'][0]['shared']='shared';assert evaluate(meta=meta).status=='READY'


def test_global_contradictions_and_date_applicability(monkeypatch):
    trusted(monkeypatch);meta=metadata();meta['supplier']='Different fictional supplier'
    assert 'SOURCE_METADATA_CONTRADICTION' in codes(evaluate(meta=meta))
    meta=metadata();meta.update(effective_start='2026-08-04',effective_end='2026-08-04')
    assert 'NO_MEETING_IN_DATE_WINDOW' in codes(evaluate(meta=meta))


def test_legacy_correction_keeps_original_and_requires_evidence(monkeypatch):
    trusted(monkeypatch);raw=csv_data(['7:30AM - 9:00AM TTF']);preview=intake.parse_file(raw,'fictional.csv','legacy_gec')
    original=preview.model_dump();meta=metadata([2])
    assert evaluate(preview,meta).status=='BLOCKED'
    meta['rows'][0]['proposed_meeting']=dict(days=['T','TH','F'],start='07:30',end='09:00',reason='',evidence_reference='')
    assert 'CORRECTION_EVIDENCE_MISSING' in codes(evaluate(preview,meta))
    meta['rows'][0]['proposed_meeting'].update(reason='Fictional supplier clarification',evidence_reference='Fictional corrected memo')
    result=evaluate(preview,meta)
    assert result.status=='READY' and preview.model_dump()==original
    assert result.effective_review.rows[0].original.days==['T','TH','F']
    assert result.metadata_origin=='administrator_provided'


def test_bad_completion_row_refs_and_client_authority_flags_rejected():
    for rows in [[metadata()['rows'][0]]*2,[{**metadata()['rows'][0],'source_row':999}]]:
        with pytest.raises(HTTPException):evaluate(meta={**metadata(),'rows':rows})
    from pydantic import ValidationError
    for extra in [{'verified':True},{'status':'READY'},{'authority':'official'}]:
        with pytest.raises(ValidationError):payload(meta={**metadata(),**extra})


def api_source(fixture,headers,kind='manual'):
    if kind=='manual':response=fixture.client.post('/api/external-schedules/preview',json={'rows':[{**ROW,'room':'','instructor':''}]},headers=headers)
    elif kind=='legacy':response=fixture.client.post('/api/external-schedules/preview-file?filename=fictional.csv&import_format=legacy_gec',json={'content_base64':base64.b64encode(csv_data()).decode(),'metadata':{'supplier':'','source_reference':'','academic_term':'','status':'draft'}},headers=headers)
    else:response=fixture.client.post('/api/external-schedules/preview-file?filename=fictional.'+kind,content=xlsx_bytes([{**ROW,'room':'','instructor':''}]) if kind=='xlsx' else csv_bytes([{**ROW,'room':'','instructor':''}]),headers=headers)
    assert response.status_code==200
    return response.json()


@pytest.mark.parametrize('kind',['manual','csv','xlsx','legacy'])
def test_all_formats_real_api_readiness_and_handoff_preserve_source(fixture,monkeypatch,kind):
    trusted(monkeypatch);headers=session(fixture);preview=api_source(fixture,headers,kind)
    body={'review_token':preview['review_token'],'mappings':[],'metadata':metadata([r['source_row'] for r in preview['rows']])}
    response=fixture.client.post('/api/external-schedules/readiness',json=body,headers=headers)
    assert response.status_code==200 and response.json()['status']=='READY'
    result=response.json();before={p:p.read_bytes() for p in fixture.path.parent.iterdir() if p.is_file()};rng=random.getstate()
    response=fixture.client.post('/api/external-schedules/handoff',json={**body,'assessment_receipt':result['assessment_receipt']},headers=headers)
    assert response.status_code==200 and response.json()['readiness']['status']=='READY'
    handoff=response.json();assert handoff['review']['source_sha256']==preview['source_sha256']
    assert [r['original'] for r in handoff['review']['rows']]==[r['input'] for r in preview['rows']]
    assert handoff['readiness']['assessment_receipt'] is None and not handoff['approved']
    assert all(p.read_bytes()==v for p,v in before.items()) and random.getstate()==rng


@pytest.mark.parametrize('change',['metadata','mapping','references','verification','reimport','invalidate','restart','expire','forged','wrong_receipt_kind'])
def test_stale_or_tampered_assessments_fail_closed(fixture,monkeypatch,change):
    trusted(monkeypatch);headers=session(fixture);preview=api_source(fixture,headers)
    body={'review_token':preview['review_token'],'mappings':[],'metadata':metadata()}
    response=fixture.client.post('/api/external-schedules/readiness',json=body,headers=headers);assert response.status_code==200
    receipt=response.json()['assessment_receipt']
    if change=='metadata':body['metadata']['term']='Changed fictional term'
    if change=='mapping':body['mappings']=[{'source_row':1,'sections':[{'reference_index':0,'target_id':'synthetic-section-b'}]}]
    if change=='references':monkeypatch.setattr(intake,'context',lambda:{**copy.deepcopy(CTX),'fixed':[dict(section='SYN-A',day='M',start='08:00',end='11:00')]})
    if change=='verification':monkeypatch.setattr(authority,'verification_for',lambda key:None)
    if change=='reimport':api_source(fixture,headers)
    if change=='invalidate':assert fixture.client.post('/api/external-schedules/readiness/invalidate',json={'review_token':preview['review_token']},headers=headers).status_code==200
    if change=='restart':monkeypatch.setattr(review,'_PROCESS_KEY',b'different-process')
    if change=='expire':
        for head in life._heads.values():head['expires']=0
    if change=='forged':receipt=receipt[:-1]+('a' if receipt[-1]!='a' else 'b')
    if change=='wrong_receipt_kind':receipt=preview['review_token']
    response=fixture.client.post('/api/external-schedules/handoff',json={**body,'assessment_receipt':receipt},headers=headers)
    assert response.status_code==409


def test_other_admin_and_same_admin_other_session_cannot_access_preview(fixture):
    headers=session(fixture);preview=api_source(fixture,headers)
    body={'review_token':preview['review_token'],'metadata':metadata(),'mappings':[]}
    with Session(fixture.engine) as db,db.begin():
        original=db.scalar(select(User).where(User.username=='admin@example.invalid'))
        db.add(User(username='other-admin@example.invalid',password_hash=original.password_hash,role='admin',is_active=True))
    for username in ['other-admin@example.invalid','admin@example.invalid']:
        login=fixture.client.post('/api/auth/login',headers={'Origin':ORIGIN},json={'username':username,'password':fixture.password});assert login.status_code==200
        other={'Origin':ORIGIN,'X-CSRF-Token':login.json()['csrf_token']}
        for path,payload_body in [('readiness',body),('review',{'review_token':preview['review_token']}),('handoff',{'review_token':preview['review_token']})]:
            assert fixture.client.post('/api/external-schedules/'+path,json=payload_body,headers=other).status_code==409


def test_auth_origin_csrf_malformed_and_size_limits(fixture):
    path='/api/external-schedules/readiness';body={'review_token':'fake','metadata':metadata()}
    assert fixture.client.post(path,json=body).status_code==401
    assert fixture.client.post(path,json=body,headers=session(fixture,'faculty')).status_code==403
    headers=session(fixture);preview=api_source(fixture,headers);body['review_token']=preview['review_token']
    assert fixture.client.post(path,json=body,headers={'Origin':ORIGIN}).status_code==403
    assert fixture.client.post(path,json=body,headers={**headers,'Origin':'https://evil.invalid'}).status_code==403
    assert fixture.client.post(path,content=b'x'*(2*intake.MAX_BYTES+1),headers={**headers,'Content-Type':'application/json'}).status_code==413
    assert fixture.client.post(path,content=b'{}',headers={**headers,'Content-Type':'text/plain'}).status_code==415
    for extra in [{'status':'READY'},{'approved':True},{'source_sha256':'forged'}]:assert fixture.client.post(path,json={**body,**extra},headers=headers).status_code==422
    assert fixture.client.post(path,json={**body,'metadata':{**metadata(),'term':'x'*121}},headers=headers).status_code==422


def test_missing_trusted_coverage_cannot_verify(monkeypatch):
    trusted(monkeypatch)
    monkeypatch.setattr(authority,'verification_for',lambda key:authority.Verification(key,'fictional-policy.1','Fictional evidence',frozenset({'source'})))
    assert 'AUTHORITATIVE_VERIFICATION_REQUIRED' in codes(evaluate())


def test_completed_section_ids_cannot_silently_override_conflicting_d4_mapping(monkeypatch):
    trusted(monkeypatch);meta=metadata();meta['rows'][0]['section_ids']=['synthetic-section-a']
    result=evaluate(meta=meta,mappings=[{'source_row':1,'sections':[{'reference_index':0,'target_id':'synthetic-section-b'}]}])
    assert 'INCONSISTENT_SECTION_MAPPING' in codes(result)


def test_invalidation_during_evaluation_cannot_publish_ready(fixture,monkeypatch):
    trusted(monkeypatch);headers=session(fixture);preview=api_source(fixture,headers)
    actual=ready.evaluate
    def changed(payload):
        result=actual(payload)
        for head in life._heads.values():head['revision']+=1;head['assessment']=None
        return result
    monkeypatch.setattr(ready,'evaluate',changed)
    response=fixture.client.post('/api/external-schedules/readiness',headers=headers,json={'review_token':preview['review_token'],'mappings':[],'metadata':metadata()})
    assert response.status_code==409
