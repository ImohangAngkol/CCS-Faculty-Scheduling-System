# Phase 4B.1: PostgreSQL acceptance and strict GA input validation

Baseline: `c770c841259b968132f8ce6b48ae5cb36df35171`. Date: 2026-10-16, Asia/Manila.

## Current acceptance assessment (documentation update 2026-10-18)

**POSTGRESQL ACCEPTANCE: 14 PASSED, USER EXECUTED; SIX BROWSER FUNCTIONAL SCENARIOS: PASS — USER CONFIRMED.** The [final written-only browser report](testing/phase-4b/manual-acceptance-results.md) records P4B-B01 through P4B-B06. **Screenshots: NOT CAPTURED for all six; automated browser execution: NOT ESTABLISHED; original manual timestamps: NOT RECORDED.** No original screenshots exist. This documentation task performed no browser execution, regression rerun or live database check.

B06 used the isolated `ready.unavailable` marker to inject HTTP 503; the user confirms error presentation, successful marker removal and recovery of the same faculty session with Compact / Very High preserved. It was not a physical PostgreSQL outage. The package is ready for written-only review with these limitations, not production qualification or complete screenshot evidence. Existing automated results, old failures/blocks and offline Stage A/recovery reports remain historical and separately attributed. The subsequent assessments describe their original stages, not the current manual completion status.

## Historical acceptance assessment before final manual confirmation

**POSTGRESQL ACCEPTANCE PASSED; BROWSER ACCEPTANCE OUTSTANDING.** The user-executed [2026-10-18 successful run](testing/phase-4b/20261018T100533+0800-postgresql-e2beb33f.json) reports 14 passed, zero failed/skipped, three warnings in 12.23s (runner 13.660s), exit 0. Codex reviewed this evidence; Codex did not execute the successful run. Earlier missing-variable skips and safety-gate setup errors remain historical evidence below. The existing application `DATABASE_URL` is never a fallback.

The strict API admission fix is implemented and tested. Executed checks, timestamps, failures and counts are in the [ledger](testing/phase-4b/README.md). **Stage A browser fixture preparation is now implemented and offline verified**; actual Stage B provisioning/migration/browser execution still requires approval. See the [Stage A report](testing/phase-4b/stage-a-fixture-preparation.md) and [execution plan](testing/phase-4b/browser-acceptance-plan.md). No provisioning or browser execution occurred in Stage A; genuine browser scenarios remain required for full acceptance.

## Objectives and scope

1. Qualify identities, authentication and authorization against the explicitly designated disposable PostgreSQL database.
2. Reject corrupt or invalid preference/settings storage before optimization admission.
3. Preserve valid-input GA results, RNG behavior, fitness calls and checkpoint compatibility.
4. Produce actual, attributable testing and thesis evidence.

No academic CRUD, preference migration, Phase 4C, scoring/weight/operator changes, checkpoint-format changes, notebook edits or Git mutations are included.

## Database safety and acceptance implementation

`backend/tests/phase4b_database_safety.py` accepts only `PHASE4B_TEST_DATABASE_URL`, PostgreSQL/psycopg2, database `ccs_ga_phase4b_test`, role `ccs_ga_phase4b_tester`, host `127.0.0.1`, port `5432`. Query-string overrides are rejected. URL/password values are not printed.

The first connection starts with `default_transaction_read_only=on`. Catalog queries verify the connected database, current role, server address/port, public schema, transaction mode and absence of superuser/createdb/createrole privileges. It inspects user relations and rejects any nonempty schema before migration. This deliberately does not infer permission from synthetic-looking account or table names. A previously used acceptance database needs explicit owner review; the harness does not reset or clean it automatically.

Only after that gate, the opt-in suite invokes the existing real Alembic upgrade to `4a_0001`. Its temporary `DATABASE_URL` assignment is scoped to that migration command and derives exclusively from the verified test URL. It does not use or change the running application's environment. No downgrade or database deletion is implemented.

