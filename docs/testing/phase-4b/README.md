# Phase 4B.1 executed testing ledger

Baseline: `c770c841259b968132f8ce6b48ae5cb36df35171`. Windows; Python 3.14.2, Node v24.11.1, npm 11.6.2. Per-run Python package versions, exact command/cwd, start/end timestamps with offsets, elapsed time, child exit status and sanitized output are in each JSON file.

## Current written-only browser acceptance (documentation update 2026-10-18)

**P4B-B01 through P4B-B06: PASS — USER CONFIRMED. Screenshot evidence: NOT CAPTURED for every scenario. Automated browser execution: NOT ESTABLISHED. Original test timestamps: NOT RECORDED.** The user confirms no screenshots were taken. The [final manual report](manual-acceptance-results.md) and [manual manifest](manual-acceptance-manifest.json) record these outcomes without inventing image hashes or original execution metadata. B06 injected fixture HTTP 503 with `ready.unavailable`; user-confirmed recovery restored the same faculty session and Compact / Very High. It was not a physical PostgreSQL outage.

This documentation-only update ran no tests, services, browser scenarios or database operations. Existing latest offline results remain **187 browser/recovery + 61 auth backend passes (1 deselected), and 78 frontend contracts**, separately from **14 user-executed real PostgreSQL passes**. Exact artifacts and warnings remain in the recovery section below and the final manual report. These scopes overlap older runs and must not be added to historical totals. Earlier blocked/failed attempts and Stage A/recovery manifests remain unchanged; their nested source hashes are historical snapshots, not assertions about subsequently edited documentation.

The remaining ledger is a chronology. Its earlier NOT RUN instructions and the following Stage A result table retain their original stage scope; use the current manual report for final browser status. No repeat setup or state-changing evidence collection is needed to review the written-only package.

Use [run_checks.py](run_checks.py) from the repository root. It creates a unique OS-temp pytest storage directory for each backend invocation and sets PYTHONDONTWRITEBYTECODE for children. No production GA is executed. PostgreSQL acceptance uses only PHASE4B_TEST_DATABASE_URL and the strict gate.

## Historical result table at Stage A completion

Repeated runs are not added to totals. A zero exit code with all cases skipped is BLOCKED, not a database pass. The three initial frontend records have child exit 0 but outer runner exit 1; see the incident record.

| Group | Result | Artifact |
|---|---|---|
| admission | 81 passed, 2 warnings in 18.68s | [20261016T234917+0800-admission-18ef74b1.json](20261016T234917+0800-admission-18ef74b1.json) |
| postgresql | USER-EXECUTED PASS: 14 passed, zero failed/skipped, 3 warnings in 12.23s; runner 13.660s, exit 0 | [20261018T100533+0800-postgresql-e2beb33f.json](20261018T100533+0800-postgresql-e2beb33f.json) |
| safety-gate-offline | CODEX-EXECUTED: 27 passed in 1.70s; no real database connection | [20261018T100212+0800-safety-gate-offline-7c09a63e.json](20261018T100212+0800-safety-gate-offline-7c09a63e.json) |
| browser-offline | STAGE A: 93 passed, 2 warnings in 6.36s; fake PG / in-memory SQLite / no TCP services | [20261018T104156+0800-browser-offline-3fc460e7.json](20261018T104156+0800-browser-offline-3fc460e7.json) |
| auth | 61 passed, 1 deselected, 4 warnings in 38.50s | [20261018T102917+0800-auth-ae3212b4.json](20261018T102917+0800-auth-ae3212b4.json) |
| domain | 219 passed, 2 warnings in 277.94s (0:04:37) | [20261016T230234+0800-domain-77bdae01.json](20261016T230234+0800-domain-77bdae01.json) |
| ga | 142 passed, 1 deselected, 2 warnings in 2150.20s (0:35:50) | [20261016T230233+0800-ga-95b3a329.json](20261016T230233+0800-ga-95b3a329.json) |
| frontend-auth | 8 passed / 0 failed | [20261018T102916+0800-frontend-auth-3b6097f2.json](20261018T102916+0800-frontend-auth-3b6097f2.json) |
| frontend-preferences | 22 passed / 0 failed | [20261018T102918+0800-frontend-preferences-d5b1246a.json](20261018T102918+0800-frontend-preferences-d5b1246a.json) |
| frontend-ga | 48 passed / 0 failed | [20261018T102919+0800-frontend-ga-96e4276b.json](20261018T102919+0800-frontend-ga-96e4276b.json) |
| build | PASS, child exit 0; 129 modules, existing >500 kB chunk warning | [20261016T230314+0800-build-713f666a.json](20261016T230314+0800-build-713f666a.json) |
| lint | PASS, child exit 0; five listed authentication frontend modules only, not full lint | [20261016T230315+0800-lint-b0358b7d.json](20261016T230315+0800-lint-b0358b7d.json) |

