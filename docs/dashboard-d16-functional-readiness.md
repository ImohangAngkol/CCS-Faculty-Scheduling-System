# D16: functional readiness and end-to-end integration

Verified 2026-10-25, Asia/Manila, on `main` at `2de39fb92eed6ac68036f45b1c82c8fb5fafe791`. **PASS for the isolated fictional demonstration scope; production institutional activation remains BLOCKED.** Two reproduced UI defects were fixed. No backend application, algorithm, migration, academic dataset or production authority implementation changed.

The repeatable demonstration uses actual React, Edge, FastAPI authentication/CSRF, file-backed SQLite, original constrained generation, durable requests, independent fictional Chair decisions and atomic versioned application. Resource preparation and initial GEC confirmation happen through existing test fixtures/services. Initial publication is an explicit test-only provider handoff; there is still no production GA-proposal promotion API. This is not a claim that institutional resource preparation and initial publication are complete self-service UI workflows.

See the [manifest](testing/dashboard-d16/manifest.json) for the exact changed/new path inventory, raw hashes, command records, earlier failures, browser observations, preservation and privacy findings. [D14](dashboard-d14-acceptance.md) supplies the reused continuous fixture; [D15](dashboard-d15-postgresql-acceptance.md) supplies historical disposable PostgreSQL acceptance, not new D16 executions.

## Requirements, inspection and readiness matrix

Read the README, roadmap, [bug report](system-bug-report.md), [documentation standard](DEVELOPMENT_DOCUMENTATION_STANDARD.md), D1-D15 report boundaries, actual frontend routes/layouts/capability links, API DTOs, FastAPI inclusion/authentication dependencies, academic repository/import planner, model/migration chain, provider contracts and existing continuous integration tests. A page or endpoint alone was not counted as verification. WORKING means the specified fictional/test scope only; BLOCKED and INCOMPLETE are explicit limitations.

