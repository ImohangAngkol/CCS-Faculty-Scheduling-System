# Dashboard-first D2: Faculty My Schedule

Implemented **2026-10-21, Asia/Manila** against source baseline `3167cda2bd2d86011b50ea582026a4c39accb529` on `main`, with the existing dirty D1/Phase 4C.2 work retained. **D2 IMPLEMENTED; FOCUSED API, REGRESSIONS, FRONTEND AND SYNTHETIC BROWSER CHECKS PASS.** D2 adds a read-only faculty timetable and authenticated own-schedule endpoint. PostgreSQL provisioning and acceptance remain paused. D3 has not started.

## Objectives and requirements

| ID | Acceptance requirement | Implementation/evidence |
|---|---|---|
| D2-OWN | Session-derived faculty identity, no cross-faculty retrieval or administrator result leakage | Real FastAPI password/session/binding tests; strict own-row response allowlist |
| D2-VIEW | Subject, section, day/time, room, lecture/laboratory and source status | Shared weekly calendar plus responsive assignment details; D2-B01/B11/B12 |
| D2-STATE | Loading, empty, missing, unavailable, stale and denied states | Backend cases, frontend contracts and D2-B01–B10 |
| D2-SOURCE | Proposal labelling, truthful compatibility/freshness | Existing hard-compatibility validator; no invented approval, term or generation date |
| D2-SAFE | Read-only operation and preservation | Source/database/template/RNG assertions and file-hash comparison |

The [D1 report](dashboard-d1-implementation.md), [metadata contract](api/phase-1-metadata.md), [confirmed future workflows](phase-4c-confirmed-scheduling-workflows.md), [academic foundation](phase-4c2-academic-foundation.md) and [documentation standard](DEVELOPMENT_DOCUMENTATION_STANDARD.md) were reviewed. No checked-in standalone dashboard-first review exists; the dashboard-first priorities in the conversation are the planning source. The existing teal/gold theme is retained.

## Exact files created or modified

Application changes:

| Path | Change |
|---|---|
| `backend/main.py` | Registers the faculty schedule router, leaving existing route guards intact. |
| `backend/routers/schedules.py` | Completes the scaffold with authenticated `GET /api/schedules/me` and verified faculty binding. |
| `backend/services/schedule_service.py` | Completes the scaffold with bounded read-only latest-result validation and own-assignment projection. |
| `backend/schemas/schedule.py` | Completes the scaffold with dedicated source/assignment/response schemas. |
| `frontend/src/services/scheduleService.ts` | New cancellable GET and strict runtime response/identity checks. |
| `frontend/src/pages/faculty/MySchedule.tsx` | Replaces the placeholder with a read-only timetable, details, provenance and actionable states. |
| `frontend/src/pages/faculty/Dashboard.tsx` | Updates My Schedule's availability and description; keeps requests/approvals/publication explicitly unavailable. |
| `frontend/src/routes/AppRoutes.tsx` | Routes My Schedule to the real page; removes the unused generic placeholder. |
| `frontend/package.json` | Adds `test:schedule` and `test:schedule:browser`; no dependency or lockfile change. |

Tests and tooling:

| Path | Change |
|---|---|
| `backend/tests/dashboard/conftest.py` | New explicit PostgreSQL/default-engine denial and isolated fixture boundary. |
| `backend/tests/dashboard/test_my_schedule.py` | New real authentication/ownership/source-preservation cases using temporary SQLite and synthetic scheduling resources. |
| `frontend/tests/mySchedule.fixtures.mjs` | New synthetic own-assignment contracts. |
| `frontend/tests/mySchedule.test.mjs` | Five focused transport/contract/security-boundary cases. |
| `frontend/tests/mySchedule.browser.test.mjs` | Thirteen rendered Edge scenarios with an isolated synthetic HTTP API and genuine screenshots. |
| `frontend/tests/dashboardD1.browser.test.mjs` | Updates obsolete My Schedule placeholder/status expectations and supplies a missing-source synthetic response. |
| `frontend/tests/gaMonitoring.browser.test.mjs` | Updates the faculty navigation expectation for the new page and missing-binding boundary. |
| `frontend/tests/auth.browser.integration.mjs` | Isolates the legacy real-auth browser's debugger/frontend targets, disables environment-file loading and owns Vite cleanup. |
| `backend/tests/test_phase4a_auth.py` | Gives that legacy browser fixture a disposable frontend port with matching exact Origin/CORS. Authentication assertions remain unchanged. |
| `docs/testing/dashboard-d2/run_checks.py` | New evidence runner: whitelisted child environment, no credential variables and unique disposable regression roots. |

