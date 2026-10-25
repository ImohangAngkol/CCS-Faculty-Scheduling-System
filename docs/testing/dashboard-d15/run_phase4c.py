"""Private-terminal first PostgreSQL acceptance phase. No reset or auto-retry."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from d15_target_guard import SafetyError, designated_target
from preflight import PublicParser, verify_preservation

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
ZONE = timezone(timedelta(hours=8))


def main():
    parser = PublicParser(description='D15 exact-target original 17 Phase4C PostgreSQL assertions; target schema will be retained')
    parser.add_argument('--execute', action='store_true', help='Explicitly authorize this first write-enabled D15 acceptance phase')
    args = parser.parse_args()
    try:
        if not args.execute:
            raise SafetyError('EXPLICIT_ACCEPTANCE_EXECUTION_FLAG_REQUIRED')
        verify_preservation()
        designated_target()  # Parse/validate privately; never render the URL.
    except SafetyError as error:
        print(json.dumps({'status': 'REJECTED_BEFORE_EXECUTION', 'error_code': error.code}))
        return 1
    except Exception:
        print(json.dumps({'status': 'REJECTED_BEFORE_EXECUTION', 'error_code': 'ACCEPTANCE_PREPARATION_FAILED'}))
        return 1
    started = datetime.now(ZONE)
    stamp = started.strftime('%Y%m%dT%H%M%S%f+0800')+'-phase4c-postgresql'
    evidence = BASE/stamp
    evidence.mkdir(exist_ok=False)
    owned = Path(tempfile.gettempdir())/('d15-postgresql-'+stamp)
    if owned.exists():
        raise SafetyError('OWNED_TEMP_ALREADY_EXISTS')
    allowed = {'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA',
               'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMDATA', 'HOMEDRIVE', 'HOMEPATH', 'PATHEXT',
               'NUMBER_OF_PROCESSORS', 'OS', 'SYSTEMDRIVE', 'ALLUSERSPROFILE', 'PUBLIC', 'PROGRAMW6432',
               'PROCESSOR_ARCHITECTURE', 'USERNAME', 'USERDOMAIN'}
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8', PYTHONUTF8='1',
        PYTHONPATH=os.pathsep.join((str(BASE), str(ROOT/'backend'))),
        D15_TEST_DATABASE_URL=os.environ['D15_TEST_DATABASE_URL'],
        D15_ACCEPTANCE_RUN='I_APPROVE_D15_PHASE4C_ACCEPTANCE', D15_ACCEPTANCE_EVIDENCE=str(evidence))
    command = [sys.executable, '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-p', 'd15_phase4c_plugin', '--noconftest',
        'docs/testing/dashboard-d15/test_phase4c_d15.py', '-q', '-x', '--tb=no', '--show-capture=no', '--basetemp', str(owned)]
    tick = time.monotonic()
    code = 1
    stdout = stderr = ''
    infrastructure = None
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as error:
        infrastructure = 'OWNED_ACCEPTANCE_DEADLINE_EXCEEDED'
        stdout = error.stdout or b''
        stderr = error.stderr or b''
        if isinstance(stdout, bytes): stdout = stdout.decode('utf-8', errors='replace')
        if isinstance(stderr, bytes): stderr = stderr.decode('utf-8', errors='replace')
    except Exception:
        infrastructure = 'OWNED_ACCEPTANCE_PROCESS_FAILED'
    try:
        verify_preservation()
    except Exception:
        infrastructure, code = 'REPOSITORY_PRESERVATION_CHANGED', 1
    sys.path.insert(0, str(ROOT/'backend'))
    from services.evidence_sanitization import sanitize_tree
    record = sanitize_tree({'check': 'phase4c-postgresql', 'command': command, 'cwd': '.',
        'started_at': started.isoformat(), 'finished_at': datetime.now(ZONE).isoformat(),
        'elapsed_seconds': round(time.monotonic()-tick, 3), 'exit_code': code,
        'stdout': stdout, 'stderr': stderr, 'infrastructure_error': infrastructure,
        'scope': 'Actual PostgreSQL only: original 17 Phase4C assertions; initially pristine exact D15 target; independent guarded connections; retained schema',
        'environment': 'Whitelisted OS plus dedicated private D15 URL and controlled runner flags; no DATABASE_URL or PG defaults inherited',
        'cleanup': 'No reset/drop/reseed/cleanup DDL. Original empty-table downgrade cases are rollback-only assertions on newly created objects.'})
    (evidence/'command.json').write_bytes((json.dumps(record, indent=2, ensure_ascii=True)+'\n').encode('utf-8'))
    summary = None
    if (evidence/'pytest-results.json').is_file():
        summary = json.loads((evidence/'pytest-results.json').read_text(encoding='utf-8'))['counts']
    guarded = None
    if (evidence/'connection-guard-summary.json').is_file():
        guarded = json.loads((evidence/'connection-guard-summary.json').read_text(encoding='utf-8'))
    safe_cleanup = (guarded is not None and guarded.get('guard') == 'd15-academic-write.1'
        and guarded.get('target') == 'ccs_ga_d15_test' and guarded.get('role') == 'ccs_ga_d15_tester'
        and guarded.get('owned_connections_closed') is True and guarded.get('cleanup_DDL_executed') is False
        and guarded.get('counts', {}).get('physical_connections', 0) > 0
        and guarded.get('counts', {}).get('identity_checks', 0) >= guarded.get('counts', {}).get('physical_connections', 0))
    status = 'ACCEPTANCE_PHASE_PASSED' if code == 0 and safe_cleanup and summary == {'PASSED': 17, 'FAILED': 0, 'ERROR': 0, 'SKIPPED': 0, 'NOT_RUN': 0} else 'STOP_REVIEW_REQUIRED'
    print(json.dumps({'status': status, 'evidence': evidence.relative_to(ROOT).as_posix(), 'exit_code': code,
                      'counts': summary, 'infrastructure_error': infrastructure, 'database': 'ccs_ga_d15_test',
                      'schema_retained': True, 'owned_connection_cleanup_verified': safe_cleanup,
                      'next_action': 'Return this public result for review; do not retry or reset automatically'}))
    return 0 if status == 'ACCEPTANCE_PHASE_PASSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
