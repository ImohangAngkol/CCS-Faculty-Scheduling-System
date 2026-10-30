"""Separate post-GC score-observer retention diagnostic; no GA modification.

Both cases intentionally clone three fictional chromosomes before original
scoring. Compare reachable live data after GC, not pre-GC allocation churn.
"""
from contextlib import redirect_stderr,redirect_stdout
from datetime import datetime
import copy
import gc
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tracemalloc
import weakref

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmarks import memory_study as memory
from benchmarks.scenarios import build,snapshot


def compare(name):
    engine,fitness,scoring_inputs,*_=memory.bench.runtime()
    from genetic_algorithm.utils.FitnessObservation import observed_scores
    rng=random.getstate(); process=memory.ProcessMemory()
    try:
        values,legacy,preferences,settings,metadata=build(name)
        with memory.bench.synthetic_scoring(values,preferences,settings),open(os.devnull,'w') as sink,redirect_stdout(sink),redirect_stderr(sink),memory.bench.no_io():
            random.seed(10101); pinned=snapshot(values,metadata); working=engine.reduced_templates(pinned,values)
            candidate=engine.construct(working,5); engine.admit(candidate,pinned,working)
            token=scoring_inputs.set(engine.freeze(values))
            try:
                expected=fitness.faculty_preference_fitness(candidate,legacy); records=[]
                for enabled in (False,True):
                    gc.collect(); scores={} if enabled else None; refs=[]; scope=observed_scores.set(scores)
                    tracemalloc.start(8)
                    try:
                        baseline=tracemalloc.take_snapshot()
                        for _ in range(3):
                            cloned=copy.deepcopy(candidate); refs.append(weakref.ref(cloned[0]))
                            assert fitness.faculty_preference_fitness(cloned,legacy)==expected
                        del cloned
                        pre=memory.trace_point(process); gc.collect(); held=memory.trace_point(process)
                        alive_held=sum(r() is not None for r in refs)
                        capture=tracemalloc.take_snapshot(); allocations=memory.allocation_rows(capture,baseline)
                        del capture,baseline
                        if scores is not None:scores.clear()
                        gc.collect(); released=memory.trace_point(process)
                        alive_after=sum(r() is not None for r in refs)
                    finally:
                        tracemalloc.stop(); observed_scores.reset(scope)
                    records.append({'observer_enabled':enabled,'copies_scored':3,'before_gc':pre,'after_gc_result_kept':held,
                                    'representative_clones_alive_after_gc_result_kept':alive_held,
                                    'after_observer_clear_gc':released,'representative_clones_alive_after_clear_gc':alive_after,
                                    'live_allocations_result_kept':allocations})
                assert records[0]['representative_clones_alive_after_gc_result_kept']==0
                assert records[1]['representative_clones_alive_after_gc_result_kept']==3
                assert all(r['representative_clones_alive_after_clear_gc']==0 for r in records)
                return {'scenario':name,'status':'SUCCESS','cases':records,
                        'scope':'Explicit optional observer experiment; direct V2 benchmark leaves this observer disabled. Strong references while enabled are intentional, not a demonstrated production leak.'}
            finally:scoring_inputs.reset(token)
    finally:
        if tracemalloc.is_tracing():tracemalloc.stop()
        random.setstate(rng)


def main():
    memory.verify_entry()
    if len(sys.argv)==3 and sys.argv[1]=='--worker':
        print(json.dumps(compare(sys.argv[2]),allow_nan=False)); return 0
    directory=memory.BASE/(datetime.now(memory.ZONE).strftime('%Y%m%dT%H%M%S%f+0800')+'-observer-followup')
    directory.mkdir(exist_ok=False)
    record={'scope':'Post-GC diagnostic complements, does not overwrite focused pre-GC snapshots','results':{}}
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE',
         'APPDATA','LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','PATHEXT'}}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    for name in ('small','medium','large'):
        try:
            reply=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--worker',name],cwd=memory.ROOT,
                                 env=env,capture_output=True,text=True,encoding='utf-8',timeout=300)
            result=json.loads(reply.stdout) if reply.returncode==0 else {'status':'WORKER_FAILED','raw_error_withheld':True}
        except subprocess.TimeoutExpired:result={'status':'WALL_DEADLINE_EXCEEDED','deadline_seconds':300}
        record['results'][name]=result
        print(json.dumps({'scenario':name,'status':result['status']}),flush=True)
    memory.verify_entry()
    (directory/'observer.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
    print(directory.relative_to(memory.ROOT).as_posix())
    return 0 if all(r['status']=='SUCCESS' for r in record['results'].values()) else 1


if __name__=='__main__':
    raise SystemExit(main())