| Feature | Status | Evidence and practical boundary |
|---|---|---|
| Login, logout, session recovery and role/owner checks | WORKING | Fresh auth/control tests and live browser login/logout/denial; genuine authentication, no principal bypass in D16 journeys. |
| Faculty dashboard/profile and subject catalog | WORKING | D1 synthetic HTTP browser regressions, metadata/contracts and live subject view. Profile is read-only metadata. |
| Faculty preferences | WORKING | Real HTTP save/full reload in owned temporary storage; invalid input and cross-owner tests. Production preferences untouched. |
| Faculty own timetable and applied status/history | WORKING | Live generated own view, APPLIED request and version-2 timetable; foreign faculty reads denied. |
| Faculty draft/validate/submit/withdraw requests | WORKING | D11 and new generated-source negative tests; immutable original content/history. |
| Chair department filtering while a request is pending | FIXED | Deliberately held real HTTP filter request reproduced stale actionable rows; final D16-L03 verifies clearing and D16-F01 screenshot shows loading without stale rows. |
| Chair approve/reject and immutable decision history | WORKING | D12 tests and live independent approval/rejection. Approval does not publish. |
| Application preview, rollback, retry and concurrent application | WORKING | D13 tests; live injected rollback plus two real competing requests, one success/one conflict. |
| Published history after a full page reload with no pending requests | FIXED | Previously absent until opening a request; final D16-L06 and D16-F02 capture show both versions without a queue selection. |
| History read failure/retry independent of queue | WORKING | D16-F03 injects a FastAPI history-service failure: authorized queue remains usable, retry restores history and clears the error. |
| GEC manual/CSV/XLSX intake, review calendar and reconciliation | WORKING | Fresh 327-case backend selection and D3-D8 synthetic HTTP browser regressions. Temporary review is not confirmation. |
| GEC review handoff/print CSS | WORKING | Existing frontend/browser regression fixture; native print dialog/physical output NOT TESTED in D16. |
| Fictional durable GEC confirmation and revision trust | WORKING | Real API fixture confirmation, live ledger inspection and backend confirmation/evidence tests. Initial confirmation is fixture-prepared, not created by D16 browser UI. |
| V2 constrained generation, schedule and original fitness | WORKING | Actual live UI generation, backend kernel/API tests; complete current confirmation-head checks and original operators preserved. |
| V1 current-release creation/continuation | WORKING | Four actual V1 fixture tests; strict fingerprints and existing compatibility policy unchanged. |
| GA monitoring, saved/history/fitness viewers | WORKING | 51 synthetic HTTP GA browser scenarios and contracts. No production-sized GA performance claim. |
| Persistence across reload/reconnection/fresh login | WORKING | Browser reload, owned engine pool disposal/new TestClient login and separate read-only Python/SQLite row-count verification. |
| Academic identity foundation and import planning | WORKING | 85 offline academic cases; seven-table model, read-only repository and identity-only dry-run planner inspected. |
| End-user academic resource CRUD/import-to-runtime catalog | INCOMPLETE | Current subject/faculty/room pages are viewers. Phase4C foundation is not a complete catalog-management UI or an automatically activated GA source. Fictional fixture prepares explicit resources instead. |
| Initial GA proposal to first published source through production UI | INCOMPLETE | Existing guarded provider boundary requires an independently authorized published source. D16 uses the existing explicit fictional handoff; no automatic promotion or new policy invented. |
| Genuine GEC issuer/confirmation, complete term/resource catalog, Chair and publisher mandates | BLOCKED | Existing institutional providers are unconfigured. Account role alone cannot replace them. No demo provider installed in deployment. |
| New PostgreSQL acceptance | NOT TESTED | D15's 17+10 recorded passes remain historical and byte-identical; no D16 PostgreSQL connection or database operation. |
| Full backend process restart with production providers, physical outage/crash recovery | NOT TESTED | Pool reconnection, fresh clients, separate read-only process and controlled owned HTTP shutdown tested; these do not prove production process/crash recovery. |
| Native print, other browsers/platforms, load/quality studies and deployment | NOT TESTED | No claims from the small fictional demonstration. |

No newly inspected target page is merely an empty placeholder. The material gaps are resource-management and independent authority/publication integration, rather than missing timetable/request/decision/application screens.

## Confirmed defects and corrections

**D16-F01: stale actionable Chair queue during filter loading.** In `frontend/src/pages/chair/Requests.tsx`, toggling the final-decisions filter set loading but retained the old queue. A browser interception held the real outgoing queue request without inventing a response; the old `SYN101 / SYN-A` button remained actionable. The first application reproduction failed at D16-L03. Filter changes now clear queue/detail/confirmation and old messages; rows render only after loading completes. The same stale-row clearing is applied to the applications page's filter/reload path. Server-side authorization and decision semantics are unchanged. This was a display/synchronization defect, not evidence of an authorization bypass.

**D16-F02: published history disappeared after navigation/reload.** `frontend/src/pages/admin/ScheduleApplications.tsx` fetched history only inside `open(request)`. Once no pending request remained, a fresh page had no visible history. After F01 passed, the next browser reproduction failed at D16-L06 waiting for history after navigation. The page now checks access, reads the queue and independently reads department-filtered versions on entry/reload. A history failure has its own retry state and does not claim empty history or revoke a successfully loaded queue. `frontend/src/api/scheduleApplications.ts` forwards an optional AbortSignal so a superseded page read cannot populate the next view. No new endpoint, permission or publication operation was introduced.

Two new frontend contracts cover independent history cancellation propagation and cancellation/denial/unavailability without a fabricated empty success. The new browser tests cover F01, F02 and the new history-failure branch against live FastAPI, with fault injection explicitly confined to the owned fixture. There were no reproduced backend scheduling defects requiring application changes.

## Isolated journey, data and storage

