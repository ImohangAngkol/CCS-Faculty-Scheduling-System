"""New fictional-only bridge tests; execute through owned snapshot runner."""
import copy
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import random
import secrets
import threading
import time
from uuid import UUID, uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest

from services.ga_worker_contract import fictional_source, Limits
try:fictional_source()
except ValueError:pytest.skip('Owned fictional source snapshot required',allow_module_level=True)

from services.ga_research_bridge import ResearchBridge, ResearchWorker, configured_service
from services.ga_research_context import ResearchPermit, derive, ResearchComparison
from services.ga_research_ledger import MAX_EVENTS
from services.ga_run_authority import RunError, canonical, digest
from services.ga_trusted_runs import Coordinator
from services.ga_owned_store import Store
from services import saved_best_policy
from services.chromosome_service import save_best_if_better as SNAPSHOT_ORIGINAL_SAVE_BEST
from tests.bounded_worker_support import dependencies
from tests.trusted_run_support import ACTOR, DEPT, OTHER, OTHER_DEPT, CATALOG, PRINCIPAL
from services.preference_authorization import PreferencePrincipal


def evidence(name,data):
    if os.environ.get('U5PB_EVIDENCE'):
        with (Path(os.environ['U5PB_EVIDENCE'])/(name+'.json')).open('x',encoding='utf-8') as f:
            json.dump(data,f,indent=2);f.write('\n')


@pytest.fixture
def fixture(monkeypatch):
    from sqlalchemy.engine import Engine
    original=Engine.connect
    allowed=set()
    monkeypatch.setattr(Engine,'connect',lambda engine,*a,**k:original(engine,*a,**k) if engine in allowed else pytest.fail('Non-fixture database access forbidden'))
    from services import chromosome_service,ga_checkpoint_service,ga_trusted_runs
    def forbidden(*a,**k):pytest.fail('Institutional GA storage forbidden')
    monkeypatch.setattr(chromosome_service,'save_best_if_better',forbidden)
    monkeypatch.setattr(ga_checkpoint_service,'save_checkpoint',forbidden)
    made=[]
    def make(generations=0,prepared=None,limits=Limits()):
        a,c,v=dependencies(generations,prepared)
        bundle=c.catalog.record.prepared_bundle
        permit=ResearchPermit(ACTOR,DEPT,CATALOG,bundle.fingerprint,'FICTIONAL-YEAR','FICTIONAL-TERM','FICTIONAL-DATASET')
        w=ResearchWorker(Coordinator(Store.create(max_runs=4),a,c),initialize=True)
        bridge=ResearchBridge(w,permit,initialize=True);made.append(bridge)
        return bridge,v
    make.allowed=allowed
    yield make
    for b in made:
        assert b.worker.close(PRINCIPAL,timeout=20)['quiescent']
        assert all(not t.is_alive() for t in b.worker.threads.values())


def admit(b,limits=Limits()):return b.admit(PRINCIPAL,str(uuid4()),limits)['run_id']
def until(b,run,timeout=90):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        s=b.observe(PRINCIPAL,run)
        if s['state'] in {'COMPLETED','STOPPED','FAILED','RESOURCE_LIMITED','INTERRUPTED','RECOVERY_REQUIRED'}:
            b.worker.wait(PRINCIPAL,run,2);return s
        time.sleep(.05)
    pytest.fail('Owned research worker exceeded test bound')


def reopen(b):
    a,c,_=dependencies(prepared=b.worker.coordinator.source.catalog.record.prepared_bundle)
    old=b.worker.storage
    w=ResearchWorker(Coordinator(Store(old.root,old.store_id,max_runs=4),a,c))
    return ResearchBridge(w,b.permit)


