"""Managed process batches for verified fictional U5H continuations only.

No HTTP route, provider installation, deployment location or UI activation.
Parent owns every persistence operation; child has no database credentials.
"""
import base64
from dataclasses import asdict
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import sysconfig
import threading
import time
from uuid import uuid4
from services.ga_run_authority import RunError,canonical,digest
from services.ga_input_bundle import InputBundle,digest as byte_digest
from services.ga_bundle_optimizer import Session
from services.ga_worker_contract import VERSION,TERMINAL,Limits,Job,fictional_source
from services.ga_worker_store import WorkerStore

class Worker:
    def __init__(self,coordinator,*,initialize=False,max_workers=1):
        self.coordinator=coordinator;self.store=WorkerStore(coordinator,initialize=initialize,max_workers=max_workers)
        self.clock=coordinator.clock;self.lock=threading.RLock();self.threads={};self.cleanup={}

    def admit(self,principal,department,request,catalog,limits=Limits()):
        fictional_source();limits.validate()
        if limits.active_workers!=self.store.max_workers:raise RunError('GA_WORKER_ACTIVE_POLICY_MISMATCH')
        admitted=self.coordinator.admit(principal,department,request,catalog)
        self.store.register(principal,admitted['run_id'],limits)
        return self.status(principal,admitted['run_id'])

    def _row(self,principal,run,action='status'):
        self.store.guard();self.coordinator.inspect(principal,run,action)
        with self.store.base.connection() as db:return self.store.row(db,self.coordinator.actor(principal),run)

    def status(self,principal,run):
        row=self._row(principal,run)
        if row['best'] is not None:
            if byte_digest(row['best'])!=row['best_hash']:raise RunError('GA_WORKER_BEST_CORRUPT')
            best=json.loads(row['best'])
        else:best=None
        return dict(contract=VERSION,run_id=run,owner_id=row['actor'],department_id=row['department'],state=row['state'],
            reason=row['reason'],generation=max(0,row['generation']),initialized=row['generation']>=0,
            total_generations_completed=max(0,row['generation']),best_chromosome_id=row['best_hash'],
            best_fitness=best['best_fitness'] if best else None,fitness_breakdown=best['fitness_breakdown'] if best else None,
            improvement_history=best['history'] if best else [],checkpoint_version=VERSION,checkpoint_sequence=row['sequence'],
            fence=row['fence'],recovery_required=bool(row['executor'] and row['lease']<=self.clock()),
            publication=False,saved_best_promotion=False,eligible_for_current=False,source_scope='FICTIONAL_ISOLATED_ONLY')

    def result(self,principal,run):
        row=self._row(principal,run,'result')
        if row['best'] is None:raise RunError('GA_WORKER_BEST_UNAVAILABLE',404)
        if byte_digest(row['best'])!=row['best_hash']:raise RunError('GA_WORKER_BEST_CORRUPT')
        return json.loads(row['best'])

    def checkpoint(self,principal,run):
        row=self._row(principal,run,'checkpoint')
        with self.store.base.connection() as db:
            current=self.store.row(db,self.coordinator.actor(principal),run)
            return self.store.checkpoint(db,current)[0]

    def command(self,principal,run,command):
        if command not in {'pause','stop'}:raise RunError('GA_WORKER_COMMAND_INVALID')
        row=self._row(principal,run,command);actor=self.coordinator.actor(principal)
        context=self.coordinator.context(actor,row,command)
        with self.coordinator.authorized(context,row['policy']):
            with self.store.base.transaction() as db:
                row=self.store.row(db,actor,run)
                if row['state'] in TERMINAL:return self.status(principal,run)
                if command=='pause' and row['state']=='PAUSED':return self.status(principal,run)
                if command=='pause' and row['state']=='CREATED':raise RunError('GA_WORKER_TRANSITION_INVALID')
                if row['desired']==('STOP' if command=='stop' else 'PAUSE'):return self.status(principal,run)
                if command=='stop' and row['state'] in {'CREATED','PAUSED'}:
                    self.store.event(db,row,'STOPPED','USER_STOP')
                    db.execute("UPDATE runs SET state='WORKER_STOPPED',executor=NULL,lease=0,fence=fence+1 WHERE id=?",(run,))
                elif row['desired']!='STOP':
                    desired='STOP' if command=='stop' else 'PAUSE';state='STOPPING' if desired=='STOP' else 'PAUSING'
                    db.execute('UPDATE workers SET desired=? WHERE run=?',(desired,run));self.store.event(db,row,state,'USER_'+desired)
                self.store.capacity(db,row)
                self.coordinator.check(context,row['policy'])
        return self.status(principal,run)

    def start(self,principal,run):return self._start(principal,run,False,False)
    def resume(self,principal,run,*,recover=False):return self._start(principal,run,True,recover)

    def _start(self,principal,run,resume,recover):
        fictional_source()
        with self.lock:
            row=self._row(principal,run,'resume' if resume else 'execute')
            if row['state'] in {'RUNNING','RESUMING','PAUSING','STOPPING'} and row['lease']>self.clock():return self.status(principal,run)
            raw=None
            if row['tip']:
                with self.store.base.connection() as db:doc,raw=self.store.checkpoint(db,row)
                self._validate(row,doc,raw)
            owner=str(uuid4());claimed,fence=self.store.claim(principal,run,owner,resume=resume,recover=recover,expected_tip=row['tip'])
            thread=threading.Thread(target=self._run,args=(principal,run,owner,fence),daemon=False,name='U5K-owned-supervisor')
            self.threads[run]=thread
            try:thread.start()
            except BaseException:self._fail(principal,run,owner,fence,'GA_WORKER_SUPERVISOR_START_FAILED');raise
        return self.status(principal,run)

    def wait(self,principal,run,timeout=5):
        self._row(principal,run)
        thread=self.threads.get(run)
        if thread:thread.join(timeout)
        return self.status(principal,run)

    def close(self,principal,timeout=5):
        """Request cooperative stop, then report actual join state; no fake ACK."""
        deadline=time.monotonic()+timeout
        for run,thread in list(self.threads.items()):
            if thread.is_alive():
                try:self.command(principal,run,'stop')
                except RunError:pass
        for thread in list(self.threads.values()):thread.join(max(0,deadline-time.monotonic()))
        return {'quiescent':not any(t.is_alive() for t in self.threads.values())}

    def _validate(self,row,doc,raw):
        bundle=InputBundle.from_bytes(bytes(row['bundle']),row['id'],row['bundle_hash'])
        return Session.restore(bundle,raw,run_id=row['id'],expected_fingerprint=doc['inner_hash'],
            expected_sequence=doc['sequence'],expected_parent=doc['inner_parent'])

    def _heartbeat(self,principal,run,owner,fence):
        actor=self.coordinator.actor(principal)
        initial=self.coordinator.inspect(principal,run,'execute');context=self.coordinator.context(actor,initial,'execute')
        with self.coordinator.authorized(context,initial['policy']):
            with self.store.base.transaction() as db:
                row=self.store.fenced(db,actor,run,owner,fence)
                limits=Limits(**json.loads(row['limits']))
                if self.clock()<row['created'] or self.clock()>=row['deadline'] or row['spent']>=limits.wall_seconds:raise RunError('GA_WORKER_TIME_BUDGET')
                db.execute('UPDATE runs SET lease=? WHERE id=?',(self.clock()+10,run))
                if row['state']=='RESUMING':self.store.event(db,row,'RUNNING','RESUME_VALIDATED')
                self.store.capacity(db,row)
                self.coordinator.check(context,row['policy'])
                return row

    def _exchange(self,request,remaining,max_message,heartbeat):
        backend=fictional_source();allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE'}
        env={k:v for k,v in os.environ.items() if k.upper() in allowed};env['PYTHONDONTWRITEBYTECODE']='1'
        # Windows venv python.exe is a redirector, which can spawn a second
        # process. Invoke the base interpreter directly so the one-process job
        # remains strict, with only the existing venv libraries/source supplied.
        bootstrap='import sys,runpy;sys.path[:0]='+repr([str(backend),sysconfig.get_paths()['purelib']])+";runpy.run_module('services.ga_worker_child',run_name='__main__')"
        process=subprocess.Popen([getattr(sys,'_base_executable',sys.executable),'-I','-B','-c',bootstrap],cwd=backend,env=env,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        job=None;threads=[];events=queue.Queue(maxsize=2);started=time.monotonic()
        try:
            job=Job(process,store_id=self.store.base.store_id,run_id=request['run'],max_workers=self.store.max_workers)
            raw=canonical(request)+b'\n'
            if len(raw)>max_message:raise RunError('GA_WORKER_REQUEST_SIZE_LIMIT')
            def write():
                try:process.stdin.write(raw);process.stdin.flush();process.stdin.close()
                except (OSError,ValueError):pass
            def read():
                try:events.put(process.stdout.readline(max_message+1),timeout=1)
                except (OSError,ValueError,queue.Full):pass
            threads=[threading.Thread(target=write,daemon=False),threading.Thread(target=read,daemon=False)]
            for thread in threads:thread.start()
            output=None
            while True:
                if time.monotonic()-started>=remaining:raise RunError('GA_WORKER_TIME_BUDGET')
                heartbeat()
                if output is None:
                    try:output=events.get(timeout=.1)
                    except queue.Empty:continue
                    if not output or len(output)>max_message or not output.endswith(b'\n'):raise RunError('GA_WORKER_RESPONSE_SIZE_OR_FORMAT')
                if process.poll() is not None:break
                time.sleep(.02)
            if process.returncode!=0:raise RunError('GA_WORKER_CHILD_FAILED')
            value=json.loads(output)
            if canonical(value)+b'\n'!=output:raise RunError('GA_WORKER_RESPONSE_INVALID')
            return value,time.monotonic()-started
        finally:
            if job:job.close()
            try:
                if process.poll() is None:process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            except (OSError,subprocess.TimeoutExpired):raise RunError('GA_WORKER_PROCESS_CLEANUP_UNVERIFIED') from None
            for thread in threads:thread.join(5)
            for stream in [process.stdin,process.stdout]:
                try:stream.close()
                except OSError:pass
            if any(t.is_alive() for t in threads):raise RunError('GA_WORKER_IO_CLEANUP_UNVERIFIED')

    def _run(self,principal,run,owner,fence):
        try:
            while True:
                self.store.guard();row=self._heartbeat(principal,run,owner,fence);limits=Limits(**json.loads(row['limits']))
                with self.store.base.connection() as db:
                    doc,raw=self.store.checkpoint(db,row) if row['tip'] else (None,None)
                total=json.loads(row['bundle'])['configuration']['generations']
                target=0 if row['generation']<0 else min(total,row['generation']+limits.batch_generations)
                request=dict(contract=VERSION,implementation=self.store.version,run=run,bundle=base64.b64encode(row['bundle']).decode(),bundle_hash=row['bundle_hash'],
                    rng=json.loads(row['initial_rng']),checkpoint=base64.b64encode(raw).decode() if raw else None,
                    inner_hash=row['inner_tip'],sequence=row['sequence'],inner_parent=doc['inner_parent'] if doc else None,target=target)
                remaining=min(row['deadline']-self.clock(),limits.wall_seconds-row['spent'])
                batch_started=time.monotonic()
                response,_spent=self._exchange(request,remaining,min(64*1024*1024,limits.run_bytes),lambda:self._heartbeat(principal,run,owner,fence))
                if response.get('contract')!=VERSION or response.get('implementation')!=self.store.version or response.get('run')!=run:raise RunError('GA_WORKER_RESPONSE_BINDING')
                inner=base64.b64decode(response['inner'],validate=True)
                if byte_digest(inner)!=response['inner_hash'] or response['sequence']!=row['sequence']+1 or response['inner_parent']!=row['inner_tip']:raise RunError('GA_WORKER_RESPONSE_BINDING')
                check=self._validate(row,dict(inner_hash=response['inner_hash'],sequence=response['sequence'],inner_parent=response['inner_parent']),inner)
                projection=response['projection'];state=check.resume_state
                if (state['generation_completed']!=target or projection['generations_completed']!=target
                        or projection['best_fitness']!=state['best_ever_fitness'] or projection['history']!=state['history']
                        or projection['saved_best_updated'] is not False):raise RunError('GA_WORKER_PROJECTION_INVALID')
                # Reuse unchanged original finalization with stop before the next
                # random draw. This validates reports as well as checkpoint state.
                check.control.request_stop();expected=check.run()
                if any(projection[k]!=expected[k] for k in ['schedule','best_fitness','history','fitness_breakdown','faculty_analysis']):
                    raise RunError('GA_WORKER_PROJECTION_INVALID')
                if check.runtime.random.getstate()!=state['random_state']:raise RunError('GA_WORKER_RNG_CHANGED')
                spent=time.monotonic()-batch_started
                outcome=self.store.save(principal,run,owner,fence,inner,projection,spent,row['inner_tip'])
                if outcome!='RUNNING':break
        except BaseException as error:
            code=error.code if isinstance(error,RunError) else 'GA_WORKER_EXECUTION_FAILED'
            if code in {'GA_WORKER_PROCESS_CLEANUP_UNVERIFIED','GA_WORKER_IO_CLEANUP_UNVERIFIED'}:self.cleanup[run]=False
            self._fail(principal,run,owner,fence,code)
        finally:self.cleanup.setdefault(run,True)

    def _fail(self,principal,run,owner,fence,code):
        try:
            with self.store.base.transaction() as db:
                row=self.store.row(db,self.coordinator.actor(principal),run)
                if row['executor']!=owner or row['fence']!=fence or row['lease']<=self.clock():return
                self.store.event(db,row,'FAILED',code)
                self.store.capacity(db,row,reserve=0)
                db.execute("UPDATE runs SET state='WORKER_FAILED',executor=NULL,lease=0 WHERE id=? AND executor=? AND fence=?",(run,owner,fence))
        except Exception:self.cleanup[run]=False
