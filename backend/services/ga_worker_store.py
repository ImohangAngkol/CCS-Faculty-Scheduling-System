"""Versioned worker tables in a NEW owned U5I fixture database only.

No legacy checkpoint rows or schema versions are rewritten. Atomic worker tip,
best projection, lifecycle/event and I ownership fencing share one transaction.
"""
from dataclasses import asdict
import base64
import json
import time
from services.ga_run_authority import RunError,canonical,digest
from services.ga_input_bundle import digest as byte_digest
from services.ga_worker_contract import VERSION,TERMINAL,Limits,implementation,fictional_source
from services.ga_storage_qualification import inspect as storage_inspect

SCHEMA='''
CREATE TABLE worker_meta(version TEXT NOT NULL, implementation TEXT NOT NULL, max_workers INTEGER NOT NULL);
CREATE TABLE workers(run TEXT PRIMARY KEY REFERENCES runs(id), state TEXT NOT NULL, desired TEXT,
 policy TEXT NOT NULL, policy_hash TEXT NOT NULL, generation INTEGER NOT NULL DEFAULT -1,
 sequence INTEGER NOT NULL DEFAULT 0, tip TEXT, inner_tip TEXT, parent TEXT, best BLOB, best_hash TEXT,
 reason TEXT, deadline REAL NOT NULL, spent REAL NOT NULL DEFAULT 0);
CREATE TABLE worker_checkpoints(run TEXT NOT NULL REFERENCES workers(run), sequence INTEGER NOT NULL,
 hash TEXT NOT NULL UNIQUE, parent TEXT, raw BLOB NOT NULL, PRIMARY KEY(run,sequence));
CREATE TABLE worker_events(id INTEGER PRIMARY KEY,run TEXT NOT NULL REFERENCES workers(run),
 state TEXT NOT NULL,reason TEXT,fence INTEGER NOT NULL,tip TEXT,at REAL NOT NULL);
'''

