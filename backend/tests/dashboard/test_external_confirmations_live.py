"""Owned real HTTP/Edge smoke. Actual auth; synthetic SQLite/resources; no PostgreSQL."""
import copy
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time

import pytest
import uvicorn
from starlette.middleware.cors import CORSMiddleware

from main import app
from services import external_schedule_service as intake
from services import external_schedule_verification_service as authority
from tests.dashboard.test_my_schedule import fixture
from tests.dashboard.test_external_preview import CTX


@pytest.mark.parametrize("authorized",[False,True])
def test_d9_live_ledger_with_synthetic_storage(fixture,monkeypatch,authorized):
    from services.evidence_sanitization import sanitize
    from confirmation_models import ConfirmationBase,guard_sql,transition_sql,ConfirmationEvent
    from sqlalchemy.orm import Session
    from sqlalchemy import select
    from tests.dashboard.evidence_support import install_fictional
    from tests.dashboard.test_external_confirmations import permit
    ConfirmationBase.metadata.create_all(fixture.engine)
    with fixture.engine.begin() as db:
        for sql in guard_sql('sqlite')+transition_sql('sqlite'):db.exec_driver_sql(sql)
    monkeypatch.setattr(intake,'context',lambda:copy.deepcopy(CTX))
    monkeypatch.setattr(authority,'verification_for',lambda key,**kwargs:None)
    if authorized:install_fictional(monkeypatch);permit(monkeypatch)
    frontend_probe=socket.socket();frontend_probe.bind(('127.0.0.1',0));frontend_port=frontend_probe.getsockname()[1];frontend_probe.close()
    monkeypatch.setenv('AUTH_ALLOWED_ORIGINS',f'http://localhost:{frontend_port}')
    owned=socket.socket();owned.bind(('127.0.0.1',0));owned.listen(128)
    port=owned.getsockname()[1]
    # The production middleware was constructed before the test's ephemeral
    # origin existed. Add an exact-origin loopback wrapper for this fixture;
    # actual session Origin/CSRF checks remain unchanged inside FastAPI.
    fixture_app=CORSMiddleware(app,allow_origins=[f'http://localhost:{frontend_port}'],allow_credentials=True,
                               allow_methods=['GET','POST','OPTIONS'],allow_headers=['Content-Type','X-CSRF-Token'])
    server=uvicorn.Server(uvicorn.Config(fixture_app,host='127.0.0.1',port=port,log_level='error',access_log=False))
    worker=threading.Thread(target=lambda:server.run(sockets=[owned]),daemon=True)
    try:
        worker.start();deadline=time.monotonic()+10
        while not server.started and worker.is_alive() and time.monotonic()<deadline:time.sleep(.05)
        assert server.started,'Owned synthetic HTTP server did not start'
        private_config={'backend':f'http://localhost:{port}','frontendPort':frontend_port,'password':fixture.password,'authorized':authorized}
        # Private stdin only: never command line, environment, file, report or screenshot.
        child_env=dict(os.environ)
        if 'D9_SCREENSHOT_DIR' in child_env:child_env['D9_SCREENSHOT_DIR']=str(Path(child_env['D9_SCREENSHOT_DIR'])/('fictional-authorized' if authorized else 'default-blocked'))
        result=subprocess.run(['node','tests/externalConfirmations.live.mjs'],cwd=Path(__file__).resolve().parents[3]/'frontend',input=json.dumps(private_config),capture_output=True,text=True,encoding='utf-8',errors='replace',env=child_env,timeout=150)
        print(sanitize(result.stdout))
        if result.stderr:print(sanitize(result.stderr))
        with Session(fixture.engine) as db:
            assert len(db.scalars(select(ConfirmationEvent)).all())==(3 if authorized else 0)
        assert result.returncode==0,'Live browser smoke failed; sanitized scenario output retained above'
    finally:
        server.should_exit=True;worker.join(15);owned.close()
        assert not worker.is_alive(),'Owned HTTP server did not stop'