Documentation/evidence created: this report; `docs/testing/dashboard-d2/preservation-baseline.json`, `initial-backend-attempt.json`, `manifest.json`, timestamped `command.json` records; and four PNGs plus `browser-results.json` under `docs/screenshots/dashboard-d2/20261021T172402405419+0800-browser/`. The manifest enumerates every generated artifact and SHA-256. Existing reports, screenshots and manifests are unchanged.

## Implementation details and API verification

`GET /api/schedules/me` uses the existing real session dependency. It requires the faculty role, an existing account-to-faculty FK record, resolution through the frozen UUID/code registry, and agreement with the normal scheduling faculty's stable UUID and numeric code. Missing/inconsistent bindings fail closed. Numeric code zero is retained. No account, registry or UUID-generation formula is changed.

All query parameters are rejected. Faculty identifiers in headers or a GET body cannot change the session identity; there is no per-faculty schedule URL. The administrator GA APIs remain administrator-only. A successful response contains only schema version, availability, the caller's verified UUID/code, a small source descriptor and that caller's allowlisted assignments. Fitness, analysis, run IDs, history, source paths and other faculty rows are omitted. Existing middleware supplies `Cache-Control: no-store`.

The service reads the existing `routers.genetic_algorithm.LATEST_RESULT_FILE` alias. It never falls back to uploaded/best chromosomes or historical schedules. Reads are limited to 32 MiB, reject duplicate JSON keys/non-finite numbers, and compare file identity, size and modification time before/after reading and after validation. Source replacement yields a retryable sanitized 409. Unsupported/unreadable content yields sanitized 503 without leaking source rows or paths.

Before filtering, the existing `ga_service.validate_saved_result` validates the complete proposal against detached copies of currently loaded scheduling templates. This reuses existing hard-constraint semantics without fitness evaluation, random sampling, repair or storage writes. Any incompatible assignment rejects the source, including an incompatible assignment belonging to somebody else; validation details are never returned to faculty. Explicit non-completed status is rejected. Legacy sources with absent status retain existing latest-result semantics.

| Request/state | Expected and observed result |
|---|---|
| Valid faculty session and valid source | 200, only that faculty's lecture/laboratory rows |
| Valid source without own assignments | 200, `availability=empty`, no rows |
| Missing latest result | 200, `availability=missing`, no rows/timestamp |
| Anonymous, forged, expired, revoked or disabled session | 401 before source access |
| Administrator or missing/invalid faculty binding | 403 before source access |
| Client query selector | 400, no assignments |
| Different faculty URL | 404; no selector route exists |
| Incompatible/non-completed or concurrently replaced source | 409, no assignments |
| Malformed/unreadable/unsupported source | 503, no assignments |

Legacy files do not consistently record their original full input fingerprint or academic term. Therefore `freshness=not_recorded` is explicit. Compatibility with loaded inputs is not proof that the source is the newest institutional schedule. `saved_at` is file modification time, not generation, approval or publication time. The page always says **GA-generated proposal**.

The frontend uses `AuthContext` and the existing cookie/session transport. No faculty-side `GAProvider` or administrator result fetch is introduced. Strict response parsing checks returned UUID/code and source/availability consistency before rendering. Cancellation and request keys prevent old responses from appearing after navigation, refresh or identity changes. Shared `WeeklySchedule` and existing weekday labels render the timetable; a responsive details list exposes full fields on narrow screens. Missing title/room is labelled unknown rather than invented. There are no schedule mutation controls.

