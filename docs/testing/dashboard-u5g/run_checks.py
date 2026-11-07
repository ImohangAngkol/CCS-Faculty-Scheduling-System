"""New U5G command records only; existing milestone tools/evidence stay sealed."""
from datetime import datetime
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
COMMANDS=dict(runpy.run_path(str(BASE.parent/'dashboard-u5f/run_checks.py'))['COMMANDS'])
COMMANDS.update(**{'bundle-tests':[str(ROOT/'.venv/Scripts/python.exe'),'-B','-m','pytest','-p','no:cacheprovider','-q','tests/test_ga_input_bundle.py'],
    'analysis':[str(ROOT/'.venv/Scripts/python.exe'),'-B','-m','pytest','-p','no:cacheprovider','-q','tests/test_advanced_ga_analysis.py']})
COMMANDS['frontend']=['node','--test',*dict.fromkeys([*COMMANDS['regressions'][2:],*COMMANDS['focused'][2:],*COMMANDS['u5e-contracts'][2:]])]

def main():
    selection=sys.argv[1];cmd=COMMANDS[selection]
    target=BASE/(datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')+'-'+selection);target.mkdir(exist_ok=False)
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE','PROGRAMFILES','PROGRAMFILES(X86)'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed};env.update(PYTHONDONTWRITEBYTECODE='1',VITE_API_URL='http://localhost:57999')
    # The browser harness accepts this destination; its sealed original evidence
    # is never written. Responses remain intercepted and fictional.
    if selection=='browser':env['U5F_EVIDENCE_DIR']=str(target)
    backend=selection.startswith('backend') or selection in {'bundle-tests','receipts','analysis'}
    if backend:cmd=[*cmd,'--basetemp',str(Path(tempfile.gettempdir())/('ga-u5g-'+uuid4().hex))]
    start=datetime.now().astimezone().isoformat();tick=time.perf_counter()
    try:
        result=subprocess.run(cmd,cwd=ROOT/('backend' if backend else 'frontend'),env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
        code=result.returncode;out=result.stdout;err=result.stderr
    except subprocess.TimeoutExpired as error:
        decode=lambda v:v.decode('utf-8',errors='replace') if isinstance(v,bytes) else v or ''
        code=124;out=decode(error.stdout);err=decode(error.stderr)+'\nBound exceeded; owned process cleanup requires review.'
    row=dict(selection=selection,command=cmd,started_at=start,ended_at=datetime.now().astimezone().isoformat(),elapsed_seconds=time.perf_counter()-tick,exit_code=code,stdout=out,stderr=err,
        scope='Fictional temporary fixtures only; no PostgreSQL. Browser HTTP intercepted, not live GA acceptance. Bundle is captured-only, not consumed by V1.')
    (target/'command.json').write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(selection=selection,exit_code=code,evidence=target.relative_to(ROOT).as_posix(),summary=out[-1600:],stderr=err[-800:])))
    return code

if __name__=='__main__':raise SystemExit(main())
