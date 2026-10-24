"""Owned real Edge/FastAPI/SQLite D12 smoke; credentials travel via private stdin."""
from contextlib import redirect_stdout
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
from tests.dashboard.test_chair_reviews import chair, setup, fixture


def test_actual_edge_fastapi_sqlite_chair_flow(chair,monkeypatch,tmp_path):
    f=chair
    from services import adjustment_schedule_service as source
    from contextlib import contextmanager
    from dataclasses import replace
    fault=tmp_path/'d12-stale.marker'
    original=f.provider
    @contextmanager
    def changed():
        with original() as value:
            yield replace(value,revision='f'*64) if fault.exists() else value
    monkeypatch.setattr(source,'institutional_schedule_source',changed)
    probe=socket.socket();probe.bind(("127.0.0.1",0));frontend_port=probe.getsockname()[1];probe.close()
    origin=f"http://localhost:{frontend_port}"
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS",origin)
    owned=socket.socket();owned.bind(("127.0.0.1",0));owned.listen(128);port=owned.getsockname()[1]
    wrapper=CORSMiddleware(app,allow_origins=[origin],allow_credentials=True,allow_methods=["GET","POST","OPTIONS"],allow_headers=["Content-Type","X-CSRF-Token"])
    server=uvicorn.Server(uvicorn.Config(wrapper,host="127.0.0.1",port=port,log_level="error",access_log=False))
    worker=threading.Thread(target=lambda:server.run(sockets=[owned]),daemon=True)
    try:
        worker.start();end=time.monotonic()+10
        while not server.started and worker.is_alive() and time.monotonic()<end:time.sleep(.05)
        assert server.started,"Owned D12 HTTP fixture did not start"
        config={"backend":f"http://localhost:{port}","frontendPort":frontend_port,"password":f.password,"faultFile":str(fault)}
        with open(os.devnull,"w",encoding="utf-8") as sink,redirect_stdout(sink):
            result=subprocess.run(["node","tests/chairReviews.live.mjs"],cwd=Path(__file__).resolve().parents[3]/"frontend",
                input=json.dumps(config),capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=150)
        print(sanitize(result.stdout))
        if result.stderr:print(sanitize(result.stderr))
        assert result.returncode==0,"Live D12 fixture failed; sanitized scenario evidence retained"
    finally:
        server.should_exit=True;worker.join(15);owned.close()
        assert not worker.is_alive(),"Owned D12 HTTP fixture did not stop"
