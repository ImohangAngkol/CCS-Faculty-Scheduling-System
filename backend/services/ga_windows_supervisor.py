"""U5L Windows-only, creation-time Job containment. No deployment activation."""
from dataclasses import dataclass,asdict
import ctypes as C
from ctypes import wintypes as W
import json
import os
import subprocess
import threading
from functools import wraps
import time
from services.ga_run_authority import RunError

VERSION='ga-windows-supervision-v1'

@dataclass(frozen=True)
class Resources:
    private_commit_bytes:int=768*1024*1024
    process_user_cpu_seconds:int=60
    cpu_rate_percent:int|None=None
    grace_seconds:int=5

    def validate(self):
        if (type(self.private_commit_bytes) is not int or not 32*1024*1024<=self.private_commit_bytes<=2*1024**3
                or type(self.process_user_cpu_seconds) is not int or not 1<=self.process_user_cpu_seconds<=120
                or type(self.grace_seconds) is not int or not 1<=self.grace_seconds<=5):
            raise RunError('GA_SUPERVISION_RESOURCE_INVALID')
        if self.cpu_rate_percent is not None:raise RunError('GA_SUPERVISION_CPU_RATE_UNQUALIFIED',503)
        if os.name!='nt':raise RunError('GA_SUPERVISION_WINDOWS_REQUIRED',503)
        return self

class Basic(C.Structure):
    _fields_=[('process_time',C.c_longlong),('job_time',C.c_longlong),('flags',W.DWORD),('min_ws',C.c_size_t),
        ('max_ws',C.c_size_t),('active',W.DWORD),('affinity',C.c_size_t),('priority',W.DWORD),('scheduling',W.DWORD)]
class IO(C.Structure):
    _fields_=[(n,C.c_ulonglong) for n in ['read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes']]
class Extended(C.Structure):
    _fields_=[('basic',Basic),('io',IO),('process_memory',C.c_size_t),('job_memory',C.c_size_t),('peak_process',C.c_size_t),('peak_job',C.c_size_t)]
class Accounting(C.Structure):
    _fields_=[(n,C.c_longlong) for n in ['user','kernel','period_user','period_kernel']]+[(n,W.DWORD) for n in ['page_faults','total','active','terminated']]
class Startup(C.Structure):
    _fields_=[('cb',W.DWORD),('reserved',W.LPWSTR),('desktop',W.LPWSTR),('title',W.LPWSTR)]+[(n,W.DWORD) for n in
        ['x','y','xsize','ysize','xchars','ychars','fill','flags']]+[('show',W.WORD),('reserved_size',W.WORD),('reserved_bytes',C.c_void_p),('stdin',W.HANDLE),('stdout',W.HANDLE),('stderr',W.HANDLE)]
class StartupEx(C.Structure):_fields_=[('startup',Startup),('attributes',C.c_void_p)]
class ProcessInfo(C.Structure):_fields_=[('process',W.HANDLE),('thread',W.HANDLE),('pid',W.DWORD),('tid',W.DWORD)]

def kernel():
    if os.name!='nt':raise RunError('GA_SUPERVISION_WINDOWS_REQUIRED',503)
    k=C.WinDLL('kernel32',use_last_error=True)
    signatures={
        'CreateJobObjectW':([C.c_void_p,W.LPCWSTR],W.HANDLE),
        'SetInformationJobObject':([W.HANDLE,C.c_int,C.c_void_p,W.DWORD],W.BOOL),
        'QueryInformationJobObject':([W.HANDLE,C.c_int,C.c_void_p,W.DWORD,C.c_void_p],W.BOOL),
        'TerminateJobObject':([W.HANDLE,W.UINT],W.BOOL),
        'InitializeProcThreadAttributeList':([C.c_void_p,W.DWORD,W.DWORD,C.POINTER(C.c_size_t)],W.BOOL),
        'UpdateProcThreadAttribute':([C.c_void_p,W.DWORD,C.c_size_t,C.c_void_p,C.c_size_t,C.c_void_p,C.c_void_p],W.BOOL),
        'DeleteProcThreadAttributeList':([C.c_void_p],None),
        'SetHandleInformation':([W.HANDLE,W.DWORD,W.DWORD],W.BOOL),
        'CreateProcessW':([W.LPCWSTR,W.LPWSTR,C.c_void_p,C.c_void_p,W.BOOL,W.DWORD,C.c_void_p,W.LPCWSTR,C.c_void_p,C.POINTER(ProcessInfo)],W.BOOL),
        'WaitForSingleObject':([W.HANDLE,W.DWORD],W.DWORD),
        'GetExitCodeProcess':([W.HANDLE,C.POINTER(W.DWORD)],W.BOOL),
        'GetProcessTimes':([W.HANDLE,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p],W.BOOL),
        'CloseHandle':([W.HANDLE],W.BOOL)}
    for name,(args,result) in signatures.items():getattr(k,name).argtypes=args;getattr(k,name).restype=result
    return k

