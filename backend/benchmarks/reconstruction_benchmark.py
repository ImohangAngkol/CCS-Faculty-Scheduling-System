"""Matched Phase 6 timing/profile/allocation experiments in private processes."""
import argparse
from contextlib import redirect_stderr,redirect_stdout,nullcontext
import copy
from datetime import datetime
import gc
import hashlib
import json
import os
from pathlib import Path
import pstats
import cProfile
import random
import subprocess
import sys
import threading
import time
import tracemalloc
import weakref

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from benchmarks.reconstruction_phase6 import Prototype,VARIANTS
from benchmarks.retention_runtime import runtime,data_guard,BOOTSTRAP
from benchmarks import memory_study as memory
from benchmarks.retention_phase5 import MemoryLimit
from benchmarks.scenarios import build,snapshot

BASE=ROOT/'docs/testing/ga-reconstruction-phase6'
PARAMETERS=dict(population_size=2,generations=1,fresh_chromosomes=0,crossover_attempts=1,mutation_attempts=1,max_restarts=5,candidate_attempts=3)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_entry():
    baseline=json.loads((BASE/'preservation-baseline.json').read_text())
    assert len(baseline)==1550 and all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in baseline.items()),'BASELINE_MISMATCH_STOP_NO_REPAIR'


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def profile_rows(profile):
    records=[]
    for (filename,line,function),(primitive,calls,own,cumulative,callers) in pstats.Stats(profile).stats.items():
        path=Path(filename)
        name=path.relative_to(ROOT).as_posix() if path.is_absolute() and path.is_relative_to(ROOT) else path.as_posix() if filename.startswith('phase6-experimental/') else path.name
        edges=[]
        for (parent_file,parent_line,parent),values in callers.items():
            parent_path=Path(parent_file)
            label=parent_path.relative_to(ROOT).as_posix() if parent_path.is_absolute() and parent_path.is_relative_to(ROOT) else parent_path.name
            edges.append({'file':label,'line':parent_line,'function':parent,'statistics':values})
        records.append({'file':name,'line':line,'function':function,'primitive_calls':primitive,'total_calls':calls,
                        'exclusive_seconds':own,'cumulative_seconds':cumulative,'callers':edges})
    for record in records:
        if record['function']=='payload_to_chromosome':
            assert {parent['function'] for parent in record['callers']}=={'validate_publication'},'PROFILE_CALLER_CONTRACT_FAILED'
            assert sum(parent['statistics'][1] for parent in record['callers'])==record['total_calls'],'PROFILE_COUNT_CONTRACT_FAILED'
        if record['function'] in ('admit','payload_to_chromosome','_validate_baseline_components','time_to_minutes'):
            assert not any(parent['file']=='threading.py' for parent in record['callers']),'PROFILE_THREAD_ATTRIBUTION_FAILED'
    return sorted(records,key=lambda row:row['cumulative_seconds'],reverse=True)


def execute(bundle,values,pinned,legacy,params,seed,mode,process):
    holder={};history=[]
    def boundary(state):
        history.append(dict(state['history'][-1]))
        if state['generation']==params.generations:holder['state']=state
        if mode=='profile':
            counters=process.read()
            assert counters['working_set_bytes']<=768*1048576 and counters['private_commit_bytes_NOT_RSS']<=1536*1048576,'PROFILE_MEMORY_LIMIT'
    random.seed(seed);gc.collect();before=process.read()
    profile=cProfile.Profile() if mode=='profile' else None
    if mode=='memory':tracemalloc.start(1)
    if profile:assert len(threading.enumerate())==1,'PROFILE_REQUIRES_SINGLE_PYTHON_THREAD'
    with (nullcontext(None) if profile else memory.Sampler(process)) as sampler:
        if profile:profile.enable()
        tick=time.perf_counter()
        assert bundle.run(values,pinned,params,legacy,boundary)=='complete'
        seconds=time.perf_counter()-tick
        if profile:profile.disable()
        engine_trace=memory.trace_point(process) if mode=='memory' else None
        after=process.read()
    return holder.pop('state'),{'engine_seconds':seconds,'process_before':before,'process_after':after,
        'process_sampling':sampler.result() if sampler else {'scope':'Foreground profile checkpoints only; background threads excluded after profiler canary'},'engine_allocation_point':engine_trace,
        'history':history,'profile':profile_rows(profile) if profile else None}


