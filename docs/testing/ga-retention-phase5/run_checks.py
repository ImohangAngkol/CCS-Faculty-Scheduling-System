"""Bootstrap fictional-only imports before pytest collection; sanitized evidence."""
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
    paths={'phase5':['tests/performance/test_retention_phase5.py'],
           'regressions':['tests/performance/test_scaled_python.py','tests/performance/test_memory_study.py',
                          'tests/d10/test_v2_engine.py','tests/d10/test_v2_api.py']}
    if len(sys.argv)>2 and sys.argv[2]=='--worker':
        from unittest.mock import patch
        sys.path.insert(0,str(ROOT/'backend'))
        from benchmarks.retention_runtime import runtime,data_guard
        from benchmarks import scaled_python as bench
        runtime();import pytest
        original_run=subprocess.run
        def guarded_child(command,*args,**kwargs):
            command=list(command)
            adapter=str(ROOT/'backend/benchmarks/retention_child.py')
            if len(command)>3 and command[1:4]==['-B','-m','tests.d10.resume_v2_child']:
                command=[command[0],'-B',adapter,'checkpoint',*command[4:]]
            elif len(command)>3 and command[1]=='-B' and Path(command[2]).resolve()==ROOT/'backend/benchmarks/scaled_python.py':
                command=[command[0],'-B',adapter,'benchmark',*command[3:]]
            else:raise RuntimeError('UNREVIEWED_TEST_CHILD_REJECTED')
            return original_run(command,*args,**kwargs)
        with bench.synthetic_scoring(([],[],[]),[],bench.runtime()[3]().to_dict()),data_guard(),patch.object(subprocess,'run',guarded_child):
            return pytest.main(['-p','no:cacheprovider',*paths[key],'-q','--tb=short','--show-capture=no','--basetemp',sys.argv[3]])
    zone=timezone(timedelta(hours=8));start=datetime.now(zone);stamp=start.strftime('%Y%m%dT%H%M%S%f+0800')+'-'+key
    directory=ROOT/'docs/testing/ga-retention-phase5'/stamp;directory.mkdir(exist_ok=False)
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','PATHEXT'}}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    command=[str(ROOT/'.venv/Scripts/python.exe'),'-B',str(Path(__file__).resolve()),key,'--worker',str(Path(tempfile.gettempdir())/('phase5-tests-'+stamp))]
    tick=time.perf_counter();reply=subprocess.run(command,cwd=ROOT/'backend',env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
    sys.path.insert(0,str(ROOT/'backend'))
    from services.evidence_sanitization import sanitize_tree
    record=sanitize_tree(dict(selection=key,command=command,started_at=start.isoformat(),finished_at=datetime.now(zone).isoformat(),
        elapsed_seconds=time.perf_counter()-tick,exit_code=reply.returncode,stdout=reply.stdout,stderr=reply.stderr,
        scope='Schema-only academic import bootstrap and fictional fixtures; no parsed institutional records or PostgreSQL; genuine binary fingerprints unchanged'))
    (directory/'command.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
    print(json.dumps({'path':directory.relative_to(ROOT).as_posix(),'exit_code':reply.returncode,'stdout':record['stdout']}))
    return reply.returncode


if __name__=='__main__':raise SystemExit(main())