The prepared 14 PostgreSQL cases cover actual migration/constraints, synthetic import, concurrent bootstrap, administrator/faculty login, faculty bindings and duplicates, rollback, valid-CSRF ownership, persistent sessions across fresh Python/ASGI backend processes, logout/expiration/revocation, simulated connection failure, real row-lock timeout and concurrent last-admin protection. A simulated outage is not a claim that a PostgreSQL service was stopped. Fresh-process authentication checks are not a network/browser acceptance test.

Only synthetic identities are imported into that test database. The fixture overrides storage and synthetic identity metadata, never the authentication principal or permission dependencies. Preferences/settings and all checkpoint/history paths use pytest temporary storage. Synthetic database records are retained for owner inspection; no automatic cleanup of accounts/tables is performed. PostgreSQL tests are one-shot against an empty designated database; order-dependent lifecycle scenarios run together without parallel test distribution.

**Historical result, 2026-10-16:** 14 skipped because the required variable was absent. That suite exit code of zero meant pytest completed its skips, not a PostgreSQL pass. **Latest result, 2026-10-18:** all 14 passed after the focused host-extraction correction. The successful artifact verifies the suite's asserted migration/constraints/session/locking scenarios; server version and individual warning messages were not recorded.

## Confirmed defect and correction: BUG-011

Before the fix, a malformed preference file submitted to a GA start route passed admission. A bounded regression with an execution spy returned HTTP 200 where HTTP 503 was required. No production GA was executed. The earlier read-only audit also reproduced the legacy loaders returning empty containers for malformed JSON.

New `backend/services/ga_input_validation_service.py` validates the actual preference/settings paths used by both existing engine readers. `backend/routers/genetic_algorithm.py` calls it before acquiring execution admission, registering a run or writing a durable marker. The history execution wrapper rechecks at worker entry, and the resume path checks before claiming a worker or changing paused state.

It rejects malformed JSON, invalid UTF-8/BOM input, duplicate members/records, non-finite numbers, wrong shapes/types, unknown faculty references, invalid stored-schema values, unsupported settings and invalid numeric bounds. Error codes distinguish `GA_INPUT_INVALID` and `GA_INPUT_UNAVAILABLE`; messages identify administrative repair without echoing input values, credentials or private paths.

Missing files retain the existing defaults; an empty preference list and an empty settings object are legitimate. JSON `null` is present corruption, not a missing file. Validation does not fill defaults in files or alter values handed to the scorer. The existing legacy stored-response contract is retained: missing fields and extra preference metadata are not rewritten. New preference edits continue to use the existing stronger eligibility/component-pattern validator. Admission does not redefine historical preference semantics or revalidate old checkpoints under a different scoring policy.

The scorer, all eight fitness components, weights, GA operators, chromosome classes, frozen-input helper and checkpoint format remain unchanged. The new boundary does not evaluate fitness or consume GA random values. The teaching target remains 24 minus administrative/research/extension releases (floored at zero), underload remains soft, and the 40-unit maximum, explicit eligibility, conflicts, external Palad/ICT3A locks, immutable fixed schedules and continuous three-hour labs remain hard rules.

## Regression and compatibility strategy

New tests exercise each start route, malformed/missing/empty/unreadable inputs, unchanged saved-artifact sentinels, no worker admission, worker-entry rechecks, unchanged paused state and valid-input seeded equivalence including fitness-call counts. Existing authentication/ownership, domain, monitoring, stop, pause/resume, checkpoint/history and Unicode regressions are recorded separately in the testing ledger.

All writable tests use temporary destinations; no live preference record or institutional GA output is used for acceptance writes. Existing browser-dependent backend cases are explicitly deselected from the broad GA group. Frontend contracts, production build and focused authentication-module lint are separate checks. Full-repository lint and a production optimization/benchmark are not claimed.

## Browser acceptance and genuine screenshots

All six requested PostgreSQL browser scenarios remain **NOT RUN: separate target/fixture preparation and execution approval required**. Missing configuration was the earlier 2026-10-16 blocker; it is not an explanation for the now-successful user PostgreSQL run. The installed Computer Use guidance was previously reviewed; no browser interaction, browser-account provisioning, acceptance server startup or screenshot capture occurred during this review. Current browser automation availability/version has not been tested. Do not relabel earlier blocked attempts as successful.

