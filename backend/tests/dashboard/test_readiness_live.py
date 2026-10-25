"""Owned real Edge/FastAPI/SQLite D16 smoke; credentials travel via private stdin."""
from contextlib import redirect_stdout
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time

import uvicorn
from starlette.middleware.cors import CORSMiddleware
from main import app
from services.evidence_sanitization import sanitize
from tests.dashboard.test_system_acceptance import system, application, chair, setup, fixture, isolate


def test_readiness_edge_fastapi_sqlite_flow(system,monkeypatch,tmp_path):
    f=system
    # D2's synthetic source is not a complete legacy admin GAResult. Keep the
    # owned fixture's legacy latest-result view empty; V2 uses its actual store.
    # Preserve the synthetic source file and all publication fingerprints.
    from routers import genetic_algorithm as ga_router
    monkeypatch.setattr(ga_router,'_read_latest_result',lambda:None)
    from sqlalchemy import event
    from sqlalchemy.exc import IntegrityError
    from application_models import ScheduleApplication
    from services import chair_review_service as trust
    fault=tmp_path/'d16-fault.marker'
    def mode():return fault.read_text() if fault.exists() else ''
    def storage_failure(mapper,connection,target):
        if mode()=='rollback':raise IntegrityError('fictional persistence fault',None,None)
    event.listen(ScheduleApplication,'after_insert',storage_failure)
    original=trust.trusted_snapshot
    def current(db,source):
        if mode()=='trust':raise trust.problem(503,'FICTIONAL_GEC_TRUST_UNAVAILABLE','Injected fictional GEC trust unavailability; no production provider outage is claimed.')
        return original(db,source)
    monkeypatch.setattr(trust,'trusted_snapshot',current)
    from services import schedule_application_service as applications
    original_versions=applications.versions
    def versions(*args,**kwargs):
        if mode()=='history':raise trust.problem(503,'FICTIONAL_HISTORY_UNAVAILABLE','Injected fictional history read failure.')
        return original_versions(*args,**kwargs)
    monkeypatch.setattr(applications,'versions',versions)
    probe=socket.socket();probe.bind(("127.0.0.1",0));frontend_port=probe.getsockname()[1];probe.close()
    origin=f"http://localhost:{frontend_port}"
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS",origin)
    owned=socket.socket();owned.bind(("127.0.0.1",0));owned.listen(128);port=owned.getsockname()[1]
    wrapper=CORSMiddleware(app,allow_origins=[origin],allow_credentials=True,allow_methods=["GET","POST","PUT","OPTIONS"],allow_headers=["Content-Type","X-CSRF-Token"])
    server=uvicorn.Server(uvicorn.Config(wrapper,host="127.0.0.1",port=port,log_level="error",access_log=False))
    # This owned HTTP server needs sockets, not asyncio subprocess transports.
    # A local selector loop avoids Windows Proactor connection-reset teardown
    # leaks without changing production configuration or global event policy.
    worker=threading.Thread(target=lambda:asyncio.run(server.serve(sockets=[owned]),loop_factory=asyncio.SelectorEventLoop),daemon=True)
    stop_file=tmp_path/'d16-http.stop';watch_done=threading.Event()
    def watch():
        while not watch_done.wait(.03):
            if stop_file.exists():server.should_exit=True;return
    watcher=threading.Thread(target=watch,daemon=True)
    try:
        worker.start();watcher.start();end=time.monotonic()+10
        while not server.started and worker.is_alive() and time.monotonic()<end:time.sleep(.05)
        assert server.started,"Owned D16 HTTP fixture did not start"
        config={"backend":f"http://localhost:{port}","frontendPort":frontend_port,"password":f.password,"faultFile":str(fault),"publishFile":str(f.publish_file),"stopFile":str(stop_file),"recordId":f.confirmation["record_id"],"revisionId":f.confirmation["revision_id"]}
        with open(os.devnull,"w",encoding="utf-8") as sink,redirect_stdout(sink):
            try:
                result=subprocess.run(["node","tests/functionalReadiness.live.mjs"],cwd=Path(__file__).resolve().parents[3]/"frontend",
                    input=json.dumps(config),capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=150)
            except subprocess.TimeoutExpired as error:
                captured=error.stdout or b''
                if isinstance(captured,bytes):captured=captured.decode('utf-8',errors='replace')
                # Return public scenario diagnostics to pytest capture, never stdin.
                import sys
                print(sanitize(captured),file=sys.__stdout__)
                raise
        print(sanitize(result.stdout))
        if result.stderr:print(sanitize(result.stderr))
        assert result.returncode==0,"Live D16 fixture failed; sanitized scenario evidence retained"
    finally:
        watch_done.set();watcher.join(2)
        server.should_exit=True;worker.join(15);owned.close()
        event.remove(ScheduleApplication,'after_insert',storage_failure)
        assert not worker.is_alive(),"Owned D16 HTTP fixture did not stop"
