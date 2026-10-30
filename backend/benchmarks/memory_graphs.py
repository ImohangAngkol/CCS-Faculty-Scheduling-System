"""Census/copy actual final V2 chromosomes, not just constructive witnesses."""
from contextlib import redirect_stderr,redirect_stdout
from datetime import datetime
import copy
import gc
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmarks import memory_study as memory
from benchmarks.scenarios import build,snapshot


def measure(name):
    engine=memory.bench.runtime()[0]; process=memory.ProcessMemory(); rng=random.getstate()
    source=json.loads(memory.PHASE2.read_text()); parameters=memory.bench.runtime()[-1](**source['parameters'])
    try:
        values,legacy,rows,settings,metadata=build(name); pinned=snapshot(values,metadata)
        last=None; history=[]
        def boundary(state):
            nonlocal last
            history.append(dict(state['history'][-1]))
            # Only final state is retained by this diagnostic. Best-ever inside
            # engine.run is unchanged; do not retain earlier benchmark states.
            if state['generation']==parameters.generations:last=state
        with memory.bench.synthetic_scoring(values,rows,settings),open(os.devnull,'w') as sink,redirect_stdout(sink),redirect_stderr(sink),memory.bench.no_io():
            random.seed(714)
            assert engine.run(values,pinned,parameters,legacy,boundary)=='complete'
            signature=hashlib.sha256(json.dumps(memory.bench.signature(last['best']),sort_keys=True).encode()).hexdigest()
            assert signature==source['results'][name]['trials'][0]['best_assignment_sha256']
            assert history==source['results'][name]['trials'][0]['history']
            engine.admit(last['best'],pinned,engine.reduced_templates(pinned,values))
            gc.collect()
            graphs={'best':memory.graph_summary(last['best']),
                    'population':memory.graph_summary(last['population'])}
            for index,candidate in enumerate(last['population']):graphs['individual_'+str(index)]=memory.graph_summary(candidate)
            copied=memory.probe_operation('deepcopy_actual_final_best',lambda:copy.deepcopy(last['best']),process,include_graph=True)
            assert copied['copied_graph']['object_type_counts']==graphs['best']['object_type_counts']
            return {'status':'SUCCESS','scenario':name,'seed':714,'phase2_output_matches':True,
                    'best_assignment_sha256':signature,'graphs':graphs,'deepcopy':copied,
                    'scope':'Actual final engine graph, original parameters and hard admission; graph census outside engine measurement; no optimized or pruned candidate'}
    finally:random.setstate(rng)


def main():
    memory.verify_entry()
    if len(sys.argv)==2:
        print(json.dumps(measure(sys.argv[1]),allow_nan=False)); return 0
    directory=memory.BASE/(datetime.now(memory.ZONE).strftime('%Y%m%dT%H%M%S%f+0800')+'-actual-graphs')
    directory.mkdir(exist_ok=False)
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE',
        'APPDATA','LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','PATHEXT'}}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    for name in ('small','medium','large'):
        tick=time.perf_counter(); command=[sys.executable,'-B',str(Path(__file__).resolve()),name]
        try:
            reply=subprocess.run(command,cwd=memory.ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=300)
            result=json.loads(reply.stdout) if reply.returncode==0 else {'status':'WORKER_FAILED','raw_error_withheld':True}
        except subprocess.TimeoutExpired:result={'status':'WALL_DEADLINE_EXCEEDED','deadline_seconds':300}
        (directory/(name+'.json')).write_bytes((json.dumps({'scenario':name,'worker_wall_seconds':time.perf_counter()-tick,'result':result},indent=2)+'\n').encode())
        print(json.dumps({'scenario':name,'status':result['status']}),flush=True)
        if result['status']!='SUCCESS':return 1
    print(directory.relative_to(memory.ROOT).as_posix()); return 0


if __name__=='__main__':
    raise SystemExit(main())
