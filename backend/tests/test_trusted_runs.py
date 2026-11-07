"""Real U5H execution/owned temporary SQLite; FICTIONAL independent authority."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from sqlalchemy.engine import Engine
ORIGINAL_CONNECT=Engine.connect
import pytest
from fastapi import FastAPI,HTTPException
from fastapi.testclient import TestClient
from services.ga_owned_store import Store
from services.ga_trusted_runs import Coordinator,configured_service
from services.ga_run_authority import Context,RunError,verify
from services.preference_authorization import current_principal,PreferencePrincipal
from tests.trusted_run_support import *

@pytest.fixture
def env(monkeypatch):
    from sqlalchemy.engine import Engine
    monkeypatch.setattr(Engine,'connect',lambda *_a,**_k:pytest.fail('Institutional database forbidden'))
    from services import chromosome_service,ga_checkpoint_service
    def forbidden(*_a,**_k):pytest.fail('Legacy persistence forbidden')
    monkeypatch.setattr(chromosome_service,'save_best_if_better',forbidden)
    monkeypatch.setattr(ga_checkpoint_service,'save_checkpoint',forbidden)
    clock=[100000.0];now=lambda:clock[0]
    store=Store.create(clock=now);authority=FictionalAuthority(now);source=FictionalSource()
    service=Coordinator(store,authority,source,clock=now)
    return service,store,authority,source,clock

def admit(s,key=None):return s.admit(PRINCIPAL,DEPT,key or str(uuid4()),CATALOG)['run_id']
def paused(s):
    run=admit(s);s.command(PRINCIPAL,run,'pause');assert s.execute(PRINCIPAL,run)['state']=='PAUSED'
    return run

def test_server_identity_and_frozen_bindings(env):
    s,store,authority,source,_=env;key=str(uuid4());run=admit(s,key);public=s.status(PRINCIPAL,run)
    assert run!=key and public['owner_id']==ACTOR and public['department_id']==DEPT
    assert public['publication'] is False and configured_service() is None
    assert source.calls==1 and public['state']=='ADMITTED'
    with store.connection() as db:
        row=store.row(db,run);assert row['persistence']==s.persistence and row['initial_rng']
    assert s.admit(PRINCIPAL,DEPT,key,CATALOG)['run_id']==run and source.calls==1
    with pytest.raises(RunError,match='IDEMPOTENCY'):s.admit(PRINCIPAL,DEPT,key,'another-catalog')

@pytest.mark.parametrize('role',['admin','chair','faculty'])
def test_account_role_alone_never_grants_optimization(env,role):
    s,store,*_=env;s.authority=None
    with pytest.raises(RunError,match='AUTHORITY_UNAVAILABLE'):s.admit(PreferencePrincipal(role,user_id=ACTOR),DEPT,str(uuid4()),CATALOG)
    with store.connection() as db:assert db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]==0

@pytest.mark.parametrize('change',['scope','expired','future','capability','digest','policy'])
def test_bad_authority_grants_rejected(env,change):
    s,_,a,_,_=env;c=Context(ACTOR,DEPT,'admit');valid=a.authorize(c)
    changes={'scope':{'department_id':OTHER_DEPT},'expired':{'expires_at':1},'future':{'issued_at':200000},
             'capability':{'capability':'department_chair_review'},'digest':{'context_digest':'0'*64},'policy':{'policy_digest':'bad'}}
    a.authorize=lambda c:replace(valid,**changes[change])
    with pytest.raises(RunError,match='AUTHORITY_REQUIRED'):verify(a,c,s.clock)

def test_concurrent_idempotent_admission_captures_once(env):
    s,store,a,source,_=env;key=str(uuid4())
    second=Coordinator(store,a,source,clock=s.clock)
    with ThreadPoolExecutor(2) as pool:runs=list(pool.map(lambda svc:admit(svc,key),[s,second]))
    assert len(set(runs))==1 and source.calls==1

@pytest.mark.parametrize('action',['status','pause','stop','checkpoint','result','execute','resume'])
def test_all_run_operations_reject_other_owner(env,action):
    s,*_=env;run=admit(s);other=PreferencePrincipal('admin',user_id=OTHER)
    with pytest.raises(RunError,match='NOT_FOUND'):
        if action in {'pause','stop'}:s.command(other,run,action)
        elif action in {'execute','resume'}:s.execute(other,run,resume=action=='resume')
        else:getattr(s,action)(other,run)

def test_cross_department_and_missing_identity_fail_closed(env):
    s,*_=env
    with pytest.raises(RunError,match='AUTHORITY_REQUIRED'):s.admit(PRINCIPAL,OTHER_DEPT,str(uuid4()),CATALOG)
    with pytest.raises(RunError,match='AUTHENTICATION_REQUIRED'):s.admit(PreferencePrincipal('admin'),DEPT,str(uuid4()),CATALOG)

def test_actual_optimizer_durable_pause_restart_resume_rng_parity(env):
    s,store,a,source,_=env;source.generations=1;run=admit(s)
    with store.connection() as db:oracle=s._session(store.row(db,run))
    expected=oracle.run();expected_rng=oracle.runtime.random.getstate()
    s.command(PRINCIPAL,run,'pause');state=s.execute(PRINCIPAL,run)
    assert state['state']=='PAUSED' and state['checkpoint_sequence']==1
    raw=s.checkpoint(PRINCIPAL,run);assert hashlib.sha256(raw).hexdigest()==state['checkpoint_fingerprint']
    reopened=Store(store.root,store.store_id,clock=s.clock)
    restarted=Coordinator(reopened,a,source,clock=s.clock)
    with reopened.connection() as db:
        row=reopened.row(db,run);continuation=restarted._session(row,raw)
    expected_continuation=continuation.run();assert continuation.runtime.random.getstate()==expected_rng
    assert restarted.execute(PRINCIPAL,run,resume=True)['state']=='COMPLETED'
    actual=restarted.result(PRINCIPAL,run)
    for key in ['schedule','best_fitness','history','fitness_breakdown','faculty_analysis']:
        assert actual[key]==expected[key]==expected_continuation[key]
    assert actual['best_fitness']==0 and not actual['saved_best_updated']
    assert restarted.status(PRINCIPAL,run)['receipt']['verification_status']=='VERIFIED'

def test_fresh_process_can_restore_checkpoint_and_finish(env):
    s,store,*_=env;run=paused(s)
    code='''import json,sys
from services.ga_owned_store import Store
from services.ga_trusted_runs import Coordinator
from tests.trusted_run_support import *
clock=lambda:100000.0
s=Coordinator(Store(sys.argv[1],sys.argv[2],clock=clock),FictionalAuthority(clock),FictionalSource(),clock=clock)
r=s.execute(PRINCIPAL,sys.argv[3],resume=True)
assert r['state']=='COMPLETED' and r['receipt']['verification_status']=='VERIFIED'
print('FRESH_PROCESS_RECOVERY_VERIFIED')
'''
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE'}
    result=subprocess.run([sys.executable,'-B','-c',code,str(store.root),store.store_id,run],
        env={k:v for k,v in os.environ.items() if k.upper() in allowed},capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stderr
    assert 'FRESH_PROCESS_RECOVERY_VERIFIED' in result.stdout and s.status(PRINCIPAL,run)['state']=='COMPLETED'

def test_process_death_rolls_back_checkpoint_tip_together(env):
    s,store,*_=env;run=paused(s);before=s.checkpoint(PRINCIPAL,run)
    code='''import os,sys
from services.ga_owned_store import Store
s=Store(sys.argv[1],sys.argv[2],clock=lambda:100000.0)
with s.transaction() as db:
 db.execute("UPDATE runs SET tip='uncommitted',sequence=2 WHERE id=?",(sys.argv[3],))
 db.execute('INSERT INTO checkpoints VALUES(?,?,?,?,?)',(sys.argv[3],2,'uncommitted','old',b'interrupted'))
 os._exit(23)
'''
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE'}
    child=subprocess.run([sys.executable,'-B','-c',code,str(store.root),store.store_id,run],env={k:v for k,v in os.environ.items() if k.upper() in allowed},capture_output=True,timeout=30)
    assert child.returncode==23
    assert s.checkpoint(PRINCIPAL,run)==before and s.status(PRINCIPAL,run)['checkpoint_sequence']==1

@pytest.mark.parametrize('column,value',[('config_hash','0'*64),('optimizer','0'*64),('persistence','0'*64),('bundle_hash','0'*64)])
def test_stale_bindings_cannot_claim_or_resume(env,column,value):
    s,store,*_=env;run=paused(s)
    with store.transaction() as db:db.execute('UPDATE runs SET '+column+'=? WHERE id=?',(value,run))
    with pytest.raises(ValueError):s.execute(PRINCIPAL,run,resume=True)
    with store.connection() as db:assert store.row(db,run)['executor'] is None

def test_corruption_lineage_and_cross_run_reuse_fail_closed(env):
    s,store,*_=env;first=paused(s);second=paused(s)
    with store.connection() as db:a=store.row(db,first);b=store.row(db,second)
    with pytest.raises(ValueError):s._session(b,s.checkpoint(PRINCIPAL,first))
    with store.transaction() as db:db.execute("UPDATE checkpoints SET raw=? WHERE run=?",(b'corrupted',first))
    with pytest.raises(RunError,match='INTEGRITY'):s.execute(PRINCIPAL,first,resume=True)
    assert s.status(PRINCIPAL,second)['state']=='PAUSED'

def test_missing_checkpoint_and_terminal_rerun_rejected(env):
    s,*_=env;run=admit(s)
    with pytest.raises(RunError,match='CHECKPOINT_MISSING'):s.execute(PRINCIPAL,run,resume=True)
    with pytest.raises(RunError,match='CHECKPOINT_MISSING'):s.checkpoint(PRINCIPAL,run)
    s.execute(PRINCIPAL,run)
    with pytest.raises(RunError,match='RECOVERY_REQUIRED'):s.execute(PRINCIPAL,run)

def test_revocation_policy_change_and_action_denial(env):
    s,_,a,*_=env;run=paused(s);a.revoked=True
    with pytest.raises(RunError,match='AUTHORITY_REQUIRED'):s.execute(PRINCIPAL,run,resume=True)
    a.revoked=False;a.policy='f'*64
    with pytest.raises(RunError,match='POLICY_CHANGED'):s.status(PRINCIPAL,run)
    a.policy='e'*64;a.denied.add('checkpoint')
    with pytest.raises(RunError,match='AUTHORITY_REQUIRED'):s.checkpoint(PRINCIPAL,run)

def test_changed_external_source_never_replaces_frozen_bundle(env):
    s,store,_,source,_=env;run=paused(s);fp=s.status(PRINCIPAL,run)['bundle_fingerprint'];source.offset=100
    s.execute(PRINCIPAL,run,resume=True)
    assert source.calls==1 and s.status(PRINCIPAL,run)['bundle_fingerprint']==fp
    assert s.status(PRINCIPAL,run)['receipt']['academic_source_verification']=='UNVERIFIED_U5G_CAPTURE_ONLY'

def test_expired_execution_lease_fences_old_executor(env):
    s,store,_,_,clock=env;run=paused(s);row=s.inspect(PRINCIPAL,run)
    owner='fictional-first';_,old=store.claim(run,owner,recover=True,expected_tip=row['tip'],expected_sequence=1)
    with pytest.raises(RunError,match='EXECUTION_ACTIVE'):s.execute(PRINCIPAL,run,resume=True)
    clock[0]+=121
    assert s.status(PRINCIPAL,run)['state']=='INTERRUPTED'
    assert s.execute(PRINCIPAL,run,resume=True)['state']=='COMPLETED'
    with store.connection() as db:
        with pytest.raises(RunError,match='OWNERSHIP_LOST'):store.fenced(db,run,owner,old)

def test_failed_execution_releases_only_owned_claim(env):
    s,store,*_=env;run=admit(s)
    def fail(*_):raise RuntimeError('Fictional interrupted observer')
    with pytest.raises(RuntimeError,match='Fictional'):s.execute(PRINCIPAL,run,observer=fail)
    assert s.status(PRINCIPAL,run)['state']=='INTERRUPTED'
    with store.connection() as db:assert store.row(db,run)['executor'] is None
    with pytest.raises(RunError,match='CHECKPOINT_MISSING'):s.execute(PRINCIPAL,run,resume=True)

def test_commit_time_authority_failure_rolls_back_checkpoint(env):
    s,store,a,*_=env;run=admit(s);s.command(PRINCIPAL,run,'pause')
    original=store.checkpoint
    def deny(*args,**kwargs):
        old=kwargs['before_commit']
        def check():a.revoked=True;old()
        kwargs['before_commit']=check
        return original(*args,**kwargs)
    store.checkpoint=deny
    with pytest.raises(RunError,match='AUTHORITY_REQUIRED'):s.execute(PRINCIPAL,run)
    with store.connection() as db:
        assert store.row(db,run)['tip'] is None
        assert db.execute('SELECT COUNT(*) FROM checkpoints').fetchone()[0]==0

def test_retention_is_bounded_and_never_deletes_artifacts(env):
    s,store,_,_,clock=env;run=paused(s);clock[0]+=7*86400+1
    with pytest.raises(RunError,match='RETENTION_EXPIRED'):s.status(PRINCIPAL,run)
    with store.connection() as db:assert db.execute('SELECT COUNT(*) FROM checkpoints').fetchone()[0]==1
    with pytest.raises(RunError,match='IDENTITY_INVALID'):Store(store.root,store.store_id,max_runs=999)

def test_capacity_failure_rolls_back_admission(env):
    s,store,*_=env
    def full(*_):raise RunError('GA_STORE_RETENTION_LIMIT')
    store.capacity=full
    with pytest.raises(RunError,match='RETENTION_LIMIT'):admit(s)
    with store.connection() as db:assert db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]==0

def test_storage_identity_and_schema_version_checks(env):
    s,store,*_=env
    with pytest.raises(RunError,match='IDENTITY_INVALID'):Store(store.root,str(uuid4()))
    with store.connection() as db:db.execute('PRAGMA user_version=99')
    with pytest.raises(RunError,match='VERSION_UNSUPPORTED'):
        with store.connection():pass

def test_http_protected_versioned_routes_and_real_store(env):
    from routers.ga_trusted_runs import router,service
    s,*_=env;app=FastAPI();app.include_router(router)
    def absent():raise HTTPException(401,'Fictional sign-in required')
    app.dependency_overrides[current_principal]=absent
    with TestClient(app) as client:
        assert client.get('/api/ga/bound-runs/capabilities').status_code==401
        app.dependency_overrides[current_principal]=lambda:PRINCIPAL
        assert client.get('/api/ga/bound-runs/capabilities').json()['available'] is False
        body=dict(department_id=DEPT,request_id=str(uuid4()),catalog_reference=CATALOG)
        assert client.post('/api/ga/bound-runs',json=body).status_code==503
        app.dependency_overrides[service]=lambda:s
        assert client.post('/api/ga/bound-runs',json=dict(body,role='chair')).status_code==422
        response=client.post('/api/ga/bound-runs',json=body);assert response.status_code==200
        run=response.json()['run_id'];path='/api/ga/bound-runs/'+run
        assert client.post(path+'/execute',json={'role':'chair','department_id':OTHER_DEPT}).status_code==422
        assert client.post(path+'/pause').status_code==200
        assert client.post(path+'/execute').json()['state']=='PAUSED'
        assert client.get(path+'/checkpoint').headers['cache-control']=='no-store'
        assert client.post(path+'/resume').json()['state']=='COMPLETED'
        assert client.get(path+'/result').json()['best_fitness']==0
        app.dependency_overrides[current_principal]=lambda:PreferencePrincipal('admin',user_id=OTHER)
        assert client.get(path).status_code==404

def test_parallel_runs_have_distinct_namespaces_and_rng_isolation(env):
    import random
    s,store,a,source,_=env;first=admit(s);second=admit(s);before=random.getstate()
    other=Coordinator(store,a,source,clock=s.clock)
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda pair:pair[0].execute(PRINCIPAL,pair[1]),[(s,first),(other,second)]))
    assert {r['run_id'] for r in results}=={first,second} and all(r['state']=='COMPLETED' for r in results)
    assert random.getstate()==before
    assert s.result(PRINCIPAL,first)['best_fitness']==s.result(PRINCIPAL,second)['best_fitness']==0

def test_stop_committed_during_checkpoint_is_not_lost(env):
    s,store,*_=env;run=admit(s);s.command(PRINCIPAL,run,'pause');original=store.checkpoint
    def stop_before_commit(*args,**kwargs):
        s.command(PRINCIPAL,run,'stop');return original(*args,**kwargs)
    store.checkpoint=stop_before_commit
    result=s.execute(PRINCIPAL,run)
    assert result['state']=='STOPPED' and result['checkpoint_sequence']==1
    with pytest.raises(RunError,match='TERMINAL'):s.execute(PRINCIPAL,run,resume=True)

def test_claim_time_authority_failure_leaves_run_unclaimed(env):
    s,store,a,*_=env;run=admit(s);original=store.claim
    def revoke(*args,**kwargs):
        old=kwargs['before_commit']
        def check():a.revoked=True;old()
        kwargs['before_commit']=check;return original(*args,**kwargs)
    store.claim=revoke
    with pytest.raises(RunError,match='AUTHORITY_REQUIRED'):s.execute(PRINCIPAL,run)
    with store.connection() as db:
        row=store.row(db,run);assert row['executor'] is None and row['state']=='ADMITTED' and row['fence']==0

def test_historical_tip_cannot_replace_current_lineage(env):
    s,store,*_=env;run=paused(s);row=s.inspect(PRINCIPAL,run)
    with store.transaction() as db:db.execute('UPDATE checkpoints SET sequence=2 WHERE run=?',(run,))
    with pytest.raises(RunError,match='INTEGRITY'):s.checkpoint(PRINCIPAL,run)

def test_missing_or_bad_capture_cannot_admit(env):
    s,store,_,source,_=env;s.source=None
    with pytest.raises(RunError,match='CAPTURE_SOURCE_UNAVAILABLE'):admit(s)
    s.source=source;original=source.capture
    source.capture=lambda *args:replace(original(*args),department_id=OTHER_DEPT)
    with pytest.raises(RunError,match='CAPTURE_SCOPE_MISMATCH'):admit(s)
    with store.connection() as db:assert db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]==0

def test_storage_missing_file_never_creates_a_replacement(env):
    s,store,*_=env;dbpath=store.root/'records.sqlite3'
    # Rename an owned fictional database only, retain the original bytes.
    dbpath.rename(store.root/'retained-fixture.sqlite3')
    with pytest.raises(RunError):
        with store.connection():pass
    assert not dbpath.exists() and (store.root/'retained-fixture.sqlite3').is_file()

def test_authority_guard_failure_is_sanitized(env):
    s,_,a,*_=env
    def broken(_):raise RuntimeError('FICTIONAL_PRIVATE_PROVIDER_DETAIL')
    a.guard=broken
    with pytest.raises(RunError,match='AUTHORITY_UNAVAILABLE') as error:admit(s)
    assert 'FICTIONAL_PRIVATE_PROVIDER_DETAIL' not in str(error.value)

def test_real_session_csrf_origin_and_owned_loopback_http(monkeypatch):
    """Real existing session verification, no principal override; fictional issuer."""
    from datetime import datetime,timedelta,timezone
    import secrets,socket,threading,time
    from urllib.request import Request,urlopen
    from uuid import UUID
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as DatabaseSession
    from identity_models import Base,User,LoginSession
    from services import auth_service as auth
    from routers.ga_trusted_runs import router,service
    import uvicorn
    store=Store.create();target=store.root/'fictional-identity.sqlite3'
    def restricted(engine,*args,**kwargs):
        assert engine.dialect.name=='sqlite' and Path(engine.url.database).resolve()==target
        return ORIGINAL_CONNECT(engine,*args,**kwargs)
    monkeypatch.setattr(Engine,'connect',restricted)
    engine=create_engine('sqlite:///'+str(target),connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine)
    token=secrets.token_urlsafe(24);csrf=secrets.token_urlsafe(24)
    with DatabaseSession(engine) as db,db.begin():
        db.add(User(id=UUID(ACTOR),username='fictional-optimizer@test.invalid',role='admin',password_hash='UNUSED_NO_LOGIN',is_active=True))
        db.flush()
        db.add(LoginSession(user_id=UUID(ACTOR),token_hash=auth.token_hash(token),csrf_token=csrf,expires_at=datetime.now(timezone.utc)+timedelta(hours=1)))
    def isolated_db():
        with DatabaseSession(engine) as db:yield db
    coordinator=Coordinator(store,FictionalAuthority(),FictionalSource())
    app=FastAPI();app.include_router(router)
    app.dependency_overrides[auth.authenticated_db]=isolated_db
    app.dependency_overrides[service]=lambda:coordinator
    monkeypatch.setenv('AUTH_ALLOWED_ORIGINS','http://localhost:5173')
    try:
        with TestClient(app) as client:
            assert client.get('/api/ga/bound-runs/capabilities').status_code==401
            client.cookies.set(auth.COOKIE_NAME,token)
            body=dict(department_id=DEPT,request_id=str(uuid4()),catalog_reference=CATALOG)
            assert client.post('/api/ga/bound-runs',json=body).status_code==403
            assert client.post('/api/ga/bound-runs',json=body,headers={'Origin':'http://localhost:5173'}).status_code==403
            headers={'Origin':'http://localhost:5173','X-CSRF-Token':csrf,'X-Role':'chair','X-User-ID':OTHER}
            response=client.post('/api/ga/bound-runs',json=body,headers=headers)
            assert response.status_code==200 and response.json()['owner_id']==ACTOR
            run=response.json()['run_id']
        listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM);listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
        server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,lifespan='off',access_log=False,log_level='critical'))
        worker=threading.Thread(target=lambda:server.run(sockets=[listener]),daemon=True);worker.start()
        try:
            deadline=time.monotonic()+10
            while not server.started and worker.is_alive() and time.monotonic()<deadline:time.sleep(.02)
            assert server.started
            request=Request(f'http://127.0.0.1:{port}/api/ga/bound-runs/{run}',headers={'Cookie':auth.COOKIE_NAME+'='+token})
            with urlopen(request,timeout=5) as response:assert json.load(response)['owner_id']==ACTOR
        finally:
            server.should_exit=True;worker.join(10);listener.close();assert not worker.is_alive()
    finally:engine.dispose()

@pytest.mark.parametrize('limit',[0,-1,True,1.5])
def test_invalid_store_limits_rejected_before_directory_creation(limit):
    with pytest.raises(RunError,match='LIMITS_INVALID'):Store.create(max_runs=limit)

def test_actual_retention_capacity_and_run_count_limits():
    tiny=Store.create(max_bytes=1)
    s=Coordinator(tiny,FictionalAuthority(),FictionalSource())
    with pytest.raises(RunError,match='RETENTION_LIMIT'):admit(s)
    with tiny.connection() as db:assert db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]==0
    single=Store.create(max_runs=1)
    s=Coordinator(single,FictionalAuthority(),FictionalSource());admit(s)
    with pytest.raises(RunError,match='RETENTION_LIMIT'):admit(s)
    with single.connection() as db:assert db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]==1
