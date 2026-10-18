# Phase 4B.1 Stage B: browser recovery, offline verification

2026-10-18, Asia/Manila. **IMPLEMENTED / OFFLINE VERIFIED; LIVE RECOVERY NOT RUN.** Source checkpoint `c770c841259b968132f8ce6b48ae5cb36df35171` plus existing pending Phase 4B work. Approval covers fixture tooling, offline regressions and documentation only. No live credential update, migration, service or browser execution occurred.

## Objectives and evidence attribution

Prepare recovery of the dedicated retained browser database without reseeding, resetting it or selecting the original acceptance database. The user confirmed five read-only checks: exact browser target/read-only connection, revision `4a_0001`, exactly two declared synthetic identities, exactly one active unbound synthetic administrator and zero sessions. Earlier fixture/frontend setup and subsequent process exit/handoff removal are also **USER CONFIRMED**. No raw result/screenshot or exact observation timestamp was supplied; Codex did not independently query that database. The six browser scenarios remain **NOT RUN**, zero new screenshots.

Source confirms a 1800-second post-readiness deadline, followed by owned-server shutdown and handoff/control-marker removal. Database and storage remain. The original exit's actual reason is unknown without timestamps/exit evidence; expiration is a verified mechanism, not proof of that particular exit. No stored password/session secrets were queried.

## Files and design

| File | Change |
|---|---|
| `backend/tests/phase4b_browser_recovery.py` | New exact target/schema/content inspection, SELECT-only preflight, advisory ownership and explicitly approved credential rotation |
| `backend/tests/test_phase4b_browser_recovery.py` | New offline rejection, catalog, transaction, concurrency, redaction, lifetime and lifecycle tests |
| `docs/testing/phase-4b/serve_browser_fixture.py` | Mutually exclusive recovery option, shared lock in both modes, bounded lifetime, complete private handoff publication and safe status messages |
| `docs/testing/phase-4b/run_checks.py` | Recovery tests included in the fenced browser-offline group |
| Plan, ledger, roadmap, verification report, thesis evidence and manifests | Results, provenance, manual procedure and explicit live-approval boundary |

The original empty-target safety module, fourteen-case PostgreSQL suite, browser isolation support and production authentication/GA/frontend sources remain unchanged. Initialization retains its empty checks, immediate pre-DDL recheck, Alembic and original seeding helpers. Recovery is a separate branch and cannot invoke migration or seeding.

Only `PHASE4B_BROWSER_DATABASE_URL` selects the exact browser database/role at literal IPv4/port, without URL query overrides or fallback. Actual server identity, ownership, public CREATE privilege and restricted role flags must match. Read-only preflight connections have connect/statement/lock timeouts. Recovery requires only the public user schema, exact four-table column/default/nullability/type profile, PK/unique/FK/CHECK/index definitions and sole revision. Extra relations/functions/types/extensions/rules/policies/triggers/inheritance, invalid indexes, unexpected owners and nonvalidated/deferred/unenforced constraints are rejected. CHECK parsing preserves AND/OR grouping and only supports the declared grammar, including PostgreSQL's reflected ANY/ARRAY and text casts.