def test_new_context_not_consumed_and_no_production_activation(fixture):
    b,_=fixture();r=admit(b);s=b.observe(PRINCIPAL,r)
    assert s['context_qualification']=='UNVERIFIED_NOT_CONSUMED'
    with pytest.raises(RunError,match='CONSUMPTION_MISSING'):b.qualified_result(PRINCIPAL,r)
    caps=b.capabilities(PRINCIPAL)
    assert caps['fictional_research_execution'] and not caps['institutional_optimization']
    assert not caps['institutional_saved_best_promotion'] and not caps['continuous_dashboard_enabled']
    assert not caps['seven_day_qualified'] and not caps['active_checkpoint_restore']
    assert configured_service() is None and saved_best_policy.configured_verifier() is None


@pytest.mark.parametrize('field',['academic_year','term','dataset','catalog'])
def test_nonfictional_permit_rejected(fixture,field):
    b,_=fixture()
    with pytest.raises(RunError,match='FICTIONAL_SCOPE'):replace(b.permit,**{field:'UNAPPROVED-INSTITUTIONAL-LABEL'}).validate()


@pytest.mark.parametrize('principal',[None,PreferencePrincipal('admin',user_id=OTHER),PreferencePrincipal('faculty',user_id=OTHER)])
def test_role_claim_not_research_authority(fixture,principal):
    b,_=fixture()
    with pytest.raises(RunError):b.admit(principal,str(uuid4()))
    with b.worker.storage.connection() as db:assert db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]==0


def test_idempotent_concurrent_admission_and_restart(fixture):
    b,_=fixture();key=str(uuid4());other=reopen(b)
    with ThreadPoolExecutor(2) as pool:runs=list(pool.map(lambda x:x.admit(PRINCIPAL,key)['run_id'],[b,other]))
    assert runs[0]==runs[1]
    assert reopen(b).observe(PRINCIPAL,runs[0])['state']=='CREATED'


@pytest.mark.parametrize('field',['bundle_hash','config_hash','optimizer','department'])
def test_changed_run_binding_rejected(fixture,field):
    b,_=fixture();run=admit(b)
    with b.worker.storage.transaction() as db:db.execute('UPDATE runs SET '+field+'=? WHERE id=?',('0'*64 if field!='department' else OTHER_DEPT,run))
    with pytest.raises((RunError,ValueError)):b.observe(PRINCIPAL,run)


@pytest.mark.parametrize('mode',['scoring','preferences','subject'])
def test_changed_source_does_not_silently_requalify(fixture,mode):
    b,_=fixture();run=admit(b)
    from services.ga_input_bundle import capture
    rec=b.worker.coordinator.source.catalog.record;data=rec.prepared_bundle.materialize(rec.prepared_bundle.run_id)
    if mode=='scoring':data['scoring_context']['settings']['subject_penalty']=912
    elif mode=='preferences':data['scoring_context']['preferences']['fictional-marker']={'fictional':True}
    else:data['templates'][0][0].title='FICTIONAL-CHANGED'
    new=capture(run_id=rec.prepared_bundle.run_id,templates=data['templates'],fallback_templates=data['fallback_templates'],
        legacy_preferences=data['legacy_preferences'],scoring_context=data['scoring_context'],configuration=data['configuration'],
        source_identities=json.loads(rec.prepared_bundle._raw)['source_identities'])
    b.worker.coordinator.source.catalog.record=replace(rec,prepared_bundle=new)
    with pytest.raises(RunError):b.start(PRINCIPAL,run)


@pytest.mark.parametrize('mode',['missing','changed','truncated','reordered'])
def test_context_and_telemetry_corruption_fail_closed(fixture,mode):
    b,_=fixture();run=admit(b)
    with b.worker.storage.transaction() as db:
        if mode=='missing':db.execute('UPDATE research_runs SET context=? WHERE run=?',(b'{}',run))
        elif mode=='changed':db.execute('UPDATE research_events SET payload=? WHERE run=?',(canonical({'run_id':run,'forged':True}),run))
        elif mode=='truncated':db.execute('DELETE FROM research_events WHERE run=?',(run,))
        else:db.execute('UPDATE research_events SET sequence=19 WHERE run=?',(run,))
    with pytest.raises((RunError,ValueError,KeyError)):b.telemetry(PRINCIPAL,run)