The D16 fixture composes `tests.dashboard.test_system_acceptance.system`, which already composes D9-D13 service fixtures. Explicit fictional resources include three bound faculty identities, two subjects/sections, lecture/laboratory rooms, term/catalog mappings, capacity/enrollment policy, one external Monday section commitment and independent fictional confirmer, Chair and publisher mandates. No identity is inferred from a private name or row position. Authentication uses real password verification, sessions and Origin/CSRF; fixture credentials travel privately over child stdin and are never archived.

Real browser sequence: anonymous denial; faculty preference save/reload; administrator subject/ledger review; actual V2 generation and analysis; explicit owned fictional publication handoff; faculty validation/draft/submission; Chair filter/approval; scheduler history-error retry, complete validation, injected rollback/recovery and new version; faculty APPLIED history/timetable; foreign-owner denial; rejection; current-revision request; trust failure; competing application; mobile history; ordinary-account denial; empty faculty timetable; controlled owned backend shutdown/retry UI. The final record has **21 scenarios**, one Node parent and one pytest wrapper. Parent/wrapper counts are not extra acceptance scenarios.

The new backend suite adds three tests:

- `test_published_journey_survives_pool_restart_fresh_process_and_login`: performs actual generation/approval/application, disposes the owned SQLite engine pool, logs in through a fresh TestClient, compares the exact own timetable and APPLIED history, and independently checks durable version/head/application/decision counts from a new Python process using SQLite `mode=ro` plus `query_only=ON`. It also verifies original generated bytes and RNG state after application/reads.
- `test_generated_request_rejects_conflict_duplicate_and_stale_replay`: invalid reversed times, duplicate active proposal and stale submission are rejected while the submitted request survives.
- `test_independent_authorities_can_be_revoked_without_enabling_fallback`: a revoked fictional application grant denies access/preview and writes no versions; restoring that same owned fixture grant permits the actual application.

SQLite stores and generated outputs/preferences/settings are under newly owned OS-temp roots. Existing fixture aliases isolate writable destinations. Runner children inherit whitelisted OS variables only, with no database URLs, credentials or approval flags. Scheduling imports can read original academic inputs internally; tests use fictional resource objects and suppress import output. No raw database, run checkpoint, cookie/header dump, credential handoff or institutional row payload is copied into evidence. Fixture providers are scoped and restored on teardown; no production switch or bypass was added.

## Fresh verification results

Commands are reproducible as `.\.venv\Scripts\python.exe -B docs/testing/dashboard-d16/run_checks.py <selection>` from the repository root. The runner records the actual expanded command, cwd, times with `+08:00`, duration, exit code, sanitized stdout/stderr and scope in a new `docs/testing/dashboard-d16/<run>/command.json` every time. It excludes historical artifact-writing scripts from its allowed selections. Exact links and environment versions are indexed in the manifest.

| Selection | Final result | Scope |
|---|---:|---|
| `focused` | 3 passed | New persistence/reconnect/negative/authority tests, actual FastAPI/SQLite |
| `continuous` | 6 passed | Existing D14 continuous real-service workflow, including three independent generated samples |
| `backend` | 327 passed | Existing D2-D9 metadata/intake/review/evidence/confirmation |
| `d11-backend` | 33 passed | Requests, ownership, transitions and offline migration SQL |
| `d12-backend` | 42 passed | Chair trust/decisions and offline migration SQL |
| `d13-backend` | 47 passed | Controlled publication, rollback, concurrency, history and offline migration SQL |
| `backend-regressions` | 46 passed | Auth/control; includes an existing real browser auth wrapper |
| `academic-offline` | 85 passed | SQLite/identity planner and offline PostgreSQL SQL, no live PostgreSQL |
| `v1-fixtures` | 4 passed | Actual supported V1 checkpoint creation/continuation |
| `v2-engine` / `v2-api` | 30 / 18 passed | Versioned operators/admission/checkpoint and FastAPI trust/storage |
| `ga-resource-regressions` | 3 passed | Existing preassignment/reset/room/section behavior |
| `contracts` | 207 passed | Node models/API contracts, including two new D16 tests |
| `d16-live` | 21 scenarios passed | Real Edge -> React -> FastAPI -> owned SQLite; actual generation and fictional authority |
| `browser-regressions` | 125 scenarios passed | D1-D8 real Edge with synthetic HTTP responses; eight parent tests excluded |
| `ga-browser` | 51 scenarios passed | Existing real Edge/synthetic HTTP monitoring suite; parent excluded |
| `v2-browser` | 12 scenarios passed | Existing real Edge/synthetic HTTP constrained controls; parent excluded |
| `build` | PASS | `tsc -b && vite build`: TypeScript and production bundle |
| `lint` | PASS | Focused TypeScript/API/page/navigation list, zero errors/warnings |