See [manual browser instructions](testing/phase-4b/browser-acceptance.md), the prepared owned [browser fixture](testing/phase-4b/serve_browser_fixture.py) and the [screenshot directory record](screenshots/phase-4b/README.md). The fixture's missing-configuration rejection is tested; real PostgreSQL/browser startup remains unverified. No earlier Phase 4A screenshot is relabelled as Phase 4B evidence.

## File inventory

Production changes are limited to the new input-validation service and calls in `backend/routers/genetic_algorithm.py`. Tests add `test_ga_input_validation.py`, `phase4b_database_safety.py`, `test_phase4b_database_safety.py`, `test_phase4b_postgresql.py` and `test_phase4b_browser_fixture.py` under `backend/tests/`.

Evidence includes this report, the Phase 4B testing runner/ledger/JSON records and browser instructions, screenshot status, and [thesis evidence](thesis-evidence/phase-4b-evidence.md). Existing roadmap/bug reports receive dated Phase 4B.1 entries. The final preservation manifest enumerates created/modified paths and protected-file comparisons.

## Reproduction

From the project root, use the existing virtualenv:

```powershell
.\.venv\Scripts\python.exe docs/testing/phase-4b/run_checks.py admission
.\.venv\Scripts\python.exe docs/testing/phase-4b/run_checks.py auth
.\.venv\Scripts\python.exe docs/testing/phase-4b/run_checks.py ga
.\.venv\Scripts\python.exe docs/testing/phase-4b/run_checks.py domain
.\.venv\Scripts\python.exe docs/testing/phase-4b/run_checks.py frontend-auth
.\.venv\Scripts\python.exe docs/testing/phase-4b/run_checks.py frontend-preferences
.\.venv\Scripts\python.exe docs/testing/phase-4b/run_checks.py frontend-ga
.\.venv\Scripts\python.exe docs/testing/phase-4b/run_checks.py build
.\.venv\Scripts\python.exe docs/testing/phase-4b/run_checks.py lint
```

For PostgreSQL, the owner must privately provision the exact disposable database/role and supply `PHASE4B_TEST_DATABASE_URL` in the execution environment. Do not paste it into chat or documentation. The tester role must have DDL rights within its own database but no superuser/createdb/createrole flags. Then run the `postgresql` group. Stop for a failed safety gate; never substitute another database, reset an existing schema or downgrade to retry.

## Rollback and remaining limitations

An application rollback can remove only the new admission service/router integration after review; no data migration needs reversing. Preserve user changes rather than resetting the working tree. Database rollback is not automated: retain synthetic acceptance records and seek owner approval for any later disposal. Never run migration downgrade against institutional identities.

The guard covers API admission and worker entry, not direct notebook/Python calls to the legacy loaders. It does not establish an operating-system lease on files; arbitrary external edits after validation remain subject to the existing fingerprint checks. Admission and API preference writes share the existing process-local lock, but no multiworker guarantee is added. The stored schema is intentionally not replaced by the new-edit contract.

Genuine PostgreSQL browser screenshots and production deployment qualification remain outstanding. The recorded 14-case PostgreSQL suite passed; it does not certify production deployment. No database readiness endpoint, account workflow redesign, historical-score comparison change or result-write redesign is included. Existing large frontend bundle/full-lint limitations remain outside this phase.

## Historical first-execution results and review decision (2026-10-16)

- Backend: **503 passed**, in distinct groups (81 new admission/safety/helper, 61 auth, 219 domain/preferences/reports, 142 GA lifecycle/history); repeated successful runs are not added. Two existing browser cases deselected.
- PostgreSQL: **14 skipped / BLOCKED**. URL remained absent after the explicit user recheck; no fallback or PostgreSQL connection/migration/write.
- Frontend contracts: **78 passed** (8 + 22 + 48). Build passed (129 modules; existing 751.57 kB JS chunk warning). Focused lint passed on five authentication frontend modules; full lint not run.
- Browser: **six BLOCKED / NOT RUN**, zero Phase 4B screenshots. Prepared PostgreSQL/browser fixture behavior is not claimed verified.
- Final [artifact and preservation manifest](testing/phase-4b/manifest.json) lists every created/modified file and the protected-source/data checks. The index and HEAD are unchanged; no staging/commit/push.

