"""Explicit fictional-only bridge to the unchanged K/L/H bounded optimizer.

No default service, main registration, institutional storage or resume/restore.
"""
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
import threading
from services.ga_run_authority import RunError, canonical, digest, uuid
from services.ga_worker_contract import fictional_source, Limits
from services.ga_supervised_worker import Worker as SupervisedWorker
from services.ga_windows_supervisor import alive
from services.ga_research_ledger import Ledger, VERSION, MAX_EVENTS
from services.ga_research_context import derive, verify_consumption, ResearchComparison
from services import saved_best_policy


def configured_service():
    return None


class ResearchWorker(SupervisedWorker):
    """Observe the original protocol; never replace child or optimizer logic."""
    bridge=None

    def _heartbeat(self, principal, run, owner, fence):
        if self.bridge is None:raise RunError('RESEARCH_BRIDGE_REQUIRED')
        with self.bridge.qualified(principal, run, 'execute'):
            return super()._heartbeat(principal,run,owner,fence)

    def _exchange(self, request, remaining, max_message, heartbeat):
        response,spent=super()._exchange(request,remaining,max_message,heartbeat)
        row=heartbeat()
        proof=verify_consumption(self,row,response)
        with self.storage.transaction() as db:
            self.store.fenced(db,row['actor'],row['id'],row['executor'],row['fence'])
            self.bridge.ledger.save_proof(db,row['id'],proof)
        # A proof observed before commit is not sufficient for qualification.
        # K still validates and atomically persists checkpoint/projection/tip.
        return response,spent

    def _run(self, principal, run, owner, fence):
        try:super()._run(principal,run,owner,fence)
        finally:
            try:self.bridge.observe(principal,run)
            except Exception:
                # Original lifecycle/checkpoints remain durable even if extra
                # observation capacity is exhausted. Never fabricate an ACK.
                self.bridge.observation_failures[run]='RESEARCH_OBSERVATION_NOT_COMMITTED'