The listed backend selections total **644 passed pytest cases**, excluding the D16 browser wrapper. One existing auth browser wrapper is included in the 46-case selection; do not add its scenarios again. Synthetic HTTP browser scenarios total **188** and are separate from the **21 actual backend-connected D16 browser scenarios**. Latest selected results have zero failures/skips; earlier failed attempts are retained and excluded from success totals.

Warnings remain: Starlette's deprecated HTTPX TestClient path, AnyIO BlockingPortal alias and Alembic's missing `path_separator`; production build reports existing mixed static/dynamic imports and a >500 kB bundle. These were not hidden, upgraded or cleaned up in D16.

## Failure history and browser evidence

Five nonzero command records remain preserved. Two initial D16 browser runs and one auth regression run failed at DevTools `Runtime.enable` in the restricted sandbox before their browser scenarios executed. The same owned browser harnesses work outside the sandbox; their later runs pass. This is evidence of an environment/automation boundary, not proof of a specific Edge internal cause. No timeout was increased, failing test removed or application behavior changed to accommodate it.

The first unrestricted D16 run reproduced F01 (six scenarios passed, seventh failed). The next reproduced F02 (nine passed, tenth failed). Both retained captures/results remain indexed alongside the successful 20-scenario intermediate run and the final 21-scenario run. These histories are not erased or summed into the final count.

Final real browser: **Edge 155.0.4283.62**, desktop viewport 1366x1100 and mobile 390x844, owned ephemeral loopback app/backend URLs. URL, timestamp, viewport and scenario attribution are in each capture record; queries are intentionally omitted. [Final observations](screenshots/dashboard-d16/20261025T183158054647+0800-d16-live/browser-results.json). Corrected states: [Chair loading](screenshots/dashboard-d16/20261025T183158054647+0800-d16-live/D16-F01-filter-loading.png), [history after reload](screenshots/dashboard-d16/20261025T183158054647+0800-d16-live/D16-F02-history-after-reload.png), [faculty published timetable](screenshots/dashboard-d16/20261025T183158054647+0800-d16-live/D16-L07-faculty-published-timetable.png).

Screenshots are genuine viewport captures, visually reviewed for privacy and labels. Some long-page captures show only the top of a page: the preference importance and mobile empty-state text can be outside the viewport. Their assertions and HTTP reads, rather than those cropped images alone, establish persistence/empty-state results. There is no new native print, full-process production restart, physical outage or production browser evidence.

## Repeating the fictional demonstration