def verify_state(state,values,pinned,legacy):
    engine,fitness,scoring_inputs,*_=runtime()
    from services import ga_checkpoint_service as codec
    publication=engine.reduced_templates(pinned,values)
    for candidate in [*state['population'],state['best']]:engine.admit(candidate,pinned,publication)
    projection=dict(state)
    # REPORTING COMPARISON ONLY. Actual checkpoint identity is never changed.
    projection['engine_identity']='COMPARISON_ONLY_NOT_A_VALID_ENGINE_ID'
    signature=digest(memory.bench.signature(state['best']))
    availability_and_state=hashlib.sha256(codec.canonical(codec.encode_graph(projection))).hexdigest()
    token=scoring_inputs.set(state['scoring_inputs'])
    try:score,breakdown=fitness.faculty_preference_fitness(state['best'],legacy,return_breakdown=True)
    finally:scoring_inputs.reset(token)
    assert score==state['best_fitness']
    workload=memory.bench.workload(state['best'],values[1])
    assert all(b['best_ever_fitness']<=a['best_ever_fitness'] for a,b in zip(state['history'],state['history'][1:]))
    return {'assignment_sha256':signature,'state_availability_workload_aliases_sha256':availability_and_state,
            'history':state['history'],'final_fitness':score,'fitness_breakdown':breakdown,'workload':workload,
            'final_rng_sha256':digest(state['random_state']),'hard_constraints':'PASS: original admit on every final member and best',
            'scope':'Full graph projection normalizes only the distinct experimental engine identity for comparison; no validation/continuation identity is spoofed'}


def worker(config):
    verify_entry();rng=random.getstate();threshold=gc.get_threshold();enabled=gc.isenabled()
    process=memory.ProcessMemory();stream=sys.stdout;mode=config['mode']
    try:
        runtime();values,legacy,rows,settings,metadata=build(config['scenario']);pinned=snapshot(values,metadata)
        parameters=json.loads(memory.PHASE2.read_text())['parameters'] if mode=='reference' else PARAMETERS
        params=runtime()[-1](**parameters);bundle=Prototype(config['variant'],collect=mode=='profile')
        with memory.bench.synthetic_scoring(values,rows,settings),data_guard(),(nullcontext() if mode=='profile' else MemoryLimit(process,stream)),open(os.devnull,'w') as sink,redirect_stdout(sink),redirect_stderr(sink),memory.bench.no_io():
            warm=None
            if mode!='reference':
                state,measurement=execute(bundle,values,pinned,legacy,params,config['seed'],'timing',process)
                warm=verify_state(state,values,pinned,legacy);warm['engine_seconds']=measurement['engine_seconds']
                state=None;measurement=None;gc.collect()
                if bundle.stats is not None:bundle.stats.clear()
            state,measurement=execute(bundle,values,pinned,legacy,params,config['seed'],mode,process)
            gc.collect();verify_started=time.perf_counter();outcome=verify_state(state,values,pinned,legacy)
            verify_seconds=time.perf_counter()-verify_started
            if warm is not None:
                assert all(outcome[k]==warm[k] for k in ('assignment_sha256','state_availability_workload_aliases_sha256','history','final_rng_sha256'))
            if mode=='reference':
                reference=json.loads(memory.PHASE2.read_text())['results'][config['scenario']]['trials'][0]
                assert outcome['assignment_sha256']==reference['best_assignment_sha256'] and outcome['history']==reference['history']
            copy_control=None
            if mode=='memory':
                # Engine peak captured earlier. Separate incremental COPY control,
                # with the existing best held as input and no changed copy logic.
                gc.collect();initial=tracemalloc.get_traced_memory()[0];tracemalloc.reset_peak()
                cloned=copy.deepcopy(state['best'])
                current,peak=tracemalloc.get_traced_memory()
                copy_control={'incremental_live_bytes':current-initial,'incremental_peak_bytes':max(0,peak-initial),
                              'scope':'Original deepcopy only; separate from saved engine peak, input best remains held'}
                assert digest(memory.bench.signature(cloned))==outcome['assignment_sha256'];cloned=None;gc.collect()
            subject=state['best'][0]
            refs=[weakref.ref(subject),weakref.ref(subject.assigned_faculty),weakref.ref(subject.lecture_room)]
            subject=None;state=None;gc.collect()
            retained=memory.trace_point(process) if mode=='memory' else None
            snapshots=None
            if mode=='memory':
                capture=tracemalloc.take_snapshot();snapshots=memory.allocation_rows(capture);del capture
                tracemalloc.stop()
            assert all(ref() is None for ref in refs)
            result={'status':'SUCCESS','config':config,'parameters':parameters,'provenance':bundle.provenance(),
                    'warmup_excluded':warm,'measurement':measurement,'correctness':outcome,
                    'post_verification_seconds_excluded':verify_seconds,'transient_copy_control':copy_control,
                    'post_release':retained,'post_release_live_allocations':snapshots,
                    'sampled_model_weakrefs_alive':0,'cache_diagnostics_profile_only':dict(bundle.stats) if bundle.stats is not None else None,
                    'bootstrap':dict(BOOTSTRAP),'production_GC_allocator_settings_changed':False,'database_or_publication_operations':0}
        assert gc.get_threshold()==threshold and gc.isenabled()==enabled
        return result
    finally:
        if tracemalloc.is_tracing():tracemalloc.stop()
        random.setstate(rng)


