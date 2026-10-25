"""Public outcome recorder; never serializes exceptions, SQL params or locals."""
import json
import os
import re
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent
CASES = {}
COLLECTED = []
SCOPE = 'Actual D15 PostgreSQL D9-D13 services, migrations and fictional trust providers; in-process FastAPI, not browser evidence'


def output_directory():
    directory = Path(os.environ.get('D15_ACCEPTANCE_EVIDENCE', '')).resolve()
    if directory.parent != BASE or not directory.name.endswith('-workflows-postgresql') or not directory.is_dir():
        raise RuntimeError('Owned D15 evidence directory required; values withheld')
    return directory


def write_record(name, data):
    if name not in {'pytest-results.json', 'connection-guard-summary.json', 'retained-schema.json', 'upgraded-schema.json'}:
        raise RuntimeError('Unsupported public evidence record')
    with (output_directory()/name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=True)
        stream.write('\n')


def pytest_collection_finish(session):
    COLLECTED[:] = [item.nodeid for item in session.items]
    expected = [
        'test_01_additive_upgrade_atomic_rollback_then_commit',
        'test_02_durable_confirmation_revision_and_concurrent_one_winner',
        'test_03_postgresql_ledger_triggers_and_row_lock_recovery',
        'test_04_actual_v2_generation_from_postgresql_heads',
        'test_05_owned_request_submit_unauthorized_and_idempotency',
        'test_06_independent_chair_concurrency_and_no_schedule_mutation',
        'test_07_application_failure_rolls_back_and_same_command_recovers',
        'test_08_independent_applications_publish_once_and_retry_is_idempotent',
        'test_09_immutable_publication_history_own_view_and_new_connections',
        'test_10_revocation_blocks_fresh_v2_scope_and_preserves_history']
    if COLLECTED != ['docs/testing/dashboard-d15/test_workflows_d15.py::'+name for name in expected]:
        raise pytest.UsageError('D15 expects exactly the 10 ordered retained-schema workflow cases')


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    record_report(item.nodeid, report, call.excinfo.value if call.excinfo else None)


def record_report(nodeid, report, error=None):
    entry = CASES.setdefault(nodeid, {'id':nodeid, 'phases':{}})
    phase = {'outcome':'FAILED' if report.failed else 'SKIPPED' if report.skipped else 'PASSED'}
    if report.failed:
        phase.update(exception_type=type(error).__name__, message='Exception details withheld.')
        from d15_target_guard import SafetyError
        if isinstance(error,SafetyError) and re.fullmatch(r'[A-Z][A-Z0-9_]{0,79}',error.code):
            phase.update(safety_code=error.code,
                         message='D15 safety preflight rejected: '+error.code+'; connection details withheld.')
        state = getattr(getattr(error,'orig',None),'pgcode',None)
        if isinstance(state,str) and re.fullmatch(r'[A-Z0-9]{5}',state):
            phase['SQLSTATE'] = state
    # Each phase is retained independently. Teardown never edits call details.
    if report.when in entry['phases']:
        raise RuntimeError('Duplicate acceptance phase report')
    entry['phases'][report.when] = phase


def outcome_summary():
    rows = []
    counts = dict.fromkeys(('PASSED','FAILED','ERROR','SKIPPED','NOT_RUN'),0)
    for id in COLLECTED:
        row = CASES.get(id, {'id':id,'phases':{}})
        phases = row['phases']
        failed = [p for p in ('setup','teardown') if phases.get(p,{}).get('outcome')=='FAILED']
        counts['ERROR'] += len(failed)
        call = phases.get('call',{}).get('outcome')
        skipped = sum(p['outcome']=='SKIPPED' for p in phases.values())
        counts['SKIPPED'] += skipped
        if call in ('PASSED','FAILED'):counts[call] += 1
        status = 'ERROR' if failed else 'FAILED' if call=='FAILED' else 'SKIPPED' if skipped else 'PASSED' if call=='PASSED' else 'NOT_RUN'
        if status=='NOT_RUN':counts['NOT_RUN'] += 1
        rows.append({**row,'status':status})
    return {'counts':counts,'case_counts':{status:sum(r['status']==status for r in rows) for status in counts},'cases':rows}


def pytest_sessionfinish(session, exitstatus):
    write_record('pytest-results.json', {'scope': SCOPE,
        'collected': len(COLLECTED), 'exit_code': int(exitstatus),
        **outcome_summary(), 'count_semantics':'pytest phase reports; a call failure and teardown error count separately; case_counts are exclusive',
        'credentials_or_exception_payloads_recorded': False})
