"""User-terminal SELECT-only D15 preflight; no credential command arguments."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from d15_target_guard import SafetyError, read_only_preflight

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
ZONE = timezone(timedelta(hours=8))


class PublicParser(argparse.ArgumentParser):
    def error(self, message):
        # Unknown command arguments could themselves contain pasted secrets.
        self.exit(2, 'D15 preflight rejects unsupported arguments; values withheld.\n')


def verify_preservation():
    baseline = json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'))
    if any(not (ROOT/p).is_file() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != h for p, h in baseline.items()):
        raise SafetyError('REPOSITORY_PRESERVATION_CHANGED')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()
    if head != 'c6baad2a0d59515555b33c84eca337a78a913a65':
        raise SafetyError('REPOSITORY_BASELINE_CHANGED')


def main():
    parser = PublicParser(description='Pristine D15 read-only preflight; no migrations or test writes')
    parser.add_argument('--read-only', action='store_true', help='Explicitly permit a single read-only D15 connection')
    args = parser.parse_args()
    started = datetime.now(ZONE)
    result = {'status': 'REJECTED', 'writes_performed': False}
    code = 1
    try:
        verify_preservation()
        result = {'status': 'READ_ONLY_PREFLIGHT_PASSED', **read_only_preflight(allow_connect=args.read_only)}
        verify_preservation()
        code = 0
    except SafetyError as error:
        result['status'] = 'REJECTED'
        result['error_code'] = error.code
    except Exception:
        result = {'status': 'REJECTED', 'error_code': 'PREFLIGHT_INFRASTRUCTURE_FAILED', 'writes_performed': False}
    record = {'kind': 'D15 read-only PostgreSQL preflight', 'observer': 'LOCAL_OPERATOR_EXECUTION',
              'started_at': started.isoformat(), 'finished_at': datetime.now(ZONE).isoformat(),
              'command': ['.venv/Scripts/python.exe', '-B', 'docs/testing/dashboard-d15/preflight.py', *(['--read-only'] if args.read_only else [])],
              'scope': 'One exact-target SELECT-only connection; no migrations, fixtures or cleanup DDL',
              'credential_handling': 'D15_TEST_DATABASE_URL read privately from this process; no URL/password retained',
              'exit_code': code, 'result': result}
    destination = BASE/(datetime.now(ZONE).strftime('%Y%m%dT%H%M%S%f+0800')+'-read-only-preflight')
    destination.mkdir(exist_ok=False)
    (destination/'result.json').write_bytes((json.dumps(record, indent=2, ensure_ascii=True)+'\n').encode('utf-8'))
    print(json.dumps({'evidence': destination.relative_to(ROOT).as_posix(), **result}, ensure_ascii=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
