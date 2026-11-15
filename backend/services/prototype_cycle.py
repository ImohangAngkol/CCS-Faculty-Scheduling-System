"""Versioned fictional scheduling/review and finite continuation foundation.

The only executor here is an explicitly enabled OFFLINE qualification oracle.
It is never registered as an HTTP execution path or a native worker substitute.
Native resource/ownership/restart qualification and seven-day admission remain
blocked. The original Session, score, operators and checkpoint codec are reused.
"""
from contextlib import closing, ExitStack
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import random
import secrets
import sqlite3
import threading
import time
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from services.prototype_workload import Store, canonical, digest, require
from services.prototype_inputs import Grant, Inputs

VERSION = 'fictional-scheduling-continuation-v1'
MAX_STORED_BYTES = 64 * 1024 * 1024
FLAGS = dict(prototype_only=True, production_admission='BLOCKED', institutional_promotion=False,
             continuous_optimization='DISABLED', active_institutional_restore=False, seven_day='NO_GO')


class Admission(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    request_id: str
    preparation_id: str


class Decision(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    request_id: str
    expected_review: int = Field(ge=0)
    candidate_fingerprint: str = Field(pattern=r'^[a-f0-9]{64}$')
    decision: Literal['APPROVE', 'REJECT', 'REQUEST_REVISION']
    explanation: str = Field(min_length=10, max_length=1000)


def identity(value):
    require(type(value) is str and str(UUID(value)) == value, 'CYCLE_ID_INVALID', 422)
    return value


class Cycle:
    def __init__(self, inputs, directory=None, witness=None, *, root=None, offline_qualification=False,
                 clock=time.time, state_factory=None):
        require(type(inputs) is Inputs, 'CYCLE_INPUT_SERVICE_REQUIRED')
        self.inputs, self.directory, self.witness, self.clock = inputs, directory, witness, clock
        self.offline_qualification = offline_qualification
        self.state_factory = state_factory or (lambda: random.Random(secrets.randbits(256)).getstate())
        self.binding = digest(dict(contract=VERSION, inputs=inputs.binding, witness_identity=getattr(witness, 'binding', None),
            implementation=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
        self.storage = Store.create(self.binding) if root is None else Store(root, self.binding)
        self.path = self.storage.root/'cycle.sqlite3'
        self.active = set()
        self.failure_recording_errors = {}
        self.lock = threading.RLock()
        self._initializing = root is None
        if root is None:
            with self.path.open('xb'):
                pass
            with closing(self.db()) as db, db:
                db.executescript('''
CREATE TABLE metadata(binding TEXT NOT NULL);
CREATE TABLE runs(id TEXT PRIMARY KEY,actor TEXT NOT NULL,nonce TEXT NOT NULL,raw TEXT NOT NULL,hash TEXT NOT NULL,bundle BLOB NOT NULL,rng BLOB NOT NULL,UNIQUE(actor,nonce));
CREATE TABLE control(run TEXT PRIMARY KEY,state TEXT NOT NULL,desired TEXT,fence INTEGER NOT NULL,owner TEXT,lease REAL NOT NULL,sequence INTEGER NOT NULL,tip TEXT,spent REAL NOT NULL);
CREATE TABLE segments(run TEXT NOT NULL,sequence INTEGER NOT NULL,raw TEXT NOT NULL,hash TEXT NOT NULL,checkpoint BLOB NOT NULL,result TEXT NOT NULL,PRIMARY KEY(run,sequence));
CREATE TABLE reviews(run TEXT NOT NULL,sequence INTEGER NOT NULL,actor TEXT NOT NULL,nonce TEXT NOT NULL,raw TEXT NOT NULL,hash TEXT NOT NULL,PRIMARY KEY(run,sequence),UNIQUE(actor,nonce));
CREATE TABLE commands(run TEXT NOT NULL,sequence INTEGER NOT NULL,actor TEXT NOT NULL,nonce TEXT NOT NULL,raw TEXT NOT NULL,hash TEXT NOT NULL,PRIMARY KEY(run,sequence),UNIQUE(actor,nonce));
CREATE TABLE versions(version INTEGER PRIMARY KEY,raw TEXT NOT NULL,hash TEXT NOT NULL);
''')
                for table in ['runs', 'segments', 'reviews', 'versions', 'commands']:
                    for operation in ['UPDATE', 'DELETE']:
                        db.execute(f"CREATE TRIGGER immutable_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'immutable'); END")
                db.execute('INSERT INTO metadata VALUES(?)', (self.binding,))
        self._initializing = False
        with closing(self.db()) as db:
            require([tuple(r) for r in db.execute('SELECT binding FROM metadata')] == [(self.binding,)], 'CYCLE_STORAGE_BINDING')

    def db(self):
        self.storage.check()
        require(self.path.is_file() and not self.path.is_symlink() and not self.path.is_junction()
                and self.path.stat().st_size < 128*1024*1024, 'CYCLE_STORAGE_INVALID')
        db = sqlite3.connect(self.path.as_uri()+'?mode=rw', uri=True, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        if not self._initializing:
            try:
                require([tuple(row) for row in db.execute('SELECT binding FROM metadata')] == [(self.binding,)], 'CYCLE_STORAGE_BINDING')
            except Exception:
                db.close(); raise
        return db

    def authorize(self, principal, action, code=None):
        actor = identity(getattr(principal, 'user_id', None))
        try:
            grant = self.directory.grant(actor, self.inputs.workload.scope, action, code) if self.directory else None
            allowed = {'run.create': {'SCHEDULER'}, 'run.read': {'SCHEDULER', 'DEPARTMENT_CHAIR'},
                'run.segment': {'SCHEDULER'}, 'run.stop': {'SCHEDULER'}, 'run.recover': {'SCHEDULER'},
                'review.decide': {'DEPARTMENT_CHAIR'}, 'schedule.read': {'SCHEDULER', 'DEPARTMENT_CHAIR'},
                'schedule.export': {'SCHEDULER', 'DEPARTMENT_CHAIR'}, 'faculty.timetable': {'FACULTY_SELF'}}
            require(type(grant) is Grant and grant.actor_id == actor and grant.scope_digest == self.inputs.scope_digest
                and grant.action == action and grant.faculty_code == code and grant.reference.startswith('FICTIONAL-')
                and grant.capacity in allowed[action] and self.clock() < grant.expires_at <= self.clock()+300,
                'CYCLE_SCOPED_AUTHORITY_REQUIRED', 403)
            return grant
        except (ValueError, TypeError, AttributeError, KeyError):
            require(False, 'CYCLE_SCOPED_AUTHORITY_REQUIRED', 403)

    def capacity(self, db, extra, *, reserve=4096):
        used = db.execute('SELECT COALESCE(SUM(length(raw)+length(bundle)+length(rng)),0) FROM runs').fetchone()[0]
        used += db.execute('SELECT COALESCE(SUM(length(raw)+length(checkpoint)+length(result)),0) FROM segments').fetchone()[0]
        for table in ['commands', 'reviews', 'versions']:
            used += db.execute(f'SELECT COALESCE(SUM(length(raw)),0) FROM {table}').fetchone()[0]
        require(used+extra+reserve <= MAX_STORED_BYTES and self.path.stat().st_size+extra+reserve < 120*1024*1024,
                'CYCLE_DURABLE_STORAGE_CAPACITY', 413)

    def _witness(self, run, expected, replacement=None):
        require(self.witness is not None, 'CYCLE_INDEPENDENT_TIP_PROVIDER_REQUIRED', 503)
        require(self.witness.read(self.binding, run) == expected, 'CYCLE_TIP_WITNESS_MISMATCH')
        if replacement is not None:
            require(self.witness.advance(self.binding, run, expected, replacement) is True, 'CYCLE_TIP_COMMIT_UNCERTAIN')

    def _read(self, db, run, actor=None):
        row = db.execute('SELECT * FROM runs WHERE id=?', (identity(run),)).fetchone()
        require(row is not None, 'CYCLE_RUN_NOT_FOUND', 404)
        if actor is not None:
            require(row['actor'] == actor, 'CYCLE_RUN_OWNER_REQUIRED', 403)
        admission = json.loads(row['raw'])
        require(digest(admission) == row['hash'] and admission['binding'] == self.binding
                and hashlib.sha256(row['bundle']).hexdigest() == admission['bundle_fingerprint']
                and hashlib.sha256(row['rng']).hexdigest() == admission['initial_rng_fingerprint'], 'CYCLE_ADMISSION_CORRUPT')
        control = dict(db.execute('SELECT * FROM control WHERE run=?', (run,)).fetchone())
        segments, parent = [], None
        for record in db.execute('SELECT * FROM segments WHERE run=? ORDER BY sequence', (run,)):
            doc = json.loads(record['raw'])
            require(doc['run_id'] == run and doc['sequence'] == record['sequence'] == len(segments)+1
                and doc['parent'] == parent and digest(doc) == record['hash']
                and hashlib.sha256(record['checkpoint']).hexdigest() == doc['inner_fingerprint']
                and digest(json.loads(record['result'])) == doc['result_fingerprint'], 'CYCLE_SEGMENT_CORRUPT')
            receipt = json.loads(record['result'])['receipt']
            require(receipt['verification_status'] == 'VERIFIED' and receipt['run_id'] == admission['optimizer_run_id']
                and receipt['bundle_fingerprint'] == admission['bundle_fingerprint']
                and receipt['optimizer_fingerprint'] == admission['optimizer_fingerprint']
                and receipt['configuration_fingerprint'] == admission['configuration_fingerprint']
                and receipt['scoring_context_fingerprint'] == admission['scoring_fingerprint']
                and receipt['checkpoint_fingerprint'] == doc['inner_fingerprint'], 'CYCLE_CONSUMPTION_BINDING_INVALID')
            segments.append((doc, record))
            parent = record['hash']
        require((control['sequence'], control['tip']) == (len(segments), parent), 'CYCLE_TIP_CORRUPT')
        self._witness(run, dict(admission=row['hash'], sequence=len(segments), tip=parent))
        return admission, row, control, segments

    def admit(self, principal, command):
        require(self.witness is not None, 'CYCLE_INDEPENDENT_TIP_PROVIDER_REQUIRED', 503)
        grant = self.authorize(principal, 'run.create')
        require(type(command) is Admission, 'CYCLE_COMMAND_INVALID', 422)
        identity(command.request_id)
        prepared = self.inputs.prepared(principal, command.preparation_id)
        bundle = self.inputs.prepared(principal, command.preparation_id, internal_bundle=True)
        data = bundle.materialize(bundle.run_id)
        from services.ga_bundle_runtime import profile_fingerprint
        require(profile_fingerprint(data['templates']) == profile_fingerprint(self.inputs.data['templates']), 'CYCLE_RESOURCE_PROFILE_CHANGED')
        config = data['configuration']
        require(0 <= config['generations'] <= 20 and 2 <= config['population_size'] <= 8, 'CYCLE_FINITE_PROFILE_LIMIT')
        # The unchanged reporting path joins this priority frame to the model
        # cohort. A captured graph alone does not prove that join is complete.
        frame = data['legacy_preferences']
        require({'Faculty_Code', 'Faculty_Prio'} <= set(frame.columns), 'CYCLE_LEGACY_COHORT_COLUMNS_REQUIRED', 422)
        codes = list(frame['Faculty_Code'])
        require(len(codes) == len(set(codes)) and set(codes) == {f.code for f in data['templates'][1]}
                and all(type(p) is not bool and math.isfinite(float(p)) and float(p).is_integer() and float(p) >= 1
                        for p in frame['Faculty_Prio']), 'CYCLE_LEGACY_COHORT_PRIORITY_MISMATCH', 422)
        snapshot = prepared['provenance']['minimum_policy']
        faculty, minima = self.inputs.workload.minimums(snapshot)
        shortages = [dict(faculty_code=c, minimum=minima[c], eligible_units=faculty[c]['eligible_units'],
                          shortage=minima[c]-faculty[c]['eligible_units']) for c in minima if minima[c] > faculty[c]['eligible_units']]
        with closing(self.db()) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                old = db.execute('SELECT id,raw FROM runs WHERE actor=? AND nonce=?', (grant.actor_id, command.request_id)).fetchone()
                if old:
                    require(json.loads(old['raw'])['preparation_id'] == command.preparation_id, 'CYCLE_NONCE_REUSE_MISMATCH')
                    return self.inspect(principal, old['id'])
                require(db.execute('SELECT COUNT(*) FROM runs').fetchone()[0] < 16, 'CYCLE_RUN_CAPACITY')
                from services.ga_checkpoint_service import rng_to_json
                from services.ga_bundle_optimizer import Session
                initial_state = self.state_factory()
                rng = canonical(rng_to_json(initial_state)).encode()
                session = Session(bundle, run_id=bundle.run_id, random_state=initial_state)
                from services.ga_bundle_checkpoint import semantic_graph_fingerprint
                evaluation = digest(dict(resources=semantic_graph_fingerprint(data['templates']),
                    scoring=session.scoring_fingerprint, config=session.config_fingerprint, optimizer=session.optimizer_fingerprint,
                    minima=snapshot, weights=prepared['provenance']['weights_policy']['digest'],
                    preferences=prepared['provenance']['preferences_digest']))
                admission = dict(binding=self.binding, preparation_id=command.preparation_id, scope=prepared['provenance']['scope'],
                    provenance=prepared['provenance'], bundle_fingerprint=bundle.fingerprint, optimizer_run_id=bundle.run_id,
                    configuration_fingerprint=session.config_fingerprint, optimizer_fingerprint=session.optimizer_fingerprint,
                    scoring_fingerprint=session.scoring_fingerprint, evaluation_fingerprint=evaluation,
                    initial_rng_fingerprint=hashlib.sha256(rng).hexdigest(), initial_at=self.clock(), deadline=self.clock()+600,
                    config=config, shortages=shortages)
                run = str(uuid4())
                self.capacity(db, len(bundle._raw)+len(rng)+len(canonical(admission).encode())+1024)
                db.execute('INSERT INTO runs VALUES(?,?,?,?,?,?,?)', (run, grant.actor_id, command.request_id, canonical(admission), digest(admission), bundle._raw, rng))
                db.execute('INSERT INTO control VALUES(?,?,NULL,0,NULL,0,0,NULL,0)', (run, 'INPUT_INFEASIBLE' if shortages else 'ADMITTED_NATIVE_BLOCKED'))
                self.authorize(principal, 'run.create')
                db.commit()
                self._witness(run, None, dict(admission=digest(admission), sequence=0, tip=None))
            except Exception:
                db.rollback()
                raise
        return self.inspect(principal, run)

    def inspect(self, principal, run):
        grant = self.authorize(principal, 'run.read')
        with closing(self.db()) as db:
            admission, row, control, segments = self._read(db, run, grant.actor_id if grant.capacity == 'SCHEDULER' else None)
            result = json.loads(segments[-1][1]['result']) if segments else None
            reviews = self._reviews(db, run)
            commands = self._commands(db, run)
        return dict(contract=VERSION, **FLAGS, run_id=run, state=control['state'], sequence=control['sequence'],
            tip=control['tip'], preparation_id=admission['preparation_id'], provenance=admission['provenance'],
            evaluation_fingerprint=admission['evaluation_fingerprint'], result=result, shortages=admission['shortages'],
            latest_candidate_fingerprint=digest(result) if result else None, reviews=reviews, commands=commands,
            native_verified=False, browser_verified=False, generated=result is not None,
            execution_classification='ACTUAL_ORIGINAL_GA_IN_PROCESS_OFFLINE' if result else 'NOT_EXECUTED',
            segment_history=[doc for doc, _record in segments],
            physical_worker_termination='NOT_ESTABLISHED_NO_NATIVE_WORKER',
            checkpoint_witness='CALLER_SUPPLIED_PROVIDER_NOT_DEPLOYMENT_QUALIFIED')

    def listing(self, principal):
        grant = self.authorize(principal, 'run.read')
        with closing(self.db()) as db:
            ids = [r[0] for r in db.execute('SELECT id FROM runs ORDER BY id')]
        result = [self.inspect(principal, run) for run in ids if grant.capacity == 'DEPARTMENT_CHAIR'
                  or self._owner(run) == grant.actor_id]
        return result

    def _owner(self, run):
        with closing(self.db()) as db:
            row = db.execute('SELECT actor FROM runs WHERE id=?', (run,)).fetchone()
            return row[0] if row else None

    def _commands(self, db, run):
        result, parent = [], None
        for row in db.execute('SELECT raw,hash FROM commands WHERE run=? ORDER BY sequence', (run,)):
            doc = json.loads(row['raw'])
            require(doc['run_id'] == run and doc['sequence'] == len(result)+1 and doc['parent'] == parent
                    and digest(doc) == row['hash'], 'CYCLE_COMMAND_AUDIT_CORRUPT')
            parent = row['hash']; result.append(doc | {'fingerprint': parent})
        return result

    def request_stop(self, principal, run, nonce=None):
        grant = self.authorize(principal, 'run.stop')
        nonce = identity(nonce or str(uuid4()))
        with closing(self.db()) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                _admission, _row, control, _segments = self._read(db, run, grant.actor_id)
                old = db.execute('SELECT raw,hash FROM commands WHERE actor=? AND nonce=?', (grant.actor_id, nonce)).fetchone()
                if old:
                    doc = json.loads(old['raw'])
                    require(doc['run_id'] == run and digest(doc) == old['hash'], 'CYCLE_STOP_NONCE_MISMATCH')
                    return doc
                history = self._commands(db, run)
                accepted = control['state'] not in {'COMPLETED', 'STOPPED', 'INPUT_INFEASIBLE'}
                require(len(history) < 32, 'CYCLE_COMMAND_AUDIT_CAPACITY')
                doc = dict(run_id=run, sequence=len(history)+1, parent=history[-1]['fingerprint'] if history else None,
                    actor=grant.actor_id, stop_requested=accepted, termination_verified=False,
                    at=datetime.now(timezone.utc).isoformat())
                self.capacity(db, len(canonical(doc).encode())+1024)
                db.execute('INSERT INTO commands VALUES(?,?,?,?,?,?)', (run, doc['sequence'], grant.actor_id, nonce, canonical(doc), digest(doc)))
                if accepted:
                    db.execute("UPDATE control SET desired='STOP' WHERE run=?", (run,))
                self.authorize(principal, 'run.stop')
                db.commit()
                return doc
            except Exception:
                db.rollback(); raise

    def recover(self, principal, run):
        require(self.offline_qualification is True, 'CYCLE_NATIVE_RECOVERY_UNQUALIFIED', 503)
        grant = self.authorize(principal, 'run.recover')
        with closing(self.db()) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                admission, row, control, segments = self._read(db, run, grant.actor_id)
                require(control['state'] not in {'COMPLETED', 'STOPPED', 'INPUT_INFEASIBLE'} and segments
                        and control['lease'] <= self.clock() and run not in self.active
                        and self.clock() < admission['deadline'] and control['spent'] < 600, 'CYCLE_RECOVERY_NOT_IDLE')
                self._session(admission, row, segments)
                db.execute("UPDATE control SET state='BETWEEN_SEGMENTS',owner=NULL,lease=0,fence=fence+1 WHERE run=?", (run,))
                db.commit()
            except Exception:
                db.rollback(); raise
        return self.inspect(principal, run)

    def _session(self, admission, row, segments):
        from services.ga_input_bundle import InputBundle
        from services.ga_bundle_optimizer import Session
        from services.ga_checkpoint_service import rng_from_json
        bundle = InputBundle.from_bytes(bytes(row['bundle']), admission['optimizer_run_id'], admission['bundle_fingerprint'])
        if segments:
            doc, checkpoint = segments[-1]
            session = Session.restore(bundle, bytes(checkpoint['checkpoint']), run_id=bundle.run_id,
                expected_fingerprint=doc['inner_fingerprint'], expected_sequence=doc['inner_sequence'], expected_parent=doc['inner_parent'])
        else:
            session = Session(bundle, run_id=bundle.run_id, random_state=rng_from_json(json.loads(row['rng'])))
        require(session.optimizer_fingerprint == admission['optimizer_fingerprint'] and session.config_fingerprint == admission['configuration_fingerprint']
                and session.scoring_fingerprint == admission['scoring_fingerprint'], 'CYCLE_EXECUTION_CONTEXT_CHANGED')
        return session

    def step_offline(self, principal, run):
        """Genuine original GA; no endpoint calls this qualification-only oracle.

        Boundary/elapsed checks are cooperative, NOT an OS resource supervisor.
        A qualified native adapter remains mandatory before live admission.
        """
        require(self.offline_qualification is True, 'CYCLE_NATIVE_EXECUTION_UNQUALIFIED', 503)
        grant = self.authorize(principal, 'run.segment')
        with closing(self.db()) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                admission, row, control, segments = self._read(db, run, grant.actor_id)
                require(not admission['shortages'] and control['state'] not in {'COMPLETED', 'STOPPED'}, 'CYCLE_RUN_NOT_EXECUTABLE')
                if control['desired'] == 'STOP':
                    require(control['owner'] is None or control['lease'] <= self.clock(), 'CYCLE_ACTIVE_OWNER_STOP_PENDING')
                    db.execute("UPDATE control SET state='STOPPED',owner=NULL,lease=0,fence=fence+1 WHERE run=?", (run,))
                    db.commit()
                    return self.inspect(principal, run)
                require(control['lease'] <= self.clock() and self.clock() < admission['deadline'] and control['spent'] < 600, 'CYCLE_LEASE_OR_BUDGET')
                require(control['sequence'] < 8 and admission['config']['generations'] <= 2, 'CYCLE_OFFLINE_QUALIFICATION_PROFILE')
                owner, fence = str(uuid4()), control['fence']+1
                db.execute("UPDATE control SET state='QUALIFICATION_RUNNING',owner=?,lease=?,fence=? WHERE run=?",
                           (owner, self.clock()+60, fence, run))
                db.commit()
            except Exception:
                db.rollback(); raise
        with self.lock:
            require(run not in self.active, 'CYCLE_ALREADY_EXECUTING')
            self.active.add(run)
        started = time.monotonic()
        try:
            session = self._session(admission, row, segments)
            generation = segments[-1][0]['generation']+1 if segments else 0
            require(generation <= admission['config']['generations'], 'CYCLE_GENERATION_HORIZON_REACHED')
            def boundary(_kind, data):
                require(time.monotonic()-started < 60, 'CYCLE_SEGMENT_TIME_BUDGET')
                if data['generation'] >= generation:
                    session.control.request_pause()
            require(session.run(boundary) is None and session.checkpoint is not None, 'CYCLE_EXPECTED_BOUNDARY_CHECKPOINT')
            from services.ga_bundle_optimizer import Session
            projection = Session.restore(session.bundle, session.checkpoint, run_id=session.run_id,
                expected_fingerprint=session.checkpoint_fingerprint, expected_sequence=session.sequence, expected_parent=session.parent_fingerprint)
            projection.control.request_stop()
            result = projection.run()  # Original finalization; does not advance RNG.
            require(projection.runtime.random.getstate() == session.resume_state['random_state'], 'CYCLE_PROJECTION_RNG_CHANGED')
            require(result['best_fitness'] == session.resume_state['best_ever_fitness']
                    and result['history'] == session.resume_state['history']
                    and result['generations_completed'] == generation and result['saved_best_updated'] is False,
                    'CYCLE_ORIGINAL_BEST_OR_HISTORY_CHANGED')
            from services.chromosome_service import payload_to_chromosome
            data = session.bundle.materialize(session.run_id)
            keys = sorted(str(s.number)+'::'+str(s.section.code) for s in data['templates'][0])
            candidate = payload_to_chromosome(dict(format='ccs-ga-chromosome', version=1, best_fitness=result['best_fitness'], subject_keys=keys, schedule=result['schedule']), *data['templates'])
            from services.prototype_scheduling import assess_snapshot
            qualification = assess_snapshot(self.inputs.workload, {'policy': admission['provenance']['minimum_policy']}, candidate)
            public = dict(original_result=result, qualification=qualification, receipt=session.receipt(),
                provenance=admission['provenance'], bundle_fingerprint=session.bundle.fingerprint,
                execution_mode='ACTUAL_ORIGINAL_GA_OFFLINE_IN_PROCESS', native_supervision_verified=False,
                generated=True, schedule_promoted=False)
            require(public['receipt']['verification_status'] == 'VERIFIED', 'CYCLE_ORIGINAL_CONSUMPTION_NOT_VERIFIED')
            elapsed = time.monotonic()-started
            require(elapsed < 60 and len(session.checkpoint) <= 8*1024*1024, 'CYCLE_SEGMENT_RESOURCE_PROFILE')
            with closing(self.db()) as db:
                try:
                    db.execute('BEGIN IMMEDIATE')
                    fresh = dict(db.execute('SELECT * FROM control WHERE run=?', (run,)).fetchone())
                    require((fresh['owner'], fresh['fence'], fresh['tip']) == (owner, fence, control['tip'])
                        and fresh['lease'] > self.clock() and self.clock() < admission['deadline']
                        and fresh['spent']+elapsed <= 600, 'CYCLE_STALE_SEGMENT_OWNER')
                    require(db.execute('SELECT COALESCE(SUM(length(checkpoint)),0) FROM segments').fetchone()[0]+len(session.checkpoint) <= 64*1024*1024, 'CYCLE_CHECKPOINT_STORAGE_CAP')
                    doc = dict(run_id=run, sequence=control['sequence']+1, parent=control['tip'], generation=generation,
                        inner_fingerprint=session.checkpoint_fingerprint, inner_sequence=session.sequence, inner_parent=session.parent_fingerprint,
                        result_fingerprint=digest(public), fence=fence, elapsed_seconds=elapsed,
                        original_rng_fingerprint=hashlib.sha256(canonical(__import__('services.ga_checkpoint_service', fromlist=['rng_to_json']).rng_to_json(session.resume_state['random_state'])).encode()).hexdigest())
                    state = 'STOPPED' if fresh['desired'] == 'STOP' else 'COMPLETED' if generation == admission['config']['generations'] else 'BETWEEN_SEGMENTS'
                    self.capacity(db, len(session.checkpoint)+len(canonical(public).encode())+len(canonical(doc).encode())+1024)
                    db.execute('INSERT INTO segments VALUES(?,?,?,?,?,?)', (run, doc['sequence'], canonical(doc), digest(doc), session.checkpoint, canonical(public)))
                    db.execute('UPDATE control SET state=?,owner=NULL,lease=0,sequence=?,tip=?,spent=spent+? WHERE run=?', (state, doc['sequence'], digest(doc), elapsed, run))
                    self.authorize(principal, 'run.segment')
                    db.commit()
                    self._witness(run, dict(admission=row['hash'], sequence=control['sequence'], tip=control['tip']),
                        dict(admission=row['hash'], sequence=doc['sequence'], tip=digest(doc)))
                except Exception:
                    db.rollback(); raise
        except Exception as exc:
            try:
                self._failure(run, owner, fence, grant.actor_id, getattr(exc, 'code', 'CYCLE_OFFLINE_EXECUTION_FAILED'))
            except Exception:
                # Preserve the primary error; never overwrite it with teardown.
                self.failure_recording_errors[run] = 'CYCLE_FAILURE_AUDIT_UNAVAILABLE'
            raise
        finally:
            with self.lock:
                self.active.discard(run)
        return self.inspect(principal, run)

    def _failure(self, run, owner, fence, actor, code):
        with closing(self.db()) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT * FROM control WHERE run=?', (run,)).fetchone()
                if row is None or row['fence'] != fence:
                    return  # An older executor cannot change a newer owner.
                if row['owner'] == owner:
                    state = 'RECOVERY_REQUIRED' if row['sequence'] else 'FAILED_NO_CHECKPOINT'
                elif row['owner'] is None:
                    state = 'QUARANTINED_COMMIT_UNCERTAINTY'
                else:
                    return
                history = self._commands(db, run)
                require(len(history) < 32, 'CYCLE_FAILURE_AUDIT_CAPACITY')
                doc = dict(run_id=run, sequence=len(history)+1, parent=history[-1]['fingerprint'] if history else None,
                    actor=actor, action='EXECUTION_FAILED', code=code, resulting_state=state,
                    primary_exception_preserved=True, native_termination_verified=False,
                    at=datetime.now(timezone.utc).isoformat())
                self.capacity(db, len(canonical(doc).encode())+1024, reserve=0)
                db.execute('INSERT INTO commands VALUES(?,?,?,?,?,?)', (run, doc['sequence'], actor, str(uuid4()), canonical(doc), digest(doc)))
                db.execute('UPDATE control SET state=?,owner=NULL,lease=0 WHERE run=?', (state, run))
                db.commit()
            except Exception:
                db.rollback(); raise

    def _reviews(self, db, run):
        items, parent = [], None
        for row in db.execute('SELECT raw,hash FROM reviews WHERE run=? ORDER BY sequence', (run,)):
            doc = json.loads(row['raw'])
            require(doc['run_id'] == run and doc['sequence'] == len(items)+1 and doc['parent'] == parent
                    and digest(doc) == row['hash'], 'CYCLE_REVIEW_CORRUPT')
            parent = row['hash']; items.append(doc | {'fingerprint': row['hash']})
        return items

    def decide(self, principal, run, command):
        grant = self.authorize(principal, 'review.decide')
        require(type(command) is Decision, 'CYCLE_COMMAND_INVALID', 422)
        identity(command.request_id)
        with closing(self.db()) as db, ExitStack() as policy_guard:
            try:
                db.execute('BEGIN IMMEDIATE')
                admission, _row, control, segments = self._read(db, run)
                history = self._reviews(db, run)
                old = db.execute('SELECT raw,hash FROM reviews WHERE actor=? AND nonce=?', (grant.actor_id, command.request_id)).fetchone()
                if old:
                    require(json.loads(old['raw'])['command_digest'] == digest(dict(run=run, command=command.model_dump())), 'CYCLE_REVIEW_NONCE_MISMATCH')
                    return json.loads(old['raw']) | {'fingerprint': old['hash']}
                require(segments and control['state'] in {'COMPLETED', 'STOPPED'} and control['owner'] is None,
                        'CYCLE_FINAL_GENERATED_CANDIDATE_REQUIRED')
                candidate = json.loads(segments[-1][1]['result'])
                require(command.expected_review == len(history) and command.candidate_fingerprint == digest(candidate), 'CYCLE_REVIEW_STALE')
                require(not history, 'CYCLE_REVIEW_ALREADY_DECIDED_NEW_CANDIDATE_REQUIRED')
                if command.decision == 'APPROVE':
                    require(candidate['qualification']['fully_feasible_under_captured_policy'] is True, 'CYCLE_CONSTRAINT_VIOLATION_APPROVAL_DENIED')
                    minimum_db = policy_guard.enter_context(closing(self.inputs.workload.store.connection()))
                    input_db = policy_guard.enter_context(closing(self.inputs.connection()))
                    minimum_db.execute('BEGIN IMMEDIATE'); input_db.execute('BEGIN IMMEDIATE')
                    minima = self.inputs.workload.store.read(minimum_db)
                    weights = self.inputs._head(input_db, 'weights', self.inputs.data['scoring_context']['settings'])
                    preferences = self.inputs._preference_heads(input_db)
                    pinned = admission['provenance']
                    require(minima['digest'] == pinned['minimum_policy']['digest']
                            and weights['digest'] == pinned['weights_policy']['digest']
                            and digest(preferences) == pinned['preferences_digest'], 'CYCLE_CURRENT_REVIEW_INPUTS_CHANGED')
                doc = dict(run_id=run, sequence=len(history)+1, parent=history[-1]['fingerprint'] if history else None,
                    actor=grant.actor_id, decision=command.decision, explanation=command.explanation,
                    candidate_fingerprint=digest(candidate), command_digest=digest(dict(run=run, command=command.model_dump())),
                    at=datetime.now(timezone.utc).isoformat(), institutional_approval=False,
                    current_policy_rechecked=command.decision == 'APPROVE')
                self.capacity(db, len(canonical(doc).encode())+1024)
                db.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?)', (run, doc['sequence'], grant.actor_id, command.request_id, canonical(doc), digest(doc)))
                if command.decision == 'APPROVE':
                    versions = self._versions(db)
                    version = dict(version=len(versions)+1, previous=versions[-1]['fingerprint'] if versions else None,
                        run_id=run, decision_fingerprint=digest(doc), candidate_fingerprint=digest(candidate),
                        evaluation_fingerprint=admission['evaluation_fingerprint'], candidate=candidate,
                        scope=admission['scope'], prototype_approved=True, institutional_publication=False)
                    self.capacity(db, len(canonical(version).encode())+1024)
                    db.execute('INSERT INTO versions VALUES(?,?,?)', (version['version'], canonical(version), digest(version)))
                self.authorize(principal, 'review.decide')
                db.commit()
                return doc | {'fingerprint': digest(doc)}
            except Exception:
                db.rollback(); raise

    def _versions(self, db):
        items, parent = [], None
        for row in db.execute('SELECT * FROM versions ORDER BY version'):
            doc = json.loads(row['raw'])
            require(doc['version'] == row['version'] == len(items)+1 and doc['previous'] == parent
                    and digest(doc) == row['hash'], 'CYCLE_VERSION_CORRUPT')
            admission, _run, _control, segments = self._read(db, doc['run_id'])
            decisions = self._reviews(db, doc['run_id'])
            require(doc['evaluation_fingerprint'] == admission['evaluation_fingerprint'] and doc['scope'] == admission['scope']
                and digest(doc['candidate']) == doc['candidate_fingerprint']
                and doc['candidate']['qualification']['fully_feasible_under_captured_policy'] is True
                and any(s['result_fingerprint'] == doc['candidate_fingerprint'] for s, _record in segments)
                and any(d['fingerprint'] == doc['decision_fingerprint'] and d['decision'] == 'APPROVE'
                        and d['candidate_fingerprint'] == doc['candidate_fingerprint'] for d in decisions), 'CYCLE_APPROVED_SOURCE_BINDING_INVALID')
            parent = row['hash']; items.append(doc | {'fingerprint': row['hash']})
        return items

    def versions(self, principal):
        self.authorize(principal, 'schedule.read')
        with closing(self.db()) as db:
            return self._versions(db)

    def timetable(self, principal, code):
        self.authorize(principal, 'faculty.timetable', code)
        with closing(self.db()) as db:
            versions = self._versions(db)
        if not versions:
            return dict(contract=VERSION, **FLAGS, state='NO_APPROVED_PROTOTYPE_SCHEDULE', version=None, schedule=[])
        version = versions[-1]
        candidate = version['candidate']
        workload = next((r for r in candidate['qualification']['faculty'] if r['faculty_code'] == code), None)
        require(workload is not None, 'CYCLE_FACULTY_OUTSIDE_APPROVED_COHORT', 404)
        return dict(contract=VERSION, **FLAGS, state='APPROVED_PROTOTYPE_VERSION', version=version['version'],
            version_fingerprint=version['fingerprint'], workload=workload, provenance=candidate['provenance'],
            schedule=[r for r in candidate['original_result']['schedule'] if str(r['faculty']) == str(code)],
            current_institutional_or_latest_policy_revalidation='NOT_ESTABLISHED')

    def compare(self, principal, left, right):
        a, b = self.inspect(principal, left), self.inspect(principal, right)
        require(a['result'] is not None and b['result'] is not None, 'CYCLE_GENERATED_COMPARISON_REQUIRED')
        if a['evaluation_fingerprint'] != b['evaluation_fingerprint']:
            return dict(classification='INCOMPARABLE', fitness_difference=None, best_saved=False)
        x, y = a['result']['original_result']['best_fitness'], b['result']['original_result']['best_fitness']
        return dict(classification='SAME_FROZEN_EVALUATION', fitness_difference=x-y,
                    lower_fitness_run=left if x < y else right if y < x else None, tie=x == y, best_saved=False,
                    feasibility_separate=True)

    def export_version(self, principal, number, kind):
        self.authorize(principal, 'schedule.export')
        version = next((v for v in self.versions(principal) if v['version'] == number), None)
        require(version is not None, 'CYCLE_VERSION_NOT_FOUND', 404)
        if kind == 'json':
            raw = canonical(version)
        elif kind == 'csv':
            stream = io.StringIO(newline=''); writer = csv.writer(stream)
            writer.writerow(['prototype_version', 'run_id', 'original_fitness', 'assignment_json'])
            for item in version['candidate']['original_result']['schedule']:
                writer.writerow([number, version['run_id'], version['candidate']['original_result']['best_fitness'], canonical(item)])
            raw = stream.getvalue()
        elif kind == 'txt':
            raw = 'FICTIONAL PROTOTYPE ONLY\n'+canonical(dict(version=number, run_id=version['run_id'],
                original_fitness=version['candidate']['original_result']['best_fitness'],
                qualification=version['candidate']['qualification'], provenance=version['candidate']['provenance']))+'\n'
        else:
            require(False, 'CYCLE_EXPORT_FORMAT_INVALID', 422)
        require(len(raw.encode()) <= 256*1024, 'CYCLE_EXPORT_TOO_LARGE', 413)
        return raw

    def export_run(self, principal, run, kind):
        self.authorize(principal, 'schedule.export')
        view = self.inspect(principal, run)
        require(view['result'] is not None, 'CYCLE_GENUINE_OBSERVATIONS_REQUIRED', 409)
        if kind == 'json':
            raw = canonical(view)
        elif kind == 'csv':
            stream = io.StringIO(newline=''); writer = csv.writer(stream)
            writer.writerow(['run_id', 'generation', 'original_observation_json'])
            for row in view['result']['original_result']['history']:
                writer.writerow([run, row['generation'], canonical(row)])
            raw = stream.getvalue()
        elif kind == 'txt':
            raw = 'GENUINE ORIGINAL GA / OFFLINE IN-PROCESS / FICTIONAL ONLY\n'+canonical(dict(
                run_id=run, native_verified=False, original_fitness=view['result']['original_result']['best_fitness'],
                qualification=view['result']['qualification'], provenance=view['provenance'],
                segment_history=view['segment_history']))+'\n'
        else:
            require(False, 'CYCLE_EXPORT_FORMAT_INVALID', 422)
        require(len(raw.encode()) <= 256*1024, 'CYCLE_EXPORT_TOO_LARGE', 413)
        return raw
