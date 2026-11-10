"""Real loopback/session/SQLite/worker continuity; fictional snapshots only."""
import copy
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from uuid import uuid4
import pytest
from services.ga_worker_contract import fictional_source
try:fictional_source()
except ValueError:pytest.skip('Owned fictional source required',allow_module_level=True)
from services.ga_research_continuity import ContinuityObserver
from tests.test_research_bridge import fixture,admit,reopen
from tests.test_research_observations import files
from tests.research_console_support import Environment
from tests.trusted_run_support import PRINCIPAL


def research_files(b):return {k:v for k,v in files(b).items() if not k.startswith('CONSOLE-AUTH.sqlite3')}
def evidence(name,data):
    with (Path(os.environ['U5PD_EVIDENCE'])/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(data,f,indent=2);f.write('\n')


def test_real_HTTP_API_offline_during_worker_and_reconstruction(fixture,monkeypatch):
    import urllib.request,http.cookiejar
    b,_=fixture(generations=1);env=Environment(b,fixture.allowed.add);env.observer=ContinuityObserver(b)
    monkeypatch.setenv('AUTH_ALLOWED_ORIGINS',env.origin);monkeypatch.setenv('AUTH_COOKIE_SECURE','false')
    jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    entered=threading.Event();release=threading.Event();original=b.worker._exchange
    def gate(*a,**k):
        entered.set()
        if not release.wait(10):raise RuntimeError('Fictional dispatch barrier exceeded bound')
        return original(*a,**k)
    monkeypatch.setattr(b.worker,'_exchange',gate)
    def request(path):
        with opener.open(env.backend+path,timeout=15) as response:return json.loads(response.read())
    try:
        env.serve()
        payload=json.dumps(dict(username='research@fictional.invalid',password=env._password)).encode()
        req=urllib.request.Request(env.backend+'/api/auth/login',data=payload,headers={'Origin':env.origin,'Content-Type':'application/json'})
        with opener.open(req,timeout=15) as response:assert response.status==200
        run=admit(b);path='/api/research/observations/runs/'+run;first=request(path)
        assert first['contract']=='research-observation-v2' and first['overview']['state']=='CREATED'
        b.start(PRINCIPAL,run);assert entered.wait(5)
        env.server.should_exit=True;env.thread.join(10);env.sock.close();assert not env.thread.is_alive()
        assert b.worker.threads[run].is_alive()
        # The barrier is only in the test's dispatch wrapper. Original native
        # optimizer execution now happens while this API listener is stopped.
        release.set();b.worker.threads[run].join(90);assert not b.worker.threads[run].is_alive()
        before=research_files(b);finished=ContinuityObserver(b).detail(PRINCIPAL,run)
        assert finished['overview']['state']=='COMPLETED' and finished['overview']['freshness']['state']=='TERMINAL'
        assert research_files(b)==before
        env.observer=ContinuityObserver(reopen(b));env.serve();after=request(path)
        old=copy.deepcopy(finished);new=copy.deepcopy(after);old['overview'].pop('freshness');new['overview'].pop('freshness');assert old==new
        assert after['overview']['freshness']['state']=='TERMINAL' and research_files(b)==before
        evidence('real-api-offline-reconstruction.json',dict(actual_TCP_FastAPI=True,actual_sessions=True,actual_SQLite=True,actual_native_optimizer=True,
            API_listener_stopped_before_optimizer_dispatch=True,test_only_dispatch_barrier=True,worker_completed_without_API=True,
            API_reconstructed=True,durable_observations_equal=True,read_only_research_bytes_identical=True,terminal='COMPLETED',fitness=after['overview']['best_so_far_fitness'],
            interpretation='API reconstruction within one host process; not institutional failover. Actual separate supervisor interruption covered by new native test.'))
    finally:release.set();env.close()


def test_live_edge_v2_retention_and_reload(fixture,monkeypatch):
    from starlette.responses import JSONResponse
    b,_=fixture(generations=1);env=Environment(b,fixture.allowed.add);env.observer=ContinuityObserver(b)
    monkeypatch.setenv('AUTH_ALLOWED_ORIGINS',env.origin);monkeypatch.setenv('AUTH_COOKIE_SECURE','false')
    fault=b.worker.storage.root/'U5PD-HTTP-FAULT';original=env.app
    def app(*args,**kwargs):
        a=original(*args,**kwargs)
        @a.middleware('http')
        async def injected_failure(request,call_next):
            mode=fault.read_text() if fault.exists() else ''
            path=request.url.path
            if path.startswith('/api/research/observations/runs') and (mode=='DETAIL' and path!='/api/research/observations/runs' or mode=='LIST' and path=='/api/research/observations/runs'):
                # Explicit fictional test injection, not a storage/server outage.
                return JSONResponse({'detail':{'code':'FICTIONAL_INJECTED_HTTP_UNAVAILABLE'}},503,headers={'Cache-Control':'no-store','Access-Control-Allow-Origin':env.origin,'Access-Control-Allow-Credentials':'true'})
            return await call_next(request)
        return a
    env.app=app
    try:
        env.prepare();env.serve();before=research_files(b);target=Path(os.environ['U5PD_EVIDENCE'])
        private={**env.private_browser_input(),'fault_path':str(fault)}
        child=dict(os.environ,VITE_API_URL=env.backend,U5PD_EVIDENCE=str(target))
        result=subprocess.run(['node','tests/observationContinuity.live.mjs'],cwd=Path.cwd().parent/'frontend',env=child,input=json.dumps(private)+'\n',capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
        evidence('live-browser-command.json',dict(exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr,scope='Actual Edge/React/TCP FastAPI/session/private SQLite/native worker; HTTP faults and expired-owner metadata explicitly injected'))
        assert result.returncode==0,'Live browser did not pass; sanitized evidence retained'
        assert not fault.exists() and research_files(b)==before
        evidence('live-preservation.json',dict(research_files_byte_identical=True,auth_database_separate=True,GET_methods_only=True,fault_injection='Private test marker and middleware; not actual database failure',production_authority=False))
    finally:
        if fault.exists():fault.unlink() # only this newly owned fixture marker
        env.close()
