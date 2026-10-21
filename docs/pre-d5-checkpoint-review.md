# Pre-D5 GitHub checkpoint review

Review date: 2026-10-21, Asia/Manila. Status: **PROPOSED ONLY ? no staging, commit or push**. D5 has not started. This review creates this documentation file only; it changes no application code, existing evidence or protected data.

## Remote comparison and existing checkpoint

A read-only git ls-remote lookup verified GitHub refs/heads/main at **f3a07e5461430caab7a3998a2fd9d16b0aa1287d**. Local HEAD, main and origin/main match it; local ahead/behind is **0 / 0**. No fetch or remote-tracking update was needed. The initial sandboxed lookup could not reach GitHub; the authorized read-only lookup outside that restriction succeeded.

That existing commit, ?feat: add Phase 4C academic foundation and dashboard D1-D2?, already contains 96 changed/added paths for Phase 4C.1/4C.2 and D1?D2. Those sources and reports are already on GitHub and need no duplicate commit. Key existing files include:

- backend/academic_models.py; backend/migrations/versions/4c_0001_academic_foundation.py; backend/tests/academic/.
- docs/phase-4c1-academic-data-contract.md; docs/architecture/phase-4c1-relational-schema.md; docs/phase-4c-confirmed-scheduling-workflows.md; docs/phase-4c2-academic-foundation.md.
- docs/dashboard-d1-implementation.md; docs/dashboard-d2-implementation.md; their tests, screenshots and manifests.

The current incremental checkpoint is D3?D4. At inspection there were five modified tracked files and 79 untracked files. Four tracked modifications and all 79 untracked files are proposed, plus this new review document: **84 files total: four modified and 80 added**. The excluded tracked preference modification remains intact. Existing pending files total 2,600,371 bytes before adding this document; this is a small evidence-inclusive checkpoint.

## Proposed commit groups and exact allowlist

Use explicit paths from these lists after approval. Do not use git add ., git add -A, git commit -a or force-add ignored files. Recheck the protected exclusion and staged diff before any commit. A later approval may authorize a single combined commit instead; this review performs neither option.

D3 and D4 share six source/script files. Their final contents are already validated together. Splitting those files into historical D3/D4 implementations would require reconstructing intermediate content, which is outside this code-preserving checkpoint. The two groups below preserve the final files as reviewed.

### Group 1 ? application, focused tests and fictional template (21 files)

Proposed message: **feat(dashboard): add external schedule intake and reconciled review calendar**

This contains D3 intake/CSV/XLSX preview and D4 weekly resource review, administrator guards, typed frontend transport, navigation, tests and fictional CSV template. There are no persistence, confirmation, GA-input or Chair-approval changes.

```text
backend/main.py
backend/routers/external_schedules.py
backend/schemas/external_schedule.py
backend/services/external_schedule_review_service.py
backend/services/external_schedule_service.py
backend/tests/dashboard/test_external_preview.py
backend/tests/dashboard/test_external_review.py
frontend/package.json
frontend/public/templates/external-gec-fictional.csv
frontend/src/api/externalSchedules.ts
frontend/src/components/schedule/ExternalScheduleReview.tsx
frontend/src/components/schedule/externalReviewModel.ts
frontend/src/layouts/AdminLayout.tsx
frontend/src/pages/admin/ExternalSchedules.tsx
frontend/src/routes/AppRoutes.tsx
frontend/tests/externalReview.browser.test.mjs
frontend/tests/externalReview.fixtures.mjs
frontend/tests/externalReview.test.mjs
frontend/tests/externalSchedules.browser.test.mjs
frontend/tests/externalSchedules.fixtures.mjs
frontend/tests/externalSchedules.test.mjs
```

### Group 2 ? reports, evidence and reproducible check runners (63 files)

Proposed message: **docs(testing): archive D3-D4 validation and pre-D5 checkpoint review**

Includes final and earlier failed attempts, superseded screenshots, preservation baselines, manifests and evidence runners. Failed runs remain labeled as failures; duplicate/superseded captures are retained because the manifests reference them. The large D3 failed-run log is 485,147 bytes: synthetic XML stress-input repetition, not an uploaded institutional file or credential dump.

