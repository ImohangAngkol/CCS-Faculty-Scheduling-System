# D11: faculty schedule adjustment requests

Implemented and validated 2026-10-24, Asia/Manila, on `main` against pushed D10 baseline `1b831ebc36e1208c0d4b406b6697ad18df3921d4`.

**The durable workflow works in isolated fictional environments. Production request creation/submission remains blocked until a verified, guarded schedule/term/resource/constraint source is configured and database deployment is separately approved.** No PostgreSQL connection, online migration, schedule alteration, automatic GA run, Chair decision, staging, commit or push occurred. D12 was not implemented.

## Inspected and reused boundaries

Inspected current routes/layouts, real password/session/Origin/CSRF authentication, registered faculty UUID/code binding, D1 profiles/preferences, D2 own-schedule projection, saved-result reconstruction, D8 evidence trust, D9 immutable confirmations, D10 constraint projections/orchestration/storage, SQLAlchemy metadata and Alembic conventions, and existing test/browser fixtures. Initial working tree contained only the protected local preference modification. No AGENTS.md was found.

The existing D2 `bound_faculty` dependency is reused unchanged: an authenticated faculty account must have a registered database binding, a matching identity-registry numeric code and a matching runtime faculty UUID. Neither client IDs nor display names authorize a request. Existing shared API/session utilities, dashboard states, layout, account menu and teal/gold styling are reused.

Legacy latest-result files have no authoritative academic year/semester or durable assignment IDs. D11 does not invent them. `institutional_schedule_source()` defaults to None, with no environment switch, client flag or role checkbox bypass. A deployment adapter must provide a `ReviewSchedule` inside a coherent version/authority guard and keep that guard through the request transaction. It must supply exact term/resource mappings and freshly pinned D10 constraints. A historical D8 VERIFIED display field or expired receipt is insufficient.

The reusable `legacy_projection` adapter reads the existing saved-result format via the D2 bounded/race-checked reader, validates detached copies with the unchanged GA saved-result validator, and accepts explicit server-owned mappings. Numeric GA faculty codes must match their registered UUIDs; an incorrect cross-faculty mapping rejects the source. Subject/section/room IDs come from the supplied catalog, not names or row order. Source revisions and meeting references are canonical content addresses, not new academic identities. Missing rooms/mappings or duplicate meeting keys reject the source. The fictional fixture supplies this catalog explicitly; it is not institutional verification.

Existing Faculty My Schedule remains a read-only V1 latest-result view. D11 adds a navigation link, not a new schedule publication source. No automatic V2 run discovery or production V2-to-faculty source adapter was installed; V2 execution and continuation remain unchanged.

## Durable model and lifecycle

Two new tables use separate `AdjustmentBase` metadata alongside the existing identity, academic and confirmation metadata:

| Table | Stored purpose |
|---|---|
| `faculty_adjustment_requests` | Request UUID, authenticated owner/faculty FKs, creation operation/digest, immutable canonical input and original assignment/review snapshot, content digest, active-proposal uniqueness key, status/version and timestamps |
| `faculty_adjustment_events` | Append-only request/actor/operation references, sequence, previous/event digests, timestamp and immutable event/validation payload |

The request snapshot binds schedule ID/revision, academic year/term, assignment reference, explicit subject/section/room identities, component, original meeting, proposed meeting, justification and pinned GEC digest. It preserves sufficient original comparison information without copying the entire administrator result, chromosome, faculty directory or academic catalog.

Lifecycle: `DRAFT -> SUBMITTED -> WITHDRAWN`, with `DRAFT -> WITHDRAWN` also allowed. SUBMITTED means a recorded proposal awaiting a future D12 workflow; it does not mean Chair approval or that a review queue has been implemented. There are no APPROVED, REJECTED, APPLIED or published transitions. Unknown actions and PUT/PATCH editing are unsupported.

Saved drafts are immutable as a deliberate minimal lifecycle choice. To change one, withdraw it and create another draft. Neither drafts nor submitted content can be silently edited. Repeated requests remain distinguishable by UUID/history. Withdrawal retains history and releases the duplicate-active-proposal key.

Creation, submission and withdrawal are transactional. Per-actor operation UUIDs bind exact commands; retries cannot append duplicate events or reuse an operation for different content. Active duplicate proposals are rejected. Updates use expected versions and compare-and-swap conditions; account state/binding is rechecked in the writing transaction. PostgreSQL row-lock intent is explicit, while SQLite fixtures verify the winning update/rollback behavior. The schema has foreign keys, unique keys and lifecycle/version constraints. The PostgreSQL migration also prevents event updates/deletes, request deletion and mutation of original request content.

