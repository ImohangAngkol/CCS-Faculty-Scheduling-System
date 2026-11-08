"""U5L fixture-only supervisor; inherits unchanged K/H GA and persistence logic."""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import queue
import sys
import sysconfig
import threading
import time
from uuid import uuid4
from services.ga_bounded_worker import Worker as BoundedWorker
from services.ga_worker_contract import Limits,fictional_source
from services.ga_run_authority import RunError,canonical
from services.ga_supervised_storage import LimitedStore,StorageLimits
from services.ga_windows_supervisor import Process,Resources,alive,VERSION

def arguments(backend):
    bootstrap='import sys,runpy;sys.path[:0]='+repr([str(backend),sysconfig.get_paths()['purelib']])+";runpy.run_module('services.ga_worker_child',run_name='__main__')"
    return [getattr(sys,'_base_executable',sys.executable),'-I','-B','-c',bootstrap]

class Worker(BoundedWorker):
    def __init__(self,coordinator,*,initialize=False,max_workers=1,resources=Resources(),storage=StorageLimits()):
        resources.validate();storage.validate();super().__init__(coordinator,initialize=initialize,max_workers=max_workers)
        self.resources=resources;self.storage=LimitedStore(coordinator.store,resources,storage,initialize=initialize)
        # All coordinator and worker connections now use this explicit,
        # version-bound instance adapter; no module/class globals are replaced.
        coordinator.store=self.storage;self.store.base=self.storage;self.storage.worker_store=self.store;self.processes={}

    def admit(self,principal,department,request,catalog,limits=Limits()):
        status=super().admit(principal,department,request,catalog,limits);self.storage.bind(status['run_id']);return self.status(principal,status['run_id'])

    def status(self,principal,run):
        value=super().status(principal,run)
        with self.storage.connection() as db:
            registered=db.execute('SELECT policy FROM l_runs WHERE run=?',(run,)).fetchone()
            count=db.execute('SELECT COUNT(*) FROM l_processes WHERE run=?',(run,)).fetchone()[0]
        value.update(supervision_contract=VERSION,physical_policy=self.storage.policy,
            supervision_registered=bool(registered and registered[0]==self.storage.policy),
            resources=asdict(self.resources),observed_process_batches=count,
            physical_enforcement='CREATION_TIME_JOB_BINDING_RECORDED' if count else 'NOT_STARTED',deployment_ready=False)
        return value

    def _start(self,principal,run,resume,recover):
        row=self._row(principal,run,'resume' if resume else 'execute');self.storage.pin(row)
        with self.storage.connection() as db:
            attempts=db.execute('SELECT * FROM l_processes WHERE run=?',(run,)).fetchall()
        for p in attempts:
            if p['status']=='CLEANUP_UNVERIFIED':raise RunError('GA_SUPERVISION_CLEANUP_REVIEW_REQUIRED')
            if p['status']=='ACTIVE' and alive(p['pid'],p['created']):
                if row['lease']>self.clock():return self.status(principal,run)
                raise RunError('GA_SUPERVISION_OLD_PROCESS_ACTIVE')
        return super()._start(principal,run,resume,recover)

    def checkpoint(self,principal,run):
        self.storage.pin(self._row(principal,run,'checkpoint'))
        return super().checkpoint(principal,run)

    def result(self,principal,run):
        self.storage.pin(self._row(principal,run,'result'))
        return super().result(principal,run)

    def recover(self,principal,run,*,expected_tip,expected_fence):
        row=self._row(principal,run,'resume');self.storage.pin(row)
        if (row['tip'],row['fence'])!=(expected_tip,expected_fence):raise RunError('GA_SUPERVISION_RECOVERY_STALE')
        if not row['tip']:raise RunError('GA_WORKER_CHECKPOINT_MISSING')
        if row['state'] in {'COMPLETED','STOPPED'}:raise RunError('GA_WORKER_TERMINAL')
        if row['executor'] and row['lease']>self.clock():raise RunError('GA_WORKER_EXECUTION_ACTIVE')
        with self.storage.connection() as db:processes=db.execute('SELECT * FROM l_processes WHERE run=?',(run,)).fetchall()
        if any(alive(p['pid'],p['created']) for p in processes):raise RunError('GA_SUPERVISION_OLD_PROCESS_ACTIVE')
        with self.storage.connection() as db:doc,raw=self.store.checkpoint(db,row)
        self._validate(row,doc,raw)
        actor=self.coordinator.actor(principal);context=self.coordinator.context(actor,row,'resume')
        with self.coordinator.authorized(context,row['policy']):
            with self.storage.transaction() as db:
                current=self.store.row(db,actor,run)
                if (current['tip'],current['fence'],current['executor'])!=(row['tip'],row['fence'],row['executor']):raise RunError('GA_SUPERVISION_RECOVERY_STALE')
                db.execute("UPDATE runs SET state='WORKER_PAUSED',executor=NULL,lease=0,fence=fence+1 WHERE id=?",(run,))
                db.execute('UPDATE workers SET desired=NULL WHERE run=?',(run,));self.store.event(db,current,'PAUSED','AUTHORIZED_PROCESS_RECOVERY')
                db.execute("UPDATE l_processes SET status='RECOVERY_DEATH_VERIFIED' WHERE run=? AND status!='EXIT_VERIFIED'",(run,))
                self.store.capacity(db,current);self.coordinator.check(context,row['policy'])
        return self.resume(principal,run,recover=True)

    def _exchange(self,request,remaining,max_message,heartbeat):
        backend=fictional_source();row=heartbeat();self.storage.pin(row);raw=canonical(request)+b'\n'
        if len(raw)>max_message:raise RunError('GA_WORKER_REQUEST_SIZE_LIMIT')
        allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE'}
        env={k:v for k,v in os.environ.items() if k.upper() in allowed};env['PYTHONDONTWRITEBYTECODE']='1'
        process=None;threads=[];events=queue.Queue(2);attempt=str(uuid4());started=time.monotonic();registered=False
        try:
            process=Process(arguments(backend),cwd=backend,env=env,store_id=self.storage.store_id,run_id=request['run'],
                max_workers=self.store.max_workers,resources=self.resources)
            self.processes[request['run']]=process
            with self.storage.transaction() as db:
                self.store.fenced(db,row['actor'],row['id'],row['executor'],row['fence'])
                if db.execute('SELECT COUNT(*) FROM l_processes WHERE run=?',(row['id'],)).fetchone()[0]>=64:raise RunError('GA_SUPERVISION_ATTEMPT_LIMIT')
                db.execute('INSERT INTO l_processes VALUES(?,?,?,?,?,?,?,?,?)',
                    (attempt,row['id'],row['fence'],row['executor'],process.pid,process.identity,'ACTIVE',self.clock(),None));registered=True
            def write():
                try:
                    position=0
                    while position<len(raw):
                        n=process.stdin.write(raw[position:])
                        if not n:break
                        position+=n
                    process.stdin.close()
                except (OSError,ValueError):pass
            def read():
                try:events.put(process.stdout.readline(max_message+1),timeout=1)
                except (OSError,ValueError,queue.Full):pass
            threads=[threading.Thread(target=write,daemon=False),threading.Thread(target=read,daemon=False)]
            for t in threads:t.start()
            output=None
            while True:
                if time.monotonic()-started>=remaining:raise RunError('GA_WORKER_TIME_BUDGET')
                current=heartbeat()
                with self.storage.transaction() as db:
                    self.store.fenced(db,row['actor'],row['id'],row['executor'],row['fence'])
                    db.execute('UPDATE l_processes SET heartbeat=? WHERE attempt=?',(self.clock(),attempt))
                code=process.poll()
                if code is not None and code!=0:raise RunError('GA_SUPERVISION_CHILD_CRASH')
                if output is None:
                    try:output=events.get(timeout=.1)
                    except queue.Empty:continue
                    if not output or len(output)>max_message or not output.endswith(b'\n'):raise RunError('GA_WORKER_RESPONSE_SIZE_OR_FORMAT')
                if code is not None:break
            value=json.loads(output)
            if canonical(value)+b'\n'!=output:raise RunError('GA_WORKER_RESPONSE_INVALID')
            return value,time.monotonic()-started
        finally:
            if process:
                clean=False;observation=None
                try:
                    # Must reap the physical process before K can persist a
                    # PAUSED/STOPPED/COMPLETED response.
                    observation=process.close()
                    if len(canonical(observation))>2048:raise RunError('GA_SUPERVISION_OBSERVATION_SIZE_LIMIT')
                    for t in threads:t.join(self.resources.grace_seconds)
                    clean=not any(t.is_alive() for t in threads)
                finally:
                    if registered:
                        with self.storage.transaction() as db:
                            db.execute('UPDATE l_processes SET status=?,observation=? WHERE attempt=?',
                                ('EXIT_VERIFIED' if clean else 'CLEANUP_UNVERIFIED',canonical(observation).decode() if observation else None,attempt))
                if not clean:raise RunError('GA_WORKER_PROCESS_CLEANUP_UNVERIFIED')

    def shutdown(self,principal,grace=5):
        if type(grace) is not int or not 1<=grace<=5:raise RunError('GA_SUPERVISION_GRACE_INVALID')
        for run in list(self.threads):self._row(principal,run,'stop')
        result=self.close(principal,timeout=grace)
        if not result['quiescent']:
            for p in list(self.processes.values()):
                if p.handle:p.terminate()
            result=self.close(principal,timeout=grace)
        if not result['quiescent']:raise RunError('GA_SUPERVISION_SHUTDOWN_UNVERIFIED')
        return result

    def retention_plan(self,principal,run,*,expected_tip,expected_fence):
        row=self._row(principal,run,'checkpoint');self.storage.pin(row)
        if (row['tip'],row['fence'])!=(expected_tip,expected_fence):raise RunError('GA_SUPERVISION_RETENTION_STALE')
        if row['executor'] or row['state'] not in {'COMPLETED','STOPPED','FAILED'}:raise RunError('GA_SUPERVISION_RETENTION_ACTIVE')
        return dict(cleanup_enabled=False,reason='INDEPENDENT_RETENTION_AUTHORITY_AND_RESTORE_POLICY_REQUIRED',tip=row['tip'],fence=row['fence'])