```text
docs/dashboard-d3-implementation.md
docs/dashboard-d4-implementation.md
docs/pre-d5-checkpoint-review.md
docs/screenshots/dashboard-d3/20261021T180849851957+0800-browser/D3-B02-manual-intake.png
docs/screenshots/dashboard-d3/20261021T180849851957+0800-browser/D3-B03-review-findings.png
docs/screenshots/dashboard-d3/20261021T180849851957+0800-browser/D3-B06-csv-preview.png
docs/screenshots/dashboard-d3/20261021T180849851957+0800-browser/D3-B12-mobile-intake.png
docs/screenshots/dashboard-d3/20261021T180849851957+0800-browser/browser-results.json
docs/screenshots/dashboard-d3/20261021T181109118902+0800-browser/D3-B02-manual-intake.png
docs/screenshots/dashboard-d3/20261021T181109118902+0800-browser/D3-B03-review-findings.png
docs/screenshots/dashboard-d3/20261021T181109118902+0800-browser/D3-B06-csv-preview.png
docs/screenshots/dashboard-d3/20261021T181109118902+0800-browser/D3-B12-mobile-intake.png
docs/screenshots/dashboard-d3/20261021T181109118902+0800-browser/browser-results.json
docs/screenshots/dashboard-d4/20261021T192854352300+0800-browser/D4-B05-explicit-resource-reconciliation.png
docs/screenshots/dashboard-d4/20261021T192854352300+0800-browser/D4-B08-invalid-source-details.png
docs/screenshots/dashboard-d4/20261021T192854352300+0800-browser/D4-B12-mobile-review.png
docs/screenshots/dashboard-d4/20261021T193051605221+0800-browser/D4-B02-weekly-overlap-calendar.png
docs/screenshots/dashboard-d4/20261021T193051605221+0800-browser/D4-B05-explicit-resource-reconciliation.png
docs/screenshots/dashboard-d4/20261021T193051605221+0800-browser/D4-B08-invalid-source-details.png
docs/screenshots/dashboard-d4/20261021T193051605221+0800-browser/D4-B12-mobile-review.png
docs/screenshots/dashboard-d4/20261021T193051605221+0800-browser/browser-results.json
docs/screenshots/dashboard-d4/20261021T193418759578+0800-browser/D4-B02-weekly-overlap-calendar.png
docs/screenshots/dashboard-d4/20261021T193418759578+0800-browser/D4-B05-explicit-resource-reconciliation.png
docs/screenshots/dashboard-d4/20261021T193418759578+0800-browser/D4-B08-invalid-source-details.png
docs/screenshots/dashboard-d4/20261021T193418759578+0800-browser/D4-B12-mobile-review.png
docs/screenshots/dashboard-d4/20261021T193418759578+0800-browser/browser-results.json
docs/testing/dashboard-d3/20261021T180432458430+0800-backend/command.json
docs/testing/dashboard-d3/20261021T180444482420+0800-build/command.json
docs/testing/dashboard-d3/20261021T180649240181+0800-contracts/command.json
docs/testing/dashboard-d3/20261021T180651152173+0800-lint/command.json
docs/testing/dashboard-d3/20261021T180849851957+0800-browser/command.json
docs/testing/dashboard-d3/20261021T180930036624+0800-backend-regressions/command.json
docs/testing/dashboard-d3/20261021T180942367522+0800-d1-browser/command.json
docs/testing/dashboard-d3/20261021T180954769004+0800-d2-browser/command.json
docs/testing/dashboard-d3/20261021T181006615455+0800-ga-browser/command.json
docs/testing/dashboard-d3/20261021T181109118902+0800-browser/command.json
docs/testing/dashboard-d3/20261021T181124497502+0800-backend/command.json
docs/testing/dashboard-d3/20261021T181359114595+0800-backend/command.json
docs/testing/dashboard-d3/20261021T181548123118+0800-backend/command.json
docs/testing/dashboard-d3/manifest.json
docs/testing/dashboard-d3/preservation-baseline.json
docs/testing/dashboard-d3/run_checks.py
docs/testing/dashboard-d4/20261021T192123664940+0800-build/command.json
docs/testing/dashboard-d4/20261021T192124736771+0800-backend/command.json
docs/testing/dashboard-d4/20261021T192126222976+0800-lint/command.json
docs/testing/dashboard-d4/20261021T192416412281+0800-contracts/command.json
docs/testing/dashboard-d4/20261021T192850190990+0800-contracts/command.json
docs/testing/dashboard-d4/20261021T192854352300+0800-browser/command.json
docs/testing/dashboard-d4/20261021T192949768046+0800-backend-regressions/command.json
docs/testing/dashboard-d4/20261021T192951721172+0800-d2-browser/command.json
docs/testing/dashboard-d4/20261021T192951865651+0800-d3-browser/command.json
docs/testing/dashboard-d4/20261021T192952905704+0800-d1-browser/command.json
docs/testing/dashboard-d4/20261021T192955321225+0800-ga-browser/command.json
docs/testing/dashboard-d4/20261021T193048577215+0800-backend/command.json
docs/testing/dashboard-d4/20261021T193051605221+0800-browser/command.json
docs/testing/dashboard-d4/20261021T193232225140+0800-build/command.json
docs/testing/dashboard-d4/20261021T193233342148+0800-lint/command.json
docs/testing/dashboard-d4/20261021T193415632019+0800-build/command.json
docs/testing/dashboard-d4/20261021T193416872014+0800-lint/command.json
docs/testing/dashboard-d4/20261021T193418759578+0800-browser/command.json
docs/testing/dashboard-d4/manifest.json
docs/testing/dashboard-d4/preservation-baseline.json
docs/testing/dashboard-d4/run_checks.py
```

