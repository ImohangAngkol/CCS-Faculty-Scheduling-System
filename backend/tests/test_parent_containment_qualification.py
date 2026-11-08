"""U5N actual outer parent + nested L worker Jobs, no deployed daemon."""
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import queue
import sys
import sysconfig
import threading
import time
from uuid import uuid4
import pytest
from services.ga_windows_supervisor import Resources,Process,alive,kernel
from services.ga_run_authority import RunError
from services.ga_supervised_worker import Worker
from services.ga_owned_store import Store
from services.ga_trusted_runs import Coordinator
from tests.test_windows_supervision import launch,environment
from tests.test_supervised_worker import fixture,paused
from tests.test_bounded_worker import until
from tests.bounded_worker_support import dependencies
from tests.trusted_run_support import PRINCIPAL,ACTOR

def line(p,timeout=60):
    q=queue.Queue(1)
    def read():q.put(p.stdout.readline())
    t=threading.Thread(target=read,daemon=True);t.start()
    try:
        value=q.get(timeout=timeout)
        if value.startswith(b'U5N_DIAGNOSTIC:'):pytest.fail(value.decode('utf-8',errors='replace').strip())
        return value
    except queue.Empty:raise AssertionError('Owned parent readiness deadline exceeded') from None

def record(name,values):
    if os.environ.get('U5H_PROTOCOL_EVIDENCE'):
        with (Path(os.environ['U5H_PROTOCOL_EVIDENCE'])/('U5N-'+name+'.json')).open('x',encoding='utf-8') as f:json.dump(values,f,indent=2)

def parent(code,resources=Resources(),*,redirector=False):
    # The venv redirector consumes a second Job process slot on Windows.
    # Launch the real interpreter with explicit, already installed venv deps
    # and the owned snapshot, preserving the same two-process containment cap.
    from services.ga_worker_contract import fictional_source
    backend=fictional_source()
    prefix='import sys;sys.path[:0]='+repr([str(backend),sysconfig.get_path('purelib')])+'\n'
    wrapped=prefix+'try:\n exec('+repr(code)+')\nexcept BaseException as error:\n print("U5N_DIAGNOSTIC:"+type(error).__name__+":"+str(error),file=sys.__stdout__,flush=True)\n raise SystemExit(91)\n'
    executable=sys.executable if redirector else getattr(sys,'_base_executable',sys.executable)
    return Process([executable,'-I','-B','-c',wrapped],cwd=backend,env=environment(),store_id=uuid4().hex,run_id=uuid4().hex,resources=resources,tree_probe=True)

def test_venv_redirector_process_slot_diagnosis():
    code="import os;print(os.getpid(),flush=True);input()";rows=[]
    for redirected in [True,False]:
        p=parent(code,redirector=redirected)
        try:
            actual=int(line(p));o=p.observation()
            # Job accounting is sampled and wrapper topology is installation-
            # dependent. Record it, do not assert an invented exact count.
            assert o['active_processes']>=1 and member(p,actual)
            rows.append(dict(venv_redirector=redirected,job_active_processes=o['active_processes'],actual_python_is_creation_pid=actual==p.pid))
        finally:assert p.close()['active_processes']==0
    record('redirector-process-slots',dict(observations=rows,cap_unchanged=2))

def test_explicit_snapshot_import_boundary():
    probe="import importlib.util,json;print(json.dumps(dict(tests=importlib.util.find_spec('tests') is not None)),flush=True)"
    a=launch(probe);b=None
    try:
        assert not json.loads(line(a))['tests'];assert a.wait(10)==0
        b=parent(probe);assert json.loads(line(b))['tests'];assert b.wait(10)==0
        record('parent-import-boundary',dict(original_isolated_base_python_cannot_import_snapshot_tests=True,explicit_snapshot_venv_can_import=True))
    finally:
        a.close()
        if b:b.close()

NESTED="""import json,sys,ctypes
from tests.test_windows_supervision import launch
p=launch('import ctypes;ctypes.windll.kernel32.Sleep(60000)')
print(json.dumps(dict(pid=p.pid,created=p.identity)),flush=True)
sys.stdin.readline()
"""

def member(p,pid):
    k=kernel();k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
    k.IsProcessInJob.argtypes=[W.HANDLE,W.HANDLE,C.POINTER(W.BOOL)];k.IsProcessInJob.restype=W.BOOL
    h=k.OpenProcess(0x1000,False,pid);assert h
    try:
        result=W.BOOL();assert k.IsProcessInJob(h,p.jobs[-1],C.byref(result));return bool(result.value)
    finally:k.CloseHandle(h)

def dead(pid,created):
    # TerminateJobObject is asynchronous. Do not mistake an empty Job's
    # accounting snapshot for the descendant process handle being signaled.
    end=time.monotonic()+5
    while alive(pid,created) and time.monotonic()<end:time.sleep(.01)
    assert not alive(pid,created)
    return True

def test_nested_parent_worker_membership_tree_cleanup_and_unrelated_survival():
    outsider=launch('import ctypes;ctypes.windll.kernel32.Sleep(60000)');p=None
    try:
        p=parent(NESTED);child=json.loads(line(p));assert member(p,p.pid) and member(p,child['pid'])
        assert alive(child['pid'],child['created'])
        observation=p.close();assert observation['active_processes']==0 and dead(child['pid'],child['created'])
        assert outsider.poll() is None
        record('parent-tree',dict(parent_and_nested_worker_in_outer_job=True,active_after_close=0,unrelated_owned_sentinel_survived=True))
    finally:
        if p:p.close()
        outsider.close()

