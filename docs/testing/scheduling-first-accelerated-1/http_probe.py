"""Real loopback API/listener restart; fictional private SQLite; no GA/browser."""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time
from uuid import UUID

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'backend'))


def main():
    from services.ga_worker_contract import fictional_source
    fictional_source()
    from tests.test_prototype_inputs import configured, Directory, CHAIR_ID, FACULTY_ID, FACULTY
    from tests.test_prototype_workload import ACTOR, OTHER
    from services.prototype_inputs import Inputs
    from routers.prototype_inputs import create_app
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from identity_models import Base, User, FacultyIdentityRecord
    from services import auth_service as auth
    import uvicorn
    inputs, _ = configured()
    engine = create_engine('sqlite:///'+str(inputs.storage.root/'identity.sqlite3'), connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    password = secrets.token_urlsafe(24)
    with Session(engine) as db, db.begin():
        db.add(FacultyIdentityRecord(id=UUID(FACULTY.faculty_id), display_code='SYN-F2', name='Fictional Faculty 2'))
        for actor, name, role, faculty in [(ACTOR, 'scheduler', 'admin', None), (CHAIR_ID, 'chair', 'admin', None),
            (FACULTY_ID, 'faculty', 'faculty', UUID(FACULTY.faculty_id)), (OTHER, 'unscoped', 'admin', None)]:
            db.add(User(id=UUID(actor), username=name+'@fictional.invalid', role=role, faculty_id=faculty, password_hash=auth.hash_password(password)))
    def identity_db():
        with Session(engine) as db:
            yield db
    records = []
    try:
        for reopened in [False, True]:
            if reopened:
                inputs = Inputs(inputs.workload, Directory(), root=inputs.storage.root)
            sock = socket.socket()
            sock.bind(('127.0.0.1', 0))
            base = 'http://127.0.0.1:'+str(sock.getsockname()[1])
            os.environ['AUTH_ALLOWED_ORIGINS'] = base
            os.environ['AUTH_COOKIE_SECURE'] = 'false'
            server = uvicorn.Server(uvicorn.Config(create_app(inputs, identity_db), log_level='critical', access_log=False, lifespan='off'))
            thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=False)
            thread.start()
            try:
                until = time.monotonic()+10
                while not server.started and thread.is_alive() and time.monotonic() < until:
                    time.sleep(.01)
                assert server.started, 'OWNED_INPUT_API_STARTUP_FAILED'
                previous = records[0] if reopened else None
                child = subprocess.run(['node', 'tests/prototypeInputs.live.mjs'], cwd=ROOT/'frontend',
                    input=json.dumps(dict(base=base, password=password, reopened=reopened, previous=previous)),
                    capture_output=True, text=True, encoding='utf-8', timeout=45)
                assert child.returncode == 0, child.stderr
                records.append(json.loads(child.stdout))
            finally:
                server.should_exit = True
                thread.join(10)
                sock.close()
                assert not thread.is_alive(), 'OWNED_INPUT_API_EXIT_UNVERIFIED'
    finally:
        password = ''
        engine.dispose()
    print(json.dumps(dict(scope='REAL_NODE_HTTP_FRONTEND_MODEL_FASTAPI_SESSIONS_NEW_SQLITE_NO_BROWSER_NO_WORKER',
        records=records, scenario_checks=sum(len(x['scenarios']) for x in records),
        owned_API_exits_verified=True, actual_listener_and_service_reconstruction=True,
        OS_process_restart=False, native_workers=0, browser_scenarios=0, institutional_operations=False)))


if __name__ == '__main__':
    main()
