"""Isolated SQLite durable store. Only newly owned, ACL-private OS-temp roots.

No default application path, connection URL, PostgreSQL, existing database or
legacy scheduling store. Production storage configuration remains uninstalled.
SQLite transactions atomically bind checkpoint bytes and their trusted tip.
"""
from contextlib import contextmanager
import base64
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
from uuid import uuid4
from services.ga_run_authority import RunError,canonical

CONTRACT='ga-owned-sqlite-store-v1'
SCHEMA='''
CREATE TABLE runs(
 id TEXT PRIMARY KEY, actor TEXT NOT NULL, department TEXT NOT NULL, request_key TEXT NOT NULL,
 request_digest TEXT NOT NULL, catalog TEXT NOT NULL, policy TEXT NOT NULL, created REAL NOT NULL, retain_until REAL NOT NULL,
 bundle BLOB NOT NULL, bundle_hash TEXT NOT NULL, config_hash TEXT NOT NULL, optimizer TEXT NOT NULL,
 persistence TEXT NOT NULL, initial_rng BLOB NOT NULL,
 state TEXT NOT NULL, desired TEXT, fence INTEGER NOT NULL DEFAULT 0, executor TEXT, lease REAL NOT NULL DEFAULT 0,
 tip TEXT, sequence INTEGER NOT NULL DEFAULT 0, parent TEXT, result BLOB, result_hash TEXT, receipt TEXT, error TEXT,
 UNIQUE(actor,department,request_key));
CREATE TABLE checkpoints(run TEXT NOT NULL REFERENCES runs(id), sequence INTEGER NOT NULL,
 hash TEXT NOT NULL UNIQUE, parent TEXT, raw BLOB NOT NULL, PRIMARY KEY(run,sequence));
PRAGMA user_version=1;
'''


def secure(root):
    if os.name!='nt':root.chmod(0o700);return
    # The exact newly-created target is checked before any ACL operation.
    assert root.parent==Path(tempfile.gettempdir()).resolve() and root.name.startswith('ga-u5i-')
    path=str(root).replace("'","''")
    script="""$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
Import-Module (Join-Path $PSHOME 'Modules/Microsoft.PowerShell.Security/Microsoft.PowerShell.Security.psd1') -ErrorAction Stop
$p='TARGET'
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
$acl=[IO.Directory]::GetAccessControl($p,[Security.AccessControl.AccessControlSections]::Access)
$acl.SetAccessRuleProtection($true,$false)
foreach($existing in @($acl.GetAccessRules($true,$false,[Security.Principal.SecurityIdentifier]))){$acl.RemoveAccessRuleSpecific($existing)}
$ids=@($sid.Value,'S-1-5-18','S-1-5-32-544')
foreach($id in $ids){$rule=New-Object Security.AccessControl.FileSystemAccessRule([Security.Principal.SecurityIdentifier]$id,'FullControl','ContainerInherit,ObjectInherit','None','Allow');$acl.AddAccessRule($rule)}
[IO.Directory]::SetAccessControl($p,$acl)
$actual=Get-Acl -LiteralPath $p
if(-not $actual.AreAccessRulesProtected){throw 'ACL'}
$rules=@($actual.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
if($rules.Count -ne 3){throw 'ACL'}
foreach($r in $rules){if($r.IdentityReference.Value -notin $ids -or $r.IsInherited -or $r.AccessControlType -ne 'Allow' -or ($r.FileSystemRights -band [Security.AccessControl.FileSystemRights]::FullControl) -ne [Security.AccessControl.FileSystemRights]::FullControl){throw 'ACL'}}
Write-Output 'ACL_VERIFIED'
""".replace('TARGET',path)
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE'}
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(script.encode('utf-16le')).decode()],
        env={k:v for k,v in os.environ.items() if k.upper() in allowed},capture_output=True,text=True,timeout=30)
    if result.returncode or result.stdout.strip()!='ACL_VERIFIED':raise RunError('GA_STORE_ACL_UNVERIFIED',503)