**Recommendation:** the API admission correction is ready for review. The complete Phase 4B.1 remains **not ready for acceptance** until the designated disposable PostgreSQL environment and genuine browser scenarios are verified.

## Acceptance resumption attempt: 2026-10-16, 23:49 +08:00

After the user reported private database configuration, the variable was checked again in the actual command execution environment without displaying its value. `PHASE4B_TEST_DATABASE_URL` was still absent. The documented PostgreSQL runner completed with **14 skipped, zero passed and zero failed**; it made no connection or migration/write attempt. Database identity, role privileges, schema, revision and existing records therefore remain **NOT VERIFIED**. `DATABASE_URL` was not used as a fallback. No schema initialization or cleanup was attempted.

All six browser scenarios remain **BLOCKED / NOT RUN**, with zero screenshots. No isolated backend/frontend was started and no browser interaction occurred: the required verified PostgreSQL prerequisite was unavailable. Browser-tool unavailability is not asserted. The existing manual instructions remain applicable once the variable is present in this execution environment; configuration in a separate shell may not be inherited here.

Safe isolated reruns passed: **81 admission/safety/helper + 61 authentication backend cases**, and **8 authentication + 22 preference frontend contracts**. One existing authentication browser case was deselected. These are reruns of existing cases, not additions to the prior 503/78 distinct totals. The previous domain/GA, build and lint evidence remains historical; those unchanged groups were not rerun during this attempt.

The [resumption record](testing/phase-4b/2026-10-16-resume-01/acceptance-status.json) records commands/results, the blocked scenarios and protected-file comparisons. The [ledger](testing/phase-4b/README.md) links the five new execution artifacts. No application, test-helper or protected-data changes were required. Full phase acceptance remains blocked.

## PostgreSQL success and pre-Stage A browser readiness (2026-10-18)

The user's authorized run [20261018T100533+0800-postgresql-e2beb33f.json](testing/phase-4b/20261018T100533+0800-postgresql-e2beb33f.json) reports **14 passed, zero failed/skipped, three warnings, exit 0**. Pytest time was **12.23s**; runner elapsed was **13.660s**. Start/end: 10:05:33.735990 to 10:05:47.395945 +08:00. Runtime: Python 3.14.2, pytest 9.1.1, SQLAlchemy 2.0.52, FastAPI 0.141.1, Alembic 1.19.2, psycopg2-binary 2.9.12. This is genuine user-executed database evidence inspected by Codex, not a Codex-executed online run.

All fourteen assertions/cases passed, including revision `4a_0001`, table/constraint creation, synthetic imports, bindings/duplicates, genuine login/valid-CSRF ownership, session persistence across fresh backend processes, logout/expiration/revocation, concurrent bootstrap/last-admin protection, real lock timeout and a sanitized injected outage. The supplied record does not contain server version, raw catalog rows or warning details. Do not claim a physical database outage or HTTP/browser restart from the ASGI subprocess/session checks.

**Warnings:** `--disable-warnings` suppressed the three messages; the artifact contains only their count. Exact identification remains unavailable. Static Alembic source/config inspection suggests a missing-`path_separator` deprecation as one UNCONFIRMED candidate; the other warning messages/categories are unknown. Do not invent warning attributions or rerun the now-nonempty database to recover them. Details may be added only from original output or separately approved future instrumentation, with provenance.

The existing browser helper cannot use a second database as written and cannot reuse the now-nonempty successful database. Its redirects also need tightening before privacy-safe browser acceptance: synthetic identity labels still accompany copied real profile metadata, and `routers.chromosomes.LATEST_RESULT_FILE` remains a separate unredirected reader. The [browser plan](testing/phase-4b/browser-acceptance-plan.md) proposes a new restricted browser role/database/variable, an independently fail-closed test-only target policy, complete temporary storage/profile isolation and explicit no-GA guards. Those changes are **planned, not implemented**. No database reset is proposed.

