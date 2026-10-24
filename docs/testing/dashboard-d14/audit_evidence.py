"""Read-only preservation/privacy checks; writes only the D14 evidence manifest.

No database import, connection, migration, Git mutation or artifact cleanup.
Original PNGs were visually reviewed; identical images share that review.
"""
import ast
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import zlib

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
MANIFEST = BASE / 'manifest.json'
HEAD = '7a0c3eaf32dc3cc350c04871fdb6f8dd72c43bb4'
MODIFIED = {'frontend/src/pages/admin/ExternalSchedules.tsx', 'frontend/src/pages/faculty/MySchedule.tsx'}
NEW = {'backend/tests/dashboard/test_system_acceptance.py', 'backend/tests/dashboard/test_system_acceptance_live.py',
       'frontend/tests/systemAcceptance.live.mjs'}
RESULTS = {'focused': 6, 'd13-backend': 47, 'd12-backend': 42, 'd11-backend': 33, 'backend': 327,
           'backend-regressions': 46, 'academic-offline': 85, 'ga-resource-regressions': 3,
           'v1-fixtures': 4, 'v2-engine': 30, 'v2-api': 18, 'contracts': 205,
           'browser-regressions': 125, 'ga-browser': 51, 'v2-browser': 12,
           'live': 16, 'v2-live': 6, 'd11-live': 12, 'd12-live': 12, 'd13-live': 14, 'd14-live': 20}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, stderr=subprocess.DEVNULL).decode('utf-8').strip()


