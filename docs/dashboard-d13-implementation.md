# D13: controlled schedule adjustment application

Implemented and validated 2026-10-24, Asia/Manila, on `main` at D12 baseline `d0d548d8ede489246011ab67e9c85967afc4729b`. **D13 is implemented and verified with isolated fictional institutional providers. Genuine production application remains BLOCKED.** No PostgreSQL connection or migration execution occurred. No staging, commit, push, subsequent milestone or C++ work occurred.

An independently authorized scheduler can preview and apply one current Chair-approved faculty adjustment to a new immutable published version. Faculty see their committed APPLIED outcome and updated own timetable. The original GA result, saved-best, fitness, all existing schedule files, D11 request history and D12 decision remain unchanged.

The [evidence manifest](testing/dashboard-d13/manifest.json) contains the exact source inventory, command records, raw artifact hashes, privacy findings and preservation comparison. The [starting baseline](testing/dashboard-d13/preservation-baseline.json) covers 1,124 files, including the Git index, all 23 academic data paths and retained checkpoints/results. Only the 16 intended existing implementation/test files differ; 1,108 baselined files remain byte-identical, including protected faculty preferences and every original V1/V2 engine source.

## Independent application authority and verified publication source

`application_authority_service.institutional_application_directory()` defaults to `None`. A server-owned guarded directory must supply an ACTIVE `schedule_application` mandate for the exact account UUID, canonical department UUID scopes, policy digest/reference and aware validity timestamps lasting at most 300 seconds. It also supplies an exact faculty/subject/section/year/term department binding. Client flags, ordinary administrator status and Chair status cannot grant application authority. The same actor requires a separate mandate even if already authorized as Chair. Existing session, active-account, Origin and CSRF protection remains in force.

The new `published_schedule_source.institutional_publication_source()` also defaults to `None`. Its guarded `PublicationContext` must identify an explicitly verified published origin, academic year/term, current D10 snapshot, authoritative resource mappings, source/policy references, detached original GA templates, storage session factory and explicit capacity applicability/source. There is no public bootstrap endpoint and no automatic promotion of a GA proposal to an official schedule. A provider that is configured but fails validation causes an unavailable error; it never falls back silently to the GA file.

Production still lacks genuine application/Chair directories, institutional scope bindings, a verified published origin and complete authoritative metadata/trust providers. The fictional test providers are installed only by pytest monkeypatches. No environment variable or API field activates them in deployment.

## Fresh review and complete scheduling validation

Before application, the service verifies the immutable D11 content/event chain, exact faculty owner and active account binding, immutable D12 APPROVE decision/digest, department scope, original approving Chair's current mandate/policy/scope, original assignment and current published revision/year/term. An old approval is never rebased onto a newer publication. Rejected, draft, merely submitted, withdrawn, already applied or stale requests cannot publish.

The review reconstructs the proposed complete schedule while changing only the authorized meeting's day/start/end/room. It reuses D11 availability and half-open conflict checks for every resulting meeting, then performs detached reconstruction through the original `payload_to_chromosome` and `validate_publication` validators. It does not evaluate fitness, consume GA random draws, repair chromosomes or save GA results. Existing qualification/eligibility, teaching-load ceilings, complete offerings, lecture/laboratory hours and continuity, preassignments, fixed sections, room types, faculty/room/section availability and GEC commitments remain hard gates. Adjacent nonoverlapping intervals retain existing semantics. Three-hour laboratory structure is preserved by the original validators.

Capacity is an explicit provider contract because the current room model alone does not establish authoritative capacity. When capacity is applicable, missing/non-integer enrollment or room capacity yields `CAPACITY_METADATA_UNAVAILABLE`; insufficient capacity yields `ROOM_CAPACITY_EXCEEDED`. An explicit sourced `not_applicable` policy is supported. No capacity, enrollment, dates or identities are fabricated.

Fresh D8 issuer/evidence, D9 current-head and independent confirmer, and D10 applicability/snapshot verification run through the existing trusted-snapshot service in the application transaction. Changed/revoked/unavailable trust blocks publication. Separate backend integration tests exercise the actual D8/D9/D10 code with fictional issuers, including evidence loss, issuer loss, confirmer loss and durable revocation after Chair approval. The browser uses a simpler explicitly fictional snapshot provider; it does not prove genuine institutional approval.

