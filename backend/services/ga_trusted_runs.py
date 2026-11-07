"""Server-owned, synchronous U5H admission. No deployed issuer/source/store."""
from contextlib import contextmanager,ExitStack
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import random
import secrets
import time
from uuid import uuid4
from services.ga_run_authority import Context,RunError,verify,uuid,canonical,digest
from services.ga_input_bundle import InputBundle
from services.ga_bundle_optimizer import Session
from services import ga_owned_store,ga_run_authority

VERSION='ga-trusted-admission-v1'

@dataclass(frozen=True)
class Capture:
    bundle:InputBundle
    department_id:str
    catalog_reference:str

def configured_service():
    """Genuine optimization authority/capture/storage remain unconfigured."""
    return None

def release_fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes()+Path(ga_owned_store.__file__).read_bytes()+Path(ga_run_authority.__file__).read_bytes()).hexdigest()

class Coordinator:
    def __init__(self,store,authority,source,*,clock=time.time):
        self.store=store;self.authority=authority;self.source=source;self.clock=clock
        self.process_id=str(uuid4());self.persistence=release_fingerprint()

    @staticmethod
    def actor(principal):
        if principal is None or not principal.user_id:raise RunError('GA_RUN_AUTHENTICATION_REQUIRED',401)
        return uuid(principal.user_id)

    @contextmanager
    def authorized(self,context,policy=None):
        if self.authority is None:raise RunError('GA_OPTIMIZATION_AUTHORITY_UNAVAILABLE',503)
        stack=ExitStack()
        try:stack.enter_context(self.authority.guard(context))
        except Exception:raise RunError('GA_OPTIMIZATION_AUTHORITY_UNAVAILABLE',503) from None
        with stack:
            grant=verify(self.authority,context,self.clock)
            if policy and grant.policy_digest!=policy:raise RunError('GA_OPTIMIZATION_POLICY_CHANGED')
            yield grant

    def check(self,context,policy):
        grant=verify(self.authority,context,self.clock)
        if grant.policy_digest!=policy:raise RunError('GA_OPTIMIZATION_POLICY_CHANGED')

    def context(self,actor,row,action):
        return Context(actor,row['department'],action,row['id'],row['bundle_hash'],row['config_hash'],row['catalog'])

    def owned(self,db,actor,run_id):
        uuid(run_id);row=self.store.row(db,run_id)
        if row['actor']!=actor:raise RunError('GA_RUN_NOT_FOUND',404)
        if row['persistence']!=self.persistence:raise RunError('GA_RUN_PERSISTENCE_VERSION_CHANGED')
        return row

    def public(self,row):
        state=row['state']
        if row['executor'] and row['lease']<=self.clock() and state not in {'COMPLETED','STOPPED'}:state='INTERRUPTED'
        return {'contract':VERSION,'run_id':row['id'],'owner_id':row['actor'],'department_id':row['department'],
            'optimizer_version':'ga-bundle-consumer-v1','storage_contract':ga_owned_store.CONTRACT,
            'persistence_fingerprint':row['persistence'],'eligible_for_current':False,
            'state':state,'bundle_fingerprint':row['bundle_hash'],'configuration_fingerprint':row['config_hash'],
            'optimizer_fingerprint':row['optimizer'],'checkpoint_fingerprint':row['tip'],'checkpoint_sequence':row['sequence'],
            'error_code':row['error'],'receipt':json.loads(row['receipt']) if row['receipt'] else None,
            'publication':False,'saved_best_promotion':False,'schedule_status':'GA-generated proposal'}

    def admit(self,principal,department_id,request_key,catalog_reference):
        actor=self.actor(principal);uuid(department_id);uuid(request_key)
        if not isinstance(catalog_reference,str) or not 1<=len(catalog_reference)<=100:raise RunError('GA_CATALOG_REFERENCE_INVALID',422)
        request_digest=digest({'contract':VERSION,'actor':actor,'department':department_id,'catalog':catalog_reference})
        initial=Context(actor,department_id,'admit',catalog_reference=catalog_reference)
        with self.authorized(initial):
            with self.store.transaction() as db:
                existing=db.execute('SELECT * FROM runs WHERE actor=? AND department=? AND request_key=?',(actor,department_id,request_key)).fetchone()
                if existing:
                    row=self.owned(db,actor,existing['id'])
                    if row['request_digest']!=request_digest:raise RunError('GA_RUN_IDEMPOTENCY_CONFLICT')
                    self.check(self.context(actor,row,'admit'),row['policy']);return self.public(row)
                if db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]>=self.store.max_runs:raise RunError('GA_STORE_RETENTION_LIMIT')
                if self.source is None:raise RunError('GA_RUN_CAPTURE_SOURCE_UNAVAILABLE',503)
                run_id=str(uuid4())
                with self.source.guard(actor,department_id,catalog_reference) as source:captured=source.capture(run_id,actor,department_id,catalog_reference)
                if type(captured) is not Capture or captured.department_id!=department_id or captured.catalog_reference!=catalog_reference:raise RunError('GA_RUN_CAPTURE_SCOPE_MISMATCH')
                from services.ga_checkpoint_service import rng_to_json
                rng=random.Random(secrets.randbits(128)).getstate();session=Session(captured.bundle,run_id=run_id,random_state=rng)
                raw=captured.bundle._raw;initial_rng=canonical(rng_to_json(rng));self.store.capacity(db,len(raw)+len(initial_rng))
                row={'id':run_id,'actor':actor,'department':department_id,'bundle_hash':captured.bundle.fingerprint,'config_hash':session.config_fingerprint,'catalog':catalog_reference}
                grant=verify(self.authority,self.context(actor,row,'admit'),self.clock)
                db.execute('''INSERT INTO runs(id,actor,department,request_key,request_digest,catalog,policy,created,retain_until,
                    bundle,bundle_hash,config_hash,optimizer,persistence,initial_rng,state) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (run_id,actor,department_id,request_key,request_digest,catalog_reference,grant.policy_digest,self.clock(),self.clock()+self.store.retention_seconds,
                     raw,captured.bundle.fingerprint,session.config_fingerprint,session.optimizer_fingerprint,self.persistence,initial_rng,'ADMITTED'))
                self.check(self.context(actor,row,'admit'),grant.policy_digest);return self.public(self.store.row(db,run_id))

    def inspect(self,principal,run_id,action='status'):
        actor=self.actor(principal)
        with self.store.connection() as db:row=self.owned(db,actor,run_id)
        with self.authorized(self.context(actor,row,action),row['policy']):return row

    def status(self,principal,run_id):return self.public(self.inspect(principal,run_id))

    def command(self,principal,run_id,command):
        if command not in {'pause','stop'}:raise RunError('GA_RUN_COMMAND_INVALID',422)
        row=self.inspect(principal,run_id,command);actor=self.actor(principal);context=self.context(actor,row,command)
        with self.authorized(context,row['policy']):
            with self.store.transaction() as db:
                row=self.owned(db,actor,run_id)
                if row['state'] not in {'COMPLETED','STOPPED'}:
                    active=bool(row['executor'] and row['lease']>self.clock())
                    if command=='stop' and not active:db.execute("UPDATE runs SET state='STOPPED',desired=NULL,executor=NULL,lease=0,fence=fence+1 WHERE id=?",(run_id,))
                    elif row['desired']!='STOP':
                        desired='STOP' if command=='stop' else 'PAUSE'
                        state=('STOP_REQUESTED' if desired=='STOP' else 'PAUSE_REQUESTED') if active else row['state']
                        db.execute('UPDATE runs SET desired=?,state=? WHERE id=?',(desired,state,run_id))
                self.check(context,row['policy']);return self.public(self.store.row(db,run_id))

    def _session(self,row,raw=None,cls=Session):
        from services.ga_checkpoint_service import rng_from_json
        bundle=InputBundle.from_bytes(bytes(row['bundle']),row['id'],row['bundle_hash'])
        if raw is None:session=cls(bundle,run_id=row['id'],random_state=rng_from_json(json.loads(row['initial_rng'])))
        else:session=cls.restore(bundle,raw,run_id=row['id'],expected_fingerprint=row['tip'],expected_sequence=row['sequence'],expected_parent=row['parent'])
        if session.optimizer_fingerprint!=row['optimizer'] or session.config_fingerprint!=row['config_hash']:raise RunError('GA_RUN_OPTIMIZER_BINDING_CHANGED')
        return session

    def checkpoint(self,principal,run_id):
        row=self.inspect(principal,run_id,'checkpoint')
        with self.authorized(self.context(self.actor(principal),row,'checkpoint'),row['policy']):
            with self.store.connection() as db:
                current=self.owned(db,self.actor(principal),run_id);raw=self.store.load_checkpoint(db,current);self._session(current,raw);return raw

    def result(self,principal,run_id):
        row=self.inspect(principal,run_id,'result')
        if row['result'] is None:raise RunError('GA_RUN_RESULT_UNAVAILABLE',404)
        if hashlib.sha256(row['result']).hexdigest()!=row['result_hash']:raise RunError('GA_RUN_RESULT_CORRUPT')
        return json.loads(row['result'])

    def execute(self,principal,run_id,*,resume=False,observer=None):
        actor=self.actor(principal);action='resume' if resume else 'execute'
        row=self.inspect(principal,run_id,action);context=self.context(actor,row,action)
        if not resume and row['state']!='ADMITTED':raise RunError('GA_RUN_RECOVERY_REQUIRED')
        owner=str(uuid4())
        with self.authorized(context,row['policy']):
            with self.store.connection() as db:
                raw=self.store.load_checkpoint(db,row) if row['tip'] else None
                if resume and raw is None:raise RunError('GA_RUN_CHECKPOINT_MISSING')
                self._session(row,raw)
            owned,fence=self.store.claim(run_id,owner,recover=resume,expected_tip=row['tip'],expected_sequence=row['sequence'],before_commit=lambda:self.check(context,row['policy']))
        coordinator=self
        class DurableSession(Session):
            def _save_checkpoint(self,control,state,templates):
                reference=super()._save_checkpoint(control,state,templates)
                commit_context=coordinator.context(actor,row,'checkpoint_write')
                with coordinator.authorized(commit_context,row['policy']):
                    coordinator.store.checkpoint(run_id,owner,fence,self.checkpoint,self.checkpoint_fingerprint,self.sequence,self.parent_fingerprint,before_commit=lambda:coordinator.check(commit_context,row['policy']))
                return reference
        def boundary(kind,data):
            with self.authorized(context,row['policy']):
                with self.store.transaction() as db:
                    current=self.store.fenced(db,run_id,owner,fence);db.execute('UPDATE runs SET lease=? WHERE id=?',(self.clock()+120,run_id));self.check(context,row['policy'])
                if current['desired']=='STOP':session.control.request_stop()
                elif current['desired']=='PAUSE':session.control.request_pause()
            if observer:observer(kind,data)
        try:
            session=self._session(owned,raw,DurableSession)
            result=session.run(boundary)
            with self.authorized(context,row['policy']):
                with self.store.transaction() as db:
                    final=self.store.fenced(db,run_id,owner,fence)
                    raw_result=canonical(result) if result is not None else None
                    self.store.capacity(db,(len(raw_result) if raw_result is not None else 0)+len(canonical(session.receipt())))
                    db.execute('UPDATE runs SET state=?,executor=NULL,lease=0,result=?,result_hash=?,receipt=?,desired=NULL WHERE id=?',
                        ('STOPPED' if final['desired']=='STOP' else session.control.state,raw_result,hashlib.sha256(raw_result).hexdigest() if raw_result else None,canonical(session.receipt()).decode(),run_id))
                    self.check(context,row['policy'])
            return self.status(principal,run_id)
        except BaseException as primary:
            try:
                with self.store.transaction() as db:db.execute("UPDATE runs SET state='INTERRUPTED',executor=NULL,lease=0,error='GA_RUN_EXECUTION_INTERRUPTED' WHERE id=? AND executor=? AND fence=?",(run_id,owner,fence))
            except Exception:
                primary.add_note('GA_RUN_CLEANUP_UNVERIFIED: ownership lease must expire before recovery.')
            raise
