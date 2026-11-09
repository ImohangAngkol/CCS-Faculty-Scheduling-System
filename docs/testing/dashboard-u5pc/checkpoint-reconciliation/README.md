# U5P-C checkpoint reconciliation

The original 99-file candidate staged the working AppRoutes bytes verbatim.
HEAD uses LF, while that working copy has 240 CRLF endings. Git therefore saw
the inherited trailing space at HEAD line 126 as an added line at staged line
128. The required staged whitespace check stopped with exit 2. No commit or
push occurred in that attempt.

The replacement is constructed from the exact HEAD blob, retaining its LF
convention and inherited trailing space, with only the import at line 53 and
route at line 75 added. The replacement equals the original staged content
after removing only 240 CR bytes immediately before LF. No character within
any source line, route, authorization check or optimization code changes.

- Original HEAD blob: `433839200edc0225cd39121aeca6ea5921098307`
- Original staged blob: `51747f3f656494aa57f1b0c01aad1db883ae104d`
- Replacement staged blob: `4de8abbdcb5125f22a36ad9cc7278b04cddbaa15`
- Working-tree SHA-256 before/after:
  `546a20c8310dbf613ed64cd7c9f64916975b8022e905990c8f00d81db03c0ea9`

`repair-verification.json` confirms the other 98 staged blobs stayed identical
during the index-only repair. The subsequent manifest/plan refresh changes only
those two metadata blobs among the other 98; all remaining 96 are unchanged.
The original metadata bytes are preserved in `original-manifest.json` and
`original-staging-plan.json`. The original implementation report, tests, failed
attempt records and other evidence remain untouched.

`source-byte-snapshots.json` preserves complete HEAD, original staged and
replacement bytes as lossless hex with independent hashes. It also retains the
original reviewed context patch, whose hash was recorded by repair verification.
`AppRoutes.index-only.patch` is an equivalent zero-context HEAD-to-replacement
intent patch: no whitespace rule is disabled, and no inherited blank context is
introduced as trailing whitespace in a newly added evidence file. Only our new,
unsealed duplicate source snapshots were converted to this lossless JSON form;
no historical source/evidence was deleted.

The initial preparation guard also caught an incorrect draft import line number
(54 instead of 53), before any index write. That failed draft and diagnostic
remain separately preserved. The corrected metadata matches the actual bytes.

The exact staged frontend was exported to a fresh owned temporary snapshot;
every indexed frontend file was verified before a documented test-only Vite
cache-location adjustment. Unrelated working-tree UI changes were not overlaid.
Fresh results: 361 contracts, TypeScript, production build, focused ESLint and
12 real Edge/React scenarios with intercepted fictional HTTP passed. Those
browser checks are not fresh live FastAPI/PostgreSQL acceptance. The existing
265 Python passes, nine live FastAPI/SQLite scenarios, 455.0 parity and checkpoint
continuation evidence were reviewed and preserved, not rerun for this EOL-only
frontend correction. The unchanged U5P-B no-research-routes assertion failure
remains a recorded limitation; no fully green repository-wide claim is made.

The current parent manifest and staging plan explicitly supersede the archived
99-path checkpoint. Their artifact hashes describe intended committed bytes;
the AppRoutes working-tree hash exception is recorded separately. No automatic
legacy fingerprint, Saved Best, checkpoint or production authority change occurs.
The original pre-staging auditor remains historical and pinned to its original
HEAD/index/inventory assumptions; use the reconciliation verifier for this
authorized checkpoint state.

Reproduce staged-source frontend checks before committing:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pc/checkpoint-reconciliation/test_staged_frontend.py
```

This creates new timestamped evidence; a sealed inventory then requires a new
reviewed addendum. Do not automatically rewrite sealed historical records.

Replay the final checkpoint audit:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pc/checkpoint-reconciliation/verify_checkpoint.py
```

After the authorized commit, use `--committed`. No command here accesses a
database or starts a research worker. Production admission and restoration
remain BLOCKED, Continuous Optimization DISABLED and seven-day readiness NO-GO.