def rel(path):
    return path.relative_to(ROOT).as_posix()


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
    baseline = json.loads((BASE / 'preservation-baseline.json').read_text(encoding='utf-8'))
    changed = {p for p, h in baseline.items() if not (ROOT / p).is_file() or sha(ROOT / p) != h}
    assert changed == MODIFIED, 'Unexpected baseline delta; do not restore files'
    assert git('rev-parse', 'HEAD') == git('rev-parse', 'main') == git('rev-parse', 'origin/main') == HEAD
    assert git('branch', '--show-current') == 'main'
    assert not git('diff', '--cached', '--name-only')
    assert sha(ROOT / 'backend/data/faculty_preferences.json') == baseline['backend/data/faculty_preferences.json']
    untracked = set(git('ls-files', '--others', '--exclude-standard', '-z').split('\0')) - {''}
    def allowed(p):
        return p in NEW or p == 'docs/dashboard-d14-acceptance.md' or p.startswith('docs/testing/dashboard-d14/') or p.startswith('docs/screenshots/dashboard-d14/')
    assert all(allowed(p) for p in untracked), 'Unexpected untracked paths'
    modified = set(git('diff', '--name-only', '-z').split('\0')) - {''}
    assert modified == MODIFIED | {'backend/data/faculty_preferences.json'}
    files = sorted({ROOT / p for p in MODIFIED | NEW | untracked if ROOT / p != MANIFEST})
    sys.path.insert(0, str(ROOT / 'backend'))
    from services.evidence_sanitization import SENSITIVE, ENCODED, URI, PEM
    with (ROOT / 'backend/data/Faculty.csv').open(encoding='utf-8-sig', newline='') as stream:
        names = [r['Faculty'].strip() for r in csv.DictReader(stream) if r.get('Faculty', '').strip()]
    patterns = {'encoded_or_truncated_receipt': ENCODED, 'credential_URI': URI, 'private_key': PEM,
                'short_receipt_fragment': re.compile(r'(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_=.-]+'),
                'bearer': re.compile(r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}')}
    findings = []
    images = []
    records = []
    browser_records = []
    for path in files:
        assert path.suffix in {'.json', '.py', '.mjs', '.tsx', '.md', '.png'}, 'Unexpected generated file type'
        if path.suffix == '.png':
            raw = path.read_bytes()
            assert raw[:8] == b'\x89PNG\r\n\x1a\n'
            width, height = struct.unpack('>II', raw[16:24])
            offset = 8
            chunks = []
            while offset < len(raw):
                n = struct.unpack('>I', raw[offset:offset+4])[0]
                kind = raw[offset+4:offset+8]
                data = raw[offset+8:offset+8+n]
                assert zlib.crc32(kind+data) == struct.unpack('>I', raw[offset+8+n:offset+12+n])[0]
                chunks.append(kind)
                offset += 12+n
            assert chunks[-1] == b'IEND' and offset == len(raw)
            assert not set(chunks) & {b'tEXt', b'zTXt', b'iTXt', b'eXIf'}, 'PNG metadata needs separate review'
            images.append({'path': rel(path), 'sha256': sha(path), 'width': width, 'height': height,
                           'privacy': 'Original visually reviewed or byte-identical to reviewed original; fictional records only',
                           'scope': 'Real Edge/React/FastAPI/SQLite with fictional institutional providers; no genuine approval'})
            continue
        text = path.read_text(encoding='utf-8')
        values = [text]
        if path.suffix == '.py':
            ast.parse(text)
        if path.suffix == '.json':
            document = json.loads(text)
            values = list(strings(document))
            if path.name == 'command.json':
                records.append((path, document))
                for field in ('stdout', 'stderr'):
                    if any(SENSITIVE.search(line) for line in document.get(field, '').splitlines()):
                        findings.append({'path': rel(path), 'kind': 'sensitive_output_assignment'})
            if path.name == 'browser-results.json':
                browser_records.append({'path': rel(path), 'sha256': sha(path), 'record': document})
        for kind, pattern in patterns.items():
            if any(pattern.search(value) for value in values):
                findings.append({'path': rel(path), 'kind': kind})
        if any(re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)', text, re.I) for name in names):
            findings.append({'path': rel(path), 'kind': 'private_faculty_name'})
        if rel(path) not in MODIFIED:
            assert not any(line.rstrip() != line for line in text.splitlines()), 'New-file trailing whitespace: '+rel(path)
    assert not findings, 'Privacy findings, values omitted: '+json.dumps(findings)
    subprocess.run(['git', 'diff', '--check', '--', *sorted(MODIFIED)], cwd=ROOT, check=True, capture_output=True)
    latest = {}
    for path, record in sorted(records):
        latest[record['check']] = {'path': rel(path), 'exit_code': record['exit_code'], 'elapsed_seconds': record['elapsed_seconds'], 'scope': record['scope']}
    required = set(RESULTS) | {'build', 'lint'}
    assert required <= latest.keys() and all(latest[key]['exit_code'] == 0 for key in required)
    final_browser = next(r for r in browser_records if '20261024T210021246779' in r['path'])
    metrics = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT / Path(latest['focused']['path']).parent / 'metrics').glob('*.json'))]
    assert len(metrics) == 3 and all(v['hard_constraint_validation'] == 'PASS' for v in metrics)
    manifest = {
        'milestone': 'D14', 'status': 'PASSED within isolated fictional acceptance scope; production authority and PostgreSQL BLOCKED',
        'recorded_at': datetime.now(timezone(timedelta(hours=8))).isoformat(), 'baseline_commit': HEAD,
        'latest_commands': latest, 'fresh_counts_by_category': RESULTS,
        'counting': 'One latest run per group; browser counts exclude Node parent tests and pytest wrappers; no attempt totals or historical passes added',
        'build': 'PASS with existing mixed import and chunk-size warnings', 'focused_ESLint': 'PASS: zero errors/warnings',
        'complete_workflow_metrics': metrics,
        'implementation_inventory': {'modified': sorted(MODIFIED), 'new_tests': sorted(NEW),
                                     'new_report': 'docs/dashboard-d14-acceptance.md', 'other_new_files': sorted(untracked - NEW - {'docs/dashboard-d14-acceptance.md', rel(MANIFEST)})},
        'preservation': {'baseline_files': len(baseline), 'byte_identical': len(baseline)-len(changed),
                         'intended_existing_modifications': sorted(changed),
                         'academic_data_files_byte_identical': sum(p.startswith('backend/data/') for p in baseline),
                         'protected_preferences_byte_identical': True, 'all_original_GA_V1_V2_sources_unchanged': True,
                         'historical_checkpoints_schedules_and_D1_D13_evidence_unchanged': True,
                         'Git_index_HEAD_and_last_fetched_origin_unchanged': True,
                         'PostgreSQL_connections_or_migrations': 0, 'existing_schedule_file_writes': 0,
                         'SQLite_writes': 'Only owned fictional test stores'},
        'historical_nonzero_commands_retained': [{'path': rel(p), 'check': r['check'], 'exit_code': r['exit_code']} for p, r in records if r['exit_code'] != 0],
        'privacy': {'findings': findings, 'screenshots': images, 'unique_images': len({i['sha256'] for i in images}),
                    'methods': ['Whole sensitive log/header assignment filtering before evidence writes', 'Independent full/partial encoded receipt, bearer, private key and credential URI scan',
                                'Decoded JSON string scan and local private faculty-name comparison with no names exported', 'Original image visual review and PNG CRC/text/EXIF metadata checks'],
                    'raw_database_checkpoint_HAR_cookie_or_provider_payloads_archived': False},
        'browser_records': browser_records, 'final_D14_browser_record': final_browser['path'],
        'limitations': ['Institutional evidence, issuer, confirmation, catalog, Chair and publication providers remain unconfigured in production',
                        'Explicit owned fictional publication designation is a test provider, not a new production GA promotion API',
                        '17 Phase4C PostgreSQL cases and D9-D13 online PostgreSQL acceptance NOT RUN',
                        'Database-unavailable case injects SQLite OperationalError; it is not a physical PostgreSQL outage',
                        'Older D9 Windows Proactor teardown failed once; same unchanged suite passed in isolation; broader teardown reliability unresolved',
                        'Six historical incompatible checkpoints remain incompatible and untouched; four current V1 continuation fixtures passed',
                        'Tiny three-sample workload is not a performance, memory, scalability or institutional feasibility benchmark',
                        'Native browser printing and real institutional data accuracy NOT RUN'],
        'hash_convention': 'Raw-byte SHA-256; this manifest excludes itself. Hashes do not establish institutional authority or screenshot coverage.',
        'artifacts': [{'path': rel(p), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in files]}
    encoded = json.dumps(manifest, indent=2, ensure_ascii=True)+'\n'
    assert not any(p.search(encoded) for p in patterns.values()), 'Manifest privacy finding, values omitted'
    MANIFEST.write_text(encoded, encoding='utf-8')
    assert all(sha(ROOT / a['path']) == a['sha256'] for a in manifest['artifacts'])
    print(json.dumps({'artifacts_hashed': len(files), 'baseline_byte_identical': len(baseline)-len(changed),
                      'intended_existing_changes': len(changed), 'privacy_findings': len(findings),
                      'PNGs': len(images), 'unique_images': manifest['privacy']['unique_images'],
                      'failed_commands_retained': len(manifest['historical_nonzero_commands_retained'])}))


if __name__ == '__main__':
    main()
