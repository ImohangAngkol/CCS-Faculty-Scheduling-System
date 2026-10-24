"""Owned offline/fictional D11 validation; no database credentials inherited."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
ZONE = timezone(timedelta(hours=8))
previous = runpy.run_path(str(ROOT/'docs/testing/dashboard-d10/run_compatibility_checks.py'))
COMMANDS = dict(previous['COMMANDS'])
SCOPES = dict(previous['SCOPES'])
COMMANDS['focused'] = ([str(ROOT/'.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', 'tests/dashboard/test_adjustments.py', 'tests/dashboard/test_adjustment_migration.py', '-q', '--tb=short', '--show-capture=no'], ROOT/'backend')
SCOPES['focused'] = 'D11 real FastAPI sessions/ownership and SQLAlchemy transactions, fictional guarded schedule/catalog and owned SQLite; offline PostgreSQL SQL rendering only'
COMMANDS['contracts'] = (['node','--test','tests/adjustments.test.mjs',*COMMANDS['contracts'][0][2:]], ROOT/'frontend')
COMMANDS['lint'] = (['node','node_modules/eslint/bin/eslint.js','src/api/adjustments.ts','src/pages/faculty/AdjustmentRequests.tsx','src/pages/faculty/Dashboard.tsx','src/pages/faculty/MySchedule.tsx','src/layouts/FacultyLayout.tsx','src/routes/AppRoutes.tsx'], ROOT/'frontend')
COMMANDS['d11-live'] = ([str(ROOT/'.venv/Scripts/python.exe'),'-B','-m','pytest','-p','no:cacheprovider','tests/dashboard/test_adjustments_live.py','-q','-s','--tb=short','--show-capture=no'],ROOT/'backend')
SCOPES['d11-live'] = 'Actual Edge/React to owned FastAPI/SQLite with real faculty authentication; fictional guarded schedule/term/resource source, no genuine authority or PostgreSQL'


def main():
    key=sys.argv[1];command,cwd=COMMANDS[key]
    stamp=datetime.now(ZONE).strftime('%Y%m%dT%H%M%S%f+0800')+'-'+key
    evidence=ROOT/'docs/testing/dashboard-d11'/stamp;evidence.mkdir(exist_ok=False)
    allowed={'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','HOMEDRIVE','HOMEPATH','PATHEXT','NUMBER_OF_PROCESSORS','OS','SYSTEMDRIVE','ALLUSERSPROFILE','PUBLIC','PROGRAMW6432','PROCESSOR_ARCHITECTURE','USERNAME','USERDOMAIN'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',PYTHONUTF8='1')
    if cwd==ROOT/'backend':
        owned=Path(tempfile.gettempdir())/('d11-pytest-'+stamp)
        if owned.exists():raise RuntimeError('Refusing existing temporary root')
        command=[*command,'--basetemp',str(owned)]
    if key in {'d11-live','v2-live','v2-browser'}:
        env['D11_SCREENSHOT_DIR']=str(ROOT/'docs/screenshots/dashboard-d11'/stamp)
    tick=time.monotonic();started=datetime.now(ZONE).isoformat()
    result=subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
    sys.path.insert(0,str(ROOT/'backend'))
    from services.evidence_sanitization import sanitize_tree
    record=sanitize_tree({'check':key,'command':command,'cwd':str(cwd.relative_to(ROOT)), 'started_at':started,'finished_at':datetime.now(ZONE).isoformat(),'elapsed_seconds':round(time.monotonic()-tick,3),'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'scope':SCOPES[key], 'environment':'Whitelisted OS variables only; database URLs/credentials/approval flags excluded','sanitization':'Whole sensitive assignment/header lines, full/truncated signed receipts, bearer values, credential URIs and private keys filtered before writing'})
    (evidence/'command.json').write_text(json.dumps(record,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
    print(json.dumps({'evidence':evidence.relative_to(ROOT).as_posix(),'exit_code':result.returncode,'stdout_tail':record['stdout'][-4500:],'stderr_tail':record['stderr'][-1200:]},ensure_ascii=True))
    return result.returncode


if __name__=='__main__':raise SystemExit(main())
