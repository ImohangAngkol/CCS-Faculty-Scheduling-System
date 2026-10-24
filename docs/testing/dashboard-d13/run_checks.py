"""Owned offline/fictional D13 validation; no database credentials inherited."""
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
previous = runpy.run_path(str(ROOT/'docs/testing/dashboard-d12/run_checks.py'))
COMMANDS = dict(previous['COMMANDS'])
SCOPES = dict(previous['SCOPES'])
COMMANDS['focused'] = ([str(ROOT/'.venv/Scripts/python.exe'),'-B','-m','pytest','-p','no:cacheprovider','tests/dashboard/test_schedule_applications.py','tests/dashboard/test_application_migration.py','tests/dashboard/test_application_trust.py','-q','--tb=short','--show-capture=no'],ROOT/'backend')
SCOPES['focused']='D13 actual FastAPI/auth/transactional SQLite with fictional independent publisher, Chair and published schedule; PostgreSQL SQL rendering only'
COMMANDS['contracts']=(['node','--test','tests/scheduleApplications.test.mjs',*COMMANDS['contracts'][0][2:]],ROOT/'frontend')
COMMANDS['d12-backend']=previous['COMMANDS']['focused']
SCOPES['d12-backend']=previous['SCOPES']['focused']
COMMANDS['d13-live']=([str(ROOT/'.venv/Scripts/python.exe'),'-B','-m','pytest','-p','no:cacheprovider','tests/dashboard/test_applications_live.py','-q','-s','--tb=short','--show-capture=no'],ROOT/'backend')
COMMANDS['lint']=(['node','node_modules/eslint/bin/eslint.js','src/api/scheduleApplications.ts','src/api/scheduleApplicationModel.ts','src/api/adjustments.ts','src/services/scheduleService.ts','src/pages/admin/ScheduleApplications.tsx','src/pages/faculty/AdjustmentRequests.tsx','src/pages/faculty/MySchedule.tsx','src/components/common/AccountMenu.tsx','src/components/common/ApplicationReviewLink.tsx','src/routes/AppRoutes.tsx'],ROOT/'frontend')
SCOPES['d13-live']='Actual Edge/React to owned FastAPI/SQLite with real auth and fictional independent application/Chair/publication providers; no PostgreSQL or genuine institutional authority'
COMMANDS['publication-preservation']=([str(ROOT/'.venv/Scripts/python.exe'),'-B','-m','pytest','-p','no:cacheprovider','tests/dashboard/test_schedule_applications.py::test_full_application_versions_own_view_and_immutable_history','-q','--tb=short','--show-capture=no'],ROOT/'backend')
SCOPES['publication-preservation']='Additional exact RNG-state and synthetic original-source byte preservation assertion across real D13 SQLite application, replay, version/history and own timetable reads'




def main():
    key=sys.argv[1];command,cwd=COMMANDS[key]
    stamp=datetime.now(ZONE).strftime('%Y%m%dT%H%M%S%f+0800')+'-'+key
    evidence=ROOT/'docs/testing/dashboard-d13'/stamp;evidence.mkdir(exist_ok=False)
    allowed={'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','HOMEDRIVE','HOMEPATH','PATHEXT','NUMBER_OF_PROCESSORS','OS','SYSTEMDRIVE','ALLUSERSPROFILE','PUBLIC','PROGRAMW6432','PROCESSOR_ARCHITECTURE','USERNAME','USERDOMAIN'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',PYTHONUTF8='1')
    if cwd==ROOT/'backend':
        owned=Path(tempfile.gettempdir())/('d13-pytest-'+stamp)
        if owned.exists():raise RuntimeError('Refusing existing temporary root')
        command=[*command,'--basetemp',str(owned)]
    if key == 'd13-live':
        env['D13_SCREENSHOT_DIR']=str(ROOT/'docs/screenshots/dashboard-d13'/stamp)
    tick=time.monotonic();started=datetime.now(ZONE).isoformat()
    result=subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
    sys.path.insert(0,str(ROOT/'backend'))
    from services.evidence_sanitization import sanitize_tree
    record=sanitize_tree({'check':key,'command':command,'cwd':str(cwd.relative_to(ROOT)), 'started_at':started,'finished_at':datetime.now(ZONE).isoformat(),'elapsed_seconds':round(time.monotonic()-tick,3),'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'scope':SCOPES[key], 'environment':'Whitelisted OS variables only; database URLs/credentials/approval flags excluded','sanitization':'Whole sensitive assignment/header lines, full/truncated signed receipts, bearer values, credential URIs and private keys filtered before writing'})
    (evidence/'command.json').write_text(json.dumps(record,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
    print(json.dumps({'evidence':evidence.relative_to(ROOT).as_posix(),'exit_code':result.returncode,'stdout_tail':record['stdout'][-4500:],'stderr_tail':record['stderr'][-1200:]},ensure_ascii=True))
    return result.returncode


if __name__=='__main__':raise SystemExit(main())
