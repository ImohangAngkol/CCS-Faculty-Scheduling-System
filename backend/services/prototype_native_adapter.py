"""Versioned frozen-input adapter. Original Cycle/checkpoint files unchanged.

New private supervisor namespace only. Simulated transport never establishes
native execution. No seven-day clocks, generation caps or retention are raised.
"""
import base64
import csv
from contextlib import closing
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import time
from uuid import uuid4

from services.prototype_cycle import Cycle, identity
from services.prototype_continuation_supervisor import Supervisor, checkpoint_audit
from services.prototype_workload import canonical, digest, require
from services.prototype_native_transport import WindowsTransport, InProcessQualification, SEGMENT_SECONDS

VERSION = 'prototype-frozen-native-adapter-v1'


def release_fingerprint(transport):
    return digest(dict(contract=VERSION, mode=transport.kind,
        source={n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in
            ['prototype_native_adapter.py','prototype_native_transport.py','prototype_cycle.py',
             'prototype_continuation_supervisor.py','ga_windows_supervisor.py','ga_supervised_worker.py',
             'ga_worker_child.py','ga_worker_contract.py','ga_worker_store.py','ga_bounded_worker.py',
             'prototype_workload.py','prototype_scheduling.py']},
        resources=asdict(transport.resources) if transport.native else None))


