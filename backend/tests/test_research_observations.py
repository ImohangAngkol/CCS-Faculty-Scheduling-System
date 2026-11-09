"""Fictional-only SELECT projection qualification; use owned snapshot runner."""
import hashlib
import json
import random
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from services.ga_worker_contract import fictional_source
try:fictional_source()
except ValueError:pytest.skip('Owned fictional source required',allow_module_level=True)
from tests.test_research_bridge import fixture,admit,until,reopen,http_fixture,client_for
from tests.trusted_run_support import PRINCIPAL,OTHER,DEPT
from services.preference_authorization import PreferencePrincipal
from services.ga_research_observation import Observer,configured_observer
from services.ga_run_authority import RunError
from routers.research_observations import create_app


def files(b):
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in b.worker.storage.root.iterdir() if p.is_file()}


def test_created_missing_metrics_durable_read_only(fixture,monkeypatch):
    b,_=fixture();run=admit(b);o=Observer(b);before=files(b);rng=random.getstate()
    for name in ['observe','telemetry','qualified_result','start','stop','compare_best']:
        monkeypatch.setattr(b,name,lambda *a:pytest.fail('Read attempted mutable/execution path'))
    for name in ['transaction','connection']:
        monkeypatch.setattr(b.worker.storage,name,lambda *a:pytest.fail('Read opened write-capable connection'))
    a=o.detail(PRINCIPAL,run)
    assert a['overview']['state']=='CREATED' and a['overview']['best_so_far_fitness'] is None
    assert a['fitness']=={'availability':'UNAVAILABLE_NOT_RECORDED','points':[]}
    assert a['overview']['context_qualification']=='UNVERIFIED_NOT_CONSUMED'
    assert o.listing(PRINCIPAL)['items']==[a['overview']]
    assert files(b)==before and configured_observer() is None and random.getstate()==rng


@pytest.mark.parametrize('sql',["CREATE TABLE forbidden(x)","DELETE FROM research_events","PRAGMA user_version=2","ATTACH DATABASE ':memory:' AS other","INSERT INTO research_meta SELECT * FROM research_meta"])
def test_server_handle_rejects_writes(fixture,sql):
    b,_=fixture();admit(b);before=files(b)
    with pytest.raises(RunError,match='STORAGE_UNAVAILABLE'):
        with Observer(b).snapshot(PRINCIPAL) as db:
            assert db.execute('PRAGMA query_only').fetchone()[0]==1
            db.execute(sql)
    assert files(b)==before


@pytest.mark.parametrize('principal',[None,PreferencePrincipal('admin',user_id=OTHER),PreferencePrincipal('chair',user_id=OTHER),PreferencePrincipal('faculty',user_id=OTHER)])
def test_unscoped_roles_cannot_read(fixture,principal):
    b,_=fixture();run=admit(b);before=files(b)
    with pytest.raises(RunError):Observer(b).listing(principal)
    with pytest.raises(RunError):Observer(b).detail(principal,run)
    assert files(b)==before


@pytest.mark.parametrize('offset,limit',[(-1,1),(0,0),(0,11),(1025,1),(True,1)])
def test_page_bounds(fixture,offset,limit):
    b,_=fixture()
    with pytest.raises(RunError):Observer(b).listing(PRINCIPAL,offset,limit)


def test_pagination_order_concurrency_and_restart(fixture):
    b,_=fixture();runs=[admit(b) for _ in range(3)];o=Observer(b)
    with b.worker.storage.transaction() as db:
        for n in range(70):b.ledger.append(db,runs[0],dict(run_id=runs[0],observed_at=float(n),reason='FICTIONAL-OBSERVATION'))
    before=files(b)
    allrows=o.listing(PRINCIPAL);first=o.listing(PRINCIPAL,0,1);second=o.listing(PRINCIPAL,1,1)
    assert allrows['total']==3 and first['next_offset']==1 and first['items']!=second['items']
    page=o.telemetry(PRINCIPAL,runs[0]);after=o.telemetry(PRINCIPAL,runs[0],page['next_after'])
    events=page['items']+after['items'];assert len(events)==page['total'] and [e['sequence'] for e in events]==list(range(1,len(events)+1))
    with ThreadPoolExecutor(4) as pool:rows=list(pool.map(lambda _:o.detail(PRINCIPAL,runs[0]),range(8)))
    assert all(r==rows[0] for r in rows) and files(b)==before
    assert Observer(reopen(b)).detail(PRINCIPAL,runs[0])==rows[0]