def test_quota_is_bounded_no_deletion_or_false_ack(fixture):
    b,_=fixture();run=admit(b)
    with b.worker.storage.transaction() as db:
        for i in range(MAX_EVENTS-1):b.ledger.append(db,run,dict(run_id=run,fictional_counter=i))
    with pytest.raises(RunError,match='TELEMETRY_LIMIT'):
        with b.worker.storage.transaction() as db:b.ledger.append(db,run,dict(run_id=run,overflow=True))
    with b.worker.storage.connection() as db:assert len(b.ledger.check(db,run)[1])==MAX_EVENTS


def test_concurrent_readers_and_restart_integrity(fixture):
    b,_=fixture();run=admit(b);other=reopen(b)
    with ThreadPoolExecutor(4) as pool:rows=list(pool.map(lambda _:other.telemetry(PRINCIPAL,run),range(8)))
    assert all(r==rows[0] for r in rows)


def test_revocation_blocks_old_result_and_source(fixture):
    b,v=fixture();run=admit(b);v.revoked=True
    with pytest.raises(RunError):b.start(PRINCIPAL,run)
    with pytest.raises(RunError):b.telemetry(PRINCIPAL,run)


def test_created_stop_is_truthful_and_idempotent(fixture):
    b,_=fixture();run=admit(b)
    assert b.stop(PRINCIPAL,run)['state']=='STOPPED'
    assert b.stop(PRINCIPAL,run)['checkpoint_sequence']==0
    with pytest.raises(RunError):b.compare_best(PRINCIPAL,run)
    assert not (b.worker.storage.root/'RESEARCH-BEST.json').exists()


def test_expired_owner_no_process_is_interrupted_not_success(fixture):
    b,_=fixture();run=admit(b)
    with b.worker.storage.transaction() as db:
        db.execute("UPDATE runs SET executor='fictional-expired-owner',lease=1,state='WORKER_RUNNING' WHERE id=?",(run,))
        db.execute("UPDATE workers SET state='RUNNING' WHERE run=?",(run,))
    again=reopen(b);assert again.observe(PRINCIPAL,run)['state']=='INTERRUPTED'
    with pytest.raises(RunError,match='QUARANTINE_REQUIRED'):again.start(PRINCIPAL,run)


def test_false_completion_without_checkpoint_rejected(fixture):
    b,_=fixture();run=admit(b)
    with b.worker.storage.transaction() as db:db.execute("UPDATE workers SET state='COMPLETED' WHERE run=?",(run,))
    with pytest.raises(RunError,match='COMPLETION_UNVERIFIED'):b.observe(PRINCIPAL,run)


def test_partial_telemetry_transaction_rolls_back(fixture):
    b,_=fixture();run=admit(b);before=b.telemetry(PRINCIPAL,run)
    with pytest.raises(RuntimeError,match='FICTIONAL_ABORT'):
        with b.worker.storage.transaction() as db:
            b.ledger.append(db,run,dict(run_id=run,fictional_partial=True))
            raise RuntimeError('FICTIONAL_ABORT')
    assert b.telemetry(PRINCIPAL,run)==before


def test_receipt_missing_rejected_before_qualification(fixture):
    from services.ga_research_context import verify_consumption
    b,_=fixture();run=admit(b)
    with b.qualified(PRINCIPAL,run) as row:
        with pytest.raises(RunError,match='CONSUMPTION_MISSING'):verify_consumption(b.worker,row,{})


def test_durable_key_corruption_rejected(fixture):
    b,_=fixture();run=admit(b);b.ledger.path.write_bytes(b'changed-fictional-key')
    with pytest.raises(RunError,match='KEY_CHANGED'):b.observe(PRINCIPAL,run)


def test_existing_worker_ceiling_not_extended(fixture):
    b,_=fixture()
    with pytest.raises(RunError,match='FIXTURE_LIMIT_EXCEEDED'):admit(b,Limits(wall_seconds=601))


