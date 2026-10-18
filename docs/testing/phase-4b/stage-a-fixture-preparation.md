# Phase 4B.1 Stage A: isolated browser fixture preparation

2026-10-18, Asia/Manila. Source checkpoint `c770c841259b968132f8ce6b48ae5cb36df35171` plus the documented pending Phase 4B.1 work. **STAGE A IMPLEMENTED / OFFLINE VERIFIED. STAGE B NOT EXECUTED.** No PostgreSQL connection, migration, provisioning, server/browser startup or browser acceptance occurred in this stage.

## Objectives, files and design

Prepare a genuinely authenticated, synthetic browser instance without selecting the successful PostgreSQL acceptance database or modifying institutional storage. This is test/evidence tooling, not an application feature or GA change.

| File | Stage A change |
|---|---|
| `backend/tests/phase4b_browser_safety.py` | New independent exact browser variable/database/role/IPv4/port gate; read-only catalog/ownership/privilege/emptiness checks |
| `backend/tests/phase4b_browser_support.py` | New synthetic profiles and account seeding; fourteen path aliases; real-auth dependency isolation; Windows private-directory ACL enforcement; guarded future migration |
| `backend/tests/test_phase4b_browser_safety.py` | New offline target/catalog rejection and SELECT-only tests |
| `backend/tests/test_phase4b_browser_fixture.py` | Expanded offline in-memory SQLite/ASGI lifecycle, authorization, storage, failure and ACL tests |
| `backend/tests/test_phase4b_browser_evidence.py` | New evidence IO/hash/privacy/attribution tests, not browser acceptance |
| `docs/testing/phase-4b/serve_browser_fixture.py` | Browser-only entry point; explicit initialization opt-in; reserved owned socket; no acceptance-fixture reuse |
| `docs/testing/phase-4b/record_browser_evidence.py` | New helper hashes an existing operator-reviewed PNG and writes pending-review metadata; never captures/generates an image or automatically declares PASS |
| `docs/testing/phase-4b/run_checks.py` | New `browser-offline` group; redact both private test/browser URLs and passwords |

Documentation updates cover this report, [execution plan](browser-acceptance-plan.md), ledger, browser instructions/screenshot status, main verification report, roadmap, thesis evidence and manifests. Exact pending paths/hashes are in [manifest.json](manifest.json); this stage's results/provenance are in [stage-a-manifest.json](stage-a-manifest.json). No production source, original fourteen-case PostgreSQL test or original acceptance safety helper was changed.

## Independent browser target and pre-write gate

Only `PHASE4B_BROWSER_DATABASE_URL` is read. Allowed target: PostgreSQL/psycopg2, `ccs_ga_phase4b_browser_test`, `ccs_ga_phase4b_browser_tester`, literal `127.0.0.1`, explicit `5432`, no URL query overrides. Both the original acceptance database and its role are rejected; neither its variable nor `DATABASE_URL` is a fallback. The original gate remains unchanged.

Every preflight connection starts read-only with connect/statement/lock timeouts. Actual database/current role/address/port/current schema, restricted role flags (including replication/BYPASSRLS), database ownership and public CREATE permission must match. Only the public user schema is allowed. Relations, functions, types and non-default extensions cause rejection before migration. A literal `pg_` prefix is excluded as system scope; a user schema such as `pgshadow` is not mistaken for a system schema. No reset/drop/downgrade/reuse path exists.

The executable helper requires `--allow-browser-database-initialization`; without it, it stops before URL access, socket binding or any database operation. Stage B is not authorized yet. On an approved run it validates a new private OS-temp root, reserves only its own socket, verifies ACLs/preflight, installs and asserts isolation, then rechecks the empty target immediately before real Alembic upgrade. It seeds only two synthetic identities and one synthetic administrator. Existing data or setup failure stops the run; do not rerun against a partially initialized database without owner review.

## Complete isolation and genuine authorization

