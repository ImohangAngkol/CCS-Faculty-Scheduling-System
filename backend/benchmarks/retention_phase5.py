"""Bounded Phase 5 retention/ownership experiments, not production optimization."""
import argparse
from collections import Counter
from contextlib import redirect_stderr,redirect_stdout
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
from datetime import datetime

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from benchmarks.retention_runtime import runtime,data_guard,BOOTSTRAP
from benchmarks import memory_study as memory
from benchmarks.scenarios import build,snapshot

BASE=ROOT/'docs/testing/ga-retention-phase5'
PARAMETERS=dict(population_size=2,generations=1,fresh_chromosomes=1,crossover_attempts=1,mutation_attempts=1,max_restarts=5,candidate_attempts=3)
MODEL_TYPES={'Subject','Faculty','Room','Section','TimeBlock'}


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def verify_entry():
    baseline=json.loads((BASE/'preservation-baseline.json').read_text())
    if not all((ROOT/p).is_file() and memory.sha(ROOT/p)==h for p,h in baseline.items()):
        raise RuntimeError('BASELINE_MISMATCH_STOP_NO_REPAIR')
    return len(baseline)


class Lease:
    """Weak-referenceable reporting root; actual chromosomes remain plain lists."""
    def __init__(self,state):self.state=state


def model_counts():
    # Aggregate class counts only; no names, values or arbitrary referrer dumps.
    counts=Counter(type(obj).__name__ for obj in gc.get_objects()
                   if isinstance(type(obj).__module__,str) and type(obj).__module__.startswith('genetic_algorithm.models.')
                   and type(obj).__name__ in MODEL_TYPES)
    return {name:counts[name] for name in sorted(MODEL_TYPES)}


def point(process):
    result={'process':process.read(),'model_counts':model_counts(),'gc_counts':gc.get_count()}
    if tracemalloc.is_tracing():
        current,peak=tracemalloc.get_traced_memory()
        result.update(traced_current_bytes=current,traced_peak_bytes_NOT_RSS=peak,tracer_metadata_bytes=tracemalloc.get_tracemalloc_memory())
    return result


class MemoryLimit:
    """Read-only OS counter watchdog; exits only its own private worker.

    No working-set trimming, GC disabling or allocator settings. Polling can
    overshoot; completed public JSON lines survive worker termination.
    """
    def __init__(self,process,stream,working=768*1048576,private=1536*1048576):
        self.process=process;self.stream=stream;self.working=working;self.private=private
        self.stop=threading.Event();self.peak=0;self.samples=0
    def run(self):
        while not self.stop.wait(.05):
            try:value=self.process.read()
            except Exception:
                self.stream.write(json.dumps({'event':'MEMORY_GUARD_QUERY_FAILED'})+'\n');self.stream.flush();os._exit(89)
            self.samples+=1;self.peak=max(self.peak,value['working_set_bytes'])
            if value['working_set_bytes']>self.working or value['private_commit_bytes_NOT_RSS']>self.private:
                self.stream.write(json.dumps({'event':'MEMORY_LIMIT_EXCEEDED','process':value})+'\n');self.stream.flush()
                os._exit(88)
    def __enter__(self):
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start();return self
    def __exit__(self,*args):
        self.stop.set();self.thread.join(timeout=2)


def execute(values,pinned,legacy,params,seed,process,policy='retain_last',reference=False,light=False):
    engine=runtime()[0];last=None;history=[];sampled=[];lease_refs=[];during=[]
    def callback(state):
        nonlocal last
        history.append(dict(state['history'][-1]))
        candidate=state['best'];subject=candidate[0]
        for obj in (subject,subject.assigned_faculty,subject.lecture_room,subject.lecture_time_blocks[0][1]):
            sampled.append((type(obj).__name__,weakref.ref(obj)))
        # Explicit experimental reporting ownership only. Never change engine best.
        if policy=='retain_last' or state['generation']==params.generations:
            last=Lease(state);lease_refs.append(weakref.ref(last))
        during.append({'generation':state['generation'],**({} if light else point(process))})
    random.seed(seed);tick=time.perf_counter()
    assert engine.run(values,pinned,params,legacy,callback)=='complete'
    elapsed=time.perf_counter()-tick;final=last.state
    # All final population candidates plus best pass the original hard gate.
    publication=engine.reduced_templates(pinned,values)
    for candidate in [*final['population'],final['best']]:engine.admit(candidate,pinned,publication)
    assignments=memory.bench.signature(final['best'])
    signature=digest(assignments)
    assert all(b['best_ever_fitness']<=a['best_ever_fitness'] for a,b in zip(history,history[1:]))
    if reference:
        baseline=json.loads(memory.PHASE2.read_text())['results'][reference]['trials'][0]
        assert signature==baseline['best_assignment_sha256'] and history==baseline['history']
    return {'seed':seed,'best_assignment_sha256':signature,'history':history,'final_fitness':final['best_fitness'],
            'final_rng_sha256':digest(random.getstate()),'hard_constraints':'PASS: every final population member and best',
            'engine_seconds_with_instrumentation':elapsed,'during':during,
            'chromosome_root_tracking':'Plain lists do not support weakref; reporting Lease proxies plus model weakrefs are sampled'},sampled,lease_refs


