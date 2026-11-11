"""Opt-in fictional operator adapter. No configured provider or engine changes."""
from dataclasses import asdict
from contextlib import contextmanager
import json
import sqlite3
import threading
import time
from services.ga_worker_contract import fictional_source, Limits
from services.ga_research_bridge import ResearchBridge
from services.ga_research_continuity import ContinuityObserver
from services.ga_run_authority import Context, RunError, canonical, digest, uuid

VERSION='fictional-research-operator-v1'


@contextmanager
def read_guard(bridge,principal):
    """Match heartbeat authority -> source -> SQLite order, including reads."""
    actor=bridge.actor(principal)
    context=Context(actor,bridge.permit.department,'status',catalog_reference=bridge.permit.catalog)
    with bridge.worker.coordinator.authorized(context),bridge.source(principal):yield


class IdleObservations:
    """Same four read-only contracts, explicitly unavailable while work owns a lease.

    Full reconstruction is never skipped for verified results. Defer it so a
    reader cannot hold source/authority locks across the worker heartbeat.
    """
    def __init__(self,base):self.base=base
    def capabilities(self,p):return self._read(p,'capabilities')
    def _idle(self,p):
        with self.base.snapshot(p) as db:
            if db.execute('SELECT COUNT(*) FROM runs WHERE executor IS NOT NULL').fetchone()[0]:raise RunError('OPERATOR_ACTIVE_OBSERVATION_DEFERRED',503)
    def _read(self,p,method,*args):
        self.base.bridge.actor(p)
        lock=self.base.bridge.lock
        if not lock.acquire(timeout=2):raise RunError('OPERATOR_OBSERVATION_BUSY',503)
        try:
            with read_guard(self.base.bridge,p):
                self._idle(p);return getattr(self.base,method)(p,*args)
        finally:lock.release()
    def listing(self,p,offset=0,limit=10):return self._read(p,'listing',offset,limit)
    def detail(self,p,run):return self._read(p,'detail',run)
    def telemetry(self,p,run,after=0,limit=64):return self._read(p,'telemetry',run,after,limit)