## Backend test results

Runtime: Windows, Python **3.14.2**, SQLite **3.50.4**, project virtual environment. Exact command arrays, cwd, start/end ISO timestamps, elapsed durations and exit codes are retained in the linked command records. The runner removes all database URLs and approval/credential environment variables from children. It never reads `.env` credentials.

- **PASS: 29 focused API cases**, 0 failed/skipped, pytest 13.00 s, 17:21:30–17:21:46 +08:00. [Recorded command](testing/dashboard-d2/20261021T172130961419+0800-backend/command.json).
- **PASS: 46 existing authentication/GA control regression cases**, 0 failed/skipped, pytest 46.98 s, 17:36:49–17:37:39 +08:00. This includes the real HTTP authentication browser wrapper and seven GA lifecycle/control cases. [Final recorded command](testing/dashboard-d2/20261021T173649821170+0800-backend-regressions/command.json). Earlier failures are retained below.

The 29 new cases run the actual FastAPI app in-process through ASGI TestClient, real Argon2 password verification, real cookies/session lookups, revocation/expiry and account ownership. Only the database dependency is redirected to temporary SQLite; principals are not bypassed. Faculty registry and GA templates are synthetic. The existing hard-compatibility validator executes normally. Tests deny any PostgreSQL/default identity-engine connection. Repeated GETs preserve synthetic source bytes, identity/session rows, scheduling templates and Python/NumPy RNG states; fitness calls are forbidden.

The separate legacy authentication suite also uses temporary SQLite and preference/settings files. Its browser wrapper starts a real loopback FastAPI server against that temporary storage. The GA control cases use private temporary markers and explicit administrator test principals; they do not test credentials or execute evolution. This selection does not establish a full GA-suite pass or a new GA-quality evaluation. Existing lower-penalty-is-better fitness semantics are unchanged.

## Frontend tests, build and lint

Runtime: Node **v24.11.1**, Vite **8.2.2**. Run from repository root through `.venv/Scripts/python.exe -B docs/testing/dashboard-d2/run_checks.py <check>`; child cwd and exact command arrays are in each artifact.

| Check | Result | Evidence |
|---|---|---|
| `contracts` | **PASS: 91 cases**, 5 D2 + 86 existing, 0 failed/skipped | [Command](testing/dashboard-d2/20261021T172823919102+0800-contracts/command.json) |
| `build` | **PASS**, TypeScript and production build, 215 modules | [Command](testing/dashboard-d2/20261021T172826162090+0800-build/command.json) |
| `lint` | **PASS**, no findings in the four changed/new TS/TSX modules | [Command](testing/dashboard-d2/20261021T172827574821+0800-lint/command.json) |
| `browser` | **PASS: 13 D2 scenarios + one parent wrapper** | [Command](testing/dashboard-d2/20261021T172402405419+0800-browser/command.json) |
| `d1-browser` | **PASS: 16 D1 scenarios + one parent wrapper** | [Command](testing/dashboard-d2/20261021T172846407072+0800-d1-browser/command.json) |
| `ga-browser` | **PASS: 51 existing GA scenarios + one parent wrapper** | [Command](testing/dashboard-d2/20261021T172845983460+0800-ga-browser/command.json) |

Parent wrappers are not additional functional/security cases. Full-project lint was not run. The existing build chunk-size warning remains: main JS **838.32 kB**, gzip **236.65 kB**, above 500 kB. Focused backend execution reports Starlette/httpx and AnyIO deprecations; the legacy suite additionally exercises offline Alembic rendering and its existing `path_separator` warning. Offline SQL rendering is not a live migration.

## Browser acceptance and screenshots

