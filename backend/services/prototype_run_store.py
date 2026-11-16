"""Append-only minimum/run bindings in a NEW owned prototype SQLite file.

Corruption checking is not an institutional signature or hostile-OS guarantee.
"""
from contextlib import closing
from datetime import datetime, timezone
import json
import sqlite3
from uuid import uuid4
from services.prototype_workload import canonical, digest, require

VERSION = 'prototype-minimum-run-ledger-v1'


class RunStore:
    def __init__(self, policy_store, binding, *, initialize=False):
        self.policy_store, self.binding = policy_store, binding
        self.path = policy_store.root / 'executions.sqlite3'
        policy_store.check()
        if initialize:
            with self.path.open('xb'):
                pass
            with closing(self.connection()) as db, db:
                db.executescript('''
CREATE TABLE metadata(binding TEXT NOT NULL);
CREATE TABLE requests(id TEXT PRIMARY KEY,actor TEXT NOT NULL,nonce TEXT NOT NULL,raw TEXT NOT NULL,hash TEXT NOT NULL,UNIQUE(actor,nonce));
CREATE TABLE events(run TEXT NOT NULL,sequence INTEGER NOT NULL,raw TEXT NOT NULL,hash TEXT NOT NULL,PRIMARY KEY(run,sequence));
CREATE TRIGGER no_request_update BEFORE UPDATE ON requests BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER no_request_delete BEFORE DELETE ON requests BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER no_event_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER no_event_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'immutable'); END;
''')
                db.execute('INSERT INTO metadata VALUES(?)', (binding,))
        with closing(self.connection()) as db:
            require(db.execute('SELECT binding FROM metadata').fetchall() == [(binding,)], 'PROTOTYPE_RUN_STORE_BINDING')

    def connection(self):
        self.policy_store.check()
        require(self.path.is_file() and not self.path.is_symlink() and not self.path.is_junction(), 'PROTOTYPE_RUN_STORE_INVALID')
        require(self.path.stat().st_size < 16 * 1024 * 1024, 'PROTOTYPE_RUN_STORE_FULL', 413)
        db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=5)
        db.execute('PRAGMA synchronous=FULL')
        return db

    def _read(self, db, run, actor):
        row = db.execute('SELECT raw,hash FROM requests WHERE id=? AND actor=?', (run, actor)).fetchone()
        require(row is not None, 'PROTOTYPE_RUN_NOT_FOUND', 404)
        record = json.loads(row[0])
        require(digest(record) == row[1] and record['id'] == run and record['actor'] == actor
                and record['binding'] == self.binding, 'PROTOTYPE_RUN_RECORD_CORRUPT')
        events, parent = [], row[1]
        for sequence, raw, identity in db.execute('SELECT sequence,raw,hash FROM events WHERE run=? ORDER BY sequence', (run,)):
            item = json.loads(raw)
            require(sequence == len(events)+1 == item['sequence'] and item['parent'] == parent
                    and item['run'] == run and digest(item) == identity, 'PROTOTYPE_RUN_EVENT_CORRUPT')
            parent = identity
            events.append(item)
        return record, events

    def get(self, run, actor):
        with closing(self.connection()) as db:
            return self._read(db, run, actor)

    def find(self, actor, nonce):
        with closing(self.connection()) as db:
            row = db.execute('SELECT id FROM requests WHERE actor=? AND nonce=?', (actor, nonce)).fetchone()
            return self._read(db, row[0], actor)[0] if row else None

    def create(self, actor, selector, snapshot):
        with closing(self.connection()) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                old = db.execute('SELECT id FROM requests WHERE actor=? AND nonce=?', (actor, selector['request_id'])).fetchone()
                if old:
                    record, _ = self._read(db, old[0], actor)
                    require(record['selector'] == selector, 'PROTOTYPE_REQUEST_REUSE_MISMATCH')
                    return record, False
                require(db.execute('SELECT COUNT(*) FROM requests').fetchone()[0] < 32, 'PROTOTYPE_RUN_RETENTION_FULL', 413)
                record = dict(id=str(uuid4()), actor=actor, binding=self.binding, selector=selector,
                              snapshot=snapshot, snapshot_hash=digest(snapshot),
                              created_at=datetime.now(timezone.utc).isoformat())
                db.execute('INSERT INTO requests VALUES(?,?,?,?,?)',
                           (record['id'], actor, selector['request_id'], canonical(record), digest(record)))
                db.commit()
                return record, True
            except Exception:
                db.rollback()
                raise

    def append(self, run, actor, kind, data, *, terminal=False):
        with closing(self.connection()) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                record, events = self._read(db, run, actor)
                if events and events[-1]['terminal']:
                    return
                require(len(events) < 32, 'PROTOTYPE_RUN_EVENT_LIMIT', 413)
                parent = digest(events[-1]) if events else digest(record)
                item = dict(run=run, sequence=len(events)+1, parent=parent, kind=kind, data=data,
                            terminal=terminal, at=datetime.now(timezone.utc).isoformat())
                raw = canonical(item)
                require(len(raw.encode()) <= 512 * 1024, 'PROTOTYPE_RESULT_TOO_LARGE', 413)
                db.execute('INSERT INTO events VALUES(?,?,?,?)', (run, item['sequence'], raw, digest(item)))
                db.commit()
            except Exception:
                db.rollback()
                raise
