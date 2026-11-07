"""New U5J command records only; existing milestone tools/evidence stay sealed."""
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

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
COMMANDS={'consumption': ['C:\\Users\\User\\Desktop\\Genetic-Algorithm Dashboard\\.venv\\Scripts\\python.exe',
                 '-B',
                 '-m',
                 'pytest',
                 '-p',
                 'no:cacheprovider',
                 '-q',
                 'tests/test_ga_bundle_optimizer.py'],
 'receipt-isolation': ['C:\\Users\\User\\Desktop\\Genetic-Algorithm Dashboard\\.venv\\Scripts\\python.exe',
                       '-B',
                       '-m',
                       'pytest',
                       '-p',
                       'no:cacheprovider',
                       '-q',
                       'tests/test_ga_input_receipt.py::test_distinct_thread_observations_are_isolated_not_a_concurrent_engine_claim'],
 'receipts': ['C:\\Users\\User\\Desktop\\Genetic-Algorithm Dashboard\\.venv\\Scripts\\python.exe',
              '-B',
              '-m',
              'pytest',
              '-p',
              'no:cacheprovider',
              '-q',
              'tests/test_ga_input_receipt.py'],
 'analysis': ['C:\\Users\\User\\Desktop\\Genetic-Algorithm Dashboard\\.venv\\Scripts\\python.exe',
              '-B',
              '-m',
              'pytest',
              '-p',
              'no:cacheprovider',
              '-q',
              'tests/test_advanced_ga_analysis.py'],
 'backend': ['C:\\Users\\User\\Desktop\\Genetic-Algorithm Dashboard\\.venv\\Scripts\\python.exe',
             '-B',
             '-m',
             'pytest',
             '-p',
             'no:cacheprovider',
             '-q',
             'tests/test_continuous_readiness.py'],
 'backend-regressions': ['C:\\Users\\User\\Desktop\\Genetic-Algorithm Dashboard\\.venv\\Scripts\\python.exe',
                         '-B',
                         '-m',
                         'pytest',
                         '-p',
                         'no:cacheprovider',
                         '-q',
                         'tests/test_ga_source_qualification.py',
                         'tests/test_ga_academic_context.py',
                         'tests/test_ga_result_compatibility.py'],
 'frontend': ['node',
              '--test',
              'tests/academicContext.test.mjs',
              'tests/currentEvaluation.test.mjs',
              'tests/evaluationCoverage.test.mjs',
              'tests/dashboardControls.test.mjs',
              'tests/resultPresentation.test.mjs',
              'tests/auth.test.mjs',
              'tests/authSessionRace.test.mjs',
              'tests/dashboardD1.test.mjs',
              'tests/mySchedule.test.mjs',
              'tests/preferenceModel.test.mjs',
              'tests/preferenceApi.test.mjs',
              'tests/gaMonitoring.test.mjs',
              'tests/gaRecovery.test.mjs',
              'tests/gaLogs.test.mjs',
              'tests/gaHistory.test.mjs',
              'tests/fitnessReporting.test.mjs',
              'tests/facultyDisplay.test.mjs',
              'tests/continuousOptimization.test.mjs',
              'tests/advancedAnalysis.test.mjs',
              'tests/advancedAnalysisInteraction.test.mjs'],
 'build': ['node', 'node_modules/typescript/bin/tsc', '-b'],
 'bundle': ['node', 'node_modules/vite/bin/vite.js', 'build'],
 'lint': ['node',
          'node_modules/eslint/bin/eslint.js',
          'src/components/ga/OptimizationMode.tsx',
          'src/services/continuousOptimization.ts',
          'src/pages/admin/GenerateSchedule.tsx'],
 'browser': ['node', '--test', 'tests/continuousOptimization.browser.test.mjs'],
 'integrity': ['git',
               '-c',
               'safe.directory=C:\\Users\\User\\Desktop\\Genetic-Algorithm Dashboard',
               'fsck',
               '--no-reflogs'],
 'bundle-tests': ['C:\\Users\\User\\Desktop\\Genetic-Algorithm Dashboard\\.venv\\Scripts\\python.exe',
                  '-B',
                  '-m',
                  'pytest',
                  '-p',
                  'no:cacheprovider',
                  '-q',
                  'tests/test_ga_input_bundle.py']}
for command in COMMANDS.values():
    if command[0].endswith('python.exe'):command[0]=str(ROOT/'.venv/Scripts/python.exe')
COMMANDS['integrity']=['git','-c','safe.directory='+str(ROOT),'fsck','--no-reflogs']

def main():
    selection=sys.argv[1];cmd=COMMANDS[selection]
    target=BASE/(datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')+'-'+selection);target.mkdir(exist_ok=False)
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE','PROGRAMFILES','PROGRAMFILES(X86)'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed};env.update(PYTHONDONTWRITEBYTECODE='1',VITE_API_URL='http://localhost:57999')
    # The browser harness accepts this destination; its sealed original evidence
    # is never written. Responses remain intercepted and fictional.
    if selection=='browser':env['U5F_EVIDENCE_DIR']=str(target)
    backend=selection.startswith('backend') or selection in {'bundle-tests','receipts','analysis','consumption','receipt-isolation'}
    if backend:cmd=[*cmd,'--basetemp',str(Path(tempfile.gettempdir())/('ga-u5j-check-'+uuid4().hex))]
    start=datetime.now().astimezone().isoformat();tick=time.perf_counter()
    try:
        result=subprocess.run(cmd,cwd=ROOT/('backend' if backend else 'frontend'),env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
        code=result.returncode;out=result.stdout;err=result.stderr
    except subprocess.TimeoutExpired as error:
        decode=lambda v:v.decode('utf-8',errors='replace') if isinstance(v,bytes) else v or ''
        code=124;out=decode(error.stdout);err=decode(error.stderr)+'\nBound exceeded; owned process cleanup requires review.'
    row=dict(selection=selection,command=cmd,started_at=start,ended_at=datetime.now().astimezone().isoformat(),elapsed_seconds=time.perf_counter()-tick,exit_code=code,stdout=out,stderr=err,
        scope='Fictional temporary fixtures only; no PostgreSQL. Browser HTTP intercepted, not live GA acceptance. Legacy APIs remain unverified; the new versioned internal entry qualifies technical bundle consumption only, without institutional source authority.')
    (target/'command.json').write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(selection=selection,exit_code=code,evidence=target.relative_to(ROOT).as_posix(),summary=out[-1600:],stderr=err[-800:])))
    return code

if __name__=='__main__':raise SystemExit(main())