def synchronized(method):
    @wraps(method)
    def call(self,*args,**kwargs):
        with self.lock:return method(self,*args,**kwargs)
    return call

class Process:
    """One owned process, atomic Job-list assignment and explicit handle list.

    Resource quotas cover the optimizer process, not the trusted parent Python
    validator/SQLite. No descendants are permitted in normal worker mode.
    """
    def __init__(self,args,*,cwd,env,store_id,run_id,max_workers=1,resources=Resources(),tree_probe=False):
        import msvcrt
        resources.validate();self.lock=threading.RLock();self.resources=resources;self.k=kernel();self.jobs=[];self.handle=None;self.returncode=None
        self.stdin=None;self.stdout=None;fds=[];attrs=None;attrs_ready=False
        try:
            names=[('Local\\GA-U5K-store-'+store_id,max_workers),('Local\\GA-U5K-run-'+store_id+'-'+run_id,1), (None,2 if tree_probe else 1)]
            # Descendant probe has its own isolated namespace and no single-run
            # job; production/test worker execution never enables this mode.
            if tree_probe:names=[(None,2)]
            for name,active in names:
                job=self.k.CreateJobObjectW(None,name)
                if not job:raise ValueError()
                self.jobs.append(job);limits=Extended();limits.basic.flags=0x2000|0x8;limits.basic.active=active
                if name is None:
                    limits.basic.flags|=0x100|0x2;limits.process_memory=resources.private_commit_bytes
                    limits.basic.process_time=resources.process_user_cpu_seconds*10_000_000
                if not self.k.SetInformationJobObject(job,9,C.byref(limits),C.sizeof(limits)):raise ValueError()
                actual=Extended()
                if not self.k.QueryInformationJobObject(job,9,C.byref(actual),C.sizeof(actual),None):raise ValueError()
                if actual.basic.flags!=limits.basic.flags or actual.basic.active!=active or actual.process_memory!=limits.process_memory or actual.basic.process_time!=limits.basic.process_time:raise ValueError()
            read_in,write_in=os.pipe();fds.extend([read_in,write_in]);read_out,write_out=os.pipe();fds.extend([read_out,write_out])
            null=os.open(os.devnull,os.O_WRONLY);fds.append(null)
            child_handles=(W.HANDLE*3)(*[msvcrt.get_osfhandle(n) for n in [read_in,write_out,null]])
            for h in child_handles:
                if not self.k.SetHandleInformation(h,1,1):raise ValueError()
            size=C.c_size_t();self.k.InitializeProcThreadAttributeList(None,2,0,C.byref(size));attrs=C.create_string_buffer(size.value)
            if not self.k.InitializeProcThreadAttributeList(attrs,2,0,C.byref(size)):raise ValueError()
            attrs_ready=True;job_handles=(W.HANDLE*len(self.jobs))(*self.jobs)
            for key,value in [(0x20002,child_handles),(0x2000D,job_handles)]:
                if not self.k.UpdateProcThreadAttribute(attrs,0,key,C.cast(value,C.c_void_p),C.sizeof(value),None,None):raise ValueError()
            startup=StartupEx();startup.startup.cb=C.sizeof(startup);startup.startup.flags=0x100
            startup.startup.stdin=child_handles[0];startup.startup.stdout=child_handles[1];startup.startup.stderr=child_handles[2];startup.attributes=C.cast(attrs,C.c_void_p)
            command=C.create_unicode_buffer(subprocess.list2cmdline(args));block=C.create_unicode_buffer('\0'.join(k+'='+v for k,v in sorted(env.items()))+'\0\0');info=ProcessInfo()
            if not self.k.CreateProcessW(args[0],command,None,None,True,0x08000000|0x00080000|0x400,block,str(cwd),C.byref(startup),C.byref(info)):raise ValueError()
            self.handle=info.process;self.pid=int(info.pid);self.k.CloseHandle(info.thread)
            self.stdin=os.fdopen(write_in,'wb',buffering=0);fds.remove(write_in)
            self.stdout=os.fdopen(read_out,'rb');fds.remove(read_out)
            self.identity=self.times()['created_100ns']
        except BaseException:
            self.close();raise RunError('GA_SUPERVISION_CREATION_OR_LIMITS_UNAVAILABLE',503) from None
        finally:
            if attrs_ready:self.k.DeleteProcThreadAttributeList(attrs)
            for fd in fds:os.close(fd)

    @synchronized
    def poll(self):
        if self.returncode is None and self.k.WaitForSingleObject(self.handle,0)==0:
            code=W.DWORD()
            if not self.k.GetExitCodeProcess(self.handle,C.byref(code)):raise RunError('GA_SUPERVISION_EXIT_UNVERIFIED')
            self.returncode=code.value
        return self.returncode
    @synchronized
    def wait(self,timeout=5):
        if self.k.WaitForSingleObject(self.handle,int(timeout*1000))!=0:raise RunError('GA_SUPERVISION_TERMINATION_UNVERIFIED')
        return self.poll()
    @synchronized
    def terminate(self):
        if self.handle is None:return self.returncode
        if not self.k.TerminateJobObject(self.jobs[-1],137):raise RunError('GA_SUPERVISION_TERMINATION_UNVERIFIED')
        return self.wait(self.resources.grace_seconds)
    @synchronized
    def times(self):
        values=[C.c_ulonglong() for _ in range(4)]
        if not self.k.GetProcessTimes(self.handle,*[C.byref(v) for v in values]):raise RunError('GA_SUPERVISION_IDENTITY_UNVERIFIED')
        return dict(created_100ns=values[0].value,kernel_seconds=values[2].value/10_000_000,user_seconds=values[3].value/10_000_000)
    @synchronized
    def observation(self):
        limits=Extended();account=Accounting()
        if not self.k.QueryInformationJobObject(self.jobs[-1],9,C.byref(limits),C.sizeof(limits),None) or not self.k.QueryInformationJobObject(self.jobs[-1],1,C.byref(account),C.sizeof(account),None):
            raise RunError('GA_SUPERVISION_ACCOUNTING_UNVERIFIED')
        return dict(pid=self.pid,**self.times(),exit_code=self.poll(),active_processes=account.active,
            peak_private_commit_bytes=limits.peak_process,enforced=asdict(self.resources),creation_time_job_binding=True)
    @synchronized
    def close(self):
        observed=None
        if self.handle:
            self.k.TerminateJobObject(self.jobs[-1],137)
            self.wait(self.resources.grace_seconds)
            until=time.monotonic()+self.resources.grace_seconds
            while True:
                observed=self.observation()
                if observed['active_processes']==0:break
                if time.monotonic()>=until:raise RunError('GA_SUPERVISION_TERMINATION_UNVERIFIED')
                time.sleep(.01)
            self.k.CloseHandle(self.handle);self.handle=None
        for stream in [self.stdin,self.stdout]:
            if stream and not stream.closed:stream.close()
        for job in reversed(self.jobs):self.k.CloseHandle(job)
        self.jobs=[]
        return observed

def alive(pid,created):
    """Read-only PID + creation-time check. Never kill by a stored PID."""
    k=kernel();k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
    h=k.OpenProcess(0x100000|0x1000,False,pid)
    if not h:
        if C.get_last_error() in {87,1168}:return False
        raise RunError('GA_SUPERVISION_OLD_PROCESS_UNVERIFIED')
    try:
        values=[C.c_ulonglong() for _ in range(4)]
        if not k.GetProcessTimes(h,*[C.byref(v) for v in values]):raise RunError('GA_SUPERVISION_OLD_PROCESS_UNVERIFIED')
        return values[0].value==created and k.WaitForSingleObject(h,0)!=0
    finally:k.CloseHandle(h)
