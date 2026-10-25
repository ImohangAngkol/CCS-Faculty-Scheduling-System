"""Public outcome recorder; never serializes exceptions, SQL params or locals."""
import json
import os
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent
CASES = {}
COLLECTED = []


def output_directory():
    directory = Path(os.environ.get('D15_ACCEPTANCE_EVIDENCE', '')).resolve()
    if directory.parent != BASE or not directory.name.endswith('-phase4c-postgresql') or not directory.is_dir():
        raise RuntimeError('Owned D15 evidence directory required; values withheld')
    return directory


def write_record(name, data):
    if name not in {'pytest-results.json', 'connection-guard-summary.json'}:
        raise RuntimeError('Unsupported public evidence record')
    with (output_directory()/name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=True)
        stream.write('\n')


def pytest_collection_finish(session):
    COLLECTED[:] = [item.nodeid for item in session.items]
    if len(COLLECTED) != 17:
        raise pytest.UsageError('D15 expects exactly the original 17 academic cases')


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == 'call' or report.failed or report.skipped:
        entry = CASES.setdefault(item.nodeid, {'id': item.nodeid, 'status': 'NOT_RUN'})
        if report.failed:
            entry.update(status='FAILED' if report.when == 'call' else 'ERROR', phase=report.when)
            error = call.excinfo.value if call.excinfo else None
            entry['exception_type'] = type(error).__name__
            from d15_target_guard import SafetyError
            if isinstance(error, SafetyError):
                entry['safety_code'] = error.code
            state = getattr(getattr(error, 'orig', None), 'pgcode', None)
            if isinstance(state, str) and len(state) == 5 and state.isalnum():
                entry['SQLSTATE'] = state
        elif report.skipped:
            entry['status'] = 'SKIPPED'
        elif entry['status'] == 'NOT_RUN':
            entry['status'] = 'PASSED'


def pytest_sessionfinish(session, exitstatus):
    rows = [CASES.get(id, {'id': id, 'status': 'NOT_RUN'}) for id in COLLECTED]
    write_record('pytest-results.json', {'scope': 'Actual D15 PostgreSQL original Phase4C assertions with D15 guarded fixtures',
        'collected': len(COLLECTED), 'exit_code': int(exitstatus),
        'counts': {status: sum(r['status'] == status for r in rows) for status in ('PASSED', 'FAILED', 'ERROR', 'SKIPPED', 'NOT_RUN')},
        'cases': rows, 'credentials_or_exception_payloads_recorded': False})
