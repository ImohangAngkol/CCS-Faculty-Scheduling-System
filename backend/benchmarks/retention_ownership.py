"""Copy independence and original in-memory checkpoint/resume verification."""
import copy
import gc
import hashlib
from contextlib import redirect_stderr,redirect_stdout
from datetime import datetime
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import weakref

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmarks import retention_phase5 as study
from benchmarks.retention_runtime import runtime,data_guard
from benchmarks.scenarios import build,snapshot


def mutable_nodes(root):
    pending=[root];seen=set();mutable=set();edges={}
    while pending:
        value=pending.pop();identifier=id(value)
        if identifier in seen:continue
        seen.add(identifier);kind=type(value)
        if kind in (list,dict,set):mutable.add(identifier)
        if kind is dict:pending.extend(value.keys());pending.extend(value.values())
        elif kind in (list,tuple,set,frozenset):pending.extend(value)
        elif isinstance(kind.__module__,str) and kind.__module__.startswith('genetic_algorithm.models.'):
            mutable.add(identifier);attributes=vars(value);pending.append(attributes)
            for name,child in attributes.items():
                if type(child).__name__ in {'Faculty','Subject','Room','Section','TimeBlock'}:
                    key=kind.__name__+'.'+name+'->'+type(child).__name__
                    edges[key]=edges.get(key,0)+1
                elif type(child) in (list,dict,set,tuple):
                    key=kind.__name__+'.'+name+'->'+type(child).__name__
                    edges[key]=edges.get(key,0)+1
    return mutable,edges


def verify(name):
    rng=random.getstate();engine=runtime()[0]
    from services import ga_checkpoint_service as codec
    from services.ga_v2_constraints import ConstraintError
    values,legacy,rows,settings,meta=build(name);pinned=snapshot(values,meta)
    params=runtime()[-1](**study.PARAMETERS)
    try:
        with study.memory.bench.synthetic_scoring(values,rows,settings),data_guard(),open(os.devnull,'w') as sink,redirect_stdout(sink),redirect_stderr(sink),study.memory.bench.no_io():
            holder={}
            def final(state):holder['state']=state
            random.seed(714);assert engine.run(values,pinned,params,legacy,final)=='complete'
            expected=holder.pop('state');expected_rng=study.digest(random.getstate())
            expected_signature=study.digest(study.memory.bench.signature(expected['best']))
            expected_history=copy.deepcopy(expected['history'])
            best=expected['best'];cloned=copy.deepcopy(best)
            source_ids,edges=mutable_nodes(best);clone_ids,_=mutable_nodes(cloned)
            assert not source_ids&clone_ids
            original_signature=study.digest(study.memory.bench.signature(best))
            source_block=best[0].lecture_time_blocks[0][1];clone_block=cloned[0].lecture_time_blocks[0][1]
            assert clone_block is not source_block and clone_block.subject is cloned[0]
            assert clone_block.faculty is cloned[0].assigned_faculty
            prior=clone_block.is_available;clone_block.is_available=not prior
            assert source_block.is_available==prior
            clone_block.is_available=prior
            marker=object();before=len(best[0].assigned_faculty.subjects_assigned)
            cloned[0].assigned_faculty.subjects_assigned.append(marker)
            assert len(best[0].assigned_faculty.subjects_assigned)==before
            cloned[0].assigned_faculty.subjects_assigned.pop()
            publication=engine.reduced_templates(pinned,values);engine.admit(cloned,pinned,publication)
            assert study.digest(study.memory.bench.signature(best))==original_signature
            population_ids,_=mutable_nodes(expected['population'])
            assert not source_ids&population_ids
            # Capture a real original-engine checkpoint at generation zero.
            paused_refs=[]
            def pause(state):
                paused_refs.append(weakref.ref(state['best'][0]))
                # Isolated callback prototype: encode immediately, keep bytes,
                # release the model graph after returning. Original codec only.
                holder['encoded']=codec.canonical(codec.encode_graph(state))
                return 'pause'
            random.seed(714);assert engine.run(values,pinned,params,legacy,pause)=='pause'
            encoded=holder.pop('encoded');gc.collect()
            assert all(ref() is None for ref in paused_refs)
            restored=codec.decode_graph(json.loads(encoded))
            engine.validate_state(restored,pinned,values)
            bad=copy.deepcopy(restored);bad['engine_identity']='0'*64
            try:engine.validate_state(bad,pinned,values)
            except ConstraintError as error:assert error.code=='V2_CHECKPOINT_INCOMPATIBLE'
            else:raise AssertionError('Strict fingerprint rejection did not occur')
            random.seed(999);assert engine.run(values,pinned,params,legacy,final,state=restored)=='complete'
            resumed=holder.pop('state')
            assert study.digest(study.memory.bench.signature(resumed['best']))==expected_signature
            assert resumed['history']==expected_history and study.digest(random.getstate())==expected_rng
            assert resumed['best_fitness']==expected['best_fitness']
            return {'status':'SUCCESS','scenario':name,'seed':714,'parameters':params.model_dump(),
                    'mutable_original_clone_intersection':0,'mutable_best_population_intersection':0,
                    'copy_internal_subject_faculty_aliases_preserved':True,'mutation_isolation':True,
                    'source_graph_mutable_nodes':len(source_ids),'observed_model_edges':edges,
                    'best_assignment_sha256':expected_signature,'history':expected_history,
                    'original_encoded_graph_sha256':hashlib.sha256(encoded).hexdigest(),
                    'in_memory_checkpoint_continuation':'EXACT assignments, history, final fitness and RNG state',
                    'fingerprint_tampering':'REJECTED by original validate_state',
                    'encoded_callback_released_paused_model_roots':True,
                    'checkpoint_files_written':0,'production_checkpoints_opened':0,
                    'scope':'Original graph codec/validator/continuation; in-memory fictional state only. Existing persisted-checkpoint regressions are separately executed.'}
    finally:random.setstate(rng)


def main():
    study.verify_entry()
    if len(sys.argv)==2:
        with study.MemoryLimit(study.memory.ProcessMemory(),sys.stdout):
            print(json.dumps(verify(sys.argv[1]),allow_nan=False))
        return 0
    directory=study.BASE/(datetime.now(study.memory.ZONE).strftime('%Y%m%dT%H%M%S%f+0800')+'-checkpoint-ownership');directory.mkdir(exist_ok=False)
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','PATHEXT'}}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    for name in ('small','medium'):
        tick=time.perf_counter()
        try:
            reply=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),name],cwd=study.ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=300)
            result=json.loads(reply.stdout) if reply.returncode==0 else {'status':'WORKER_FAILED','raw_error_withheld':True}
        except subprocess.TimeoutExpired:result={'status':'WALL_DEADLINE_EXCEEDED','deadline_seconds':300}
        (directory/(name+'.json')).write_bytes((json.dumps({'result':result,'worker_wall_seconds':time.perf_counter()-tick},indent=2)+'\n').encode())
        print(json.dumps({'scenario':name,'status':result['status']}),flush=True)
        if result['status']!='SUCCESS':return 1
    print(directory.relative_to(study.ROOT).as_posix());return 0


if __name__=='__main__':raise SystemExit(main())