## Commands and incidents

Commands for every group are in [the phase report](../../phase-4b-postgresql-verification.md). [collection-incidents.json](collection-incidents.json) preserves the pre-fix 200-versus-503 failure, the paused-fixture clock correction and the cp1252 evidence-runner printing failure. The initial two uninstrumented executions have unknown wall-clock timestamps; pytest-reported durations and exit/results are recorded without invented times.

The runner now emits UTF-8 output in its own process. No production diagnostic logging was changed. The first frontend children passed before their runner printing error; later clean reruns confirm both child and runner success. Existing JSON records were retained.

[database-environment-recheck.json](database-environment-recheck.json) records the absence of PHASE4B_TEST_DATABASE_URL after the user asked for a recheck. No connection or migration occurred. Any future nonempty test schema is refused, not reset.

## Browser / database / preservation boundaries

[Browser acceptance](browser-acceptance.md): all six PostgreSQL scenarios BLOCKED, no screenshots. The existing installed Computer Use guidance was reviewed, but no browser interaction or account creation was attempted. Browser-dependent backend cases are deselected from the GA group; the SQLite auth group deselects its browser case. This does not claim an automated browser pass.

Real PostgreSQL migration/constraints/locking/bootstrap/login/restart remain unverified in this execution. Prepared code is not executed evidence. The schema fixture retains synthetic database data after a future approved run; it has no downgrade or database deletion path.

Source scoring helpers/operators/checkpoint format, identity registry and live preferences are protected by baseline/final hashes. Final file inventory and artifact hashes are in the phase manifest once verification finishes. Full repository lint, empirical optimization benchmarks, production workloads and database deployment acceptance are not claimed.

## All execution artifacts


- [20261016T230130+0800-admission-1fd0a944.json](20261016T230130+0800-admission-1fd0a944.json)
- [20261016T230148+0800-auth-6d4c0d92.json](20261016T230148+0800-auth-6d4c0d92.json)
- [20261016T230159+0800-postgresql-5b17e22d.json](20261016T230159+0800-postgresql-5b17e22d.json)
- [20261016T230234+0800-domain-77bdae01.json](20261016T230234+0800-domain-77bdae01.json)
- [20261016T230234+0800-frontend-auth-e87a852a.json](20261016T230234+0800-frontend-auth-e87a852a.json)
- [20261016T230235+0800-frontend-preferences-3a541c8b.json](20261016T230235+0800-frontend-preferences-3a541c8b.json)
- [20261016T230236+0800-frontend-ga-741573e0.json](20261016T230236+0800-frontend-ga-741573e0.json)
- [20261016T230313+0800-frontend-auth-dbed8e40.json](20261016T230313+0800-frontend-auth-dbed8e40.json)
- [20261016T230313+0800-frontend-preferences-f0bc29ed.json](20261016T230313+0800-frontend-preferences-f0bc29ed.json)
- [20261016T230314+0800-build-713f666a.json](20261016T230314+0800-build-713f666a.json)
- [20261016T230314+0800-frontend-ga-25d59fcf.json](20261016T230314+0800-frontend-ga-25d59fcf.json)
- [20261016T230315+0800-lint-b0358b7d.json](20261016T230315+0800-lint-b0358b7d.json)
- [20261016T230545+0800-admission-bcc53354.json](20261016T230545+0800-admission-bcc53354.json)
- [20261016T231114+0800-admission-e0a6b0f7.json](20261016T231114+0800-admission-e0a6b0f7.json)

## Final distinct verification summary

**Backend: 503 passed** across disjoint groups: 81 new admission/safety/helper checks, 61 existing authentication/ownership checks, 219 domain/preference/report checks, and 142 monitoring/control/checkpoint/history checks. The 81 new cases comprise 65 admission/security/equivalence cases, 15 database-gate unit cases and one missing-environment browser-helper check. Two browser cases were deselected across the existing backend groups.

**PostgreSQL: 14 skipped / BLOCKED**; no database connection, migration or write occurred. These are not included in passed totals. Browser: six requested scenarios BLOCKED / NOT RUN; zero new screenshots.

**Frontend: 78 passed** (8 auth + 22 preferences + 48 GA/report contracts). Production build passed with the existing chunk-size warning; focused lint passed on the five listed authentication frontend modules. No full-project lint or frontend browser pass is claimed.

The backend GA group completed with 142 passed / 1 deselected / 2 warnings in 2150.20 seconds. Its initial pytest source was unchanged by later work except new test/helper/doc files outside that group; the production admission service/router were already in place. PostgreSQL fixture preparation after the skipped collection remains unverified against a real database.

