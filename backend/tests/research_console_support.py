"""Explicit fictional operator fixture, importable ONLY in an owned snapshot."""
from pathlib import Path
import json
import secrets
import socket
import threading
import time
from uuid import UUID,uuid4
from services.ga_worker_contract import fictional_source
fictional_source()
from services.ga_run_authority import canonical
from services.ga_research_observation import Observer
from services.ga_research_bridge import ResearchWorker,ResearchBridge
from services.ga_research_context import ResearchPermit
from services.ga_trusted_runs import Coordinator
from services.ga_owned_store import Store
from tests.bounded_worker_support import dependencies
from tests.trusted_run_support import ACTOR,DEPT,CATALOG,PRINCIPAL,OTHER


def free_port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]


class Environment:
    def __repr__(self):return '<Owned fictional console; credentials withheld>'
    def __init__(self,bridge=None,allow_engine=lambda e:None):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from identity_models import Base,User
        from services import auth_service as auth
        if bridge is None:
            a,c,_=dependencies(1);bundle=c.catalog.record.prepared_bundle
            worker=ResearchWorker(Coordinator(Store.create(max_runs=4),a,c),initialize=True)
            bridge=ResearchBridge(worker,ResearchPermit(ACTOR,DEPT,CATALOG,bundle.fingerprint,'FICTIONAL-YEAR','FICTIONAL-TERM','FICTIONAL-DATASET'),initialize=True)
        self.bridge=bridge;self.observer=Observer(bridge);self.origin='http://localhost:'+str(free_port())
        self.engine=create_engine('sqlite:///'+str(bridge.worker.storage.root/'CONSOLE-AUTH.sqlite3'),connect_args={'check_same_thread':False})
        allow_engine(self.engine);Base.metadata.create_all(self.engine);self._password=secrets.token_urlsafe(24)
        with Session(self.engine) as db,db.begin():
            for actor,label in [(ACTOR,'research'),(OTHER,'unscoped')]:db.add(User(id=UUID(actor),username=label+'@fictional.invalid',role='admin',password_hash=auth.hash_password(self._password)))
        self.runs={}
    def prepare(self):
        b=self.bridge
        for name in ['completed','missing','interrupted']:self.runs[name]=b.admit(PRINCIPAL,str(uuid4()))['run_id']
        run=self.runs['completed'];b.start(PRINCIPAL,run);end=time.monotonic()+90
        while time.monotonic()<end:
            state=b.observe(PRINCIPAL,run)
            if state['state'] in {'COMPLETED','FAILED','RESOURCE_LIMITED'}:break
            time.sleep(.05)
        if state['state']!='COMPLETED':raise RuntimeError('Fictional fixture worker failed: '+str(state['reason']))
        # Explicit injected expired-owner metadata, not a fresh physical crash.
        with b.worker.storage.transaction() as db:
            db.execute("UPDATE runs SET executor='fictional-expired-owner',lease=1,state='WORKER_RUNNING' WHERE id=?",(self.runs['interrupted'],))
            db.execute("UPDATE workers SET state='RUNNING' WHERE run=?",(self.runs['interrupted'],))
    def app(self,observer=None):
        from sqlalchemy.orm import Session
        import database
        from services import auth_service as auth
        from routers.research_observations import create_app
        from fastapi.middleware.cors import CORSMiddleware
        def db():
            with Session(self.engine) as session:yield session
        app=create_app(observer or self.observer)
        app.dependency_overrides[database.get_identity_db]=db;app.dependency_overrides[auth.authenticated_db]=db
        app.add_middleware(CORSMiddleware,allow_origins=[self.origin],allow_credentials=True,allow_methods=['GET','POST'],allow_headers=['Content-Type','X-CSRF-Token'])
        return app
    def serve(self):
        import uvicorn
        sock=socket.socket();sock.bind(('127.0.0.1',0));self.backend='http://localhost:'+str(sock.getsockname()[1]);self.sock=sock
        self.server=uvicorn.Server(uvicorn.Config(self.app(),log_level='critical',access_log=False,lifespan='off'))
        self.thread=threading.Thread(target=lambda:self.server.run(sockets=[sock]),daemon=False);self.thread.start();end=time.monotonic()+10
        while not self.server.started and time.monotonic()<end:time.sleep(.01)
        if not self.server.started:raise RuntimeError('Owned API startup failed')
    def private_browser_input(self):return dict(username='research@fictional.invalid',password=self._password,runs=self.runs,port=int(self.origin.rsplit(':',1)[1]))
    def close(self):
        if hasattr(self,'server'):
            self.server.should_exit=True;self.thread.join(10);self.sock.close()
            if self.thread.is_alive():raise RuntimeError('Owned API cleanup failed')
        self.engine.dispose()
        if not self.bridge.worker.close(PRINCIPAL,timeout=20)['quiescent']:raise RuntimeError('Owned worker cleanup failed')
