"""U5M actual ASGI/auth/SQLite qualification; no institutional provider."""
from dataclasses import dataclass
from datetime import timedelta
import secrets
from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,event,select
from sqlalchemy.orm import Session
import database
from identity_models import Base,User,FacultyIdentityRecord,LoginSession,now
from main import app
from services import auth_service as auth,identity_service as identities
from services import chair_authority_service as chairs,application_authority_service as applications,ga_trusted_runs as runs
from services.ga_worker_contract import fictional_source

ORIGIN='http://localhost:5173'
FACULTY='81000000-0000-4000-8000-000000000001'
OTHER='81000000-0000-4000-8000-000000000002'

@dataclass(repr=False)
class Fixture:
    client:object
    engine:object
    password:str
    def __repr__(self):return '<Owned fictional auth/SQLite fixture; credentials withheld>'
    def login(self,username='faculty@fictional.invalid'):
        response=self.client.post('/api/auth/login',headers={'Origin':ORIGIN},json={'username':username,'password':self.password})
        if response.status_code!=200:pytest.fail('Fictional login failed; response withheld')
        return {'Origin':ORIGIN,'X-CSRF-Token':response.json()['csrf_token']}

@pytest.fixture
def identity(monkeypatch,tmp_path):
    fictional_source()
    engine=create_engine('sqlite:///'+str(tmp_path/'fictional-auth.sqlite3'),connect_args={'check_same_thread':False})
    @event.listens_for(engine,'connect')
    def fk(db,unused):db.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine);password=secrets.token_urlsafe(24)
    registry=(identities.FacultyIdentity(FACULTY,0,'FIC-0','Fictional Faculty Zero'),identities.FacultyIdentity(OTHER,1,'FIC-1','Fictional Faculty One'))
    monkeypatch.setattr(identities,'load_faculty_identities',lambda:registry)
    with Session(engine) as db,db.begin():
        for record in registry:db.add(FacultyIdentityRecord(id=UUID(record.faculty_id),display_code=record.display_code,name=record.name))
        db.flush()
        for username,role,binding in [('admin@fictional.invalid','admin',None),('faculty@fictional.invalid','faculty',UUID(FACULTY))]:
            db.add(User(username=username,role=role,faculty_id=binding,password_hash=auth.hash_password(password)))
    def isolated_db():
        with Session(engine) as db:yield db
    monkeypatch.setattr(database,'identity_engine',lambda:pytest.fail('Institutional database forbidden'))
    monkeypatch.setattr(app,'dependency_overrides',{database.get_identity_db:isolated_db,auth.authenticated_db:isolated_db})
    monkeypatch.setattr(auth,'LOGIN_LIMITER',auth.LoginLimiter());monkeypatch.setenv('AUTH_ALLOWED_ORIGINS',ORIGIN);monkeypatch.setenv('AUTH_COOKIE_SECURE','false')
    with TestClient(app,base_url='http://localhost') as client:yield Fixture(client,engine,password)
    engine.dispose()

@pytest.mark.parametrize('mode',['headers','query','forged_cookie'])
def test_client_role_claims_never_create_identity(identity,mode):
    headers={'X-Role':'admin','X-Department-ID':'FICTIONAL-CLAIM','X-Faculty-ID':OTHER}
    if mode=='forged_cookie':identity.client.cookies.set(auth.COOKIE_NAME,'FICTIONAL-INVALID-COOKIE')
    response=identity.client.get('/api/auth/me'+('?role=admin&department=IT' if mode=='query' else ''),headers=headers)
    assert response.status_code==401

def test_server_binding_beats_headers_and_query(identity):
    identity.login();response=identity.client.get('/api/auth/me?role=admin',headers={'X-Role':'admin','X-Faculty-ID':OTHER})
    data=response.json()['user']
    if data['role']!='faculty' or data['faculty_id']!=FACULTY:pytest.fail('Server identity binding was not retained')
    assert identity.client.get('/api/auth/users',headers={'X-Role':'admin'}).status_code==403

