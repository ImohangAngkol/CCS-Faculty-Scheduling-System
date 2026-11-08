"""U5N disposable writable quarantine, NOT an activated worker/store restore.

Independent anchor and vault transactions deliberately fail closed across a
crash between commits. Existing I-L worker paths do not consult this anchor;
therefore no API here resumes, publishes, replaces or deletes an existing run.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import base64
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import time
from services.ga_owned_store import Store
from services.ga_storage_qualification import permissions
from services.ga_run_authority import RunError,canonical,digest,uuid
from services.ga_recovery_qualification import RecoveryContext
from services.ga_worker_contract import fictional_source

VERSION='ga-checkpoint-quarantine-v1'

@dataclass(frozen=True,repr=False)
class Package:
    run_id:str
    owner_id:str
    department_id:str
    bundle:bytes
    chain:tuple[bytes,...]
    def __repr__(self):return '<Fictional checkpoint package; payload withheld>'
    def raw(self):
        return canonical(dict(contract=VERSION,run_id=self.run_id,owner_id=self.owner_id,department_id=self.department_id,
            bundle=base64.b64encode(self.bundle).decode(),chain=[base64.b64encode(r).decode() for r in self.chain]))
    @classmethod
    def decode(cls,raw):
        try:
            d=json.loads(raw)
            if set(d)!={'contract','run_id','owner_id','department_id','bundle','chain'} or d['contract']!=VERSION:raise ValueError()
            p=cls(d['run_id'],d['owner_id'],d['department_id'],base64.b64decode(d['bundle'],validate=True),tuple(base64.b64decode(r,validate=True) for r in d['chain']))
            if p.raw()!=raw:raise ValueError()
            return p
        except Exception:raise RunError('GA_RECOVERY_PACKAGE_INVALID') from None
    def validate(self):
        from services.ga_input_bundle import InputBundle
        from services.ga_bundle_optimizer import Session
        try:
            for value in [self.run_id,self.owner_id,self.department_id]:uuid(value)
            if type(self.bundle) is not bytes or type(self.chain) is not tuple or not 1<=len(self.chain)<=8:raise ValueError()
            if len(self.bundle)>8*1024*1024 or any(type(r) is not bytes or len(r)>8*1024*1024 for r in self.chain):raise ValueError()
            bundle=InputBundle.from_bytes(self.bundle,self.run_id,hashlib.sha256(self.bundle).hexdigest());parent=None
            for index,raw in enumerate(self.chain,1):
                tip=hashlib.sha256(raw).hexdigest()
                session=Session.restore(bundle,raw,run_id=self.run_id,expected_fingerprint=tip,expected_sequence=index,expected_parent=parent)
                parent=tip
            return dict(contract=VERSION,run_id=self.run_id,owner_id=self.owner_id,department_id=self.department_id,
                bundle=bundle.fingerprint,configuration=session.config_fingerprint,optimizer=session.optimizer_fingerprint,
                sequence=len(self.chain),tip=parent,package_hash=hashlib.sha256(self.raw()).hexdigest())
        except Exception:raise RunError('GA_RECOVERY_PACKAGE_OR_CHECKPOINT_INVALID') from None

class PrivateRoot:
    """Server-created approval in memory; never accepts a client-selected root.

    Stat identities supplement I's marker and J's real private DACL inspection.
    This is a trusted-local-process boundary, not hostile-admin FS protection.
    """
    @classmethod
    def create(cls):
        fictional_source();store=Store.create(max_runs=4)
        pins=tuple((p,cls.identity(p)) for p in [store.root,store.root/'OWNER.json',store.root/'records.sqlite3'])
        return cls(store,RootApproval(str(store.root),store.store_id,pins))
    def __init__(self,store,approval=None):
        fictional_source()
        if (type(store) is not Store or type(approval) is not RootApproval
                or (approval.root,approval.store_id)!=(str(store.root),store.store_id)
                or tuple(p for p,_ in approval.pins)!=(store.root,store.root/'OWNER.json',store.root/'records.sqlite3')):
            raise RunError('GA_RECOVERY_ROOT_UNAPPROVED')
        self.store=store;self.approval=approval;self.pins=approval.pins;self.guard()
    @staticmethod
    def identity(path):
        if path.is_symlink() or path.is_junction():raise RunError('GA_RECOVERY_REPARSE_REJECTED')
        s=path.stat();return s.st_dev,s.st_ino
    def guard(self):
        try:
            self.store.guard()
            if any(self.identity(p)!=pin for p,pin in self.pins):raise ValueError()
            permissions(self.store.root)
        except Exception:raise RunError('GA_RECOVERY_ROOT_IDENTITY_CHANGED') from None
    @contextmanager
    def transaction(self):
        self.guard()
        if shutil.disk_usage(self.store.root).free<64*1024*1024:raise RunError('GA_RECOVERY_DISK_HEADROOM')
        with self.store.transaction() as db:
            if db.execute('PRAGMA journal_mode=DELETE').fetchone()[0]!='delete':raise RunError('GA_RECOVERY_JOURNAL_INVALID')
            page=db.execute('PRAGMA page_size').fetchone()[0]
            if db.execute('PRAGMA max_page_count='+str(32*1024*1024//page)).fetchone()[0]*page>32*1024*1024:raise RunError('GA_RECOVERY_DATABASE_QUOTA')
            yield db
            self.guard()

@dataclass(frozen=True)
class RootApproval:
    """Trusted provisioning registry value, not a client/file approval claim."""
    root:str
    store_id:str
    pins:tuple

class Anchor:
    """Independent, durable fictional freshness oracle. No deployment provider.

    Pin updates must come from trusted checkpoint observations, never a backup
    manifest. Existing workers are NOT automatically fenced by this oracle.
    """
    def __init__(self,root,*,initialize=False):
        self.root=root
        if initialize:
            with root.transaction() as db:db.execute('CREATE TABLE n_heads(run TEXT PRIMARY KEY,facts TEXT NOT NULL,epoch INTEGER NOT NULL,request TEXT,target TEXT)')
    def pin(self,package,*,expected_epoch):
        facts=package.validate()
        with self.root.transaction() as db:
            old=db.execute('SELECT * FROM n_heads WHERE run=?',(package.run_id,)).fetchone()
            if (old['epoch'] if old else 0)!=expected_epoch:raise RunError('GA_RECOVERY_ANCHOR_STALE')
            if old:
                previous=json.loads(old['facts'])
                if (any(previous[k]!=facts[k] for k in ['run_id','owner_id','department_id','bundle','configuration','optimizer'])
                        or facts['sequence']<=previous['sequence']
                        or hashlib.sha256(package.chain[previous['sequence']-1]).hexdigest()!=previous['tip']):
                    raise RunError('GA_RECOVERY_ANCHOR_NONADVANCING_LINEAGE')
            db.execute('INSERT OR REPLACE INTO n_heads VALUES(?,?,?,NULL,NULL)',(package.run_id,canonical(facts).decode(),expected_epoch+1))
        return expected_epoch+1
    @contextmanager
    def reserve(self,context,facts):
        with self.root.transaction() as db:
            row=db.execute('SELECT * FROM n_heads WHERE run=?',(context.run_id,)).fetchone()
            if not row or row['epoch']!=context.epoch or row['facts']!=canonical(facts).decode():raise RunError('GA_RECOVERY_ANCHOR_STALE')
            if row['request'] is not None:raise RunError('GA_RECOVERY_REPLAY_REJECTED')
            yield
            db.execute('UPDATE n_heads SET request=?,target=? WHERE run=?',(context.request_id,context.target_store,context.run_id))
    def completed(self,context):
        with self.root.transaction() as db:
            r=db.execute('SELECT * FROM n_heads WHERE run=?',(context.run_id,)).fetchone()
            if not r or (r['epoch'],r['request'],r['target'])!=(context.epoch,context.request_id,context.target_store):raise RunError('GA_RECOVERY_ANCHOR_INCOMPLETE')
            facts=json.loads(r['facts'])
            if (facts['package_hash'],facts['owner_id'],facts['department_id'])!=(context.package_hash,context.actor_id,context.department_id):raise RunError('GA_RECOVERY_ANCHOR_BINDING_CHANGED')

class Vault:
    def __init__(self,root,anchor,authority,*,initialize=False,maximum_package_bytes=8*1024*1024,maximum_total_bytes=16*1024*1024,clock=time.time,fault=lambda _:None):
        fictional_source()
        if type(root) is not PrivateRoot or type(anchor) is not Anchor or root.store.store_id==anchor.root.store.store_id:raise RunError('GA_RECOVERY_INDEPENDENT_ROOTS_REQUIRED')
        if any(type(v) is not int or v<=0 or v>16*1024*1024 for v in [maximum_package_bytes,maximum_total_bytes]):raise RunError('GA_RECOVERY_LIMIT_INVALID')
        self.root=root;self.anchor=anchor;self.authority=authority;self.maximum_package_bytes=maximum_package_bytes;self.maximum_total_bytes=maximum_total_bytes;self.clock=clock;self.fault=fault
        if initialize:
            with root.transaction() as db:
                db.execute('CREATE TABLE n_restores(run TEXT UNIQUE NOT NULL,request TEXT PRIMARY KEY,actor TEXT NOT NULL,department TEXT NOT NULL,epoch INTEGER NOT NULL,hash TEXT NOT NULL,raw BLOB NOT NULL)')
                db.execute('CREATE TABLE n_audit(id INTEGER PRIMARY KEY,body TEXT NOT NULL)')
    def event(self,db,context,decision,provenance=None):
        if db.execute('SELECT COUNT(*) FROM n_audit').fetchone()[0]>=256:raise RunError('GA_RECOVERY_AUDIT_CAPACITY')
        row=dict(actor_id=context.actor_id,department_id=context.department_id,target_run=context.run_id,
            action=context.action,decision=decision,time=self.clock(),request_id=context.request_id,epoch=context.epoch,
            target_store=context.target_store,package_hash=context.package_hash,authority=provenance)
        db.execute('INSERT INTO n_audit(body) VALUES(?)',(canonical(row).decode(),))
    def restore(self,principal,package,request_id,epoch):
        from services.ga_trusted_runs import Coordinator
        actor=Coordinator.actor(principal);uuid(request_id);facts=package.validate()
        context=RecoveryContext(actor,package.department_id,package.run_id,request_id,facts['package_hash'],epoch,self.root.store.store_id)
        committed=False
        try:
            if actor!=package.owner_id:raise RunError('GA_RECOVERY_OWNER_REQUIRED',403)
            if self.authority is None:raise RunError('GA_RECOVERY_AUTHORITY_UNAVAILABLE',503)
            with self.authority.authorized(context) as grant,self.anchor.reserve(context,facts):
                raw=package.raw()
                with self.root.transaction() as db:
                    if db.execute('SELECT 1 FROM n_restores WHERE run=? OR request=?',(package.run_id,request_id)).fetchone():raise RunError('GA_RECOVERY_EXISTING_RUN_OR_REQUEST')
                    used=db.execute('SELECT COALESCE(SUM(length(raw)),0) FROM n_restores').fetchone()[0]
                    if len(raw)>self.maximum_package_bytes or used+len(raw)>self.maximum_total_bytes:raise RunError('GA_RECOVERY_PAYLOAD_QUOTA')
                    db.execute('INSERT INTO n_restores VALUES(?,?,?,?,?,?,?)',(package.run_id,request_id,actor,package.department_id,epoch,facts['package_hash'],raw))
                    self.event(db,context,'QUARANTINE_PREPARED',grant);self.fault('BEFORE_VAULT_COMMIT')
                    if self.clock()>=grant['expires_at']:raise RunError('GA_RECOVERY_AUTHORITY_EXPIRED')
                committed=True;self.fault('AFTER_VAULT_COMMIT')
            return self.inspect(principal,package.run_id)
        except BaseException as exc:
            # Do not discard an uncertain committed package or silently retry.
            failure=exc if isinstance(exc,RunError) else RunError('GA_RECOVERY_INTERRUPTED_REVIEW_REQUIRED')
            try:
                with self.root.transaction() as db:self.event(db,context,'INDETERMINATE' if committed else 'REJECTED')
            except Exception:failure.add_note('GA_RECOVERY_AUDIT_UNAVAILABLE')
            raise failure from None
    def inspect(self,principal,run_id):
        from services.ga_trusted_runs import Coordinator
        actor=Coordinator.actor(principal);uuid(run_id)
        with self.root.transaction() as db:r=db.execute('SELECT * FROM n_restores WHERE run=? AND actor=?',(run_id,actor)).fetchone()
        if r is None:raise RunError('GA_RECOVERY_NOT_FOUND',404)
        context=RecoveryContext(actor,r['department'],run_id,r['request'],r['hash'],r['epoch'],self.root.store.store_id,'inspect_quarantine')
        if self.authority is None:raise RunError('GA_RECOVERY_AUTHORITY_UNAVAILABLE',503)
        with self.authority.authorized(context):
            self.anchor.completed(context);package=Package.decode(bytes(r['raw']));facts=package.validate()
            if facts['package_hash']!=r['hash'] or (package.owner_id,package.department_id)!=(actor,r['department']):raise RunError('GA_RECOVERY_STORED_PACKAGE_CHANGED')
            return dict(contract=VERSION,state='VALIDATED_QUARANTINE',request_id=r['request'],run_id=run_id,
                checkpoint_tip=facts['tip'],sequence=facts['sequence'],epoch=r['epoch'],optimizer=facts['optimizer'],
                writable_quarantine=True,worker_resume_enabled=False,institutional_restore_enabled=False,
                reason='EXISTING_WORKERS_NOT_BOUND_TO_INDEPENDENT_RECOVERY_FENCE')