Fourteen path aliases cover preference/settings router readers/writers, both GA/scorer input readers, checkpoint/history/stopped storage, both GA and chromosome latest-result readers, and saved/best/uploaded results. [The plan's inventory](browser-acceptance-plan.md#required-storage-and-process-isolation) identifies every alias. All resolve under the single owned temporary storage root and are asserted before migration/readiness. Identity/session access and direct engine access are bound to the supplied browser engine. In offline tests that engine is explicitly **in-memory SQLite**, not PostgreSQL.

Faculty objects are newly constructed synthetic dataclasses; no real faculty object is copied or iterated. IDs use a browser-only UUID namespace; names, rank, releases, targets and expertise/eligibility fields are synthetic. The catalog is intentionally empty. This supports the six account/style/preference scenarios without exposing real academic profiles, but does not prove course-card/calendar behavior. Existing preference validation and role/ownership/Origin/CSRF logic remain real. Any subject preference is rejected against the empty synthetic catalog; no eligibility rule is relaxed.

The fixture replaces only database/storage/metadata dependencies, never a principal or permission guard. A fresh run registry plus blocked fresh generation and resume entry points prevent optimization/recovery. Offline tests assert zero scorer calls and unchanged Python GA random state for denied execution requests. Real workload/fitness policy, eligibility, external locks, operator code and checkpoint representation remain untouched.

Runtime services are one owned loopback backend using its prebound ephemeral socket and React on `localhost:5189 --strictPort`; no reload or additional workers. A public, nonsecret `/__phase4b_fixture` marker reports the owned instance ID and synthetic/no-GA scope. A dedicated browser profile is required in Stage B because localhost cookies are shared across ports. No existing service is stopped or reconfigured.

Windows ACLs are applied and verified on the new private fixture directory for current user, SYSTEM and Administrators only. The ACL child receives no database connection variables. Its handoff contains only synthetic app credentials/backend metadata, not database credentials. Cleanup removes only known owned handoff/control files after shutdown; disposable data and the browser database remain for review. Failed startup closes only its owned socket/resources and cannot issue service/process stop commands. A hung owned daemon thread causes failure/private-file retention and helper-process exit; no automatic reset is attempted.

The unavailable marker injects a labelled fixture 503 into database dependencies. Recovery removes only that owned marker. It does not stop PostgreSQL or simulate a demonstrated physical database-service outage.

## Executed tests and incident provenance

| Group | Actual result | Artifact |
|---|---|---|
| Browser offline: original safety + new browser safety/fixture/evidence | **93 passed**, 2 warnings, 6.36s | [final browser offline](20261018T104156+0800-browser-offline-3fc460e7.json) |
| Existing authentication/ownership | **61 passed**, 1 browser case deselected, 4 warnings, 38.50s | [auth](20261018T102917+0800-auth-ae3212b4.json) |
| Frontend auth contracts | **8 passed**, zero failures | [auth contracts](20261018T102916+0800-frontend-auth-3b6097f2.json) |
| Frontend preferences contracts | **22 passed**, zero failures | [preference contracts](20261018T102918+0800-frontend-preferences-d5b1246a.json) |
| Frontend GA/report contracts | **48 passed**, zero failures | [GA contracts](20261018T102919+0800-frontend-ga-96e4276b.json) |

This stage totals **154 passed backend cases and 78 passed frontend contracts**, with one existing browser case deselected. Do not add repeated/overlapping earlier suites to these totals. No PostgreSQL acceptance test was run. The existing genuine user-executed 14-case PASS remains separately attributed and unchanged. No build/full lint/production GA regression was rerun for test-only tooling changes; no frontend or engine source changed. Exact commands, timestamps, versions, temporary destinations and outputs are in the artifacts.

**Retained initial failure:** [first browser-offline run](20261018T102915+0800-browser-offline-a6cf6d43.json): 90 passed, 1 failed, 2 warnings, 8.91s. A leading `+` introduced in the new embedded PowerShell ACL script caused a parser error before ACL setup. The character was removed, without loosening permission requirements. An actual owned-temp Windows ACL test then passed. This is a pre-release implementation incident, not a new production scheduling/authentication defect. No private credentials or database calls were involved. The diagnostic temp directory contained no credentials. Intermediate [91-case](20261018T103008+0800-browser-offline-496f2ecf.json) and [92-case](20261018T103133+0800-browser-offline-354d402a.json) successful runs are retained; subsequent tests added schema-prefix and existing-storage preservation coverage.

Earlier 93-case passes [103234](20261018T103234+0800-browser-offline-d1531e28.json) and [104004](20261018T104004+0800-browser-offline-c9b696bd.json) remain archived. Catalog dependency/event-trigger/publication checks and the final additional offline PostgreSQL-engine fence were verified by the latest 104156 run, without changing case count. The runner suppresses warning details; actual counts are recorded, not invented messages. The original PostgreSQL run's three warning messages remain unavailable.

## Browser/API/evidence status and thesis scope

Offline ASGI requests exercised account creation/binding/duplicates, faculty save/re-read/new authenticated client, administrator review, valid-CSRF ownership rejection, unauthenticated/role denial, logout and injected-fault recovery. These are real-auth **in-memory SQLite tests**, not React browser observations or a PostgreSQL browser pass. Offline startup tests fake engines/sockets and prohibit Alembic/server execution. The six actual browser scenarios remain **NOT RUN**; screenshots remain **zero**.

The evidence helper consumes only existing PNG bytes, requires explicit privacy/observer metadata and offset timestamps/local URLs, refuses overwrite/credential-like notes, records SHA-256/dimensions and labels injected faults. It writes **CAPTURE RECORDED - ACCEPTANCE REVIEW PENDING**, not PASS. Hashes cannot prove authenticity or detect private text in images; an operator must verify the actual browser, observed result and privacy before acceptance. Its IO tests use a previously reviewed Phase 4A image only in pytest temporary storage, never archive/relabel it as Phase 4B evidence.

This establishes controlled fixture/readiness and regression evidence for the thesis prototype, not usability, production deployment, physical outage or GA-quality results. Browser/real database startup, migrations on the new target, profile handling and genuine captures remain unverified until Stage B. No screenshots or successful browser results have been fabricated.

## Reproduction, Stage B and rollback

Offline: `.\.venv\Scripts\python.exe docs/testing/phase-4b/run_checks.py browser-offline`, plus `auth`, `frontend-auth`, `frontend-preferences`, `frontend-ga`. Writable fixture/test storage is under unique OS-temp paths or in-memory SQLite. The [Stage B plan](browser-acceptance-plan.md) provides exact private setup/preflight/startup commands and capture/shutdown procedures; **do not execute its database-changing commands until separately approved**.

Stage B needs approval, an authorized verified administrator connection for the new role/database if absent, privately available browser URL, successful read-only gate, port/profile availability, and current Computer Use URL verification. No database/role existence check was made in Stage A. Leave the successful acceptance database and institutional development database unchanged. Do not run the old PostgreSQL suite or manually pre-migrate the new target: the owned helper requires empty preflight before its approved initialization.

Rollback is limited to reviewed fixture/test/documentation changes; no application or database rollback is necessary for Stage A. Preserve all existing pending work. There is no automatic database deletion or migration downgrade. Final hashes/Git state are recorded in the stage/main manifests. No staging, commit or push occurred.
