"""Qualify exact staged frontend bytes in a fresh owned snapshot; no Git writes."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import tarfile
import tempfile
import time

ROOT=Path(__file__).resolve().parents[4];BASE=Path(__file__).resolve().parent
HEAD='1299d000a205287dbfc2d306decc427c98c2ee6e'


def git(*args):return subprocess.check_output(['git','-c','core.autocrlf=false',*args],cwd=ROOT,
    env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def blob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def main():
    assert git('rev-parse','HEAD').decode().strip()==HEAD
    entry=json.loads((BASE/'reconciliation.json').read_text());route=entry['path']
    assert blob(git('show',':'+route))==entry['replacement_staged_blob']
    assert sha((ROOT/route).read_bytes())==entry['working_tree_sha256_before']
    index=sha((ROOT/'.git/index').read_bytes())
    owned=Path(tempfile.mkdtemp(prefix='u5o-frontend-u5pc-index-')).resolve()
    snapshot=owned/'repository';snapshot.mkdir()
    with (owned/'frontend.tar').open('xb') as stream:
        subprocess.run(['git','-c','core.autocrlf=false','archive',HEAD,'--','frontend'],cwd=ROOT,stdout=stream,check=True)
    with tarfile.open(owned/'frontend.tar') as source:
        for item in source.getmembers():assert (snapshot/item.name).resolve().is_relative_to(snapshot) and not item.issym() and not item.islnk()
        source.extractall(snapshot,filter='data')
    changed=git('diff','--cached','--name-only','-z','--','frontend/').decode().strip('\0').split('\0')
    for name in changed:
        p=snapshot/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(git('show',':'+name))
    staged={}
    for row in git('ls-files','--stage','-z','--','frontend/').decode().strip('\0').split('\0'):
        meta,name=row.split('\t',1);mode,oid,stage=meta.split()
        assert mode=='100644' and stage=='0' and blob((snapshot/name).read_bytes())==oid,name
        staged[name]=oid
    fixture='docs/testing/dashboard-u5e/fictional-api.json';p=snapshot/fixture;p.parent.mkdir(parents=True);p.write_bytes(git('show',':'+fixture))
    subprocess.run(['cmd','/d','/c','mklink','/J',str(snapshot/'frontend/node_modules'),str(ROOT/'frontend/node_modules')],capture_output=True,check=True)
    cache=runpy.run_path(str(ROOT/'docs/testing/dashboard-u5pa/isolate_vite_cache.py'))['prepare'](snapshot,owned)
    env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE','PROGRAMFILES','PROGRAMFILES(X86)'}}
    env['VITE_API_URL']='http://localhost:57999'
    commands=runpy.run_path(str(ROOT/'docs/testing/dashboard-u5j/run_checks.py'))['COMMANDS']
    commands['contracts-all']=['node','--test',*[str(p.relative_to(snapshot/'frontend')) for p in sorted((snapshot/'frontend/tests').glob('*.test.mjs')) if '.browser.' not in p.name and '.live.' not in p.name]]
    commands['lint']=['node','node_modules/eslint/bin/eslint.js','src/api/researchObservations.ts','src/pages/ResearchConsole.tsx','src/routes/AppRoutes.tsx','src/layouts/AdminLayout.tsx']
    commands['preview-browser']=['node','--test','tests/researchConsole.browser.test.mjs']
    for selection in ['contracts-all','build','bundle','lint','preview-browser']:
        target=BASE/(datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')+'-'+selection);target.mkdir()
        child=dict(env,U5PC_EVIDENCE=str(target));command=commands[selection];tick=time.monotonic();start=datetime.now().astimezone().isoformat()
        try:
            r=subprocess.run(command,cwd=snapshot/'frontend',env=child,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
            code=r.returncode;out=r.stdout;err=r.stderr
        except subprocess.TimeoutExpired as error:
            decode=lambda v:v.decode('utf-8',errors='replace') if isinstance(v,bytes) else v or ''
            code=124;out=decode(error.stdout);err=decode(error.stderr)+'\nOwned snapshot qualification exceeded bound.'
        row=dict(selection=selection,exit_code=code,command=command,started_at=start,ended_at=datetime.now().astimezone().isoformat(),elapsed_seconds=time.monotonic()-tick,
            stdout=out,stderr=err,head=HEAD,route_staged_blob=entry['replacement_staged_blob'],route_sha256=sha(git('show',':'+route)),
            exact_index_frontend_blobs=staged,test_cache_isolation=cache,scope='Exact staged application/frontend source; only temporary Vite cache configuration transformed. Real Edge/React uses fictional intercepted HTTP, not a fresh live FastAPI/database execution. No working-tree edits or dependencies installed.')
        with (target/'command.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(row,f,indent=2);f.write('\n')
        print(json.dumps(dict(selection=selection,exit_code=code,evidence=target.relative_to(ROOT).as_posix())),flush=True)
        assert sha((ROOT/'.git/index').read_bytes())==index and git('rev-parse','HEAD').decode().strip()==HEAD
        assert sha((ROOT/route).read_bytes())==entry['working_tree_sha256_before']
        if code:return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
