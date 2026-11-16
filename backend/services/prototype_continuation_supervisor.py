"""Finite fictional continuation journal; no native launch or HTTP control.

Original Cycle owns atomic checkpoint/result commits and its separate tip pin.
This journal records intent before dispatch and verifies the committed checkpoint
afterwards. A missing acknowledgement is reconciled explicitly, never rerun.
"""
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time
from uuid import uuid4

from services.prototype_cycle import Cycle, identity
from services.prototype_workload import Store, canonical, digest, require

VERSION = 'fictional-finite-supervisor-v1'
MAX_EVENTS = 64
MAX_LOGICAL_BYTES = 4*1024*1024
TERMINAL = {'COMPLETED', 'STOPPED', 'INPUT_INFEASIBLE'}


def checkpoint_audit(cycle, principal, run):
    grant = cycle.authorize(principal, 'run.read')
    with closing(cycle.db()) as db:
        admission, row, control, segments = cycle._read(db, run,
            grant.actor_id if grant.capacity == 'SCHEDULER' else None)
        if not segments:
            return dict(present=False, sequence=0, generation=None, native_verified=False)
        session = cycle._session(admission, row, segments)  # Original strict codec.
        state = session.resume_state
        from services.ga_checkpoint_service import rng_to_json
        require(state['history'] == json.loads(segments[-1][1]['result'])['original_result']['history'],
                'SUPERVISOR_HISTORY_DIVERGED')
        return dict(present=True, sequence=len(segments), generation=state['generation_completed'],
            next_generation=state['next_generation'], population=len(state['population']),
            best_ever_present=state['best_ever'] is not None, best_fitness=state['best_ever_fitness'],
            history_points=len(state['history']), history_fingerprint=digest(state['history']),
            RNG_fingerprint=digest(rng_to_json(state['random_state'])),
            checkpoint_fingerprint=session.checkpoint_fingerprint,
            bundle_fingerprint=admission['bundle_fingerprint'],
            configuration_fingerprint=admission['configuration_fingerprint'],
            optimizer_fingerprint=admission['optimizer_fingerprint'],
            scoring_fingerprint=admission['scoring_fingerprint'],
            captured_policies_fingerprint=digest(admission['provenance']),
            original_codec_verified=True, native_verified=False)


def storage_report(cycle, principal, run):
    """Actual finite file sizes plus a conditional constant-size illustration."""
    view = cycle.inspect(principal, run)
    with closing(cycle.db()) as db:
        rows = list(db.execute('SELECT length(checkpoint),length(result),length(raw) FROM segments WHERE run=? ORDER BY sequence', (run,)))
        stored = db.execute('SELECT SUM(length(raw)+length(bundle)+length(rng)) FROM runs').fetchone()[0] or 0
        stored += db.execute('SELECT SUM(length(raw)+length(checkpoint)+length(result)) FROM segments').fetchone()[0] or 0
    largest = max((r[0] for r in rows), default=None)
    checkpoints = math.ceil(7*24*3600/600)
    return dict(measurement='FINITE_FICTIONAL_STORE_ONLY', segments=len(rows),
        checkpoint_bytes=[r[0] for r in rows], result_bytes=[r[1] for r in rows],
        cycle_database_bytes=cycle.path.stat().st_size, logical_run_and_segment_bytes=stored,
        witness_database_bytes=(cycle.witness.storage.root/'witness.sqlite3').stat().st_size,
        raw_checkpoint_cap_bytes=8*1024*1024, checkpoint_total_cap_bytes=64*1024*1024,
        checkpoint_count_cap=8, existing_lifetime_seconds=600, existing_generation_cap=20,
        offline_generation_cap=2, retention='KEEP_ALL_NO_AUTOMATIC_DELETE',
        hypothetical_7day_cadence_seconds=600, hypothetical_7day_checkpoint_count=checkpoints,
        hypothetical_constant_size_checkpoint_bytes=None if largest is None else checkpoints*largest,
        assumes_largest_observed_checkpoint_repeats_unchanged=True,
        per_checkpoint_cap_times_count_bytes=checkpoints*8*1024*1024,
        projection_is_not_capacity_or_throughput_qualification=True,
        complete_histories_repeat_in_checkpoints=True, future_generations=None,
        current_history_points=None if not view['result'] else len(view['result']['original_result']['history']),
        current_history_json_bytes=None if not view['result'] else len(canonical(view['result']['original_result']['history']).encode()),
        current_export_bytes=None if not view['result'] else {kind: len(cycle.export_run(principal, run, kind).encode()) for kind in ['json', 'csv', 'txt']},
        physical_recovery_time_seconds=None, maximum_interruption_loss='SINCE_LAST_VERIFIED_BOUNDARY_ONLY; NO_NATIVE_TIME_BOUND_PROVEN',
        seven_day='NO_GO')


