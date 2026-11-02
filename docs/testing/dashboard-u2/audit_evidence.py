"""Read-only replay of U2 hashes/privacy/preservation; --record creates the first manifest."""
from datetime import datetime
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
    'frontend/src/components/common/Sidebar.tsx',
    'frontend/src/layouts/AdminLayout.tsx',
    'frontend/src/layouts/FacultyLayout.tsx',
    'frontend/src/components/faculty/FacultyPreferenceEditor.tsx',
    'frontend/src/components/faculty/preferences.css',
    'frontend/tests/preferences.browser.test.mjs',
]
NEW_FRONTEND = [
    'frontend/src/components/common/dashboardLayout.css',
    'frontend/src/components/faculty/PreferenceControls.tsx',
    'frontend/tests/dashboardControls.test.mjs',
    'frontend/tests/dashboardControls.browser.test.mjs',
]
REPORT = 'docs/dashboard-u2-navigation-preferences.md'
PROTECTED = {'backend/data/faculty_preferences.json', 'backend/data/ga_settings.json'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT,
        env=dict(os.environ, GIT_OPTIONAL_LOCKS='0')).decode('utf-8')


def inspect():
    assert git('rev-parse', 'HEAD').strip() == HEAD, 'HEAD_CHANGED_STOP'
    baseline = json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'))
    assert len(baseline) == 2778
    assert len([p for p in baseline if p.startswith('backend/data/')]) == 23
    for path, digest in baseline.items():
        if path not in MODIFIED:
            assert (ROOT/path).is_file() and sha(ROOT/path) == digest, 'BASELINE_MISMATCH_STOP: '+path
    assert not git('diff', '--cached', '--name-only').strip(), 'STAGED_CHANGES_STOP'
    modified = set(git('diff', '--name-only').splitlines())
    u1=json.loads((ROOT/'docs/testing/dashboard-u1/manifest.json').read_text(encoding='utf-8'))
    for name,digest in u1['artifact_sha256'].items():
        assert sha(ROOT/name)==digest,'U1_ARTIFACT_MISMATCH_STOP: '+name
    assert modified == set(MODIFIED) | set(u1['modified_files']) | PROTECTED, 'UNEXPECTED_TRACKED_SCOPE_STOP'
    subprocess.run(['git', 'diff', '--check', '--', *MODIFIED], cwd=ROOT, check=True, capture_output=True)
    own = sorted([REPORT, *MODIFIED, *NEW_FRONTEND,
        *(p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file())])
    # Include manifest in the exact inventory, but not in its own hash list.
    manifest_path = (BASE/'manifest.json').relative_to(ROOT).as_posix()
    own = sorted(set(own) | {manifest_path})
    untracked = set(git('ls-files', '--others', '--exclude-standard', '-z').split('\0')) - {''}
    assert not (untracked - set(baseline) - set(own)), 'UNAPPROVED_NEW_PATH_STOP'
    paths = [ROOT/p for p in own if p != manifest_path]
    # Compare private names in memory only; no protected preferences/settings are parsed.
    registry = json.loads((ROOT/'backend/data/faculty_identities.json').read_text(encoding='utf-8'))['faculty']
    names = {re.sub(r'\s+', ' ', value.strip().upper()) for row in registry
        for value in (row['name'], *row.get('aliases', [])) if len(value.strip()) >= 8}
    patterns = [r'eyJ[A-Za-z0-9_=-]{16,}', r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}',
        r'(?i)\b(?:postgresql|postgres|mysql)(?:\+\w+)?://[^\s]+',
        r'-----BEGIN [A-Z ]*PRIVATE KEY-----', r'(?i)https?://[^\s/]+:[^\s/@]+@',
        r'(?i)(?:set-cookie|authorization)\s*:\s*[^\s]{16,}']
    pngs = []
    for path in paths:
        if path.suffix == '.png':
            raw = path.read_bytes()
            assert raw[:8] == b'\x89PNG\r\n\x1a\n', 'PNG_FORMAT_STOP'
            offset = 8
            chunks = []
            while offset < len(raw):
                size = struct.unpack('>I', raw[offset:offset+4])[0]
                kind = raw[offset+4:offset+8]
                chunks.append(kind.decode('ascii'))
                assert kind not in {b'tEXt', b'zTXt', b'iTXt', b'eXIf'}, 'UNREVIEWED_IMAGE_METADATA_STOP'
                offset += 12+size
            pngs.append(dict(path=path.relative_to(ROOT).as_posix(), metadata_chunks=chunks))
            continue
        text = path.read_text(encoding='utf-8')
        assert text.endswith('\n') and all(line == line.rstrip() for line in text.splitlines()), 'WHITESPACE_STOP: '+str(path.relative_to(ROOT))
        normalized = re.sub(r'\s+', ' ', text.upper())
        assert not any(re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)', normalized) for name in names), 'PRIVATE_IDENTITY_STOP_WITHHELD'
        assert not any(re.search(pattern, text) for pattern in patterns), 'SENSITIVE_PATTERN_STOP_WITHHELD'
    attempts = []
    for path in sorted(BASE.glob('*/command.json')):
        record = json.loads(path.read_text(encoding='utf-8'))
        counts = {key: int(value) for key, value in re.findall(r'(?m)^\S+ (tests|pass|fail|skipped|cancelled) (\d+)\s*$', record['stdout'])}
        attempts.append(dict(path=path.relative_to(ROOT).as_posix(), selection=record['selection'], exit_code=record['exit_code'], counts=counts))
    final = {item['selection']: item for item in attempts}
    for selection, count in [('focused',9),('regressions',112),('browser',18),('u1-browser',13),('ga-browser',52),('preferences-browser',23)]:
        assert final[selection]['exit_code'] == 0 and final[selection]['counts']['pass'] == count, 'FINAL_CHECK_STOP: '+selection
    for selection in ['build','bundle','lint']:
        assert final[selection]['exit_code'] == 0
    browser = json.loads((ROOT/final['browser']['path']).with_name('browser-results.json').read_text(encoding='utf-8'))
    assert len(browser['scenarios']) == 17 and all(item['status'] == 'PASS' for item in browser['scenarios'])
    assert not browser['runtime_errors'] and all(item['method'] in {'GET','PUT','OPTIONS'} for item in browser['requests'])
    assert browser['fictional_put_count']==1
    assert all(item['path']=='/preferences/1' for item in browser['requests'] if item['method']=='PUT')
    return dict(schema_version=1, milestone='U2', head=HEAD, branch=git('branch','--show-current').strip(),
        scope='Frontend presentation; no live backend, GA generation, database or institutional acceptance.',
        compatibility='U1 classification and authority boundaries unchanged',
        baseline_files=2778, unchanged_baseline_files=2772, academic_files=23,
        protected_preferences_and_settings='BYTE_IDENTICAL_TO_LOCAL_ENTRY_STATE; unstaged',
        git_index_and_head='UNCHANGED', production_ga_and_historical_artifacts='UNCHANGED',
        modified_files=MODIFIED, new_files=[p for p in own if p not in MODIFIED], exact_u2_inventory=own,
        artifact_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in paths},
        attempts=attempts, final_checks=final, png_metadata_audit=pngs,
        visual_privacy_review='All retained U2 PNGs viewed; fictional account/resources only.',
        privacy='PASS_TEXT_PATTERNS_AND_IN_MEMORY_PRIVATE_NAME_COMPARISON; no cookie/header dumps or signed receipts',
        whitespace='PASS', failed_attempts_preserved=True, database_operations=0,
        warnings=['Vite mixed import and bundle size warnings'],
        browser_scenarios=dict(u2=17,u1=12,existing_ga=51,existing_preferences=22,not_live_backend=True))


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
    print(json.dumps(dict(status='U2_AUDIT_PASSED', inventory=len(finding['exact_u2_inventory']),
        hashed_artifacts=len(finding['artifact_sha256']), unchanged_baseline_files=2772,
        privacy='PASS', whitespace='PASS', head=HEAD)))


if __name__ == '__main__':
    main()
