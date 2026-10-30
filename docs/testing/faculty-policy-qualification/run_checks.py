"""New evidence only; fictional bootstrap before collection, no database."""
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent


def main():
    if len(sys.argv)>1 and sys.argv[1]=='--worker':
        from unittest.mock import patch
        sys.path.insert(0,str(ROOT/'backend'))
        from benchmarks.retention_runtime import runtime,data_guard
        from benchmarks import scaled_python as bench
        runtime();import pytest
        real_run=subprocess.run
        def child(command,*args,**kwargs):
            command=list(command)
            if command[1:4]!=['-B','-m','tests.d10.resume_v2_child']:
                raise RuntimeError('UNREVIEWED_CHILD_REJECTED')
            return real_run([command[0],'-B',str(ROOT/'backend/benchmarks/retention_child.py'),'checkpoint',*command[4:]],*args,**kwargs)
        with bench.synthetic_scoring(([],[],[]),[],runtime()[3]().to_dict()),data_guard(),patch.object(subprocess,'run',child):
            return pytest.main(['-p','no:cacheprovider',str(BASE/'test_policy_qualification.py'),
                'tests/audit/test_thesis_correctness.py','tests/d10/test_v2_engine.py','-q','--tb=short','--show-capture=no',
                '--basetemp',sys.argv[2]])
    start=datetime.now(timezone(timedelta(hours=8)));stamp=start.strftime('%Y%m%dT%H%M%S%f+0800')
    output=BASE/stamp;output.mkdir(exist_ok=False)
    env={k:v for k,v in os.environ.items() if k.upper() in {
        'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','PROGRAMFILES',
        'PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','PATHEXT'}}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',PYTHONUTF8='1',PYTHONIOENCODING='utf-8',POLICY_QUALIFICATION_OUTPUT=str(output))
    command=[str(ROOT/'.venv/Scripts/python.exe'),'-B',str(Path(__file__).resolve()),'--worker',
             str(Path(tempfile.gettempdir())/('faculty-policy-tests-'+stamp))]
    tick=time.perf_counter()
    reply=subprocess.run(command,cwd=ROOT/'backend',env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    sys.path.insert(0,str(ROOT/'backend'))
    from services.evidence_sanitization import sanitize_tree
    record=sanitize_tree(dict(command=command,cwd='backend',started_at=start.isoformat(),
        finished_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),elapsed_seconds=time.perf_counter()-tick,
        exit_code=reply.returncode,stdout=reply.stdout,stderr=reply.stderr,
        scope='Fictional in-memory policy controls and existing audit/D10 regressions; no live database or production corrections'))
    with (output/'command.json').open('x',encoding='utf-8') as out:json.dump(record,out,indent=2);out.write('\n')
    print(json.dumps({'path':output.relative_to(ROOT).as_posix(),'exit_code':reply.returncode,'stdout':record['stdout']}))
    return reply.returncode


if __name__=='__main__':raise SystemExit(main())