def matrix(part):
    jobs=[]
    for scenario in ('small','medium','large'):
        if part=='baseline-profile':
            jobs.append(dict(mode='profile',scenario=scenario,variant='baseline',seed=714,repetition=1));continue
        if part in ('reference','profile'):
            for variant in VARIANTS:jobs.append(dict(mode=part,scenario=scenario,variant=variant,seed=714,repetition=1))
        if part=='timing':
            for repetition in (1,2):
                for index,seed in enumerate((714,715,716)):
                    order=list(VARIANTS);offset=(index+repetition)%3;order=order[offset:]+order[:offset]
                    for variant in order:jobs.append(dict(mode='timing',scenario=scenario,variant=variant,seed=seed,repetition=repetition))
        if part=='memory':
            for index,seed in enumerate((714,715,716)):
                order=list(VARIANTS);order=order[index:]+order[:index]
                for variant in order:jobs.append(dict(mode='memory',scenario=scenario,variant=variant,seed=seed,repetition=1))
    return jobs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--part',choices=['baseline-profile','reference','profile','timing','memory'],default='baseline-profile')
    parser.add_argument('--worker',help=argparse.SUPPRESS)
    args=parser.parse_args();verify_entry()
    if args.worker:
        print(json.dumps(worker(json.loads(args.worker)),allow_nan=False));return 0
    directory=BASE/(datetime.now(memory.ZONE).strftime('%Y%m%dT%H%M%S%f+0800')+'-'+args.part);directory.mkdir(exist_ok=False)
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','PATHEXT'}}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    results=[];comparisons={}
    for index,config in enumerate(matrix(args.part)):
        started=datetime.now(memory.ZONE);tick=time.perf_counter()
        try:
            reply=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--worker',json.dumps(config)],cwd=ROOT,env=env,
                                 capture_output=True,text=True,encoding='utf-8',timeout=600)
            result=json.loads(reply.stdout) if reply.returncode==0 else {'status':'STOP_REVIEW_REQUIRED','diagnostic':json.loads(reply.stdout) if reply.stdout.startswith('{') else None,'raw_error_withheld':True}
        except subprocess.TimeoutExpired:result={'status':'WALL_DEADLINE_EXCEEDED','deadline_seconds':600}
        if result['status']=='SUCCESS':
            key=(config['scenario'],config['seed'],json.dumps(result['parameters'],sort_keys=True))
            comparison={field:result['correctness'][field] for field in ('assignment_sha256','state_availability_workload_aliases_sha256','history','final_fitness','fitness_breakdown','workload','final_rng_sha256')}
            if key in comparisons and comparisons[key]!=comparison:
                result['status']='DIFFERENTIAL_MISMATCH';result['different_fields']=[field for field in comparison if comparisons[key][field]!=comparison[field]]
            else:comparisons[key]=comparison
        name=f"{index:03}-{config['scenario']}-{config['variant']}-{config['seed']}-r{config['repetition']}.json"
        record={'started_at':started.isoformat(),'finished_at':datetime.now(memory.ZONE).isoformat(),
                'worker_wall_seconds':time.perf_counter()-tick,'config':config,'result':result}
        (directory/name).write_bytes((json.dumps(record,indent=2)+'\n').encode())
        status=dict(config,status=result['status']);results.append(status);print(json.dumps(status),flush=True)
        if result['status']!='SUCCESS':break
    (directory/'summary.json').write_bytes((json.dumps({'part':args.part,'results':results},indent=2)+'\n').encode())
    print(directory.relative_to(ROOT).as_posix())
    return 0 if all(r['status']=='SUCCESS' for r in results) else 1


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        import traceback
        print(json.dumps({'status':'HARNESS_EXCEPTION','exception_type':type(error).__name__,
            'frames':[{'file':Path(f.filename).name,'line':f.lineno,'function':f.name} for f in traceback.extract_tb(error.__traceback__)],
            'message_withheld':True}),flush=True)
        raise SystemExit(1)
