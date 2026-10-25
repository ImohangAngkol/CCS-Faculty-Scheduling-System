"""D15 blocked-environment evidence audit; writes its manifest only.

No database engine, connection, migration or test fixture is invoked.
"""
import ast
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
MANIFEST = BASE/'manifest.json'
EXPECTED = {'academic-offline': 85, 'backend': 327, 'v2-engine': 30, 'v2-api': 18,
            'd11-backend': 33, 'd12-backend': 42, 'd13-backend': 47, 'focused': 6}
GUARD_EXPECTED = 84
WRITE_GUARD_EXPECTED = 243
WORKFLOW_GUARD_EXPECTED = 469


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, stderr=subprocess.DEVNULL).decode('utf-8').strip()


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def main():
    previous = json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.is_file() else {}
    intentionally_updated = {'docs/dashboard-d15-postgresql-acceptance.md'} | {
        'docs/testing/dashboard-d15/'+name for name in ('d15_workflow_guard.py','d15_workflow_plugin.py',
        'run_workflows.py','test_workflows_d15.py','run_offline_checks.py','audit_evidence.py')}
    assert all((ROOT/a['path']).is_file() and (a['path'] in intentionally_updated or sha(ROOT/a['path'])==a['sha256'])
               for a in previous.get('artifacts',[])), 'Unexpected prior artifact change; do not restore'
    baseline = json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'))
    assert all((ROOT/p).is_file() and sha(ROOT/p) == h for p, h in baseline.items()), 'Preservation failed; do not restore'
    assert git('rev-parse', 'HEAD') == git('rev-parse', 'origin/main') == 'c6baad2a0d59515555b33c84eca337a78a913a65'
    assert git('branch', '--show-current') == 'main'
    assert not git('diff', '--cached', '--name-only')
    assert git('diff', '--name-only', '-z').strip('\0') == 'backend/data/faculty_preferences.json'
    untracked = set(git('ls-files', '--others', '--exclude-standard', '-z').strip('\0').split('\0'))
    assert all(p.startswith('docs/testing/dashboard-d15/') or p == 'docs/dashboard-d15-postgresql-acceptance.md' for p in untracked)
    files = sorted(ROOT/p for p in untracked if ROOT/p != MANIFEST)
    sys.path.insert(0, str(ROOT/'backend'))
    from services.evidence_sanitization import ENCODED, SENSITIVE, URI, PEM
    patterns = [ENCODED, URI, PEM, re.compile(r'(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_=.-]+'),
                re.compile(r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}')]
    with (ROOT/'backend/data/Faculty.csv').open(encoding='utf-8-sig', newline='') as stream:
        names = [r['Faculty'].strip() for r in csv.DictReader(stream) if r.get('Faculty', '').strip()]
    records = []
    for path in files:
        assert path.suffix in {'.md', '.json', '.py'}
        raw = path.read_text(encoding='utf-8')
        values = [raw]
        if path.suffix == '.json':
            document = json.loads(raw)
            values = list(strings(document))
            if path.name == 'command.json':
                records.append((path, document))
                assert not any(SENSITIVE.search(line) for field in ('stdout', 'stderr') for line in document.get(field, '').splitlines()), 'Sensitive output; values omitted'
        if path.suffix == '.py':
            ast.parse(raw)
        assert not any(pattern.search(v) for pattern in patterns for v in values), 'Sensitive evidence; values omitted'
        assert not any(re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)', raw, re.I) for name in names), 'Private faculty name; values omitted'
        assert all(line == line.rstrip() for line in raw.splitlines()), 'Trailing whitespace in new evidence'
    latest = {}
    for path, record in sorted(records):
        latest[record['check']] = {'path': path.relative_to(ROOT).as_posix(), 'exit_code': record['exit_code'],
                                   'elapsed_seconds': record['elapsed_seconds'], 'scope': record['scope']}
    for key, expected in {**EXPECTED, 'd15-guard': GUARD_EXPECTED, 'd15-write-guard': WRITE_GUARD_EXPECTED,
                          'd15-workflow-guard': WORKFLOW_GUARD_EXPECTED, 'd15-workflow-rehearsal':7}.items():
        record = json.loads((ROOT/latest[key]['path']).read_text(encoding='utf-8'))
        assert re.search(r'\b'+str(expected)+r' passed\b', record['stdout'])
    assert set(EXPECTED) | {'postgres-collection', 'd15-guard', 'd15-write-guard', 'd15-phase4c-collection'} <= latest.keys()
    # A successfully audited historical failure is not a passed acceptance run.
    assert all(r['exit_code'] == 0 for key,r in latest.items() if key != 'workflows-postgresql')
    collection = json.loads((ROOT/latest['postgres-collection']['path']).read_text(encoding='utf-8'))
    cases = [line for line in collection['stdout'].splitlines() if line.startswith('tests/academic/test_academic_postgresql.py::')]
    assert len(cases) == 17 and '17 tests collected' in collection['stdout']
    wrapped = json.loads((ROOT/latest['d15-phase4c-collection']['path']).read_text(encoding='utf-8'))
    wrapped_cases = [line for line in wrapped['stdout'].splitlines() if line.startswith('docs/testing/dashboard-d15/test_phase4c_d15.py::')]
    assert [c.split('::', 1)[1] for c in cases] == [c.split('::', 1)[1] for c in wrapped_cases]
    online_path = ROOT/latest['phase4c-postgresql']['path']
    online = json.loads(online_path.read_text(encoding='utf-8'))
    outcomes = json.loads((online_path.parent/'pytest-results.json').read_text(encoding='utf-8'))
    connections = json.loads((online_path.parent/'connection-guard-summary.json').read_text(encoding='utf-8'))
    assert online['exit_code'] == outcomes['exit_code'] == 0 and outcomes['collected'] == 17
    assert outcomes['counts'] == {'PASSED':17, 'FAILED':0, 'ERROR':0, 'SKIPPED':0, 'NOT_RUN':0}
    assert [r['id'].split('::',1)[1] for r in outcomes['cases']] == [c.split('::',1)[1] for c in cases]
    assert all(r['status'] == 'PASSED' for r in outcomes['cases'])
    assert connections['target'] == 'ccs_ga_d15_test' and connections['role'] == 'ccs_ga_d15_tester'
    assert connections['owned_connections_closed'] and connections['schema_retained'] and not connections['cleanup_DDL_executed']
    assert connections['counts'] == {'physical_connections':22, 'identity_checks':370, 'guarded_statements':314}
    workflow_collection = json.loads((ROOT/latest['d15-workflow-collection']['path']).read_text(encoding='utf-8'))
    assert '10 tests collected' in workflow_collection['stdout']
    failed_path = BASE/'20261025T163206495077+0800-workflows-postgresql'
    failure = json.loads((failed_path/'pytest-results.json').read_text(encoding='utf-8'))
    failure_guard = json.loads((failed_path/'connection-guard-summary.json').read_text(encoding='utf-8'))
    assert failure['counts'] == {'PASSED':0,'FAILED':0,'ERROR':1,'SKIPPED':0,'NOT_RUN':9}
    assert failure['cases'][0]['phase'] == 'setup' and failure['cases'][0]['safety_code'] == 'RETAINED_CONSTRAINT_CONTRACT_MISMATCH'
    assert failure_guard['counts'] == {'physical_connections':1,'identity_checks':1,'guarded_statements':0}
    assert failure_guard['owned_connections_closed'] is True and failure_guard['cleanup_DDL_executed'] is False
    diagnosis = json.loads((BASE/'operator-pg18-diagnosis.json').read_text(encoding='utf-8'))
    assert diagnosis['constraint_type_counts'] == {'n':76,'p':11,'c':37,'f':11,'u':18}
    assert diagnosis['read_only_enforcement_verified'] is True and diagnosis['writes_performed'] is False
    assert all(not differences for differences in diagnosis['differences'].values())
    assert all(sha(ROOT/a['path']) == a['sha256'] for a in diagnosis['prior_failure_artifacts'])
    retest_path = BASE/'20261025T170223852944+0800-workflows-postgresql'
    retest_command = json.loads((retest_path/'command.json').read_text(encoding='utf-8'))
    retest_outcomes = json.loads((retest_path/'pytest-results.json').read_text(encoding='utf-8'))
    retest_guard = json.loads((retest_path/'connection-guard-summary.json').read_text(encoding='utf-8'))
    assert '1 failed, 1 warning, 1 error' in retest_command['stdout'] and retest_command['exit_code']==1
    assert retest_outcomes['cases'][0]['phase']=='teardown' and retest_outcomes['cases'][0]['exception_type']=='AssertionError'
    assert retest_outcomes['cases'][0]['safety_code']=='UNREVIEWED_WORKFLOW_DDL_REJECTED'
    assert retest_guard['owned_connections_closed'] is True and retest_guard['cleanup_DDL_executed'] is False
    recovery = json.loads((BASE/'operator-post-abort-diagnosis.json').read_text(encoding='utf-8'))
    assert recovery['result']['schema_matches_retest_entry'] is True and recovery['result']['verified_revision']=='4c_0001'
    assert recovery['result']['read_only_enforcement_verified'] is True and recovery['result']['writes_performed'] is False
    assert all(sha(ROOT/a['path'])==a['sha256'] for a in recovery['retest_artifacts'])
    preflights = []
    for path in sorted(BASE.glob('*/result.json')):
        record = json.loads(path.read_text(encoding='utf-8'))
        if record.get('kind') == 'D15 read-only PostgreSQL preflight':
            preflights.append({'path': path.relative_to(ROOT).as_posix(), 'record': record})
    passed_preflights = [p for p in preflights if p['record'].get('result', {}).get('status') == 'READ_ONLY_PREFLIGHT_PASSED']
    assert passed_preflights, 'Operator read-only preflight evidence required'
    for result in (p['record']['result'] for p in passed_preflights):
        assert result['database'] == 'ccs_ga_d15_test' and result['session_user'] == result['current_user'] == result['owner'] == 'ccs_ga_d15_tester'
        assert result['host'] == '127.0.0.1' and result['port'] == 5432 and result['empty'] is True and result['writes_performed'] is False
    manifest = {'milestone': 'D15', 'status': 'PHASE4C 17 PASSED; two failed workflow attempts preserved; rollback confirmed USER_REPORTED; transport/abort/reporting fixes offline verified; supervised resumption pending',
        'recorded_at': datetime.now(timezone(timedelta(hours=8))).isoformat(), 'baseline_commit': git('rev-parse', 'HEAD'),
        'latest_commands': latest, 'fresh_offline_or_SQLite_cases': EXPECTED, 'fresh_offline_or_SQLite_passed': sum(EXPECTED.values()),
        'guard_offline_tests_latest_passed': GUARD_EXPECTED,
        'write_guard_offline_tests_latest_passed': WRITE_GUARD_EXPECTED,
        'workflow_guard_offline_tests_latest_passed':WORKFLOW_GUARD_EXPECTED,
        'workflow_fixture_SQLite_rehearsal_passed':7,
        'test_attribution': 'Operator executed 17 actual PostgreSQL Phase4C cases; Codex inspected unchanged artifacts. Earlier 588 offline/SQLite cases remain historical. Latest combined guard selection includes the prior 243; not added twice. New 7-case SQLite fixture rehearsal is not PostgreSQL or browser evidence.',
        'phase4c_PostgreSQL_evidence': {'observer':'LOCAL_OPERATOR_EXECUTION; inspected by Codex',
            'command':online_path.relative_to(ROOT).as_posix(), 'outcomes':outcomes,
            'connection_guard':connections, 'warnings':'3 emissions of Alembic path_separator deprecation; no warning suppression',
            'duration_pytest_seconds':13.10, 'duration_runner_seconds':online['elapsed_seconds']},
        'workflow_PostgreSQL_failure':{'path':failed_path.relative_to(ROOT).as_posix(), 'outcomes':failure,
            'connection_guard':failure_guard, 'stage':'Initial read-only fixture gate, before any migration/write-mode activation',
            'original_traceback':'Not captured: controlled runner used --tb=no', 'migration_writes_reached':False,
            'superseded_by_successful_workflow_execution':False},
        'operator_pg18_read_only_diagnosis':{'path':'docs/testing/dashboard-d15/operator-pg18-diagnosis.json',
            'attribution':diagnosis['attribution'],'record':diagnosis},
        'workflow_PostgreSQL_retest':{'path':retest_path.relative_to(ROOT).as_posix(),
            'legacy_outcomes_unmodified':retest_outcomes,'guard_summary_unmodified':retest_guard,
            'actual_pytest_phase_counts':{'PASSED':0,'FAILED':1,'ERROR':1,'SKIPPED':0,'NOT_RUN':9},
            'legacy_summary_defect':'Call SafetyError was overwritten by teardown AssertionError; original artifacts retained, not rewritten',
            'primary_cause':'Frozen D9 statement14 percent ROWTYPE is doubled by psycopg2 dialect compilation; raw expected SQL mismatched transport',
            'secondary_cause':'Unconditional successful final revision assertion after aborted migration',
            'recovery_diagnostic':recovery},
        'transport_abort_reporting_correction':{'scope':'D15 tooling/tests/evidence only',
            'matching':'Exact trusted frozen SQL compiled with actual connection dialect; no incoming percent or whitespace rewrite; no DDL parameters or executemany',
            'teardown':'Explicit committed-upgrade flag; abort requires verified entry catalog and empty fixture tables; no repair operation',
            'reporting':'Independent setup/call/teardown outcomes; phase counts match pytest and exclusive case_counts retained; factual row-retention/end-state fields',
            'synthetic_pytest_SQLite_cases_in_guard_count':3,
            'live_correction_attempt_executed':False},
        'PG18_guard_correction':{'scope':'D15 guard/tests/docs only; no database connection or application change',
            'fixture':'docs/testing/dashboard-d15/fixtures/pg18-constraint-inventory.json',
            'validation':'All 76 NOT NULL bindings/definitions and validation/enforcement flags checked; duplicate/inconsistent/other-type constraints rejected; complete records fingerprinted',
            'older_versions':'Catalog reader handles pre18 conenforced absence; exact D15 live guard still requires PostgreSQL18',
            'resume_command':'.\\.venv\\Scripts\\python.exe -B docs/testing/dashboard-d15/run_workflows.py --execute',
            'resume_executed':True, 'resume_outcome':'Retained gate passed; subsequent D9 transport rejection and teardown reporting defect; recovery USER_REPORTED'},
        'operator_read_only_preflights': preflights,
        'PostgreSQL': {'successful_read_only_preflights': len(passed_preflights), 'Codex_connections_attempted': 0,
                       'Phase4C_owned_physical_connections':22,
                       'connections_attempted':'Operator artifacts: preflight, 22 Phase4C physical connections, first workflow1 and second workflow3; additional READ ONLY diagnoses USER_REPORTED',
                       'migration_scope_executed':'Committed through 4c_0001; partial D9 DDL during second workflow rolled back according to user-reported post-abort diagnostic',
                       'tests_executed':18, 'passed':17, 'failed':1, 'setup_errors':1, 'teardown_errors':1, 'skipped_during_execution':0,
                       'Phase4C_collected': 17, 'Phase4C_blocked_NOT_RUN': 0,
                       'collected_case_ids': cases, 'D9_D13_online_acceptance': 'Initial setup rejection; second attempt FAILED call plus teardown ERROR; user reports verified rollback to unchanged 4c_0001; corrected resumption pending',
                       'actual_connected_server_version': {'value': passed_preflights[-1]['record']['result']['server_version'], 'observer': 'LOCAL_OPERATOR_EXECUTION; artifact inspected by Codex'}},
        'preservation': {'baseline_files_byte_identical': len(baseline), 'academic_data_files_byte_identical': sum(p.startswith('backend/data/') for p in baseline),
                         'protected_preferences_unchanged': True, 'Git_index_HEAD_origin_unchanged': True,
                         'GA_V1_V2_sources_checkpoints_saved_results_D14_evidence_unchanged': True, 'existing_application_files_modified': 0},
        'privacy': {'findings': 0, 'methods': ['Pre-write whole sensitive assignment/header and receipt filtering', 'Independent full/truncated receipt, bearer, URI and private key scans',
                                            'Decoded JSON and all failure/output fields scanned', 'Private faculty names compared locally without exporting values'],
                    'screenshots_browser_traces_raw_databases_or_session_payloads_archived': False},
        'historical_nonzero_commands_retained': [{'path': p.relative_to(ROOT).as_posix(), 'exit_code': r['exit_code']} for p, r in records if r['exit_code'] != 0],
        'continuation': previous.get('continuation'),
        'guard_readiness': {'private_terminal_ready': 'USER CONFIRMED', 'read_only_guard': 'Operator execution passed; original artifact retained',
                            'write_guard': 'Default pristine academic guard preserved. WorkflowRun adds explicit retained 4c contract, schema fingerprint checks, frozen additive DDL and academic DML/drop/truncate rejection; inherits exact identity/barrier/connection lifecycle',
                            'Codex_has_private_terminal_credentials': False,
                            'prepared_command': '.\\.venv\\Scripts\\python.exe -B docs/testing/dashboard-d15/run_workflows.py --execute',
                            'controlled_scope': 'Exact retained 4c empty-fixture profile; rollback upgrade rehearsals then committed additive D9-D13 upgrades; 10 ordered acceptance cases; no reset/automatic retry; retain all new fictional rows'},
        'limitations': ['Codex has inspected operator Phase4C acceptance/preflight evidence but has not connected or run PostgreSQL writes',
                        'Existing Phase4C exact target differs from proposed D15 identity; no bypass or original gate modification',
                        'Bare Alembic CLI uses DATABASE_URL; future live acceptance must pass a gated caller-owned connection',
                        'First-phase execution passed; PG18 constraint correction passed live retained gate during second attempt; transport/abort/reporting correction not yet exercised against PostgreSQL',
                        'D9-D13 online migrations/workflows/concurrency acceptance remain pending',
                        'User-reported post-abort READ ONLY diagnostic confirms unchanged 4c catalog and empty tables; next supervised acceptance still freshly gates target before writes',
                        'Genuine institutional providers remain blocked; new rehearsal uses fictional providers and SQLite',
                        'Workflow recovery covers transaction rollback, lock release and synthetic storage exceptions; no PostgreSQL service crash, physical outage or cross-process workflow recovery claim',
                        'No fresh frontend/browser run or production build: no application/frontend change',
                        'D15 guard PG18 catalog mismatch confirmed by user-reported live differences and offline reproduction; no application PostgreSQL defect established',
                        'Guard controls the trusted acceptance harness, not hostile Python code or privileged DB administrators'],
        'hash_convention': 'Raw-byte SHA-256 of new D15 artifacts; manifest excludes itself. Hashes do not establish live database correctness.',
        'artifacts': [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in files]}
    encoded = json.dumps(manifest, indent=2, ensure_ascii=True)+'\n'
    assert not any(pattern.search(encoded) for pattern in patterns)
    MANIFEST.write_bytes(encoded.encode('utf-8'))
    assert all(sha(ROOT/a['path']) == a['sha256'] for a in manifest['artifacts'])
    print(json.dumps({'artifacts_hashed': len(files), 'preserved_files': len(baseline), 'offline_or_SQLite_passed': sum(EXPECTED.values()),
                      'combined_guard_tests_latest_passed': WORKFLOW_GUARD_EXPECTED, 'PostgreSQL_cases_operator_passed':17,
                      'D9_D13_workflow_cases_collected':10, 'corrected_live_attempt_executed':False,
                      'operator_read_only_preflights': len(passed_preflights), 'Codex_PostgreSQL_connections': 0, 'privacy_findings': 0}))


if __name__ == '__main__':
    main()
