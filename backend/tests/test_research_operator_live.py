"""Actual loopback HTTP and Edge acceptance, fictional credentials on stdin only."""
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import urllib.request
import http.cookiejar
import pytest
from services.ga_worker_contract import fictional_source
try:fictional_source()
except ValueError:pytest.skip('Owned snapshot required',allow_module_level=True)
from services.ga_research_operator import Operator
from routers.research_operator import create_app
from tests.test_research_bridge import fixture
from tests.research_console_support import Environment
from tests.trusted_run_support import PRINCIPAL
from uuid import uuid4


def host(b,allow):
    env=Environment(b,allow);env.operator=Operator(b,initialize=True);original=env.app;env.http_trace=[]
    def app():
        result=create_app(env.operator);result.dependency_overrides.update(original().dependency_overrides)
        @result.middleware('http')
        async def timing(request,call_next):
            tick=time.monotonic();response=await call_next(request)
            if request.url.path.startswith(('/api/research/operator','/api/auth/')):
                env.http_trace.append(dict(method=request.method,path=request.url.path,status=response.status_code,elapsed_seconds=time.monotonic()-tick))
            return response
        return result
    env.app=app;return env

def record(name,value):
    with (Path(os.environ['U5PE_EVIDENCE'])/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')


def test_real_edge_operator(fixture,monkeypatch):
    b,_=fixture(generations=1);env=host(b,fixture.allowed.add)
    try:
        env.serve();monkeypatch.setenv('AUTH_ALLOWED_ORIGINS',env.backend);monkeypatch.setenv('AUTH_COOKIE_SECURE','false')
        private=dict(username='research@fictional.invalid',password=env._password,backend=env.backend)
        child=dict(os.environ,U5PE_EVIDENCE=os.environ['U5PE_EVIDENCE'])
        result=subprocess.run(['node','tests/researchOperator.live.mjs'],cwd=Path.cwd().parent/'frontend',env=child,input=json.dumps(private)+'\n',capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
        record('browser-command.json',dict(exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr,scope='Actual Edge, loopback HTTP, real sessions/private SQLite and original Windows worker. E11 failed GET and E13 busy error are explicit client fault injections; no mocked success.'))
        record('http-timings.json',dict(requests=env.http_trace,scope='Actual server status/latency only; no headers, bodies, credentials or client-ack claim'))
        assert result.returncode==0,'Browser failed; sanitized diagnostic retained'
        cleanup=json.loads((Path(os.environ['U5PE_EVIDENCE'])/'browser-cleanup.json').read_text())
        assert cleanup['root_process_exit_verified'] and cleanup['unused_Vite_started'] is False
        with b.worker.storage.connection() as db:
            count=db.execute('SELECT COUNT(*) FROM runs').fetchone()[0];processes=db.execute('SELECT status FROM l_processes').fetchall()
        assert count==1 and len(processes)>=1 and all(p[0]=='EXIT_VERIFIED' for p in processes)
        record('live-process-summary.json',dict(actual_Edge=True,actual_HTTP=True,actual_SQLite=True,actual_native_worker=True,runs=count,process_batches=len(processes),all_process_exits_verified=True,production_authority=False))
    finally:env.close()


def test_control_API_reconstruction_without_relaunch(fixture,monkeypatch):
    b,_=fixture(generations=1);env=host(b,fixture.allowed.add);request=str(uuid4());opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def post(path,payload,token=None):
        headers={'Origin':env.backend,'Content-Type':'application/json'}
        if token:headers['X-CSRF-Token']=token
        req=urllib.request.Request(env.backend+path,data=json.dumps(payload).encode(),headers=headers)
        with opener.open(req,timeout=30) as response:return json.loads(response.read())
    entered=threading.Event();release=threading.Event();old=b.worker._exchange
    def gate(*a,**k):
        entered.set()
        if not release.wait(15):raise RuntimeError('Owned API-offline bound')
        return old(*a,**k)
    monkeypatch.setattr(b.worker,'_exchange',gate)
    try:
        env.serve();monkeypatch.setenv('AUTH_ALLOWED_ORIGINS',env.backend);monkeypatch.setenv('AUTH_COOKIE_SECURE','false')
        token=post('/api/auth/login',dict(username='research@fictional.invalid',password=env._password))['csrf_token']
        first=post('/api/research/operator/start',dict(request_id=request),token);run=first['run_id'];assert entered.wait(5)
        env.server.should_exit=True;env.thread.join(10);env.sock.close();assert not env.thread.is_alive()
        release.set();b.worker.threads[run].join(60);assert not b.worker.threads[run].is_alive()
        with b.worker.storage.connection() as db:before=db.execute('SELECT COUNT(*) FROM l_processes').fetchone()[0]
        env.operator=Operator(b);env.serve();monkeypatch.setenv('AUTH_ALLOWED_ORIGINS',env.backend)
        replay=post('/api/research/operator/start',dict(request_id=request),token)
        assert replay['replayed'] and replay['run_id']==run and replay['confirmation']=='DURABLE_TERMINAL_VERIFIED'
        with b.worker.storage.connection() as db:assert before==db.execute('SELECT COUNT(*) FROM l_processes').fetchone()[0]
        record('real-API-reconstruction.json',dict(actual_TCP_listener_restart=True,worker_completed_with_API_off=True,request_replayed_without_new_worker=True,process_batches=before,active_restore=False,scope='Same-host API reconstruction, not OS restart or institutional failover'))
    finally:release.set();env.close()
