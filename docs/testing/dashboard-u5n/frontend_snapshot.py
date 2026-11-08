"""Test committed frontend bytes, never unrelated in-progress UI changes."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
HEAD='ed35d620111490d3021567ba7dcc6b26ec93d212'

def main():
    git=['git','-c','safe.directory='+str(ROOT)]
    assert subprocess.check_output([*git,'rev-parse','HEAD'],cwd=ROOT).decode().strip()==HEAD
    index=hashlib.sha256((ROOT/'.git/index').read_bytes()).hexdigest()
    commands=runpy.run_path(str(ROOT/'docs/testing/dashboard-u5j/run_checks.py'))['COMMANDS']
    selections=sys.argv[1:] or ['frontend','build','bundle','lint','browser']
    assert all(s in {'frontend','build','bundle','lint','browser'} for s in selections)
    owned=Path(tempfile.mkdtemp(prefix='u5n-frontend-')).resolve();snapshot=owned/'repository';snapshot.mkdir()
    with (owned/'frontend.tar').open('xb') as f:
        subprocess.run([*git,'archive',HEAD,'--','frontend'],cwd=ROOT,stdout=f,check=True)
    with tarfile.open(owned/'frontend.tar') as source:
        for m in source.getmembers():assert (snapshot/m.name).resolve().is_relative_to(snapshot) and not m.issym() and not m.islnk()
        source.extractall(snapshot,filter='data')
    # Existing frontend contracts import this committed fictional DTO fixture.
    fixture='docs/testing/dashboard-u5e/fictional-api.json'
    destination=snapshot/fixture;destination.parent.mkdir(parents=True)
    destination.write_bytes(subprocess.check_output([*git,'show',HEAD+':'+fixture],cwd=ROOT))
    subprocess.run(['cmd','/d','/c','mklink','/J',str(snapshot/'frontend/node_modules'),str(ROOT/'frontend/node_modules')],capture_output=True,check=True)
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE','PROGRAMFILES','PROGRAMFILES(X86)'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed};env.update(VITE_API_URL='http://localhost:57999')
    for selection in selections:
        target=BASE/(datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')+'-'+selection);target.mkdir(exist_ok=False)
        child_env=dict(env)
        if selection=='browser':child_env['U5F_EVIDENCE_DIR']=str(target)
        command=commands[selection];start=datetime.now().astimezone().isoformat();tick=time.perf_counter()
        try:
            result=subprocess.run(command,cwd=snapshot/'frontend',env=child_env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
            code=result.returncode;out=result.stdout;err=result.stderr
        except subprocess.TimeoutExpired as error:
            decode=lambda v:v.decode('utf-8',errors='replace') if isinstance(v,bytes) else v or ''
            code=124;out=decode(error.stdout);err=decode(error.stderr)+'\nTimeout; owned process cleanup requires review.'
        row=dict(selection=selection,head=HEAD,command=command,started_at=start,ended_at=datetime.now().astimezone().isoformat(),
            elapsed_seconds=time.perf_counter()-tick,exit_code=code,stdout=out,stderr=err,
            scope='Committed frontend source in owned temporary snapshot; dependencies reused without installation. Browser uses actual Edge/React with intercepted fictional HTTP, not live FastAPI or U5N worker acceptance. Unrelated working-tree UI changes are not qualified by this check.')
        (target/'command.json').write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(dict(selection=selection,exit_code=code,evidence=target.relative_to(ROOT).as_posix())),flush=True)
        if code:return code
    assert subprocess.check_output([*git,'rev-parse','HEAD'],cwd=ROOT).decode().strip()==HEAD
    assert hashlib.sha256((ROOT/'.git/index').read_bytes()).hexdigest()==index
    return 0
if __name__=='__main__':raise SystemExit(main())
