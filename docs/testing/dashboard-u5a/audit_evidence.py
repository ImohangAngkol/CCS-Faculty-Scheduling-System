"""Replay U5A raw hashes, privacy, attempt attribution and entry-state preservation."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import zlib

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
HEAD = '705cc44655ba775259ca21c38f4f10959d9fdf78'
MODIFIED = [
    'backend/main.py',
    'frontend/src/pages/admin/ChromosomeViewer.tsx',
    'frontend/src/pages/admin/GenerationHistory.tsx',
    'frontend/src/pages/admin/FitnessAnalysis.tsx',
    'frontend/tests/resultPresentation.test.mjs',
    'frontend/tests/evaluationCoverage.test.mjs',
    'frontend/tests/resultPresentation.browser.test.mjs',
    'frontend/tests/evaluationCoverage.browser.test.mjs',
]
NEW_SOURCE = [
    'backend/services/ga_result_compatibility.py', 'backend/routers/ga_evaluation.py',
    'backend/tests/test_ga_result_compatibility.py',
    'frontend/src/services/currentEvaluation.ts', 'frontend/src/components/ga/CurrentEvaluation.tsx',
    'frontend/tests/currentEvaluation.fixtures.mjs', 'frontend/tests/currentEvaluation.test.mjs',
    'frontend/tests/currentEvaluation.browser.test.mjs',
]
REPORT = 'docs/dashboard-u5a-current-evaluation-compatibility.md'
PROTECTED = {'backend/data/faculty_preferences.json', 'backend/data/ga_settings.json'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT,
        env=dict(os.environ, GIT_OPTIONAL_LOCKS='0')).decode('utf-8')


def inspect():
    assert git('rev-parse', 'HEAD').strip() == HEAD, 'HEAD_CHANGED_STOP'
    assert git('branch', '--show-current').strip() == 'main', 'BRANCH_CHANGED_STOP'
    baseline = json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'))
    assert len(baseline) == 3039
    assert len([p for p in baseline if p.startswith('backend/data/')]) == 23
    for name, digest in baseline.items():
        if name not in MODIFIED:
            assert (ROOT/name).is_file() and sha(ROOT/name) == digest, 'PRESERVATION_MISMATCH_STOP: '+name
    assert not git('diff', '--cached', '--name-only').strip(), 'STAGED_CHANGES_STOP'
    u4 = json.loads((ROOT/'docs/testing/dashboard-u4/manifest.json').read_text(encoding='utf-8'))
    tracked = set(git('ls-files', '-z').split('\0')) - {''}
    live = json.loads((ROOT/'docs/testing/ga-live-center/manifest.json').read_text(encoding='utf-8'))
    expected_tracked = (set(MODIFIED) | set(u4['modified_files']) | set(live['modified_from_entry']) | PROTECTED) & tracked
    actual_tracked = set(git('diff', '--name-only').splitlines())
    assert actual_tracked == expected_tracked, 'TRACKED_SCOPE_MISMATCH_STOP'
    subprocess.run(['git', 'diff', '--check', '--', *MODIFIED], cwd=ROOT,
        env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'), check=True, capture_output=True)
    previous = {}
    for number in (1, 2, 3, 4):
        record = json.loads((ROOT/f'docs/testing/dashboard-u{number}/manifest.json').read_text(encoding='utf-8'))
        previous.update(record['artifact_sha256'])
    previous.update(live['artifact_sha256'])
    prior_verified = 0
    for name, digest in previous.items():
        if name not in MODIFIED:
            assert sha(ROOT/name) == digest, 'PRIOR_ARTIFACT_MISMATCH_STOP: '+name
            prior_verified += 1
    manifest_name = (BASE/'manifest.json').relative_to(ROOT).as_posix()
    own = sorted(set([REPORT, *MODIFIED, *NEW_SOURCE, manifest_name,
        *(p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file())]))
    untracked = set(git('ls-files', '--others', '--exclude-standard', '-z').split('\0')) - {''}
    assert not untracked - set(baseline) - set(own), 'UNAPPROVED_NEW_PATH_STOP'
    paths = [ROOT/name for name in own if name != manifest_name]
    # Identity comparison stays in memory. Protected preferences/settings are raw-hashed only.
    registry = json.loads((ROOT/'backend/data/faculty_identities.json').read_text(encoding='utf-8'))['faculty']
    names = {re.sub(r'\s+', ' ', value.strip().upper()) for row in registry
        for value in (row['name'], *row.get('aliases', [])) if len(value.strip()) >= 8}
    patterns = [r'eyJ[A-Za-z0-9_=-]{16,}', r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}',
        r'(?i)\b(?:postgresql|postgres|mysql)(?:\+\w+)?://[^\s]+',
        r'-----BEGIN [A-Z ]*PRIVATE KEY-----', r'(?i)https?://[^\s/]+:[^\s/@]+@',
        r'(?i)(?<![\w])(?:set-cookie|authorization)\s*:\s*[^\s]{16,}']
    assert re.search(patterns[-1], 'Authorization: ' + 'x'*24)
    assert re.search(patterns[-1], 'Set-Cookie: ' + 'x'*24)
    assert not re.search(patterns[-1], 'institutional_authorization: NOT_ESTABLISHED')
    pngs, image_hashes = [], set()
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        if path.suffix == '.png':
            raw = path.read_bytes()
            assert raw[:8] == b'\x89PNG\r\n\x1a\n', 'PNG_FORMAT_STOP'
            width, height = struct.unpack('>II', raw[16:24])
            offset, chunks = 8, []
            while offset < len(raw):
                size = struct.unpack('>I', raw[offset:offset+4])[0]
                kind = raw[offset+4:offset+8]
                expected_crc = struct.unpack('>I', raw[offset+8+size:offset+12+size])[0]
                assert zlib.crc32(raw[offset+4:offset+8+size]) == expected_crc, 'PNG_CRC_STOP'
                chunks.append(kind.decode('ascii'))
                assert kind not in {b'tEXt', b'zTXt', b'iTXt', b'eXIf'}, 'UNREVIEWED_IMAGE_METADATA_STOP'
                offset += 12+size
            assert offset == len(raw) and chunks[-1] == 'IEND', 'PNG_STRUCTURE_STOP'
            image_hashes.add(sha(path))
            pngs.append(dict(path=relative, width=width, height=height, metadata_chunks=chunks))
            continue
        content = path.read_text(encoding='utf-8')
        assert content.endswith('\n') and all(line == line.rstrip() for line in content.splitlines()), 'WHITESPACE_STOP: '+relative
        normalized = re.sub(r'\s+', ' ', content.upper())
        assert not any(re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)', normalized) for name in names), 'PRIVATE_IDENTITY_STOP_WITHHELD'
        assert not any(re.search(pattern, content) for pattern in patterns), 'SENSITIVE_PATTERN_STOP_WITHHELD'
    attempts = []
    for path in sorted(BASE.glob('*/command.json')):
        record = json.loads(path.read_text(encoding='utf-8'))
        counts = {key: int(value) for key, value in re.findall(r'(?m)^\S+ (tests|pass|fail|skipped|cancelled) (\d+)\s*$', record['stdout'])}
        if record['selection'].startswith('backend'):
            counts = {key: int(value) for value,key in re.findall(r'(\d+) (passed|failed|skipped|errors?)', record['stdout'].split('short test summary info')[-1])}
        assert not record['timed_out'], 'UNREVIEWED_RUNNER_TIMEOUT_STOP'
        attempts.append(dict(path=path.relative_to(ROOT).as_posix(), selection=record['selection'], exit_code=record['exit_code'], counts=counts))
    final = {item['selection']: item for item in attempts}
    expected = [('focused',16),('regressions',182),('browser',15),('u4-browser',22),
        ('u3-browser',16),('u1-browser',13),('live-browser',21),('ga-browser',52)]
    for selection, count in expected:
        item = final[selection]
        assert item['exit_code'] == 0 and item['counts']['pass'] == count, 'FINAL_CHECK_STOP: '+selection
        assert item['counts']['fail'] == item['counts']['skipped'] == item['counts']['cancelled'] == 0
    for selection,count in [('backend',20),('backend-regressions',52)]:
        assert final[selection]['exit_code']==0 and final[selection]['counts']['passed']==count
        assert not any(final[selection]['counts'].get(key,0) for key in ['failed','skipped','error','errors'])
    for selection in ['build','bundle','lint','integrity']:
        assert final[selection]['exit_code'] == 0, 'FINAL_CHECK_STOP: '+selection
    browser = json.loads((ROOT/final['browser']['path']).with_name('browser-results.json').read_text(encoding='utf-8'))
    assert len(browser['scenarios']) == 14 and all(item['status'] == 'PASS' for item in browser['scenarios'])
    assert not browser['runtime_errors'] and all(item['method']=='GET' for item in browser['requests'])
    failures = [item for item in attempts if item['exit_code']]
    assert len(failures)==5 and [item['selection'] for item in failures].count('browser')==2
    assert {item['selection'] for item in failures}=={'backend','build','browser','integrity'}
    assert len(pngs)==16 and len(image_hashes)==7, 'VISUAL_REVIEW_SCOPE_CHANGED_STOP'
    # Verify no Git metadata changed during the read-only audit itself.
    assert git('rev-parse', 'HEAD').strip() == HEAD and sha(ROOT/'.git/index') == baseline['.git/index']
    return dict(schema_version=1, milestone='U5A', implementation_status='PARTIAL', head=HEAD, branch='main',
        scope='Read-only V1 result projection and UI. Production CURRENT remains blocked by unestablished academic context. No provenance writes or baseline changes.',
        baseline_files=3039, unchanged_baseline_files=3031, academic_files=23,
        protected_preferences_and_settings='BYTE_IDENTICAL_TO_LOCAL_ENTRY_STATE; unstaged; raw hashes only',
        git_index_and_head='UNCHANGED', backend_ga_fingerprints_authority_auth_migrations_checkpoints_schedules='UNCHANGED',
        prior_latest_artifact_hashes_verified=prior_verified,
        explicitly_extended_prior_source_files=sorted(set(MODIFIED) & set(previous)),
        modified_from_entry=MODIFIED, new_files=[name for name in own if name not in MODIFIED],
        exact_u5a_inventory=own, staged_files=[], tracked_worktree_changes=sorted(actual_tracked),
        existing_untracked_paths_preserved=len(untracked & set(baseline)),
        artifact_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in paths},
        attempts=attempts, final_checks=final, historical_unsuccessful_attempts=failures,
        png_metadata_audit=pngs, unique_images=7,
        visual_privacy_review='All seven unique PNG contents viewed; sixteen retained images verified by raw hash. No image editing. Fictional resources, term/context and intercepted responses only.',
        privacy='PASS_PATTERNS_AND_IN_MEMORY_PRIVATE_NAME_COMPARISON; no credentials, signed receipts, authorization/cookie dumps or private faculty rows',
        whitespace='PASS', failed_attempts_preserved=True,
        postgresql_operations=0, production_ga_executions=0, existing_database_changes=0,
        temporary_sqlite_scope_exception='Earlier D10 API regressions performed fictional SQLite fixture schema/row writes. Exceeds blanket no-database-writes scope; disclosed for owner review. No further SQLite workflow tests after recognition.',
        backend_focused_tests=20, backend_regressions=52, frontend_focused_tests=16, frontend_regressions=182,
        user_reported_manual_attempt={'setup_errors':11,'deselected':7,'cause':'WinError 5 at pytest-of-User; user-attributed, not reproduced here'},
        fresh_backend_temp_isolation='Unique verified nonexistent --basetemp path; existing autouse checkpoint/history redirects and V1 Saved Best fixture reviewed; final no cacheprovider',
        browser_scenarios={'u5a':14,'u1':12,'u3':15,'u4':21,'live_center':20,'existing_ga':51,'total':133,'node_tests_with_parents':139,'actual_edge':True,'intercepted_http':True,'live_backend':False},
        browser=browser['browser'], warnings=['Installed TestClient/httpx and anyio BlockingPortal deprecations','Existing Vite mixed import and large chunk warnings','Git fsck dangling objects retained; no corruption reported'],
        blockers=['No server-established verified academic context or captured V1 term; genuine records cannot be promoted to strict CURRENT',
            'Saved Best has no captured producer provenance; persistent version-aware comparison requires separate authorization',
            'No global best across different configuration fingerprints',
            'V2 aggregation and institutional providers remain separate/unconfigured',
            'Owner review required for temporary SQLite scope exception before unqualified checkpoint signoff'],
        checkpoint_readiness='MANUAL_REVIEW_ONLY; no unqualified signoff; no staging/commit/push',
        limitations=['Complete-provenance CURRENT examples are fictional contract tests, not an installed institutional workflow',
            'No fresh live browser-to-FastAPI or PostgreSQL acceptance',
            'Full screen-reader/WCAG/device conformance not established'])


def main():
    finding = inspect()
    path = BASE/'manifest.json'
    if sys.argv[1:] == ['--record']:
        finding['recorded_at'] = datetime.now().astimezone().isoformat()
        with path.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(finding, indent=2, ensure_ascii=False)+'\n')
    else:
        previous = json.loads(path.read_text(encoding='utf-8'))
        for key, value in finding.items():
            assert previous[key] == value, 'MANIFEST_MISMATCH_STOP: '+key
    print(json.dumps(dict(status='U5A_AUDIT_PASSED', inventory=len(finding['exact_u5a_inventory']),
        hashed_artifacts=len(finding['artifact_sha256']), unchanged_baseline_files=3031,
        privacy='PASS', whitespace='PASS', head=HEAD)))


if __name__ == '__main__':
    main()
