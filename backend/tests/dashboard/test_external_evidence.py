"""D8 policy boundaries using independently injected fictional provider records."""
import copy
from dataclasses import replace
from datetime import datetime,timedelta,timezone
import json
import random

import pytest

from services import external_schedule_verification_service as trust
from services import external_schedule_readiness_service as ready
from services.evidence_sanitization import sanitize, sanitize_tree, MARKER
from tests.dashboard.evidence_support import fictional, install_fictional
from tests.dashboard.test_external_readiness import isolate, source, payload, metadata, api_source
from tests.dashboard.test_external_preview import ROW, session
from tests.dashboard.test_my_schedule import fixture, ORIGIN


def context():
    return trust.EvidenceContext('a'*64,'b'*64,'c'*64,'Fictional College','fictional-source.1','2026-2027','Fictional first term',{1:'SYN-GEC101',2:'SYN-GEC102'},frozenset())


def configured(monkeypatch, change=None):
    ctx=context();now=datetime.now(timezone.utc);policy,proof=fictional(ctx,now)
    if change:policy,proof=change(policy,proof,now)
    monkeypatch.setattr(trust,'verification_for',lambda key,**kwargs:proof)
    monkeypatch.setattr(trust,'authority_policy_for',lambda issuer:policy)
    return ctx


def evidence(proof,**changes):return replace(proof,evidence=proof.evidence.model_copy(update=changes))


@pytest.mark.parametrize('name,change,outcome,code',[
 ('unknown',lambda p,v,n:(None,v),'UNVERIFIED','UNKNOWN_ISSUER'),
 ('unauthorized',lambda p,v,n:(p.model_copy(update={'issuer_id':'other-issuer'}),v),'INVALID','UNAUTHORIZED_ISSUER'),
 ('term',lambda p,v,n:(p,evidence(v,term='Other term')),'INVALID','TERM_SCOPE_MISMATCH'),
 ('year',lambda p,v,n:(p,evidence(v,academic_year='2025-2026')),'INVALID','TERM_SCOPE_MISMATCH'),
 ('organization',lambda p,v,n:(p,evidence(v,organization_id='other-college')),'INVALID','ORGANIZATION_SCOPE_MISMATCH'),
 ('subject',lambda p,v,n:(p.model_copy(update={'subjects':['SYN-GEC101']}),v),'INVALID','SUBJECT_SCOPE_MISMATCH'),
 ('source',lambda p,v,n:(p,evidence(v,source_fingerprint='f'*64)),'STALE','EVIDENCE_BINDING_MISMATCH'),
 ('candidate',lambda p,v,n:(p,evidence(v,input_fingerprint='f'*64)),'STALE','EVIDENCE_BINDING_MISMATCH'),
 ('preview',lambda p,v,n:(p,evidence(v,preview_fingerprint='f'*64)),'STALE','EVIDENCE_BINDING_MISMATCH'),
 ('source_revision',lambda p,v,n:(p,evidence(v,source_revision='old')),'STALE','EVIDENCE_BINDING_MISMATCH'),
 ('issuer_claim',lambda p,v,n:(p,evidence(v,supplier='Other college')),'STALE','EVIDENCE_BINDING_MISMATCH'),
 ('policy',lambda p,v,n:(p.model_copy(update={'revision':'fictional-policy.2'}),v),'STALE','POLICY_REVISION_MISMATCH'),
 ('suspended',lambda p,v,n:(p.model_copy(update={'state':'suspended'}),v),'REVOKED','ISSUER_SUSPENDED'),
 ('issuer_revoked',lambda p,v,n:(p.model_copy(update={'state':'revoked'}),v),'REVOKED','ISSUER_REVOKED'),
 ('revoked',lambda p,v,n:(p,evidence(v,revocation_status='revoked')),'REVOKED','EVIDENCE_REVOKED'),
 ('revocation_unknown',lambda p,v,n:(p,evidence(v,revocation_status='unknown')),'UNVERIFIED','REVOCATION_UNKNOWN'),
 ('expired',lambda p,v,n:(p,evidence(v,expires_at=(n-timedelta(seconds=1)).isoformat(),verified_at=(n-timedelta(seconds=2)).isoformat())),'EXPIRED','EVIDENCE_EXPIRED'),
 ('old_check',lambda p,v,n:(p,evidence(v,verified_at=(n-timedelta(seconds=900)).isoformat(),issued_at=(n-timedelta(seconds=1000)).isoformat())),'STALE','EVIDENCE_FRESHNESS'),
 ('old_revocation',lambda p,v,n:(p,evidence(v,revocation_checked_at=(n-timedelta(seconds=900)).isoformat())),'STALE','EVIDENCE_FRESHNESS'),
 ('future_check',lambda p,v,n:(p,evidence(v,verified_at=(n+timedelta(seconds=2)).isoformat())),'STALE','EVIDENCE_FRESHNESS'),
 ('before_authority',lambda p,v,n:(p,evidence(v,issued_at=(n-timedelta(days=2)).isoformat())),'EXPIRED','AUTHORITY_WINDOW'),
 ('after_authority',lambda p,v,n:(p.model_copy(update={'expires_at':(n-timedelta(seconds=120)).isoformat()}),v),'EXPIRED','AUTHORITY_WINDOW'),
 ('invalid',lambda p,v,n:(p,evidence(v,outcome='INVALID')),'INVALID','PROVIDER_INVALID'),
 ('unsupported',lambda p,v,n:(p,evidence(v,outcome='UNSUPPORTED')),'UNSUPPORTED','PROVIDER_UNSUPPORTED'),
 ('rows',lambda p,v,n:(p,evidence(v,source_rows=[99])),'INVALID','ROW_COVERAGE_MISMATCH'),
])
def test_issuer_scope_binding_and_lifecycle(monkeypatch,name,change,outcome,code):
    result=trust.evaluate_trust(configured(monkeypatch,change))
    assert result.outcome==outcome
    assert code in {f.code for f in result.findings}
    assert not result.institutionally_confirmed and not result.activated


