"""Run only new standard-library qualification controls; save fresh evidence."""
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent


def main():
    start=datetime.now(timezone(timedelta(hours=8)));stamp=start.strftime('%Y%m%dT%H%M%S%f+0800')+'-tests'
    output=BASE/stamp;output.mkdir(exist_ok=False)
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','PATHEXT'}}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    command=[str(ROOT/'.venv/Scripts/python.exe'),'-B','-m','pytest',str(BASE/'test_source_qualification.py'),
             '-p','no:cacheprovider','-q','--tb=short','--show-capture=no','--basetemp',str(Path(tempfile.gettempdir())/('faculty-source-qualification-'+stamp))]
    tick=time.perf_counter();reply=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
    record=dict(command=command,cwd='repository root',started_at=start.isoformat(),finished_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),
        elapsed_seconds=time.perf_counter()-tick,exit_code=reply.returncode,stdout=reply.stdout,stderr=reply.stderr,
        scope='New fictional CSV/ZIP/XML aggregate controls only; no GA, DB, authority, IS faculty or institutional fixtures')
    with (output/'command.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
    print(json.dumps(dict(path=output.relative_to(ROOT).as_posix(),exit_code=reply.returncode,stdout=reply.stdout)))
    return reply.returncode


if __name__=='__main__':raise SystemExit(main())