Preview returns structured blocking findings and no persisted versions. Apply repeats validation and checks the exact decision UUID/digest, current revision/sequence and constraint digest supplied by the reviewed command. Source, trust and both authorities are rechecked before commit. The original Chair guard, publication guard and application guard remain held through the commit boundary; a focused test observes that ordering.

## Versioning, lifecycle and transaction safety

Three additive tables separate post-GA publication from the GA artifacts:

| Table | Purpose |
|---|---|
| `published_schedule_versions` | Immutable canonical full meeting snapshots, sequence, revision/content digest and previous-version link |
| `published_schedule_heads` | One current version per exact schedule/year/term aggregate |
| `schedule_adjustment_applications` | Immutable application, request/approval links, independent publisher, department, operation key, old/new versions, validation and authority/trust provenance |

The first successful application atomically records a copy of the explicitly verified published origin as version 1, creates version 2, writes the application audit and advances the head. A preview does not adopt the origin. Subsequent applications create version N+1 and retain all earlier versions. The updated schedule is labeled `POST_GA_AUTHORIZED_ADJUSTMENT`; original fitness is not attributed to it or recalculated.

Canonical payload/digest checks validate the complete version chain, the D11/D12 links and exactly one authorized meeting delta. Unaffected assignments must match byte-for-byte canonical content. The application record binds old/new revisions, academic term, D12 digest, fresh D10 heads/digest, policy/scope references, publisher and timestamp. Historical reads verify retained integrity but do not claim current institutional constraint certification.

The immutable D11 row and CREATED/SUBMITTED events remain unchanged. The D12 decision still says `APPROVED_PENDING_APPLICATION`. A separate read projection exposes APPLIED only when a committed application record and version lineage verify. Pending previews show PENDING_APPLICATION or APPLICATION_BLOCKED. The UI's busy/confirmation state does not claim a durable APPLYING event. Failed attempts return structured HTTP/preview explanations and roll back all publication writes; D13 does not persist a separate failed-attempt ledger.

On SQLite tests, `BEGIN IMMEDIATE`, uniqueness, head compare-and-swap and equivalent fixture triggers protect the transaction. PostgreSQL code additionally specifies account/request/head row locks and the existing timeout/trust-lock boundaries, but those database semantics have not been executed on PostgreSQL. Two distinct publisher actors using independent concurrent SQLite sessions produce exactly one application. Concurrent actual HTTP attempts also produce one success and one 409. Exact same-actor/same-operation replay returns the retained result; reusing a key for a different command or issuing a second application operation is rejected. A competing approval against the old revision becomes stale; a newly created request against the current version can produce version 3.

Injected failure after application insertion proves that versions, head and application roll back together, then retry can succeed. Authority revocation after insertion also rolls back. A fresh Python process authenticates a faculty session and retrieves the durable APPLIED record and unchanged two-event request history from owned SQLite storage.

## Backend and UI interfaces

All application routes require independent application authority and server-side scope:

| Endpoint | Behavior |
|---|---|
| `GET /api/schedule-applications/access` | Current capability and verified department scopes |
| `GET /api/schedule-applications` | Approved pending queue; optional `include_applied=true` |
| `GET /api/schedule-applications/{id}/preview` | Fresh before/after, findings, pinned command and eligibility; no version writes |
| `GET /api/schedule-applications/{id}/status` | Current preview/status projection |
| `GET /api/schedule-applications/{id}/history` | Verified immutable successful application audit |
| `POST /api/schedule-applications/{id}/apply` | Strict command, fresh checks and atomic version application |
| `GET /api/schedule-applications/versions` | Current/preserved versions; optional exact `version_id`; department-filtered read-only meetings |

The `/schedule-applications` React page uses server capability checks, shared account navigation, loading/error/retry states, approved queue, Chair explanation, before/after comparison, complete validation findings, explicit confirmation, committed application audit and shared weekly timetable history. It uses the existing teal/gold theme. The route is capability-based; the account's `admin` string alone is insufficient. Imported/request text is rendered as React text, without raw HTML injection.

Faculty request history now distinguishes immutable approval from committed application and shows application date/version/audit. `/api/schedules/me` preserves the existing UUID/code ownership gate and rejects client selectors. A configured published source returns schema version 2 with only the bound faculty's assignments, source/version/year/term and `NOT_RECHECKED_READ_ONLY`. When no publication provider is configured, the existing schema-1 GA-generated proposal behavior remains. The shared calendar renders the new published timetable without exposing other faculty's assignments, the whole GA result, fitness or private administrative data.

