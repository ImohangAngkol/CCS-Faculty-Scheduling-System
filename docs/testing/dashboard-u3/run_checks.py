"""Frontend-only U3 checks. No backend import, credential inheritance or database access."""
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
COMMANDS = {
    'focused': ['node', '--test', 'tests/evaluationCoverage.test.mjs'],
    'regressions': ['node', '--test', 'tests/dashboardControls.test.mjs', 'tests/resultPresentation.test.mjs', 'tests/auth.test.mjs', 'tests/authSessionRace.test.mjs', 'tests/dashboardD1.test.mjs', 'tests/mySchedule.test.mjs', 'tests/preferenceModel.test.mjs', 'tests/preferenceApi.test.mjs', 'tests/gaMonitoring.test.mjs', 'tests/gaRecovery.test.mjs', 'tests/gaLogs.test.mjs', 'tests/gaHistory.test.mjs', 'tests/fitnessReporting.test.mjs', 'tests/facultyDisplay.test.mjs'],
    'build': ['node', 'node_modules/typescript/bin/tsc', '-b'],
    'bundle': ['node', 'node_modules/vite/bin/vite.js', 'build'],
    'lint': ['node', 'node_modules/eslint/bin/eslint.js', 'src/pages/admin/ChromosomeViewer.tsx', 'src/pages/admin/ScheduleView.tsx', 'src/pages/admin/FitnessAnalysis.tsx', 'src/services/facultyCoverage.ts', 'src/services/workloadPresentation.ts', 'src/components/ga/WorkloadChart.tsx'],
    'browser': ['node', '--test', 'tests/evaluationCoverage.browser.test.mjs'],
    'u1-browser': ['node', '--test', 'tests/resultPresentation.browser.test.mjs'],
    'preferences-browser': ['node', '--test', 'tests/preferences.browser.test.mjs'],
    'u2-browser': ['node', '--test', 'tests/dashboardControls.browser.test.mjs'],
    'ga-browser': ['node', '--test', 'tests/gaMonitoring.browser.test.mjs'],
}


def main():
    selection = sys.argv[1]
    command = COMMANDS[selection]
    stamp = datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')
    target = BASE / (stamp + '-' + selection)
    target.mkdir(exist_ok=False)
    allowed = {'SYSTEMROOT', 'WINDIR', 'PATH', 'PATHEXT', 'TEMP', 'TMP', 'COMSPEC', 'LOCALAPPDATA', 'APPDATA', 'USERPROFILE', 'PROGRAMFILES', 'PROGRAMFILES(X86)'}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env['VITE_API_URL'] = 'http://localhost:57999'  # Unprivileged origin; intercepted before network.
    if selection in {'ga-browser', 'preferences-browser', 'preferences-baseline'}:
        env['VITE_API_URL'] = 'http://localhost:8000'  # Original suite intercepts this exact origin.
    if selection == 'browser':
        env['U3_EVIDENCE_DIR'] = str(target)
    start = datetime.now().astimezone().isoformat()
    tick = time.perf_counter()
    timed_out = False
    try:
        result = subprocess.run(command, cwd=ROOT / 'frontend', env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
    except subprocess.TimeoutExpired as error:
        timed_out = True
        decode = lambda value: value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value or ''
        result = SimpleNamespace(returncode=124, stdout=decode(error.stdout), stderr=decode(error.stderr)+'\nOwned test runner exceeded its 300-second limit. Test completion/child cleanup must be reviewed.\n')
    record = dict(selection=selection, command=command, cwd='frontend', started_at=start,
                  ended_at=datetime.now().astimezone().isoformat(), elapsed_seconds=time.perf_counter()-tick,
                  exit_code=result.returncode, timed_out=timed_out, stdout=result.stdout, stderr=result.stderr,
                  scope='Frontend only; browser API data is fictional/intercepted, no FastAPI or PostgreSQL acceptance.')
    (target / 'command.json').write_text(json.dumps(record, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps(dict(selection=selection, exit_code=result.returncode, evidence=target.relative_to(ROOT).as_posix(), summary=result.stdout[-1100:], stderr=result.stderr[-1500:]), ensure_ascii=True))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
