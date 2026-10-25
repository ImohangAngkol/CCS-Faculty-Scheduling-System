"""D15 offline/SQLite regression evidence only. Never selects a live DB run.

The PostgreSQL selection only collects test IDs; it executes no test fixtures.
Connection credentials and approval flags are excluded from child environments.
"""
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
previous = runpy.run_path(str(ROOT/'docs/testing/dashboard-d14/run_checks.py'))
ALLOWED = {'academic-offline', 'backend', 'v2-engine', 'v2-api', 'd11-backend', 'd12-backend', 'd13-backend', 'focused'}
COMMANDS = {key: previous['COMMANDS'][key] for key in ALLOWED}
COMMANDS['postgres-collection'] = ([str(ROOT/'.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider',
    'tests/academic/test_academic_postgresql.py', '--collect-only', '-q'], ROOT/'backend')
COMMANDS['d15-guard'] = ([str(ROOT/'.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '--noconftest',
    'docs/testing/dashboard-d15/test_d15_target_guard.py', '-q', '--tb=short', '--show-capture=no'], ROOT)
COMMANDS['d15-write-guard'] = ([str(ROOT/'.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '--noconftest',
    'docs/testing/dashboard-d15/test_d15_target_guard.py', 'docs/testing/dashboard-d15/test_d15_write_guard.py', '-q', '--tb=short', '--show-capture=no'], ROOT)
COMMANDS['d15-phase4c-collection'] = ([str(ROOT/'.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '--noconftest',
    'docs/testing/dashboard-d15/test_phase4c_d15.py', '--collect-only', '-q'], ROOT)
COMMANDS['d15-workflow-guard'] = ([str(ROOT/'.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '--noconftest',
    'docs/testing/dashboard-d15/test_d15_target_guard.py', 'docs/testing/dashboard-d15/test_d15_write_guard.py',
    'docs/testing/dashboard-d15/test_d15_workflow_guard.py', 'docs/testing/dashboard-d15/test_d15_workflow_tooling.py',
    '-q', '--tb=short', '--show-capture=no'], ROOT)
COMMANDS['d15-workflow-rehearsal'] = ([str(ROOT/'.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '--noconftest',
    'docs/testing/dashboard-d15/test_workflow_rehearsal.py', '-q', '-x', '--tb=short', '--show-capture=no'], ROOT)
COMMANDS['d15-workflow-collection'] = ([str(ROOT/'.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '--noconftest',
    'docs/testing/dashboard-d15/test_workflows_d15.py', '--collect-only', '-q'], ROOT)


def main():
    key = sys.argv[1]
    command, cwd = COMMANDS[key]  # Fail closed for unlisted live/browser commands.
    stamp = datetime.now(ZONE).strftime('%Y%m%dT%H%M%S%f+0800')+'-'+key
    directory = ROOT/'docs/testing/dashboard-d15'/stamp
    directory.mkdir(exist_ok=False)
    allowed = {'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA',
               'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMDATA', 'HOMEDRIVE', 'HOMEPATH', 'PATHEXT',
               'NUMBER_OF_PROCESSORS', 'OS', 'SYSTEMDRIVE', 'ALLUSERSPROFILE', 'PUBLIC', 'PROGRAMW6432',
               'PROCESSOR_ARCHITECTURE', 'USERNAME', 'USERDOMAIN'}
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    env['PYTHONPATH'] = os.pathsep.join((str(ROOT/'docs/testing/dashboard-d15'), str(ROOT/'backend')))
    owned = Path(tempfile.gettempdir())/('d15-offline-'+stamp)
    if owned.exists():
        raise RuntimeError('Refusing an existing owned temporary target')
    command = [*command, '--basetemp', str(owned)]
    started = datetime.now(ZONE).isoformat()
    tick = time.monotonic()
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
    sys.path.insert(0, str(ROOT/'backend'))
    from services.evidence_sanitization import sanitize_tree
    record = sanitize_tree({'check': key, 'command': command, 'cwd': str(cwd.relative_to(ROOT)), 'started_at': started,
        'finished_at': datetime.now(ZONE).isoformat(), 'elapsed_seconds': round(time.monotonic()-tick, 3),
        'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr,
        'scope': ('Offline D15 target/write guard; fake DBAPI catalogs and blocked real connectors' if key in {'d15-guard', 'd15-write-guard', 'd15-workflow-guard'} else
                  'Collection only; no PostgreSQL fixtures or tests executed' if key in {'postgres-collection', 'd15-phase4c-collection', 'd15-workflow-collection'} else
                  'Owned fictional SQLite rehearsal of new workflow fixtures; NOT PostgreSQL migration, trigger or locking evidence' if key == 'd15-workflow-rehearsal' else previous['SCOPES'][key]),
        'database_scope': 'Offline/owned fictional SQLite only; no live PostgreSQL operation',
        'environment': 'Whitelisted OS variables only; all database URLs/credentials/approval flags excluded',
        'sanitization': 'Whole sensitive assignments/headers, full/truncated receipts, bearer values, credential URIs and private keys filtered before writing'})
    (directory/'command.json').write_bytes((json.dumps(record, indent=2, ensure_ascii=True)+'\n').encode('utf-8'))
    print(json.dumps({'path': directory.relative_to(ROOT).as_posix(), 'exit_code': result.returncode,
                      'stdout_tail': record['stdout'][-1200:], 'stderr_tail': record['stderr'][-600:]}))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