@pytest.mark.parametrize('mode',['expired','disabled','logout'])
def test_credential_lifecycle_rejects_old_session(identity,mode):
    headers=identity.login()
    if mode=='logout':assert identity.client.post('/api/auth/logout',headers=headers).status_code==204
    else:
        with Session(identity.engine) as db,db.begin():
            if mode=='expired':db.scalar(select(LoginSession)).expires_at=now()-timedelta(seconds=1)
            else:db.scalar(select(User).where(User.role=='faculty')).is_active=False
    assert identity.client.get('/api/auth/me').status_code==401

def test_csrf_cannot_be_replaced_by_administrator_header(identity):
    identity.login();response=identity.client.post('/api/auth/logout',headers={'Origin':ORIGIN,'X-Role':'admin','X-CSRF-Token':'FICTIONAL-FORGED'})
    assert response.status_code==403 and identity.client.get('/api/auth/me').status_code==200

def test_real_administrator_is_not_institutional_chair_or_optimizer(identity):
    identity.login('admin@fictional.invalid')
    assert identity.client.get('/api/auth/users').status_code==200
    assert chairs.institutional_chair_directory() is None and applications.institutional_application_directory() is None and runs.configured_service() is None
    response=identity.client.get('/api/chair-reviews',headers={'X-Role':'department_chair','X-Department-ID':'FICTIONAL-CLAIM'})
    assert response.status_code==503

def test_profile_cannot_self_promote_an_account(identity):
    headers=identity.login();data=identity.client.get('/api/auth/me').json()['user']
    response=identity.client.patch('/api/auth/users/'+data['id'],headers=headers,json={'role':'admin'})
    assert response.status_code==403

def test_login_rotation_revokes_prior_cookie(identity):
    identity.login();old=identity.client.cookies.get(auth.COOKIE_NAME);identity.login()
    if old==identity.client.cookies.get(auth.COOKIE_NAME):pytest.fail('Session rotation did not occur; cookies withheld')
    identity.client.cookies.clear();identity.client.cookies.set(auth.COOKIE_NAME,old)
    assert identity.client.get('/api/auth/me').status_code==401

@pytest.mark.parametrize('change',['password','role'])
def test_administrator_account_change_revokes_existing_session(identity,change):
    identity.login();old=identity.client.cookies.get(auth.COOKIE_NAME)
    with Session(identity.engine) as db:target=str(db.scalar(select(User.id).where(User.role=='faculty')))
    identity.client.cookies.clear();headers=identity.login('admin@fictional.invalid')
    update={'password':secrets.token_urlsafe(24)} if change=='password' else {'role':'admin','faculty_id':None}
    response=identity.client.patch('/api/auth/users/'+target,headers=headers,json=update)
    if response.status_code!=200:pytest.fail('Fictional administrator account update failed; response withheld')
    identity.client.cookies.clear();identity.client.cookies.set(auth.COOKIE_NAME,old)
    assert identity.client.get('/api/auth/me').status_code==401

@pytest.mark.parametrize('operation',['capabilities','admission','recovery'])
def test_authenticated_administrator_cannot_activate_bound_runs(identity,operation):
    headers=identity.login('admin@fictional.invalid');headers.update({'X-Role':'department_chair','X-Department-ID':'FICTIONAL-CLAIM'})
    if operation=='capabilities':
        response=identity.client.get('/api/ga/bound-runs/capabilities',headers=headers)
        assert response.status_code==200 and not response.json()['available'] and not response.json()['admin_implies_chair']
    elif operation=='admission':
        response=identity.client.post('/api/ga/bound-runs',headers=headers,json={'department_id':FACULTY,'request_id':OTHER,'catalog_reference':'FICTIONAL-CATALOG'})
        assert response.status_code==503
    else:
        assert identity.client.post('/api/ga/bound-runs/'+FACULTY+'/resume',headers=headers).status_code==503