Final archive inventory, source/evidence SHA-256, protected-file comparisons and Git preservation are in [manifest.json](manifest.json). Hashes identify actual archived bytes; no manifest hashes itself. The [browser helper](serve_browser_fixture.py) is prepared but not verified against PostgreSQL; its missing-URL exit is tested.

Additional retained execution artifacts:

- [20261016T231746+0800-admission-39ee929c.json](20261016T231746+0800-admission-39ee929c.json)

## Acceptance resumption: 2026-10-16 23:49 +08:00

The required variable was absent in the actual execution environment after the user's private-configuration notice. No database connection/migration/write or fallback occurred. The new PostgreSQL runner result is 14 skipped / zero passed / zero failed, not acceptance. All six browser scenarios remain BLOCKED / NOT RUN; no dedicated application instance or screenshot was created.

The five new execution records linked in the table above establish **142 passed backend cases, one deselected browser case, and 30 passed frontend contracts** for this attempt. These repeat previous cases and are not added to the 503/78 distinct totals. Domain/GA, build and lint rows above are previous evidence, not new executions. See [acceptance-status.json](2026-10-16-resume-01/acceptance-status.json) for this attempt's boundaries and protected-file comparisons. The earlier latest admission record remains archived as [20261016T232435+0800-admission-366311ce.json](20261016T232435+0800-admission-366311ce.json); previous frontend reruns remain in the artifact list.

## Focused safety-gate correction: 2026-10-18

The earlier missing-variable records and 503/78 totals above remain historical. The user's first authenticated PostgreSQL run produced [two setup errors](20261018T095643+0800-postgresql-ab3e0ed0.json), exit 1, before Alembic or any test body. It is not a fourteen-case pass or skip result. No PostgreSQL run was performed by Codex for this correction.