def test_parent_private_commit_limit_with_nested_worker():
    code=NESTED.replace('sys.stdin.readline()',"try:\n x=bytearray(256*1024*1024)\n print('UNEXPECTED',flush=True)\nexcept MemoryError:\n print('PARENT_MEMORY_DENIED',flush=True)\nsys.stdin.readline()")
    p=parent(code,resources=Resources(private_commit_bytes=64*1024*1024))
    try:
        child=json.loads(line(p));assert member(p,child['pid']) and line(p).strip()==b'PARENT_MEMORY_DENIED'
        o=p.observation();assert o['peak_private_commit_bytes']<=64*1024*1024
        record('parent-memory',dict(parent_memory_denied=True,peak_process_commit=o['peak_private_commit_bytes'],per_process_limit=64*1024*1024,aggregate_limit=False))
    finally:assert p.close()['active_processes']==0

def test_parent_cpu_death_kills_nested_worker_handles():
    code=NESTED.replace('sys.stdin.readline()','while True: pass')
    p=parent(code,resources=Resources(process_user_cpu_seconds=1))
    try:
        child=json.loads(line(p));assert p.wait(15)!=0
        end=time.monotonic()+5
        while alive(child['pid'],child['created']) and time.monotonic()<end:time.sleep(.02)
        assert not alive(child['pid'],child['created'])
        o=p.observation();record('parent-cpu',dict(user_seconds=o['user_seconds'],exit_code=o['exit_code'],nested_worker_dead=True,scope='Periodic per-process user CPU, not aggregate CPU rate'))
    finally:assert p.close()['active_processes']==0

def test_parent_breakaway_request_rejected():
    code="""import subprocess,sys
try:
 subprocess.Popen([sys.executable,'-I','-c','pass'],creationflags=0x01000000)
 print('UNEXPECTED',flush=True)
except OSError:
 print('BREAKAWAY_DENIED',flush=True)
"""
    p=parent(code)
    try:assert line(p).strip()==b'BREAKAWAY_DENIED' and p.wait(10)==0
    finally:p.close()

def test_real_checkpoint_survives_outer_parent_tree_termination(fixture):
    w,run,_=paused(fixture);checkpoint=w.checkpoint(PRINCIPAL,run);best=w.result(PRINCIPAL,run)
    code="""import sys,time,json
wire=sys.stdout
class Discard:
 def write(self,s):return len(s)
 def flush(self):pass
sys.stdout=Discard()
from services.ga_supervised_worker import Worker
from services.ga_trusted_runs import Coordinator
from services.ga_owned_store import Store
from tests.bounded_worker_support import dependencies
from tests.trusted_run_support import PRINCIPAL
from tests.test_supervised_worker import blocking_arguments
import services.ga_supervised_worker as module
a,c,_=dependencies(1)
w=Worker(Coordinator(Store(ROOT,IDENTITY,max_runs=4),a,c))
module.arguments=blocking_arguments
w.resume(PRINCIPAL,RUN)
end=time.monotonic()+25
while time.monotonic()<end:
 p=w.processes.get(RUN)
 with w.storage.connection() as db:
  registered=db.execute("SELECT pid FROM l_processes WHERE run=? AND status='ACTIVE'",(RUN,)).fetchone()
 if p and p.handle and p.poll() is None and registered and registered[0]==p.pid:break
 time.sleep(.02)
else:raise RuntimeError('Owned nested worker unavailable')
wire.write(json.dumps(dict(pid=p.pid,created=p.identity))+'\\n');wire.flush()
sys.stdin.readline()
""".replace('ROOT',repr(str(w.storage.root))).replace('IDENTITY',repr(w.storage.store_id)).replace('RUN',repr(run))
    p=parent(code)
    try:
        child=json.loads(line(p));assert member(p,child['pid'])
        assert p.close()['active_processes']==0 and dead(child['pid'],child['created'])
    finally:p.close()
    end=time.monotonic()+15
    while time.monotonic()<end and not w.status(PRINCIPAL,run)['recovery_required']:time.sleep(.05)
    assert w.checkpoint(PRINCIPAL,run)==checkpoint and w.result(PRINCIPAL,run)==best
    a,c,_=dependencies(1);again=Worker(Coordinator(Store(w.storage.root,w.storage.store_id,max_runs=4),a,c))
    with again.storage.connection() as db:row=again.store.row(db,ACTOR,run)
    assert row['lease']<=again.clock()
    again.recover(PRINCIPAL,run,expected_tip=row['tip'],expected_fence=row['fence'])
    assert until(again,run,{'COMPLETED','FAILED'})['state']=='COMPLETED'
    with again.storage.connection() as db:
        with pytest.raises(RunError):again.store.fenced(db,ACTOR,run,row['executor'],row['fence'])
    assert again.close(PRINCIPAL)['quiescent']
    record('parent-checkpoint-recovery',dict(durable_checkpoint_unchanged_after_outer_termination=True,explicit_scoped_same_store_recovery_completed=True,stale_owner_fenced=True,backup_restore=False))
