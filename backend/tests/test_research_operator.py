"""Owned fictional tests only; preserve original K/L/H engines."""
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
import subprocess
import sys
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from services.ga_worker_contract import fictional_source
try:fictional_source()
except ValueError:pytest.skip('Owned fictional snapshot required',allow_module_level=True)
from services.ga_research_operator import Operator
from services.ga_run_authority import RunError
from routers.research_operator import create_app
from tests.test_research_bridge import fixture,http_fixture,client_for
from tests.trusted_run_support import PRINCIPAL,OTHER
from services.preference_authorization import PreferencePrincipal


def diagnostic(b,run,label):
    with b.worker.storage.connection() as db:
        w=db.execute('SELECT state,reason,generation,sequence FROM workers WHERE run=?',(run,)).fetchone()
        p=db.execute('SELECT status,observation FROM l_processes WHERE run=?',(run,)).fetchall()
        base=db.execute('SELECT lease,executor FROM runs WHERE id=?',(run,)).fetchone()
    row=dict(worker=dict(w),lease_expired=bool(base['executor'] and base['lease']<=time.time()),process_status=[x['status'] for x in p],physical_observations=[json.loads(x['observation']) if x['observation'] else None for x in p],scope='Public fictional worker state/physical cleanup only; no bundles/keys/authentication artifacts')
    folder=os.environ.get('U5PE_EVIDENCE')
    if folder:
        with (Path(folder)/(label+'.json')).open('x',encoding='utf-8') as f:json.dump(row,f,indent=2);f.write('\n')


def finished(b,run):
    # The older helper polls full bridge reconstruction and accepts derived
    # INTERRUPTED as an outcome. Neither is appropriate for a successful native
    # Stop assertion: heavy reads also contend with the original heartbeat.
    # Join only our known supervisor, within the same existing 90-second bound.
    thread=b.worker.threads[run];thread.join(90)
    assert not thread.is_alive(),'Owned supervisor did not finish within test bound'
    with b.worker.storage.connection() as db:
        row=db.execute('SELECT executor,lease FROM runs WHERE id=?',(run,)).fetchone()
        assert row['executor'] is None and row['lease']==0,'Ownership not released; termination cannot be claimed'


def test_factory_not_in_production_and_GET_routes_unchanged():
    from main import app
    assert not any(p.startswith('/api/research/operator') for p in app.openapi()['paths'])
    routes=create_app().openapi()['paths']
    observed=[p for p in routes if p.startswith('/api/research/observations')]
    assert len(observed)==4 and all(set(routes[p])=={'get'} for p in observed)
    assert not any(any(x in p for x in ['resume','pause','restore','compare-research-best']) for p in routes)
    with client_for(create_app()) as c:
        assert c.post('/api/auth/login',json={'username':'fictional','password':'fictional'}).status_code==503


@pytest.mark.parametrize('field',['department','role','limits','context','fitness','bundle'])
def test_real_auth_csrf_and_untrusted_metadata(http_fixture,field):
    f=http_fixture;o=Operator(f.bridge,initialize=True);a=create_app(o);a.dependency_overrides.update(f.app().dependency_overrides)
    with client_for(a) as c:
        assert c.post('/api/research/operator/start',json={'request_id':str(uuid4())}).status_code==401
        headers=f.login(c)
        assert c.post('/api/research/operator/start',json={'request_id':str(uuid4())}).status_code==403
        assert c.post('/api/research/operator/start',headers=headers,json={'request_id':str(uuid4()),field:'untrusted'}).status_code==422
    with client_for(a) as c:
        headers=f.login(c,'unscoped')
        assert c.post('/api/research/operator/start',headers=headers,json={'request_id':str(uuid4())}).status_code==403
    with f.bridge.worker.storage.connection() as db:assert db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]==0


def test_native_idempotent_start_concurrency_and_reconstruction(fixture):
    b,_=fixture(generations=1);o=Operator(b,initialize=True);request=str(uuid4())
    controllers=[o,Operator(b)]
    def call(i):
        try:return controllers[i].control(PRINCIPAL,request,'start')
        except RunError as e:
            assert e.code=='OPERATOR_BUSY_RETRY_SAME_REQUEST';return None
    with ThreadPoolExecutor(2) as pool:results=[d for d in pool.map(call,range(2)) if d is not None]
    assert len({x['run_id'] for x in results})==1
    run=results[0]['run_id'];finished(b,run);diagnostic(b,run,'native-idempotency')
    with b.worker.storage.connection() as db:before=db.execute('SELECT COUNT(*) FROM l_processes').fetchone()[0]
    second=Operator(b);d=second.control(PRINCIPAL,request,'start')
    assert d['replayed'] and d['confirmation']=='DURABLE_TERMINAL_VERIFIED'
    with b.worker.storage.connection() as db:assert db.execute('SELECT COUNT(*) FROM l_processes').fetchone()[0]==before
    assert before==2  # Original H initialization then one generation, not duplicate workers.