[BUG-012](../../system-bug-report.md#bug-012-valid-ipv4-server-rejected-because-inet-text-includes-its-netmask) documents the `inet::text` netmask mismatch and the approved one-line `host(inet_server_addr())` correction. The exact `127.0.0.1` comparison and every other safety condition remain unchanged. No role/database/schema/data changes, migrations, acceptance tests, browser tests or GA generation occurred.

**Executed offline result:** 27 passed, zero failed/errors/skipped in 1.70s. The [execution record](20261018T100212+0800-safety-gate-offline-7c09a63e.json) contains the exact command, temporary-storage path, timestamps, runtime/package versions and output. The suite previously had 15 cases; twelve negative cases were added and positive query-contract assertions strengthened. Do not add all 27 to previous distinct totals or interpret these fake-engine tests as PostgreSQL qualification. No frontend/build rerun was necessary for a test-harness-only change.

**Next action, after review:** run only the existing read-only `designated_url()` + `inspect_empty_database()` preflight from the user's configured PowerShell terminal. Never print the URL, use `DATABASE_URL` as fallback, run the acceptance runner, reset a schema, or start the browser fixture without the required subsequent approval. A nonempty database still stops preflight. The exact preflight command is provided in the final review response; it makes no migration/bootstrap call.

## User-executed PostgreSQL acceptance PASS (2026-10-18)

The [successful execution artifact](20261018T100533+0800-postgresql-e2beb33f.json) records 14 passed, zero failed/skipped and three warnings in 12.23s, exit 0; runner elapsed 13.660s. Codex inspected the existing file without rerunning tests or connecting to the database. The earlier [two setup errors](20261018T095643+0800-postgresql-ab3e0ed0.json), [missing-variable skips](20261016T234917+0800-postgresql-9d993683.json) and 27-case offline correction remain distinct historical evidence. The preceding next-action instruction was issued before this successful run and must not be used to rerun the suite against retained tables.

Warning identification is **INCOMPLETE**: `--disable-warnings` removed the summary/messages; only the count of three survives. A static Alembic `path_separator` warning candidate is UNCONFIRMED. No exact list of three warnings can honestly be reconstructed from the JSON. Preserve original output if separately available; do not reset/re-execute the database suite for warning discovery. No credentials or headers appear in the supplied success record.

The [browser readiness/execution plan](browser-acceptance-plan.md) proposes a second database rather than touching the successful one. The current helper is not compatible with that target and needs test-only changes plus isolation assertions. Browser: six NOT RUN, zero screenshots. No new backend/frontend regression or browser execution occurred during this documentation review. Historical 503/78 figures above remain their original scoped totals; the real fourteen-case PostgreSQL result is separately reported, not mixed with skipped or overlapping unit runs.

## Stage A preparation and offline verification (2026-10-18)

The [Stage A report](stage-a-fixture-preparation.md) supersedes the preceding planned-fixture status: separate target and synthetic/private fixture are implemented, but Stage B is NOT RUN. No PostgreSQL connection, migration, provisioning, TCP/browser service or screenshot capture occurred. The original acceptance module/gate and existing successful database were not changed. [Stage A manifest](stage-a-manifest.json) enumerates this task's changed paths and evidence; [main manifest](manifest.json) retains the complete pending Phase 4B inventory.

Actual final results: **93 browser/safety/fixture/evidence + 61 auth backend cases passed**, one existing browser case deselected; **78 frontend contracts passed** (8 + 22 + 48). These are overlapping reruns/new fixture cases, not additions to the historical 503/78 totals. The 93 cases comprise 27 original acceptance-gate units, 39 independent browser-gate units, 18 fixture/real-auth in-memory SQLite/ASGI units and nine evidence-IO units. No physical PostgreSQL/browser acceptance is inferred. Build/full lint/GA execution were not rerun for test-only changes.

Initial [90 passed / one failed](20261018T102915+0800-browser-offline-a6cf6d43.json), 2 warnings in 8.91s: a leading `+` in the newly embedded PowerShell ACL script caused a parser error. It was corrected without relaxing ACLs; the actual owned-temp Windows ACL test passed. Retained follow-ups: [91 passed](20261018T103008+0800-browser-offline-496f2ecf.json), [92 passed](20261018T103133+0800-browser-offline-354d402a.json), [93 passed](20261018T103234+0800-browser-offline-d1531e28.json), and the final [93 passed](20261018T104004+0800-browser-offline-c9b696bd.json) after broadening empty-object metadata checks. Do not add intermediate counts. This is a disclosed implementation incident, not a new production defect.

The latest [93-case pass](20261018T104156+0800-browser-offline-3fc460e7.json) followed the final additional PostgreSQL-engine fence in offline fixture tests. The preceding 104004 record remains an intermediate pass, not an extra suite. No implementation changes followed this final test run.

The [updated manual plan](browser-acceptance-plan.md) contains the exact separate-role/database SQL, secure environment setup, read-only browser preflight, NEW private-directory/ready.json command with explicit initialization flag, frontend port/profile, fault/shutdown controls and operator-reviewed PNG hashing. All six actual browser scenarios remain NOT RUN and require Stage B approval. Existing blocked/failed/user-executed PostgreSQL artifacts remain unchanged.


## Stage B retained-fixture recovery: offline implementation (2026-10-18)

**IMPLEMENTED / OFFLINE VERIFIED; LIVE RECOVERY NOT RUN.** The user reports initial fixture/frontend setup and five retained-database read-only checks passed; these are user-attributed observations, not a Codex browser/database execution. No administrator login or six-scenario acceptance has completed. Earlier blocked attempts and Stage A artifacts remain historical.

The [recovery report](stage-b-recovery-offline.md) records exact files, gate/locking/rotation design, scope and limitations; the [updated plan](browser-acceptance-plan.md#recovery-of-the-retained-browser-database-offline-prepared) contains the separate SELECT-only preflight and proposed four-hour recovery command. Default initialization emptiness/authentication/ACL/GA rules remain unchanged. Live credential rotation, migrations, seeding, service and browser execution were not performed.

Latest actual results: [187 browser-offline cases](20261018T124936+0800-browser-offline-517a1187.json), 2 warnings, 7.39s; [61 auth cases](20261018T124832+0800-auth-bcf8ebc9.json), 1 existing browser case deselected, 4 warnings, 37.06s; [8 frontend auth](20261018T124833+0800-frontend-auth-5addb12f.json), [22 preference](20261018T124834+0800-frontend-preferences-d0aa5fd2.json), [48 GA/report contracts](20261018T124836+0800-frontend-ga-88a9fe6a.json). Distinct within this attempt: 248 backend passes and 78 frontend contracts, not added to overlapping historical totals. No failed test run in this implementation attempt; intermediate 173/186/187 successes are retained in the report. Build/full lint/full GA runs were not repeated because application source is unchanged. Zero actual browser screenshots/passes.

[Recovery manifest](stage-b-recovery-manifest.json) pins current changed artifacts and preservation checks. [Main manifest](manifest.json) maintains the current cumulative inventory and prior hash revisions. The unchanged Stage A manifest retains historical Stage A source hashes; newly edited tooling must be checked against the recovery/current manifest, not that earlier source snapshot.

Final archive validation: 74 current artifact hashes, 18 task artifact hashes, 289 protected-file comparisons, 139 documentation links, 49 JSON files, four Python AST parses and five Markdown anchors verified; sensitive-pattern scan and git diff --check passed. An additional ad hoc anchor check initially used the Windows cp1252 default and failed to decode an existing UTF-8 document; rerunning with explicit UTF-8 passed. This was a validation-command encoding issue, not a product or regression-test failure, and changed no source/data bytes.
