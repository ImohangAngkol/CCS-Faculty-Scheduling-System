"""F1 fictional-only validation; no production cohort or provider activation."""
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
    key=sys.argv[1]
    paths={'cohort':['tests/f1/test_cohort.py','tests/audit/test_thesis_correctness.py','tests/d10/test_v2_engine.py'],
           'workflow':['tests/dashboard/test_system_acceptance.py','tests/dashboard/test_chair_trust.py',
                       'tests/dashboard/test_application_trust.py','tests/dashboard/test_adjustments.py']}
    if len(sys.argv)>2 and sys.argv[2]=='--worker':
        from unittest.mock import patch
        sys.path.insert(0,str(ROOT/'backend'))
        from benchmarks.retention_runtime import runtime,data_guard
        from benchmarks import scaled_python as bench
        runtime();import pytest
        real_run=subprocess.run
        def child(command,*args,**kwargs):
            command=list(command)
            if command[1:4]==['-B','-m','tests.d10.resume_v2_child']:
                command=[command[0],'-B',str(ROOT/'backend/benchmarks/retention_child.py'),'checkpoint',*command[4:]]
            elif len(command)==5 and command[1:4]==['-B','-m','tests.dashboard.adjustment_restart_child']:
                database=Path(command[4]).resolve()
                assert database.is_file() and database.is_relative_to(Path(tempfile.gettempdir()).resolve())
                command=[command[0],'-B',str(ROOT/'docs/testing/thesis-functional-audit/restart_child.py'),str(database)]
            else:raise RuntimeError('UNREVIEWED_TEST_CHILD_REJECTED')
            return real_run(command,*args,**kwargs)
        with bench.synthetic_scoring(([],[],[]),[],runtime()[3]().to_dict()),data_guard(),patch.object(subprocess,'run',child):
            return pytest.main(['-p','no:cacheprovider',*paths[key],'-q','--tb=short','--show-capture=no','--basetemp',sys.argv[3]])
    start=datetime.now(timezone(timedelta(hours=8)));stamp=start.strftime('%Y%m%dT%H%M%S%f+0800')+'-'+key
    output=BASE/stamp;output.mkdir(exist_ok=False)
    env={k:v for k,v in os.environ.items() if k.upper() in {
        'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','PROGRAMFILES',
        'PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','PATHEXT'}}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',PYTHONUTF8='1',PYTHONIOENCODING='utf-8',F1_OBSERVATIONS=str(output))
    command=[str(ROOT/'.venv/Scripts/python.exe'),'-B',str(Path(__file__).resolve()),key,'--worker',
             str(Path(tempfile.gettempdir())/('faculty-cohort-f1-'+stamp))]
    cwd=ROOT/'backend'
    if key=='frontend':
        command=['node','--test',*['tests/'+name+'.test.mjs' for name in ('preferenceModel','preferenceApi','mySchedule','adjustments',
            'chairReviews','scheduleApplications','constrainedGA','fitnessReporting','functionalReadiness','auth','authSessionRace')]]
        cwd=ROOT/'frontend'
    tick=time.perf_counter();reply=subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
    sys.path.insert(0,str(ROOT/'backend'))
    from services.evidence_sanitization import sanitize_tree
    record=sanitize_tree(dict(selection=key,command=command,cwd=cwd.relative_to(ROOT).as_posix(),started_at=start.isoformat(),
        finished_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),elapsed_seconds=time.perf_counter()-tick,
        exit_code=reply.returncode,stdout=reply.stdout,stderr=reply.stderr,
        scope='Fictional F1 adapter; original source byte-identical. Workflow uses real in-process FastAPI/auth and owned SQLite with fictional authority; frontend uses Node contracts, not a browser.'))
    with (output/'command.json').open('x',encoding='utf-8') as out:json.dump(record,out,indent=2);out.write('\n')
    print(json.dumps({'path':output.relative_to(ROOT).as_posix(),'exit_code':reply.returncode,'stdout':record['stdout']}))
    return reply.returncode


if __name__=='__main__':raise SystemExit(main())
