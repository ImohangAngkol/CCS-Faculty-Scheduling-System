"""Read-only qualification checks; --create writes only a NEW evidence manifest.

Does not access the denied backend cache, authenticate owner attestations, launch
the optimizer, or qualify native/browser acceptance. No Git index writes.
"""
from collections import Counter
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
MANIFEST = BASE/'manifest.json'
OWNED = [
    'backend/routers/prototype_cycle.py',
    'backend/services/prototype_cycle.py',
    'backend/services/prototype_tip_witness.py',
    'backend/tests/test_prototype_cycle.py',
    'backend/tests/test_prototype_cycle_api.py',
    'frontend/src/prototypeCycle/index.html',
    'frontend/src/prototypeCycle/model.mjs',
    'frontend/src/prototypeCycle/console.mjs',
    'frontend/tests/prototypeCycle.test.mjs',
    'frontend/tests/prototypeCycle.live.mjs',
    'docs/thesis-deadline-accelerated-increment-2.md',
]


def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blob(path):
    raw = path.read_bytes()
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-c', 'core.autocrlf=false', *args], cwd=ROOT).decode('utf-8').strip()


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def audit():
    entry = read('docs/testing/scheduling-first-accelerated-2/entry.json')
    baseline = read(entry['prior_baseline_ref'])
    baseline.update(entry['supplemental_baseline_sha256'])
    require(len(baseline) == entry['readable_baseline_count'] == 5761, 'BASELINE_BINDING')
    for name, expected in baseline.items():
        require(sha(ROOT/name) == expected, 'BASELINE_CONTENT_MISMATCH: '+name)
    require(git('rev-parse', 'HEAD') == entry['head'], 'HEAD_CHANGED')
    require(git('branch', '--show-current') == entry['branch'], 'BRANCH_CHANGED')
    require(not git('diff', '--cached', '--name-only'), 'INDEX_NOT_EMPTY')
    require(set(git('diff', '--name-only').splitlines()) == set(entry['tracked_modifications']), 'TRACKED_PATH_SET_CHANGED')
    for name, expected in entry['original_metadata'].items():
        require(sha(ROOT/name) == expected, 'GIT_METADATA_CHANGED')
    previous_entry = read('docs/testing/scheduling-first-increment-2/entry.json')
    old_untracked = set(previous_entry['untracked_files'])
    references = 0
    for folder in ['scheduling-first-increment-1', 'scheduling-first-increment-2',
                   'scheduling-first-increment-3', 'scheduling-first-accelerated-1']:
        previous = read('docs/testing/'+folder+'/manifest.json')
        for name, expected in previous['artifact_sha256'].items():
            require(sha(ROOT/name) == expected, 'PRIOR_ARTIFACT_MISMATCH')
            references += 1
        for name, expected in previous.get('proposed_raw_blob_oids', {}).items():
            require(blob(ROOT/name) == expected, 'PRIOR_BLOB_MISMATCH')
        if folder != 'scheduling-first-increment-1':
            old_untracked.update(previous['exact_new_file_inventory'])
    require(len(old_untracked) == entry['entry_untracked_count'] == 1059, 'UNTRACKED_BASELINE_BINDING')
    inventory = sorted(set(OWNED + [p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file()]
                           + [MANIFEST.relative_to(ROOT).as_posix()]))
    require(set(git('ls-files', '--others', '--exclude-standard').splitlines()) ==
            old_untracked | (set(inventory)-({MANIFEST.relative_to(ROOT).as_posix()} if not MANIFEST.exists() else set())),
            'UNAPPROVED_NEW_OR_MISSING_FILES')
    ga_files = {p.relative_to(ROOT).as_posix() for p in (ROOT/'backend/genetic_algorithm').rglob('*.py')}
    require(ga_files == {n for n in baseline if n.startswith('backend/genetic_algorithm/') and n.endswith('.py')},
            'ORIGINAL_GA_SOURCE_SET_CHANGED')
    academic = [n for n in baseline if n.startswith('backend/data/')]
    require(len(academic) == 23, 'ACADEMIC_INVENTORY_MISMATCH')
    # Names are compared locally only; neither values nor their fragments are emitted.
    names = set()
    for filename in ['Faculty.csv', 'Faculty Preferences V2.csv']:
        with (ROOT/'backend/data'/filename).open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream):
                name = (row.get('Faculty') or '').strip().casefold()
                if len(name) >= 5:
                    names.add(name)
    patterns = [r'eyJ[A-Za-z0-9_\-]{16,}', r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
                r'(?:postgres(?:ql)?|https?)://[^\s/:]+:[^\s/@]+@',
                r'(?i)(?:Bearer|session_receipt|preview_receipt|access_token|refresh_token)[\s"\x27:=]+[A-Za-z0-9_\-]{20,}']
    artifacts, blobs = {}, {}
    for name in inventory:
        path = ROOT/name
        if path == MANIFEST:
            continue
        require(path.is_file() and not path.is_symlink() and not path.is_junction(), 'ARTIFACT_PATH_INVALID')
        raw = path.read_text(encoding='utf-8')
        require(not any(re.search(pattern, raw) for pattern in patterns), 'SENSITIVE_PATTERN_IN: '+name)
        require(not any(n in raw.casefold() for n in names), 'PRIVATE_NAME_IN: '+name)
        if path.suffix == '.json':
            json.loads(raw)
        check = subprocess.run(['git', '-c', 'core.autocrlf=false', '-c',
            'core.whitespace=blank-at-eol,blank-at-eof,cr-at-eol', 'diff', '--no-index', '--check', '--',
            'NUL', str(path)], cwd=ROOT, capture_output=True)
        require(check.returncode in (0, 1) and not check.stdout and not check.stderr, 'WHITESPACE_FAILURE: '+name)
        artifacts[name], blobs[name] = sha(path), blob(path)
    fsck = subprocess.run(['git', 'fsck', '--no-reflogs'], cwd=ROOT, capture_output=True)
    require(fsck.returncode == 0, 'GIT_INTEGRITY_FAILURE')
    attempts = []
    for path in sorted(BASE.glob('*/command.json')):
        d = json.loads(path.read_text(encoding='utf-8'))
        attempts.append(dict(path=path.relative_to(ROOT).as_posix(), selection=d['selection'],
                             exit_code=d['exit_code'], elapsed_seconds=d['elapsed_seconds']))
    return dict(schema='scheduling-first-accelerated-2-evidence-v1',
        recorded_at=datetime.now(ZoneInfo('Asia/Manila')).isoformat(), head=entry['head'], branch=entry['branch'],
        exact_new_file_inventory=inventory, new_files=len(inventory),
        file_types=dict(Counter(Path(n).suffix for n in inventory)), existing_files_modified=[],
        artifact_sha256=artifacts, proposed_raw_blob_oids=blobs, self_hash_excluded=True, attempts=attempts,
        results=read('docs/testing/scheduling-first-accelerated-2/qualification.json'),
        preservation=dict(readable_baseline_verified=len(baseline), mismatches=[], academic_files_verified=23,
            original_tracked_modifications_preserved=11, entry_untracked_preserved=1059,
            protected_JSON='UNCHANGED_UNSTAGED', GA_sources_and_fingerprint_sources='UNCHANGED',
            prior_artifact_references_verified=references, git_index_HEAD_config_unchanged=True,
            ignored_historical_runtime_groups={folder: len([n for n in baseline if n.startswith(folder+'/')])
                for folder in ['backend/run_checkpoints', 'backend/saved_chromosomes', 'backend/data', '.pytest_cache']},
            excluded_dependency_build_roots=previous_entry['excluded_roots'],
            inaccessible_directories=previous_entry['inaccessible_directories'],
            owner_cache_attestation='UNAUTHENTICATED_NOT_PROMOTED', full_preservation_qualification=False,
            prior_evidence_preserved=True, current_attempt_rng_redaction='EXPLICIT_REDACTION_ADDENDUM_RETAINED'),
        privacy=dict(encoded_credential_fragment_scan='PASS', private_faculty_name_local_comparison='PASS',
            fixture_review='FICTIONAL_ONLY', raw_RNG_checkpoint_key_exported=False,
            limitation='Pattern/name scans do not prove absence of all possible secrets'),
        whitespace='PASS_CRLF_AWARE', git_integrity='PASS', native_workers=0, Edge=0,
        OS_process_restart=False, institutional_database_operations=0, dependency_installations=0,
        ordinary_React_types_build='NOT_RERUN_NO_EXISTING_REACT_OR_TS_INPUT_CHANGES',
        production_admission='BLOCKED', institutional_promotion='BLOCKED',
        institutional_continuous_optimization='DISABLED', active_institutional_restore='BLOCKED',
        seven_day='NO_GO', native_and_browser_acceptance='BLOCKED_PRESERVATION_AND_RESOURCE_GATES',
        staged=False, committed=False, pushed=False, deployed=False, checkpoint_ready=False)


if __name__ == '__main__':
    document = audit()
    if sys.argv[1:] == ['--create']:
        with MANIFEST.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(document, indent=2)+'\n')
    else:
        require(not sys.argv[1:], 'UNSUPPORTED_ARGUMENT')
        recorded = json.loads(MANIFEST.read_text(encoding='utf-8'))
        for key in ['artifact_sha256', 'proposed_raw_blob_oids', 'exact_new_file_inventory', 'results', 'preservation']:
            require(document[key] == recorded[key], 'SEALED_MANIFEST_MISMATCH: '+key)
    print(json.dumps(dict(status='READABLE_CONTENT_AND_EVIDENCE_VERIFIED_FULL_GATE_UNRESOLVED',
        new_files=document['new_files'], artifact_hashes=len(document['artifact_sha256']),
        readable_baseline=5761, prior_artifact_references=document['preservation']['prior_artifact_references_verified'],
        full_preservation_qualification=False, seven_day='NO_GO')))
