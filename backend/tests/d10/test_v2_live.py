"""Owned real Edge/FastAPI/SQLite D10 smoke; credentials travel via private stdin."""
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
from tests.d10.test_v2_api import environment,setup,fixture,isolate


def test_actual_edge_fastapi_sqlite_constrained_flow(environment,monkeypatch):
    f=environment
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
        assert server.started,"Owned D10 HTTP fixture did not start"
        config={"backend":f"http://localhost:{port}","frontendPort":frontend_port,"password":f.password}
        with open(os.devnull,"w",encoding="utf-8") as sink,redirect_stdout(sink):
            result=subprocess.run(["node","tests/constrainedGA.live.mjs"],cwd=Path(__file__).resolve().parents[3]/"frontend",
                input=json.dumps(config),capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=150)
        print(sanitize(result.stdout))
        if result.stderr:print(sanitize(result.stderr))
        assert result.returncode==0,"Live D10 fixture failed; sanitized scenario evidence retained"
    finally:
        server.should_exit=True;worker.join(15);owned.close()
        assert not worker.is_alive(),"Owned D10 HTTP fixture did not stop"
