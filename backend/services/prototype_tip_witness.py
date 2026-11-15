"""Separate fictional durable tip journal, not a qualified deployment witness.

No ACL changes. The owner must retain the key fingerprint outside restored DBs.
Signed independent files detect ordinary primary-store rollback/corruption, not
replacement/rollback of the entire host, key and all journals together.
"""
from contextlib import closing
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from services.prototype_workload import Store, canonical, digest, require

VERSION = 'fictional-tip-witness-v1'


class TipWitness:
    def __init__(self, *, root=None, key_fingerprint=None):
        if root is None:
            key = secrets.token_bytes(32)
            self.key_fingerprint = hashlib.sha256(key).hexdigest()
            self.binding = digest(dict(contract=VERSION, key=self.key_fingerprint))
            self.storage = Store.create(self.binding)
            with (self.storage.root/'witness-key.bin').open('xb') as stream:
                stream.write(key); stream.flush(); os.fsync(stream.fileno())
            with (self.storage.root/'witness.sqlite3').open('xb'):
                pass
            with closing(self.db()) as db, db:
                db.execute('CREATE TABLE tips(binding TEXT NOT NULL,run TEXT NOT NULL,sequence INTEGER NOT NULL,raw TEXT NOT NULL,mac TEXT NOT NULL,PRIMARY KEY(binding,run,sequence))')
                for op in ['UPDATE', 'DELETE']:
                    db.execute(f"CREATE TRIGGER no_{op} BEFORE {op} ON tips BEGIN SELECT RAISE(ABORT,'immutable'); END")
        else:
            require(type(key_fingerprint) is str and len(key_fingerprint) == 64, 'WITNESS_OWNER_KEY_PIN_REQUIRED')
            self.key_fingerprint = key_fingerprint
            self.binding = digest(dict(contract=VERSION, key=key_fingerprint))
            self.storage = Store(root, self.binding)
        self._key()

    def _key(self):
        self.storage.check()
        path = self.storage.root/'witness-key.bin'
        require(path.is_file() and not path.is_symlink() and not path.is_junction(), 'WITNESS_KEY_INVALID')
        value = path.read_bytes()
        require(len(value) == 32 and hashlib.sha256(value).hexdigest() == self.key_fingerprint, 'WITNESS_KEY_PIN_MISMATCH')
        return value

    def db(self):
        self.storage.check()
        path = self.storage.root/'witness.sqlite3'
        require(path.is_file() and not path.is_symlink() and not path.is_junction()
                and path.stat().st_size < 4*1024*1024, 'WITNESS_STORE_INVALID')
        db = sqlite3.connect(path.as_uri()+'?mode=rw', uri=True, timeout=5)
        db.execute('PRAGMA synchronous=FULL')
        return db

    def _read(self, db, binding, run):
        tip, parent, count = None, None, 0
        key = self._key()
        for sequence, raw, signature in db.execute('SELECT sequence,raw,mac FROM tips WHERE binding=? AND run=? ORDER BY sequence', (binding, run)):
            doc = json.loads(raw)
            require(sequence == count+1 == doc['sequence'] and doc['binding'] == binding and doc['run'] == run
                and doc['parent'] == parent and doc['previous'] == tip
                and hmac.compare_digest(signature, hmac.new(key, raw.encode(), hashlib.sha256).hexdigest()), 'WITNESS_CHAIN_CORRUPT')
            tip, parent, count = doc['tip'], signature, count+1
        return tip, parent, count

    def read(self, binding, run):
        with closing(self.db()) as db:
            return self._read(db, binding, run)[0]

    def advance(self, binding, run, expected, replacement):
        with closing(self.db()) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                current, parent, count = self._read(db, binding, run)
                require(current == expected and count < 32, 'WITNESS_CAS_OR_CAPACITY')
                doc = dict(binding=binding, run=run, sequence=count+1, previous=current, parent=parent, tip=replacement)
                raw = canonical(doc)
                db.execute('INSERT INTO tips VALUES(?,?,?,?,?)', (binding, run, count+1, raw,
                    hmac.new(self._key(), raw.encode(), hashlib.sha256).hexdigest()))
                db.commit()
                return True
            except Exception:
                db.rollback(); raise