## Exact implementation inventory

Created 21 application/test files:

- `backend/application_models.py`
- `backend/migrations/versions/d13_0001_schedule_application.py`
- `backend/routers/schedule_applications.py`
- `backend/schemas/schedule_applications.py`
- `backend/services/application_authority_service.py`
- `backend/services/published_schedule_source.py`
- `backend/services/published_schedule_views.py`
- `backend/services/schedule_application_service.py`
- `backend/services/schedule_version_store.py`
- `backend/tests/dashboard/application_restart_child.py`
- `backend/tests/dashboard/application_sqlite.py`
- `backend/tests/dashboard/test_application_migration.py`
- `backend/tests/dashboard/test_application_trust.py`
- `backend/tests/dashboard/test_applications_live.py`
- `backend/tests/dashboard/test_schedule_applications.py`
- `frontend/src/api/scheduleApplicationModel.ts`
- `frontend/src/api/scheduleApplications.ts`
- `frontend/src/components/common/ApplicationReviewLink.tsx`
- `frontend/src/pages/admin/ScheduleApplications.tsx`
- `frontend/tests/scheduleApplications.live.mjs`
- `frontend/tests/scheduleApplications.test.mjs`

Modified 16 existing implementation/test files:

- `backend/main.py` — register protected application routes.
- `backend/migrations/env.py` — additive application metadata only.
- `backend/routers/adjustments.py` — include verified application in own status.
- `backend/routers/schedules.py` — own published timetable projection with preserved identity checks.
- `backend/schemas/schedule.py` — additive schema-2 published source DTOs.
- `backend/services/adjustment_schedule_service.py` — use configured current published source; allow complete validation of unchanged rows without changing default proposal rules.
- `backend/services/adjustment_service.py` — project committed application alongside immutable approval/history.
- `backend/tests/academic/test_academic_foundation.py` — expected additive Alembic head/metadata; seven-table foundation unchanged.
- `backend/tests/dashboard/test_adjustments.py` — install application tables/guards in owned SQLite fixture.
- `frontend/src/api/adjustments.ts` — accept APPLIED only with verified-shape application and approval provenance.
- `frontend/src/components/common/AccountMenu.tsx` — capability-gated application navigation.
- `frontend/src/pages/faculty/AdjustmentRequests.tsx` — applied date/version/status and accurate lifecycle wording.
- `frontend/src/pages/faculty/MySchedule.tsx` — published provenance and shared own timetable.
- `frontend/src/routes/AppRoutes.tsx` — authenticated application page.
- `frontend/src/services/scheduleService.ts` — strict schema-1/schema-2 union and own-identity validation.
- `frontend/tests/mySchedule.browser.test.mjs` — allow only the new read-only capability probe in the existing request allowlist.

Created documentation/evidence: this report; `docs/testing/dashboard-d13/{preservation-baseline.json,run_checks.py,audit_evidence.py,manifest.json}`; uniquely timestamped command records; and original captures/browser-results under `docs/screenshots/dashboard-d13/`. The manifest enumerates and hashes each artifact individually, excluding itself. Existing historical evidence was not replaced.

## Fresh validation results

All results below were executed during D13, rather than copied from historical reports. Commands use a whitelisted child environment without database URLs, passwords or approval flags. Each command's exact argv, cwd, elapsed time, timestamp, scope and sanitized output is retained in the manifest's `latest_commands` link.