class Supervisor:
    def __init__(self, cycle, *, root=None, offline_qualification=False, clock=time.time):
        require(type(cycle) is Cycle, 'SUPERVISOR_CYCLE_REQUIRED')
        self.cycle, self.clock, self.offline_qualification = cycle, clock, offline_qualification
        self.failure_recording_errors = {}
        self.binding = digest(dict(contract=VERSION, cycle=cycle.binding,
            implementation=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
        self.storage = Store.create(self.binding) if root is None else Store(root, self.binding)
        self.path = self.storage.root/'supervisor.sqlite3'
        self._initializing = root is None
        if root is None:
            with self.path.open('xb'):
                pass
            with closing(self.db()) as db, db:
                db.execute('PRAGMA max_page_count=2048')  # New database only, ~8 MiB.
                db.executescript('''
CREATE TABLE metadata(binding TEXT NOT NULL);
CREATE TABLE events(run TEXT NOT NULL,sequence INTEGER NOT NULL,raw TEXT NOT NULL,hash TEXT NOT NULL,PRIMARY KEY(run,sequence));
CREATE TABLE claims(run TEXT PRIMARY KEY,nonce TEXT NOT NULL,actor TEXT NOT NULL,owner TEXT NOT NULL,fence INTEGER NOT NULL,lease REAL NOT NULL,state TEXT NOT NULL,before_sequence INTEGER NOT NULL,before_tip TEXT,observed_sequence INTEGER);
CREATE TRIGGER immutable_events_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER immutable_events_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'immutable'); END;
''')
                db.execute('INSERT INTO metadata VALUES(?)', (self.binding,))
        self._initializing = False
        with closing(self.db()):
            pass

    def db(self):
        self.storage.check()
        require(self.path.is_file() and not self.path.is_symlink() and not self.path.is_junction()
                and self.path.stat().st_size < 8*1024*1024, 'SUPERVISOR_STORE_INVALID')
        db = sqlite3.connect(self.path.as_uri()+'?mode=rw', uri=True, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        try:
            if not self._initializing:
                require([tuple(r) for r in db.execute('SELECT binding FROM metadata')] == [(self.binding,)],
                        'SUPERVISOR_STORE_BINDING')
        except Exception:
            db.close(); raise
        return db

    def _events(self, db, run):
        history, previous = [], None
        for row in db.execute('SELECT * FROM events WHERE run=? ORDER BY sequence', (run,)):
            doc = json.loads(row['raw'])
            require(doc['binding'] == self.binding and doc['run_id'] == run and doc['sequence'] == row['sequence'] == len(history)+1
                    and doc['parent'] == previous and digest(doc) == row['hash'], 'SUPERVISOR_EVENT_CORRUPT')
            history.append(doc); previous = row['hash']
        return history

    def _append(self, db, run, event, **fields):
        events = self._events(db, run)
        require(len(events) < MAX_EVENTS, 'SUPERVISOR_EVENT_LIMIT', 413)
        doc = dict(binding=self.binding, run_id=run, sequence=len(events)+1,
            parent=digest(events[-1]) if events else None, event=event, at=self.clock(), **fields)
        raw = canonical(doc)
        used = db.execute('SELECT COALESCE(SUM(length(raw)),0) FROM events').fetchone()[0]
        require(used+len(raw.encode())+4096 <= MAX_LOGICAL_BYTES and self.path.stat().st_size+len(raw.encode())+8192 < 8*1024*1024,
                'SUPERVISOR_STORAGE_CAPACITY', 413)
        db.execute('INSERT INTO events VALUES(?,?,?,?)', (run, len(events)+1, raw, digest(doc)))
        return doc

    def _claim(self, db, run):
        events = self._events(db, run)
        row = db.execute('SELECT * FROM claims WHERE run=?', (run,)).fetchone()
        intents = [e for e in events if e['event'] == 'SEGMENT_INTENT']
        require((row is None) == (not intents), 'SUPERVISOR_CLAIM_JOURNAL_MISMATCH')
        if row is None:
            return None
        intent = intents[-1]
        require(all(row[key] == intent[key] for key in ['nonce', 'actor', 'owner', 'fence', 'before_sequence', 'before_tip']),
                'SUPERVISOR_CLAIM_JOURNAL_MISMATCH')
        related = [e for e in events if e.get('nonce') == row['nonce']]
        if row['state'] == 'ACKNOWLEDGED':
            acks = [e for e in related if e['event'] in {'VERIFIED_SEGMENT', 'RECOVERED_COMMITTED_SEGMENT'}]
            require(len(acks) == 1 and row['lease'] == 0 and row['observed_sequence'] == acks[0]['sequence_observed']
                    and acks[0]['fence'] == row['fence'], 'SUPERVISOR_CLAIM_JOURNAL_MISMATCH')
        else:
            require(row['state'] in {'ACTIVE', 'RECOVERY_REQUIRED'} and row['observed_sequence'] is None
                    and row['lease'] == intent['lease_until'], 'SUPERVISOR_CLAIM_JOURNAL_MISMATCH')
            require(not any(e['event'] in {'VERIFIED_SEGMENT', 'RECOVERED_COMMITTED_SEGMENT'} for e in related),
                    'SUPERVISOR_CLAIM_JOURNAL_MISMATCH')
            require(row['state'] != 'RECOVERY_REQUIRED' or any(e['event'] == 'SEGMENT_FAILED' for e in related),
                    'SUPERVISOR_CLAIM_JOURNAL_MISMATCH')
        return row

    def status(self, principal, run):
        view = self.cycle.inspect(principal, run)
        with closing(self.db()) as db:
            events = self._events(db, run)
            row = self._claim(db, run)
        return dict(contract=VERSION, run_id=run, cycle_state=view['state'],
            controller_state='NOT_DISPATCHED' if row is None else row['state'],
            pending_reconciliation=row is not None and row['state'] in {'ACTIVE', 'RECOVERY_REQUIRED'},
            failure_audit_error=self.failure_recording_errors.get(run),
            history=events, checkpoint=checkpoint_audit(self.cycle, principal, run),
            native_execution='NOT_IMPLEMENTED_NOT_QUALIFIED', physical_termination='NOT_VERIFIED',
            seven_day='NO_GO', institutional_continuous_optimization='DISABLED')

    def step_offline(self, principal, run, nonce):
        require(self.offline_qualification is True and self.cycle.offline_qualification is True,
                'SUPERVISOR_NATIVE_TRANSPORT_UNQUALIFIED', 503)
        identity(nonce)
        actor = self.cycle.authorize(principal, 'run.segment').actor_id
        view = self.cycle.inspect(principal, run)
        owner = str(uuid4())
        with closing(self.db()) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                events = self._events(db, run)
                old = self._claim(db, run)
                completed = [e for e in events if e.get('nonce') == nonce and e['event'] in {'VERIFIED_SEGMENT', 'RECOVERED_COMMITTED_SEGMENT'}]
                if completed:
                    require(completed[-1]['actor'] == actor, 'SUPERVISOR_NONCE_OWNER')
                    db.rollback()
                    return self.status(principal, run)
                require(not any(e.get('nonce') == nonce for e in events), 'SUPERVISOR_NONCE_REQUIRES_RECONCILIATION')
                require(old is None or old['state'] == 'ACKNOWLEDGED', 'SUPERVISOR_RECOVERY_REQUIRED')
                if old is not None:
                    require(view['sequence'] == old['observed_sequence'], 'SUPERVISOR_UNOBSERVED_CYCLE_ADVANCE')
                require(view['state'] not in TERMINAL, 'SUPERVISOR_TERMINAL')
                fence = 1 if old is None else old['fence']+1
                lease = self.clock()+60
                self._append(db, run, 'SEGMENT_INTENT', nonce=nonce, actor=actor, owner=owner, fence=fence,
                    before_sequence=view['sequence'], before_tip=view['tip'], lease_until=lease)
                db.execute('INSERT OR REPLACE INTO claims VALUES(?,?,?,?,?,?,?,?,?,NULL)',
                    (run, nonce, actor, owner, fence, lease, 'ACTIVE', view['sequence'], view['tip']))
                db.commit()
            except Exception:
                db.rollback(); raise
        try:
            after = self.cycle.step_offline(principal, run)
            proof = checkpoint_audit(self.cycle, principal, run)
            require(after['sequence'] in {view['sequence'], view['sequence']+1}
                    and (after['sequence'] > view['sequence'] or after['state'] == 'STOPPED'), 'SUPERVISOR_SEGMENT_SEQUENCE')
            # No worker exists in this oracle. A boolean Stop is not exit proof.
            self._ack(principal, run, owner, fence, nonce, after, proof, 'VERIFIED_SEGMENT')
        except Exception as primary:
            try:
                with closing(self.db()) as db, db:
                    current = self._claim(db, run)
                    require(current['owner'] == owner and current['fence'] == fence, 'SUPERVISOR_STALE_OWNER')
                    self._append(db, run, 'SEGMENT_FAILED', nonce=nonce, actor=actor,
                        code=getattr(primary, 'code', 'SUPERVISOR_SEGMENT_FAILED'), primary_preserved=True,
                        worker_termination_verified=False)
                    db.execute("UPDATE claims SET state='RECOVERY_REQUIRED' WHERE run=?", (run,))
            except Exception:
                self.failure_recording_errors[run] = 'SUPERVISOR_FAILURE_AUDIT_UNAVAILABLE'
            raise
        return self.status(principal, run)

    def _ack(self, principal, run, owner, fence, nonce, view, proof, event):
        actor = self.cycle.authorize(principal, 'run.segment').actor_id
        with closing(self.db()) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                row = self._claim(db, run)
                require(row['owner'] == owner and row['fence'] == fence and row['nonce'] == nonce
                        and row['actor'] == actor and row['state'] in {'ACTIVE', 'RECOVERY_REQUIRED'}, 'SUPERVISOR_STALE_OWNER')
                require(event != 'VERIFIED_SEGMENT' or row['lease'] > self.clock(), 'SUPERVISOR_ACK_LEASE_EXPIRED')
                self._append(db, run, event, nonce=nonce, actor=actor, fence=fence,
                    sequence_observed=view['sequence'], tip_observed=view['tip'], checkpoint=proof,
                    physical_worker_termination='NOT_APPLICABLE_IN_PROCESS_ORACLE', native_verified=False)
                db.execute("UPDATE claims SET state='ACKNOWLEDGED',lease=0,observed_sequence=? WHERE run=?",
                           (view['sequence'], run))
                db.commit()
            except Exception:
                db.rollback(); raise

    def reconcile_offline(self, principal, run):
        require(self.offline_qualification is True and self.cycle.offline_qualification is True,
                'SUPERVISOR_NATIVE_RECOVERY_UNQUALIFIED', 503)
        actor = self.cycle.authorize(principal, 'run.recover').actor_id
        require(run not in self.cycle.active, 'SUPERVISOR_EXECUTION_STILL_ACTIVE')
        with closing(self.db()) as db:
            row = self._claim(db, run)
            require(row is not None and row['actor'] == actor and row['state'] in {'ACTIVE', 'RECOVERY_REQUIRED'}
                    and row['lease'] <= self.clock(), 'SUPERVISOR_RECOVERY_NOT_IDLE')
            self._events(db, run)
        view = self.cycle.inspect(principal, run)  # Separate witness must agree.
        require(view['sequence'] == row['before_sequence']+1, 'SUPERVISOR_NO_RECOVERABLE_COMMITTED_SEGMENT')
        proof = checkpoint_audit(self.cycle, principal, run)
        self._ack(principal, run, row['owner'], row['fence'], row['nonce'], view, proof, 'RECOVERED_COMMITTED_SEGMENT')
        return self.status(principal, run)

    def request_stop(self, principal, run, nonce):
        command = self.cycle.request_stop(principal, run, nonce)
        with closing(self.db()) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                recorded = [e for e in self._events(db, run) if e['event'] == 'STOP_REQUEST_RECORDED' and e.get('nonce') == nonce]
                if recorded:
                    require(recorded[-1]['command_fingerprint'] == digest(command), 'SUPERVISOR_STOP_NONCE_MISMATCH')
                else:
                    self._append(db, run, 'STOP_REQUEST_RECORDED', nonce=nonce, command_fingerprint=digest(command),
                        worker_termination_verified=False)
                db.commit()
            except Exception:
                db.rollback(); raise
        return dict(command=command, worker_termination_verified=False, native_verified=False)
