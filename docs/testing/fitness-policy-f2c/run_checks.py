"""F2C isolated contract tests, unchanged V2 regression and arithmetic study."""
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


def worker(key,output,temporary):
    if key=='numeric':
        from numeric_study import main
        sys.argv=[sys.argv[0],str(output/'numeric.json')];main();return 0
    if key=='inventory':
        from inventory_calls import collect
        data=collect()
        with (output/'call-paths.json').open('x',encoding='utf-8') as f:json.dump(data,f,indent=2);f.write('\n')
        print(json.dumps(dict(indexed_files=len(data['files']),calls=sum(len(x['calls']) for x in data['files']))));return 0
    import pytest
    class Outcomes:
        def __init__(self):self.counts={x:0 for x in ('passed','failed','skipped','errors')}
        def pytest_runtest_logreport(self,report):
            if report.when=='call' or report.failed or (report.when=='setup' and report.skipped):
                key='errors' if report.failed and report.when!='call' else report.outcome
                self.counts[key]+=1
        def pytest_sessionfinish(self,session,exitstatus):
            with (output/'outcomes.json').open('x',encoding='utf-8') as f:
                json.dump(dict(selection=key,counts=self.counts,collected=session.testscollected,exit_code=int(exitstatus)),f,indent=2);f.write('\n')
    plugin=Outcomes()
    args=['-p','no:cacheprovider','-q','--tb=short','--show-capture=no','--basetemp',temporary]
    if key=='contract':return pytest.main([*args,str(BASE/'test_contract.py')],plugins=[plugin])
    if key!='engine':raise ValueError('UNSUPPORTED_SELECTION')
    from unittest.mock import patch
    sys.path.insert(0,str(ROOT/'backend'))
    from benchmarks.retention_runtime import runtime,data_guard
    from benchmarks import scaled_python as bench
    runtime()
    real_run=subprocess.run
    def child(command,*args,**kwargs):
        command=list(command)
        if command[1:4]!=['-B','-m','tests.d10.resume_v2_child']:raise RuntimeError('UNREVIEWED_TEST_CHILD_REJECTED')
        return real_run([command[0],'-B',str(ROOT/'backend/benchmarks/retention_child.py'),'checkpoint',*command[4:]],*args,**kwargs)
    with bench.synthetic_scoring(([],[],[]),[],runtime()[3]().to_dict()),data_guard(),patch.object(subprocess,'run',child):
        from services.ga_checkpoint_service import engine_fingerprint
        from services.ga_v2_store import engine_fingerprint as v2_fingerprint
        with (output/'engine-identity.json').open('x',encoding='utf-8') as f:
            json.dump(dict(v1=engine_fingerprint(),v2=v2_fingerprint(),scope='Unmodified supported default engine, schema-only imports and fictional tests'),f,indent=2);f.write('\n')
        return pytest.main([*args,'tests/d10/test_v2_engine.py'],plugins=[plugin])


def main():
    key=sys.argv[1]
    if key not in ('contract','engine','numeric','inventory'):raise ValueError('UNSUPPORTED_SELECTION')
    if len(sys.argv)>2 and sys.argv[2]=='--worker':return worker(key,Path(sys.argv[3]),sys.argv[4])
    start=datetime.now(timezone(timedelta(hours=8)));stamp=start.strftime('%Y%m%dT%H%M%S%f+0800')+'-'+key
    output=BASE/stamp;output.mkdir(exist_ok=False)
    allow={'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','PATHEXT'}
    env={k:v for k,v in os.environ.items() if k.upper() in allow}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    command=[str(ROOT/'.venv/Scripts/python.exe'),'-B',str(Path(__file__).resolve()),key,'--worker',str(output),
        str(Path(tempfile.gettempdir())/('f2c-'+stamp))]
    tick=time.perf_counter();timed_out=False
    try:
        reply=subprocess.run(command,cwd=ROOT/'backend',env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
        code,stdout,stderr=reply.returncode,reply.stdout,reply.stderr
    except subprocess.TimeoutExpired as error:
        timed_out=True;code=124
        stdout=error.stdout.decode('utf-8',errors='replace') if isinstance(error.stdout,bytes) else error.stdout or ''
        stderr='F2C_WORKER_TIMEOUT'
    sys.path.insert(0,str(ROOT/'backend'))
    from services.evidence_sanitization import sanitize_tree
    record=sanitize_tree(dict(selection=key,command=command,cwd='backend',started_at=start.isoformat(),
        finished_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),elapsed_seconds=time.perf_counter()-tick,
        exit_code=code,timed_out=timed_out,stdout=stdout,stderr=stderr,
        scope='F2C executable specification or unchanged default-mode regression; no experimental production scoring/authority/database/browser.'))
    with (output/'command.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
    print(json.dumps(dict(path=output.relative_to(ROOT).as_posix(),exit_code=code,stdout=record['stdout'],stderr=record['stderr'])))
    return code


if __name__=='__main__':raise SystemExit(main())
