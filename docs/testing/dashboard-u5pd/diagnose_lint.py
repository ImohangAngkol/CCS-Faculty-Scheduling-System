"""Bounded per-file lint in the already owned failed snapshot. No app changes."""
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent


def main():
    previous=sorted(BASE.glob('*-lint/command.json'))[0]
    old=json.loads(previous.read_text());owned=Path(old['test_cache_isolation']['isolated_cache']).parent
    import tempfile
    assert owned.parent==Path(tempfile.gettempdir()).resolve() and owned.name.startswith('u5o-frontend-')
    snapshot=owned/'repository/frontend'
    env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE','PROGRAMFILES','PROGRAMFILES(X86)'}}
    target=BASE/(datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')+'-lint-diagnosis');target.mkdir()
    results=[]
    for source in ['src/api/researchObservations.ts','src/services/researchFreshness.ts','src/pages/ResearchConsole.tsx']:
        command=['node','node_modules/eslint/bin/eslint.js','--debug',source];start=time.monotonic()
        try:
            r=subprocess.run(command,cwd=snapshot,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45)
            code=r.returncode;out=r.stdout;err=r.stderr
        except subprocess.TimeoutExpired as e:
            decode=lambda v:v.decode('utf-8',errors='replace') if isinstance(v,bytes) else v or ''
            code=124;out=decode(e.stdout);err=decode(e.stderr)
        results.append(dict(source=source,command=command,exit_code=code,elapsed_seconds=time.monotonic()-start,stdout=out,stderr=err))
        print(json.dumps(dict(source=source,exit_code=code,elapsed_seconds=results[-1]['elapsed_seconds'])),flush=True)
        with (target/(Path(source).stem+'.json')).open('x',encoding='utf-8',newline='\n') as f:json.dump(results[-1],f,indent=2);f.write('\n')
        if code==124:break
    return int(any(r['exit_code'] for r in results))
if __name__=='__main__':raise SystemExit(main())
