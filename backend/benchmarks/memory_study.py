"""Isolated fictional GA memory study. No production changes or persistence.

Windows working set, traced allocations and retention are different experiments.
Only numeric summaries, source locations and fictional output hashes are saved.
"""
import argparse
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
import copy
import ctypes
from ctypes import wintypes
from datetime import datetime, timedelta, timezone
import gc
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import threading
import time
import tracemalloc
import weakref

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from benchmarks import scaled_python as bench
from benchmarks.scenarios import build,snapshot

BASE=ROOT/'docs/testing/ga-memory-study'
PHASE2=ROOT/'docs/testing/ga-performance-phase2/20261028T113836085281+0800/results.json'
ZONE=timezone(timedelta(hours=8))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_entry():
    record=json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'))
    if not all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in record.items()):
        raise RuntimeError('BASELINE_MISMATCH_STOP_NO_REPAIR')
    return len(record)


class Counters(ctypes.Structure):
    _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in (
        'PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
        'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage')]


class ProcessMemory:
    def __init__(self):
        if os.name!='nt':
            raise RuntimeError('WINDOWS_PROCESS_MEMORY_REQUIRES_WINDOWS')
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.get=kernel.K32GetProcessMemoryInfo
        self.get.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        self.get.restype=wintypes.BOOL
        kernel.GetCurrentProcess.argtypes=[]
        kernel.GetCurrentProcess.restype=wintypes.HANDLE
        self.handle=kernel.GetCurrentProcess()

    def read(self):
        counters=Counters(); counters.cb=ctypes.sizeof(counters)
        if not self.get(self.handle,ctypes.byref(counters),counters.cb):
            raise RuntimeError('PROCESS_MEMORY_QUERY_FAILED')
        return {'working_set_bytes':counters.WorkingSetSize,
                'process_lifetime_peak_working_set_bytes':counters.PeakWorkingSetSize,
                'private_commit_bytes_NOT_RSS':counters.PrivateUsage}


class Sampler:
    def __init__(self,process,interval=.05):
        self.process=process; self.interval=interval; self.stop=threading.Event()
        self.maximum=0; self.count=0; self.failed=False

    def sample(self):
        try:
            self.maximum=max(self.maximum,self.process.read()['working_set_bytes']); self.count+=1
        except RuntimeError:
            self.failed=True

    def loop(self):
        while not self.stop.wait(self.interval):
            self.sample()

    def __enter__(self):
        self.sample(); self.thread=threading.Thread(target=self.loop,daemon=True); self.thread.start()
        return self

    def __exit__(self,*args):
        self.sample(); self.stop.set(); self.thread.join(timeout=2)
        if self.thread.is_alive() or self.failed:
            raise RuntimeError('PROCESS_MEMORY_SAMPLER_FAILED')

    def result(self):
        return {'sampled_interval_peak_working_set_bytes':self.maximum,'sample_count':self.count,
                'poll_interval_seconds':self.interval,'scope':'Sampled peak may miss short spikes; OS lifetime peak is separately reported'}


def location(frame):
    path=Path(frame.filename)
    return {'file':path.relative_to(ROOT).as_posix() if path.is_absolute() and path.is_relative_to(ROOT) else path.name,
            'line':frame.lineno}


def allocation_rows(after,before=None,limit=12):
    stats=after.compare_to(before,'traceback') if before is not None else after.statistics('traceback')
    positive=[s for s in stats if (s.size_diff if before is not None else s.size)>0]
    positive.sort(key=lambda s:s.size_diff if before is not None else s.size,reverse=True)
    def row(stat):
        return {'bytes':stat.size_diff if before is not None else stat.size,
                'blocks':stat.count_diff if before is not None else stat.count,
                'traceback':[location(f) for f in stat.traceback]}
    return {'scope':'Positive NET LIVE allocation differences, not total churn or exclusive function allocation',
            'top':list(map(row,positive[:limit])),
            'positive_net_bytes':sum(s.size_diff if before is not None else s.size for s in positive),
            'positive_net_bytes_with_copy_frame':sum(s.size_diff if before is not None else s.size for s in positive
                if any(Path(f.filename).name=='copy.py' for f in s.traceback))}