class NativeAdapter:
    def __init__(self, cycle, *, transport=None, root=None):
        require(type(cycle) is Cycle, 'NATIVE_EXACT_CYCLE_REQUIRED')
        self.cycle = cycle
        self.transport = transport if transport is not None else WindowsTransport()
        require(type(self.transport) in {WindowsTransport, InProcessQualification}, 'NATIVE_SERVER_TRANSPORT_REQUIRED')
        self.release = release_fingerprint(self.transport)
        self.journal = Supervisor(cycle, root=root)  # Reuse finite journal, not its offline executor.
        self.ownership=digest(dict(root=str(self.journal.storage.root),release=self.release))
        self.marker = self.journal.storage.root/'native-release.json'
        self.document = dict(contract=VERSION, release=self.release, supervisor=self.journal.binding,
                             cycle=cycle.binding, transport=self.transport.kind,ownership=self.ownership)
        self.audit_errors = {}
        if root is None:
            with self.marker.open('x',encoding='utf-8') as stream:
                stream.write(canonical(self.document))
            with closing(self.journal.db()) as db, db:
                db.execute('CREATE TABLE native_attempts(run TEXT NOT NULL,nonce TEXT NOT NULL,owner TEXT NOT NULL,fence INTEGER NOT NULL,pid INTEGER,created INTEGER,mode TEXT NOT NULL,state TEXT NOT NULL,raw TEXT,PRIMARY KEY(run,nonce))')
        self.guard()

    def guard(self):
        self.journal.storage.check()
        require(self.release==release_fingerprint(self.transport) and self.marker.is_file() and not self.marker.is_symlink() and not self.marker.is_junction()
                and self.marker.read_text(encoding='utf-8') == canonical(self.document), 'NATIVE_ADAPTER_RELEASE_CHANGED')

    def _attempts(self, run):
        with closing(self.journal.db()) as db:
            events = self.journal._events(db, run)
            rows = list(db.execute('SELECT * FROM native_attempts WHERE run=? ORDER BY rowid', (run,)))
        for row in rows:
            require(row['mode']==self.transport.kind,'NATIVE_PROCESS_MODE_CORRUPT')
            intent=[e for e in events if e['event']=='SEGMENT_INTENT' and e.get('nonce')==row['nonce']]
            require(len(intent)==1 and (intent[0]['owner'],intent[0]['fence'])==(row['owner'],row['fence']), 'NATIVE_ATTEMPT_INTENT_MISMATCH')
            if row['raw'] is not None:
                end = [e for e in events if e['event']=='TRANSPORT_EXIT' and e.get('nonce')==row['nonce']]
                require(len(end)==1 and digest(json.loads(row['raw']))==end[0]['observation_fingerprint'], 'NATIVE_EXIT_RECORD_CORRUPT')
                observed=json.loads(row['raw'])
                require(observed['pid']==row['pid'] and observed['created_100ns']==row['created']
                        and observed['kind']==row['mode'], 'NATIVE_PROCESS_RECORD_CORRUPT')
            start = [e for e in events if e['event']=='TRANSPORT_STARTED' and e.get('nonce')==row['nonce']]
            if start:
                require(len(start)==1 and (start[0]['pid'],start[0]['created_100ns'],start[0]['owner'],start[0]['fence'])
                    == (row['pid'],row['created'],row['owner'],row['fence']), 'NATIVE_PROCESS_RECORD_CORRUPT')
                if row['raw'] is not None and self.transport.native:
                    require(json.loads(row['raw']).get('preservation')==start[0].get('preservation'), 'NATIVE_PRESERVATION_RECORD_CORRUPT')
            else:
                require(row['pid'] is None and row['created'] is None, 'NATIVE_UNJOURNALED_PROCESS')
        return rows

    def status(self, principal, run):
        self.guard()
        view = self.cycle.inspect(principal, run)
        self._registered(principal,run,create=False)
        journal = self.journal.status(principal, run)
        rows = self._attempts(run)
        proofs = [json.loads(r['raw']) for r in rows if r['raw'] is not None]
        real = bool(proofs) and len(proofs)==len(rows) and self.transport.native and all(p.get('exit_verified') is True for p in proofs)
        verified=real and view['result'] is not None and view['result']['native_supervision_verified'] is True
        view=dict(view,legacy_cycle_native_projection=view['native_verified'],native_verified=verified,
            execution_classification=view['result']['execution_mode'] if view['result'] else 'NOT_EXECUTED',
            physical_worker_termination='VERIFIED_OWNED_WINDOWS_JOB_EXIT' if real else 'NOT_VERIFIED')
        return dict(contract=VERSION, release=self.release, run=view, supervision=journal,
            transport=self.transport.kind, physical_exit_verified=real,
            native_result_verified=verified,
            attempt_count=len(rows), observations=proofs, failure_audit_error=self.audit_errors.get(run),
            recovery_death_observations=[e for e in journal['history'] if e['event']=='RECOVERY_PROCESS_DEATH_OBSERVED'],
            production_admission='BLOCKED', institutional_promotion=False, seven_day='NO_GO')

    def _heartbeat(self, principal, run, owner, fence):
        self.guard(); self.cycle.authorize(principal, 'run.segment')
        with closing(self.cycle.db()) as db:
            row = db.execute('SELECT * FROM control WHERE run=?',(run,)).fetchone()
            require(row['owner']==owner and row['fence']==fence and row['lease']>self.cycle.clock(), 'NATIVE_STALE_EXECUTOR')
        return row['desired']  # Cooperative Stop is honored at the next boundary.

    def _registered(self, principal, run, *, create):
        grant=self.cycle.authorize(principal,'run.segment' if create else 'run.read');actor=grant.actor_id
        with closing(self.cycle.db()) as db:
            try:
                if create:db.execute('BEGIN IMMEDIATE')
                admission,row,control,_segments=self.cycle._read(db,run,actor if grant.capacity=='SCHEDULER' else None)
                commands=self.cycle._commands(db,run)
                records=[d for d in commands if d.get('action')=='NATIVE_ADAPTER_OWNERSHIP']
                if records:
                    require(len(records)==1 and records[0]['ownership']==self.ownership
                            and records[0]['adapter_release']==self.release,'NATIVE_OWNERSHIP_CONTEXT_DIFFERENT')
                elif create:
                    require(control['sequence']==0 and control['state']=='ADMITTED_NATIVE_BLOCKED'
                            and not admission['shortages'],'NATIVE_FRESH_ADMISSION_REQUIRED_OR_INPUT_INFEASIBLE')
                    require(len(commands)<32,'NATIVE_OWNERSHIP_AUDIT_LIMIT')
                    doc=dict(run_id=run,sequence=len(commands)+1,parent=commands[-1]['fingerprint'] if commands else None,
                        actor=actor,action='NATIVE_ADAPTER_OWNERSHIP',ownership=self.ownership,adapter_release=self.release,
                        at=datetime.fromtimestamp(self.cycle.clock(),timezone.utc).isoformat())
                    self.cycle.capacity(db,len(canonical(doc).encode())+1024)
                    db.execute('INSERT INTO commands VALUES(?,?,?,?,?,?)',
                        (run,doc['sequence'],actor,str(uuid4()),canonical(doc),digest(doc)))
                if create:db.commit()
            except BaseException:
                if create:db.rollback()
                raise

    def _started(self, run, nonce, owner, fence, pid, created, mode, preservation=None):
        require(mode==self.transport.kind, 'NATIVE_TRANSPORT_MODE_CHANGED')
        require((type(pid) is int and pid>0 and type(created) is int and created>0) if self.transport.native
                else pid is None and created is None,'NATIVE_START_IDENTITY_REQUIRED')
        with closing(self.journal.db()) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                claim=self.journal._claim(db,run)
                require(claim['owner']==owner and claim['fence']==fence and claim['nonce']==nonce, 'NATIVE_STALE_EXECUTOR')
                self.journal._append(db,run,'TRANSPORT_STARTED',nonce=nonce,owner=owner,fence=fence,
                    pid=pid,created_100ns=created,mode=mode,preservation=preservation)
                db.execute("UPDATE native_attempts SET pid=?,created=?,state='STARTED' WHERE run=? AND nonce=?",(pid,created,run,nonce))
                db.commit()
            except BaseException:
                db.rollback();raise

    def _exited(self, run, nonce, observation):
        require(observation['kind']==self.transport.kind, 'NATIVE_TRANSPORT_MODE_CHANGED')
        if not self.transport.native:
            require(observation.get('exit_verified') is False and observation['pid'] is None
                    and observation['created_100ns'] is None, 'NATIVE_SIMULATED_EXIT_CANNOT_BE_VERIFIED')
        with closing(self.journal.db()) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                self.journal._append(db,run,'TRANSPORT_EXIT',nonce=nonce,
                    observation_fingerprint=digest(observation),native_verified=self.transport.native and observation.get('exit_verified') is True)
                db.execute('UPDATE native_attempts SET state=?,raw=? WHERE run=? AND nonce=?',
                    ('EXIT_VERIFIED' if observation.get('exit_verified') else 'NO_NATIVE_EXIT_PROOF',canonical(observation),run,nonce))
                db.commit()
            except BaseException:
                db.rollback();raise

    def step(self, principal, run, nonce):
        self.guard(); identity(nonce)
        grant=self.cycle.authorize(principal,'run.segment')
        view=self.cycle.inspect(principal,run)
        self.transport.validate()  # Fail BEFORE intent/launch when the gate is absent.
        self._registered(principal,run,create=True)
        owner=str(uuid4()); before=time.monotonic()
        with closing(self.journal.db()) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                history=self.journal._events(db,run); old=self.journal._claim(db,run)
                done=[e for e in history if e.get('nonce')==nonce and e['event'] in {'VERIFIED_SEGMENT','RECOVERED_COMMITTED_SEGMENT'}]
                if done:
                    require(done[-1]['actor']==grant.actor_id,'NATIVE_NONCE_OWNER')
                    db.rollback();return self.status(principal,run)
                require(not any(e.get('nonce')==nonce for e in history),'NATIVE_NONCE_NEEDS_RECOVERY')
                require(old is None or old['state']=='ACKNOWLEDGED','NATIVE_RECOVERY_REQUIRED')
                require(view['sequence']==(old['observed_sequence'] if old else 0),'NATIVE_UNREGISTERED_CHECKPOINT_ADVANCE')
                require(view['state'] not in {'COMPLETED','STOPPED','INPUT_INFEASIBLE'},'NATIVE_TERMINAL_OR_INFEASIBLE')
                owner_fence=1 if old is None else old['fence']+1
                lease=self.cycle.clock()+SEGMENT_SECONDS
                self.journal._append(db,run,'SEGMENT_INTENT',nonce=nonce,actor=grant.actor_id,owner=owner,fence=owner_fence,
                    before_sequence=view['sequence'],before_tip=view['tip'],lease_until=lease,adapter_release=self.release)
                db.execute('INSERT OR REPLACE INTO claims VALUES(?,?,?,?,?,?,?,?,?,NULL)',
                    (run,nonce,grant.actor_id,owner,owner_fence,lease,'ACTIVE',view['sequence'],view['tip']))
                db.execute('INSERT INTO native_attempts VALUES(?,?,?,?,NULL,NULL,?,?,NULL)',
                    (run,nonce,owner,owner_fence,self.transport.kind,'INTENT'))
                db.commit()
            except BaseException:
                db.rollback();raise
        cycle_fence=None
        try:
            with closing(self.cycle.db()) as db:
                try:
                    db.execute('BEGIN IMMEDIATE')
                    admission,row,control,segments=self.cycle._read(db,run,grant.actor_id)
                    require(not admission['shortages'] and control['lease']<=self.cycle.clock() and run not in self.cycle.active,
                            'NATIVE_CYCLE_ALREADY_EXECUTING')
                    require(control['state'] not in {'COMPLETED','STOPPED','INPUT_INFEASIBLE'},'NATIVE_TERMINAL_OR_INFEASIBLE')
                    require((control['sequence'],control['tip'])==(view['sequence'],view['tip']),'NATIVE_CYCLE_ADVANCED')
                    if control['desired']=='STOP':
                        db.execute("UPDATE control SET state='STOPPED',owner=NULL,lease=0,fence=fence+1 WHERE run=?",(run,))
                        db.commit()
                        self._ack(principal,run,nonce,owner,owner_fence,'VERIFIED_SEGMENT','STOP_BEFORE_DISPATCH_NO_WORKER')
                        return self.status(principal,run)
                    require(control['sequence']<8 and admission['config']['generations']+1<=8,'NATIVE_CHECKPOINT_COUNT_CAP')
                    remaining=min(SEGMENT_SECONDS,admission['deadline']-self.cycle.clock(),600-control['spent'])
                    require(remaining>0,'NATIVE_LIFETIME_EXHAUSTED')
                    frozen=self.cycle.inputs.prepared(principal,admission['preparation_id'],internal_bundle=True)
                    require(frozen.fingerprint==admission['bundle_fingerprint'],'NATIVE_FROZEN_INPUT_CHANGED')
                    cycle_fence=control['fence']+1
                    db.execute("UPDATE control SET state='NATIVE_SEGMENT_RUNNING',owner=?,fence=?,lease=? WHERE run=?",
                        (owner,cycle_fence,min(lease,admission['deadline']),run))
                    db.commit()
                except BaseException:
                    db.rollback();raise
            from services.ga_worker_contract import VERSION as CHILD_VERSION, implementation
            target=segments[-1][0]['generation']+1 if segments else 0
            previous=segments[-1] if segments else None
            request=dict(contract=CHILD_VERSION,implementation=implementation(),run=admission['optimizer_run_id'],
                bundle=base64.b64encode(row['bundle']).decode(),bundle_hash=admission['bundle_fingerprint'],rng=json.loads(row['rng']),
                checkpoint=base64.b64encode(previous[1]['checkpoint']).decode() if previous else None,
                inner_hash=previous[0]['inner_fingerprint'] if previous else None,
                sequence=previous[0]['inner_sequence'] if previous else 0,
                inner_parent=previous[0]['inner_parent'] if previous else None,target=target)
            response=self.transport.execute(request,remaining=remaining,
                heartbeat=lambda:self._heartbeat(principal,run,owner,cycle_fence),
                started=lambda pid,created,mode,**meta:self._started(run,nonce,owner,owner_fence,pid,created,mode,**meta),
                exited=lambda observation:self._exited(run,nonce,observation),
                ownership=dict(store=self.journal.binding,run=run))
            public,raw,doc=self._qualify(admission,row,control,previous,target,response,cycle_fence,time.monotonic()-before)
            attempts=self._attempts(run); observation=json.loads(attempts[-1]['raw'])
            require(not self.transport.native or observation.get('exit_verified') is True and observation.get('exit_code')==0,
                    'NATIVE_SUCCESSFUL_EXIT_REQUIRED')
            public.update(execution_mode=self.transport.kind,native_supervision_verified=self.transport.native,
                          adapter_release=self.release,process_observation_fingerprint=digest(observation))
            doc['result_fingerprint']=digest(public)
            doc['elapsed_seconds']=time.monotonic()-before
            require(doc['elapsed_seconds']<SEGMENT_SECONDS,'NATIVE_PARENT_SEGMENT_TIME_BUDGET')
            with closing(self.cycle.db()) as db:
                try:
                    db.execute('BEGIN IMMEDIATE')
                    _admission,_row,fresh,_segments=self.cycle._read(db,run,grant.actor_id)
                    require((fresh['owner'],fresh['fence'],fresh['tip'])==(owner,cycle_fence,control['tip'])
                            and fresh['lease']>self.cycle.clock() and self.cycle.clock()<admission['deadline']
                            and fresh['spent']+doc['elapsed_seconds']<=600,'NATIVE_STALE_COMMIT_OR_LIFETIME')
                    self.cycle.capacity(db,len(raw)+len(canonical(public).encode())+len(canonical(doc).encode())+1024)
                    db.execute('INSERT INTO segments VALUES(?,?,?,?,?,?)',
                        (run,doc['sequence'],canonical(doc),digest(doc),raw,canonical(public)))
                    state='STOPPED' if fresh['desired']=='STOP' else 'COMPLETED' if target==admission['config']['generations'] else 'BETWEEN_SEGMENTS'
                    db.execute('UPDATE control SET state=?,owner=NULL,lease=0,sequence=?,tip=?,spent=spent+? WHERE run=?',
                        (state,doc['sequence'],digest(doc),doc['elapsed_seconds'],run))
                    self.cycle.authorize(principal,'run.segment');db.commit()
                    self.cycle._witness(run,dict(admission=row['hash'],sequence=control['sequence'],tip=control['tip']),
                        dict(admission=row['hash'],sequence=doc['sequence'],tip=digest(doc)))
                except BaseException:
                    db.rollback();raise
            self._ack(principal,run,nonce,owner,owner_fence,'VERIFIED_SEGMENT','COMMITTED_NEW_BOUNDARY')
            return self.status(principal,run)
        except BaseException as primary:
            try:
                with closing(self.journal.db()) as db:
                    try:
                        db.execute('BEGIN IMMEDIATE');claim=self.journal._claim(db,run)
                        if (claim['owner'],claim['fence'],claim['state']) in {
                                (owner,owner_fence,'ACTIVE'),(owner,owner_fence,'RECOVERY_REQUIRED')}:
                            if cycle_fence is not None:
                                self.cycle._failure(run,owner,cycle_fence,grant.actor_id,getattr(primary,'code','NATIVE_SEGMENT_FAILED'))
                            self.journal._append(db,run,'SEGMENT_FAILED',nonce=nonce,actor=grant.actor_id,
                                code=getattr(primary,'code','NATIVE_SEGMENT_FAILED'),cleanup_code=getattr(primary,'cleanup_code',None),primary_preserved=True)
                            db.execute("UPDATE claims SET state='RECOVERY_REQUIRED' WHERE run=?",(run,))
                        db.commit()  # An old failure cannot overwrite a completed acknowledgement.
                    except BaseException:
                        db.rollback();raise
            except BaseException:
                self.audit_errors[run]='NATIVE_FAILURE_AUDIT_UNAVAILABLE'
            raise

    def _qualify(self, admission, row, control, previous, target, response, fence, elapsed):
        from services.ga_worker_contract import VERSION as CHILD_VERSION, implementation
        from services.ga_input_bundle import InputBundle, canonical as wire, digest as wire_digest
        from services.ga_bundle_optimizer import Session
        require(set(response)=={'contract','implementation','run','inner','inner_hash','sequence','inner_parent','projection','rng_hash','receipt'}
                and response['contract']==CHILD_VERSION and response['implementation']==implementation()
                and response['run']==admission['optimizer_run_id'],'NATIVE_RESPONSE_BINDING')
        raw=base64.b64decode(response['inner'],validate=True)
        expected_sequence=previous[0]['inner_sequence']+1 if previous else 1
        parent=previous[0]['inner_fingerprint'] if previous else None
        require(0<len(raw)<=8*1024*1024 and hashlib.sha256(raw).hexdigest()==response['inner_hash']
                and response['sequence']==expected_sequence and response['inner_parent']==parent,'NATIVE_CHECKPOINT_BINDING')
        bundle=InputBundle.from_bytes(bytes(row['bundle']),admission['optimizer_run_id'],admission['bundle_fingerprint'])
        check=Session.restore(bundle,raw,run_id=bundle.run_id,expected_fingerprint=response['inner_hash'],
            expected_sequence=expected_sequence,expected_parent=parent)
        state=check.resume_state
        require(state['generation_completed']==target,'NATIVE_GENERATION_MISMATCH')
        from services.ga_checkpoint_service import rng_to_json
        require(response['rng_hash']==wire_digest(wire(rng_to_json(state['random_state']))),'NATIVE_RNG_BINDING')
        check.control.request_stop();expected=check.run()  # Original reporting only, before another RNG draw.
        require(check.runtime.random.getstate()==state['random_state'] and response['projection']==expected
                and expected['saved_best_updated'] is False,'NATIVE_PROJECTION_OR_RNG_MISMATCH')
        receipt=response['receipt']
        require(receipt['verification_status']=='VERIFIED' and receipt['run_id']==bundle.run_id
                and receipt['bundle_fingerprint']==bundle.fingerprint and receipt['checkpoint_fingerprint']==response['inner_hash']
                and receipt['optimizer_fingerprint']==admission['optimizer_fingerprint']
                and receipt['configuration_fingerprint']==admission['configuration_fingerprint']
                and receipt['scoring_context_fingerprint']==admission['scoring_fingerprint'],'NATIVE_CONSUMPTION_BINDING')
        from services.chromosome_service import payload_to_chromosome
        from services.prototype_scheduling import assess_snapshot
        data=bundle.materialize(bundle.run_id)
        keys=sorted(str(s.number)+'::'+str(s.section.code) for s in data['templates'][0])
        candidate=payload_to_chromosome(dict(format='ccs-ga-chromosome',version=1,best_fitness=expected['best_fitness'],
            subject_keys=keys,schedule=expected['schedule']),*data['templates'])
        qualification=assess_snapshot(self.cycle.inputs.workload,{'policy':admission['provenance']['minimum_policy']},candidate)
        public=dict(original_result=expected,qualification=qualification,receipt=receipt,provenance=admission['provenance'],
                    bundle_fingerprint=bundle.fingerprint,generated=True,schedule_promoted=False)
        doc=dict(run_id=row['id'],sequence=control['sequence']+1,parent=control['tip'],generation=target,
            inner_fingerprint=response['inner_hash'],inner_sequence=expected_sequence,inner_parent=parent,
            fence=fence,elapsed_seconds=elapsed,original_rng_fingerprint=digest(rng_to_json(state['random_state'])),
            adapter_release=self.release,result_fingerprint=None)
        return public,raw,doc

    def _ack(self, principal, run, nonce, owner, fence, event, recovery_kind):
        view=self.cycle.inspect(principal,run); proof=checkpoint_audit(self.cycle,principal,run)
        actor=self.cycle.authorize(principal,'run.segment').actor_id
        with closing(self.journal.db()) as db:
            try:
                db.execute('BEGIN IMMEDIATE');claim=self.journal._claim(db,run)
                require((claim['owner'],claim['fence'],claim['nonce'],claim['actor'])==(owner,fence,nonce,actor),'NATIVE_STALE_ACK')
                require(claim['state'] in {'ACTIVE','RECOVERY_REQUIRED'},'NATIVE_ACK_ALREADY_RECORDED')
                self.journal._append(db,run,event,nonce=nonce,actor=actor,fence=fence,sequence_observed=view['sequence'],
                    tip_observed=view['tip'],checkpoint=proof,recovery_kind=recovery_kind,
                    native_transport=self.transport.native)
                db.execute("UPDATE claims SET state='ACKNOWLEDGED',lease=0,observed_sequence=? WHERE run=?",(view['sequence'],run));db.commit()
            except BaseException:
                db.rollback();raise

    def recover(self, principal, run):
        self.guard();actor=self.cycle.authorize(principal,'run.recover').actor_id
        self._registered(principal,run,create=False)
        with closing(self.journal.db()) as db:
            try:
                db.execute('BEGIN IMMEDIATE')  # Serializes recovery across controllers/processes.
                claim=self.journal._claim(db,run)
                require(claim is not None and claim['actor']==actor and claim['state'] in {'ACTIVE','RECOVERY_REQUIRED'}
                        and claim['lease']<=self.cycle.clock(),'NATIVE_RECOVERY_NOT_IDLE')
                for attempt in self._attempts(run):
                    if attempt['pid'] is not None:
                        require(self.transport.native and self.transport.prove_dead(attempt['pid'],attempt['created']), 'NATIVE_OLD_WORKER_STILL_ALIVE')
                        self.journal._append(db,run,'RECOVERY_PROCESS_DEATH_OBSERVED',nonce=attempt['nonce'],actor=actor,
                            pid=attempt['pid'],created_100ns=attempt['created'],
                            method='READ_ONLY_PID_PLUS_CREATION_IDENTITY_NOT_ALIVE',
                            historical_exit_code_reconstructed=False,job_accounting_reconstructed=False)
                    elif self.transport.native:
                        require(False,'NATIVE_WORKER_IDENTITY_UNVERIFIED')
                view=self.cycle.inspect(principal,run)
                require(view['sequence'] in {claim['before_sequence'],claim['before_sequence']+1}
                        and view['sequence']>0,'NATIVE_NO_VERIFIED_CHECKPOINT_RECOVERY')
                proof=checkpoint_audit(self.cycle,principal,run)
                with closing(self.cycle.db()) as source,source:
                    source.execute('BEGIN IMMEDIATE')
                    _a,_r,control,_s=self.cycle._read(source,run,actor)
                    require(control['lease']<=self.cycle.clock(),'NATIVE_CYCLE_OWNER_ACTIVE')
                    require(self.cycle.clock()<_a['deadline'] and control['spent']<600,'NATIVE_RECOVERY_LIFETIME_EXHAUSTED')
                    if view['state'] not in {'COMPLETED','STOPPED'}:
                        source.execute("UPDATE control SET owner=NULL,lease=0,state='BETWEEN_SEGMENTS',fence=fence+1 WHERE run=?",(run,))
                kind='ACK_ALREADY_COMMITTED_BOUNDARY' if view['sequence']>claim['before_sequence'] else 'RETRY_PRIOR_VERIFIED_BOUNDARY_NO_NEW_WORK'
                self.journal._append(db,run,'RECOVERED_COMMITTED_SEGMENT',nonce=claim['nonce'],actor=actor,
                    fence=claim['fence'],sequence_observed=view['sequence'],tip_observed=view['tip'],checkpoint=proof,
                    recovery_kind=kind,native_transport=self.transport.native)
                db.execute("UPDATE claims SET state='ACKNOWLEDGED',lease=0,observed_sequence=? WHERE run=?",(view['sequence'],run))
                self.cycle.authorize(principal,'run.recover');db.commit()
            except BaseException:
                db.rollback();raise
        return self.status(principal,run)

    def request_stop(self, principal, run, nonce):
        self.guard()
        return self.journal.request_stop(principal,run,nonce)

    def export_run(self, principal, run, kind):
        self.cycle.authorize(principal,'schedule.export')
        status=self.status(principal,run)
        require(status['run']['result'] is not None,'NATIVE_GENUINE_RESULT_REQUIRED')
        if kind=='json':raw=canonical(status)
        elif kind=='csv':
            stream=io.StringIO(newline='');writer=csv.writer(stream)
            writer.writerow(['run_id','execution_mode','generation','original_observation_json'])
            for observation in status['run']['result']['original_result']['history']:
                writer.writerow([run,self.transport.kind,observation['generation'],canonical(observation)])
            raw=stream.getvalue()
        elif kind=='txt':raw='FICTIONAL ORIGINAL GA / '+self.transport.kind+'\n'+canonical(status)+'\n'
        else:require(False,'NATIVE_EXPORT_FORMAT_INVALID',422)
        require(len(raw.encode())<=256*1024,'NATIVE_EXPORT_SIZE_LIMIT',413)
        return raw
