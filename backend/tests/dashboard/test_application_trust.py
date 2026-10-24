"""D13 application with actual D8/D9/D10 ledger checks, fictional issuers."""
from contextlib import contextmanager
from dataclasses import replace
from uuid import uuid4
import pytest
from tests.dashboard.test_schedule_applications import application,chair,setup,fixture,approved,preview,apply,counts
from tests.dashboard.test_chair_trust import real_trust,isolate
from services import published_schedule_source as publication,adjustment_schedule_service as schedules
from services import external_schedule_verification_service as evidence,confirmation_authority_service as confirmer

@pytest.fixture
def trusted_application(application,real_trust,monkeypatch):
    f=application;assert f is real_trust
    prior=f.publication_provider
    @contextmanager
    def source():
        with prior() as ctx,schedules.institutional_schedule_source() as real:
            yield replace(ctx,source=real)
    monkeypatch.setattr(publication,'institutional_publication_source',source)
    return f

def test_actual_trusted_confirmation_applies_and_preserves_history(trusted_application):
    f=trusted_application;r=approved(f);response=apply(f,r);assert response.status_code==200,response.json();assert counts(f)==[2,1,1]

@pytest.mark.parametrize('loss',['evidence','issuer','confirmer','revoked'])
def test_fresh_real_trust_loss_after_approval_blocks_application(trusted_application,monkeypatch,loss):
    f=trusted_application;r=approved(f);body={**preview(f,r).json()['command'],'operation_id':str(uuid4())}
    if loss=='evidence':monkeypatch.setattr(evidence,'verification_for',lambda *a,**k:None)
    elif loss=='issuer':monkeypatch.setattr(evidence,'authority_policy_for',lambda *a,**k:None)
    elif loss=='confirmer':monkeypatch.setattr(confirmer,'authorization_for',lambda *a,**k:None)
    else:
        from tests.dashboard.test_schedule_applications import session,publisher
        headers=session(f,'admin')
        reply=f.client.post('/api/external-confirmations/records/'+f.confirmation['record_id']+'/revoke',headers=headers,json={'operation_id':str(uuid4()),'expected_version':1,'reason':'Fictional withdrawal before application'})
        assert reply.status_code==200;publisher(f)
    assert apply(f,r,body).status_code in (409,503);assert counts(f)==[0,0,0]
