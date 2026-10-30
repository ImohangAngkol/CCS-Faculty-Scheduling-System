"""Separate operation-level allocation controls on an identical fictional best."""
from contextlib import redirect_stdout,redirect_stderr
import copy
from datetime import datetime
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

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from benchmarks.reconstruction_benchmark import BASE,PARAMETERS,verify_entry,verify_state
from benchmarks.reconstruction_phase6 import Prototype,VARIANTS
from benchmarks.retention_runtime import runtime,data_guard
from benchmarks import memory_study as memory
from benchmarks.scenarios import build,snapshot


def worker(scenario,variant):
    verify_entry();before_rng=random.getstate();runtime()
    from services import chromosome_service as chromosome,ga_checkpoint_service as codec
    engine,fitness,scoring_inputs,*_=runtime()
    values,legacy,rows,settings,metadata=build(scenario);pinned=snapshot(values,metadata)
    params=runtime()[-1](**PARAMETERS);bundle=Prototype(variant);holder={}
    process=memory.ProcessMemory()
    try:
        with memory.bench.synthetic_scoring(values,rows,settings),data_guard(),open(os.devnull,'w') as sink,redirect_stdout(sink),redirect_stderr(sink),memory.bench.no_io():
            random.seed(714);warm_start=time.perf_counter()
            bundle.run(values,pinned,params,legacy,lambda state:holder.update(state=state))
            warm_seconds=time.perf_counter()-warm_start
            state=holder.pop('state');best=state['best']
            expected=verify_state(state,values,pinned,legacy)
            plain=[]
            for _ in range(3):
                state=None;best=None;gc.collect();random.seed(714)
                assert not tracemalloc.is_tracing() and sys.getprofile() is None and len(threading.enumerate())==1
                before=process.read();tick=time.perf_counter()
                bundle.run(values,pinned,params,legacy,lambda current:holder.update(state=current))
                seconds=time.perf_counter()-tick;after=process.read()
                state=holder.pop('state');best=state['best']
                assert verify_state(state,values,pinned,legacy)==expected
                assert after['working_set_bytes']<=768*1048576 and after['private_commit_bytes_NOT_RSS']<=1536*1048576
                plain.append({'engine_seconds':seconds,'process_before':before,'process_after':after})
            publication=engine.reduced_templates(pinned,values)
            encoded=codec.canonical(codec.encode_graph(state));rng=random.getstate()
            payload=chromosome.chromosome_to_payload(best,0)
            def evaluate():
                token=scoring_inputs.set(state['scoring_inputs'])
                try:return fitness.faculty_preference_fitness(best,legacy,return_breakdown=True)
                finally:scoring_inputs.reset(token)
            operations={'component_validation':lambda:bundle.validate_components(best),
                'payload_reconstruction':lambda:bundle.payload(payload,*publication),
                'candidate_admission':lambda:bundle.admit(best,pinned,publication),
                'fitness_evaluation_original':evaluate,'deepcopy_original':lambda:copy.deepcopy(best)}
            records={}
            for name,function in operations.items():
                function();gc.collect()  # operation warm-up, output not retained
                controls=[]
                for _ in range(3):
                    counters=process.read()
                    assert counters['working_set_bytes']<=768*1048576 and counters['private_commit_bytes_NOT_RSS']<=1536*1048576
                    gc.collect();process_before=process.read();tick=time.perf_counter();value=function();seconds=time.perf_counter()-tick
                    value=None;gc.collect()
                    tracemalloc.start(1);tick=time.perf_counter();value=function();trace_seconds=time.perf_counter()-tick
                    current,peak=tracemalloc.get_traced_memory();trace_metadata=tracemalloc.get_tracemalloc_memory()
                    del value;gc.collect();retained=tracemalloc.get_traced_memory()[0];tracemalloc.stop()
                    controls.append({'uninstrumented_seconds':seconds,'traced_seconds_NOT_wall_baseline':trace_seconds,
                        'traced_peak_bytes_NOT_RSS':peak,'traced_current_return_held_bytes':current,'post_release_GC_traced_bytes':retained,
                        'tracer_metadata_bytes':trace_metadata,'process_before':process_before,'process_after':process.read()})
                records[name]=controls
                assert codec.canonical(codec.encode_graph(state))==encoded and random.getstate()==rng
            return {'status':'SUCCESS','scenario':scenario,'variant':variant,'seed':714,'parameters':PARAMETERS,
                    'correctness':expected,'operations':records,'full_input_graph_and_rng_unchanged':True,
                    'admission_diagnostics':dict(state['diagnostics']),
                    'unobserved_engine_controls':plain,'excluded_engine_warmup_seconds':warm_seconds,
                    'scope':'One seed per fresh variant/scale worker. Three warm engine repetitions with no sampler/watchdog Python threads, profiler or tracer; separately three operation repetitions. No timing categories pooled.'}
    finally:
        if tracemalloc.is_tracing():tracemalloc.stop()
        random.setstate(before_rng)


def main():
    if len(sys.argv)==4 and sys.argv[1]=='--worker':
        print(json.dumps(worker(*sys.argv[2:]),allow_nan=False));return 0
    verify_entry();directory=BASE/(datetime.now(memory.ZONE).strftime('%Y%m%dT%H%M%S%f+0800')+'-operations');directory.mkdir(exist_ok=False)
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','PATHEXT'}}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    comparisons={};results=[]
    for scenario in ('small','medium','large'):
        for variant in VARIANTS:
            started=datetime.now(memory.ZONE);tick=time.perf_counter()
            try:
                reply=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--worker',scenario,variant],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=300)
                result=json.loads(reply.stdout) if reply.returncode==0 else {'status':'WORKER_FAILED','raw_error_withheld':True}
            except subprocess.TimeoutExpired:result={'status':'WALL_DEADLINE_EXCEEDED','deadline_seconds':300}
            if result['status']=='SUCCESS':
                key=scenario;fingerprint=result['correctness']
                if key in comparisons:assert comparisons[key]==fingerprint
                else:comparisons[key]=fingerprint
            record={'started_at':started.isoformat(),'finished_at':datetime.now(memory.ZONE).isoformat(),'worker_wall_seconds':time.perf_counter()-tick,'result':result}
            (directory/(scenario+'-'+variant+'.json')).write_bytes((json.dumps(record,indent=2)+'\n').encode())
            row={'scenario':scenario,'variant':variant,'status':result['status']};results.append(row);print(json.dumps(row),flush=True)
            if result['status']!='SUCCESS':break
        if results[-1]['status']!='SUCCESS':break
    (directory/'summary.json').write_bytes((json.dumps({'part':'operations','results':results},indent=2)+'\n').encode())
    print(directory.relative_to(ROOT).as_posix());return 0 if len(results)==9 and all(r['status']=='SUCCESS' for r in results) else 1


if __name__=='__main__':raise SystemExit(main())