class Operator:
    def __init__(self,bridge,*,initialize=False,clock=time.time):
        fictional_source()
        if type(bridge) is not ResearchBridge:raise RunError('OPERATOR_RESEARCH_BRIDGE_REQUIRED')
        self.bridge=bridge;self.full_observer=ContinuityObserver(bridge);self.observer=IdleObservations(self.full_observer);self.clock=clock;self.lock=threading.RLock()
        bridge.ledger.guard()
        self.limits=Limits(total_generations=2,wall_seconds=60)
        self.binding=dict(contract=VERSION,permit=digest(asdict(bridge.permit)),limits=asdict(self.limits))
        if initialize:
            with bridge.worker.storage.transaction() as db:
                if db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]:raise RunError('OPERATOR_EMPTY_OWNED_STORE_REQUIRED')
                db.execute('CREATE TABLE operator_meta(doc BLOB NOT NULL,mac TEXT NOT NULL)')
                db.execute('CREATE TABLE operator_requests(id TEXT PRIMARY KEY,doc BLOB NOT NULL,mac TEXT NOT NULL)')
                db.execute('CREATE TABLE operator_events(seq INTEGER PRIMARY KEY,doc BLOB NOT NULL,mac TEXT NOT NULL)')
                doc=dict(**self.binding,expires=self.clock()+300,audit_count=0,audit_head=None)
                db.execute('INSERT INTO operator_meta VALUES(?,?)',(canonical(doc),bridge.ledger.mac(doc)))
        with bridge.worker.storage.connection() as db:self._guard(db)

    @contextmanager
    def _locked(self):
        if not self.lock.acquire(timeout=2):raise RunError('OPERATOR_BUSY_RETRY_SAME_REQUEST',409)
        try:
            if not self.bridge.lock.acquire(timeout=2):raise RunError('OPERATOR_BUSY_RETRY_SAME_REQUEST',409)
            try:yield
            finally:self.bridge.lock.release()
        finally:self.lock.release()

    def _guard(self,db):
        rows=db.execute('SELECT * FROM operator_meta').fetchall()
        if len(rows)!=1:raise RunError('OPERATOR_METADATA_INVALID')
        doc=json.loads(rows[0]['doc'])
        if not self.bridge.ledger.matches(doc,rows[0]['mac']) or any(doc.get(k)!=v for k,v in self.binding.items()):raise RunError('OPERATOR_BINDING_CHANGED')
        events=db.execute('SELECT * FROM operator_events ORDER BY seq').fetchall()
        parent=None;latest={}
        for i,row in enumerate(events,1):
            item=json.loads(row['doc'])
            if row['seq']!=i or item.get('parent')!=parent or not self.bridge.ledger.matches(item,row['mac']):raise RunError('OPERATOR_AUDIT_CHANGED')
            parent=row['mac']
            latest[item['request']]=(bytes(row['doc']),row['mac'])
        if doc.get('audit_count')!=len(events) or doc.get('audit_head')!=parent:raise RunError('OPERATOR_AUDIT_ANCHOR_CHANGED')
        requests=db.execute('SELECT * FROM operator_requests').fetchall()
        if len(requests)!=len(latest) or any(latest.get(r['id'])!=(bytes(r['doc']),r['mac']) for r in requests):raise RunError('OPERATOR_REQUEST_AUDIT_CHANGED')
        if len(events)>128:raise RunError('OPERATOR_AUDIT_CAPACITY')
        return doc,len(events),parent

    def _record(self,request,action,run,phase,code=None):
        b=self.bridge
        b.ledger.guard()  # Never open an auxiliary connection under our write transaction.
        with b.worker.storage.transaction() as db:
            meta,count,parent=self._guard(db)
            if count>=128:raise RunError('OPERATOR_AUDIT_CAPACITY')
            doc=dict(request=request,action=action,run=run,phase=phase,code=code,at=self.clock(),parent=parent)
            mac=b.ledger.mac(doc)
            if phase=='REQUEST':db.execute('INSERT INTO operator_requests VALUES(?,?,?)',(request,canonical(doc),mac))
            else:db.execute('UPDATE operator_requests SET doc=?,mac=? WHERE id=?',(canonical(doc),mac,request))
            db.execute('INSERT INTO operator_events VALUES(?,?,?)',(count+1,canonical(doc),mac))
            meta.update(audit_count=count+1,audit_head=mac)
            db.execute('UPDATE operator_meta SET doc=?,mac=?',(canonical(meta),b.ledger.mac(meta)))

    def capabilities(self,principal):
        b=self.bridge;b.actor(principal);b.ledger.guard()
        with self._locked(),read_guard(b,principal),b.worker.storage.connection() as db:
            doc,_,_=self._guard(db)
        return dict(contract=VERSION,fictional_only=True,production_admission='BLOCKED',continuous_ui='DISABLED',active_restore=False,
            institutional_saved_best_promotion=False,seven_day='NO_GO',start_available=self.clock()<doc['expires'],stop_available=True,
            context=asdict(b.permit),limits=asdict(self.limits),expires_at=doc['expires'],warning='Fictional research only; no institutional authorization. Stop requests are not verified termination.')

    def status(self,principal,run):
        uuid(run)
        return self.observer.detail(principal,run)

    def request_status(self,principal,request):
        """Read-only nonce mapping, never dispatch/retry an interrupted action."""
        uuid(request);self.bridge.actor(principal)
        # Observer.snapshot opens a read transaction before source validation.
        # Admission holds source then commits SQLite. Serialize them before
        # opening that read handle, just as IdleObservations does above.
        with self._locked(),read_guard(self.bridge,principal):return self._request_status(principal,request)

    def _request_status(self,principal,request):
        b=self.bridge
        with self.full_observer.snapshot(principal) as db:
            self._guard(db)
            audit=db.execute('SELECT doc FROM operator_requests WHERE id=?',(request,)).fetchone()
            if audit is None:raise RunError('OPERATOR_REQUEST_NOT_FOUND',404)
            doc=json.loads(audit['doc'])
            rows=db.execute('SELECT id FROM runs WHERE actor=? AND department=? AND catalog=? AND request_key=?',
                (b.actor(principal),b.permit.department,b.permit.catalog,request)).fetchall()
            if len(rows)>1:raise RunError('OPERATOR_REQUEST_BINDING_CHANGED')
            run=rows[0]['id'] if rows else doc['run']
            if rows and doc['run'] is not None and doc['run']!=run:raise RunError('OPERATOR_REQUEST_BINDING_CHANGED')
        return dict(contract=VERSION,request_id=request,phase=doc['phase'],run_id=run,
            runtime=self.runtime(principal,run) if run else None,execution_retried=False,
            message='Read-only mapping only. A recorded request is not proof of execution or completion.')

    def runtime(self,principal,run):
        """Owned lifecycle metadata only, no reconstructed schedule/fitness claim."""
        uuid(run);self.bridge.actor(principal)
        with self._locked():return self._runtime(principal,run)

    def _runtime(self,principal,run):
        uuid(run);b=self.bridge
        with b.qualified(principal,run,'status'):
            with b.worker.storage.connection() as db:
                row=b.worker.store.row(db,b.actor(principal),run)
                state,reason=b._state(db,row)
                processes=db.execute('SELECT status FROM l_processes WHERE run=?',(run,)).fetchall()
                event=db.execute('SELECT state,reason,tip,fence FROM worker_events WHERE run=? ORDER BY id DESC LIMIT 1',(run,)).fetchone()
                base=db.execute('SELECT state,executor,lease FROM runs WHERE id=?',(run,)).fetchone()
                fence=event is not None and (event['fence']==row['fence'] or row['state']=='STOPPED' and row['reason']=='USER_STOP' and event['fence']+1==row['fence'])
                terminal=(state in {'STOPPED','COMPLETED','FAILED','RESOURCE_LIMITED'} and event is not None and fence
                    and event['state']==row['state'] and event['reason']==row['reason'] and event['tip']==row['tip']
                    and base['state']=='WORKER_'+row['state'] and base['executor'] is None and base['lease']==0
                    and all(p['status']=='EXIT_VERIFIED' for p in processes))
            b.worker.storage.pin(row)
        return dict(contract=VERSION,run_id=run,recorded_state=state,reason=reason,terminal_cleanup_recorded=bool(terminal),
            result_verification='FULL_READ_ONLY_PROJECTION_REQUIRED',fitness=None,production_admission='BLOCKED')

    def control(self,principal,request,action,run=None):
        uuid(request)
        if action not in {'start','stop'}:raise RunError('OPERATOR_ACTION_UNSUPPORTED',404)
        if run is not None:uuid(run)
        b=self.bridge;b.actor(principal);b.ledger.guard()
        # Do not hold the source lock while the worker acquires authority then
        # source during heartbeat. Reuse original per-operation trust guards.
        with self._locked():
            with b.source(principal):pass
            with b.worker.storage.connection() as db:
                meta,count,_=self._guard(db)
                row=db.execute('SELECT * FROM operator_requests WHERE id=?',(request,)).fetchone()
                if row:
                    old=json.loads(row['doc'])
                    if not b.ledger.matches(old,row['mac']) or old['action']!=action or action=='stop' and old['run']!=run:raise RunError('OPERATOR_REQUEST_BINDING_CHANGED')
                    if old['phase']!='ACK':raise RunError('OPERATOR_REQUEST_INDETERMINATE')
                    return self._response(principal,old['run'],True)
                if action=='start' and self.clock()>=meta['expires']:raise RunError('OPERATOR_START_WINDOW_EXPIRED')
                if action=='start' and (db.execute('SELECT COUNT(*) FROM runs WHERE executor IS NOT NULL').fetchone()[0]
                        or any(t.is_alive() for t in b.worker.threads.values())):raise RunError('OPERATOR_ACTIVE_OR_UNCERTAIN_RUN',409)
                if count>125:raise RunError('OPERATOR_AUDIT_CAPACITY')
            # Validate stop ownership before recording a cross-run command.
            if action=='stop':
                with b.qualified(principal,run,'stop'):pass
            try:self._record(request,action,run,'REQUEST')
            except sqlite3.IntegrityError:raise RunError('OPERATOR_REQUEST_IN_PROGRESS') from None
            try:
                if action=='start':
                    run=b.admit(principal,request,self.limits)['run_id']
                    with b.worker.storage.connection() as db:
                        if self.clock()>=self._guard(db)[0]['expires']:raise RunError('OPERATOR_START_WINDOW_EXPIRED')
                    # Fresh admission only. Reuse original ownership/state
                    # claims and exact ResearchWorker; no resume or state repair.
                    with b.qualified(principal,run,'execute'):
                        state=b.worker.status(principal,run)
                        if state['state']!='CREATED':raise RunError('OPERATOR_FRESH_ADMISSION_REQUIRED')
                        b.worker.start(principal,run)
                else:
                    with b.qualified(principal,run,'stop'):b.worker.command(principal,run,'stop')
                result=self._response(principal,run,False)
            except (RunError,OSError,sqlite3.Error) as exc:
                code=exc.code if isinstance(exc,RunError) else 'OPERATOR_STORAGE_OR_EXECUTION_UNAVAILABLE'
                try:self._record(request,action,run,'FAILED',code)
                except (RunError,OSError,sqlite3.Error):pass  # REQUEST stays indeterminate, never an ACK.
                if isinstance(exc,RunError):raise
                raise RunError(code,503) from None
            self._record(request,action,run,'ACK')
            return result

    def _response(self,principal,run,replayed):
        runtime=self.runtime(principal,run)
        d=self.status(principal,run) if runtime['terminal_cleanup_recorded'] else None
        return dict(contract=VERSION,run_id=run,replayed=replayed,
            confirmation='DURABLE_TERMINAL_VERIFIED' if d and d['overview']['freshness']['state']=='TERMINAL' else 'REQUEST_RECORDED_NOT_TERMINATION',runtime=runtime,observation=d)