PostgreSQL 18 represents NOT NULL constraints explicitly in `pg_constraint`; these receive exact validation rather than being mistaken for extra objects ([official catalog documentation](https://www.postgresql.org/docs/18/catalog-pg-constraint.html)). Earlier representation is tested offline too. Live reflection compatibility remains unverified until the new read-only preflight actually runs.

Contents must be exactly two declared synthetic UUID/name/label tuples, the one seeded active unbound administrator, and zero sessions. Extra or changed accounts/identities/sessions cause rejection; no silent revocation/deletion. SELECTs explicitly project nonsecret fields and aggregate session count; schema reflection reads definitions, never stored password/token/CSRF values. Matching deterministic IDs alone is not proof of provenance; user authorization of this dedicated database remains required.

Both CLI modes hold one session-level advisory lock throughout setup, serving and worker shutdown. A second participating fixture is rejected before mutation or launch. Legacy helpers do not participate and must already be stopped. This lock coordinates fixture tooling, not arbitrary external administrator writes.

After separate live approval, generate a fresh administrator password with `secrets` and the existing authentication hasher. Revalidate the complete profile under table locks in a transaction immediately before updating only that administrator's password hash and update timestamp. Require exactly one changed row; failure rolls back. Do not select the old hash, insert identities/accounts, delete sessions, or run DDL. Read-only default transaction behavior resumes afterward.

A NEW private OS-temp directory retains the existing Windows ACL policy. New storage, app/registry, instance ID and handoff prevent reuse of stale files/state. All fourteen path aliases and generation/resume blocks remain enforced. Old storage is retained; this mode does not restore edited preferences. Publish the complete five-field handoff through an exclusive private pending file after server readiness; refuse existing handoffs. Cleanup removes only known owned marker/pending files after worker shutdown. If the worker cannot stop within its bound, terminate only this CLI's process before relinquishing database ownership, retaining private artifacts for review. Tests intercept termination; no process was actually terminated.

Default lifetime remains 1800 seconds. Explicit `--lifetime-seconds 14400` allows four hours; valid integer bounds are 60 through 14400, never unlimited/autoextended. Print nonsecret expiry, remaining-time warnings, requested-stop/deadline reason and static failure stage. Do not print exception details, credentials or URLs. Ordinary authentication/session expiry, CSRF, cookies, ACLs and authorization are unchanged.

## Tests actually executed

Commands: `.\.venv\Scripts\python.exe -B docs/testing/phase-4b/run_checks.py <group>` from repository root. Fixtures prohibit real PostgreSQL engines, migrations and services. Existing Windows owned-temp ACL and in-memory SQLite/ASGI authentication tests remain included.

| Group | Result | Artifact |
|---|---|---|
| Final browser-offline | **187 passed**, zero failed/skipped, 2 warnings, 7.39s | [browser offline](20261018T124936+0800-browser-offline-517a1187.json) |
| Auth/ownership | **61 passed**, 1 existing browser case deselected, 4 warnings, 37.06s | [auth](20261018T124832+0800-auth-bcf8ebc9.json) |
| Frontend auth contracts | **8 passed**, zero failed/skipped | [auth contracts](20261018T124833+0800-frontend-auth-5addb12f.json) |
| Frontend preference contracts | **22 passed**, zero failed/skipped | [preferences](20261018T124834+0800-frontend-preferences-d0aa5fd2.json) |
| Frontend GA/report contracts | **48 passed**, zero failed/skipped | [GA contracts](20261018T124836+0800-frontend-ga-88a9fe6a.json) |

Totals for this attempt: **248 backend passes, 78 frontend contract passes**; do not add overlapping historical/intermediate runs. Retained intermediate successes: [173 cases](20261018T124430+0800-browser-offline-e3861185.json), [186 cases](20261018T124739+0800-browser-offline-8fe74e92.json), [187 cases before final status/order refinement](20261018T124831+0800-browser-offline-a0883cb8.json). No failed test run occurred in this implementation attempt. The existing runner suppresses warning details; counts are not invented categories.

Coverage: wrong URL/server/privileges/schema/revision; identity/account/session drift; changed columns, defaults, constraints, boolean grouping and indexes; PG18 nullability catalogs; both modes and exclusive flags; overlapping ownership threads; credential-update shape, revalidation and rollback; deadline/stop/startup/rotation/handoff failures; worker-termination interception; private handoff publication; original fourteen storage aliases/GA blocks; unchanged Python GA RNG and zero fitness calls. The actual migration declarations are compared to the recovery profile in memory without DDL. SQLite transaction tests verify commit/rollback only; PostgreSQL-specific locking/server/schema operations are mocked.

Build/full lint/full GA execution were not rerun because application/frontend/engine source did not change. Live PostgreSQL/API recovery, credentials, migrations, seeding and browser acceptance were **NOT RUN**. No screenshots were fabricated. Protected file/head/index comparisons and current artifact hashes are in the [recovery manifest](stage-b-recovery-manifest.json).

## Manual procedure, limitations and thesis relevance

Follow the [recovery execution plan](browser-acceptance-plan.md#recovery-of-the-retained-browser-database-offline-prepared) after separate approval: first SELECT-only preflight, then explicit credential rotation/new private fixture, dedicated frontend target verification and actual browser scenarios. Use a fresh isolated browser context; do not reuse old cookies, instance IDs or remembered GA runs. User enters credentials privately. Preserve correct user/Codex observer attribution and genuine screenshot metadata.

Live catalog reflection, PostgreSQL lock/rotation behavior and recovery startup remain unverified. This narrow mode rejects sessions or faculty accounts from partially completed acceptance. Failure after committed rotation but before readiness can require another explicitly approved rotation; no automatic retry, password rollback or reset exists. Deadline cleanup still removes the plaintext handoff; four hours is finite, not persistent credential storage. Original PostgreSQL success, blocked attempts and Stage A source hashes remain historical evidence, not current-byte assertions for edited tooling.

This establishes testable fixture lifecycle and fail-closed recovery design for thesis evidence. It does not establish browser acceptance, actual PostgreSQL recovery, usability, GA quality or production readiness. Production authentication, GA mathematics/weights/operators/RNG/checkpoint format and live records remain unchanged. No staging, commit or push occurred.
