"""HEAD plus U5F-only rehearsal. Real fixed GA uses fictional snapshot data only."""
from datetime import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import tarfile
import tempfile
import time
from integration import main as integrate_main,generate

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
HEAD='d6db077793da52b7559351a5d0f8e6d54608cb77'
MIXED={'backend/main.py':integrate_main,'frontend/src/pages/admin/GenerateSchedule.tsx':generate}
OVERLAY=['backend/services/continuous_readiness.py','backend/routers/continuous_optimization.py','backend/tests/test_continuous_readiness.py','backend/tests/test_continuous_fixed_qualification.py',
    'frontend/src/services/continuousOptimization.ts','frontend/src/components/ga/OptimizationMode.tsx','frontend/tests/continuousOptimization.test.mjs','frontend/tests/continuousOptimization.browser.test.mjs',
    'frontend/tests/continuousOptimization.fixtures.mjs','frontend/tests/continuousOptimizationRun.fixtures.mjs','frontend/tests/continuousOptimization.scenarios.mjs']
def git(*args,input=None):return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),*args],cwd=ROOT,input=input,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)

def main():
    assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('diff','--cached','--name-only').strip()
    index=hashlib.sha256((ROOT/'.git/index').read_bytes()).hexdigest()
    owned=Path(tempfile.mkdtemp(prefix='u5c-r1-snapshot-u5f-')).resolve();assert owned.parent==Path(tempfile.gettempdir()).resolve()
    (owned/'OWNED-SNAPSHOT.json').write_text(json.dumps({'head':HEAD,'purpose':'U5F fictional fixed qualification; continuous execution blocked'}),encoding='utf-8')
    snapshot=owned/'repository';snapshot.mkdir();archive=owned/'head.tar'
    with archive.open('xb') as f:subprocess.run(['git','-c','safe.directory='+str(ROOT),'-c','core.autocrlf=false','archive',HEAD],cwd=ROOT,stdout=f,check=True)
    with tarfile.open(archive) as t:
        for m in t.getmembers():assert (snapshot/m.name).resolve().is_relative_to(snapshot) and not m.issym() and not m.islnk()
        t.extractall(snapshot,members=[m for m in t.getmembers() if not m.name.startswith('backend/data/')],filter='data')
    helper=runpy.run_path(str(ROOT/'docs/testing/dashboard-u5c-r1/fictional_bootstrap.py'));helper['prepare'](snapshot)
    helper['release_bytes'](snapshot,json.loads((ROOT/'docs/testing/dashboard-u5c-r1/release-byte-layout.json').read_text(encoding='utf-8')))
    hashes={};blobs={}
    for name in OVERLAY:
        raw=(ROOT/name).read_bytes();p=snapshot/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        hashes[name]=hashlib.sha256(raw).hexdigest();blobs[name]=git('hash-object','--stdin',input=raw).decode().strip()
    for name,transform in MIXED.items():
        assert transform((BASE/'entry'/Path(name).name).read_bytes())==(ROOT/name).read_bytes(),'Mixed user bytes changed outside U5F insertion'
        old=git('show',HEAD+':'+name);new=transform(old);(snapshot/name).write_bytes(new)
        patch=''.join(difflib.unified_diff(old.decode().splitlines(keepends=True),new.decode().splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name)).encode()
        target=BASE/(Path(name).stem+'-integration.patch')
        if target.exists():assert target.read_bytes()==patch
        else:target.write_bytes(patch)
        git('apply','--check','--cached',str(target));hashes[name]=hashlib.sha256(new).hexdigest();blobs[name]=git('hash-object','--stdin',input=new).decode().strip()
    for name in ['backend/services/ga_input_receipt.py','backend/services/advanced_ga_analysis.py','frontend/src/services/liveOptimization.ts']:assert not (snapshot/name).exists()
    for name,target in [('.venv',ROOT/'.venv'),('frontend/node_modules',ROOT/'frontend/node_modules')]:
        dest=snapshot/name;assert not dest.exists() and dest.parent.resolve().is_relative_to(snapshot)
        subprocess.run(['cmd','/d','/c','mklink','/J',str(dest),str(target)],capture_output=True,check=True)
    target=BASE/(datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')+'-snapshot');target.mkdir(exist_ok=False)
    commands=runpy.run_path(str(BASE/'run_checks.py'))['COMMANDS']
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE','PROGRAMFILES','PROGRAMFILES(X86)'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed};env.update(PYTHONDONTWRITEBYTECODE='1',VITE_API_URL='http://localhost:57999',U5F_EVIDENCE_DIR=str(target))
    results=[]
    for key in ['backend','fixed','focused','regressions','build','bundle','lint','browser']:
        cmd=commands.get(key)
        if key in ['backend','fixed']:
            cmd=[str(ROOT/'.venv/Scripts/python.exe'),'-B','-m','pytest','-p','no:cacheprovider','-q','tests/test_continuous_'+('readiness' if key=='backend' else 'fixed_qualification')+'.py','--durations=10','--basetemp',str(owned/('pytest-'+key))]
        tick=time.perf_counter();start=datetime.now().astimezone().isoformat()
        result=subprocess.run(cmd,cwd=snapshot/('backend' if key in ['backend','fixed'] else 'frontend'),env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240)
        item=dict(selection=key,command=cmd,started_at=start,ended_at=datetime.now().astimezone().isoformat(),elapsed_seconds=time.perf_counter()-tick,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr,scope='U5F-only temporary source snapshot, empty fictional import tables and declared fictional model fixtures; no institutional data or DB')
        (target/(key+'-command.json')).write_text(json.dumps(item,indent=2)+'\n',encoding='utf-8');results.append(dict(selection=key,exit_code=result.returncode));print(json.dumps(results[-1]),flush=True)
        if result.returncode:break
    assert git('rev-parse','HEAD').decode().strip()==HEAD and hashlib.sha256((ROOT/'.git/index').read_bytes()).hexdigest()==index
    proof=dict(head=HEAD,source_sha256=hashes,proposed_blob_oids=blobs,results=results,complete=len(results)==8 and all(r['exit_code']==0 for r in results),fictional_source_only=True,no_u5d_u5e_or_live_center_dependency=True,no_actual_staging=True,snapshot=str(snapshot))
    (target/'snapshot-proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    return 0 if proof['complete'] else 1
if __name__=='__main__':raise SystemExit(main())
