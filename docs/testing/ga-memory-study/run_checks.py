"""Finite, sanitized memory-study test runner. No PostgreSQL cases."""
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[3]


def main():
    key=sys.argv[1]
    selections={'memory':['tests/performance/test_memory_study.py'],
                'regressions':['tests/performance/test_scaled_python.py','tests/d10/test_v2_engine.py','tests/d10/test_v2_api.py',
                               'tests/test_fitness_reporting.py','tests/test_preassigned_assignments.py']}
    zone=timezone(timedelta(hours=8)); started=datetime.now(zone)
    stamp=started.strftime('%Y%m%dT%H%M%S%f+0800')+'-'+key
    directory=ROOT/'docs/testing/ga-memory-study'/stamp; directory.mkdir(exist_ok=False)
    command=[str(ROOT/'.venv/Scripts/python.exe'),'-B','-m','pytest','-p','no:cacheprovider',*selections[key],'-q','--tb=short',
             '--show-capture=no','--basetemp',str(Path(tempfile.gettempdir())/('ga-memory-tests-'+stamp))]
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE',
         'APPDATA','LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','PATHEXT'}}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    tick=time.perf_counter()
    run=subprocess.run(command,cwd=ROOT/'backend',env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
    sys.path.insert(0,str(ROOT/'backend'))
    from services.evidence_sanitization import sanitize_tree
    record=sanitize_tree({'selection':key,'command':command,'started_at':started.isoformat(),
        'finished_at':datetime.now(zone).isoformat(),'elapsed_seconds':time.perf_counter()-tick,'exit_code':run.returncode,
        'stdout':run.stdout,'stderr':run.stderr,'scope':'Fictional Python memory probes and owned regression fixtures; no PostgreSQL or optimization'})
    (directory/'command.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
    print(json.dumps({'path':directory.relative_to(ROOT).as_posix(),'exit_code':run.returncode,'stdout':record['stdout']}))
    return run.returncode


if __name__=='__main__':
    raise SystemExit(main())