D2, D1 and GA dashboard checks ran actual React rendering in headless **Microsoft Edge 155.0.4283.62**, driven through Node/CDP with private temporary profiles. D2 used owned ephemeral frontend/API/debug ports and a synthetic HTTP server. It made **zero mutation, faculty-selector or administrator-result requests**, with no runtime errors. This is genuine browser/UI evidence with synthetic responses; it does not independently establish FastAPI authorization. The 29 ASGI cases provide that separate authorization evidence, with SQLite rather than PostgreSQL.

All D2 scenarios and actual timestamps are in [browser-results.json](screenshots/dashboard-d2/20261021T172402405419+0800-browser/browser-results.json). Tests assert expected outcomes for loading; own lecture/lab rows; refresh; missing versus empty; unavailable retry; stale rejection/recovery; denied access; missing/mismatched binding; anonymous/wrong-role navigation; expired session; unknown fields; mobile containment; and navigation during delayed responses.

These four original PNGs were visually inspected for correctness/privacy. Only synthetic records and the target application appear; no credentials, cookies, developer tools or real faculty records are captured. No image was generated, redacted or edited.

| Scenario | Original capture | Time (+08:00) / viewport |
|---|---|---|
| D2-B01 | [Own proposal timetable](screenshots/dashboard-d2/20261021T172402405419+0800-browser/D2-B01-own-proposal-timetable.png) | 17:24:05.171, 1366×1100 |
| D2-B03 | [No own assignments](screenshots/dashboard-d2/20261021T172402405419+0800-browser/D2-B03-no-own-assignments.png) | 17:24:06.017, 1366×1100 |
| D2-B05 | [Stale source](screenshots/dashboard-d2/20261021T172402405419+0800-browser/D2-B05-stale-source.png) | 17:24:06.734, 1366×1100 |
| D2-B12 | [Mobile assignment details](screenshots/dashboard-d2/20261021T172402405419+0800-browser/D2-B12-mobile-assignment-details.png) | 17:24:08.671, 390×844 |

Capture URL: `http://localhost:53902/faculty/schedule`, isolated Vite development fixture, 2026-10-21. The mobile capture is scrolled to details; the wide weekly calendar scrolls within its container. Browser refresh verifies fixture rendering, not real database persistence. Existing D1 screenshots/reports remain historical; changed test-source hashes supersede their historical source snapshots without rewriting that evidence.

## Bugs found, failed attempts and fixes

1. The first focused backend attempt produced **23 passed, 5 failed**. Windows/Python 3.14 `fstat`/`Path.stat` creation/change-time differences falsely marked stable overwritten files as changed. The guard now compares device/inode/size/modification time, with a new repeated-overwrite regression. The final 29 cases pass. [Sanitized initial summary](testing/dashboard-d2/initial-backend-attempt.json); initial wall-clock timestamps were not recorded and are not reconstructed.
2. The first legacy backend regression run produced **45 passed, 1 failed**: existing Edge authentication rendering timed out at `Runtime.enable` inside the sandbox. [Original record](testing/dashboard-d2/20261021T172822613724+0800-backend-regressions/command.json).
3. Its first outside-sandbox rerun produced **46 setup errors**, all caused by access denied to an earlier sandbox-owned pytest temporary root. [Original record](testing/dashboard-d2/20261021T172958938888+0800-backend-regressions/command.json). The evidence runner now supplies a unique, previously absent `--basetemp`; it does not delete/reset the old root or change its ACLs.
4. With the temporary-root issue resolved, the legacy wrapper still failed before login (**45 passed, 1 failed**). [Record](testing/dashboard-d2/20261021T173101459491+0800-backend-regressions/command.json). Its fixed debugger and Vite launch were replaced with an owned ephemeral debugger and programmatic Vite. The next run correctly refused the occupied fixed frontend port 5189 (**45 passed, 1 failed**), confirming a collision; [record](testing/dashboard-d2/20261021T173524892874+0800-backend-regressions/command.json). No occupying process was stopped or modified. The Python/Node test fixture now chooses a disposable frontend port and configures matching exact Origin/CORS. This is test infrastructure only; application authentication and authorization rules are unchanged.