def test_original_http_and_production_providers_unmodified():
    from services.ga_trusted_runs import configured_service as production
    from main import app
    assert production() is None and configured_service() is None
    # Installed FastAPI stores lazy included routers without a direct .path.
    # Inspect the effective OpenAPI path set, including nested registrations.
    assert not any(path.startswith('/api/research/') for path in app.openapi()['paths'])


def test_native_tampered_child_receipt_never_commits_checkpoint(fixture,monkeypatch):
    from services.ga_supervised_worker import Worker
    original=Worker._exchange
    def changed(worker,*a,**k):
        response,elapsed=original(worker,*a,**k)
        response['receipt']['loaded_model_fingerprint']='0'*64
        return response,elapsed
    monkeypatch.setattr(Worker,'_exchange',changed)
    b,_=fixture();run=admit(b);b.start(PRINCIPAL,run);s=until(b,run)
    assert s['state']=='FAILED' and s['reason']=='RESEARCH_CONSUMPTION_TAMPERED' and s['checkpoint_sequence']==0


def test_native_real_worker_zero_tie_restart_and_provenance(fixture):
    b,_=fixture(generations=1);run=admit(b);prior=random.getstate()
    b.start(PRINCIPAL,run);done=until(b,run);assert done['state']=='COMPLETED',done['reason']
    ctx,result=b.qualified_result(PRINCIPAL,run)
    assert result['best_fitness']==0 and random.getstate()==prior
    first=b.compare_best(PRINCIPAL,run);assert first['classification']=='ELIGIBLE' and first['updated']
    saved=b.worker.storage.root/'RESEARCH-BEST.json';raw=saved.read_bytes()
    assert not b.compare_best(PRINCIPAL,run)['updated'] and saved.read_bytes()==raw
    after=reopen(b);assert after.observe(PRINCIPAL,run)['state']=='COMPLETED'
    assert after.qualified_result(PRINCIPAL,run)[1]==result
    observations=after.telemetry(PRINCIPAL,run);scores=[x['best_so_far_fitness'] for x in observations if x.get('best_so_far_fitness') is not None]
    assert scores and scores==sorted(scores,reverse=True)
    assert all(x.get('current_fitness') is None for x in observations)
    assert after.start(PRINCIPAL,run)['state']=='COMPLETED'
    with after.worker.storage.connection() as db:
        procs=[json.loads(x[0]) for x in db.execute('SELECT observation FROM l_processes WHERE run=?',(run,))]
    assert procs and all(p['active_processes']==0 and p['creation_time_job_binding'] for p in procs)
    evidence('native-real-worker',dict(scenarios='Real U5L child + H optimizer + disposable SQLite; no institutional approval',
        state=done['state'],fitness=result['best_fitness'],generation=done['generation'],checkpoint_sequence=done['checkpoint_sequence'],
        best_values=scores,telemetry_events=len(observations),durable_restart_equal=True,RNG_unchanged=True,
        research_best_tie_bytes_preserved=True,production_promotion=False,physical_observations=procs))


def test_native_cross_run_consumption_not_client_forged(fixture):
    b,_=fixture();run=admit(b);second=admit(b)
    b.start(PRINCIPAL,run);assert until(b,run)['state']=='COMPLETED'
    with b.worker.storage.transaction() as db:
        proof=db.execute('SELECT payload,signature FROM research_proofs WHERE run=?',(run,)).fetchone()
        db.execute('INSERT INTO research_proofs VALUES(?,?,?,?)',(second,1,proof[0],proof[1]))
    with b.worker.storage.connection() as db:
        with pytest.raises(RunError,match='TAMPERED'):b.ledger.proof(db,second,1)
    with pytest.raises(RunError):ResearchComparison(b,PRINCIPAL,run).attest(b.qualified_result(PRINCIPAL,run)[0]['context'],'0'*64)