One additive migration, `d11_0001` after `d9_0001`, contains frozen SQL and refuses downgrade when request/history rows exist. Startup never creates these tables. No database migration was executed; PostgreSQL upgrade/downgrade SQL was rendered offline only. SQLite fixture tables are created from models with fixture-only append-only history triggers; this is not execution or acceptance of the PostgreSQL migration.

## Authorization, validation and history

All endpoints require the existing genuine faculty authentication/binding dependency. Mutations inherit real Origin/CSRF enforcement. Request queries are filtered by both authenticated user and bound faculty UUID. Another faculty member receives the same 404 for a private request as for a missing one. The backend rejects extra client owner, faculty or approval fields. No administrator full-result endpoint is opened to faculty.

Validation checks exact source revision and academic term, owned assignment existence, recognized room/component, positive half-hour times, unchanged original meeting duration, and faculty/room/section calendar coverage. Coverage permits contiguous adjacent availability blocks. Pairwise meeting and fixed-GEC checks use half-open intervals: adjacency is allowed and overlap is reported. D10 resource IDs are mapped through explicit runtime/catalog mappings into the request-resource namespace; faculty names are not compared for ownership or conflicts.

The proposed complete detached schedule also passes through the original saved-result reconstruction boundary. Existing component continuity, preassignment, fixed-section, resource and academic validation failures become explicit `SCHEDULING_RULE_REVIEW_REQUIRED` findings. No chromosome is repaired or evaluated to obtain a better score. Invalid input, wrong term, stale references and missing/unrecognized required resources reject the operation. Faculty, room, section and confirmed-GEC conflicts remain visible and never receive a conflict-free label.

Conflicting proposals may be recorded as `REQUIRES_REVIEW`; this records a faculty request, not permission to use its meeting. The UI shows every discrepancy and the lack of approval. D12 would require fresh institutional policy, schedule and GEC revalidation before any decision/application. D11 cannot edit a confirmed GEC commitment or write any generated schedule.

Creation and submission events retain their performed validation findings; withdrawal is recorded separately. The service verifies canonical content, contiguous event sequences, digest linkage, actor/request linkage and lifecycle consistency on reads. GET requests do not append audit events or alter history. Staleness is a separate read-time `CURRENT`, `STALE` or `UNAVAILABLE` finding. A changed schedule or GEC digest preserves the original request and blocks new submission. An unavailable source does not prevent reading historical requests or withdrawing an eligible request. It never redirects an old request to a replacement assignment.

## API and faculty dashboard

| Endpoint under `/api/adjustment-requests` | Purpose |
|---|---|
| `GET /assignments` | Own eligible assignments with verified term/source references and recognized rooms |
| `POST /preview` | Nonpersistent validation of a proposed meeting |
| `POST /` | Create immutable DRAFT request after fresh validation |
| `GET /` | Own requests, 25-item pages with UUID cursor |
| `GET /{id}` | Own original/proposed details, current freshness and immutable history |
| `GET /{id}/status`, `GET /{id}/history` | Own status/history projections |
| `POST /{id}/submit` | Versioned, idempotent submission with current source/GEC validation |
| `POST /{id}/withdraw` | Versioned withdrawal preserving history, even if source is unavailable |

`/faculty/adjustments` provides assignment selection, original/proposed comparison, day/time/room inputs, justification, preview findings, draft creation, explicit two-step submission confirmation, paged request list, status badges, details/history, refresh and eligible withdrawal. Faculty sidebar, dashboard and My Schedule link to it. The page has loading, missing-binding, empty, validation-error, unavailable-source, stale and retry states. History remains usable while the current source is blocked. Account changes remount private page state, and imported justification is rendered as text, not HTML. Typed DTOs are validated through the existing authenticated API client.

## Exact source changes

New application files:

- `backend/adjustment_models.py`
- `backend/migrations/versions/d11_0001_faculty_adjustments.py`
- `backend/routers/adjustments.py`
- `backend/schemas/adjustments.py`
- `backend/services/adjustment_schedule_service.py`
- `backend/services/adjustment_service.py`
- `frontend/src/api/adjustments.ts`
- `frontend/src/pages/faculty/AdjustmentRequests.tsx`

Modified existing files:

- `backend/main.py` — register protected D11 router.
- `backend/migrations/env.py` — register the separate additive metadata.
- `backend/tests/academic/test_academic_foundation.py` — explicitly extend expected migration head/metadata to D11; original seven-table and frozen-foundation checks remain intact.
- `frontend/src/routes/AppRoutes.tsx` — faculty-only route.
- `frontend/src/layouts/FacultyLayout.tsx` — navigation/title.
- `frontend/src/pages/faculty/Dashboard.tsx` — honest request link/status.
- `frontend/src/pages/faculty/MySchedule.tsx` — request navigation only.

