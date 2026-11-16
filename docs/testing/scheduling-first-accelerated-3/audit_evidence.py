"""Readable preservation and evidence seal; never promotes cache attestation."""
from collections import Counter
import csv
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
DEST = BASE/'manifest.json'
OWNED = ['backend/services/prototype_recovery_bootstrap.py',
    'backend/services/prototype_continuation_supervisor.py',
    'backend/tests/test_prototype_research_continuation.py',
    'docs/thesis-deadline-accelerated-increment-3.md']


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def blob(p):
    raw = Path(p).read_bytes()
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def git(*args):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    return subprocess.check_output(['git', '-c', 'core.autocrlf=false', *args], cwd=ROOT, env=env).decode('utf-8').strip()


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def strict_files(root):
    output = set()
    if not root.exists():
        return output
    # os.scandir propagates denial; Path.rglob could silently omit it.
    with os.scandir(root) as entries:
        for entry in entries:
            path = Path(entry.path)
            require(not path.is_symlink() and not path.is_junction(), 'RUNTIME_REPARSE')
            if entry.is_dir(follow_symlinks=False):
                output.update(strict_files(path))
            elif entry.is_file(follow_symlinks=False):
                output.add(path.relative_to(ROOT).as_posix())
    return output


def audit():
    entry, baseline = read(BASE/'entry.json'), read(BASE/'preservation-baseline.json')
    require(len(baseline) == entry['readable_baseline_count'] == 5822, 'BASELINE_COUNT')
    for n, h in baseline.items():
        require(sha(ROOT/n) == h, 'BASELINE_MISMATCH: '+n)
    require(git('rev-parse', 'HEAD') == entry['head'] and git('branch', '--show-current') == entry['branch'], 'HEAD_OR_BRANCH_CHANGED')
    require(git('rev-parse', 'main') == entry['main'], 'MAIN_CHANGED')
    require(not git('diff', '--cached', '--name-only'), 'UNEXPECTED_STAGING')
    require(set(git('diff', '--name-only').splitlines()) == set(entry['tracked_modifications']), 'TRACKED_PATH_SET_CHANGED')
    inventory = sorted(set(OWNED + [p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file()]
                           + [DEST.relative_to(ROOT).as_posix()]))
    present_inventory = set(inventory)-({DEST.relative_to(ROOT).as_posix()} if not DEST.exists() else set())
    require(set(git('ls-files', '--others', '--exclude-standard', '-z').split('\0'))-{''} == set(entry['untracked_files'])|present_inventory,
            'NEW_OR_MISSING_UNAPPROVED_PATH')
    prior_references = 0
    for folder in ['scheduling-first-increment-1', 'scheduling-first-increment-2', 'scheduling-first-increment-3',
                   'scheduling-first-accelerated-1', 'scheduling-first-accelerated-2']:
        m = read(ROOT/'docs/testing'/folder/'manifest.json')
        for n,h in m['artifact_sha256'].items():
            require(sha(ROOT/n) == h, 'PRIOR_ARTIFACT_MISMATCH'); prior_references += 1
        for n,h in m['proposed_raw_blob_oids'].items():
            require(blob(ROOT/n) == h, 'PRIOR_BLOB_MISMATCH')
    runtime_roots = [ROOT/n for n in ['backend/run_checkpoints', 'backend/saved_chromosomes',
        'backend/constrained_runs_v2', 'backend/run_input_receipts_v1']]
    for parent in ['backend', 'notebooks']:
        runtime_roots.extend(p for p in (ROOT/parent).glob('*_20*') if p.is_dir())
    runtime = {}
    for root in runtime_roots:
        prefix = root.relative_to(ROOT).as_posix()
        actual = strict_files(root)
        require(actual == {n for n in baseline if n.startswith(prefix+'/')}, 'RUNTIME_MEMBERSHIP_CHANGED: '+prefix)
        runtime[prefix] = len(actual)
    require(len([n for n in baseline if n.startswith('backend/data/')]) == 23, 'ACADEMIC_COUNT')
    actual_GA = {p.relative_to(ROOT).as_posix() for p in (ROOT/'backend/genetic_algorithm').rglob('*.py')}
    require(actual_GA == {n for n in baseline if n.startswith('backend/genetic_algorithm/') and n.endswith('.py')}, 'GA_SOURCE_SET_CHANGED')
    latest = {s:read(sorted(BASE.glob('*-'+s+'/command.json'))[-1]) for s in ['core','regressions','parity','integrity']}
    counts = dict(core=26, regressions=5, parity=5, integrity=12)
    for s,n in counts.items():
        require(latest[s]['exit_code'] == 0 and re.search(r'\b'+str(n)+r' passed\b',latest[s]['stdout']), 'TEST_RESULT_NOT_QUALIFIED: '+s)
    for n in ['backend/services/prototype_recovery_bootstrap.py', 'backend/services/prototype_continuation_supervisor.py',
              'backend/tests/test_prototype_research_continuation.py',
              'docs/testing/scheduling-first-accelerated-3/cold_metadata_probe.py']:
        require(latest['core']['source_sha256'][n] == sha(ROOT/n), 'FINAL_CORE_SOURCE_MISMATCH')
    # These preserved sources were exercised by the existing API/parity groups.
    for s in ['regressions', 'parity', 'integrity']:
        for n,h in latest[s]['source_sha256'].items():
            if n in baseline:
                require(sha(ROOT/n) == h, 'REGRESSION_SOURCE_MISMATCH')
    require(latest['integrity']['source_sha256']['docs/testing/scheduling-first-accelerated-3/run_checks.py'] == sha(BASE/'run_checks.py'),
            'FINAL_RUNNER_NOT_EXERCISED')
    patterns = [r'eyJ[A-Za-z0-9_\-]{16,}', r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        r'(?:postgres(?:ql)?|https?)://[^\s/:]+:[^\s/@]+@', r'gh[pousr]_[A-Za-z0-9]{30,}', r'github_pat_[A-Za-z0-9_]{40,}',
        r'(?i)(?:Bearer|session_receipt|preview_receipt|access_token|refresh_token)[\s"\x27:=]+[A-Za-z0-9_\-]{20,}']
    names = set()
    for n in ['Faculty.csv','Faculty Preferences V2.csv']:
        with (ROOT/'backend/data'/n).open(encoding='utf-8-sig',newline='') as stream:
            for row in csv.DictReader(stream):
                value = (row.get('Faculty') or '').strip().casefold()
                if len(value) >= 5:
                    names.add(value)
    artifacts, blobs = {}, {}
    for n in inventory:
        path = ROOT/n
        if path == DEST and not path.exists():
            continue
        require(path.is_file() and not path.is_symlink() and not path.is_junction(), 'INVALID_NEW_PATH')
        text = path.read_text(encoding='utf-8')
        require(not any(re.search(p,text) for p in patterns), 'SENSITIVE_PATTERN: '+n)
        require(not any(name in text.casefold() for name in names), 'PRIVATE_NAME: '+n)
        if path.suffix == '.json':
            json.loads(text)
        check = subprocess.run(['git','-c','core.autocrlf=false','-c','core.whitespace=blank-at-eol,blank-at-eof,cr-at-eol',
            'diff','--no-index','--check','--','NUL',str(path)],cwd=ROOT,capture_output=True)
        require(check.returncode in (0,1) and not check.stdout and not check.stderr, 'WHITESPACE_FAILURE: '+n)
        if path != DEST:
            artifacts[n],blobs[n] = sha(path),blob(path)
    require(subprocess.run(['git','fsck','--no-reflogs'],cwd=ROOT,capture_output=True).returncode == 0, 'GIT_INTEGRITY')
    attempts = []
    for p in sorted(BASE.glob('*/command.json')):
        d = read(p); attempts.append(dict(path=p.relative_to(ROOT).as_posix(), selection=d['selection'],
            exit_code=d['exit_code'],elapsed_seconds=d['elapsed_seconds']))
    return dict(schema='scheduling-first-accelerated-3-evidence-v1',recorded_at=datetime.now(ZoneInfo('Asia/Manila')).isoformat(),
        head=entry['head'],branch=entry['branch'],main=entry['main'],exact_new_file_inventory=inventory,new_files=len(inventory),
        file_types=dict(Counter(Path(n).suffix for n in inventory)),existing_files_modified=[],
        artifact_sha256=artifacts,proposed_raw_blob_oids=blobs,self_hash_excluded=True,attempts=attempts,
        tests=dict(final_core=26,scheduling_and_API_regressions=5,original_GA_parity=5,checkpoint_integrity=12,
            distinct_passing_cases=48,combined_suite=False,collection_not_counted=True,earlier_successes_not_added=True,
            failed_attempts_retained=1,failed_attempt_classification='NEW_HARNESS_MISSING_PRESERVED_FRONTEND_ASSETS_4PASS_1FAIL',
            final_source_hashes='PASS',fresh_readonly_metadata_process='PASS_NO_GA_RUN',
            full_object_graph_reconstruction='PASS',physical_crash_or_native_resume='NOT_RUN',
            real_TCP_HTTP='NOT_RERUN',HTTP='REAL_TESTCLIENT_COOKIE_CSRF_SQLITE_AND_GENUINE_IN_PROCESS_RESULTS',
            frontend_contracts_types_build='NOT_RERUN_NO_FRONTEND_CHANGES',native_workers=0,Edge=0),
        preservation=dict(readable_baseline_verified=5822,academic_files=23,tracked_modifications_preserved=11,
            entry_untracked_preserved=972,ignored_runtime_membership=runtime,prior_artifact_references=prior_references,
            protected_JSON_original_GA_migrations_notebooks_Saved_Best_checkpoints='UNCHANGED',
            index_HEAD_config_unchanged=True,inaccessible_cache='backend/.pytest_cache',
            cache_origin='UNAUTHENTICATED_NOT_PROMOTED',full_preservation_qualification=False),
        privacy=dict(credential_patterns='PASS',private_faculty_name_local_comparison='PASS',fictional_fixture_review='PASS',
            raw_checkpoint_RNG_key_or_bootstrap_archived=False,limitation='Scans cannot prove absence of every possible secret'),
        whitespace='PASS_CRLF_AWARE',git_integrity='PASS',no_ACL_or_ownership_changes=True,no_permission_elevation=True,
        institutional_database_operations=0,dependency_installations=0,staged=False,committed=False,pushed=False,deployed=False,
        production_admission='BLOCKED',institutional_promotion='BLOCKED',institutional_continuous_optimization='DISABLED',
        active_institutional_restore='BLOCKED',native_adapter='NOT_IMPLEMENTED_NOT_QUALIFIED',seven_day='NO_GO',checkpoint_ready=False)


if __name__ == '__main__':
    doc = audit()
    if sys.argv[1:] == ['--create']:
        with DEST.open('x',encoding='utf-8',newline='\n') as stream:
            stream.write(json.dumps(doc,indent=2)+'\n')
    else:
        require(not sys.argv[1:], 'UNSUPPORTED_ARGUMENT')
        old = read(DEST)
        for key in ['artifact_sha256','proposed_raw_blob_oids','exact_new_file_inventory','preservation','tests']:
            require(old[key] == doc[key], 'SEALED_MANIFEST_MISMATCH: '+key)
    print(json.dumps(dict(status='READABLE_PRESERVATION_AND_EVIDENCE_PASS_FULL_GATE_UNRESOLVED',
        files=doc['new_files'],artifacts=len(doc['artifact_sha256']),baseline=5822,prior_references=doc['preservation']['prior_artifact_references'],
        distinct_Python_passes=48,native_workers=0,Edge=0,seven_day='NO_GO')))
