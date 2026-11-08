"""Real Win32 processes with fictional/no academic inputs, not mocks of quotas."""
from dataclasses import replace
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4
import pytest
from services.ga_windows_supervisor import Process,Resources,alive,kernel
from services.ga_run_authority import RunError

def environment():
    return {k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE'}}
def launch(code,resources=Resources(),**kwargs):
    return Process([getattr(sys,'_base_executable',sys.executable),'-I','-B','-c',code],cwd=Path.cwd(),env=environment(),
        store_id=uuid4().hex,run_id=uuid4().hex,resources=resources,**kwargs)
def record(name,value):
    if os.environ.get('U5H_PROTOCOL_EVIDENCE'):
        with (Path(os.environ['U5H_PROTOCOL_EVIDENCE'])/('U5L-'+name+'.json')).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)

def test_creation_bound_identity_limits_clean_exit():
    p=launch("print('FICTIONAL_READY',flush=True)")
    try:
        assert p.stdout.readline()==b'FICTIONAL_READY\r\n';assert p.wait(10)==0
        o=p.observation();assert o['created_100ns']==p.identity and o['creation_time_job_binding']
        assert o['peak_private_commit_bytes']<=p.resources.private_commit_bytes;record('clean-process',o)
    finally:assert p.close()['active_processes']==0

def test_real_private_commit_denies_excess_allocation():
    p=launch("try:\n x=bytearray(256*1024*1024)\n print('UNEXPECTED')\nexcept MemoryError:\n print('MEMORY_DENIED',flush=True)",Resources(private_commit_bytes=64*1024*1024))
    try:
        output=p.stdout.readline();assert output.strip()==b'MEMORY_DENIED';assert p.wait(10)==0
        o=p.observation();assert o['peak_private_commit_bytes']<=64*1024*1024;record('private-commit-denial',o)
    finally:p.close()

def test_real_user_cpu_quota_terminates_computation():
    p=launch('while True: pass',Resources(process_user_cpu_seconds=1));start=time.monotonic()
    try:
        assert p.wait(15)!=0;o=p.observation()
        assert .8<=o['user_seconds']<5 and time.monotonic()-start<15
        record('cpu-time-termination',o)
    finally:assert p.close()['active_processes']==0

def test_descendant_creation_denied_in_single_worker_mode():
    code="import sys,subprocess\ntry:\n subprocess.Popen([sys.executable,'-I','-c','import time;time.sleep(60)'])\n print('UNEXPECTED',flush=True)\nexcept OSError:\n print('DESCENDANT_DENIED',flush=True)"
    p=launch(code)
    try:assert p.stdout.readline().strip()==b'DESCENDANT_DENIED';assert p.wait(10)==0
    finally:assert p.close()['active_processes']==0

def test_explicit_tree_probe_terminates_both_owned_processes():
    code="import sys,subprocess,time\np=subprocess.Popen([sys.executable,'-I','-c','import time;time.sleep(60)'])\nprint(p.pid,flush=True)\ntime.sleep(60)"
    p=launch(code,tree_probe=True);h=None;k=kernel()
    k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
    try:
        child=int(p.stdout.readline());h=k.OpenProcess(0x100000,False,child);assert h
        result=p.close();assert result['active_processes']==0 and k.WaitForSingleObject(h,5000)==0
        record('owned-tree-cleanup',dict(active_after_close=0,parent_pid=p.pid,child_pid=child,scope='Separate two-process primitive probe, not a multi-process GA mode'))
    finally:
        p.close()
        if h:k.CloseHandle(h)

@pytest.mark.parametrize('field,value',[('private_commit_bytes',0),('private_commit_bytes',2**40),('process_user_cpu_seconds',0),('process_user_cpu_seconds',True),('cpu_rate_percent',20),('grace_seconds',9)])
def test_invalid_or_unqualified_resource_modes_fail_closed(field,value):
    with pytest.raises(RunError):replace(Resources(),**{field:value}).validate()

def test_parent_death_closes_noninherited_jobs_and_kills_child():
    code="""import sys,os
from tests.test_windows_supervision import launch
p=launch('import ctypes;ctypes.windll.kernel32.Sleep(60000)')
print(str(p.pid)+','+str(p.identity),flush=True)
sys.stdin.readline()
os._exit(23)
"""
    parent=subprocess.Popen([sys.executable,'-B','-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=environment(),text=True)
    try:
        pid,created=map(int,parent.stdout.readline().strip().split(','));assert alive(pid,created)
        parent.stdin.write('exit supervisor\n');parent.stdin.flush();assert parent.wait(10)==23
        end=time.monotonic()+5
        while alive(pid,created) and time.monotonic()<end:time.sleep(.02)
        assert not alive(pid,created);record('supervisor-death',dict(supervisor_exit=23,owned_child_dead=True,job_handles_not_inherited=True))
    finally:
        if parent.poll() is None:parent.terminate();parent.wait(5)
        parent.stdin.close();parent.stdout.close()
