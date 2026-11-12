"""Read-only, fail-closed preservation review after the R2 cache gate stop.

No application imports, database access, cache repair or test execution.
Use --record once to retain a separate review; never rewrite old evidence.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parent
F = BASE.parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def git(*args):
    return subprocess.check_output(
        ['git', '--no-optional-locks', *args], cwd=ROOT,
        env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'), stderr=subprocess.PIPE,
    )


def inspect():
    entry = read(F / 'entry.json')
    baseline = read(F / 'recovery-r1/preservation-baseline.json')
    previous = read(F / 'recovery-r2/manifest.json')
    matches, inaccessible, different = [], [], []
    for name, expected in baseline.items():
        try:
            actual = sha(ROOT / name)
        except OSError as exc:
            inaccessible.append(dict(path=name, error=type(exc).__name__,
                                     winerror=getattr(exc, 'winerror', None)))
            continue
        if actual == expected:
            matches.append(name)
        else:
            different.append(name)
    artifacts = []
    for name, expected in previous['artifact_sha256'].items():
        assert sha(ROOT / name) == expected, 'PRIOR_EVIDENCE_MISMATCH: ' + name
        artifacts.append(name)
    tracked = sorted(git('diff', '--name-only').decode().splitlines())
    assert tracked == sorted(entry['tracked_modifications']), 'TRACKED_PATH_MISMATCH'
    assert not git('diff', '--cached', '--name-only').strip(), 'INDEX_NOT_EMPTY'
    assert git('rev-parse', 'HEAD').decode().strip() == entry['head'], 'HEAD_CHANGED'
    assert git('branch', '--show-current').strip() == b'main', 'BRANCH_CHANGED'
    untracked = set(git('ls-files', '--others', '--exclude-standard', '-z').decode().split('\0')) - {''}
    own = {p.relative_to(ROOT).as_posix() for p in BASE.iterdir() if p.is_file()}
    assert untracked == set(entry['untracked_files']) | set(previous['exact_changed_and_new_file_inventory']) | own, 'UNTRACKED_PATH_MISMATCH'
    enumeration_error = None
    enumeration_count = 0
    ignored_directories = set()
    ignored = set(git('ls-files', '--others', '--ignored', '--exclude-standard', '-z').decode().split('\0')) - {''}
    def fail(exc):
        raise exc
    try:
        for parent, dirs, files in os.walk(ROOT, onerror=fail, followlinks=False):
            dirs[:] = [d for d in dirs if (Path(parent) / d).relative_to(ROOT).as_posix() not in entry['excluded_roots']]
            for d in dirs:
                p = Path(parent) / d
                assert not p.is_symlink() and not p.is_junction(), 'UNREVIEWED_LINK'
            for name in files:
                relative = (Path(parent) / name).relative_to(ROOT).as_posix()
                enumeration_count += 1
                if relative in ignored:
                    ignored_directories.add(str(Path(relative).parent).replace('\\', '/'))
    except OSError as exc:
        enumeration_error = dict(path=Path(exc.filename).relative_to(ROOT).as_posix(),
                                 error=type(exc).__name__, winerror=getattr(exc, 'winerror', None))
    academic = [name for name in entry['academic_paths'] if name in matches]
    historical = [name for name, expected in entry['historical_eight'].items()
                  if name in matches and baseline[name] == expected]
    return dict(
        recorded_at=datetime.now(ZoneInfo('Asia/Manila')).isoformat(),
        head=entry['head'], branch='main', index_empty=True,
        status='STOP_CACHE_ACCESS_DENIED' if enumeration_error or inaccessible else 'REVIEW_REQUIRED',
        known_baseline_paths=len(baseline), known_baseline_matches=len(matches),
        inaccessible_baseline_paths=inaccessible, changed_baseline_paths=different,
        previous_artifact_hashes_verified=len(artifacts),
        previous_F_R1_R2_paths=len(previous['exact_changed_and_new_file_inventory']),
        academic_files_verified=len(academic), historical_eight_verified=len(historical),
        protected_JSON_unchanged=all(n in matches for n in ['backend/data/faculty_preferences.json', 'backend/data/ga_settings.json']),
        original_tracked_paths=tracked, original_unrelated_untracked_count=len(entry['untracked_files']),
        strict_enumeration_error=enumeration_error, partial_enumeration_count=enumeration_count,
        ignored_directories_observed_before_stop=sorted(ignored_directories),
        dependency_build_exclusions=entry['excluded_roots'],
        complete_preservation_baseline_established=False,
        inaccessible_files_classified_as_preserved=False,
        tests_executed=0, native_workers_launched=0, Edge_scenarios_executed=0,
        no_permission_changes=True, no_elevation=True, no_PostgreSQL_operations=True,
        production_admission='BLOCKED', continuous_optimization='DISABLED',
        active_restore='BLOCKED', seven_day_readiness='NO_GO', checkpoint_ready=False,
    )


if __name__ == '__main__':
    result = inspect()
    if '--record' in sys.argv:
        with (BASE / 'review.json').open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
    print(json.dumps({k: result[k] for k in [
        'status', 'known_baseline_paths', 'known_baseline_matches',
        'inaccessible_baseline_paths', 'changed_baseline_paths',
        'previous_artifact_hashes_verified', 'academic_files_verified',
        'historical_eight_verified', 'strict_enumeration_error', 'checkpoint_ready',
    ]}))