def test_created_stop_replay_cross_owner_and_binding(fixture):
    b,_=fixture();o=Operator(b,initialize=True);run=b.admit(PRINCIPAL,str(uuid4()))['run_id'];request=str(uuid4())
    with pytest.raises(RunError):o.control(PreferencePrincipal('admin',user_id=OTHER),request,'stop',run)
    d=o.control(PRINCIPAL,request,'stop',run)
    assert d['observation']['overview']['state']=='STOPPED' and d['confirmation']=='DURABLE_TERMINAL_VERIFIED'
    assert o.control(PRINCIPAL,request,'stop',run)['replayed']
    with pytest.raises(RunError):o.control(PRINCIPAL,request,'start')
    assert not b.worker.threads


def test_native_stop_during_checkpoint_publication(fixture,monkeypatch):
    b,_=fixture(generations=1);o=Operator(b,initialize=True);entered=threading.Event();release=threading.Event();original=b.worker.store.save
    def gate(*a,**k):
        entered.set()
        if not release.wait(15):raise RuntimeError('Owned checkpoint gate bound')
        return original(*a,**k)
    monkeypatch.setattr(b.worker.store,'save',gate)
    try:
        first=o.control(PRINCIPAL,str(uuid4()),'start');run=first['run_id']
        if not entered.wait(30):diagnostic(b,run,'checkpoint-gate-not-reached');pytest.fail('Native checkpoint gate not reached; state diagnostic retained')
        with pytest.raises(RunError,match='OBSERVATION_DEFERRED'):o.status(PRINCIPAL,run)
        assert o.runtime(PRINCIPAL,run)['fitness'] is None
        d=o.control(PRINCIPAL,str(uuid4()),'stop',run)
        assert d['confirmation']=='REQUEST_RECORDED_NOT_TERMINATION'
        assert d['runtime']['recorded_state']=='STOPPING' and d['observation'] is None
    finally:release.set()
    finished(b,run);diagnostic(b,run,'native-checkpoint-stop');assert o.status(PRINCIPAL,run)['overview']['freshness']['state']=='TERMINAL'
    with b.worker.storage.connection() as db:assert all(x[0]=='EXIT_VERIFIED' for x in db.execute('SELECT status FROM l_processes'))


