"""U5L versioned adapter for NEW disposable U5I stores, never deployments."""
from contextlib import contextmanager
from dataclasses import dataclass,asdict
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from uuid import uuid4
from services.ga_run_authority import RunError,canonical,digest
from services.ga_storage_qualification import permissions

VERSION='ga-supervised-storage-v1'
SCHEMA='''
CREATE TABLE l_runs(run TEXT PRIMARY KEY REFERENCES workers(run), policy TEXT NOT NULL);
CREATE TABLE l_pins(run TEXT NOT NULL REFERENCES l_runs(run), sequence INTEGER NOT NULL, tip TEXT NOT NULL,
 policy TEXT NOT NULL, PRIMARY KEY(run,sequence));
CREATE TABLE l_processes(attempt TEXT PRIMARY KEY,run TEXT NOT NULL REFERENCES l_runs(run), fence INTEGER NOT NULL,
 executor TEXT NOT NULL,pid INTEGER NOT NULL,created INTEGER NOT NULL,status TEXT NOT NULL,
 heartbeat REAL NOT NULL,observation TEXT);
'''

@dataclass(frozen=True)
class StorageLimits:
    database_bytes:int=64*1024*1024
    minimum_free_bytes:int=64*1024*1024
    backup_count:int=1
    filesystem_bytes:int|None=None
    def validate(self):
        if (type(self.database_bytes) is not int or not 128*1024<=self.database_bytes<=256*1024*1024
                or self.database_bytes%4096 or type(self.minimum_free_bytes) is not int or self.minimum_free_bytes<=0
                or type(self.backup_count) is not int or self.backup_count!=1):raise RunError('GA_STORAGE_LIMIT_INVALID')
        if self.filesystem_bytes is not None:raise RunError('GA_FILESYSTEM_QUOTA_UNAVAILABLE',503)
        return self

def implementation():
    folder=Path(__file__).parent
    return digest({n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in
        ['ga_windows_supervisor.py','ga_supervised_storage.py','ga_supervised_worker.py']})

