"""U5F foundation checks. Reuse existing selections; write only new evidence."""
from datetime import datetime
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
COMMANDS=runpy.run_path(str(ROOT/'docs/testing/dashboard-u5e/run_checks.py'))['COMMANDS']
COMMANDS.update(focused=['node','--test','tests/continuousOptimization.test.mjs'],
    **{'u5e-contracts':['node','--test','tests/advancedAnalysis.test.mjs','tests/advancedAnalysisInteraction.test.mjs']},
    **{'backend-regressions':[str(ROOT/'.venv/Scripts/python.exe'),'-B','-m','pytest','-p','no:cacheprovider','-q','tests/test_ga_source_qualification.py','tests/test_ga_academic_context.py','tests/test_ga_result_compatibility.py']},
    browser=['node','--test','tests/continuousOptimization.browser.test.mjs'],
    lint=['node','node_modules/eslint/bin/eslint.js','src/components/ga/OptimizationMode.tsx','src/services/continuousOptimization.ts','src/pages/admin/GenerateSchedule.tsx'],
    backend=[str(ROOT/'.venv/Scripts/python.exe'),'-B','-m','pytest','-p','no:cacheprovider','-q','tests/test_continuous_readiness.py'],
    receipts=[str(ROOT/'.venv/Scripts/python.exe'),'-B','-m','pytest','-p','no:cacheprovider','-q','tests/test_ga_input_receipt.py'])

def main():
    selection=sys.argv[1];command=COMMANDS[selection]
    target=BASE/(datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')+'-'+selection);target.mkdir(exist_ok=False)
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE','PROGRAMFILES','PROGRAMFILES(X86)'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed}
    env.update(PYTHONDONTWRITEBYTECODE='1',VITE_API_URL='http://localhost:57999')
    if selection=='browser':env['U5F_EVIDENCE_DIR']=str(target)
    backend=selection.startswith('backend') or selection=='receipts'
    if backend:command=[*command,'--basetemp',str(Path(tempfile.gettempdir())/('ga-u5f-'+uuid4().hex))]
    tick=time.perf_counter();start=datetime.now().astimezone().isoformat()
    try:
        result=subprocess.run(command,cwd=ROOT/('backend' if backend else 'frontend'),env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
        code=result.returncode;out=result.stdout;err=result.stderr
    except subprocess.TimeoutExpired as error:
        code=124;out=error.stdout or b'';err=error.stderr or b''
        if isinstance(out,bytes):out=out.decode('utf-8',errors='replace')
        if isinstance(err,bytes):err=err.decode('utf-8',errors='replace')
        err+='\nBound exceeded; incomplete result, owned child cleanup must be reviewed.'
    value=dict(selection=selection,command=command,started_at=start,ended_at=datetime.now().astimezone().isoformat(),elapsed_seconds=time.perf_counter()-tick,exit_code=code,stdout=out,stderr=err,
        scope='Fictional temporary fixtures only. Browser responses intercepted; no institutional database, live sessions or production authority.')
    (target/'command.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(selection=selection,exit_code=code,evidence=target.relative_to(ROOT).as_posix(),summary=out[-1400:],stderr=err[-800:])))
    return code

if __name__=='__main__':raise SystemExit(main())
