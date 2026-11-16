"""Actual cookie/CSRF HTTP with genuine IN-PROCESS protocol output, no worker."""
import secrets
from uuid import UUID, uuid4
import pytest
from services.ga_worker_contract import fictional_source
try:
    fictional_source()
except ValueError:
    pytest.skip('Owned empty-import snapshot required', allow_module_level=True)


def test_versioned_segment_authorization_gate_and_review_API(monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from identity_models import Base, User, FacultyIdentityRecord
    from services import auth_service as auth
    from services.prototype_native_adapter import NativeAdapter
    from routers.prototype_native import create_app
    from tests.test_prototype_native_adapter import setup, adapter_for
    from tests.test_prototype_inputs import CHAIR_ID, FACULTY_ID, FACULTY
    from tests.test_prototype_workload import ACTOR, OTHER
    cycle,run,_=setup();adapter=adapter_for(cycle)
    engine=create_engine('sqlite:///'+str(adapter.journal.storage.root/'identity.sqlite3'),connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine);password=secrets.token_urlsafe(24)
    with Session(engine) as db,db.begin():
        db.add(FacultyIdentityRecord(id=UUID(FACULTY.faculty_id),display_code='SYN-F2',name='Fictional Faculty 2'))
        for actor,label,role,faculty in [(ACTOR,'scheduler','admin',None),(CHAIR_ID,'chair','admin',None),
            (FACULTY_ID,'faculty','faculty',UUID(FACULTY.faculty_id)),(OTHER,'unscoped','admin',None)]:
            db.add(User(id=UUID(actor),username=label+'@fictional.invalid',role=role,faculty_id=faculty,password_hash=auth.hash_password(password)))
    def identity_db():
        with Session(engine) as db:yield db
    def login(client,label):
        result=client.post('/api/auth/login',json={'username':label+'@fictional.invalid','password':password},headers={'Origin':'http://localhost:5173'})
        assert result.status_code==200
        return {'Origin':'http://localhost:5173','X-CSRF-Token':result.json()['csrf_token']}
    monkeypatch.setenv('AUTH_ALLOWED_ORIGINS','http://localhost:5173');monkeypatch.setenv('AUTH_COOKIE_SECURE','false')
    app=create_app(adapter,identity_db);url='/api/prototype/native-v1/runs/'+run
    with TestClient(app) as client:
        assert client.get(url).status_code==401
        headers=login(client,'unscoped')
        assert client.post(url+'/segment',json={'request_id':str(uuid4())},headers=headers).status_code==403
        assert client.post(url+'/recover',headers=headers).status_code==403
        headers=login(client,'chair')
        assert client.post(url+'/segment',json={'request_id':str(uuid4())},headers=headers).status_code==403
        headers=login(client,'scheduler')
        assert client.post(url+'/segment',json={'request_id':str(uuid4())}).status_code==403
        assert client.post(url+'/recover').status_code==403
        assert client.post(url+'/segment',json={'request_id':str(uuid4()),'role':'admin'},headers=headers).status_code==422
        nonce=str(uuid4());first=client.post(url+'/segment',json={'request_id':nonce},headers=headers)
        assert first.status_code==200 and first.json()['run']['sequence']==1
        assert client.post(url+'/segment',json={'request_id':nonce},headers=headers).json()==first.json()
        completed=client.post(url+'/segment',json={'request_id':str(uuid4())},headers=headers)
        assert completed.status_code==200 and completed.json()['run']['state']=='COMPLETED'
        actual=completed.json()['run'];assert actual['generated'] and not completed.json()['native_result_verified']
        headers=login(client,'chair')
        decision=dict(request_id=str(uuid4()),expected_review=0,candidate_fingerprint=actual['latest_candidate_fingerprint'],
            decision='APPROVE',explanation='Fictional HTTP protocol candidate reviewed')
        assert client.post('/api/prototype/cycle/runs/'+run+'/decision',json=decision,headers=headers).status_code==200
        headers=login(client,'faculty')
        assert client.get('/api/prototype/cycle/timetable/2').json()['version']==1
        assert client.get(url).status_code==403
        headers=login(client,'scheduler')
        for kind in ['json','csv','txt']:
            exported=client.get('/api/prototype/cycle/runs/'+run+'/export/'+kind)
            assert exported.status_code==200 and exported.headers['Cache-Control']=='no-store'
            versioned=client.get(url+'/export/'+kind)
            assert versioned.status_code==200 and versioned.headers['Cache-Control']=='no-store'
            assert adapter.transport.kind in versioned.text
    # Genuine Windows mode is not activated by exposing the separate route.
    blocked=create_app(NativeAdapter(cycle),identity_db)
    with TestClient(blocked) as client:
        headers=login(client,'scheduler')
        response=client.post(url+'/segment',json={'request_id':str(uuid4())},headers=headers)
        assert response.status_code==503 and 'PRESERVATION_PROVIDER' in response.text
    engine.dispose()