class LimitedStore:
    """Explicit per-instance adapter, not replacement of a production symbol.

    Every coordinator/worker connection uses its SQLite page limit. The limit
    covers the main database, not journals, backups or a filesystem/NTFS quota.
    """
    def __init__(self,base,resources,limits=StorageLimits(),*,initialize=False):
        self.original=base;self.limits=limits.validate();resources.validate();self.version=implementation()
        self.document=dict(contract=VERSION,store=base.store_id,implementation=self.version,
            resources=asdict(resources),storage=asdict(limits));self.policy=digest(self.document)
        marker=base.root/'U5L-policy.json'
        permissions(base.root)
        if initialize:
            if marker.exists():raise RunError('GA_SUPERVISION_NEW_STORAGE_REQUIRED')
            with base.connection() as db:
                if db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]:raise RunError('GA_SUPERVISION_NEW_STORAGE_REQUIRED')
                db.executescript('BEGIN IMMEDIATE;'+SCHEMA);db.commit()
            with marker.open('xb') as f:f.write(canonical(self.document));f.flush();__import__('os').fsync(f.fileno())
        self.guard()
        with self.connection():pass
    def __getattr__(self,name):return getattr(self.original,name)
    def guard(self):
        self.original.guard();p=self.root/'U5L-policy.json'
        if p.is_symlink() or p.is_junction() or p.read_bytes()!=canonical(self.document) or implementation()!=self.version:
            raise RunError('GA_SUPERVISION_STORAGE_POLICY_CHANGED')
    @contextmanager
    def connection(self):
        self.guard()
        if shutil.disk_usage(self.root).free<self.limits.minimum_free_bytes:raise RunError('GA_STORAGE_FREE_SPACE_INSUFFICIENT')
        with self.original.connection() as db:
            page=db.execute('PRAGMA page_size').fetchone()[0];maximum=self.limits.database_bytes//page
            if db.execute('PRAGMA page_count').fetchone()[0]>maximum:raise RunError('GA_STORAGE_PHYSICAL_DATABASE_LIMIT')
            if db.execute('PRAGMA journal_mode=DELETE').fetchone()[0]!='delete':raise RunError('GA_STORAGE_JOURNAL_UNQUALIFIED')
            if db.execute('PRAGMA max_page_count='+str(maximum)).fetchone()[0]!=maximum:raise RunError('GA_STORAGE_PHYSICAL_DATABASE_LIMIT')
            def authorize(action,a,b,*unused):
                if action==sqlite3.SQLITE_ATTACH or (action==sqlite3.SQLITE_PRAGMA and a in {'max_page_count','journal_mode'} and b is not None):return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            db.set_authorizer(authorize)
            yield db
    @contextmanager
    def transaction(self):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                yield db
                # K checkpoint and L physical-policy pin share this commit.
                for row in db.execute('SELECT w.run,w.sequence,w.tip,l.policy FROM workers w JOIN l_runs l ON l.run=w.run WHERE w.tip IS NOT NULL').fetchall():
                    old=db.execute('SELECT tip,policy FROM l_pins WHERE run=? AND sequence=?',(row['run'],row['sequence'])).fetchone()
                    if old:
                        if tuple(old)!=(row['tip'],self.policy):raise RunError('GA_SUPERVISION_CHECKPOINT_POLICY_MISMATCH')
                    else:
                        count=db.execute('SELECT COUNT(*) FROM l_pins WHERE run=?',(row['run'],)).fetchone()[0]
                        if row['policy']!=self.policy or count!=row['sequence']-1:raise RunError('GA_SUPERVISION_CHECKPOINT_POLICY_MISMATCH')
                        db.execute('INSERT INTO l_pins VALUES(?,?,?,?)',(row['run'],row['sequence'],row['tip'],self.policy))
                # Include conservatively bounded L metadata in the inherited
                # per-run payload quota, in addition to the real database cap.
                extra_total=0
                for row in db.execute('SELECT w.run,w.policy FROM workers w JOIN l_runs l ON l.run=w.run').fetchall():
                    extra=4096+2048*db.execute('SELECT COUNT(*) FROM l_processes WHERE run=?',(row['run'],)).fetchone()[0]
                    extra+=1024*db.execute('SELECT COUNT(*) FROM l_pins WHERE run=?',(row['run'],)).fetchone()[0]
                    if self.worker_store.size(db,row['run'])+extra+1024>json.loads(row['policy'])['run_bytes']:
                        raise RunError('GA_SUPERVISION_STORED_BYTES_LIMIT')
                    extra_total+=extra
                if self.worker_store.size(db)+extra_total+1024>self.max_bytes:raise RunError('GA_SUPERVISION_STORED_BYTES_LIMIT')
                db.commit()
            except BaseException:db.rollback();raise
    def bind(self,run):
        with self.transaction() as db:
            existing=db.execute('SELECT policy FROM l_runs WHERE run=?',(run,)).fetchone()
            if existing:
                if existing[0]!=self.policy:raise RunError('GA_SUPERVISION_POLICY_MISMATCH')
            else:db.execute('INSERT INTO l_runs VALUES(?,?)',(run,self.policy))
    def pin(self,row):
        with self.connection() as db:
            l=db.execute('SELECT policy FROM l_runs WHERE run=?',(row['id'],)).fetchone()
            if not l or l[0]!=self.policy:raise RunError('GA_SUPERVISION_POLICY_MISMATCH')
            if row['tip']:
                p=db.execute('SELECT tip,policy FROM l_pins WHERE run=? AND sequence=?',(row['id'],row['sequence'])).fetchone()
                if not p or tuple(p)!=(row['tip'],self.policy):raise RunError('GA_SUPERVISION_CHECKPOINT_POLICY_MISMATCH')
    def backup(self,coordinator,principal,run):
        row=self.owned_worker(coordinator,principal,run);self.pin(row)
        if row['executor'] or row['state'] not in {'PAUSED','COMPLETED','STOPPED','FAILED'}:
            raise RunError('GA_BACKUP_INACTIVE_RUN_REQUIRED')
        folder=self.root/'backups'
        if folder.exists():raise RunError('GA_BACKUP_RETENTION_LIMIT')
        if shutil.disk_usage(self.root).free<self.limits.minimum_free_bytes+2*self.limits.database_bytes:raise RunError('GA_STORAGE_FREE_SPACE_INSUFFICIENT')
        folder.mkdir();path=folder/'snapshot.sqlite3'
        with path.open('xb'):pass
        with self.connection() as source,sqlite3.connect(path) as target:
            source.execute('BEGIN');source.backup(target);source.rollback()
        metadata=dict(contract=VERSION,store=self.store_id,policy=self.policy,run=run,owner=row['actor'],department=row['department'],
            bundle=row['bundle_hash'],tip=row['tip'],sequence=row['sequence'],fence=row['fence'],sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        with (folder/'manifest.json').open('xb') as f:f.write(canonical(metadata))
        return self.inspect_backup(coordinator,principal,run)
    def inspect_backup(self,coordinator,principal,run):
        row=self.owned_worker(coordinator,principal,run);self.pin(row);folder=self.root/'backups';path=folder/'snapshot.sqlite3';meta=folder/'manifest.json'
        if any(p.is_symlink() or p.is_junction() for p in [folder,path,meta]) or path.stat().st_size>self.limits.database_bytes:raise RunError('GA_BACKUP_SCOPE_INVALID')
        d=json.loads(meta.read_bytes())
        if (set(d)!={'contract','store','policy','run','owner','department','bundle','tip','sequence','fence','sha256'}
                or d['contract']!=VERSION or d['bundle']!=row['bundle_hash']
                or d['store']!=self.store_id or d['policy']!=self.policy or d['run']!=run or d['owner']!=row['actor'] or d['department']!=row['department']
                or d['sha256']!=hashlib.sha256(path.read_bytes()).hexdigest()):raise RunError('GA_BACKUP_BINDING_INVALID')
        if (d['tip'],d['sequence'],d['fence'])!=(row['tip'],row['sequence'],row['fence']):raise RunError('GA_BACKUP_STALE')
        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchall():raise RunError('GA_BACKUP_CORRUPT')
            w=db.execute('SELECT tip,sequence FROM workers WHERE run=?',(run,)).fetchone()
            if tuple(w)!=(row['tip'],row['sequence']):raise RunError('GA_BACKUP_BINDING_INVALID')
            if row['tip']:self.worker_store.checkpoint(db,row)
        return dict(scope='FICTIONAL_BACKUP_INSPECTION_ONLY',integrity='PASS',lineage_tip=row['tip'],restore_enabled=False,
            reason='WRITABLE_RESTORE_AND_RETENTION_AUTHORITY_UNQUALIFIED',physical_database_bytes=path.stat().st_size)

    def owned_worker(self,coordinator,principal,run):
        coordinator.inspect(principal,run,'checkpoint')
        with self.connection() as db:return self.worker_store.row(db,coordinator.actor(principal),run)