def test_valid_fictional_provider_never_confirms(monkeypatch):
    result=trust.evaluate_trust(configured(monkeypatch))
    assert result.outcome=='VERIFIED' and all(r.outcome=='VERIFIED' for r in result.rows)
    assert result.verified_issuer=='fictional-issuer' and result.policy_provenance=='fictional-authorization'
    assert result.valid_until and not result.institutionally_confirmed


def test_partial_rows_do_not_inherit_verification(monkeypatch):
    result=trust.evaluate_trust(configured(monkeypatch,lambda p,v,n:(p,evidence(v,source_rows=[1]))))
    assert result.outcome=='UNVERIFIED'
    assert [(r.source_row,r.outcome) for r in result.rows]==[(1,'VERIFIED'),(2,'UNVERIFIED')]


@pytest.mark.parametrize('mode,allowed',[('exact_source',True),('authorized_revision',False)])
def test_corrections_require_explicit_revision_scope(monkeypatch,mode,allowed):
    ctx=configured(monkeypatch,lambda p,v,n:(p.model_copy(update={'allow_authorized_revisions':allowed}),evidence(v,coverage_mode=mode)))
    result=trust.evaluate_trust(replace(ctx,changed_rows=frozenset({1})))
    assert result.outcome=='UNVERIFIED' and result.findings[0].code=='UNVERIFIED_CORRECTION'


def test_policy_changes_are_in_fresh_assessment(monkeypatch):
    ctx=configured(monkeypatch);first=trust.evaluate_trust(ctx)
    old=trust.authority_policy_for('fictional-issuer')
    monkeypatch.setattr(trust,'authority_policy_for',lambda _:old.model_copy(update={'max_age_seconds':180}))
    second=trust.evaluate_trust(ctx)
    assert first.policy_digest!=second.policy_digest


def test_exact_source_is_valid_only_without_material_changes(monkeypatch):
    ctx=configured(monkeypatch,lambda p,v,n:(p,evidence(v,coverage_mode='exact_source')))
    assert trust.evaluate_trust(ctx).outcome=='VERIFIED'


@pytest.mark.parametrize('problem',['conflicting_evidence','invalid_signature','unsupported_signature'])
def test_provider_conflicts_or_signature_problems_fail_closed(monkeypatch,problem):
    ctx=configured(monkeypatch,lambda p,v,n:(p,evidence(v,problem=problem)))
    result=trust.evaluate_trust(ctx)
    assert result.outcome!='VERIFIED' and result.findings[0].code==problem.upper()


def test_provider_cannot_mutate_expected_row_inventory(monkeypatch):
    original=context();now=datetime.now(timezone.utc);policies={}
    def provider(key,*,context):
        context.subjects.pop(2)
        policy,proof=fictional(context,now);policies[policy.issuer_id]=policy
        return proof
    monkeypatch.setattr(trust,'verification_for',provider)
    monkeypatch.setattr(trust,'authority_policy_for',policies.get)
    result=trust.evaluate_trust(original)
    assert len(original.subjects)==2 and result.outcome=='UNVERIFIED'


@pytest.mark.parametrize('field',['organizations','terms','subjects'])
def test_unbounded_authority_scope_is_not_supported(monkeypatch,field):
    result=trust.evaluate_trust(configured(monkeypatch,lambda p,v,n:(p.model_copy(update={field:['*']}),v)))
    assert result.outcome!='VERIFIED'


def test_completion_rejects_encoded_receipt_fragments_without_echo(monkeypatch):
    from fastapi import HTTPException
    request=payload();request.metadata.evidence_reference='eyJmaWN0aW9uYWwiOiJub3QtcmVhbC1zZWNyZXQifQ...tail'
    with pytest.raises(HTTPException) as error: ready.evaluate(request)
    assert 'eyJ' not in str(error.value.detail)


