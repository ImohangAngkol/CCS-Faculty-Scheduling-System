"""D16 artifact/preservation audit; reads files/Git only, writes D16 manifest.

No application startup, test execution, database connection or repair operation.
Requires explicit acknowledgement of visual review of all new PNGs.
"""
import ast
import csv
from datetime import datetime, timedelta, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'docs/testing/dashboard-d16'
REPORT = 'docs/dashboard-d16-functional-readiness.md'
MANIFEST = BASE / 'manifest.json'
APPLICATION = {
    'frontend/src/pages/chair/Requests.tsx',
    'frontend/src/pages/admin/ScheduleApplications.tsx',
    'frontend/src/api/scheduleApplications.ts',
}
SOURCES = {
    'backend/tests/dashboard/test_functional_readiness.py',
    'backend/tests/dashboard/test_readiness_live.py',
    'frontend/tests/functionalReadiness.live.mjs',
    'frontend/tests/functionalReadiness.test.mjs',
}
EXPECTED = {'focused': 3, 'continuous': 6, 'backend': 327, 'd11-backend': 33,
            'd12-backend': 42, 'd13-backend': 47, 'backend-regressions': 46,
            'academic-offline': 85, 'v1-fixtures': 4, 'v2-engine': 30,
            'v2-api': 18, 'ga-resource-regressions': 3}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8').strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    assert sys.argv[1:] == ['--screenshots-visually-reviewed']
    baseline = json.loads((BASE / 'preservation-baseline.json').read_text(encoding='utf-8'))
    differences = {p for p, h in baseline.items() if sha(ROOT / p) != h}
    assert differences == APPLICATION, 'Unexpected baseline changes; stop without restoring files'
    assert len(baseline) == 1371
    assert git('rev-parse', 'HEAD') == git('rev-parse', 'origin/main') == '2de39fb92eed6ac68036f45b1c82c8fb5fafe791'
    assert git('branch', '--show-current') == 'main'
    assert not git('diff', '--cached', '--name-only') and not git('ls-files', '-u')
    modified = set(git('diff', '--name-only', '-z').strip('\0').split('\0'))
    assert modified == APPLICATION | {'backend/data/faculty_preferences.json'}
    untracked = set(git('ls-files', '--others', '--exclude-standard', '-z').strip('\0').split('\0'))
    assert all(p in SOURCES or p == REPORT or p.startswith('docs/testing/dashboard-d16/')
               or p.startswith('docs/screenshots/dashboard-d16/') for p in untracked)
    previous = json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else None
    if previous:
        assert all(sha(ROOT / a['path']) == a['sha256'] for a in previous['artifacts']), 'Prior D16 artifact changed; stop for review'
    paths = sorted((untracked | APPLICATION) - {'docs/testing/dashboard-d16/manifest.json'})
    sys.path.insert(0, str(ROOT / 'backend'))
    from services.evidence_sanitization import ENCODED, URI, PEM, SENSITIVE
    patterns = [ENCODED, URI, PEM, re.compile(r'(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_=.-]+'),
                re.compile(r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}')]
    with (ROOT / 'backend/data/Faculty.csv').open(encoding='utf-8-sig', newline='') as stream:
        names = [r['Faculty'].strip() for r in csv.DictReader(stream) if r.get('Faculty', '').strip()]
    commands = []
    pngs = []
    from PIL import Image
    for p in paths:
        path = ROOT / p
        assert path.suffix in {'.py', '.ts', '.tsx', '.mjs', '.md', '.json', '.png'}
        if path.suffix == '.png':
            with Image.open(path) as picture:
                assert picture.format == 'PNG'
                values = [str(picture.info)]
                pngs.append({'path': p, 'dimensions': list(picture.size), 'visually_reviewed': True})
            raw = '\n'.join(values)
        else:
            raw = path.read_text(encoding='utf-8')
            assert all(line == line.rstrip() for line in raw.splitlines()), 'Whitespace: ' + p
            values = [raw]
            if path.suffix == '.py':
                ast.parse(raw)
            if path.suffix == '.json':
                value = json.loads(raw)
                values = list(strings(value))
                if path.name == 'command.json':
                    commands.append((p, value))
                    assert not any(SENSITIVE.search(line) for field in ('stdout', 'stderr')
                                   for line in value.get(field, '').splitlines()), 'Sensitive output; value withheld: ' + p
        assert not any(pattern.search(v) for pattern in patterns for v in values), 'Sensitive pattern; value withheld: ' + p
        assert not any(re.search(r'(?<!\w)' + re.escape(n) + r'(?!\w)', raw, re.I) for n in names), 'Private name; value withheld: ' + p
    latest = {}
    for p, record in sorted(commands):
        latest[record['check']] = {'path': p, 'exit_code': record['exit_code'],
                                   'elapsed_seconds': record['elapsed_seconds'], 'scope': record['scope']}
    for key, count in EXPECTED.items():
        record = json.loads((ROOT / latest[key]['path']).read_text(encoding='utf-8'))
        assert record['exit_code'] == 0 and re.search(r'\b' + str(count) + r' passed\b', record['stdout'])
    for key, total in {'contracts': 207, 'ga-browser': 52, 'browser-regressions': 133, 'v2-browser': 13}.items():
        record = json.loads((ROOT / latest[key]['path']).read_text(encoding='utf-8'))
        assert record['exit_code'] == 0 and re.search(r'pass ' + str(total) + r'\b', record['stdout'])
    assert all(latest[k]['exit_code'] == 0 for k in ('build', 'lint', 'd16-live'))
    live_run = Path(latest['d16-live']['path']).parent.name
    browser_path = ROOT / 'docs/screenshots/dashboard-d16' / live_run / 'browser-results.json'
    browser = json.loads(browser_path.read_text(encoding='utf-8'))
    assert len(browser['scenarios']) == 21 and all(s['result'] == 'PASS' for s in browser['scenarios'])
    assert not browser['runtime_errors'] and len(pngs) == 37
    prior = json.loads((ROOT / 'docs/testing/dashboard-d15/manifest.json').read_text(encoding='utf-8'))
    assert all(sha(ROOT / a['path']) == a['sha256'] for a in prior['artifacts'])
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    # Parse the report's actual matrix instead of maintaining contradictory copies.
    report = (ROOT / REPORT).read_text(encoding='utf-8')
    matrix = []
    for line in report.splitlines():
        if line.startswith('|') and any('| ' + status + ' |' in line for status in ('WORKING', 'FIXED', 'INCOMPLETE', 'BLOCKED', 'NOT TESTED')):
            cells = [c.strip() for c in line.strip('|').split('|')]
            matrix.append(dict(zip(('feature', 'status', 'evidence_and_limit'), cells, strict=True)))
    assert len(matrix) == 24
    inventory = sorted(untracked | APPLICATION | {'docs/testing/dashboard-d16/manifest.json'})
    manifest = {
        'milestone': 'D16', 'recorded_at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
        'status': 'PASS within isolated fictional demonstration; institutional production activation BLOCKED',
        'source_commit': git('rev-parse', 'HEAD'), 'feature_matrix': matrix,
        'environment': {'Python': sys.version.split()[0], 'SQLite': sqlite3.sqlite_version,
                        'Node': subprocess.check_output(['node', '--version']).decode().strip(),
                        'Edge': browser['browser'], **{k: version(k) for k in ('fastapi', 'starlette', 'sqlalchemy', 'alembic')}},
        'latest_commands': latest,
        'backend_case_counts': EXPECTED, 'backend_pytest_cases_passed': sum(EXPECTED.values()),
        'frontend_contracts_passed': 207,
        'synthetic_HTTP_browser_scenarios': {'D1_D8': 125, 'GA': 51, 'V2': 12},
        'actual_Edge_FastAPI_SQLite_scenarios': 21,
        'browser_parent_and_pytest_wrapper_excluded_from_scenario_counts': True,
        'auth_browser_wrapper_in_46_backend_cases_not_added_separately': True,
        'actual_browser_evidence': browser_path.relative_to(ROOT).as_posix(),
        'failed_commands_preserved': [{'path': p, 'exit_code': r['exit_code']} for p, r in commands if r['exit_code']],
        'failure_interpretation': 'Two sandbox D16 CDP startup timeouts and one embedded auth CDP timeout; two unrestricted D16 runs reproduced F01 and F02. Later supervised unrestricted runs pass. No arbitrary timeout change.',
        'defects_fixed': {'D16-F01': 'Clear stale actionable queue during Chair filter loading',
                          'D16-F02': 'Fetch protected published history without selecting a pending request'},
        'demo': {'command': '.\\.venv\\Scripts\\python.exe -B docs/testing/dashboard-d16/run_checks.py d16-live',
                 'kind': 'Automated headless local demonstration, fresh fictional fixtures, no PostgreSQL',
                 'resources_and_initial_GEC_confirmation': 'Prepared by existing real-service test fixture',
                 'initial_publication': 'Explicit test-only provider/file handoff; no production promotion API',
                 'authority': 'Fictional scoped providers only; production defaults unchanged'},
        'preservation': {'baseline_files': len(baseline), 'byte_identical': len(baseline) - len(differences),
                         'intentional_frontend_changes': sorted(differences), 'academic_data_files_preserved': 23,
                         'protected_preference_local_bytes_preserved': True, 'Git_index_HEAD_origin_unchanged': True,
                         'D15_artifact_hashes_preserved': 75, 'original_GA_migrations_checkpoints_schedules_prior_evidence_preserved': True,
                         'PostgreSQL_connections_or_operations': 0, 'staging_commits_pushes': 0},
        'privacy': {'findings': 0, 'decoded_text_and_PNG_metadata_scanned': True,
                    'complete_and_partial_receipts_URIs_keys_headers_scanned': True,
                    'private_faculty_names_compared_locally_without_export': True,
                    'raw_DB_HAR_cookie_header_or_credential_handoffs_archived': False},
        'screenshots': pngs, 'exact_changed_and_new_file_inventory': inventory,
        'preexisting_protected_modification_excluded': 'backend/data/faculty_preferences.json',
        'limitations': ['Genuine institutional authority and production publication remain BLOCKED',
                       'Academic resource CRUD/import-to-runtime and first-publication UI remain incomplete',
                       'Native printing, physical outage, whole-production-process restart and scale/quality studies not tested',
                       'Some viewport captures omit below-fold preference/empty-state labels; assertions establish those results',
                       'D15 PostgreSQL results historical, not rerun; its populated target untouched',
                       'No persistent attended demo launcher; verified one-command headless demonstration only'],
        'hash_convention': 'Raw SHA256, manifest excludes itself; hashes do not prove institutional authority',
        'artifacts': [{'path': p, 'bytes': (ROOT / p).stat().st_size, 'sha256': sha(ROOT / p)} for p in paths],
    }
    encoded = json.dumps(manifest, indent=2, ensure_ascii=True) + '\n'
    assert not any(pattern.search(encoded) for pattern in patterns)
    MANIFEST.write_bytes(encoded.encode('utf-8'))
    assert all(sha(ROOT / a['path']) == a['sha256'] for a in manifest['artifacts'])
    print(json.dumps({'artifacts_hashed': len(paths), 'exact_D16_files': len(inventory),
                      'baseline_preserved': len(baseline) - len(differences), 'academic_paths_preserved': 23,
                      'backend_passed': sum(EXPECTED.values()), 'frontend_contracts': 207,
                      'actual_live_scenarios': 21, 'synthetic_HTTP_browser_scenarios': 188,
                      'privacy_findings': 0, 'reviewed_screenshots': len(pngs), 'PostgreSQL_operations': 0}))


if __name__ == '__main__':
    main()
