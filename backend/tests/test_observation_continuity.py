"""Fictional observation tests; no production data/engine changes."""
import copy
import json
import random
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from services.ga_observation_freshness import evaluate


@pytest.mark.parametrize('times,now,state,confirmed,terminal_at,expected,reason',[
 ([990],1000,'RUNNING',False,None,'FRESH','RECENT_DURABLE_OBSERVATION'),
 ([970],1000,'RUNNING',False,None,'FRESH','RECENT_DURABLE_OBSERVATION'),
 ([969],1000,'RUNNING',False,None,'STALE','OBSERVATION_AGE_EXCEEDED'),
 ([],1000,'CREATED',False,None,'UNKNOWN','MISSING_TIMESTAMP'),
 ([None],1000,'RUNNING',False,None,'UNKNOWN','MISSING_TIMESTAMP'),
 ([1003],1000,'RUNNING',False,None,'UNKNOWN','FUTURE_OBSERVATION'),
 ([1002],1000,'RUNNING',False,None,'FRESH','WITHIN_CLOCK_SKEW_TOLERANCE'),
 ([999,998],1000,'RUNNING',False,None,'UNKNOWN','OBSERVATION_TIME_REVERSED'),
 ([990,990],1000,'RUNNING',False,None,'FRESH','RECENT_DURABLE_OBSERVATION'),
 ([True],1000,'RUNNING',False,None,'UNKNOWN','INVALID_TIMESTAMP'),
 ([float('inf')],1000,'RUNNING',False,None,'UNKNOWN','INVALID_TIMESTAMP'),
 ([990],float('nan'),'RUNNING',False,None,'UNKNOWN','SERVER_CLOCK_UNVERIFIABLE'),
 ([990],1000,'COMPLETED',False,None,'UNKNOWN','TERMINAL_OUTCOME_NOT_INDEPENDENTLY_CONFIRMED'),
 ([900],1000,'COMPLETED',True,910,'TERMINAL','DURABLE_TERMINAL_OUTCOME'),
 ([900],1000,'STOPPED',True,910,'TERMINAL','DURABLE_TERMINAL_OUTCOME'),
 ([900],1000,'FAILED',True,910,'TERMINAL','DURABLE_TERMINAL_OUTCOME'),
 ([900],1000,'RESOURCE_LIMITED',True,910,'TERMINAL','DURABLE_TERMINAL_OUTCOME'),
 ([990],1000,'FAILED',True,1003,'UNKNOWN','TERMINAL_OUTCOME_NOT_INDEPENDENTLY_CONFIRMED'),
 ([990],1000,'INTERRUPTED',False,None,'UNKNOWN','OWNERSHIP_OR_ORPHAN_UNCERTAIN'),
 ([990],1000,'RECOVERY_REQUIRED',False,None,'UNKNOWN','OWNERSHIP_OR_ORPHAN_UNCERTAIN'),
])
def test_freshness_oracle(times,now,state,confirmed,terminal_at,expected,reason):
    r=evaluate(now=now,times=times,state=state,terminal_confirmed=confirmed,terminal_at=terminal_at)
    assert (r['state'],r['reason'])==(expected,reason)
    assert r['worker_health']=='NOT_ESTABLISHED_BY_OBSERVATION_HTTP'
    if expected=='TERMINAL':assert r['telemetry_state']=='STALE'


from services.ga_worker_contract import fictional_source
try:fictional_source()
except ValueError:pytest.skip('Owned fictional source required',allow_module_level=True)
from services.ga_research_continuity import ContinuityObserver
from services.ga_run_authority import RunError
from services.preference_authorization import PreferencePrincipal
from tests.test_research_bridge import fixture,admit,until,reopen,http_fixture,client_for
from tests.test_research_observations import files
from tests.trusted_run_support import PRINCIPAL,OTHER,ACTOR


def durable(d):
    data=copy.deepcopy(d);data['overview'].pop('freshness');return data


def test_recent_stale_and_readonly_snapshot(fixture,monkeypatch):
    b,_=fixture();run=admit(b)
    with b.worker.storage.connection() as db:t=b.ledger.check(db,run)[1][-1]['observed_at']
    clock=[t+1];o=ContinuityObserver(b,clock=lambda:clock[0]);before=files(b);rng=random.getstate()
    for name in ['observe','telemetry','start','qualified_result','compare_best']:
        monkeypatch.setattr(b,name,lambda *a:pytest.fail('GET attempted mutable research path'))
    d=o.detail(PRINCIPAL,run);assert d['overview']['freshness']['state']=='FRESH' and d['contract']=='research-observation-v2'
    clock[0]=t+31;stale=o.detail(PRINCIPAL,run)
    assert stale['overview']['freshness']['state']=='STALE' and stale['overview']['state']=='CREATED'
    assert durable(stale)==durable(d) and files(b)==before and random.getstate()==rng


@pytest.mark.parametrize('kind',['missing','future','backward','partial'])
def test_signed_unusual_time_not_hidden(fixture,kind):
    b,_=fixture();run=admit(b)
    with b.worker.storage.transaction() as db:
        t=b.ledger.check(db,run)[1][-1]['observed_at'];payload=dict(run_id=run)
        if kind!='missing':payload['observed_at']=t+100 if kind=='future' else t-1
        if kind=='partial':payload['worker_state']='NOT_A_VALID_WORKER_STATE'
        b.ledger.append(db,run,payload)
    o=ContinuityObserver(b,clock=lambda:t+1);before=files(b)
    if kind=='partial':
        with pytest.raises(RunError,match='STATE_INVALID'):o.detail(PRINCIPAL,run)
    else:
        data=o.detail(PRINCIPAL,run);assert data['overview']['freshness']['state']=='UNKNOWN'
        assert len(data['telemetry']['items'])==2
    assert files(b)==before


