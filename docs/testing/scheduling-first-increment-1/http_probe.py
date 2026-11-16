"""Bounded real TCP acceptance using a new fictional policy/auth store only."""
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
sys.path.insert(0, str(ROOT / 'backend'))


def main():
    from services.ga_worker_contract import fictional_source
    fictional_source()
    from tests.test_prototype_workload import service_for, FictionalGrants, ACTOR, OTHER
    from services.prototype_workload import WorkloadService, Store
    from routers.prototype_workload import create_app
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from identity_models import Base, User
    from services import auth_service
    import uvicorn
    service, _ = service_for()
    engine = create_engine('sqlite:///'+str(service.store.root/'auth.sqlite3'), connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    password = secrets.token_urlsafe(24)
    with Session(engine) as db, db.begin():
        for actor, name in [(ACTOR, 'editor'), (OTHER, 'unscoped')]:
            db.add(User(id=UUID(actor), username=name+'@fictional.invalid', role='admin', password_hash=auth_service.hash_password(password)))
    def identity_db():
        with Session(engine) as db:
            yield db
    records = []
    try:
        for reopened in [False, True]:
            if reopened:
                service = WorkloadService(service.scope, service.bundle, FictionalGrants(), Store(service.store.root, service.binding))
            sock = socket.socket()
            sock.bind(('127.0.0.1', 0))
            base = 'http://127.0.0.1:'+str(sock.getsockname()[1])
            os.environ['AUTH_ALLOWED_ORIGINS'] = base
            os.environ['AUTH_COOKIE_SECURE'] = 'false'
            server = uvicorn.Server(uvicorn.Config(create_app(service, identity_db), log_level='critical', access_log=False, lifespan='off'))
            thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=False)
            thread.start()
            try:
                end = time.monotonic() + 10
                while not server.started and thread.is_alive() and time.monotonic() < end:
                    time.sleep(.01)
                assert server.started, 'OWNED_API_STARTUP_FAILED'
                command = ['node', 'tests/prototypeWorkload.live.mjs']
                result = subprocess.run(command, cwd=ROOT/'frontend', input=json.dumps(dict(base=base, password=password, reopened=reopened)),
                                        capture_output=True, text=True, encoding='utf-8', timeout=45)
                assert result.returncode == 0, result.stderr
                records.append(json.loads(result.stdout))
            finally:
                server.should_exit = True
                thread.join(10)
                sock.close()
                assert not thread.is_alive(), 'OWNED_API_EXIT_UNVERIFIED'
    finally:
        password = ''
        engine.dispose()
    print(json.dumps(dict(records=records, scenarios=sum(len(x['scenarios']) for x in records),
                         owned_API_listener_exits_verified=True, actual_listener_restart=True,
                         SQLite_engine_disposed=True, OS_process_restart=False, GA_worker_started=False,
                         institutional_operations=False)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
