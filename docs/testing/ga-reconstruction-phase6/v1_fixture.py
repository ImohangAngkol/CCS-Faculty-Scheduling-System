"""Unmodified V1 tests in an owned source-byte-identical, fictional-data mirror.

No original input reads, fingerprint replacements, archive suppression or engine
changes. The original writer archives actual fictional files in its real ROOT.
"""
from contextlib import redirect_stdout,redirect_stderr
from datetime import datetime,timedelta,timezone
import csv
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def worker(mirror):
    original_data=(ROOT/'backend/data').resolve();backend=mirror/'backend'
    def guard(event,args):
        if event=='open':
            try:path=Path(args[0]).resolve()
            except TypeError:return
            if path.is_relative_to(original_data):raise RuntimeError('ORIGINAL_ACADEMIC_READ_REJECTED')
            mode=args[1] if isinstance(args[1],str) else ''
            flags=args[2] if len(args)>2 and isinstance(args[2],int) else 0
            if path.is_relative_to(ROOT) and (any(c in mode for c in 'wax+') or flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC)):
                raise RuntimeError('ORIGINAL_REPOSITORY_WRITE_REJECTED')
        if event in ('socket.connect','sqlite3.connect') or event.startswith('psycopg'):raise RuntimeError('DATABASE_NETWORK_REJECTED')
    sys.addaudithook(guard);sys.path.insert(0,str(backend))
    import pytest
    from services import ga_checkpoint_service as codec
    from services.ga_progress_service import input_fingerprint
    expected=json.loads((mirror/'fixture-contract.json').read_text(encoding='utf-8'))
    assert codec.engine_fingerprint()==expected['original_engine_fingerprint']
    assert input_fingerprint()==expected['fictional_input_fingerprint']
    capture=io.StringIO()
    with redirect_stdout(capture),redirect_stderr(capture):
        code=pytest.main(['-p','no:cacheprovider','tests/d10/test_v1_baseline.py','-q','--tb=short','--show-capture=no','--basetemp',str(mirror/'pytest')])
    artifacts=list((mirror/'pytest').rglob('checkpoint-*.json.gz'));verified=0
    for path in artifacts:
        envelope=json.loads(gzip.decompress(path.read_bytes()));payload=envelope['payload']
        assert hashlib.sha256(codec.canonical(payload)).hexdigest()==envelope['sha256']
        assert payload['engine_fingerprint']==expected['original_engine_fingerprint']
        assert payload['input_fingerprint']==expected['fictional_input_fingerprint']
        assert payload['source_inputs']==expected['fictional_source_inputs']
        verified+=1
    assert code!=0 or verified==3
    assert all(sha(backend/p)==h for p,h in expected['source_hashes'].items())
    return {'selection':'v1-mirror','exit_code':code,'stdout':capture.getvalue(),'stderr':'',
        'verified_fictional_checkpoint_archives':verified,'source_files_byte_identical':len(expected['source_hashes']),
        'engine_fingerprint_matches_original_current_release':True,'engine_fingerprint':codec.engine_fingerprint(),
        'fictional_input_fingerprint':input_fingerprint(),'actual_owned_input_fingerprint_verified':True,
        'original_academic_access_permitted':False,'fingerprint_functions_replaced':False,
        'scope':'Original V1 source and four original tests unchanged in owned temporary mirror. Actual source_inputs archives equal generated fictional files. No workspace academic reads or PostgreSQL.'}


def main():
    if len(sys.argv)==3 and sys.argv[1]=='--worker':
        with open(os.devnull,'w') as sink,redirect_stdout(sink),redirect_stderr(sink):result=worker(Path(sys.argv[2]))
        print(json.dumps(result));return result['exit_code']
    zone=timezone(timedelta(hours=8));started=datetime.now(zone)
    directory=BASE/(started.strftime('%Y%m%dT%H%M%S%f+0800')+'-v1-mirror');directory.mkdir(exist_ok=False)
    sys.path.insert(0,str(ROOT/'backend'))
    from benchmarks.retention_runtime import runtime,CSV_SCHEMAS,JSON_SCHEMAS
    runtime()
    from services.ga_checkpoint_service import engine_fingerprint
    from services.evidence_sanitization import sanitize_tree
    original=engine_fingerprint()
    paths=[p for p in subprocess.check_output(['git','ls-files','-z','backend'],cwd=ROOT).decode().split('\0') if p]
    test_paths={'backend/tests/__init__.py','backend/tests/conftest.py','backend/tests/d10/__init__.py',
                'backend/tests/d10/support.py','backend/tests/d10/test_v1_baseline.py'}
    sources=[p for p in paths if p.endswith('.py') and (not p.startswith('backend/tests/') or p in test_paths)]
    sources.append('backend/services/fitness_policy_compatibility.json')
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','PATHEXT'}}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    with tempfile.TemporaryDirectory(prefix='phase6-v1-source-') as temporary:
        mirror=Path(temporary).resolve();assert mirror.name.startswith('phase6-v1-source-') and not mirror.is_relative_to(ROOT)
        hashes={}
        for relative in sources:
            source=ROOT/relative;target=mirror/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
            assert sha(target)==sha(source);hashes[Path(relative).relative_to('backend').as_posix()]=sha(source)
        data=mirror/'backend/data';data.mkdir()
        for name,columns in CSV_SCHEMAS.items():
            with (data/name).open('w',encoding='utf-8',newline='') as stream:csv.writer(stream).writerow(columns)
        for name,value in {**JSON_SCHEMAS,'faculty_preferences.json':[],'ga_settings.json':runtime()[3]().to_dict()}.items():
            (data/name).write_bytes(json.dumps(value).encode())
        digest=hashlib.sha256();source_inputs={}
        for path in sorted(data.iterdir()):
            relative=str(path.relative_to(mirror/'backend'));digest.update(relative.encode());digest.update(path.read_bytes())
            source_inputs[relative]=path.read_text(encoding='utf-8-sig')
        expected={'source_hashes':hashes,'original_engine_fingerprint':original,
            'fictional_input_fingerprint':digest.hexdigest(),'fictional_source_inputs':source_inputs}
        (mirror/'fixture-contract.json').write_bytes(json.dumps(expected).encode())
        reply=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--worker',str(mirror)],cwd=mirror/'backend',env=env,
                             capture_output=True,text=True,encoding='utf-8',timeout=300)
        if reply.stdout.startswith('{'):result=json.loads(reply.stdout)
        else:result={'selection':'v1-mirror','exit_code':reply.returncode,'stdout':'','stderr':'','status':'MIRROR_WORKER_PROTOCOL_FAILED','raw_error_withheld':True}
    result=sanitize_tree(result);result.update(started_at=started.isoformat(),finished_at=datetime.now(zone).isoformat())
    (directory/'command.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps(result));print(directory.relative_to(ROOT).as_posix());return result['exit_code']


if __name__=='__main__':raise SystemExit(main())