def graph_summary(root):
    """Walk only explicit data containers/models, NEVER arbitrary GC referents.

    No module/class/function/closure traversal and no serialized attribute values.
    getsizeof sums shallow sizes of unique reachable objects; not native buffers.
    """
    pending=[root]; seen=set(); counts=Counter(); shallow=0; unassigned_blocks=0
    subject_keys=Counter(); faculty_codes=set(); roots=set()
    if isinstance(root,(list,tuple)):
        roots={id(s) for s in root if type(s).__name__=='Subject'}
    assigned=set()
    if roots:
        assigned={getattr(s.assigned_faculty,'code',None) for s in root if id(s) in roots}
    reachable_root_subjects=0
    while pending:
        value=pending.pop(); identity=id(value)
        if identity in seen:
            continue
        seen.add(identity); shallow+=sys.getsizeof(value)
        kind=type(value); counts[kind.__name__]+=1
        if type(value) is dict:
            pending.extend(value.keys()); pending.extend(value.values())
        elif type(value) in (list,tuple,set,frozenset):
            pending.extend(value)
        elif kind.__module__.startswith('genetic_algorithm.models.') and hasattr(value,'__dict__'):
            pending.append(vars(value))
            if kind.__name__=='TimeBlock':
                unassigned_blocks+=getattr(value,'subject',None) is None
            elif kind.__name__=='Subject':
                subject_keys[(value.number,getattr(value.section,'code',None))]+=1
                reachable_root_subjects+=identity in roots
            elif kind.__name__=='Faculty':
                faculty_codes.add(value.code)
    return {'unique_objects':len(seen),'estimated_unique_shallow_bytes_NOT_RSS':shallow,
            'object_type_counts':dict(counts),'unassigned_TimeBlocks':unassigned_blocks,
            'root_Subject_objects':len(roots),'reachable_nonroot_Subject_objects':counts['Subject']-reachable_root_subjects,
            'extra_Subject_objects_for_repeated_offering_keys':sum(n-1 for n in subject_keys.values()),
            'reachable_faculty_identity_count':len(faculty_codes),'root_assigned_faculty_identity_count':len(assigned),
            'interpretation':'Reachable does not mean unnecessary; full calendars/metadata can be required for validation and copying semantics'}


def trace_point(process):
    current,peak=tracemalloc.get_traced_memory()
    return {'traced_current_bytes':current,'traced_peak_bytes_NOT_RSS':peak,
            'tracer_metadata_bytes':tracemalloc.get_tracemalloc_memory(),'process':process.read()}


def engine_once(name,process,trace=False):
    engine=bench.runtime()[0]
    parameters=bench.runtime()[-1](**json.loads(PHASE2.read_text())['parameters'])
    values,legacy,preferences,settings,metadata=build(name)
    pinned=snapshot(values,metadata)
    last=None; history=[]; boundaries=[]; baseline=None
    def boundary(state):
        nonlocal last
        last=state
        history.append(dict(state['history'][-1]))
        point={'generation':state['generation'],'process':process.read()}
        if trace:
            point.update(trace_point(process))
            capture=tracemalloc.take_snapshot()
            point['live_allocations']=allocation_rows(capture,baseline)
            del capture
        boundaries.append(point)
    with bench.synthetic_scoring(values,preferences,settings),open(os.devnull,'w') as sink,redirect_stdout(sink),redirect_stderr(sink),bench.no_io():
        gc.collect()
        before=process.read()
        if trace:
            tracemalloc.start(1)
            baseline=tracemalloc.take_snapshot()
        tick=time.perf_counter()
        assert engine.run(values,pinned,parameters,legacy,boundary)=='complete'
        elapsed=time.perf_counter()-tick
        peak_point=trace_point(process) if trace else None
        # Validation happens after capturing the measured engine peak.
        reduced=engine.reduced_templates(pinned,values)
        engine.admit(last['best'],pinned,reduced)
        assignments=bench.signature(last['best'])
        signature=hashlib.sha256(json.dumps(assignments,sort_keys=True).encode()).hexdigest()
        reference=json.loads(PHASE2.read_text())['results'][name]['trials'][0]
        assert signature==reference['best_assignment_sha256'] and history==reference['history']
        refs=[weakref.ref(last['best'][0]),weakref.ref(last['best'][0].assigned_faculty),
              weakref.ref(last['best'][0].lecture_room)]
        result={'status':'SUCCESS','scenario':name,'seed':714,'parameters':parameters.model_dump(),
                'history':history,'best_assignment_sha256':signature,'phase2_output_matches':True,
                'hard_constraints':'PASS: original admission','before_engine_process':before,
                'after_engine_process':peak_point['process'] if trace else process.read(),
                'engine_peak_point':peak_point,'generation_points':boundaries,
                'instrumented_seconds_NOT_performance_baseline':elapsed}
    return result,refs,baseline


