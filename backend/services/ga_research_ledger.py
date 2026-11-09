"""Bounded HMAC-chained research observations inside an owned U5L store.

Not institutional persistence or protection against a malicious OS/store owner.
No truncation/retention deletion: quotas reject new writes explicitly.
"""
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
from services.ga_run_authority import RunError, canonical, digest

VERSION='fictional-research-ledger-v1'
MAX_EVENTS=256
MAX_EVENT_BYTES=8192
SCHEMA='''
CREATE TABLE research_meta(version TEXT NOT NULL, release TEXT NOT NULL, permit TEXT NOT NULL, key_hash TEXT NOT NULL);
CREATE TABLE research_runs(run TEXT PRIMARY KEY REFERENCES workers(run), context BLOB NOT NULL,
 context_mac TEXT NOT NULL, head TEXT, count INTEGER NOT NULL, head_mac TEXT NOT NULL);
CREATE TABLE research_proofs(run TEXT NOT NULL REFERENCES research_runs(run), sequence INTEGER NOT NULL,
 payload BLOB NOT NULL, signature TEXT NOT NULL, PRIMARY KEY(run,sequence));
CREATE TABLE research_events(run TEXT NOT NULL REFERENCES research_runs(run), sequence INTEGER NOT NULL,
 payload BLOB NOT NULL, parent TEXT, hash TEXT NOT NULL, signature TEXT NOT NULL, PRIMARY KEY(run,sequence));
'''


def implementation():
    folder=Path(__file__).parent
    return digest({n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in
        ['ga_research_ledger.py','ga_research_context.py','ga_research_bridge.py']})


