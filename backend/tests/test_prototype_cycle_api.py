"""Real original GA preparation, FastAPI cookies/CSRF, and new SQLite only."""
import csv
import io
import json
import secrets
from uuid import UUID, uuid4
import pytest
from services.ga_worker_contract import fictional_source
try:
    fictional_source()
except ValueError:
    pytest.skip('Owned empty-import snapshot required', allow_module_level=True)


def test_actual_generated_review_application_exports_and_faculty_refresh(monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from identity_models import Base, User, FacultyIdentityRecord
    from routers.prototype_cycle import create_app
    from services import auth_service as auth
    from services.prototype_cycle import Cycle
    from services.prototype_tip_witness import TipWitness
    from tests.test_prototype_cycle import create, admit, finish, WorkflowDirectory
    from tests.test_prototype_inputs import CHAIR_ID, FACULTY_ID, FACULTY
    from tests.test_prototype_workload import ACTOR, OTHER, PRINCIPAL, change
    s = create(); s.inputs.workload.save(PRINCIPAL, change(**{'2': 3}))
    record, command = admit(s); generated = finish(s, record['run_id'])
    s.offline_qualification = False  # API must never be an in-process execution shortcut.
    engine = create_engine('sqlite:///'+str(s.storage.root/'identity.sqlite3'), connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    password = secrets.token_urlsafe(24)
    with Session(engine) as db, db.begin():
        db.add(FacultyIdentityRecord(id=UUID(FACULTY.faculty_id), display_code='SYN-F2', name='Fictional Faculty 2'))
        for actor, name, role, faculty in [(ACTOR, 'scheduler', 'admin', None), (CHAIR_ID, 'chair', 'admin', None),
            (FACULTY_ID, 'faculty', 'faculty', UUID(FACULTY.faculty_id)), (OTHER, 'unscoped', 'admin', None)]:
            db.add(User(id=UUID(actor), username=name+'@fictional.invalid', role=role, faculty_id=faculty, password_hash=auth.hash_password(password)))
    def identity_db():
        with Session(engine) as db:
            yield db
    def login(client, label):
        r = client.post('/api/auth/login', json={'username': label+'@fictional.invalid', 'password': password}, headers={'Origin': 'http://localhost:5173'})
        assert r.status_code == 200
        return {'Origin': 'http://localhost:5173', 'X-CSRF-Token': r.json()['csrf_token']}
    monkeypatch.setenv('AUTH_ALLOWED_ORIGINS', 'http://localhost:5173'); monkeypatch.setenv('AUTH_COOKIE_SECURE', 'false')
    app = create_app(s, identity_db)
    assert not any(any(word in p for word in ['/execute', '/recover', '/resume', '/step']) for p in app.openapi()['paths'])
    with TestClient(app) as client:
        assert client.get('/api/prototype/cycle/runs').status_code == 401
        for url in ['/prototype/cycle', '/prototype/cycle/model.mjs', '/prototype/cycle/console.mjs']:
            assert client.get(url).status_code == 200
        headers = login(client, 'scheduler')
        assert client.get('/api/prototype/cycle/runs/'+record['run_id']).json()['result'] == generated['result']
        assert client.post('/api/prototype/cycle/admissions', json=command.model_dump(), headers=headers).json()['result'] == generated['result']
        extra = client.post('/api/prototype/cycle/admissions', json=command.model_dump() | {'seed': 710}, headers=headers)
        assert extra.status_code == 422
        deferred = client.post('/api/prototype/cycle/admissions', json=command.model_dump() | {'request_id': str(uuid4())}, headers=headers).json()
        assert deferred['state'] == 'ADMITTED_NATIVE_BLOCKED' and not deferred['generated']
        ack = client.post('/api/prototype/cycle/runs/'+deferred['run_id']+'/stop', json={'request_id': str(uuid4())}, headers=headers)
        assert ack.status_code == 200 and not ack.json()['termination_verified']
        assert client.get('/api/prototype/cycle/compare/'+record['run_id']+'/'+record['run_id']).json()['tie']
        headers = login(client, 'faculty')
        assert client.get('/api/prototype/cycle/timetable/2').json()['state'] == 'NO_APPROVED_PROTOTYPE_SCHEDULE'
        assert client.get('/api/prototype/cycle/timetable/1').status_code == 403
        assert client.get('/api/prototype/cycle/runs/'+record['run_id']).status_code == 403
        review = dict(request_id=str(uuid4()), expected_review=0, candidate_fingerprint=generated['latest_candidate_fingerprint'],
                      decision='APPROVE', explanation='Explicit fictional Chair mandate reviewed workload and conflicts.')
        assert client.post('/api/prototype/cycle/runs/'+record['run_id']+'/decision', json=review, headers=headers).status_code == 403
        headers = login(client, 'chair')
        assert client.post('/api/prototype/cycle/runs/'+record['run_id']+'/decision', json=review).status_code == 403
        response = client.post('/api/prototype/cycle/runs/'+record['run_id']+'/decision', json=review, headers=headers)
        assert response.status_code == 200 and not response.json()['institutional_approval']
        assert client.post('/api/prototype/cycle/runs/'+record['run_id']+'/decision', json=review, headers=headers).json() == response.json()
        versions = client.get('/api/prototype/cycle/versions').json()
        assert len(versions) == 1 and versions[0]['candidate'] == generated['result']
        for kind in ['json', 'csv', 'txt']:
            exported = client.get('/api/prototype/cycle/runs/'+record['run_id']+'/export/'+kind)
            assert exported.status_code == 200 and exported.headers['Cache-Control'] == 'no-store'
            assert record['run_id'] in exported.text
            approved = client.get('/api/prototype/cycle/versions/1/export/'+kind)
            assert approved.status_code == 200 and approved.headers['Content-Disposition'].startswith('attachment;')
        raw = client.get('/api/prototype/cycle/runs/'+record['run_id']+'/export/json').json()
        assert raw['result'] == generated['result']
        rows = list(csv.DictReader(io.StringIO(client.get('/api/prototype/cycle/runs/'+record['run_id']+'/export/csv').text)))
        assert [json.loads(row['original_observation_json']) for row in rows] == generated['result']['original_result']['history']
        login(client, 'faculty')
        timetable = client.get('/api/prototype/cycle/timetable/2').json()
        assert timetable['version'] == 1 and timetable['workload']['assigned_units'] == 3
        assert all(row['faculty'] == '2' for row in timetable['schedule'])
        login(client, 'unscoped')
        assert client.get('/api/prototype/cycle/versions').status_code == 403
    reopened = Cycle(s.inputs, WorkflowDirectory(), TipWitness(root=s.witness.storage.root, key_fingerprint=s.witness.key_fingerprint), root=s.storage.root)
    with TestClient(create_app(reopened, identity_db)) as client:
        login(client, 'faculty')
        assert client.get('/api/prototype/cycle/timetable/2').json() == timetable
    with TestClient(create_app()) as client:
        assert client.get('/api/prototype/cycle/runs').status_code == 503
    engine.dispose()