## Sensitive content and generated-artifact review

Reviewed every proposed existing text file, parsed all proposed JSON and decoded command stdout/stderr, including the large failed-run log. Checks covered private-key markers, common credential/token patterns, credential-bearing/database connection URIs, password/secret assignments, environment/credential filenames and email addresses. **No secrets, PostgreSQL connection URLs, real account credentials, environment files, database copies, uploaded institutional records or raw authenticated headers/responses were detected in the proposed set.** The only email matches are reserved example.invalid synthetic test users. The fictional CSV template contains fictional placeholders only.

Compared proposed text against the seven names in the current local faculty identity registry without copying names/IDs into this review: **no matches**. This targeted comparison is not an exhaustive institutional directory scan or formal secret-scanner certification. Source review confirms test metadata is explicitly synthetic. HMAC process keys are generated at runtime; a public synthetic fixture receipt is not a real credential or persisted signing key.

All **19 PNGs** were privacy reviewed: **12 distinct images** were visually inspected, and the seven byte-identical copies were verified by SHA-256. They show only fictional fixtures; no passwords, account/session headers, real faculty records, backend signing receipts or unrelated private windows are visible. Synthetic source hashes are provenance, not credentials. Earlier D4 images lacking individual archived timestamps remain explicitly limited by the manifest; timestamps have not been invented.

Some diagnostic JSON contains this machine's generic User workspace path and owned temporary test-directory names. These strings are not credentials, and the temporary directories/files themselves are not proposed. Browser URLs are public loopback fixture URLs, not database connection URLs. No evidence was rewritten or sanitized during this review.

The generated files proposed here are intentionally archived test evidence, not runtime application outputs. The build output, dependencies, virtual environment, caches, database files, private CSV/XLSX source datasets, actual saved schedules and checkpoints remain outside the allowlist. No ignored files will be force-added.

## Exclusions and preservation

**The only tracked or nonignored-untracked item outside the planned checkpoint is backend/data/faculty_preferences.json.** It is a pre-existing protected modification, not a D3/D4 deliverable; never stage it, even if it is the last dirty file. Do not discard, restore, overwrite or attempt to repair it.

Its raw-byte SHA-256 remains **72a5f4f239b5cf99cfb6d7159d443375f8496b69c6b3d1d67ad42e449fd2d8a9**. The Git index remains **b7187e43380ab38040baf1cf51e3b70f4c1ee8ac3cf51b46358946c6d653463b** and is empty of staged changes.

Ignored local-only material also remains excluded: environment/credential files, backend/data private CSV/XLSX files, saved_chromosomes runtime data, run_checkpoints, local SQLite databases, frontend/dist, node_modules, .venv and caches. These ignored files are not counted as outstanding checkpoint changes and have not been read for credentials, deleted or reset. No actual schedule, checkpoint or dataset is proposed.

The pre-D3 507-file baseline has exactly four expected modified paths: backend/main.py, frontend/package.json, frontend/src/layouts/AdminLayout.tsx and frontend/src/routes/AppRoutes.tsx. Its other **503 files** remain byte-identical, including protected preferences, GA operators/fitness/RNG/checkpoints, existing inputs/schedules/history, account/identity sources, Phase 4C and historical evidence. No database contents were queried to make that comparison.

