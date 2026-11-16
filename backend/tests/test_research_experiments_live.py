"""Actual loopback/session/SQLite/Edge/original worker experiment acceptance."""
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
import http.cookiejar
import pytest
from services.ga_worker_contract import fictional_source
try:fictional_source()
except ValueError:pytest.skip('Owned snapshot required',allow_module_level=True)
from services.ga_research_operator import Operator
from services.ga_run_authority import digest
from routers.research_experiments import create_app
from tests.test_research_bridge import fixture
from tests.research_console_support import Environment


def test_real_edge_complete_and_stopped_experiments_with_exports(fixture,monkeypatch):
    b,_=fixture(generations=1);env=Environment(b,fixture.allowed.add);o=Operator(b,initialize=True);original=env.app;trace=[]
    def app():
        a=create_app(o);a.dependency_overrides.update(original().dependency_overrides)
        @a.middleware('http')
        async def timing(request,call_next):
            tick=time.monotonic();response=await call_next(request)
            if request.url.path.startswith(('/api/research/','/api/auth/')):trace.append(dict(method=request.method,path=request.url.path,status=response.status_code,elapsed_seconds=time.monotonic()-tick))
            return response
        return a
    env.app=app;folder=Path(os.environ['U5PF_EVIDENCE'])
    try:
        env.serve();monkeypatch.setenv('AUTH_ALLOWED_ORIGINS',env.backend);monkeypatch.setenv('AUTH_COOKIE_SECURE','false')
        private=dict(username='research@fictional.invalid',password=env._password,backend=env.backend)
        result=subprocess.run(['node','tests/researchExperiments.live.mjs'],cwd=Path.cwd().parent/'frontend',env=os.environ,input=json.dumps(private)+'\n',capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
        for name,doc in [('browser-command.json',dict(exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr)),('http-timings.json',dict(requests=trace,scope='Actual method/path/status only; no headers, bodies, cookies or credentials'))]:
            with (folder/name).open('x',encoding='utf-8') as f:json.dump(doc,f,indent=2);f.write('\n')
        assert result.returncode==0,'Real browser failure; diagnostics retained'
        cleanup=json.loads((folder/'browser-cleanup.json').read_text());assert cleanup['root_process_exit_verified']
        raw=(folder/'http-export.json').read_bytes();doc=json.loads(raw);assert digest(doc['record'])==doc['record_sha256']
        rows=list(csv.DictReader(io.StringIO((folder/'http-export.csv').read_text())));assert rows and all(x['record_sha256']==doc['record_sha256'] for x in rows)
        with b.worker.storage.connection() as db:
            runs=db.execute('SELECT COUNT(*) FROM runs').fetchone()[0];statuses=[r[0] for r in db.execute('SELECT status FROM l_processes')]
        assert runs==2 and statuses and all(x=='EXIT_VERIFIED' for x in statuses)
        # Reconstruct the actual F factory, retaining the same owned store and
        # session DB. This is API listener restart, not OS failover/active restore.
        opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        login=urllib.request.Request(env.backend+'/api/auth/login',data=json.dumps(dict(username='research@fictional.invalid',password=env._password)).encode(),headers={'Content-Type':'application/json','Origin':env.backend})
        with opener.open(login,timeout=30) as response:assert response.status==200
        env.server.should_exit=True;env.thread.join(10);env.sock.close();assert not env.thread.is_alive()
        o=Operator(b);env.serve();monkeypatch.setenv('AUTH_ALLOWED_ORIGINS',env.backend)
        with opener.open(env.backend+'/api/research/experiments/runs/'+doc['record']['run_id']+'/exports/json',timeout=30) as response:restored=json.loads(response.read())
        assert restored['record']['experiment_id']==doc['record']['experiment_id'] and restored['record_sha256']==doc['record_sha256']
        with b.worker.storage.connection() as db:assert len(statuses)==db.execute('SELECT COUNT(*) FROM l_processes').fetchone()[0]
        with (folder/'experiment-API-reconstruction.json').open('x',encoding='utf-8') as f:json.dump(dict(actual_TCP_restart=True,stable_experiment_identity=True,stable_record_hash=True,no_worker_relaunch=True,active_restore=False),f,indent=2);f.write('\n')
        with (folder/'live-acceptance.json').open('x',encoding='utf-8') as f:json.dump(dict(actual_Edge=True,actual_HTTP=True,actual_SQLite=True,original_native_worker=True,export_record_hash_verified=True,runs=runs,process_batches=len(statuses),all_process_exits_verified=True,production_authority=False),f,indent=2);f.write('\n')
    finally:env.close()


def test_existing_real_api_reconstruction_is_preserved(fixture,monkeypatch):
    # Same original TCP listener restart and durable idempotency oracle from E.
    from tests.test_research_operator_live import test_control_API_reconstruction_without_relaunch
    test_control_API_reconstruction_without_relaunch(fixture,monkeypatch)
