"""Replay U3 evidence and entry-state preservation; --record creates the first manifest."""
from datetime import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
HEAD = 'f5262637acfb2d4d063cad1b0de80779a10bcba3'
MODIFIED = [
    'frontend/src/pages/admin/ChromosomeViewer.tsx',
    'frontend/src/pages/admin/ScheduleView.tsx',
    'frontend/src/pages/admin/FitnessAnalysis.tsx',
    'frontend/tests/resultPresentation.browser.test.mjs',
    'frontend/tests/gaMonitoring.browser.test.mjs',
]
NEW_FRONTEND = [
    'frontend/src/services/facultyCoverage.ts',
    'frontend/src/services/workloadPresentation.ts',
    'frontend/src/components/ga/WorkloadChart.tsx',
    'frontend/src/components/ga/workloadChart.css',
    'frontend/tests/evaluationCoverage.test.mjs',
    'frontend/tests/evaluationCoverage.fixtures.mjs',
    'frontend/tests/evaluationCoverage.browser.test.mjs',
]
REPORT = 'docs/dashboard-u3-evaluation-coverage-authority.md'
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
    assert len(baseline) == 2857 and len([p for p in baseline if p.startswith('backend/data/')]) == 23
    for path, digest in baseline.items():
        if path not in MODIFIED:
            assert (ROOT/path).is_file() and sha(ROOT/path) == digest, 'BASELINE_MISMATCH_STOP: '+path
    assert not git('diff', '--cached', '--name-only').strip(), 'STAGED_CHANGES_STOP'
    prior = [json.loads((ROOT/f'docs/testing/dashboard-u{number}/manifest.json').read_text(encoding='utf-8')) for number in (1, 2)]
    historical = []
    for number, manifest in enumerate(prior, 1):
        exemptions = []
        verified = 0
        for name, digest in manifest['artifact_sha256'].items():
            if name in MODIFIED:
                exemptions.append(name)
            else:
                assert sha(ROOT/name) == digest, 'PRIOR_ARTIFACT_MISMATCH_STOP: '+name
                verified += 1
        historical.append(dict(milestone=f'U{number}', verified=verified, authorized_source_extensions=sorted(exemptions)))
    tracked = set(git('ls-files', '-z').split('\0')) - {''}
    expected_modified = (set(MODIFIED) | set(prior[0]['modified_files']) | set(prior[1]['modified_files']) | PROTECTED) & tracked
    assert set(git('diff', '--name-only').splitlines()) == expected_modified, 'UNEXPECTED_TRACKED_SCOPE_STOP'
    # Check the U3 diff only. Never display, restore or parse protected preferences/settings.
    subprocess.run(['git', 'diff', '--check', '--', *[p for p in MODIFIED if p in tracked]], cwd=ROOT,
        env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'), check=True, capture_output=True)
    manifest_path = (BASE/'manifest.json').relative_to(ROOT).as_posix()
    own = sorted(set([REPORT, *MODIFIED, *NEW_FRONTEND,
        *(p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file()), manifest_path]))
    untracked = set(git('ls-files', '--others', '--exclude-standard', '-z').split('\0')) - {''}
    assert not (untracked - set(baseline) - set(own)), 'UNAPPROVED_NEW_PATH_STOP'
    paths = [ROOT/p for p in own if p != manifest_path]
    # Compare institutional names privately in memory; emit no names and never parse protected files.
    registry = json.loads((ROOT/'backend/data/faculty_identities.json').read_text(encoding='utf-8'))['faculty']
    names = {re.sub(r'\s+', ' ', value.strip().upper()) for row in registry
        for value in (row['name'], *row.get('aliases', [])) if len(value.strip()) >= 8}
    patterns = [r'eyJ[A-Za-z0-9_=-]{16,}', r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}',
        r'(?i)\b(?:postgresql|postgres|mysql)(?:\+\w+)?://[^\s]+',
        r'-----BEGIN [A-Z ]*PRIVATE KEY-----', r'(?i)https?://[^\s/]+:[^\s/@]+@',
        r'(?i)(?:set-cookie|authorization)\s*:\s*[^\s]{16,}']
    pngs = []
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        if path.suffix == '.png':
            raw = path.read_bytes()
            assert raw[:8] == b'\x89PNG\r\n\x1a\n', 'PNG_FORMAT_STOP'
            width, height = struct.unpack('>II', raw[16:24])
            offset = 8
            chunks = []
            while offset < len(raw):
                size = struct.unpack('>I', raw[offset:offset+4])[0]
                kind = raw[offset+4:offset+8]
                chunks.append(kind.decode('ascii'))
                assert kind not in {b'tEXt', b'zTXt', b'iTXt', b'eXIf'}, 'UNREVIEWED_IMAGE_METADATA_STOP'
                offset += 12+size
            assert offset == len(raw) and chunks[-1] == 'IEND', 'PNG_STRUCTURE_STOP'
            pngs.append(dict(path=relative, width=width, height=height, metadata_chunks=chunks))
            continue
        content = path.read_text(encoding='utf-8')
        assert content.endswith('\n') and all(line == line.rstrip() for line in content.splitlines()), 'WHITESPACE_STOP: '+relative
        # The pre-existing GA browser source contains retained named fixtures. Audit only its added
        # diff lines for privacy; changing one navigation must not copy/republish those fixture rows.
        if relative == 'frontend/tests/gaMonitoring.browser.test.mjs':
            diff = git('diff', '--', relative)
            additions = [line[1:] for line in diff.splitlines() if line.startswith('+') and not line.startswith('+++')]
            deletions = [line[1:] for line in diff.splitlines() if line.startswith('-') and not line.startswith('---')]
            assert len(additions) == len(deletions) == 1, 'GA_BROWSER_SCOPE_STOP'
            assert additions[0] == deletions[0].replace('/admin/chromosomes\'', '/admin/chromosomes?view=archive\''), 'GA_BROWSER_NAVIGATION_SCOPE_STOP'
            content = '\n'.join(additions)
        normalized = re.sub(r'\s+', ' ', content.upper())
        assert not any(re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)', normalized) for name in names), 'PRIVATE_IDENTITY_STOP_WITHHELD'
        assert not any(re.search(pattern, content) for pattern in patterns), 'SENSITIVE_PATTERN_STOP_WITHHELD'
    attempts = []
    for path in sorted(BASE.glob('*/command.json')):
        record = json.loads(path.read_text(encoding='utf-8'))
        counts = {key: int(value) for key, value in re.findall(r'(?m)^\S+ (tests|pass|fail|skipped|cancelled) (\d+)\s*$', record['stdout'])}
        assert not record['timed_out'], 'UNREVIEWED_TIMEOUT_STOP'
        attempts.append(dict(path=path.relative_to(ROOT).as_posix(), selection=record['selection'], exit_code=record['exit_code'], counts=counts))
    final = {item['selection']: item for item in attempts}
    for selection, count in [('focused',15),('regressions',121),('browser',16),('u1-browser',13),('u2-browser',18),('preferences-browser',23),('ga-browser',52)]:
        assert final[selection]['exit_code'] == 0 and final[selection]['counts']['pass'] == count, 'FINAL_CHECK_STOP: '+selection
        assert final[selection]['counts']['fail'] == final[selection]['counts']['skipped'] == final[selection]['counts']['cancelled'] == 0
    for selection in ['build', 'bundle', 'lint']:
        assert final[selection]['exit_code'] == 0, 'FINAL_CHECK_STOP: '+selection
    browser = json.loads((ROOT/final['browser']['path']).with_name('browser-results.json').read_text(encoding='utf-8'))
    assert len(browser['scenarios']) == 15 and all(item['status'] == 'PASS' for item in browser['scenarios'])
    assert not browser['runtime_errors'] and all(item['method'] == 'GET' for item in browser['requests'])
    failures = [item for item in attempts if item['exit_code']]
    assert [(item['selection'], item['counts']['pass'], item['counts']['fail']) for item in failures] == [('browser',13,2),('ga-browser',50,2)], 'HISTORICAL_FAILURE_RECONCILIATION_STOP'
    return dict(schema_version=1, milestone='U3', head=HEAD, branch='main',
        scope='Frontend presentation and policy proposals; no live FastAPI, GA generation, database or institutional authority acceptance.',
        baseline_files=2857, unchanged_baseline_files=2852, academic_files=23,
        protected_preferences_and_settings='BYTE_IDENTICAL_TO_LOCAL_ENTRY_STATE; unstaged; contents not parsed or printed',
        git_index_and_head='UNCHANGED', production_ga_and_historical_artifacts='UNCHANGED',
        preserved_prior_manifests_and_artifacts=historical,
        modified_entry_state_files=MODIFIED, new_files=[p for p in own if p not in MODIFIED], exact_u3_inventory=own,
        prior_tracked_changes_preserved=sorted(expected_modified - set(MODIFIED)),
        artifact_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in paths},
        attempts=attempts, final_checks=final, png_metadata_audit=pngs,
        visual_privacy_review='All seven retained U3 PNGs viewed; fictional account/resources only; no image editing.',
        privacy='PASS_PATTERNS_AND_PRIVATE_NAME_COMPARISON; existing GA browser privacy scan limited to its one added navigation line; no header/cookie dumps or signed receipts',
        whitespace='PASS', failed_attempts_preserved=True, database_operations=0,
        warnings=['Existing Vite mixed import and bundle size warnings'],
        browser_scenarios=dict(u3=15,u1=12,u2=17,existing_preferences=22,existing_ga=51,actual_edge=True,intercepted_http=True,live_backend=False),
        blockers=['Server-owned current-evaluation compatibility/reset contract unavailable',
            'Authoritative semester IT cohort/eligibility/availability not established',
            'Preparations definition/persistence/scoring require academic and technical approval',
            'Chair designation lifecycle requires an independently verified institutional mandate; production activation blocked'])


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
    print(json.dumps(dict(status='U3_AUDIT_PASSED', inventory=len(finding['exact_u3_inventory']),
        hashed_artifacts=len(finding['artifact_sha256']), unchanged_baseline_files=2852,
        privacy='PASS', whitespace='PASS', head=HEAD)))


if __name__ == '__main__':
    main()