## Git, whitespace and evidence-integrity checks

- git diff origin/main reviewed for all four proposed tracked modifications: protected router registration, navigation/route and test scripts only. The protected preference content was excluded from displayed diffs.
- git diff --check origin/main and git diff --cached --check: **PASS**, with no introduced whitespace errors; staged diff is empty.
- All untracked text files were checked with git diff --no-index --check against /dev/null: **no whitespace diagnostics**. This command ordinarily returns one because the files differ from empty; that is not a whitespace failure.
- A whole-file comparison of the tracked AppRoutes.tsx also identified existing trailing whitespace on the PreferencesReview line. The same line exists in origin/main; it is outside the added diff and was deliberately left unchanged.
- Git core.autocrlf is true and reports LF-to-CRLF checkout warnings for some files. No line-ending configuration or application formatting was changed. Historical manifests hash raw working-tree bytes; checkouts with different line endings can legitimately differ. Verify evidence hashes on the reviewed raw files and distinguish Git normalization from altered evidence; do not silently rewrite old manifests.
- D4 manifest: **47/47 current artifact hashes match**, no missing artifacts.
- D3 manifest: **40 artifacts present**; six historical source/script hashes are superseded by the documented D4 extensions (router, schema, intake service, package scripts, frontend API and page). Its other **34 hashes match**. This is expected history, not six corrupt evidence files. Do not claim the D3 historical source snapshot equals the final D4 source.
- All proposed JSON parses successfully. Screenshots and evidence remain unchanged. No symlinks, private-key files, archives or runtime database/checkpoint files appear in the exact allowlist.

## Validation status and gaps

This checkpoint review performed static/Git/privacy/hash checks only. It did not rerun application tests, generate schedules, connect to PostgreSQL or execute migrations. The existing dated evidence supports:

| Scope | Most recent recorded result |
|---|---|
| Phase 4C.2, 2026-10-20 revalidation | 85 passed, 17 PostgreSQL cases skipped, two existing Alembic deprecation warnings |
| D2?D4 focused backend | 122 passed (32 D4, 61 D3, 29 D2); two warnings |
| Existing backend authentication/GA control | 46 passed; four warnings |
| Frontend contracts | 110 passed |
| Rendered browser scenarios | D4: 15; D1: 16; D2: 13; D3: 15; GA monitoring: 51; each harness also reports a parent wrapper |
| Production build / focused ESLint | Passed; existing large-bundle warning remains |

D3/D4 browser tests use actual Edge/React with **synthetic HTTP responses**. Backend tests separately exercise real FastAPI session/admin/Origin/CSRF dependencies with isolated synthetic SQLite data. This is not browser-to-live-PostgreSQL acceptance or evidence of GA activation. Full-project lint, the full backend/GA suite and performance qualification have not been newly run for this checkpoint.

**The 17 Phase 4C PostgreSQL tests remain UNVERIFIED and paused.** Offline SQLite, fake catalogs and rendered SQL do not verify the following online behavior:

- Revision 4a_0001 ? 4c_0001 and exact seven-table inventory with authentication tables preserved.
- PostgreSQL immutable identity, next-version, timezone, archive/delete/truncate and locked-parent guards.
- Same-scope/same-term FKs and offering-key integrity.
- Term/year date containment and rejection of parent-year shrink.
- Populated downgrade refusal, empty downgrade/upgrade roundtrip and transactional DDL rollback.
- Advisory writer serialization, concurrent calendar-change rejection and supported isolation enforcement.
- PostgreSQL read-only repository behavior and no implicit default term.

Future execution requires a separately approved fresh exact-gated Phase 4C target and only PHASE4C_TEST_DATABASE_URL; no DATABASE_URL fallback and no Phase 4B database reuse. The user-reported earlier absence check does not authorize provisioning or testing now. No PostgreSQL/database action is needed to commit source with these limitations disclosed.

## Review boundary and next authorized action

Review this exact 84-file proposal and the two messages before staging. After explicit approval, recheck remote HEAD and the working-tree allowlist, stage only approved paths, inspect the complete staged diff and verify the protected file is absent, then commit the approved groups and push without force. If the remote changes, stop and review divergence instead of rewriting history. If newly created files appear, review them before expanding this allowlist.

Expected result after committing these approved groups: only the existing protected preference modification remains among tracked/nonignored changes; ignored local datasets/runtime artifacts remain untouched. No D5 implementation has begun.
