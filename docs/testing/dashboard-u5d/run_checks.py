"""U5D isolated frontend/backend compatibility checks. No credential inheritance. Backend tests use temporary stores; No SQLite workflow suites selected. No PostgreSQL."""
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tempfile
from uuid import uuid4
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
COMMANDS = {
    'integrity': ['git', '-c', 'safe.directory='+str(ROOT), 'fsck', '--no-reflogs'],
    'backend': [str(ROOT / '.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q', 'tests/test_ga_input_receipt.py'],
    'backend-regressions': [str(ROOT / '.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q', 'tests/test_ga_source_qualification.py', 'tests/test_ga_academic_context.py', 'tests/test_ga_result_compatibility.py', 'tests/d10/test_v1_baseline.py', 'tests/d10/test_v2_engine.py'],
}
# Reuse committed frontend selections; U5D changes no UI or frontend API DTO.
import runpy
prior = runpy.run_path(str(ROOT/'docs/testing/dashboard-u5c/run_checks.py'))['COMMANDS']
COMMANDS.update({key: prior[key] for key in ['focused','regressions','build','bundle','lint']})


def main():
    selection = sys.argv[1]
    command = COMMANDS[selection]
    stamp = datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')
    target = BASE / (stamp + '-' + selection)
    target.mkdir(exist_ok=False)
    allowed = {'SYSTEMROOT', 'WINDIR', 'PATH', 'PATHEXT', 'TEMP', 'TMP', 'COMSPEC', 'LOCALAPPDATA', 'APPDATA', 'USERPROFILE', 'PROGRAMFILES', 'PROGRAMFILES(X86)'}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env['VITE_API_URL'] = 'http://localhost:57999'  # Unprivileged origin; intercepted before network.
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    temporary_base = None
    if selection.startswith('backend'):
        temporary_base = Path(tempfile.gettempdir()).resolve() / ('ga-u5d-pytest-' + uuid4().hex)
        assert not temporary_base.exists() and temporary_base.parent == Path(tempfile.gettempdir()).resolve()
        command = [*command, '--basetemp', str(temporary_base)]
    start = datetime.now().astimezone().isoformat()
    tick = time.perf_counter()
    timed_out = False
    try:
        result = subprocess.run(command, cwd=ROOT / ('backend' if selection.startswith('backend') else 'frontend'), env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
    except subprocess.TimeoutExpired as error:
        timed_out = True
        decode = lambda value: value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value or ''
        result = SimpleNamespace(returncode=124, stdout=decode(error.stdout), stderr=decode(error.stderr)+'\nOwned test runner exceeded its 300-second limit. Test completion/child cleanup must be reviewed.\n')
    record = dict(selection=selection, command=command, cwd='backend' if selection.startswith('backend') else 'frontend', started_at=start,
                  ended_at=datetime.now().astimezone().isoformat(), elapsed_seconds=time.perf_counter()-tick,
                  exit_code=result.returncode, timed_out=timed_out, temporary_base_new=str(temporary_base) if temporary_base else None, stdout=result.stdout, stderr=result.stderr,
                  scope='Isolated fictional fixtures; browser HTTP is intercepted, backend tests use ASGI/temporary files, no database writes. No PostgreSQL or institutional acceptance.')
    (target / 'command.json').write_text(json.dumps(record, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps(dict(selection=selection, exit_code=result.returncode, evidence=target.relative_to(ROOT).as_posix(), summary=result.stdout[-1100:], stderr=result.stderr[-1500:]), ensure_ascii=True))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