def test_duplicates_and_delayed_commit_do_not_invent_updates(fixture):
    b,_=fixture();run=admit(b);o=ContinuityObserver(b)
    first=o.detail(PRINCIPAL,run);t=first['overview']['last_observed_at']
    payload=dict(run_id=run,observed_at=t,reason='FICTIONAL-DUPLICATE')
    with b.worker.storage.transaction() as db:
        b.ledger.append(db,run,payload)
        assert o.detail(PRINCIPAL,run)['telemetry']['total']==1 # uncommitted writer is not visible
    with b.worker.storage.transaction() as db:b.ledger.append(db,run,payload)
    before=files(b);second=ContinuityObserver(b,clock=lambda:t+31).detail(PRINCIPAL,run)
    assert second['telemetry']['total']==2 and second['overview']['freshness']['state']=='STALE'
    assert not second['fitness']['points'] and files(b)==before


def test_locked_storage_fails_and_retry_never_repairs(fixture):
    b,_=fixture();run=admit(b);o=ContinuityObserver(b);before=files(b)
    with b.worker.storage.connection() as db:
        db.execute('BEGIN EXCLUSIVE')
        try:
            with pytest.raises(RunError,match='STORAGE_UNAVAILABLE'):o.detail(PRINCIPAL,run)
        finally:db.rollback()
    assert o.detail(PRINCIPAL,run)['overview']['run_id']==run and files(b)==before


def test_concurrent_readers_reconstruction_and_scope(fixture):
    b,_=fixture();run=admit(b);clock=time.time();o=ContinuityObserver(b,clock=lambda:clock);before=files(b)
    with ThreadPoolExecutor(4) as pool:rows=list(pool.map(lambda _:o.detail(PRINCIPAL,run),range(8)))
    assert all(r==rows[0] for r in rows)
    again=ContinuityObserver(reopen(b),clock=lambda:clock);assert again.detail(PRINCIPAL,run)==rows[0]
    with pytest.raises(RunError):again.detail(PreferencePrincipal('admin',user_id=OTHER),run)
    assert files(b)==before


def test_stopped_terminal_requires_durable_matching_event(fixture):
    b,_=fixture();run=admit(b);b.stop(PRINCIPAL,run);o=ContinuityObserver(b)
    assert o.detail(PRINCIPAL,run)['overview']['freshness']['state']=='TERMINAL'
    with b.worker.storage.transaction() as db:db.execute('DELETE FROM worker_events WHERE run=?',(run,))
    before=files(b);data=o.detail(PRINCIPAL,run)
    assert data['overview']['state']=='STOPPED' and data['overview']['freshness']['state']=='UNKNOWN' and files(b)==before


def test_native_completion_and_unverified_cleanup(fixture):
    b,_=fixture(generations=1);run=admit(b);b.start(PRINCIPAL,run);assert until(b,run)['state']=='COMPLETED'
    o=ContinuityObserver(b);before=files(b);data=o.detail(PRINCIPAL,run)
    assert data['overview']['freshness']['state']=='TERMINAL' and data['overview']['best_so_far_fitness']==0
    assert files(b)==before and durable(ContinuityObserver(reopen(b)).detail(PRINCIPAL,run))==durable(data)
    with b.worker.storage.transaction() as db:db.execute("UPDATE l_processes SET status='CLEANUP_UNVERIFIED' WHERE run=?",(run,))
    assert o.detail(PRINCIPAL,run)['overview']['freshness']['state']=='UNKNOWN'


def test_native_windows_supervisor_interruption_remains_uncertain(fixture):
    from tests.test_research_bridge import test_native_real_parent_interruption_truthful_after_restart as original
    made=[]
    def capture(*a,**k):
        b,v=fixture(*a,**k);made.append(b);return b,v
    original(capture)
    b=made[0];o=ContinuityObserver(reopen(b));before=files(b);data=o.listing(PRINCIPAL)['items'][0]
    assert data['state']=='INTERRUPTED' and data['freshness']['state']=='UNKNOWN' and files(b)==before


def test_v2_http_auth_and_integrity_no_new_routes(http_fixture):
    from routers.research_observations import create_app
    f=http_fixture;app=create_app(ContinuityObserver(f.bridge));app.dependency_overrides.update(f.app().dependency_overrides)
    run=admit(f.bridge)
    with client_for(app) as c:
        assert c.get('/api/research/observations/runs').status_code==401
        f.login(c);before=files(f.bridge)
        for path in ['capabilities','runs','runs/'+run,'runs/'+run+'/telemetry']:
            result=c.get('/api/research/observations/'+path);assert result.status_code==200 and result.json()['contract']=='research-observation-v2'
        assert files(f.bridge)==before and c.post('/api/research/ga/runs').status_code==404
    with client_for(app) as c:
        f.login(c,'unscoped');assert c.get('/api/research/observations/runs/'+run).status_code==403