New tests: `backend/tests/dashboard/test_adjustments.py`, `test_adjustment_migration.py`, `test_adjustments_live.py`, `adjustment_restart_child.py`; `frontend/tests/adjustments.test.mjs`, `adjustments.fixtures.mjs`, `adjustments.live.mjs`.

New documentation/tooling: this report, `docs/testing/dashboard-d11/run_checks.py`, `audit_evidence.py`, the preservation baseline, command records, manifest and genuine screenshots/browser metadata under the D11 evidence directories. Every artifact is individually listed and hashed in the [manifest](testing/dashboard-d11/manifest.json). Protected preferences are an existing local modification, not a D11 source change.

## Fresh validation and evidence attribution

All results below were freshly executed for D11. Earlier failures/reruns are retained and excluded from these latest counts. Parent Node suites and pytest browser wrappers are not extra browser scenarios.

| Check | Latest result | Record |
|---|---|---|
| D11 backend/API/persistence plus offline migration | **33 passed**, 4 warnings | [record](testing/dashboard-d11/20261024T112806724379+0800-focused/command.json) |
| D11 real Edge/FastAPI/SQLite | **12 scenarios passed**, 13 Node checks including parent; 1 pytest wrapper, 2 warnings | [record](testing/dashboard-d11/20261024T112824404727+0800-d11-live/command.json) |
| Frontend API/model contracts | **174 passed**, including 13 new D11 tests and 161 existing | [record](testing/dashboard-d11/20261024T111602591796+0800-contracts/command.json) |
| Existing D2-D9 backend | **327 passed**, 2 warnings | [record](testing/dashboard-d11/20261024T111623984337+0800-backend/command.json) |
| Existing auth/control | **46 passed**, 4 warnings | [record](testing/dashboard-d11/20261024T112310534153+0800-backend-regressions/command.json) |
| Academic offline | **85 passed**, 2 warnings | [record](testing/dashboard-d11/20261024T112003868424+0800-academic-offline/command.json) |
| Original preassignment/resource checks | **3 passed** | [record](testing/dashboard-d11/20261024T112329389467+0800-ga-resource-regressions/command.json) |
| Current supported V1 original-operator fixtures | **4 passed**, actual checkpoint creation and continuation | [record](testing/dashboard-d11/20261024T111847395527+0800-v1-fixtures/command.json) |
| D10 V2 kernel / real ASGI API | **30 / 18 passed**, API has 2 warnings | [kernel](testing/dashboard-d11/20261024T111625122941+0800-v2-engine/command.json), [API](testing/dashboard-d11/20261024T111626423747+0800-v2-api/command.json) |
| D1-D8 synthetic-HTTP Edge regressions | **125 scenarios**, 133 Node checks | [record](testing/dashboard-d11/20261024T112048347226+0800-browser-regressions/command.json) |
| GA monitoring synthetic/intercepted-HTTP Edge | **51 scenarios**, 52 Node checks | [record](testing/dashboard-d11/20261024T112356863617+0800-ga-browser/command.json) |
| D10 synthetic-HTTP Edge | **12 scenarios**, 13 Node checks | [record](testing/dashboard-d11/20261024T112513268456+0800-v2-browser/command.json) |
| D9 real Edge/FastAPI/SQLite | **16 scenarios**, 2 pytest wrappers, 2 warnings | [record](testing/dashboard-d11/20261024T112535631449+0800-live/command.json) |
| D10 real Edge/FastAPI/SQLite | **6 scenarios**, 1 pytest wrapper, 2 warnings | [record](testing/dashboard-d11/20261024T112520421541+0800-v2-live/command.json) |
| Production TypeScript/Vite build | **PASS**, existing bundling warnings | [record](testing/dashboard-d11/20261024T112239156342+0800-build/command.json) |
| Focused ESLint | **0 errors, 0 warnings** | [record](testing/dashboard-d11/20261024T112240519774+0800-lint/command.json) |

The 33 focused checks cover real session authorization/CSRF, own-only assignment and private request access, incorrect catalog UUID/code bindings, idempotency and duplicate-active proposals, submission/withdrawal eligibility, immutable history/tamper detection, wrong term, stale schedule/GEC revision, invalid times/rooms/duration, faculty/section/room/GEC overlap, adjacent intervals, laboratory duration, transaction rollback and competing updates. A fresh Python process opens the retained fictional SQLite request, starts a new FastAPI TestClient, authenticates the existing privately transferred session and retrieves the submitted request/history. Credentials/session artifacts travel through private stdin, never command arguments or evidence.