def test_native_stop_during_computation(fixture):
    sentinel=subprocess.Popen([getattr(sys,'_base_executable',sys.executable),'-I','-B','-c','import time;time.sleep(60)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        b,_=fixture(generations=1);o=Operator(b,initialize=True);d=o.control(PRINCIPAL,str(uuid4()),'start');run=d['run_id'];end=time.monotonic()+20
        while time.monotonic()<end:
            with b.worker.storage.connection() as db:active=db.execute("SELECT COUNT(*) FROM l_processes WHERE status='ACTIVE'").fetchone()[0]
            if active:break
            time.sleep(.02)
        assert active
        with pytest.raises(RunError,match='OPERATOR_ACTIVE_OR_UNCERTAIN_RUN'):o.control(PRINCIPAL,str(uuid4()),'start')
        response=o.control(PRINCIPAL,str(uuid4()),'stop',run)
        if response['runtime']['recorded_state']=='STOPPED':assert response['confirmation']=='DURABLE_TERMINAL_VERIFIED'
        finished(b,run);diagnostic(b,run,'native-computation-stop');assert o.status(PRINCIPAL,run)['overview']['freshness']['state']=='TERMINAL'
        assert sentinel.poll() is None
    finally:
        if sentinel.poll() is None:sentinel.terminate()
        sentinel.wait(5)


def test_expired_window_preserves_stop_and_no_renewal(fixture):
    b,_=fixture();now=[time.time()];o=Operator(b,initialize=True,clock=lambda:now[0]);run=b.admit(PRINCIPAL,str(uuid4()))['run_id'];now[0]+=301
    assert not o.capabilities(PRINCIPAL)['start_available']
    with pytest.raises(RunError,match='WINDOW_EXPIRED'):o.control(PRINCIPAL,str(uuid4()),'start')
    assert o.control(PRINCIPAL,str(uuid4()),'stop',run)['confirmation']=='DURABLE_TERMINAL_VERIFIED'
    assert not Operator(b,clock=lambda:now[0]).capabilities(PRINCIPAL)['start_available']


@pytest.mark.parametrize('kind',['audit','meta','request','tail','deleted-request'])
def test_tampered_control_audit_rejected(fixture,kind):
    b,_=fixture();o=Operator(b,initialize=True);run=b.admit(PRINCIPAL,str(uuid4()))['run_id'];key=str(uuid4());o.control(PRINCIPAL,key,'stop',run)
    with b.worker.storage.transaction() as db:
        if kind=='tail':db.execute('DELETE FROM operator_events WHERE seq=(SELECT MAX(seq) FROM operator_events)')
        elif kind=='deleted-request':db.execute('DELETE FROM operator_requests')
        else:db.execute('UPDATE '+{'audit':'operator_events','meta':'operator_meta','request':'operator_requests'}[kind]+' SET mac=?',('0'*64,))
    with pytest.raises(RunError):o.control(PRINCIPAL,key,'stop',run)


def test_storage_failure_before_dispatch_never_acknowledges(fixture,monkeypatch):
    b,_=fixture();o=Operator(b,initialize=True)
    def fail(*a,**k):raise sqlite3.OperationalError('fictional unavailable')
    monkeypatch.setattr(o,'_record',fail)
    with pytest.raises(sqlite3.OperationalError):o.control(PRINCIPAL,str(uuid4()),'start')
    with b.worker.storage.connection() as db:assert db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]==0


def test_interrupted_request_is_not_silently_dispatched(fixture):
    b,_=fixture();o=Operator(b,initialize=True);key=str(uuid4());o._record(key,'start',None,'REQUEST')
    with pytest.raises(RunError,match='INDETERMINATE'):Operator(b).control(PRINCIPAL,key,'start')
    assert not b.worker.threads
    pending=o.request_status(PRINCIPAL,key)
    assert pending['run_id'] is None and not pending['execution_retried']


def test_readonly_request_mapping_recovers_owned_admission_without_dispatch(fixture,monkeypatch):
    from contextlib import contextmanager
    from tests.test_research_observations import files
    b,_=fixture();o=Operator(b,initialize=True);key=str(uuid4());o._record(key,'start',None,'REQUEST')
    run=b.admit(PRINCIPAL,key)['run_id'];before=files(b)
    original=o.full_observer.snapshot
    @contextmanager
    def ordered(principal):
        # Original snapshot opens SQLite first; the adapter must have acquired
        # current authority/source guards before entering it, not afterwards.
        c=b.worker.coordinator
        assert c.authority._scope.get()==(b.permit.actor,b.permit.department,b.permit.catalog)
        assert c.source._active.get() is not None
        with original(principal) as db:yield db
    monkeypatch.setattr(o.full_observer,'snapshot',ordered)
    found=o.request_status(PRINCIPAL,key)
    assert found['run_id']==run and found['phase']=='REQUEST' and found['runtime']['recorded_state']=='CREATED'
    assert found['execution_retried'] is False and files(b)==before and not b.worker.threads
    with pytest.raises(RunError):o.request_status(PreferencePrincipal('admin',user_id=OTHER),key)
    with pytest.raises(RunError):o.request_status(PRINCIPAL,str(uuid4()))


def test_request_inspection_never_opens_snapshot_while_admission_owns_lock(fixture,monkeypatch):
    b,_=fixture();o=Operator(b,initialize=True);entered=threading.Event();release=threading.Event()
    def hold():
        with b.lock:
            entered.set();assert release.wait(5)
    def forbidden(*a,**k):pytest.fail('Read transaction opened behind admission source lock')
    monkeypatch.setattr(o.full_observer,'snapshot',forbidden)
    with ThreadPoolExecutor(1) as pool:
        future=pool.submit(hold);assert entered.wait(2)
        try:
            with pytest.raises(RunError,match='OPERATOR_BUSY_RETRY_SAME_REQUEST'):o.request_status(PRINCIPAL,str(uuid4()))
            with pytest.raises(RunError) as denied:o.request_status(PreferencePrincipal('admin',user_id=OTHER),str(uuid4()))
            assert denied.value.status==403
        finally:release.set()
        future.result(5)


def test_actual_HTTP_cross_owner_stop_denied(http_fixture):
    f=http_fixture;o=Operator(f.bridge,initialize=True);run=f.bridge.admit(PRINCIPAL,str(uuid4()))['run_id'];a=create_app(o);a.dependency_overrides.update(f.app().dependency_overrides)
    with client_for(a) as c:
        headers=f.login(c,'unscoped')
        assert c.post('/api/research/operator/runs/'+run+'/stop',headers=headers,json={'request_id':str(uuid4())}).status_code==403
    assert o.status(PRINCIPAL,run)['overview']['state']=='CREATED'