class WorkerStore:
    def __init__(self,coordinator,*,initialize=False,max_workers=1):
        fictional_source()
        from services.ga_qualification_authority import ScopedAuthority
        from services.ga_qualified_capture import CaptureAdapter
        if type(coordinator.authority) is not ScopedAuthority or type(coordinator.source) is not CaptureAdapter:
            raise RunError('GA_WORKER_QUALIFIED_PROVIDERS_REQUIRED',503)
        self.coordinator=coordinator;self.base=coordinator.store;self.clock=coordinator.clock
        self.version=implementation();self.max_workers=max_workers
        storage_inspect(self.base)
        if initialize:
            if type(max_workers) is not int or not 1<=max_workers<=2:raise RunError('GA_WORKER_LIMIT_INVALID')
            with self.base.connection() as db:
                if db.execute('SELECT COUNT(*) FROM runs').fetchone()[0] or db.execute("SELECT name FROM sqlite_master WHERE name LIKE 'worker_%'").fetchone():
                    raise RunError('GA_WORKER_NEW_STORE_REQUIRED')
                db.executescript('BEGIN IMMEDIATE;'+SCHEMA)
                db.execute('INSERT INTO worker_meta VALUES(?,?,?)',(VERSION,self.version,max_workers));db.commit()
        self.guard()

    def guard(self):
        self.base.guard()
        with self.base.connection() as db:
            rows=db.execute('SELECT * FROM worker_meta').fetchall()
            if len(rows)!=1 or tuple(rows[0])!=(VERSION,self.version,self.max_workers) or implementation()!=self.version:
                raise RunError('GA_WORKER_VERSION_MISMATCH')

    def event(self,db,row,state,reason=None):
        # Logical payload quota uses bounded metadata slots, not an assertion
        # about SQLite file/page/journal size. Reject oversized event values.
        if len(canonical(dict(run=row['id'],state=state,reason=reason,fence=row['fence'],tip=row['tip'],at=self.clock())))>1024:
            raise RunError('GA_WORKER_EVENT_SIZE_LIMIT')
        db.execute('UPDATE workers SET state=?,reason=? WHERE run=?',(state,reason,row['id']))
        db.execute('INSERT INTO worker_events(run,state,reason,fence,tip,at) VALUES(?,?,?,?,?,?)',
            (row['id'],state,reason,row['fence'],row['tip'],self.clock()))

    def row(self,db,actor,run):
        base=self.coordinator.owned(db,actor,run)
        w=db.execute('SELECT * FROM workers WHERE run=?',(run,)).fetchone()
        if w is None:raise RunError('GA_WORKER_NOT_FOUND',404)
        worker=dict(w);worker['limits']=worker.pop('policy')
        value={**base,**worker,'id':run}
        if not base['state'].startswith('WORKER_'):raise RunError('GA_WORKER_BASE_OWNERSHIP_CHANGED')
        if digest(json.loads(value['limits']))!=value['policy_hash']:raise RunError('GA_WORKER_POLICY_CORRUPT')
        Limits(**json.loads(value['limits'])).validate()
        return value

    def size(self,db,run=None):
        where=' WHERE id=?' if run else '';args=(run,) if run else ()
        used=db.execute('SELECT COALESCE(SUM(length(bundle)+length(initial_rng)+COALESCE(length(result),0)),0) FROM runs'+where,args).fetchone()[0]
        where=' WHERE run=?' if run else ''
        used+=db.execute('SELECT COALESCE(SUM(length(raw)),0) FROM worker_checkpoints'+where,args).fetchone()[0]
        used+=db.execute('SELECT COALESCE(SUM(COALESCE(length(best),0)+length(policy)),0) FROM workers'+where,args).fetchone()[0]
        used+=1024*db.execute('SELECT COUNT(*) FROM worker_events'+where,args).fetchone()[0]
        used+=4096*db.execute('SELECT COUNT(*) FROM workers'+where,args).fetchone()[0]
        return used

    def capacity(self,db,row,*,reserve=1024):
        # Normal writes reserve one failure-event slot. If even failure
        # recording cannot fit, its transaction rolls back; no false ACK.
        limit=Limits(**json.loads(row['limits'])).run_bytes
        if self.size(db,row['id'])+reserve>limit or self.size(db)+reserve>self.base.max_bytes:
            raise RunError('GA_WORKER_STORED_BYTES_LIMIT')

    def register(self,principal,run,limits):
        limits.validate();actor=self.coordinator.actor(principal);row=self.coordinator.inspect(principal,run,'admit')
        context=self.coordinator.context(actor,row,'admit')
        with self.coordinator.authorized(context,row['policy']):
            with self.base.transaction() as db:
                old=db.execute('SELECT * FROM workers WHERE run=?',(run,)).fetchone()
                if old:
                    if old['policy_hash']!=digest(asdict(limits)):raise RunError('GA_WORKER_IDEMPOTENCY_CONFLICT')
                    return
                session=self.coordinator._session(row)
                if (session.working['configuration']['generations']>limits.total_generations
                        or session.working['configuration']['population_size']>8 or limits.active_workers!=self.max_workers):
                    raise RunError('GA_WORKER_FIXTURE_LIMIT_EXCEEDED')
                if self.size(db)>self.base.max_bytes or self.size(db,run)>limits.run_bytes:raise RunError('GA_WORKER_STORED_BYTES_LIMIT')
                db.execute('INSERT INTO workers(run,state,policy,policy_hash,deadline) VALUES(?,?,?,?,?)',
                    (run,'CREATED',canonical(asdict(limits)).decode(),digest(asdict(limits)),self.clock()+limits.wall_seconds))
                db.execute("UPDATE runs SET state='WORKER_CREATED' WHERE id=?",(run,));self.event(db,{**row,'tip':None},'CREATED')
                if self.size(db)>self.base.max_bytes or self.size(db,run)>limits.run_bytes:raise RunError('GA_WORKER_STORED_BYTES_LIMIT')
                self.capacity(db,self.row(db,actor,run))
                self.coordinator.check(context,row['policy'])

    def claim(self,principal,run,owner,*,resume=False,recover=False,expected_tip=None):
        actor=self.coordinator.actor(principal);action='resume' if resume else 'execute'
        initial=self.coordinator.inspect(principal,run,action);context=self.coordinator.context(actor,initial,action)
        with self.coordinator.authorized(context,initial['policy']):
            with self.base.transaction() as db:
                row=self.row(db,actor,run);limits=Limits(**json.loads(row['limits']))
                if db.execute("SELECT run FROM workers WHERE reason IN ('GA_WORKER_PROCESS_CLEANUP_UNVERIFIED','GA_WORKER_IO_CLEANUP_UNVERIFIED') LIMIT 1").fetchone():
                    raise RunError('GA_WORKER_CLEANUP_REVIEW_REQUIRED')
                if row['tip']!=expected_tip:raise RunError('GA_WORKER_TIP_CHANGED')
                if row['state'] in TERMINAL:raise RunError('GA_WORKER_TERMINAL')
                if row['executor'] and row['lease']>self.clock():raise RunError('GA_WORKER_EXECUTION_ACTIVE')
                if resume:
                    if row['state']=='CREATED':raise RunError('GA_WORKER_TRANSITION_INVALID')
                    if row['state']!='PAUSED' and not recover:raise RunError('GA_WORKER_RECOVERY_DECISION_REQUIRED')
                    if not row['tip']:raise RunError('GA_WORKER_CHECKPOINT_MISSING')
                elif row['state']!='CREATED':raise RunError('GA_WORKER_TRANSITION_INVALID')
                if self.clock()<row['created'] or self.clock()>=row['deadline'] or row['spent']>=limits.wall_seconds:raise RunError('GA_WORKER_TIME_BUDGET')
                active=db.execute('SELECT COUNT(*) FROM workers w JOIN runs r ON r.id=w.run WHERE r.executor IS NOT NULL AND r.lease>?',(self.clock(),)).fetchone()[0]
                if active>=self.max_workers:raise RunError('GA_WORKER_ACTIVE_LIMIT')
                fence=row['fence']+1;db.execute("UPDATE runs SET executor=?,fence=?,lease=?,state='WORKER_RUNNING' WHERE id=?",(owner,fence,self.clock()+10,run))
                self.event(db,{**row,'fence':fence},'RESUMING' if resume else 'RUNNING','AUTHORIZED_RECOVERY' if recover else None)
                self.capacity(db,row)
                self.coordinator.check(context,initial['policy'])
                return self.row(db,actor,run),fence

    def fenced(self,db,actor,run,owner,fence):
        self.base.fenced(db,run,owner,fence)
        return self.row(db,actor,run)

    def checkpoint(self,db,row):
        if not row['tip']:raise RunError('GA_WORKER_CHECKPOINT_MISSING')
        chain=db.execute('SELECT * FROM worker_checkpoints WHERE run=? ORDER BY sequence',(row['id'],)).fetchall();parent=None;inner=None;last_fence=0
        for seq,item in enumerate(chain,1):
            if item['sequence']!=seq or item['parent']!=parent or byte_digest(item['raw'])!=item['hash']:raise RunError('GA_WORKER_CHECKPOINT_CORRUPT')
            doc=json.loads(item['raw']);payload=base64.b64decode(doc['payload'],validate=True)
            expected={'contract':VERSION,'run':row['id'],'owner':row['actor'],'department':row['department'],
                'bundle':row['bundle_hash'],'configuration':row['config_hash'],'optimizer':row['optimizer'],
                'implementation':self.version,'policy':row['policy_hash'],'sequence':seq,'parent':parent,'inner_parent':inner}
            if any(doc.get(k)!=v for k,v in expected.items()) or byte_digest(payload)!=doc['inner_hash'] or canonical(doc)!=item['raw']:
                raise RunError('GA_WORKER_CHECKPOINT_BINDING')
            if set(doc)!=set(expected)|{'inner_hash','fence','worker_state','generation','payload'}:raise RunError('GA_WORKER_CHECKPOINT_BINDING')
            if (type(doc['fence']) is not int or not max(1,last_fence)<=doc['fence']<=row['fence']
                    or doc['worker_state'] not in {'RUNNING','PAUSED','STOPPED','COMPLETED'}):raise RunError('GA_WORKER_CHECKPOINT_BINDING')
            last_fence=doc['fence']
            parent=item['hash'];inner=doc['inner_hash']
        if len(chain)!=row['sequence'] or parent!=row['tip'] or inner!=row['inner_tip'] or doc['generation']!=row['generation']:raise RunError('GA_WORKER_CHECKPOINT_LINEAGE')
        return doc,payload

    def save(self,principal,run,owner,fence,inner,projection,spent,inner_parent):
        actor=self.coordinator.actor(principal);base=self.coordinator.inspect(principal,run,'checkpoint_write');context=self.coordinator.context(actor,base,'checkpoint_write')
        with self.coordinator.authorized(context,base['policy']):
            with self.base.transaction() as db:
                row=self.fenced(db,actor,run,owner,fence);limits=Limits(**json.loads(row['limits']))
                if self.clock()>=row['deadline'] or row['spent']+spent>limits.wall_seconds:raise RunError('GA_WORKER_TIME_BUDGET')
                if inner_parent!=row['inner_tip']:raise RunError('GA_WORKER_CHECKPOINT_LINEAGE')
                seq=row['sequence']+1
                if seq>limits.retained_checkpoints:raise RunError('GA_WORKER_CHECKPOINT_RETENTION_LIMIT')
                generation=projection['generations_completed'];total=json.loads(base['bundle'])['configuration']['generations']
                state='STOPPED' if row['desired']=='STOP' else 'COMPLETED' if generation==total else 'PAUSED' if row['desired']=='PAUSE' else 'RUNNING'
                doc=dict(contract=VERSION,run=run,owner=actor,department=row['department'],bundle=row['bundle_hash'],
                    configuration=row['config_hash'],optimizer=row['optimizer'],implementation=self.version,policy=row['policy_hash'],
                    sequence=seq,parent=row['tip'],inner_parent=inner_parent,inner_hash=byte_digest(inner),fence=fence,
                    worker_state=state,generation=generation,payload=base64.b64encode(inner).decode())
                raw=canonical(doc);best=canonical(projection)
                if len(raw)>limits.checkpoint_bytes:raise RunError('GA_WORKER_CHECKPOINT_SIZE_LIMIT')
                extra=len(raw)+len(best)
                if self.size(db,run)+extra>limits.run_bytes or self.size(db)+extra>self.base.max_bytes:raise RunError('GA_WORKER_STORED_BYTES_LIMIT')
                if row['best'] is not None and projection['best_fitness']>json.loads(row['best'])['best_fitness']:raise RunError('GA_WORKER_BEST_REGRESSION')
                if generation<row['generation']:raise RunError('GA_WORKER_GENERATION_REGRESSION')
                fp=byte_digest(raw)
                db.execute('INSERT INTO worker_checkpoints VALUES(?,?,?,?,?)',(run,seq,fp,row['tip'],raw))
                db.execute('UPDATE workers SET sequence=?,parent=?,tip=?,inner_tip=?,generation=?,best=?,best_hash=?,spent=spent+? WHERE run=?',
                    (seq,row['tip'],fp,doc['inner_hash'],generation,best,byte_digest(best),spent,run))
                reason='USER_STOP' if state=='STOPPED' else 'GENERATION_CEILING' if state=='COMPLETED' else 'USER_PAUSE' if state=='PAUSED' else 'BATCH_CHECKPOINT'
                self.event(db,{**row,'tip':fp},state,reason)
                self.capacity(db,row)
                if state!='RUNNING':db.execute('UPDATE runs SET executor=NULL,lease=0,state=? WHERE id=?',('WORKER_'+state,run))
                else:db.execute('UPDATE runs SET lease=? WHERE id=?',(self.clock()+10,run))
                db.execute('UPDATE workers SET desired=NULL WHERE run=?',(run,))
                self.coordinator.check(context,base['policy'])
                # The transaction intentionally releases ownership for terminal
                # states. Check the admitted lease, not that cleared lease; the
                # write lock prevents another fence from entering this commit.
                if row['lease']<=self.clock():raise RunError('GA_RUN_OWNERSHIP_LOST')
                if self.clock()>=row['deadline']:raise RunError('GA_WORKER_TIME_BUDGET')
                return state
