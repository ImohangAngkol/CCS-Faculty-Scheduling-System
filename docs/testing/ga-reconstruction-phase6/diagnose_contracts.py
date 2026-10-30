"""Diagnose baseline-oracle failures without changing any engine or codec."""
from datetime import datetime,timedelta,timezone
from contextlib import redirect_stdout,redirect_stderr
import json
import os
from pathlib import Path
import random
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'backend'))


def worker():
    from benchmarks.retention_runtime import runtime,data_guard
    from benchmarks import scaled_python as bench
    from benchmarks.scenarios import build,snapshot
    from benchmarks.reconstruction_benchmark import PARAMETERS
    runtime()
    from services import ga_checkpoint_service as codec,ga_publication_service as publication
    from tests.d10.support import templates
    from tests.d10.test_v2_engine import arranged,snapshot_for
    engine=runtime()[0];rng=random.getstate()
    try:
        values,legacy,rows,settings,metadata=build('small');pinned=snapshot(values,metadata);params=runtime()[-1](**PARAMETERS)
        holder={}
        def final(state):holder['state']=state
        def pause(state):holder['encoded']=codec.canonical(codec.encode_graph(state));return 'pause'
        with bench.synthetic_scoring(values,rows,settings),data_guard(),bench.no_io():
            random.seed(714);engine.run(values,pinned,params,legacy,final);left=holder.pop('state');left_rng=random.getstate()
            random.seed(714);engine.run(values,pinned,params,legacy,pause)
            restored=codec.decode_graph(json.loads(holder.pop('encoded')))
            engine.validate_state(restored,pinned,values)
            engine.run(values,pinned,params,legacy,final,state=restored);right=holder.pop('state')
            a=codec.encode_graph(left);b=codec.encode_graph(right)
            assert a['root']==b['root'] and len(a['nodes'])==len(b['nodes'])
            differences=[]
            for index,(x,y) in enumerate(zip(a['nodes'],b['nodes'])):
                if x==y:continue
                primitive=lambda items:all(type(item) in (str,int,bool,float) or item is None for item in items)
                only_set_order=(x.get('kind')==y.get('kind')=='set' and primitive(x['items']) and primitive(y['items'])
                    and sorted(map(lambda value:json.dumps(value,sort_keys=True),x['items']))==sorted(map(lambda value:json.dumps(value,sort_keys=True),y['items'])))
                differences.append({'node_index':index,'left_kind':x.get('kind'),'right_kind':y.get('kind'),
                                    'only_primitive_set_iteration_order_differs':only_set_order})
            assert differences and all(d['only_primitive_set_iteration_order_differs'] for d in differences)
            assert random.getstate()==left_rng
            values=templates(compact=True);pinned=snapshot_for(values,sections=('section-a',),faculty=None,room=None,start=570,end=630)
            reduced=engine.reduced_templates(pinned,values)
            mismatch=None
            try:publication.validate_publication(arranged(values,'7:30','9:30'),*reduced)
            except ValueError as error:mismatch={'type':type(error).__name__,'message':str(error)}
            assert mismatch
            publication.validate_publication(arranged(reduced,'7:30','9:30'),*reduced)
            return {'status':'DIAGNOSED','original_continuation':{'same_root_node_count_and_RNG':True,'different_nodes':differences,
                'all_other_nodes_including_alias_refs_equal':True,'production_codec_changed':False},
                'adjacency_fixture':{'unreduced_candidate_error':mismatch,'candidate_from_reduced_templates':'ORIGINAL_VALIDATOR_PASSED'},
                'scope':'Original unmodified engine/codec only; fictional inputs; no checkpoint files, database or publication write'}
    finally:random.setstate(rng)


def main():
    if '--worker' in sys.argv:
        with open(os.devnull,'w') as sink,redirect_stdout(sink),redirect_stderr(sink):data=worker()
        print(json.dumps(data));return
    zone=timezone(timedelta(hours=8));directory=Path(__file__).resolve().parent/(datetime.now(zone).strftime('%Y%m%dT%H%M%S%f+0800')+'-contract-diagnosis');directory.mkdir(exist_ok=False)
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','PATHEXT'}}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    reply=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--worker'],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=180)
    assert reply.returncode==0,'Diagnostic failed; no auto-correction permitted'
    data=json.loads(reply.stdout);(directory/'diagnosis.json').write_bytes((json.dumps(data,indent=2)+'\n').encode())
    print(json.dumps(data));print(directory.relative_to(ROOT).as_posix())


if __name__=='__main__':main()