The 12 D11 live scenarios use Edge `155.0.4283.62`, actual React, loopback HTTP, FastAPI, real password/session/Origin/CSRF checks and owned SQLite. They exercise the proposal form, error/conflict feedback, safely rendered HTML-like justification, durable creation/submission, full page reload, cross-faculty denial, source outage with withdrawal, recovery and mobile history. The source, calendar/catalog and GEC snapshot are explicitly fictional. This is live API testing, not synthetic HTTP interception, genuine institutional verification or PostgreSQL acceptance. D11 operations do not trigger a GA; separately executed D10 regressions intentionally exercise fictional GA runs.

Latest genuine captures and scenario metadata are in [the final browser directory](screenshots/dashboard-d11/20261024T112824404727+0800-d11-live/browser-results.json): validation, submitted original/proposed details/history, and withdrawn mobile history. Original captures from failed/earlier runs remain retained. Some earlier submitted captures show the submission notice/form rather than the lower history section; final captures scroll to the actual detail/history region. Captures were visually privacy-reviewed without editing or reconstructing them. No HAR, raw database, raw checkpoint or session payload is archived.

## Retained failures and warnings

Five nonzero command records remain in the manifest. The first lint found synchronous state updates inside an effect; page loading/retry initialization was corrected and focused lint passes. The initial sandboxed browser failed at `Runtime.enable` before navigation; the unchanged browser transport passed outside the sandbox. Two later live runs exposed harness synchronization errors: a list-level UNAVAILABLE/CURRENT label appeared before asynchronous detail buttons/DOM. Waiting for the actual enabled button/detail region resolved both, with no enlarged timeout, disabled scenario or application permission workaround. The academic regression initially had two assertions pinned to D9; they now explicitly include D11's additive migration/metadata while preserving the seven-table checks. Earlier successful smaller focused runs remain history as coverage grew from 31 to 33 cases.

Existing dependency warnings remain: Starlette TestClient's httpx compatibility fallback and AnyIO BlockingPortal alias, plus Alembic's missing `path_separator` warning during offline rendering. The build retains the existing ineffective dynamic import and large bundle warnings. Dependencies were not upgraded or warnings suppressed. Repository-wide lint and institutional-scale performance were not claimed.

## Preservation, limitations and next action

The [pre-implementation baseline](testing/dashboard-d11/preservation-baseline.json) records **973 files**. **966 remain byte-identical; exactly the seven intended existing paths above changed.** The baseline already includes the protected local preference bytes. All 23 academic data files, identity/code/qualification mappings, original professor GA modules, numerical scoring, RNG, V1/V2 sources/checkpoint formats, six retained historical checkpoints, saved schedules, historical results, D8-D10 trust/provenance artifacts, Git index and HEAD remain unchanged. Supported V1 fixtures and D10 regression suites passed without changing those engines. Historical incompatible checkpoints were neither migrated nor reinterpreted.

The privacy audit checks decoded JSON/text, complete/truncated signed fragments, sensitive command-output assignments/headers, credential URIs/keys, private faculty names locally, and PNG metadata/CRC plus visual inspection. The manifest stores raw-byte hashes excluding itself. It preserves failure records and distinguishes each testing scope. Hashes establish artifact identity, not approval or institutional correctness.

Production and remaining boundaries:

- Configure and independently verify a coherent schedule/term/resource source and fresh institutional/GEC authority before enabling production creation/submission. A bare legacy latest-result file is insufficient. The reusable legacy adapter is not itself institutional authorization.
- Separately approve a disposable PostgreSQL acceptance target and migration run. The 17 Phase 4C cases, D9 PostgreSQL acceptance, D10 V2 locking acceptance and D11 PostgreSQL migration/triggers/concurrency remain unverified. SQLite and offline SQL rendering do not establish them. No migration command was executed online.
- D11 retains immutable drafts, with withdrawal/recreation for changes. Stale detection is read-time and does not append automatic audit events or overwrite prior request status. Concurrent conflicts may require reload/retry; SQLite lock behavior is not a PostgreSQL concurrency claim.
- The current source adapter covers a caller-guarded completed legacy proposal. A genuine published/versioned source and production V2 assignment adapter remain separate integration work. No imported external commitment can be edited through D11.
- No Chair inbox, authority/decision endpoints, approval, rejection, application, publication, optimization or changes to GEC confirmations exist in D11. D12 must later revalidate the exact schedule/GEC revisions and preserve this request/history rather than rewriting it.

**Recommended next action:** review the D11 diff, scope limitations and manifest before a separately authorized secure Git checkpoint. Plan institutional source/catalog integration and isolated PostgreSQL acceptance before production use. Do not start D12 automatically. All D11 work remains unstaged and uncommitted.
