"""Read-only qualification checks; never imports or launches the GA/browser.

Writes one new evidence JSON only. Does not replace a failed preservation gate
with the operator's unsigned historical assertion.
"""
import ast
import ctypes
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
I2 = ROOT/'docs/testing/scheduling-first-increment-2'
CACHE = ROOT/'backend/.pytest_cache'
DIAG = ROOT/'docs/testing/dashboard-u5pf/cache-access-diagnosis'
EXPECTED_HEAD = '2315689196875621288939fde4a3268932305d8d'
PINNED_I2 = '386a71fe31e9673d4d6f0ba86681dcd34bcd5808521fe5cc8dd9e265dc2c0f7b'
PINNED_TOOL = '4ddebabd40d474b499ac7e57a32ec219f2a3aa064143d1ca1b7e06cb517e653d'
PINNED_CACHE_BASELINE = 'a301e0821f6d025e0ae39e8231051d6233665c4f5f4ff59255cb05c6a50ff04b'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '--no-optional-locks', '-c', 'core.autocrlf=false', *args], cwd=ROOT).decode('utf-8').strip()


def clock():
    return datetime.now(ZoneInfo('Asia/Manila')).isoformat()


def main():
    started = clock()
    destination = BASE/'preflight.json'
    assert not destination.exists(), 'Existing evidence must not be overwritten'
    assert git('rev-parse', 'HEAD') == EXPECTED_HEAD
    assert git('branch', '--show-current') == 'wip/u5pf-experiment-exports'
    assert not git('diff', '--cached', '--name-only')
    assert sha(I2/'manifest.json') == PINNED_I2
    manifest = json.loads((I2/'manifest.json').read_text())
    baseline = json.loads((I2/'preservation-baseline.json').read_text())
    assert len(baseline) == 5703
    assert all(sha(ROOT/n) == h for n, h in baseline.items()), 'Readable baseline mismatch'
    assert len(manifest['artifact_sha256']) == 26
    assert all(sha(ROOT/n) == h for n, h in manifest['artifact_sha256'].items())
    for name, expected in manifest['proposed_raw_blob_oids'].items():
        raw = (ROOT/name).read_bytes()
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == expected
    i1 = json.loads((ROOT/'docs/testing/scheduling-first-increment-1/manifest.json').read_text())
    assert len(i1['artifact_sha256']) == 28 and all(sha(ROOT/n) == h for n, h in i1['artifact_sha256'].items())
    entry = json.loads((I2/'entry.json').read_text())
    assert set(git('diff', '--name-only').splitlines()) == set(entry['tracked_modifications'])
    expected_untracked = set(entry['untracked_files']) | set(manifest['exact_new_file_inventory'])
    actual_untracked = set(git('ls-files', '--others', '--exclude-standard').splitlines())
    own = {p.relative_to(ROOT).as_posix() for p in BASE.rglob('*') if p.is_file()}
    own.add('docs/scheduling-first-increment-3.md')
    assert actual_untracked == expected_untracked | own, 'Unexpected untracked membership'

    tool = DIAG/'attest_backend_cache.py'
    cache_baseline = ROOT/'docs/testing/dashboard-u5pf/preservation-baseline.json'
    assert sha(tool) == PINNED_TOOL and sha(cache_baseline) == PINNED_CACHE_BASELINE
    tree = ast.parse(tool.read_text())
    expected = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'EXPECTED' for t in node.targets))
    pinned_rows = json.loads(cache_baseline.read_text())
    assert len(expected) == 5 and all(pinned_rows['backend/.pytest_cache/'+n] == h for n, h in expected.items())
    attestation = json.loads((DIAG/'operator-attestation.json').read_text(encoding='utf-8-sig'))
    rows = attestation['files']
    assert len(rows) == 5 and len({r['path'] for r in rows}) == 5 and {r['path'] for r in rows} == set(expected)
    assert all(r['actual_sha256'] == r['baseline_sha256'] == expected[r['path']] and r['matches'] is True for r in rows)
    assert attestation['status'] == 'SCOPED_CACHE_CONTENT_MATCH' and attestation['files_read'] == 5
    assert attestation['tool_sha256'] == PINNED_TOOL and attestation['baseline_expected_sha256'] == PINNED_CACHE_BASELINE
    assert attestation['exact_membership_verified'] is True and attestation['two_snapshots_identical'] is True
    assert attestation['writes_performed'] is False and attestation['full_preservation_audit'] is False
    assert attestation['acceptance_preflight_qualified'] is False
    a, b = (datetime.fromisoformat(attestation[k]) for k in ['started_at', 'ended_at'])
    assert a.tzinfo is not None and b.tzinfo is not None and a <= b

    # A fresh direct enumeration remains necessary; do not run the attestation
    # externally or authenticate an account from its self-reported JSON.
    try:
        with os.scandir(CACHE) as iterator:
            list(iterator)
        enumeration = dict(status='READABLE', current_file_hashes_verified=False)
    except OSError as exc:
        enumeration = dict(status='ACCESS_DENIED' if isinstance(exc, PermissionError) else 'READ_FAILED',
                           exception=type(exc).__name__, errno=exc.errno, winerror=getattr(exc, 'winerror', None))
    acl = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command',
        "Get-Acl -LiteralPath '"+str(CACHE)+"' -ErrorAction Stop | Out-Null"], capture_output=True)
    identity = subprocess.check_output(['whoami']).decode().strip().split('\\')[-1]

    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong),
                    *[(n, ctypes.c_ulonglong) for n in ['total', 'available', 'tc', 'ac', 'tv', 'av', 'ex']]]
    memory = Memory()
    memory.length = ctypes.sizeof(memory)
    queried = bool(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)))
    free = shutil.disk_usage(ROOT).free
    result = dict(schema='scheduling-first-increment-3-readonly-preflight-v1', started_at=started, ended_at=clock(),
        status='NO_GO_PRESERVATION_AND_RAM_UNQUALIFIED', head=EXPECTED_HEAD, branch=git('branch', '--show-current'),
        exact_check_executed='python -B docs/testing/scheduling-first-increment-3/preflight.py',
        preservation=dict(readable_baseline_matches=5703, academic_files_match=23, original_tracked_modifications_unchanged=11,
            entry_untracked_unchanged=1001, increment2_paths_unchanged=27, increment2_artifact_hashes_match=26,
            increment2_raw_blobs_match=len(manifest['proposed_raw_blob_oids']), increment1_artifact_hashes_match=28,
            protected_JSON_original_GA_migrations_Saved_Best_checkpoints_schedules='ALL_READABLE_BASELINED_BYTES_MATCH',
            git_index_HEAD_config_unchanged=True, current_execution_account_class=identity,
            cache_directory='backend/.pytest_cache', cache_enumeration=enumeration,
            cache_ACL_read_exit_code=acl.returncode, cache_ACL_readable=acl.returncode == 0,
            direct_current_cache_hashes_verified=False, independently_authenticated_cache_preservation=False,
            full_preservation_qualification=False, scoped_native_permission_under_existing_controls=False),
        operator_attestation=dict(classification='OPERATOR_SUPPLIED_UNAUTHENTICATED_EVIDENCE',
            historical_file_sha256=sha(DIAG/'operator-attestation.json'), pinned_tool_sha256=PINNED_TOOL,
            pinned_baseline_sha256=PINNED_CACHE_BASELINE, five_reported_hashes_match=True,
            reported_exact_membership_and_two_snapshot_flags=True, code_review_readonly=True,
            started_at=attestation['started_at'], ended_at=attestation['ended_at'], fresh_at_this_boundary=False,
            origin_authentication='NOT_ESTABLISHED', accepted_as_current_cache_preservation=False),
        resources=dict(measured_at=clock(), memory_query_succeeded=queried,
            available_bytes=memory.available if queried else None, total_bytes=memory.total if queried else None,
            required_available_bytes=3*2**30, RAM_gate_passed=queried and memory.available >= 3*2**30,
            free_disk_bytes=free, disk_screening='MORE_THAN_10_GIB_AVAILABLE' if free >= 10*2**30 else 'REVIEW_REQUIRED',
            test_database='NOT_CREATED_OR_CONNECTED; PHASE_A_FAILED', institutional_database_connections=0,
            source_recipe='Reviewed existing owned temp snapshot, empty import tables, private fictional SQLite; not executed',
            general_worker_max_wall_seconds=600, existing_operator_wall_seconds=60,
            worker_configuration='STATIC_SOURCE_REVIEW_ONLY; NO_RUNTIME_QUALIFICATION',
            worker_limits_changed=False, processes_launched_or_terminated_for_acceptance=0),
        acceptance=dict(native='NOT_RUN_PRECONDITION_FAILED', Edge='NOT_RUN_PRECONDITION_FAILED',
            service_restart='NOT_RUN', original_GA_parity='NOT_RERUN; FIVE_PREVIOUSLY_RECORDED_PASSES_REVIEWED',
            fresh_pytest_frontend_type_build_lint_tests=0, prior_results='INCREMENT_2_42_PYTHON_32_FRONTEND_HISTORICAL_NOT_FRESH'),
        no_ACL_ownership_cache_changes=True, no_original_source_or_data_changes=True,
        no_PostgreSQL_operations=True, staged=False, committed=False, pushed=False, deployed=False,
        production_admission='BLOCKED', institutional_saved_best='BLOCKED', continuous_optimization='DISABLED',
        active_institutional_restore='BLOCKED', seven_day='NO_GO')
    # This tool is a preflight reporter, never an execution launcher even if RAM
    # later improves. Direct full cache hashing/authentication must be qualified.
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(status=result['status'], available_GiB=memory.available/2**30,
        baseline_matches=5703, native='NOT_RUN', Edge='NOT_RUN', evidence=destination.relative_to(ROOT).as_posix())))


if __name__ == '__main__':
    main()
