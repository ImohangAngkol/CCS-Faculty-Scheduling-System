"""Read/hash only outside this increment; never authenticates owner attestations."""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
REPORT = 'docs/scheduling-first-increment-2.md'
OWNED = [
    'backend/routers/prototype_scheduling.py', 'backend/services/prototype_scheduling.py',
    'backend/services/prototype_run_store.py', 'backend/tests/test_prototype_scheduling.py',
    'backend/tests/test_prototype_scheduling_native.py', 'frontend/src/prototypeScheduling/index.html',
    'frontend/src/prototypeScheduling/model.mjs', 'frontend/src/prototypeScheduling/console.mjs',
    'frontend/tests/prototypeScheduling.test.mjs', REPORT,
]


def git(*args):
    return subprocess.check_output(['git', '-c', 'core.autocrlf=false', *args], cwd=ROOT).decode('utf-8').strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit():
    entry = json.loads((BASE/'entry.json').read_text())
    baseline = json.loads((BASE/'preservation-baseline.json').read_text())
    mismatches = []
    for name, expected in baseline.items():
        try:
            if sha(ROOT/name) != expected:
                mismatches.append(name)
        except OSError:
            mismatches.append(name)
    assert not mismatches, 'PRESERVATION_MISMATCH: '+repr(mismatches)
    assert git('rev-parse', 'HEAD') == entry['head'] and git('branch', '--show-current') == entry['branch']
    assert not git('diff', '--cached', '--name-only'), 'UNEXPECTED_STAGING'
    assert set(git('diff', '--name-only').splitlines()) == set(entry['tracked_modifications'])
    inventory = sorted(OWNED + [p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file()])
    if (BASE/'manifest.json').exists():
        assert json.loads((BASE/'manifest.json').read_text())['exact_new_file_inventory'] == inventory
    current_new = set(git('ls-files', '--others', '--exclude-standard').splitlines())
    assert current_new == set(entry['untracked_files']) | set(inventory), 'UNEXPECTED_NEW_OR_MISSING_PATHS'
    previous = json.loads((ROOT/'docs/testing/scheduling-first-increment-1/manifest.json').read_text())
    assert all(sha(ROOT/n) == h for n, h in previous['artifact_sha256'].items())
    assert len(previous['artifact_sha256']) == 28
    # Look for actual encoded credential/receipt fragments, never echo matches.
    patterns = [r'eyJ[A-Za-z0-9_\-]{16,}', r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
                r'(?:postgres(?:ql)?|https?)://[^\s/:]+:[^\s/@]+@',
                r'(?i)(?:Bearer|session_receipt|preview_receipt|access_token|refresh_token)[\s"\x27:=]+[A-Za-z0-9_\-]{20,}']
    privacy_failures, whitespace = [], []
    for name in inventory:
        path = ROOT/name
        if name.endswith('.json'):
            raw = path.read_text(encoding='utf-8')
            if any(re.search(pattern, raw) for pattern in patterns):
                privacy_failures.append(name)
            json.loads(raw)
        result = subprocess.run(['git', '-c', 'core.autocrlf=false', '-c', 'core.whitespace=blank-at-eol,blank-at-eof,cr-at-eol',
                                 'diff', '--no-index', '--check', '--', 'NUL', str(path)], cwd=ROOT, capture_output=True)
        if result.returncode not in (0, 1) or result.stdout or result.stderr:
            whitespace.append(name)
    assert not privacy_failures, 'PRIVACY_PATTERN_FOUND: '+repr(privacy_failures)
    assert not whitespace, 'WHITESPACE_FAILURE: '+repr(whitespace)
    committed = subprocess.run(['git', 'fsck', '--no-reflogs'], cwd=ROOT, capture_output=True)
    assert committed.returncode == 0, 'GIT_INTEGRITY_FAILURE'
    artifacts = {n: sha(ROOT/n) for n in inventory if n != (BASE/'manifest.json').relative_to(ROOT).as_posix()}
    blobs = {}
    for n in inventory:
        if n.endswith('/manifest.json'):
            continue  # Cannot self-embed its own raw identity.
        raw = (ROOT/n).read_bytes()
        blobs[n] = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    attempts = []
    for path in sorted(BASE.glob('*/command.json')):
        record = json.loads(path.read_text())
        attempts.append(dict(path=path.relative_to(ROOT).as_posix(), selection=record['selection'],
                             exit_code=record['exit_code'], elapsed_seconds=record['elapsed_seconds']))
    return dict(recorded_at=datetime.now(ZoneInfo('Asia/Manila')).isoformat(), head=entry['head'], branch=entry['branch'],
        exact_new_file_inventory=inventory, new_files=len(inventory), file_types=dict(Counter(Path(n).suffix for n in inventory)),
        existing_files_modified=[], artifact_sha256=artifacts, proposed_raw_blob_oids=blobs, attempts=attempts,
        preservation=dict(readable_baseline_paths_verified=len(baseline), mismatches=[], prior_increment_artifacts_verified=28,
            academic_files_verified=len([n for n in baseline if n.startswith('backend/data/')]),
            protected_JSON='SHA256_UNCHANGED_UNSTAGED', tracked_changes_preserved=len(entry['tracked_modifications']),
            entry_untracked_preserved=len(entry['untracked_files']), git_index_HEAD_config_unchanged=True,
            inaccessible_directories=entry['inaccessible_directories'], full_preservation_qualification=False,
            operator_attestation_origin='UNAUTHENTICATED_NOT_PROMOTED', historical_runtime_coverage='ALL_READABLE_BASELINED_PATHS_MATCH'),
        privacy=dict(encoded_fragment_scan='PASS', fixture_review='FICTIONAL_ONLY', exported_credentials=False,
            raw_RNG_or_signed_receipts_exported=False, limitation='Pattern scans are not proof against all possible secrets'),
        whitespace='PASS_CRLF_AWARE_NEW_FILE_DIFFS', git_integrity='PASS', staged=False, committed=False,
        native_acceptance='NOT_RUN_OPERATOR_REQUEST_AND_RESOURCE_GATE', Edge='NOT_RUN_RESOURCE_GATE',
        results=dict(final_backend_passed=42, final_frontend_passed=32,
            new_backend_tests=19, existing_workload_regressions=18, original_GA_parity_and_continuation=5,
            new_frontend_contracts=12, existing_frontend_contracts=20,
            TypeScript='PASS_EXISTING_REACT_SCOPE', production_build='PASS_EXISTING_REACT_SCOPE',
            focused_lint='PASS_FINAL_STANDALONE_SOURCE', native_workers_executed=0, browser_scenarios_executed=0,
            diagnostic_lifecycle_tests='MOCKED_RUNTIME_OR_PROOF_BOUNDARY_NOT_OPTIMIZER_ACCEPTANCE'),
        production_admission='BLOCKED', institutional_saved_best='BLOCKED', continuous_optimization='DISABLED',
        active_restore='BLOCKED', seven_day='NO_GO', checkpoint_ready=False)


if __name__ == '__main__':
    # Bootstrap writes a NEW manifest once; later calls only verify it.
    import sys
    destination = BASE/'manifest.json'
    if sys.argv[1:] == ['--create']:
        assert not destination.exists()
        # Include manifest in the prospective exact inventory without hashing it.
        with destination.open('x', encoding='utf-8') as stream:
            stream.write('{}\n')
        # audit expects the final inventory; compute it independently here.
        inventory = sorted(OWNED+[p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file()])
        destination.write_text(json.dumps({'exact_new_file_inventory': inventory}), encoding='utf-8')
        document = audit()
        destination.write_text(json.dumps(document, indent=2)+'\n', encoding='utf-8')
    else:
        document = audit()
        recorded = json.loads(destination.read_text())
        assert document['artifact_sha256'] == recorded['artifact_sha256']
        assert document['proposed_raw_blob_oids'] == recorded['proposed_raw_blob_oids']
    print(json.dumps(dict(status='ACCESSIBLE_PRESERVATION_AND_ARTIFACTS_VERIFIED_FULL_GATE_UNRESOLVED',
        files=document['new_files'], artifacts=len(document['artifact_sha256']),
        baseline=document['preservation']['readable_baseline_paths_verified'], checkpoint_ready=False)))