**Current decision:** PostgreSQL acceptance PASS; browser execution NOT READY / NOT RUN pending fixture/provisioning/execution approval. All six browser scenarios and screenshots remain outstanding. This review changed documentation/evidence only, did not connect to PostgreSQL, and did not start any backend, frontend or browser service. No new regressions were run for documentation-only changes. The successful database and all institutional application data were left untouched by this review.

## Stage A browser fixture preparation (2026-10-18)

**Implemented and offline verified:** independent browser-only target gate, synthetic profiles/empty catalog, fourteen temporary read/write aliases, actual authentication/CSRF/ownership, fresh registry, generation/resume blocks, startup failure containment, private Windows ACL verification and existing-PNG evidence hashing with pending-review attribution. The old acceptance gate/module and production GA/app sources are unchanged. Existing results cannot be read through either latest-result alias. The helper now accepts only `PHASE4B_BROWSER_DATABASE_URL`; original test/application variables are not fallbacks. Its explicit initialization flag remains reserved for separately approved Stage B.

Actual Stage A results: **93 offline browser/safety/evidence cases + 61 auth cases passed**, one browser case deselected; **78 frontend contracts passed**. Fake PostgreSQL engines/in-memory SQLite/ASGI are offline fixture evidence, not React or PostgreSQL browser acceptance. No real PostgreSQL connection, migration, provisioning, service startup or browser test occurred. Build/lint/full GA tests were not rerun because production/frontend/engine code was unchanged.

The first offline run's ACL-script parser error (90 passed/one failed) was corrected without relaxing ACL checks; intermediate and final runs remain archived. See the [detailed report](testing/phase-4b/stage-a-fixture-preparation.md), [stage manifest](testing/phase-4b/stage-a-manifest.json) and ledger for commands/timestamps/artifacts, isolation/rollback, thesis scope and limitations. No screenshot was generated, and the IO helper cannot automatically declare PASS.

**Current decision:** Stage A ready for review; all six actual browser scenarios remain NOT RUN. Stage B needs approval, a privately configured new browser role/database, successful actual read-only preflight and owned loopback/profile startup. Do not pre-migrate/reset any target or touch the successful acceptance database. Exact manual commands and the initialization opt-in are in the [updated plan](testing/phase-4b/browser-acceptance-plan.md). No staging/commit/push occurred.


## Retained browser-fixture recovery preparation (2026-10-18)

The user reports successful initial isolated fixture/frontend setup, later process exit/handoff removal, and five successful read-only checks of the retained browser database: exact target/read-only connection, revision 4a_0001, two expected identities, one active unbound administrator, zero sessions. These are USER CONFIRMED, not a new Codex PostgreSQL run. The original 14-case PostgreSQL acceptance artifact and database remain unchanged.

A separate recovery mode is now [implemented and offline verified](testing/phase-4b/stage-b-recovery-offline.md). Initialization retains its original empty gate; recovery validates the exact schema/accounts and holds shared fixture ownership, then would revalidate under table locks before an explicitly approved administrator credential update. It performs no migrations/seeding/reset/session deletion. Four-hour lifetime is explicit/bounded; normal authentication and all fourteen storage aliases/GA blocks remain unchanged.

Actual current results: 187 browser/recovery offline cases and 61 auth cases passed (1 browser deselected), plus 78 frontend contracts. No live PostgreSQL recovery, credential change, service/browser startup or capture occurred; build/full lint/GA execution were not rerun. Actual catalog/reflection/locking/startup must still be verified after separate approval. Full Phase 4B.1 acceptance remains incomplete: all six genuine browser scenarios/screenshots are outstanding. See the [current execution plan](testing/phase-4b/browser-acceptance-plan.md#recovery-of-the-retained-browser-database-offline-prepared) and [recovery manifest](testing/phase-4b/stage-b-recovery-manifest.json) for exact evidence/protected-file comparisons. Previous report sections remain dated historical records.