| Runner key | Final fresh result |
|---|---|
| `focused` | 47 passed: actual FastAPI/authentication/SQLite application, real-trust integration and offline migration SQL |
| `d12-backend` | 42 passed |
| `d11-backend` | 33 passed |
| `backend` | 327 passed: D2–D9 backend regressions |
| `backend-regressions` | 46 passed: existing authentication/control regressions |
| `academic-offline` | 85 passed |
| `ga-resource-regressions` | 3 passed |
| `v1-fixtures` | 4 passed: actual current-release original-operator checkpoint continuation fixtures |
| `v2-engine` | 30 passed |
| `v2-api` | 18 passed |
| `contracts` | 205 passed, including 16 new D13 contracts |
| `d13-live` | 14 D13 live HTTP browser scenarios passed; 1 pytest wrapper; Node reports 15 including parent |
| `d12-live` | 12 real HTTP scenarios passed; 1 pytest wrapper |
| `d11-live` | 12 real HTTP scenarios passed; 1 pytest wrapper |
| `v2-live` | 6 real HTTP scenarios passed; 1 pytest wrapper |
| `live` | 16 D9 real HTTP scenarios across blocked and fictional-authorized modes; 2 pytest wrappers |
| `browser-regressions` | 125 D1–D8 synthetic HTTP browser scenarios passed; Node reports 133 including parents |
| `ga-browser` | 51 GA synthetic HTTP scenarios passed; Node reports 52 including parent |
| `v2-browser` | 12 synthetic V2 HTTP scenarios passed; Node reports 13 including parent |
| `build` | TypeScript and production Vite build passed |
| `lint` | Focused ESLint passed, zero errors/warnings |
| `publication-preservation` | 1 focused existing lifecycle test rerun with added exact RNG-state preservation assertion |

Reproduction pattern from repository root: `.\.venv\Scripts\python.exe -B docs/testing/dashboard-d13/run_checks.py <runner-key>`. The runner recursively reuses reviewed previous command definitions, redirects all new command evidence to D13 and only enables screenshot output for the D13 live group. Browser runs require the supported owned Edge/CDP process access; no existing development session is reused.

The final focused suite reports four warning occurrences: Starlette's existing httpx TestClient deprecation, AnyIO's existing BlockingPortal alias deprecation, and the existing Alembic `prepend_sys_path`/missing `path_separator` warning twice during offline SQL rendering. Build warnings are the existing ineffective mixed dynamic/static import for `externalReadiness.ts` and the bundle exceeding 500 kB. No warning-suppression or unrelated dependency/settings change was made.

## Actual browser evidence and retained failures

Final actual browser evidence is [20261024T160014331704+0800-d13-live](screenshots/dashboard-d13/20261024T160014331704+0800-d13-live/browser-results.json), Edge `155.0.4283.62`, Node `v24.11.1`, desktop 1366x1100 and mobile 390x844. All 14 scenarios passed; no uncaught runtime errors remained. Six final screenshots show valid preview, injected rollback, committed application, faculty published timetable, injected trust loss and preserved mobile version. Eighteen screenshots across all four attempts are retained, with 13 unique raw images; original images were visually reviewed or compared byte-identically to reviewed originals. Browser timestamps, actual local URLs and viewports are recorded separately from hashes.

These are real React/Edge HTTP calls to owned FastAPI with real sessions, CSRF, SQLite persistence and transactions. Publishers, Chairs, departments, published schedules, capacity and snapshot providers are fictional. Injected persistence/trust faults are labeled as fixture injections. They are distinct from synthetic intercepted HTTP regression tests and from the separate backend tests of actual D8/D9/D10 validation code. No screenshot establishes real institutional approval or PostgreSQL correctness.

Six nonzero command records remain retained:

| Attempt | Finding and correction |
|---|---|
| `20261024T153449458120+0800-focused` | 31 passed, 1 failed: stale assignment test omitted the correct fail-closed 404 from expected statuses; corrected assertion. |
| `20261024T154102533237+0800-focused` | 37 passed, 5 fixture errors: real-trust tests omitted the imported D12 isolate fixture; imported it so the genuine test ledger boundary is used. |
| `20261024T155152830546+0800-focused` | 45 passed, 1 failed: fresh-process test retained the D12 `schedule_changed=false` assertion after successful application; changed expected value to true. |
| `20261024T154602177842+0800-d13-live` | 9 scenarios passed, 5 failed; Node also counted the parent failure. Initial later-login cascade lacked uncaught-exception details. |
| `20261024T155023836616+0800-d13-live` | Same scenario results with retained runtime stack: the D2 privacy fixture deliberately omitted `history`, while the existing admin Dashboard calls `gaData.history.map`. D13's owned admin HTTP fixture now supplies empty typed history/analysis arrays; no GA file, admin Dashboard or engine source changed. |
| `20261024T155728449437+0800-d13-live` | 11 scenarios passed, 3 failed; Node also counted parent failure. The trust-loss test incorrectly waited for a review panel that the UI clears on denial; it now waits for the denial. The unremoved injected marker caused the dependent 422 results. No timeout increase, test deletion or application bypass was used. |