def full_run(name,mode):
    process=ProcessMemory(); startup=process.read(); bench.runtime(); imported=process.read()
    rng=random.getstate()
    try:
        random.seed(714)
        with Sampler(process) as sampler:
            result,refs,baseline=engine_once(name,process,trace=mode=='alloc')
        # The engine callback's last state and original graph are no longer held.
        before_gc=trace_point(process) if mode=='alloc' else {'process':process.read()}
        collected=gc.collect()
        after_gc=trace_point(process) if mode=='alloc' else {'process':process.read()}
        if mode=='alloc':
            post=tracemalloc.take_snapshot()
            retained=allocation_rows(post,baseline); del post,baseline
            tracemalloc.stop()
        else:
            retained=None
        result.update(mode=mode,startup_process=startup,after_import_process=imported,
                      process_sampling=sampler.result(),before_release_collection=before_gc,
                      after_release_collection=after_gc,gc_collected=collected,
                      representative_model_weakrefs_alive_after_gc=sum(r() is not None for r in refs),
                      post_release_live_allocations=retained,
                      scope='Traced allocations with probe overhead' if mode=='alloc' else 'OS process RAM without tracemalloc; no accelerated engine')
        return result
    finally:
        if tracemalloc.is_tracing():tracemalloc.stop()
        random.setstate(rng)


def probe_operation(label,function,process,include_graph=False):
    gc.collect(); before_process=process.read()
    tracemalloc.start(8)
    try:
        baseline=tracemalloc.take_snapshot(); initial=tracemalloc.get_traced_memory()[0]
        tracemalloc.reset_peak(); tick=time.perf_counter(); value=function(); elapsed=time.perf_counter()-tick
        current,peak=tracemalloc.get_traced_memory(); metadata=tracemalloc.get_tracemalloc_memory()
        capture=tracemalloc.take_snapshot()
        allocations=allocation_rows(capture,baseline)
        scalar=value if type(value) in (int,float) else None
        del capture,baseline
    finally:
        tracemalloc.stop()
    graph=graph_summary(value) if include_graph else None
    after_process=process.read(); value=None; gc.collect()
    return {'operation':label,'incremental_traced_peak_bytes':max(0,peak-initial),
            'incremental_traced_live_bytes':current-initial,'tracer_metadata_bytes':metadata,
            'allocation_snapshot':allocations,'result_scalar':scalar,'copied_graph':graph,
            'process_before':before_process,'process_after_result':after_process,'process_after_drop_gc':process.read(),
            'instrumented_seconds_NOT_performance_baseline':elapsed,
            'scope':'8-frame standalone operation; peak includes freed temporaries, snapshot only net live blocks; inputs were allocated before tracing'}


def focused(name):
    process=ProcessMemory(); engine,fitness,scoring_inputs,*_=bench.runtime()
    rng=random.getstate()
    try:
        values,legacy,preferences,settings,metadata=build(name)
        pinned=snapshot(values,metadata)
        with bench.synthetic_scoring(values,preferences,settings),open(os.devnull,'w') as sink,redirect_stdout(sink),redirect_stderr(sink),bench.no_io():
            random.seed(10101); reduced=engine.reduced_templates(pinned,values)
            candidate=engine.construct(reduced,5); engine.admit(candidate,pinned,reduced)
            frozen=engine.freeze(values); token=scoring_inputs.set(frozen)
            from genetic_algorithm.utils.FitnessObservation import observed_scores
            assert observed_scores.get() is None
            try:
                expected=fitness.faculty_preference_fitness(candidate,legacy)
                def repeated_score():
                    result=None
                    for _ in range(25):
                        result=fitness.faculty_preference_fitness(candidate,legacy)
                        assert result==expected
                    return result
                def repeated_preferences():
                    result=None
                    for _ in range(25):result=fitness._build_effective_preferences(legacy)
                    return result
                def observer_demo(enabled):
                    scores={} if enabled else None
                    scope=observed_scores.set(scores)
                    try:
                        for _ in range(3):
                            cloned=copy.deepcopy(candidate)
                            assert fitness.faculty_preference_fitness(cloned,legacy)==expected
                        return scores if enabled else None
                    finally:observed_scores.reset(scope)
                cases=[('deepcopy_templates',lambda:copy.deepcopy(reduced),True),
                       ('deepcopy_chromosome',lambda:copy.deepcopy(candidate),True),
                       ('freeze_scoring_inputs',lambda:engine.freeze(values),False),
                       ('fitness_once',lambda:fitness.faculty_preference_fitness(candidate,legacy),False),
                       ('fitness_25_discarded_results',repeated_score,False),
                       ('effective_preferences_once',lambda:fitness._build_effective_preferences(legacy),False),
                       ('effective_preferences_25_last_kept',repeated_preferences,False),
                       ('normalize_one_preference',lambda:fitness._normalize_dashboard_preference(preferences[0]),False),
                       ('score_3_copies_observer_disabled',lambda:observer_demo(False),False),
                       ('score_3_copies_observer_enabled',lambda:observer_demo(True),False)]
                records=[probe_operation(label,fn,process,graph) for label,fn,graph in cases]
            finally:scoring_inputs.reset(token)
        return {'status':'SUCCESS','scenario':name,'fixture':'Separate original seed10101 constructive witness, not the Phase2 best chromosome',
                'witness_fitness':expected,'witness_graph':graph_summary(candidate),
                'template_graph':graph_summary(reduced),'operations':records,
                'observer_scope':'Explicit diagnostic only; production observation policy unchanged; direct V2 benchmark observation is disabled'}
    finally:random.setstate(rng)