@pytest.mark.parametrize('kind',['context','events','proofless-completion','scope'])
def test_corruption_rejected_without_repair(fixture,kind):
    b,_=fixture();run=admit(b)
    with b.worker.storage.transaction() as db:
        if kind=='context':db.execute('UPDATE research_runs SET context=? WHERE run=?',(b'{}',run))
        elif kind=='events':db.execute('DELETE FROM research_events WHERE run=?',(run,))
        elif kind=='scope':db.execute('UPDATE runs SET department=? WHERE id=?',(OTHER,run))
        else:db.execute("UPDATE workers SET state='COMPLETED' WHERE run=?",(run,))
    before=files(b)
    with pytest.raises(RunError):Observer(b).detail(PRINCIPAL,run)
    assert files(b)==before


def test_missing_run_revoked_scope_and_injected_interruption(fixture):
    b,v=fixture();run=admit(b);o=Observer(b)
    with pytest.raises(RunError):o.detail(PRINCIPAL,str(uuid4()))
    with b.worker.storage.transaction() as db:
        db.execute("UPDATE runs SET executor='fictional-expired-owner',lease=1,state='WORKER_RUNNING' WHERE id=?",(run,))
        db.execute("UPDATE workers SET state='RUNNING' WHERE run=?",(run,))
    before=files(b);d=o.detail(PRINCIPAL,run)
    assert d['overview']['state']=='INTERRUPTED' and d['overview']['state_classification']=='DERIVED'
    assert d['overview']['worker_state']=='RUNNING' and files(b)==before
    v.revoked=True
    with pytest.raises(RunError):o.detail(PRINCIPAL,run)


def test_native_verified_zero_history_restart_and_no_backfill(fixture):
    b,_=fixture(generations=1);run=admit(b);b.start(PRINCIPAL,run)
    assert until(b,run)['state']=='COMPLETED'
    o=Observer(b);before=files(b);rng=random.getstate();d=o.detail(PRINCIPAL,run)
    assert d['overview']['context_qualification']=='TRUSTED_FICTIONAL_CONSUMPTION'
    assert d['overview']['best_so_far_fitness']==0
    assert d['fitness']['availability']=='OBSERVED' and all(p['best_ever_fitness']==0 for p in d['fitness']['points'])
    assert files(b)==before and random.getstate()==rng
    assert Observer(reopen(b)).detail(PRINCIPAL,run)==d
    # Projection exports no chromosome, credentials, raw receipt or private key.
    raw=json.dumps(d).lower()
    assert all(k not in raw for k in ['csrf_token','password','signature','schedule_entries','faculty_name'])


def test_http_sessions_authorization_ids_get_only_and_no_mutation(http_fixture):
    import database
    from services import auth_service
    f=http_fixture;o=Observer(f.bridge)
    def app(observer=o):
        a=create_app(observer);old=f.app()
        a.dependency_overrides.update(old.dependency_overrides);return a
    with client_for(app()) as c:
        assert c.get('/api/research/observations/runs',headers={'X-Role':'admin'}).status_code==401
        f.login(c);run=admit(f.bridge);before=files(f.bridge)
        for path in ['capabilities','runs','runs/'+run,'runs/'+run+'/telemetry']:
            r=c.get('/api/research/observations/'+path);assert r.status_code==200,r.text
            assert r.headers['cache-control']=='no-store'
        assert c.get('/api/research/observations/runs/not-a-uuid').status_code==422
        assert c.get('/api/research/observations/runs?limit=11').status_code==422
        assert c.post('/api/research/observations/runs').status_code==405
        assert c.post('/api/research/ga/runs').status_code==404
        assert files(f.bridge)==before
    with client_for(app()) as c:
        f.login(c,'unscoped');assert c.get('/api/research/observations/runs/'+run,headers={'X-Department-ID':DEPT}).status_code==403
    with client_for(app(None)) as c:
        f.login(c);assert c.get('/api/research/observations/capabilities').status_code==503


def test_main_registers_only_unconfigured_read_routes():
    from main import app
    paths={p:set(methods) for p,methods in app.openapi()['paths'].items() if p.startswith('/api/research/')}
    assert len(paths)==4 and all(m=={'get'} for m in paths.values())
    assert configured_observer() is None