With the existing virtual environment, frontend dependencies, Node and Edge installed, run from the repository root:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-d16/run_checks.py d16-live
```

This is an automated headless demonstration, not an unattended production launch or permanent demo tenant. It provisions only fresh temporary fictional SQLite fixtures, uses existing service APIs, starts owned loopback Vite/Uvicorn and a dedicated Edge profile, runs the sequence and stops only those owned processes. It needs no PostgreSQL variables. In a sandbox that prevents CDP responses, use an authorized local terminal; do not weaken application auth or increase timeouts. Every invocation creates new evidence and refuses screenshot overwrites. Never run a historical D15 write-enabled command against its populated retained database to demonstrate D16.

`focused`, `continuous`, `contracts`, `build`, `lint` and the remaining table selections are individually reproducible through the same runner. A generated proposal becomes a fictional source only through the explicit fixture handoff; reviewing/printing/Chair approval alone never promotes it.

## Exact files and preservation

Existing application files changed:

- `frontend/src/pages/chair/Requests.tsx`: clear stale filter state and hide pending queue rows.
- `frontend/src/pages/admin/ScheduleApplications.tsx`: independent history loading/retry and pending-queue state.
- `frontend/src/api/scheduleApplications.ts`: optional history read cancellation.

New source/tool files:

- `backend/tests/dashboard/test_functional_readiness.py`: three isolated real-service persistence/security cases.
- `backend/tests/dashboard/test_readiness_live.py`: D16 owned HTTP/browser fixture, including test-only history fault.
- `frontend/tests/functionalReadiness.live.mjs`: complete journey, both UI reproductions and recovery assertions/captures.
- `frontend/tests/functionalReadiness.test.mjs`: two history API contracts.
- `docs/testing/dashboard-d16/run_checks.py`: isolated command/evidence runner.
- `docs/testing/dashboard-d16/audit_evidence.py`: read-only validation plus new manifest generation.

New documentation/evidence: this report, `docs/testing/dashboard-d16/preservation-baseline.json`, `manifest.json`, per-command records, browser observations and reviewed PNGs. The manifest contains the **full exact inventory**, including every intermediate failed run; no wildcard is an authorization to stage files.

The 1,371-file pre-test raw baseline includes all 23 academic paths, protected local preferences, original GA/V1/V2/operators/math/RNG/checkpoint compatibility, migrations, six historical checkpoints, saved schedules/history, prior D1-D15 evidence and Git index. Only the three listed frontend files intentionally differ; all other **1,368 baseline paths** remain byte-identical. Protected preferences retain their original local modification; they were not restored, edited, staged or committed. D15's 75 artifact hashes and manifest bytes remain unchanged. No PostgreSQL connection, migration, reset, cleanup, credential or permission operation occurred. SQLite-only fixture table creation is not a PostgreSQL migration.

Final privacy audit scans full/truncated encoded fragments, signed receipts, bearer/header assignments, credential URIs, private keys, decoded JSON/output fields and PNG metadata, and locally compares private faculty names without exporting them. Visual review covers every new PNG. Hashes prove byte identity, not genuine institutional approval. Git whitespace checks pass. No staging, commit, push, D17, C++ optimization or general cleanup was performed. Git status has the three intended frontend modifications, the unchanged protected preference modification and only the inventoried new D16 paths; index and HEAD remain unchanged.

## Remaining work in priority order

1. **Institutional blocker:** obtain authorized term/section/faculty/room/catalog mappings, GEC verification/confirmation policy, current Chair mandates and independent publication mandates. Integrate genuine providers only after separate verification; keep deployment fail-closed.
2. **Incomplete workflow/policy boundary:** agree the first-publication authority and transition contract before adding a production GA-to-publication UI. The fictional handoff is not that policy.
3. **Incomplete resource workflow:** scope a bounded academic-resource preparation/import UI over the existing foundation and planner, with explicit authoritative source/revision semantics. Do not write institutional CSVs or automatically activate the identity planner as GA input.
4. **Operational verification:** independently authorize a fresh disposable deployment rehearsal for whole-process restart/provider restoration, backups and interruption recovery. Preserve D15's populated database; SQLite and D15's historical passes do not replace this work.
5. **Optional demonstration/usability work:** a separately scoped attended local demo launcher, native printing, accessibility/usability and representative scale/quality evaluation. Existing one-command headless demonstration is verified; a persistent interactive demo environment is not claimed.

The isolated fictional integration is demonstrable and its two UI defects are corrected. These findings support thesis prototype workflow claims, not institutional approval, a usability study, global scheduling optimality or production deployment. Stop after D16.