def test_native_legacy_research_archive_remains_unverified(fixture):
    b,_=fixture();run=admit(b);path=b.worker.storage.root/'RESEARCH-BEST.json'
    raw=canonical(dict(format='ccs-ga-chromosome',version=1,best_fitness=0,subject_keys=['fictional'],schedule=[{}]));path.write_bytes(raw)
    b.start(PRINCIPAL,run);assert until(b,run)['state']=='COMPLETED'
    assert b.compare_best(PRINCIPAL,run)['classification']=='UNVERIFIED' and path.read_bytes()==raw


def test_native_wall_limit_and_crash_are_distinct(fixture,monkeypatch):
    import services.ga_supervised_worker as module
    from tests.test_supervised_worker import blocking_arguments
    b,_=fixture();run=admit(b,Limits(wall_seconds=5))
    monkeypatch.setattr(module,'arguments',blocking_arguments);b.start(PRINCIPAL,run)
    s=until(b,run,25);assert s['state']=='RESOURCE_LIMITED' and s['reason']=='GA_WORKER_TIME_BUDGET'
    monkeypatch.setattr(module,'arguments',lambda _: [__import__('sys')._base_executable,'-I','-B','-c','import os;os._exit(87)'])
    other,_=fixture();run2=admit(other);other.start(PRINCIPAL,run2);s2=until(other,run2)
    assert s2['state']=='FAILED' and s2['reason']=='GA_SUPERVISION_CHILD_CRASH'
    assert not other.observe(PRINCIPAL,run2)['checkpoint_sequence']
    with other.worker.storage.connection() as db:
        observed=[json.loads(x[0]) for x in db.execute('SELECT observation FROM l_processes')]
    assert all(o['active_processes']==0 for o in observed)
    evidence('native-failure-kinds',dict(wall_timeout=s['state'],wall_reason=s['reason'],crash=s2['state'],crash_reason=s2['reason'],cleanup_verified=True,CPU_or_memory_limit_not_inferred_from_crash=True))


def test_native_orphan_detection_never_activates_recovery(fixture,monkeypatch):
    import services.ga_supervised_worker as module
    from tests.test_supervised_worker import blocking_arguments
    b,_=fixture();run=admit(b);monkeypatch.setattr(module,'arguments',blocking_arguments);b.start(PRINCIPAL,run)
    end=time.monotonic()+10
    while time.monotonic()<end:
        with b.worker.storage.connection() as db:p=db.execute("SELECT * FROM l_processes WHERE run=? AND status='ACTIVE'",(run,)).fetchone()
        if p:break
        time.sleep(.02)
    assert p is not None
    # Freeze one status transaction across the real heartbeat lease update.
    with b.worker.storage.transaction() as db:
        row=b.worker.store.row(db,ACTOR,run);row['lease']=1
        state,reason=b._state(db,row)
        assert state=='RECOVERY_REQUIRED' and reason=='EXPIRED_OWNER_LEASE_ORPHAN_ALIVE'
    b.worker.processes[run].terminate();assert until(b,run)['state']=='FAILED'


def test_native_two_runs_complete_evaluation_equivalence(fixture):
    b,_=fixture();one=admit(b);two=admit(b)
    for run in [one,two]:b.start(PRINCIPAL,run);assert until(b,run)['state']=='COMPLETED'
    a=b.qualified_result(PRINCIPAL,one)[0];c=b.qualified_result(PRINCIPAL,two)[0]
    assert a['context']['bundle_fingerprint']!=c['context']['bundle_fingerprint']
    assert a['evaluation_fingerprint']==c['evaluation_fingerprint']
    assert b.compare_best(PRINCIPAL,one)['updated']
    assert b.compare_best(PRINCIPAL,two)['classification']=='ELIGIBLE'


def test_native_storage_failure_no_success_or_best(fixture,monkeypatch):
    b,_=fixture();run=admit(b)
    original=b.ledger.save_proof
    def fail(*a):raise RunError('RESEARCH_PROOF_LIMIT')
    monkeypatch.setattr(b.ledger,'save_proof',fail);b.start(PRINCIPAL,run)
    s=until(b,run);assert s['state']=='FAILED' and s['checkpoint_sequence']==0
    with pytest.raises(RunError):b.compare_best(PRINCIPAL,run)
    monkeypatch.setattr(b.ledger,'save_proof',original)


