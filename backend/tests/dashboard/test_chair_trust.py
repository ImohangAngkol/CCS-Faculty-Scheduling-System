"""D12 decisions through real D8/D9/D10 checks, fictional issuers only."""
from contextlib import contextmanager
from dataclasses import replace
from uuid import uuid4
import pytest
from sqlalchemy.orm import Session
from confirmation_models import ConfirmationBase, guard_sql, transition_sql
from services import chair_review_service as chair_service, adjustment_schedule_service as schedules
from services import ga_v2_service, ga_v2_constraints as constraints
from services import external_schedule_verification_service as evidence, confirmation_authority_service as confirmer
from tests.dashboard.test_chair_reviews import chair, setup, fixture, submitted, decide, session
from tests.dashboard.test_external_confirmations import permit, proposal, decision, isolate
from tests.dashboard.evidence_support import install_fictional
from tests.d10.support import templates, preferences
from tests.d10.test_v2_engine import catalog_for

REAL_TRUST = chair_service.trusted_snapshot


@pytest.fixture
def real_trust(chair, monkeypatch):
    f=chair
    ConfirmationBase.metadata.create_all(f.engine)
    with f.engine.begin() as db:
        for sql in guard_sql('sqlite')+transition_sql('sqlite'):db.exec_driver_sql(sql)
    install_fictional(monkeypatch);permit(monkeypatch)
    headers=session(f,'admin');f.confirmation=proposal(f,headers)
    assert decision(f,headers,f.confirmation).status_code==200
    values=templates(compact=True)
    catalog=catalog_for(values).model_copy(update={'sections':(('synthetic-section-a','SYN-A'),('synthetic-section-b','SYN-B')),
        'faculty':(('synthetic-instructor-0','990001'),('fictional-instructor-1','990002')),'rooms':(('SYN LEC','Fictional Lecture Room'),)})
    deployment=ga_v2_service.Deployment(catalog,constraints.LedgerAuthority(lambda:Session(f.engine),catalog,values),values,preferences())
    monkeypatch.setattr(ga_v2_service,'institutional_deployment',lambda year,term:deployment)
    monkeypatch.setattr(chair_service,'trusted_snapshot',REAL_TRUST)
    with Session(f.engine) as db:f.real_snapshot=constraints._read_snapshot(db,catalog,values)
    original=f.provider
    @contextmanager
    def provider():
        with original() as base:
            # Fixture-owned mapping between separate catalog namespaces, exact IDs.
            mapped=tuple(c.model_copy(update={'sections':tuple({'synthetic-section-a':'section-a','synthetic-section-b':'section-b'}[s] for s in c.sections)}) for c in f.real_snapshot.commitments)
            yield replace(base,academic_year=catalog.academic_year,term=catalog.term,constraint_digest=f.real_snapshot.digest,commitments=mapped)
    monkeypatch.setattr(schedules,'institutional_schedule_source',provider)
    return f


def test_approval_records_actual_fresh_ledger_heads(real_trust):
    f=real_trust;r=submitted(f);f.chair_headers=session(f,'admin')
    reply=decide(f,r);assert reply.status_code==200,reply.json()
    provenance=reply.json()['provenance']
    assert provenance['trust_status']=='FRESH_D8_D9_D10'
    assert provenance['constraint_heads'][0]['revision_id']==f.confirmation['revision_id']
    assert provenance['constraint_heads'][0]['content_digest']==f.real_snapshot.heads[0].content_digest


@pytest.mark.parametrize('loss',['evidence','issuer','confirmer','revocation','source_digest'])
def test_real_trust_loss_prevents_approval_and_retains_rejection(real_trust,monkeypatch,loss):
    f=real_trust;r=submitted(f);f.chair_headers=session(f,'admin')
    if loss=='evidence':monkeypatch.setattr(evidence,'verification_for',lambda *a,**k:None)
    elif loss=='issuer':monkeypatch.setattr(evidence,'authority_policy_for',lambda *a,**k:None)
    elif loss=='confirmer':monkeypatch.setattr(confirmer,'authorization_for',lambda *a,**k:None)
    elif loss=='revocation':
        response=f.client.post('/api/external-confirmations/records/'+f.confirmation['record_id']+'/revoke',headers=f.chair_headers,json={'operation_id':str(uuid4()),'expected_version':1,'reason':'Fictional issuer revocation'})
        assert response.status_code==200
    else:f.real_snapshot=f.real_snapshot.model_copy(update={'catalog':f.real_snapshot.catalog.model_copy(update={'revision':'changed-fictional-catalog'})})
    assert decide(f,r).status_code in (409,503)
    assert decide(f,r,'reject').status_code==200