class ResearchBridge:
    def __init__(self, worker, permit, *, initialize=False):
        fictional_source()
        if type(worker) is not ResearchWorker:raise RunError('RESEARCH_QUALIFIED_WORKER_REQUIRED')
        self.worker=worker;self.permit=permit.validate();self.lock=threading.RLock();self.observation_failures={}
        self.ledger=Ledger(worker.storage,digest(asdict(permit)),initialize=initialize)
        worker.bridge=self

    def actor(self, principal):
        actor=self.worker.coordinator.actor(principal)
        if actor!=self.permit.actor:raise RunError('RESEARCH_LOCAL_AUTHORITY_REQUIRED',403)
        return actor

    @contextmanager
    def source(self, principal):
        actor=self.actor(principal);c=self.worker.coordinator
        with c.source.guard(actor,self.permit.department,self.permit.catalog):
            record=c.source.catalog.snapshot(self.permit.department,self.permit.catalog)
            if record.prepared_bundle.fingerprint!=self.permit.prepared_fingerprint:
                raise RunError('RESEARCH_APPROVED_SOURCE_CHANGED')
            yield

    @contextmanager
    def qualified(self, principal, run, action='status'):
        self.ledger.guard();actor=self.actor(principal)
        row=self.worker.coordinator.inspect(principal,run,action)
        if row['department']!=self.permit.department or row['catalog']!=self.permit.catalog:
            raise RunError('RESEARCH_SCOPE_MISMATCH',403)
        with self.worker.coordinator.authorized(self.worker.coordinator.context(actor,row,action),row['policy']):
            with self.source(principal):yield row

    def capabilities(self, principal):
        self.actor(principal)
        with self.source(principal):pass
        return dict(contract=VERSION,fictional_research_execution=True,institutional_optimization=False,
            institutional_saved_best_promotion=False,continuous_dashboard_enabled=False,seven_day_qualified=False,
            active_checkpoint_restore=False,pause_resume_exposed=False,maximum_wall_seconds=600,
            maximum_events_per_run=MAX_EVENTS,authority='EXPLICIT_SERVER_FICTIONAL_PERMIT_PLUS_SCOPED_MANDATE',
            warning='Fictional research only. Not institutional approval, publication or production readiness.')

    def admit(self, principal, request_id, limits=Limits()):
        uuid(request_id);limits.validate()
        with self.lock,self.source(principal):
            status=self.worker.admit(principal,self.permit.department,request_id,self.permit.catalog,limits)
            run=status['run_id']
            with self.qualified(principal,run,'admit') as row:
                ctx=derive(row,self.permit)
                with self.worker.storage.transaction() as db:self.ledger.register(db,run,ctx)
            return self.observe(principal,run)

    def start(self, principal, run):
        with self.lock,self.qualified(principal,run,'execute'):
            current=self.observe(principal,run)
            if current['state'] in {'COMPLETED','STOPPED'}:return current
            if current['state'] in {'INTERRUPTED','RECOVERY_REQUIRED','FAILED','RESOURCE_LIMITED'}:
                raise RunError('RESEARCH_RECOVERY_QUARANTINE_REQUIRED')
            self.worker.start(principal,run)
        return self.observe(principal,run)

    def stop(self, principal, run):
        with self.qualified(principal,run,'stop'):
            self.worker.command(principal,run,'stop')
        return self.observe(principal,run)

    def _state(self, db, row):
        state=row['state'];reason=row['reason'];processes=db.execute('SELECT * FROM l_processes WHERE run=?',(row['id'],)).fetchall()
        if row['executor'] and row['lease']<=self.worker.clock():
            orphan=any(p['status']=='ACTIVE' and alive(p['pid'],p['created']) for p in processes)
            return ('RECOVERY_REQUIRED' if orphan else 'INTERRUPTED'),'EXPIRED_OWNER_LEASE_ORPHAN_ALIVE' if orphan else 'EXPIRED_OWNER_LEASE'
        if state=='FAILED' and reason=='GA_WORKER_TIME_BUDGET':return 'RESOURCE_LIMITED',reason
        # A child crash is not automatically a CPU/memory-limit diagnosis.
        return state,reason

    def observe(self, principal, run):
        """Backfill durable original lifecycle events; no invented per-generation data."""
        with self.qualified(principal,run) as _initial:
            with self.worker.storage.transaction() as db:
                row=self.worker.store.row(db,self.actor(principal),run)
                ctx,items=self.ledger.check(db,run)
                if derive(row,self.permit)!=ctx:raise RunError('RESEARCH_CONTEXT_CHANGED')
                best=None
                if row['tip']:
                    self.worker.storage.pin(row)
                    committed,_raw=self.worker.store.checkpoint(db,row)
                    consumed=self.ledger.proof(db,run,row['sequence'])
                    if (consumed['inner_hash']!=committed['inner_hash'] or consumed['projection_fingerprint']!=row['best_hash']
                            or row['best'] is None or hashlib.sha256(row['best']).hexdigest()!=row['best_hash']):
                        raise RunError('RESEARCH_RESULT_TAMPERED')
                    best=consumed['best_fitness']
                if row['state']=='COMPLETED' and (not row['tip'] or row['generation']!=json.loads(row['bundle'])['configuration']['generations']):
                    raise RunError('RESEARCH_COMPLETION_UNVERIFIED')
                last=max((e.get('worker_event_id',0) for e in items),default=0)
                for event in db.execute('SELECT * FROM worker_events WHERE run=? AND id>? ORDER BY id',(run,last)).fetchall():
                    generation=None;fitness=None;checkpoint=None
                    if event['tip']:
                        cp=db.execute('SELECT * FROM worker_checkpoints WHERE run=? AND hash=?',(run,event['tip'])).fetchone()
                        if not cp:raise RunError('RESEARCH_CHECKPOINT_MISSING')
                        doc=json.loads(cp['raw']);proof=self.ledger.proof(db,run,cp['sequence'])
                        if doc['inner_hash']!=proof['inner_hash'] or hashlib.sha256(cp['raw']).hexdigest()!=cp['hash']:
                            raise RunError('RESEARCH_CONSUMPTION_TAMPERED')
                        generation=doc['generation'];checkpoint=cp['hash']
                        # K has already validated these observations before its
                        # atomic checkpoint/event commit. Projection digest is
                        # independently bound in the signed original child proof.
                        fitness=proof['best_fitness'] if 'best_fitness' in proof else None
                    payload=dict(contract=VERSION,run_id=run,context_id=digest(ctx),worker_event_id=event['id'],
                        worker_state=event['state'],generation=generation,best_so_far_fitness=fitness,
                        current_fitness=None,current_fitness_availability='UNAVAILABLE_NOT_EXPOSED',
                        satisfaction_metrics=None,satisfaction_availability='UNAVAILABLE_NOT_EMITTED',
                        checkpoint=checkpoint,exit_reason=event['reason'],observed_at=event['at'],
                        elapsed_wall_seconds=max(0,event['at']-row['created']),elapsed_classification='DERIVED_FROM_WORKER_EVENT_TIMESTAMPS',
                        generation_and_best_classification='OBSERVED_COMMITTED_BATCH_BOUNDARY' if checkpoint else 'UNAVAILABLE',
                        institutionally_authorized=False)
                    self.ledger.append(db,run,payload)
                state,reason=self._state(db,row)
                _,items=self.ledger.check(db,run)
                if state in {'INTERRUPTED','RECOVERY_REQUIRED'} and (not items or items[-1].get('recovery_state')!=state):
                    self.ledger.append(db,run,dict(run_id=run,recovery_state=state,reason=reason,
                        observed_at=self.worker.clock(),classification='DERIVED_FROM_EXPIRED_LEASE_AND_PROCESS_LIVENESS',
                        active_restore=False,worker_event_id=last))
                ctx,items=self.ledger.check(db,run)
                return dict(run_id=run,context_id=digest(ctx),state=state,worker_state=row['state'],reason=reason,
                    generation=None if row['generation']<0 else row['generation'],checkpoint_sequence=row['sequence'],
                    best_so_far_fitness=best,current_fitness=None,current_fitness_availability='UNAVAILABLE_NOT_EXPOSED',
                    telemetry_count=len(items),context_qualification='TRUSTED_FICTIONAL_CONSUMPTION' if row['tip'] else 'UNVERIFIED_NOT_CONSUMED',
                    production_admission='BLOCKED',saved_best_production_promotion=False,continuous_ui='DISABLED',
                    seven_day='NO_GO',active_restore=False,observation_failure=self.observation_failures.get(run))

    def telemetry(self, principal, run):
        self.observe(principal,run)
        with self.qualified(principal,run):
            with self.worker.storage.connection() as db:return self.ledger.check(db,run)[1]

    def qualified_result(self, principal, run):
        with self.qualified(principal,run,'result'):
            with self.worker.storage.transaction() as db:
                row=self.worker.store.row(db,self.actor(principal),run)
                ctx,_items=self.ledger.check(db,run)
                if derive(row,self.permit)!=ctx:raise RunError('RESEARCH_CONTEXT_CHANGED')
                if row['state'] not in {'COMPLETED','STOPPED'} or not row['tip'] or row['best'] is None:
                    raise RunError('RESEARCH_CONSUMPTION_MISSING')
                self.worker.storage.pin(row)
                doc,raw=self.worker.store.checkpoint(db,row)
                proof=self.ledger.proof(db,run,row['sequence'])
                if proof['inner_hash']!=doc['inner_hash'] or proof['projection_fingerprint']!=row['best_hash']:
                    raise RunError('RESEARCH_CONSUMPTION_TAMPERED')
                restored=self.worker._validate(row,doc,raw)
                if hashlib.sha256(row['best']).hexdigest()!=row['best_hash']:raise RunError('RESEARCH_RESULT_TAMPERED')
                result=json.loads(row['best'])
                restored.control.request_stop();expected=restored.run()
                if any(expected[k]!=result[k] for k in ['schedule','best_fitness','history','fitness_breakdown','faculty_analysis']):
                    raise RunError('RESEARCH_RESULT_TAMPERED')
                return ctx,result

    def candidate(self, principal, run):
        ctx,result=self.qualified_result(principal,run)
        with self.qualified(principal,run) as row:
            session=self.worker.coordinator._session(row)
        keys=sorted(str(s.number)+'::'+str(s.section.code) for s in session.working['templates'][0])
        return dict(format='ccs-ga-chromosome',version=1,best_fitness=result['best_fitness'],subject_keys=keys,schedule=result['schedule'])

    def compare_best(self, principal, run):
        # Fixed, private research-only namespace; caller cannot choose a path or
        # supply candidate fitness/context. Never touches application Saved Best.
        self.actor(principal)
        result=saved_best_policy.consider(self.worker.storage.root/'RESEARCH-BEST.json',
            self.candidate(principal,run),ResearchComparison(self,principal,run))
        return dict(classification=result.classification,reason=result.reason,updated=result.updated,
            storage_scope='FICTIONAL_RESEARCH_ONLY',production_promotion=False)