The final isolated regression rerun passes all 46 cases, including that real HTTP browser wrapper. The prior missing-login symptom is consistent with the old harness attaching to an unrelated fixed-port target, but the precise earlier page contents were not captured; that attribution remains unconfirmed. The occupied port itself was directly confirmed by Vite's strict-port refusal.

These are scoped D2 implementation/test-infrastructure findings. The historical [system bug report](system-bug-report.md) is preserved, and its original bug totals are not rewritten.

## Database verification and preservation

**PostgreSQL: NOT RUN** by explicit instruction. No PostgreSQL provisioning, connection or migration execution, retained Phase 4B database access or Phase 4C acceptance test occurred. Temporary SQLite authentication/schema tests and legacy offline Alembic rendering provide no PostgreSQL lock, concurrency, rollback, restart or deployment acceptance.

The [preservation baseline](testing/dashboard-d2/preservation-baseline.json) contains **479** pre-D2 file hashes, including the existing dirty files, ignored local scheduling data/artifacts and Git index. The comparison finds **467 byte-identical files**, exactly **12 intended existing-file changes** listed above, no missing files and no unexpected changes. New D2 sources/evidence are listed separately in the [manifest](testing/dashboard-d2/manifest.json).

Protected `backend/data/faculty_preferences.json` retains SHA-256 `72a5f4f239b5cf99cfb6d7159d443375f8496b69c6b3d1d67ad42e449fd2d8a9`; its pre-existing dirty status is unchanged. Faculty identity registry, UUID formulas/account-binding code, GA operators/fitness/RNG/checkpoint code, all existing stored schedules/checkpoints/history, Phase 4B evidence, seven-table Phase 4C.2 implementation/tests/migration, and `.git/index` remain byte-identical. No stage, commit or push was performed. Database contents were not queried, so this is filesystem/source preservation evidence rather than a fresh database audit.

## Known limitations and safe reproduction

The endpoint requires the existing authentication deployment to be configured; D2 does not provision accounts or a database. Current supported saved-result format uses canonical numeric faculty codes. Display-only legacy aliases are not newly interpreted as schedule authorization identifiers. A legacy result may be rejected by the existing full hard-compatibility validator; D2 does not repair or overwrite it. A compatible legacy file cannot prove original input freshness, academic year, official publication or Chair approval. Large-file read/validation cost has not been benchmarked. No full application end-to-end D2 browser test against PostgreSQL was run.

To reproduce safely, use the evidence runner's `backend`, `contracts`, `build`, `lint`, `browser`, `d1-browser` and `ga-browser` selections from the repository root. `backend-regressions` additionally runs the legacy isolated authentication/browser and GA control tests. Browser execution requires Edge installed at the existing harness path and permission to run its renderer; the existing GA dashboard harness needs its dedicated localhost frontend port free. Do not launch the normal backend with institutional credentials merely to inspect this page. Test cleanup stops owned servers/browser processes and removes owned browser profiles; pytest's disposable data roots may remain for review. No retained database or schedule cleanup is part of D2.

## Thesis relevance and next milestone

D2-OWN is supported by real credential/session/ownership and no-leak ASGI assertions. D2-VIEW/D2-STATE are supported by contracts and thirteen actual rendered scenarios, including four reviewed screenshots. D2-SAFE is supported by no-write/RNG assertions and the preservation manifest. These demonstrate prototype functionality and negative access handling, not a usability study, performance benchmark, GA-quality evaluation or production deployment certification.

Recommended **D3, subject to a new task**: an administrator GEC/external schedule intake and review page with manual/CSV preview, mapping and discrepancy display, initially using isolated synthetic fixtures where needed. Clearly identify preview-only drafts. Confirmation, durable revisions, hard-constraint activation, Excel support and Chair workflows need their own explicitly scoped backend/persistence/validation acceptance; no mock confirmation should claim a real scheduling constraint. D2 does not implement or activate any of them.