def test_native_original_455_assignments_history_breakdown_rng(fixture,monkeypatch,tmp_path):
    from tests import test_bounded_worker as original_checks
    # That module may first be imported after this fixture's no-write spy.
    # Bind its oracle to the actual function captured before fixture setup;
    # its configured verifier is None and the oracle path is owned tmp_path.
    monkeypatch.setattr(original_checks,'ORIGINAL_SAVE_BEST',SNAPSHOT_ORIGINAL_SAVE_BEST)
    def adapter(generations=0,limits=None,prepared=None):
        b,v=fixture(generations=generations,prepared=prepared)
        return b.worker,admit(b,limits or Limits()),v
    # Reuse the unchanged original oracle assertions, not a second GA/fitness.
    original_checks.test_nonzero_fitness_original_fixed_engine_parity(adapter,monkeypatch,tmp_path)


def test_native_real_parent_interruption_truthful_after_restart(fixture):
    import subprocess,sys,base64
    b,_=fixture();run=admit(b)
    prepared=b.worker.coordinator.source.catalog.record.prepared_bundle
    payload=dict(root=str(b.worker.storage.root),store=b.worker.storage.store_id,run=run,
        permit=__import__('dataclasses').asdict(b.permit),prepared=base64.b64encode(prepared._raw).decode(),
        prepared_run=prepared.run_id,prepared_hash=prepared.fingerprint)
    code='''import sys,json,os,time,base64
wire=sys.stdout
class Discard:
 def write(self,v):return len(v)
 def flush(self):pass
sys.stdout=Discard()
from services.ga_input_bundle import InputBundle
from services.ga_owned_store import Store
from services.ga_trusted_runs import Coordinator
from services.ga_research_context import ResearchPermit
from services.ga_research_bridge import ResearchWorker,ResearchBridge
from tests.bounded_worker_support import dependencies
from tests.trusted_run_support import PRINCIPAL
from tests.test_supervised_worker import blocking_arguments
import services.ga_supervised_worker as module
p=json.loads(sys.stdin.readline())
prepared=InputBundle.from_bytes(base64.b64decode(p['prepared']),p['prepared_run'],p['prepared_hash'])
a,c,_=dependencies(prepared=prepared)
w=ResearchWorker(Coordinator(Store(p['root'],p['store'],max_runs=4),a,c))
b=ResearchBridge(w,ResearchPermit(**p['permit']))
module.arguments=blocking_arguments
b.start(PRINCIPAL,p['run'])
end=time.monotonic()+20
while time.monotonic()<end:
 with w.storage.connection() as db:row=db.execute("SELECT pid FROM l_processes WHERE run=? AND status='ACTIVE'",(p['run'],)).fetchone()
 if row:break
 time.sleep(.02)
else:raise RuntimeError('Owned child not observed')
wire.write('OWNED_RESEARCH_READY\\n');wire.flush()
sys.stdin.readline();os._exit(23)
'''
    env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE'}}
    child=subprocess.Popen([sys.executable,'-B','-c',code],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
    try:
        child.stdin.write(json.dumps(payload)+'\n');child.stdin.flush()
        # Bound the pipe read rather than waiting indefinitely for readiness.
        from queue import Queue,Empty
        q=Queue();reader=threading.Thread(target=lambda:q.put(child.stdout.readline()),daemon=True);reader.start()
        try:ready=q.get(timeout=30)
        except Empty:pytest.fail('Owned research parent readiness timed out')
        assert ready.strip()=='OWNED_RESEARCH_READY'
        child.stdin.write('simulate supervisor interruption\n');child.stdin.flush()
        assert child.wait(10)==23
    finally:
        if child.poll() is None:child.terminate();child.wait(5)
        child.stdin.close();child.stdout.close()
    again=reopen(b);end=time.monotonic()+14
    while time.monotonic()<end:
        s=again.observe(PRINCIPAL,run)
        if s['state']=='INTERRUPTED':break
        time.sleep(.1)
    assert s['state']=='INTERRUPTED' and s['checkpoint_sequence']==0
    with pytest.raises(RunError,match='QUARANTINE_REQUIRED'):again.start(PRINCIPAL,run)
    evidence('native-parent-interruption',dict(parent_exit=23,post_restart_state=s['state'],
        no_fabricated_completion=True,active_restore=False,checkpoint_sequence=0,quarantine_required=True))


@pytest.fixture
def http_fixture(fixture,monkeypatch,tmp_path):
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from identity_models import Base,User
    from services import auth_service as auth
    import database
    from routers.ga_research import create_app
    from routers.auth import router as auth_router
    b,_=fixture(generations=1)
    engine=create_engine('sqlite:///'+str(tmp_path/'FICTIONAL-auth.sqlite3'),connect_args={'check_same_thread':False})
    fixture.allowed.add(engine);Base.metadata.create_all(engine)
    password=secrets.token_urlsafe(24)
    with Session(engine) as db,db.begin():
        for actor,label in [(ACTOR,'research'),(OTHER,'unscoped')]:
            db.add(User(id=UUID(actor),username=label+'@fictional.invalid',role='admin',password_hash=auth.hash_password(password)))
    def isolated():
        with Session(engine) as db:yield db
    def app(bridge=b):
        a=create_app(bridge);a.include_router(auth_router)
        a.dependency_overrides[database.get_identity_db]=isolated
        a.dependency_overrides[auth.authenticated_db]=isolated
        return a
    monkeypatch.setenv('AUTH_ALLOWED_ORIGINS','http://localhost:5173');monkeypatch.setenv('AUTH_COOKIE_SECURE','false')
    monkeypatch.setattr(auth,'LOGIN_LIMITER',auth.LoginLimiter())
    class Owned:
        def __repr__(self):return '<Fictional auth fixture; credentials withheld>'
        def login(self,client,username='research'):
            response=client.post('/api/auth/login',headers={'Origin':'http://localhost:5173'},json={'username':username+'@fictional.invalid','password':password})
            if response.status_code!=200:pytest.fail('Fictional login failed; response withheld')
            return {'Origin':'http://localhost:5173','X-CSRF-Token':response.json()['csrf_token']}
        def login_tcp(self,opener,base):
            import urllib.request
            req=urllib.request.Request(base+'/api/auth/login',data=canonical({'username':'research@fictional.invalid','password':password}),
                headers={'Origin':'http://localhost:5173','Content-Type':'application/json'})
            with opener.open(req,timeout=30) as response:value=json.loads(response.read())
            return {'Origin':'http://localhost:5173','X-CSRF-Token':value['csrf_token']}
    owned=Owned();owned.bridge=b;owned.app=app;owned.engine=engine
    yield owned
    engine.dispose()


def client_for(app,remote='127.0.0.1'):
    from fastapi.testclient import TestClient
    return TestClient(app,base_url='http://localhost',client=(remote,41001))


def test_http_authentication_csrf_and_unscoped_admin(http_fixture):
    f=http_fixture
    with client_for(f.app()) as c:
        assert c.get('/api/research/ga/capabilities',headers={'X-Role':'admin'}).status_code==401
        f.login(c)
        assert c.post('/api/research/ga/runs',json={'request_id':str(uuid4())}).status_code==403
        assert c.get('/api/research/ga/capabilities').json()['fictional_research_execution']
    with client_for(f.app()) as c:
        headers=f.login(c,'unscoped')
        assert c.post('/api/research/ga/runs',headers={**headers,'X-Role':'chair','X-Department-ID':DEPT},json={'request_id':str(uuid4())}).status_code==403


@pytest.mark.parametrize('extra',['context','bundle','department_id','fitness','role','limits'])
def test_http_forged_admission_metadata_rejected(http_fixture,extra):
    with client_for(http_fixture.app()) as c:
        headers=http_fixture.login(c)
        assert c.post('/api/research/ga/runs',headers=headers,json={'request_id':str(uuid4()),extra:'FICTIONAL-FORGED'}).status_code==422


def test_http_missing_provider_and_nonlocal_requests_rejected(http_fixture):
    with client_for(http_fixture.app(None)) as c:
        http_fixture.login(c);assert c.get('/api/research/ga/capabilities').status_code==503
    with client_for(http_fixture.app(),remote='192.0.2.5') as c:
        assert c.get('/api/research/ga/capabilities').status_code==403


def test_http_account_revocation_not_bypassed_by_permit(http_fixture):
    from sqlalchemy.orm import Session
    from identity_models import User
    with client_for(http_fixture.app()) as c:
        http_fixture.login(c)
        with Session(http_fixture.engine) as db,db.begin():db.get(User,UUID(ACTOR)).is_active=False
        assert c.get('/api/research/ga/capabilities').status_code==401


def test_http_real_loopback_worker_and_api_restart(http_fixture):
    """Actual TCP HTTP/Uvicorn + auth/CSRF + Windows child + private SQLite."""
    import socket
    import urllib.request,urllib.error,http.cookiejar
    import uvicorn
    f=http_fixture;sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    server=uvicorn.Server(uvicorn.Config(f.app(),log_level='critical',access_log=False,lifespan='off'))
    thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=False)
    def request(path,body=None,headers=None):
        raw=canonical(body) if body is not None else None
        req=urllib.request.Request('http://127.0.0.1:'+str(port)+path,data=raw,headers={'Content-Type':'application/json',**(headers or {})})
        with opener.open(req,timeout=30) as response:return json.loads(response.read())
    thread.start()
    try:
        end=time.monotonic()+10
        while not server.started and time.monotonic()<end:time.sleep(.01)
        assert server.started
        # Authenticate through actual session cookie and CSRF paths. Secrets
        # remain in this fixture and are never written to evidence.
        headers=f.login_tcp(opener,'http://127.0.0.1:'+str(port))
        run=request('/api/research/ga/runs',{'request_id':str(uuid4())},headers)['run_id']
        req=urllib.request.Request('http://127.0.0.1:'+str(port)+'/api/research/ga/runs/'+run+'/start',method='POST',headers=headers)
        with opener.open(req,timeout=30) as response:assert response.status==200
        end=time.monotonic()+90
        while time.monotonic()<end:
            status=request('/api/research/ga/runs/'+run,headers=headers)
            if status['state'] in {'COMPLETED','FAILED','RESOURCE_LIMITED'}:break
            time.sleep(.1)
        if status['state']!='COMPLETED':pytest.fail('Actual loopback fictional worker failed: '+str(status.get('reason')))
        before=request('/api/research/ga/runs/'+run+'/telemetry',headers=headers)
    finally:
        server.should_exit=True;thread.join(10);sock.close()
        assert not thread.is_alive()
    restarted=f.app(reopen(f.bridge))
    with client_for(restarted) as c:
        headers2=f.login(c)
        assert c.get('/api/research/ga/runs/'+run).json()['state']=='COMPLETED'
        assert c.get('/api/research/ga/runs/'+run+'/telemetry').json()==before
        assert c.post('/api/research/ga/runs/'+run+'/resume',headers=headers2).status_code==404
        assert c.post('/api/research/ga/runs/'+run+'/start',headers=headers2,json={'context':'FICTIONAL-FORGED'}).status_code==422
    evidence('real-http-worker-restart',dict(actual_TCP_HTTP=True,actual_FastAPI_auth_CSRF=True,actual_Windows_worker=True,
        disposable_SQLite=True,state='COMPLETED',telemetry_equal_after_API_reconstruction=True,event_count=len(before),
        no_institutional_authority=True,active_restore_exposed=False))