def retention(repetitions=5):
    process=ProcessMemory(); bench.runtime(); gc.collect()
    before=process.read(); records=[]; rng=random.getstate()
    tracemalloc.start(1)
    baseline=tracemalloc.take_snapshot()
    try:
        for iteration in range(repetitions):
            random.seed(714)
            # engine_once does NOT start a second tracer here; no snapshots inside GA.
            result,refs,_=engine_once('small',process,trace=False)
            signature=result['best_assignment_sha256']; result=None
            pre=trace_point(process); collected=gc.collect(); post=trace_point(process)
            records.append({'iteration':iteration+1,'seed':714,'phase2_output_matches':True,'best_assignment_sha256':signature,
                            'before_gc':pre,'after_gc':post,'gc_collected':collected,
                            'representative_model_weakrefs_alive_after_gc':sum(r() is not None for r in refs)})
        capture=tracemalloc.take_snapshot(); retained=allocation_rows(capture,baseline); del capture
        return {'status':'SUCCESS','scenario':'small','repetitions':repetitions,'before_tracing_process':before,
                'runs':records,'post_repetition_live_allocations':retained,
                'scope':'Same interpreter, same seed and original parameters; outputs dropped before GC. Not a long-term leak proof; retained numeric probe records and caches remain.'}
    finally:
        tracemalloc.stop(); random.setstate(rng)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--part',choices=['all','ram','alloc','focused','retention'],default='all')
    parser.add_argument('--scenario',choices=['all','small','medium','large'],default='all')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args(); verify_entry()
    if args.worker:
        result=retention() if args.part=='retention' else focused(args.scenario) if args.part=='focused' else full_run(args.scenario,args.part)
        print(json.dumps(result,allow_nan=False)); return 0
    started=datetime.now(ZONE); directory=BASE/started.strftime('%Y%m%dT%H%M%S%f+0800'); directory.mkdir(exist_ok=False)
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE',
         'APPDATA','LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','PATHEXT'}}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    parts=['ram','alloc','focused','retention'] if args.part=='all' else [args.part]
    names=['small','medium','large'] if args.scenario=='all' else [args.scenario]
    statuses=[]
    for part in parts:
        for name in ['small'] if part=='retention' else names:
            command=[sys.executable,'-B',str(Path(__file__).resolve()),'--worker','--part',part,'--scenario',name]
            start=datetime.now(ZONE).isoformat(); tick=time.perf_counter()
            try:
                reply=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=600)
                result=json.loads(reply.stdout) if reply.returncode==0 else {'status':'WORKER_FAILED','raw_error_withheld':True,'exit_code':reply.returncode}
            except subprocess.TimeoutExpired:result={'status':'WALL_DEADLINE_EXCEEDED','deadline_seconds':600}
            record={'part':part,'scenario':name,'started_at':start,'finished_at':datetime.now(ZONE).isoformat(),
                    'worker_wall_seconds':time.perf_counter()-tick,'command':command,'result':result}
            (directory/(part+'-'+name+'.json')).write_bytes((json.dumps(record,indent=2)+'\n').encode())
            statuses.append({'part':part,'scenario':name,'status':result['status']}); print(json.dumps(statuses[-1]),flush=True)
    record={'started_at':started.isoformat(),'finished_at':datetime.now(ZONE).isoformat(),'python':sys.version,
            'parameters_source':PHASE2.relative_to(ROOT).as_posix(),'parameters_source_sha256':sha(PHASE2),
            'statuses':statuses,'preserved_paths':verify_entry(),'database_operations':0,'production_symbols_replaced':0,
            'scope':'Fictional memory study; not timing baseline, optimization or institutional acceptance'}
    (directory/'summary.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
    print(json.dumps({'directory':directory.relative_to(ROOT).as_posix(),'status':'COMPLETE'}))
    return 0 if all(s['status']=='SUCCESS' for s in statuses) else 1


if __name__=='__main__':
    raise SystemExit(main())