def released(samples,leases):
    counts=Counter(kind for kind,ref in samples if ref() is not None)
    return {'sampled_models_alive':dict(counts),'sampled_model_count_alive':sum(counts.values()),
            'reporting_leases_alive':sum(ref() is not None for ref in leases)}


def run_series(config,stream):
    process=memory.ProcessMemory();cold=process.read();rng=random.getstate()
    runtime();engine,fitness,scoring_inputs,*_=runtime()
    from genetic_algorithm.utils.FitnessObservation import observed_scores
    values,legacy,rows,settings,metadata=build(config['scenario']);pinned=snapshot(values,metadata)
    params=runtime()[-1](**(json.loads(memory.PHASE2.read_text())['parameters'] if config.get('reference') else PARAMETERS))
    records=[];reference_outputs={}
    try:
        with memory.bench.synthetic_scoring(values,rows,settings),data_guard(),MemoryLimit(process,stream) as guard:
            def trial(seed,label,observer):
                scores={} if observer else None;scope=observed_scores.set(scores)
                gc.collect()
                if tracemalloc.is_tracing():tracemalloc.reset_peak()
                before=point(process)
                try:
                    with open(os.devnull,'w') as sink,redirect_stdout(sink),redirect_stderr(sink),memory.bench.no_io():
                        result,samples,leases=execute(values,pinned,legacy,params,seed,process,config.get('policy','retain_last'),
                                                      config['scenario'] if config.get('reference') else False,config.get('light',False))
                    result.update(label=label,observer_enabled=observer,before=before,before_gc=point(process))
                    gc.collect();result['after_gc_while_observer_held']=point(process)
                    result['roots_while_observer_held']=released(samples,leases)
                    result['observed_candidate_roots']=len(scores) if scores is not None else 0
                    if scores is not None:scores.clear()
                finally:observed_scores.reset(scope)
                gc.collect();result['after_release_gc']=point(process);result['released_roots']=released(samples,leases)
                assert result['released_roots']['sampled_model_count_alive']==0
                assert result['released_roots']['reporting_leases_alive']==0
                key=(result['best_assignment_sha256'],result['history'],result['final_rng_sha256'])
                if seed in reference_outputs:assert reference_outputs[seed]==key
                else:reference_outputs[seed]=key
                records.append(result)
                stream.write(json.dumps({'event':'run','record':result})+'\n');stream.flush()
            for seed in config['warmup']:trial(seed,'warmup',False)
            gc.collect();warm_baseline=point(process)
            if config['trace']:tracemalloc.start(1)
            baseline=tracemalloc.take_snapshot() if config['trace'] else None
            if config['trace']:warm_baseline=point(process)
            for seed in config['seeds']:trial(seed,'measured',config.get('observer',False))
            end=point(process)
            report_release=None
            if config.get('drop_reports'):
                retained_run_records=len(records)
                records.clear();reference_outputs.clear();gc.collect()
                report_release={'released_worker_run_records':retained_run_records,'after_drop_gc':point(process),
                                'scope':'Already streamed diagnostic records only; no GA object/pruning or best-ever change'}
            allocation=None
            if config['trace']:
                capture=tracemalloc.take_snapshot();allocation=memory.allocation_rows(capture,baseline);del capture,baseline
                tracemalloc.stop()
            summary={'event':'summary','status':'SUCCESS','config':config,'parameters':params.model_dump(),
                     'cold_process':cold,'post_warmup_baseline':warm_baseline,'end':end,'post_gc_live_differences':allocation,
                     'bootstrap':dict(BOOTSTRAP),'sampled_worker_peak_working_set_bytes':guard.peak,
                     'report_buffer_release':report_release,
                     'sample_count':guard.samples,'working_set_limit_bytes':guard.working,'private_commit_limit_bytes':guard.private,
                     'scope':'Probe dictionaries/history/digests remain retained; snapshots are net live, not allocation churn. GC forced only between runs, not inside GA.'}
            stream.write(json.dumps(summary)+'\n');stream.flush()
    finally:
        if tracemalloc.is_tracing():tracemalloc.stop()
        random.setstate(rng)


