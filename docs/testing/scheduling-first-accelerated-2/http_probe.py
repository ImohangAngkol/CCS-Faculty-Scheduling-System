"""Real loopback review/export acceptance over genuinely generated offline GA.

No native worker, browser, ACL operation, institutional provider or DB is used.
"""
from contextlib import closing, redirect_stdout, redirect_stderr
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


class Discard:
    def write(self, value):
        return len(value)
    def flush(self):
        pass


def main():
    from services.ga_worker_contract import fictional_source
    fictional_source()
    with redirect_stdout(Discard()), redirect_stderr(Discard()):
        from tests.test_prototype_cycle import create, admit, finish, WorkflowDirectory
        from tests.test_prototype_inputs import CHAIR_ID, FACULTY_ID, FACULTY
        from tests.test_prototype_workload import ACTOR, OTHER, PRINCIPAL, change
        from services.prototype_cycle import Cycle
        from services.prototype_tip_witness import TipWitness
        from routers.prototype_cycle import create_app
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from identity_models import Base, User, FacultyIdentityRecord
        from services import auth_service as auth
        import uvicorn
        cycle = create(); cycle.inputs.workload.save(PRINCIPAL, change(**{'2': 3}))
        first, _ = admit(cycle); first = finish(cycle, first['run_id'])
        second, _ = admit(cycle); second = finish(cycle, second['run_id'])
        cycle.offline_qualification = False
    engine = create_engine('sqlite:///'+str(cycle.storage.root/'identity.sqlite3'), connect_args={'check_same_thread': False})
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
                cycle = Cycle(cycle.inputs, WorkflowDirectory(),
                    TipWitness(root=cycle.witness.storage.root, key_fingerprint=cycle.witness.key_fingerprint), root=cycle.storage.root)
            sock = socket.socket(); sock.bind(('127.0.0.1', 0))
            base = 'http://127.0.0.1:'+str(sock.getsockname()[1])
            os.environ['AUTH_ALLOWED_ORIGINS'] = base; os.environ['AUTH_COOKIE_SECURE'] = 'false'
            server = uvicorn.Server(uvicorn.Config(create_app(cycle, identity_db), log_level='critical', access_log=False, lifespan='off'))
            thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=False); thread.start()
            try:
                end = time.monotonic()+10
                while not server.started and thread.is_alive() and time.monotonic() < end:
                    time.sleep(.01)
                assert server.started, 'CYCLE_OWNED_LISTENER_START_FAILED'
                child = subprocess.run(['node', 'tests/prototypeCycle.live.mjs'], cwd=ROOT/'frontend',
                    input=json.dumps(dict(base=base, password=password, reopened=reopened,
                        first=first['run_id'], second=second['run_id'], expected=first['result'])),
                    capture_output=True, text=True, encoding='utf-8', timeout=45)
                assert child.returncode == 0, child.stderr
                records.append(json.loads(child.stdout))
            finally:
                server.should_exit = True; thread.join(10); sock.close()
                assert not thread.is_alive(), 'CYCLE_OWNED_LISTENER_EXIT_UNVERIFIED'
    finally:
        password = ''; engine.dispose()
    print(json.dumps(dict(scope='REAL_NODE_TCP_FRONTEND_MODEL_FASTAPI_SQLITE_OVER_GENUINE_ORIGINAL_IN_PROCESS_GA',
        records=records, scenario_checks=sum(len(r['scenarios']) for r in records),
        native_workers=0, browsers=0, OS_process_restart=False, actual_service_listener_and_witness_reconstruction=True,
        owned_API_listener_exits_verified=True, mocked_HTTP_responses=0, institutional_operations=False)))


if __name__ == '__main__':
    main()