class Store:
    @classmethod
    def create(cls,*,clock=time.time,max_runs=64,max_checkpoints=16,max_bytes=256*1024*1024,retention_seconds=7*86400):
        cls.validate_limits(max_runs,max_checkpoints,max_bytes,retention_seconds)
        root=Path(tempfile.mkdtemp(prefix='ga-u5i-')).resolve();secure(root)
        identity=str(uuid4());marker={'contract':CONTRACT,'store_id':identity,'scope':'ISOLATED_DISPOSABLE_ONLY',
            'limits':[max_runs,max_checkpoints,max_bytes,retention_seconds]}
        with (root/'OWNER.json').open('x',encoding='utf-8') as f:json.dump(marker,f)
        with (root/'records.sqlite3').open('xb') as f:f.flush();os.fsync(f.fileno())
        db=sqlite3.connect((root/'records.sqlite3').as_uri()+'?mode=rw',uri=True)
        try:db.executescript(SCHEMA)
        finally:db.close()
        return cls(root,identity,clock=clock,max_runs=max_runs,max_checkpoints=max_checkpoints,max_bytes=max_bytes,retention_seconds=retention_seconds)

    def __init__(self,root,store_id,*,clock=time.time,max_runs=64,max_checkpoints=16,max_bytes=256*1024*1024,retention_seconds=7*86400):
        self.validate_limits(max_runs,max_checkpoints,max_bytes,retention_seconds)
        self.root=Path(root).absolute();self.store_id=store_id;self.clock=clock
        self.max_runs=max_runs;self.max_checkpoints=max_checkpoints;self.max_bytes=max_bytes;self.retention_seconds=retention_seconds
        self.guard()

    @staticmethod
    def validate_limits(*limits):
        if any(type(v) is not int or v<=0 for v in limits):raise RunError('GA_STORE_LIMITS_INVALID',422)

    def guard(self):
        try:
            if self.root.parent.resolve()!=Path(tempfile.gettempdir()).resolve() or not self.root.name.startswith('ga-u5i-'):raise ValueError()
            for p in [self.root,self.root/'OWNER.json',self.root/'records.sqlite3']:
                if p.is_symlink() or p.is_junction():raise ValueError()
            marker=json.loads((self.root/'OWNER.json').read_bytes())
            if marker!={'contract':CONTRACT,'store_id':self.store_id,'scope':'ISOLATED_DISPOSABLE_ONLY',
                'limits':[self.max_runs,self.max_checkpoints,self.max_bytes,self.retention_seconds]}:raise ValueError()
        except (ValueError,OSError,TypeError):raise RunError('GA_STORE_IDENTITY_INVALID',503) from None

    @contextmanager
    def connection(self):
        self.guard()
        try:
            db=sqlite3.connect((self.root/'records.sqlite3').as_uri()+'?mode=rw',uri=True,timeout=10,isolation_level=None)
            try:
                db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA synchronous=FULL')
                if db.execute('PRAGMA user_version').fetchone()[0]!=1:raise RunError('GA_STORE_VERSION_UNSUPPORTED')
                yield db
            finally:db.close()
        except sqlite3.Error:raise RunError('GA_STORE_TRANSACTION_FAILED',503) from None

    @contextmanager
    def transaction(self):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            try:yield db;db.commit()
            except BaseException:db.rollback();raise

    def capacity(self,db,extra=0):
        used=db.execute('SELECT COALESCE(SUM(length(bundle)+length(initial_rng)+COALESCE(length(receipt),0)+COALESCE(length(result),0)),0) FROM runs').fetchone()[0]
        used+=db.execute('SELECT COALESCE(SUM(length(raw)),0) FROM checkpoints').fetchone()[0]
        if used+extra>self.max_bytes:raise RunError('GA_STORE_RETENTION_LIMIT')

    def row(self,db,run_id):
        row=db.execute('SELECT * FROM runs WHERE id=?',(run_id,)).fetchone()
        if row is None:raise RunError('GA_RUN_NOT_FOUND',404)
        if row['retain_until']<=self.clock():raise RunError('GA_RUN_RETENTION_EXPIRED',410)
        return dict(row)

    def fenced(self,db,run_id,executor,fence):
        row=self.row(db,run_id)
        if row['executor']!=executor or row['fence']!=fence or row['lease']<=self.clock():raise RunError('GA_RUN_OWNERSHIP_LOST')
        return row

    def claim(self,run_id,executor,*,recover=False,lease_seconds=120,expected_tip=None,expected_sequence=0,before_commit=lambda:None):
        with self.transaction() as db:
            row=self.row(db,run_id)
            if row['tip']!=expected_tip or row['sequence']!=expected_sequence:raise RunError('GA_RUN_CHECKPOINT_LINEAGE')
            if row['executor'] and row['lease']>self.clock():raise RunError('GA_RUN_EXECUTION_ACTIVE')
            if row['state'] in {'COMPLETED','STOPPED'}:raise RunError('GA_RUN_TERMINAL')
            if row['state'] not in {'ADMITTED','PAUSED'}:
                if not recover:raise RunError('GA_RUN_RECOVERY_REQUIRED')
                if not row['tip']:raise RunError('GA_RUN_CHECKPOINT_MISSING')
            fence=row['fence']+1
            db.execute("UPDATE runs SET executor=?,fence=?,lease=?,state='RUNNING',error=NULL WHERE id=?",(executor,fence,self.clock()+lease_seconds,run_id))
            before_commit()
            return self.row(db,run_id),fence

    def checkpoint(self,run_id,executor,fence,raw,fp,sequence,parent,*,before_commit=lambda:None):
        if hashlib.sha256(raw).hexdigest()!=fp:raise RunError('GA_RUN_CHECKPOINT_INTEGRITY')
        with self.transaction() as db:
            row=self.fenced(db,run_id,executor,fence)
            if sequence!=row['sequence']+1 or parent!=row['tip']:raise RunError('GA_RUN_CHECKPOINT_LINEAGE')
            if sequence>self.max_checkpoints:raise RunError('GA_STORE_RETENTION_LIMIT')
            self.capacity(db,len(raw))
            db.execute('INSERT INTO checkpoints VALUES(?,?,?,?,?)',(run_id,sequence,fp,parent,raw))
            db.execute("UPDATE runs SET tip=?,sequence=?,parent=?,state='PAUSED' WHERE id=?",(fp,sequence,parent,run_id))
            before_commit()

    def load_checkpoint(self,db,row):
        if not row['tip']:raise RunError('GA_RUN_CHECKPOINT_MISSING')
        chain=db.execute('SELECT * FROM checkpoints WHERE run=? ORDER BY sequence',(row['id'],)).fetchall()
        parent=None
        for index,cp in enumerate(chain,1):
            if cp['sequence']!=index or cp['parent']!=parent or hashlib.sha256(cp['raw']).hexdigest()!=cp['hash']:
                raise RunError('GA_RUN_CHECKPOINT_INTEGRITY')
            parent=cp['hash']
        if len(chain)!=row['sequence'] or parent!=row['tip'] or chain[-1]['parent']!=row['parent']:raise RunError('GA_RUN_CHECKPOINT_LINEAGE')
        return bytes(chain[-1]['raw'])