@pytest.mark.parametrize('response',[None,True,{},'untrusted','legacy'])
def test_missing_or_malformed_provider_fails_closed(monkeypatch,response):
    if response=='legacy':response=trust.Verification('a'*64,'old','name',trust.REQUIRED_COVERAGE)
    monkeypatch.setattr(trust,'verification_for',lambda *a,**kw:response)
    result=trust.evaluate_trust(context())
    assert result.outcome!='VERIFIED' and all(r.outcome!='VERIFIED' for r in result.rows)


def test_provider_exception_details_never_returned(monkeypatch):
    def fail(*args,**kwargs):raise RuntimeError('FICTIONAL_PRIVATE_DIAGNOSTIC')
    monkeypatch.setattr(trust,'verification_for',fail)
    result=trust.evaluate_trust(context())
    assert result.outcome=='PROVIDER_UNAVAILABLE' and 'FICTIONAL_PRIVATE_DIAGNOSTIC' not in result.model_dump_json()


@pytest.mark.parametrize('field,value',[('source_rows',[1,1]),('source_rows',[True]),('expires_at','not-date'),('verified_at','2026-10-23T12:00:00'),('verification_method','filename'),('unexpected','private')])
def test_malformed_provider_details_not_echoed(monkeypatch,field,value):
    result=trust.evaluate_trust(configured(monkeypatch,lambda p,v,n:(p,evidence(v,**{field:value}))))
    assert result.outcome!='VERIFIED'


@pytest.mark.parametrize('kind',['manual','csv','xlsx','legacy'])
def test_actual_api_integration_and_handoff_rechecks(fixture,monkeypatch,kind):
    install_fictional(monkeypatch);headers=session(fixture);preview=api_source(fixture,headers,kind)
    body={'review_token':preview['review_token'],'metadata':metadata([r['source_row'] for r in preview['rows']]),'mappings':[]}
    before={p:p.read_bytes() for p in fixture.path.parent.iterdir() if p.is_file()};rng=random.getstate()
    result=fixture.client.post('/api/external-schedules/readiness',json=body,headers=headers)
    assert result.status_code==200
    data=result.json();assert data['evidence_trust']['outcome']=='VERIFIED' and data['status']=='READY'
    handoff={**body,'assessment_receipt':data['assessment_receipt']}
    printed=fixture.client.post('/api/external-schedules/handoff',json=handoff,headers=headers)
    assert printed.status_code==200 and printed.json()['readiness']['evidence_trust']['outcome']=='VERIFIED'
    assert printed.json()['readiness']['assessment_receipt'] is None
    monkeypatch.setattr(trust,'authority_policy_for',lambda _:None)
    assert fixture.client.post('/api/external-schedules/handoff',json=handoff,headers=headers).status_code==409
    assert rng==random.getstate() and all(p.read_bytes()==v for p,v in before.items())


def test_claims_hashes_and_document_presence_cannot_establish_authority(monkeypatch):
    request=payload();request.metadata.evidence_reference='Fictional signed PDF matching uploaded hash'
    result=ready.evaluate(request)[1]
    assert result.status=='BLOCKED' and result.evidence_trust.outcome=='PROVIDER_UNAVAILABLE'
    assert not result.approved and not result.activated and not result.persisted


@pytest.mark.parametrize('extra',[{'verified':True},{'evidence_trust':{'outcome':'VERIFIED'}},{'issuer_id':'fictional-issuer'},{'policy_revision':'fictional-policy.1'}])
def test_client_authority_fields_rejected(fixture,extra):
    headers=session(fixture);preview=api_source(fixture,headers)
    body={'review_token':preview['review_token'],'metadata':metadata(),**extra}
    assert fixture.client.post('/api/external-schedules/readiness',json=body,headers=headers).status_code==422


@pytest.mark.parametrize('key',['review_token','assessment_receipt','session_id','authorization','cookie','password','provider_response','X-CSRF-Token','csrfToken','client_secret','api_key','session'])
def test_redaction_of_quoted_truncated_and_escaped_values(key):
    secret='eyJmaWN0aW9uYWwiOiJub3QtcmVhbC1zZWNyZXQifQ...tail.'+'f'*64
    for line in [f"E {{'{key}': '{secret}'}}",f'"{key}": "{secret}"',f'\\"{key}\\": \\"{secret}\\"']:
        clean=sanitize(line+'\n1 failed, 25 passed')
        assert secret not in clean and 'eyJ' not in clean and 'f'*16 not in clean
        assert '1 failed, 25 passed' in clean and MARKER in clean


def test_unlabelled_fragments_keys_headers_urls_and_nested_privacy():
    parts=['eyJmaWN0aW9uYWwiOiJub3QtcmVhbC1zZWNyZXQifQ...tail.'+'a'*64,'abcdefghijklmnop...tail.'+'b'*64]
    for secret in parts:assert secret not in sanitize('failure: '+secret)
    sample={'trace':"Authorization: Bearer fictional-private\n1 failed",'session_id':'fictional-private','error':'postgresql://fictional:fictional@localhost/test'}
    clean=json.dumps(sanitize_tree(sample))
    assert 'fictional-private' not in clean and 'postgresql://' not in clean and '1 failed' in clean
    assert sanitize(sanitize('review_token = hidden'))==MARKER