class Ledger:
    def __init__(self, store, permit, *, initialize=False):
        self.store=store; self.release=implementation(); self.permit=permit; self.path=store.root/'RESEARCH-KEY.bin'
        store.guard()
        if initialize:
            with store.connection() as db:
                if db.execute('SELECT COUNT(*) FROM runs').fetchone()[0] or db.execute("SELECT name FROM sqlite_master WHERE name LIKE 'research_%'").fetchone():
                    raise RunError('RESEARCH_NEW_STORE_REQUIRED')
            with self.path.open('xb') as f:
                f.write(secrets.token_bytes(32));f.flush();os.fsync(f.fileno())
            with store.connection() as db:
                db.executescript('BEGIN IMMEDIATE;'+SCHEMA)
                db.execute('INSERT INTO research_meta VALUES(?,?,?,?)',(VERSION,self.release,permit,hashlib.sha256(self.path.read_bytes()).hexdigest()));db.commit()
        self.guard()

    def guard(self):
        self.store.guard()
        if self.path.is_symlink() or self.path.is_junction():raise RunError('RESEARCH_KEY_UNVERIFIED')
        try:
            self.key=self.path.read_bytes()
            with self.store.connection() as db:rows=db.execute('SELECT * FROM research_meta').fetchall()
            if len(self.key)!=32 or len(rows)!=1 or tuple(rows[0])!=(VERSION,self.release,self.permit,hashlib.sha256(self.key).hexdigest()) or implementation()!=self.release:raise ValueError()
        except (OSError,ValueError):raise RunError('RESEARCH_LEDGER_VERSION_OR_KEY_CHANGED') from None

    def mac(self, data):return hmac.new(self.key,canonical(dict(store=self.store.store_id,release=self.release,data=data)),hashlib.sha256).hexdigest()
    def matches(self, data, signature):return type(signature) is str and hmac.compare_digest(self.mac(data),signature)

    def register(self, db, run, context):
        old=db.execute('SELECT * FROM research_runs WHERE run=?',(run,)).fetchone()
        if old:
            if bytes(old['context'])!=canonical(context):raise RunError('RESEARCH_CONTEXT_CHANGED')
            self.check(db,run);return
        db.execute('INSERT INTO research_runs VALUES(?,?,?,?,?,?)',(run,canonical(context),self.mac(context),None,0,self.mac(dict(run=run,head=None,count=0))))

    def check(self, db, run):
        row=db.execute('SELECT * FROM research_runs WHERE run=?',(run,)).fetchone()
        if not row:raise RunError('RESEARCH_RUN_MISSING',404)
        try:ctx=json.loads(row['context'])
        except (ValueError,TypeError):raise RunError('RESEARCH_CONTEXT_MALFORMED') from None
        if type(ctx) is not dict or ctx.get('run_id')!=run or not self.matches(ctx,row['context_mac']):raise RunError('RESEARCH_CONTEXT_TAMPERED')
        parent=None;items=[]
        for i,event in enumerate(db.execute('SELECT * FROM research_events WHERE run=? ORDER BY sequence',(run,)),1):
            raw=bytes(event['payload'])
            try:data=json.loads(raw)
            except (ValueError,TypeError):raise RunError('RESEARCH_TELEMETRY_CORRUPT') from None
            binding=dict(run=run,sequence=i,parent=parent,hash=hashlib.sha256(raw).hexdigest())
            if (event['sequence']!=i or event['parent']!=parent or event['hash']!=binding['hash'] or data.get('run_id')!=run
                    or len(raw)>MAX_EVENT_BYTES or not self.matches(binding,event['signature'])):raise RunError('RESEARCH_TELEMETRY_CORRUPT')
            parent=event['hash'];items.append(data)
        if len(items)!=row['count'] or parent!=row['head'] or not self.matches(dict(run=run,head=parent,count=len(items)),row['head_mac']):
            raise RunError('RESEARCH_TELEMETRY_TRUNCATED_OR_CORRUPT')
        return ctx,items

    def append(self, db, run, payload):
        _ctx,items=self.check(db,run)
        if items and items[-1]==payload:return
        raw=canonical(payload)
        if len(items)>=MAX_EVENTS or len(raw)>MAX_EVENT_BYTES:raise RunError('RESEARCH_TELEMETRY_LIMIT')
        parent=hashlib.sha256(canonical(items[-1])).hexdigest() if items else None
        seq=len(items)+1;fp=hashlib.sha256(raw).hexdigest();binding=dict(run=run,sequence=seq,parent=parent,hash=fp)
        db.execute('INSERT INTO research_events VALUES(?,?,?,?,?,?)',(run,seq,raw,parent,fp,self.mac(binding)))
        db.execute('UPDATE research_runs SET head=?,count=?,head_mac=? WHERE run=?',(fp,seq,self.mac(dict(run=run,head=fp,count=seq)),run))

    def save_proof(self, db, run, proof):
        self.check(db,run);raw=canonical(proof)
        if len(raw)>MAX_EVENT_BYTES:raise RunError('RESEARCH_PROOF_LIMIT')
        old=db.execute('SELECT * FROM research_proofs WHERE run=? AND sequence=?',(run,proof['sequence'])).fetchone()
        if old:
            if bytes(old['payload'])!=raw or not self.matches(proof,old['signature']):raise RunError('RESEARCH_PROOF_CHANGED')
            return
        if db.execute('SELECT COUNT(*) FROM research_proofs WHERE run=?',(run,)).fetchone()[0]>=21:raise RunError('RESEARCH_PROOF_LIMIT')
        db.execute('INSERT INTO research_proofs VALUES(?,?,?,?)',(run,proof['sequence'],raw,self.mac(proof)))

    def proof(self, db, run, sequence):
        row=db.execute('SELECT * FROM research_proofs WHERE run=? AND sequence=?',(run,sequence)).fetchone()
        if not row:raise RunError('RESEARCH_CONSUMPTION_MISSING')
        try:data=json.loads(row['payload'])
        except (ValueError,TypeError):raise RunError('RESEARCH_CONSUMPTION_TAMPERED') from None
        if type(data) is not dict or data.get('run_id')!=run or data.get('sequence')!=sequence or not self.matches(data,row['signature']):raise RunError('RESEARCH_CONSUMPTION_TAMPERED')
        return data

    def runs(self):
        self.guard()
        with self.store.connection() as db:return [r[0] for r in db.execute('SELECT run FROM research_runs')]