Intermediate focused runs of 42 and 46 passes are also retained. The final 47-pass suite adds commit-guard lifetime coverage. Final results supersede earlier failures; they do not erase them.

## Migration, preservation and remaining limitations

`d13_0001` follows `d12_0001`, adds only the three publication tables and append-only/lineage/application/head-transition guards, and refuses downgrade when any publication history remains. PostgreSQL upgrade/downgrade SQL was rendered offline; the actual seven academic foundation tables and earlier migrations were not rewritten. SQLite fixture equivalents exercise guards and rollback, but do not establish PostgreSQL locking, triggers, privileges or concurrent transaction behavior.

The 17 Phase4C PostgreSQL tests remain unverified. D9–D13 PostgreSQL migration and online acceptance remain unverified. No production/disposable PostgreSQL connection, provisioning or database operation occurred. Deployment requires separate target safety approval, migration execution and PostgreSQL acceptance; unmigrated decision-aware storage fails closed rather than silently omitting application history.

All 23 academic data files, stable UUID/code mappings, protected preferences, original GA operators/fitness/scoring/RNG/elitism/V1/V2 semantics, checkpoints, saved-best, historical schedule files and D1–D12 evidence remain byte-identical to the starting baseline. There is no fingerprint bypass or checkpoint reinterpretation. The six historical incompatible checkpoint artifacts retain their accepted pre-existing limitation and unchanged bytes; current-release V1 continuation tests passed.

Privacy inspection scans complete and truncated encoded receipts, sensitive assignments/headers, credential URIs, bearer values, private keys, decoded JSON/log strings and locally compared private faculty names without exporting them. PNG CRC and embedded text/EXIF metadata are checked in addition to original-image review. No raw database, HAR, session payload or actual institutional row is archived. The manifest records final findings and independently verifies every included raw hash; hashes alone do not prove authority or correctness. Git whitespace checks passed with existing LF/CRLF informational notices. HEAD, origin tracking reference and index remain at the starting baseline; the protected preference modification remains local and untouched.

Remaining functional limits are explicit: no durable failed-attempt ledger, appeal/replacement of final decisions, automatic rebasing, public initial publication/promote-GA action, email notification, automatic GA run or fitness recalculation. Queue, source and history bounds are 1,000 and fail closed when exceeded. The application API requires the current verified published aggregate; it does not combine unrelated schedules or fabricate cross-term identity mappings.

Recommended next action is review of this implementation/evidence before a separately authorized Git checkpoint. Production activation additionally requires genuine guarded institutional authority/source/metadata providers and separately approved PostgreSQL migration/transaction/concurrency acceptance. D13 ends here; no subsequent milestone was started.


## Authorized D13 Git checkpoint review

The separate checkpoint request authorized two commits: 37 implementation/test files and 60 documentation/evidence files, including the manifest. A fresh fetch confirmed `origin/main` still matched the D12 baseline before staging. All 96 original artifact hashes were checked before this documentation-only checkpoint annotation. All 97 proposed Git-bound files were reviewed; six earlier nonzero command records and all 18 original screenshots (13 unique reviewed images) remain retained. No privacy redaction was required. The protected preference modification is excluded. No application or academic-data bytes were changed during checkpoint preparation.

This checkpoint reviews recorded D13 results; it does not rerun application tests, browser scenarios, build or lint. Privacy, preservation, evidence integrity and Git whitespace/index checks are checkpoint checks, separate from the original acceptance runs. The manifest retains the original validation timestamp and historical pre-checkpoint preservation findings. The historical `audit_evidence.py` deliberately requires the pre-checkpoint HEAD and index; do not rerun it after committing as though it were a current acceptance runner.

For cross-platform verification, each artifact retains its raw working-file `sha256`/`bytes` and also records `git_blob_sha1`, `git_blob_sha256` and `git_blob_bytes` for Git's clean representation. Git's existing `core.autocrlf=true` normalizes CRLF in 50 text artifacts; this changes repository blob bytes without changing working application files or test results. The report's hash is refreshed for this annotation. The manifest excludes itself from the artifact list. Validate committed blobs against `git_blob_sha256`; validate this retained working tree against `sha256`. Neither hash convention establishes institutional authority.

Production institutional application remains BLOCKED without genuine guarded providers. The 17 Phase4C PostgreSQL tests and D9-D13 online PostgreSQL acceptance remain unverified. No PostgreSQL operation or subsequent development is part of the checkpoint.
