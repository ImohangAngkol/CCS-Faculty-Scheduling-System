"""New F2B record using unchanged Phase6 source-identical V1 mirror worker.

No prior evidence directory is used as an output. Owned mirror contains empty
CSV schemas and fictional/default JSON only; no real academic file is copied.
"""
from datetime import datetime,timedelta,timezone
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if len(sys.argv)==3 and sys.argv[1]=='--worker':
        spec=importlib.util.spec_from_file_location('preserved_phase6_v1_worker',ROOT/'docs/testing/ga-reconstruction-phase6/v1_fixture.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        result=module.worker(Path(sys.argv[2]));print(json.dumps(result));return result['exit_code']
    start=datetime.now(timezone(timedelta(hours=8)));directory=BASE/(start.strftime('%Y%m%dT%H%M%S%f+0800')+'-v1-mirror');directory.mkdir(exist_ok=False)
    sys.path.insert(0,str(ROOT/'backend'))
    from benchmarks.retention_runtime import runtime,CSV_SCHEMAS,JSON_SCHEMAS
    runtime()
    from services.ga_checkpoint_service import engine_fingerprint
    from services.evidence_sanitization import sanitize_tree
    fingerprint=engine_fingerprint()
    tracked=subprocess.check_output(['git','ls-files','-z','backend'],cwd=ROOT).decode().split('\0')
    tests={'backend/tests/__init__.py','backend/tests/conftest.py','backend/tests/d10/__init__.py','backend/tests/d10/support.py','backend/tests/d10/test_v1_baseline.py'}
    paths=[p for p in tracked if p.endswith('.py') and (not p.startswith('backend/tests/') or p in tests)]
    paths.append('backend/services/fitness_policy_compatibility.json')
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','PATHEXT'}}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    tick=time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='f2b-v1-source-') as temporary:
        mirror=Path(temporary).resolve();assert not mirror.is_relative_to(ROOT) and mirror.name.startswith('f2b-v1-source-')
        backend=mirror/'backend';hashes={}
        for relative in paths:
            target=mirror/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/relative).read_bytes())
            assert sha(target)==sha(ROOT/relative);hashes[Path(relative).relative_to('backend').as_posix()]=sha(target)
        data=backend/'data';data.mkdir()
        for name,columns in CSV_SCHEMAS.items():
            with (data/name).open('w',encoding='utf-8',newline='') as f:csv.writer(f).writerow(columns)
        for name,value in {**JSON_SCHEMAS,'faculty_preferences.json':[],'ga_settings.json':runtime()[3]().to_dict()}.items():
            (data/name).write_bytes(json.dumps(value).encode())
        digest=hashlib.sha256();source_inputs={}
        for path in sorted(data.iterdir()):
            relative=str(path.relative_to(backend));digest.update(relative.encode());digest.update(path.read_bytes());source_inputs[relative]=path.read_text(encoding='utf-8-sig')
        expected=dict(source_hashes=hashes,original_engine_fingerprint=fingerprint,fictional_input_fingerprint=digest.hexdigest(),fictional_source_inputs=source_inputs)
        (mirror/'fixture-contract.json').write_bytes(json.dumps(expected).encode())
        command=[sys.executable,'-B',str(Path(__file__).resolve()),'--worker',str(mirror)]
        reply=subprocess.run(command,cwd=backend,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
        try:result=json.loads(reply.stdout)
        except ValueError:result=dict(exit_code=reply.returncode,status='MIRROR_WORKER_PROTOCOL_FAILED',raw_error_withheld=True)
    result=sanitize_tree(result)
    result.update(command=command,started_at=start.isoformat(),finished_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),
                  elapsed_seconds=time.perf_counter()-tick,scope='Unchanged default current-release V1 continuation in owned source-byte-identical fictional mirror; no F2B scoring dispatch implemented')
    with (directory/'command.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(path=directory.relative_to(ROOT).as_posix(),exit_code=result['exit_code'],stdout=result.get('stdout',''))))
    return result['exit_code']


if __name__=='__main__':raise SystemExit(main())