def matrix(part):
    jobs=[]
    def add(name,scenario,seeds,warmup=(714,715),trace=False,**extra):
        jobs.append(dict(name=name,scenario=scenario,seeds=list(seeds),warmup=list(warmup),trace=trace,**extra))
    if part in ('all','reference'):
        for name in ('small','medium','large'):add('reference-'+name,name,[714],warmup=(),reference=True)
    if part in ('all','retention'):
        for name in ('small','medium'):
            for cohort in ('A','B'):
                add('ram-'+name+'-'+cohort,name,[714]*6+[715,716,717,718,715,716],cohort=cohort)
            add('trace-'+name,name,[714]*3+[715,716,717],trace=True)
            add('observer-'+name,name,[714,715,716],warmup=(714,),trace=True,observer=True)
        add('ram-large','large',[714,715],warmup=(714,))
        add('trace-large','large',[714],warmup=(714,),trace=True)
        for name in ('small','medium'):
            add('light-'+name,name,[714]*3+[715]*3,light=True)
    if part=='ownership':
        for name in ('small','medium'):
            for policy in ('retain_last','final_only'):
                add('ownership-'+name+'-'+policy,name,[714,715],trace=True,policy=policy,drop_reports=True)
    return jobs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--part',choices=['all','reference','retention','ownership'],default='all')
    parser.add_argument('--worker',help=argparse.SUPPRESS)
    args=parser.parse_args();verify_entry()
    if args.worker:
        run_series(json.loads(args.worker),sys.stdout);return 0
    directory=BASE/datetime.now(memory.ZONE).strftime('%Y%m%dT%H%M%S%f+0800');directory.mkdir(exist_ok=False)
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE',
         'APPDATA','LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','PATHEXT'}}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    summaries=[]
    for job in matrix(args.part):
        start=datetime.now(memory.ZONE);tick=time.perf_counter()
        command=[sys.executable,'-B',str(Path(__file__).resolve()),'--worker',json.dumps(job)]
        try:
            reply=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=900)
            events=[]
            for line in reply.stdout.splitlines():
                try:events.append(json.loads(line))
                except json.JSONDecodeError:pass
            status='SUCCESS' if reply.returncode==0 and events and events[-1].get('status')=='SUCCESS' else 'STOP_REVIEW_REQUIRED'
            exit_code=reply.returncode
        except subprocess.TimeoutExpired as error:
            events=[];status='WALL_DEADLINE_EXCEEDED';exit_code=None
            raw=error.stdout.decode() if isinstance(error.stdout,bytes) else error.stdout or ''
            for line in raw.splitlines():
                try:events.append(json.loads(line))
                except json.JSONDecodeError:pass
        record={'started_at':start.isoformat(),'finished_at':datetime.now(memory.ZONE).isoformat(),'status':status,
                'exit_code':exit_code,'worker_wall_seconds':time.perf_counter()-tick,'config':job,'events':events,
                'raw_error_withheld':status!='SUCCESS','worker_deadline_seconds':900}
        (directory/(job['name']+'.json')).write_bytes((json.dumps(record,indent=2)+'\n').encode())
        summaries.append({'name':job['name'],'status':status})
        print(json.dumps(summaries[-1]),flush=True)
        if status!='SUCCESS':break
    summary={'part':args.part,'jobs':summaries,'baseline_preserved':verify_entry(),'database_operations':0,
             'production_GC_or_allocator_settings_changed':False,'parameters':PARAMETERS}
    (directory/'summary.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
    print(directory.relative_to(ROOT).as_posix())
    return 0 if all(j['status']=='SUCCESS' for j in summaries) else 1


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        import traceback
        frames=[{'file':Path(f.filename).name,'line':f.lineno,'function':f.name} for f in traceback.extract_tb(error.__traceback__)]
        print(json.dumps({'event':'HARNESS_EXCEPTION','exception_type':type(error).__name__,'frames':frames,'message_withheld':True}),flush=True)
        raise SystemExit(1)
