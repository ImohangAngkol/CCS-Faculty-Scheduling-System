"""U5K isolated worker contract. No provider, UI or deployment activation."""
from dataclasses import dataclass,asdict
import csv
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import tempfile
from services.ga_run_authority import RunError,canonical,digest

VERSION='ga-bounded-worker-v1'
TERMINAL={'STOPPED','COMPLETED','FAILED'}

@dataclass(frozen=True)
class Limits:
    batch_generations:int=1
    total_generations:int=4
    wall_seconds:int=120
    checkpoint_bytes:int=8*1024*1024
    retained_checkpoints:int=8
    run_bytes:int=64*1024*1024
    active_workers:int=1
    cpu_seconds:int|None=None
    memory_bytes:int|None=None

    def validate(self):
        values=asdict(self)
        if any(type(values[k]) is not int or values[k]<=0 for k in values if k not in {'cpu_seconds','memory_bytes'}):raise RunError('GA_WORKER_LIMIT_INVALID',422)
        if self.batch_generations>self.total_generations or self.total_generations>20 or self.active_workers>2 or self.wall_seconds>600:
            raise RunError('GA_WORKER_FIXTURE_LIMIT_EXCEEDED')
        if self.cpu_seconds is not None or self.memory_bytes is not None:
            raise RunError('GA_WORKER_CPU_MEMORY_MODE_UNAVAILABLE',503)
        return self

def implementation():
    folder=Path(__file__).parent
    return digest({n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in
        ['ga_worker_contract.py','ga_worker_store.py','ga_bounded_worker.py','ga_worker_child.py']})

def fictional_source():
    """Only owned source snapshots with EMPTY fictional import tables can run.

    Optimizer-ready models come from the separately verified bundle, never these
    import placeholders. This is deliberately unavailable in the real checkout.
    """
    backend=Path(__file__).resolve().parents[1];snapshot=backend.parent;owner=snapshot.parent
    try:
        if (snapshot.name!='repository' or owner.parent!=Path(tempfile.gettempdir()).resolve()
                or not owner.name.startswith('u5c-r1-snapshot-u5h-') or not (owner/'OWNED-SNAPSHOT.json').is_file()):raise ValueError()
        data=backend/'data'
        expected={'first_sem_bsit_subjects.csv','BSIT_Consolidated_Subject_Schedules.csv','Faculty Preferences V2.csv',
            'Faculty Admin, Research and Extension.csv','faculty_qualifications.csv','faculty_subject_eligibility.csv','subject_domains.csv',
            'faculty_identities.json','faculty_preferences.json','ga_settings.json','preassigned_assignments.json'}
        if {p.name for p in data.iterdir() if p.is_file()}!=expected:raise ValueError()
        for p in data.iterdir():
            if p.is_symlink() or p.is_junction() or p.stat().st_size>8192:raise ValueError()
            if p.suffix=='.csv':
                with p.open(encoding='utf-8-sig',newline='') as f:
                    if len(list(csv.reader(f)))!=1:raise ValueError()
            else:
                value=json.loads(p.read_bytes())
                allowed={'faculty_identities.json':{'version':1,'faculty':[]},'ga_settings.json':{},
                    'preassigned_assignments.json':{'external_instructors':{},'assignments':[]}}
                if p.name=='faculty_preferences.json':
                    if value not in ({},[]):raise ValueError()
                elif value!=allowed[p.name]:raise ValueError()
        return backend
    except (ValueError,OSError,KeyError):raise RunError('GA_WORKER_FICTIONAL_SOURCE_REQUIRED',503) from None

class Job:
    """Owned Windows job: direct child and no descendants; kill on handle close.

    Child waits for stdin until assignment succeeds. Unsupported OS/job policies
    reject execution. CPU/private-memory quota modes are explicitly unavailable.
    """
    def __init__(self,process,*,store_id=None,run_id=None,max_workers=1):
        if os.name!='nt':raise RunError('GA_WORKER_PROCESS_ISOLATION_UNAVAILABLE',503)
        class Basic(ctypes.Structure):
            _fields_=[('process_time',ctypes.c_longlong),('job_time',ctypes.c_longlong),('flags',wintypes.DWORD),
                ('min_ws',ctypes.c_size_t),('max_ws',ctypes.c_size_t),('active',wintypes.DWORD),('affinity',ctypes.c_size_t),
                ('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]
        class IO(ctypes.Structure):_fields_=[(n,ctypes.c_ulonglong) for n in ['read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes']]
        class Extended(ctypes.Structure):
            _fields_=[('basic',Basic),('io',IO),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR];self.kernel.CreateJobObjectW.restype=wintypes.HANDLE
        self.kernel.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        self.kernel.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
        self.kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        self.handles=[]
        jobs=[(None,1)] if store_id is None else [
            ('Local\\GA-U5K-store-'+store_id,max_workers),('Local\\GA-U5K-run-'+store_id+'-'+run_id,1)]
        for name,maximum in jobs:
            handle=self.kernel.CreateJobObjectW(None,name)
            if handle:self.handles.append(handle)
            limits=Extended();limits.basic.flags=0x2000|0x8;limits.basic.active=maximum
            if (not handle or not self.kernel.SetInformationJobObject(handle,9,ctypes.byref(limits),ctypes.sizeof(limits))
                    or not self.kernel.AssignProcessToJobObject(handle,wintypes.HANDLE(int(process._handle)))):
                self.close();raise RunError('GA_WORKER_JOB_UNAVAILABLE',503)
    def close(self):
        for handle in reversed(self.handles):self.kernel.CloseHandle(handle)
        self.handles=[]
