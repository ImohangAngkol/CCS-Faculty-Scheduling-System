"""Read-only cache comparison; stdout only, no repair or acceptance promotion.

Run from the repository owner's normal non-elevated terminal. A JSON result
is evidence for review, not authentication of its origin or a full audit.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[4]
CACHE = ROOT / 'backend/.pytest_cache'
BASELINE = ROOT / 'docs/testing/dashboard-u5pf/preservation-baseline.json'
BASELINE_SHA256 = 'a301e0821f6d025e0ae39e8231051d6233665c4f5f4ff59255cb05c6a50ff04b'
EXPECTED = {
    '.gitignore': '3ed731b65d06150c138e2dadb0be0697550888a6b47eb8c45ecc9adba8b8e9bd',
    'CACHEDIR.TAG': '37dc88ef9a0abeddbe81053a6dd8fdfb13afb613045ea1eb4a5c815a74a3bde4',
    'README.md': '73fd6fccdd802c419a6b2d983d6c3173b7da97558ac4b589edec2dfe443db9ad',
    'v/cache/lastfailed': 'de1dd2fbd290e5d83ab9de5060504c7a8358eaba172be670c9fb9cf36e9123f2',
    'v/cache/nodeids': '0d42bda6f2b07775c4a1d55491a6bd0bdf6ed706d9d59cfedc1e2ec87d6c9ad7',
}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def no_link(path):
    info = path.lstat()
    require(not path.is_symlink() and not path.is_junction()
            and not (getattr(info, 'st_file_attributes', 0)
                     & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024)),
            'REPARSE_OR_LINK_REJECTED')


def snapshot():
    no_link(ROOT / 'backend')
    no_link(CACHE)
    found, directories = {}, []
    def fail(exc):
        raise exc
    for parent, dirs, files in os.walk(CACHE, onerror=fail, followlinks=False):
        folder = Path(parent)
        directories.append(folder.relative_to(CACHE).as_posix())
        for name in dirs:
            no_link(folder / name)
        for name in files:
            path = folder / name
            no_link(path)
            relative = path.relative_to(CACHE).as_posix()
            require(relative in EXPECTED, 'UNEXPECTED_CACHE_FILE')
            before = path.stat()
            digest = sha(path)
            after = path.stat()
            identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
            require(identity(before) == identity(after), 'FILE_CHANGED_DURING_READ')
            found[relative] = dict(sha256=digest, bytes=after.st_size,
                                   identity=identity(after))
    require(set(found) == set(EXPECTED), 'CACHE_MEMBERSHIP_MISMATCH')
    require(sorted(directories) == ['.', 'v', 'v/cache'], 'CACHE_DIRECTORY_MISMATCH')
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--read-only', required=True, action='store_true')
    parser.parse_args()
    started = datetime.now(ZoneInfo('Asia/Manila')).isoformat()
    tool_hash = sha(Path(__file__))
    result = dict(schema='u5pf-cache-readonly-attestation-v1',
                  started_at=started, path='backend/.pytest_cache',
                  tool_sha256=tool_hash, baseline_expected_sha256=BASELINE_SHA256,
                  writes_performed=False, full_preservation_audit=False,
                  acceptance_preflight_qualified=False,
                  origin_authentication='REQUIRES_SEPARATE_OPERATOR_VERIFICATION')
    try:
        require(sha(BASELINE) == BASELINE_SHA256, 'BASELINE_IDENTITY_MISMATCH')
        baseline = json.loads(BASELINE.read_text(encoding='utf-8'))
        require(all(baseline.get('backend/.pytest_cache/' + n) == h
                    for n, h in EXPECTED.items()), 'BASELINE_EXPECTATION_MISMATCH')
        first, second = snapshot(), snapshot()
        require(first == second, 'CACHE_CHANGED_BETWEEN_SNAPSHOTS')
        result['files'] = [dict(path=n, actual_sha256=first[n]['sha256'],
                                baseline_sha256=EXPECTED[n],
                                matches=first[n]['sha256'] == EXPECTED[n])
                           for n in sorted(EXPECTED)]
        require(all(row['matches'] for row in result['files']), 'CACHE_HASH_MISMATCH')
        require(sha(BASELINE) == BASELINE_SHA256 and sha(Path(__file__)) == tool_hash,
                'EVIDENCE_INPUT_CHANGED')
        result.update(status='SCOPED_CACHE_CONTENT_MATCH', files_read=5,
                      exact_membership_verified=True, two_snapshots_identical=True)
        code = 0
    except (OSError, ValueError) as exc:
        result.update(status='STOP_READ_ONLY_ATTESTATION_FAILED',
                      exception=type(exc).__name__, errno=getattr(exc, 'errno', None),
                      winerror=getattr(exc, 'winerror', None))
        if isinstance(exc, ValueError):
            result['reason'] = str(exc)
        code = 1
    result['ended_at'] = datetime.now(ZoneInfo('Asia/Manila')).isoformat()
    print(json.dumps(result, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
