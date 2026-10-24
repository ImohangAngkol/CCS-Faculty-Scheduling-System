# D14: full system integration and acceptance

Recorded 2026-10-24, Asia/Manila. Baseline: `main` at `7a0c3eaf32dc3cc350c04871fdb6f8dd72c43bb4` (also the unchanged, last-fetched `origin/main`). No fetch or Git checkpoint was performed.

## 1. Executive summary and acceptance decision

**PASSED within the isolated fictional acceptance scope. Production acceptance remains BLOCKED.** Fresh tests demonstrate a continuous real-service path from a trusted fictional GEC confirmation through actual constrained GA generation, a faculty adjustment request, independent Chair approval, transactional application, immutable versions and the faculty's updated timetable. Real Edge communicates with React and FastAPI over HTTP using actual authentication/CSRF and owned SQLite storage. This is not synthetic-HTTP substitution.

The path has an explicit test-only publication boundary: a fictional guarded provider designates the exact completed V2 run as a published source. There is no newly implemented production GA-to-publication API. Institutional issuers, confirmation authorities, complete academic mappings, Chair mandates and publication authority remain unconfigured in deployment. No fictional provider was installed into production. PostgreSQL was not connected; its outstanding acceptance cannot be inferred from SQLite.

Two misleading UI messages were corrected. Existing GA algorithms, V1/V2 execution services, data, historical artifacts and D1-D13 evidence are unchanged. Final selected checks pass; eight unsuccessful intermediate command records remain archived. One older D9 Windows HTTP-fixture teardown failure passed on a separate rerun and remains an infrastructure reliability limitation.

Evidence: [manifest](testing/dashboard-d14/manifest.json), [reproducible runner](testing/dashboard-d14/run_checks.py), [audit utility](testing/dashboard-d14/audit_evidence.py), [environment](testing/dashboard-d14/environment.json), [pre-test preservation baseline](testing/dashboard-d14/preservation-baseline.json). Each command record contains exact invocation, working directory, start/end timestamps with offset, elapsed time, sanitized output, scope and exit code. Manifest hashes exclude the manifest itself.

## 2. Architecture, baseline and safe environment

React/TypeScript routes use `AuthContext`, role-aware layouts and `GAContext`. FastAPI routers authenticate real sessions and use server-side faculty bindings. Academic/identity tables, the confirmation ledger, adjustment events, Chair decisions and published versions have separate explicit contracts. CSV/JSON-backed prototype metadata remains distinct from the seven-table Phase 4C academic foundation. The latter has no newly activated runtime import or migration in D14.

V1 uses the original scheduling engine and strict checkpoint fingerprints. V2 wraps unchanged operators with versioned constraints, persistent reduced availability, candidate admission and independent stores. The D8-D10 trust chain supplies current applicable confirmation heads and authoritative catalog mappings; D11-D13 require additional independent ownership, Chair and publication checks. A historical confirmation or Chair approval alone cannot activate/publish a schedule.

The new test fixture composes existing D9-D13 fixtures with actual `LedgerAuthority`, real D8 verification logic and real V2 generation. Resources are fictional: three faculty, two subjects, two sections, lecture/laboratory rooms, a fictional term, one external section commitment on Monday 09:00-10:00, independent fictional Chair/scheduler actors and explicit fictional capacity/enrollment mappings. Faculty eligibility and UUID/code mappings are specified, never inferred from names or row order. Optional GEC faculty/room are explicitly not applicable in this continuous example; separate V2 regressions exercise those constraints.

All database stores, V2 outputs, preferences and settings are new owned OS-temp files. Every preference/settings alias used by the browser fixture is redirected. The child environment includes whitelisted OS variables only and excludes database URLs, credentials and approval flags. No institutional dataset rows, raw database, checkpoint, HAR, cookie dump or provider payload is archived. Scheduling imports can read existing CSVs internally; evidence suppresses their output and tests use isolated fictional objects.

Runtime: Python 3.14.2, SQLite 3.50.4, Node 24.11.1, Edge 155.0.4283.62, FastAPI 0.141.1, Starlette 1.6.0, SQLAlchemy 2.0.52, Alembic 1.19.2. Existing dependencies were used; no new dependency/service was installed. Owned loopback Vite/Uvicorn/Edge processes were started and stopped by the harness, without reconfiguring unrelated services.

## 3. D1-D13 feature coverage inventory

Paths below are repository-relative. Test names identify actual suites freshly executed in D14, not assertions based only on historical reports. Models are SQL models unless a row explicitly says files/runtime objects. PASS means the stated isolated scope; it does not certify real institutional metadata or deployment authority.

| ID / component | Frontend and backend implementation | Storage / dependencies / integration consumers | Fresh coverage and limits |
|---|---|---|---|
| A Core dashboard | `frontend/src/routes/AppRoutes.tsx`, admin/faculty `Dashboard.tsx`, faculty `Profile.tsx`; `routers/auth.py`, `services/auth_service.py`, `metadata_service.py` | `identity_models.py`: User, LoginSession, FacultyIdentityRecord; all protected pages consume sessions | D1-D2 browser/metadata/auth regressions PASS. Account/profile reads do not imply editable academic records or invented workload statistics. |
| B Faculty management | admin `FacultyManagement.tsx`; `routers/faculty.py`, `metadata_service.py`, GA result services | File-backed Faculty/runtime mappings and verified identity binding; GA calendar consumers | PASS for current viewer/metadata behavior. This is not institutional faculty CRUD; complete GA views require an available result. |
| C Faculty preferences | faculty `Preferences.tsx`, admin `PreferencesReview.tsx`; `routers/preferences.py`, preference validation/storage services | Existing preference JSON and settings, real identity/CSRF; consumed by GA fitness/preferences | D14 owned Compact/Very High save/reload, invalid importance and cross-faculty denial PASS; original JSON untouched. |
| D Subject eligibility | admin `SubjectManagement.tsx`, subject metadata; `Functions.py` and existing operator validation | File-backed eligibility/domain mappings and Subject/Faculty objects; generation/admission consumers | Metadata/backend, resource and V2 suites PASS, including explicit fixture eligibility. No eligibility management CRUD or institutional reconciliation is implied. |
| E Faculty qualifications | faculty `Profile.tsx`, subject/faculty metadata; `metadata_service.py`, scheduling loaders | File-backed qualifications and faculty identities; generation/load checks | PASS for existing metadata/contracts and fictional generation validation. Accuracy/completeness of institutional CSV entries is NOT independently certified. |
| F Room assignments | admin `RoomAssignments.tsx`, shared `WeeklySchedule.tsx`; GA/result metadata services | Runtime Room objects, explicit trusted capacity provider for D13; calendar/application consumers | Resource, V2 and D13 compatibility/capacity tests PASS. Viewer is not authoritative room/capacity CRUD; absent capacity cannot be invented. |
| G Schedule generation | admin `GenerateSchedule.tsx`; `routers/genetic_algorithm.py`, `routers/ga_constrained.py`, `ga_service.py`, `ga_v2_service.py` | V1 files and V2 owned versioned stores; verified term/catalog/authority for V2 | Real V2 generation and original V1 continuation PASS; proposal labels retained. Production V2 providers BLOCKED. |
| H Chromosome visualization | admin `ChromosomeViewer.tsx`; `routers/chromosomes.py`, `chromosome_service.py`, chromosome analysis | Existing saved/uploaded chromosomes and metadata; GA seed/view consumers | GA regressions PASS. No existing saved chromosome overwritten; no claim of new constrained seed conversion. |
| I Fitness analysis | admin `FitnessAnalysis.tsx`; `routers/fitness_analysis.py`, fitness/faculty/chromosome analysis services | Original FitnessFunction and GA result provenance; schedule review consumes analysis | Browser, V2 kernel and actual D14 result view PASS. Penalty 30 is not a quality percentage, approval or proof of global optimality. |
| J GEC review | admin `ExternalSchedules.tsx`, weekly review/handoff components; `external_schedule_service.py`, review/handoff services | Temporary signed preview lifecycle, bounded CSV/XLSX; readiness/ledger consumers | D3-D5 validation and browser regressions PASS. Native OS print-dialog/output validation NOT RUN. Temporary preview is not durable confirmation. |
| K Legacy GEC integration | same external page; `external_schedule_legacy_service.py` | Explicit legacy dialect/source hashes and original row references; D4-D8 consumers | D6 backend/browser regressions PASS with fictional examples. Actual legacy academic-term ambiguity is not silently resolved or activated. |
| L Institutional evidence | external readiness/evidence panels; `external_schedule_readiness_service.py`, `external_schedule_verification_service.py` | Trusted evidence/issuer/catalog providers; D9/D10 consumers | D7-D9 suites and real D14 trust evaluation PASS with fictional issuers. Production provider remains BLOCKED; stored VERIFIED history is not fresh verification. |
| M Durable confirmation | `ExternalConfirmationLedger` on external page; `routers/external_confirmations.py`, `external_confirmation_service.py`, confirmation authority | `confirmation_models.py`: ExternalRecord, ExternalRevision, ConfirmationEvent; V2/current-head consumers | D9 actual HTTP and D14 confirmation/generation PASS. Independent authority required; admin role alone cannot confirm. PostgreSQL guards NOT RUN online. |
| N Confirmed revisions | same ledger; current-head/link/digest checks in confirmation and V2 constraints services | Immutable revision/event chain and optimistic record version; generation/application consumers | D9/D10 revocation, supersession, tamper and complete-head tests PASS. History read is explicitly NOT_RECHECKED. |
| O V1 GA | legacy generate/schedule/analysis pages; `ga_service.py`, original operators, checkpoint services | Strict input/engine fingerprints and existing checkpoint format; continuation/history consumers | Four actual current-release V1 fixtures PASS. Six incompatible historical checkpoints remain a pre-existing rejected class, byte-identical. |
| P V2 constrained GA | V2 controls/results on existing pages; `ga_v2_engine.py`, `ga_v2_constraints.py`, `ga_v2_store.py`, `ga_v2_service.py` | Explicit engine version, immutable snapshot, separate checkpoint/store and current trust | 30 kernel + 18 API cases, six real HTTP scenarios and new continuous generation PASS. No production constraint activation or operator rewrite. |
| Q Faculty adjustments | faculty `AdjustmentRequests.tsx`; `routers/adjustments.py`, `adjustment_service.py`, `adjustment_schedule_service.py` | `adjustment_models.py`: AdjustmentRequest/Event, verified published source; Chair consumers | 33 backend + 12 real browser regressions and D14 PASS. Request/submission does not alter schedules; owner/revision/term are server checked. |
| R Chair approvals | `pages/chair/Requests.tsx`; chair authority/review/projection services | `chair_models.py`: immutable ChairDecision, independently verified mandate/department; application consumers | 42 backend + 12 real browser regressions and D14 PASS; unauthorized/self/cross-department/stale/concurrent/withdrawn decisions covered. Approval alone cannot publish. |
| S Controlled application | admin `ScheduleApplications.tsx`; application authority/service, published source/version store | `application_models.py`: ScheduleApplication, PublishedVersion/Head; independent publisher plus full metadata/trust | 47 backend + 14 real browser regressions and D14 PASS; no partial transaction or unrelated meeting changes. Genuine publisher/source BLOCKED. |
| T Schedule version history | application version panels and faculty `MySchedule.tsx`; published schedule views/version store | Immutable PublishedVersion and guarded current PublishedHead; owned faculty/admin views | D13/D14 exact-delta/history/concurrency PASS. Original GA result stays separate; history read does not certify current external constraints. |
| U Historical results | admin `GenerationHistory.tsx`; `ga_history_service.py`, checkpoint recovery and GA control services | Existing snapshots/checkpoints/saved output; historical analysis/continuation consumers | Backend/GA-browser regressions PASS with isolated stores. Existing historical artifacts unchanged; no reinterpretation under new constraints. |
| V Audit records | confirmation/request/Chair/application histories; corresponding service digests and guards | ConfirmationEvent, AdjustmentEvent, ChairDecision, ScheduleApplication plus version provenance | Fresh restart, immutability, rollback, replay and tamper tests PASS on SQLite/offline SQL. Live PostgreSQL audit/locking guarantees remain NOT RUN. |

## 4. Fresh test matrix and counting

The following are newly executed D14 results. A scenario count excludes Node parent tests and pytest wrapper tests. Repeated attempts, intermediate passes and past D1-D13 results are not added. Exact latest record links are indexed in the manifest's `latest_commands`.

| Category / runner key | Latest result | Evidence scope |
|---|---:|---|
| New complete-system backend `focused` | **6 passed** | Three independent actual constrained-generation/request/application samples; real confirmation revocation; preferences; storage fault/recovery |
| D13 `d13-backend` | **47 passed** | Application/trust/rollback/restart and offline migration tests |
| D12 `d12-backend` | **42 passed** | Chair decisions, trust and offline migration |
| D11 `d11-backend` | **33 passed** | Requests, ownership and offline migration |
| D2-D9 `backend` | **327 passed** | Existing metadata/intake/review/evidence/confirmation APIs and validations |
| Auth/control/GA `backend-regressions` | **46 passed** | Existing backend regression selection |
| Academic `academic-offline` | **85 passed** | In-memory/offline planner/schema/safety/SQL rendering; no PostgreSQL |
| Original resources `ga-resource-regressions` | **3 passed** | Existing preassignment/resource contracts |
| Current-release V1 `v1-fixtures` | **4 passed** | Actual original-operator creation and continuation; not mocked continuation |
| V2 `v2-engine` / `v2-api` | **30 / 18 passed** | Admission, reset, trust, storage, exact continuation and rejection cases |
| Frontend `contracts` | **205 passed** | Node contract/model tests, not real-browser evidence |
| D1-D8 `browser-regressions` | **125 scenarios passed** | Actual Edge, synthetic HTTP responses; repeated after UI fixes |
| GA `ga-browser` | **51 scenarios passed** | Actual Edge, synthetic HTTP monitoring/result responses |
| D10 `v2-browser` | **12 scenarios passed** | Actual Edge, synthetic HTTP V2 responses |
| D9 `live` | **16 scenarios passed**, two pytest wrappers | Actual Edge/FastAPI/SQLite with fictional institutional providers; final isolated rerun |
| D10 `v2-live` | **6 scenarios passed**, one wrapper | Actual Edge/FastAPI/SQLite and actual V2 generation |
| D11/D12/D13 live | **12 / 12 / 14 scenarios passed**, one wrapper each | Actual Edge/FastAPI/SQLite, separate milestone fixtures |
| New D14 `d14-live` | **20 scenarios passed**, one wrapper | Continuous real Edge/React/FastAPI/SQLite path with actual generation |
| Production frontend build | **PASSED** | Existing mixed static/dynamic import and >500 kB chunk warnings retained |
| Focused ESLint | **PASSED**, zero errors/warnings | D13-focused TypeScript list plus changed ExternalSchedules page |
| Phase 4C live PostgreSQL | **17 cases NOT RUN** | Safe authorized disposable environment unavailable |
| D9-D13 live PostgreSQL acceptance | **BLOCKED / NOT RUN** | No production/disposable PostgreSQL access attempted |

Two dependency warnings in HTTP-test groups are attributable to Starlette TestClient's deprecated httpx path and anyio BlockingPortal alias. Academic offline/migration selections also emit the existing Alembic missing `path_separator` deprecation. These were captured without hiding warning summaries. No dependency upgrade or broad configuration cleanup was made for D14.

## 5. Continuous end-to-end results

New backend suite: [final six cases](testing/dashboard-d14/20261024T205920068755+0800-focused/command.json). New browser: [final command](testing/dashboard-d14/20261024T210021246779+0800-d14-live/command.json), [browser observations](screenshots/dashboard-d14/20261024T210021246779+0800-d14-live/browser-results.json). Source: `backend/tests/dashboard/test_system_acceptance.py`, `test_system_acceptance_live.py`, `frontend/tests/systemAcceptance.live.mjs`.

The backend fixture creates and confirms a fictional GEC proposal through actual D8/D9 service/API checks. The browser reads that durable ledger, requests the complete current V2 constraint set, starts actual V2 generation, opens the returned schedule and fitness views, then designates that completed result through the explicit owned fictional publication provider. Separate fresh D9 live tests exercise proposal/confirmation/revocation interactions through the UI; the D14 browser does not claim to have created the pre-seeded confirmation through its UI.

The faculty authenticates, retrieves actual generated assignments and selects its own three-hour laboratory meeting. The test searches bounded candidate intervals through the actual preview API; it does not fabricate a valid response. The UI validates, creates and submits the request. A separately authorized Chair approves. That actor cannot apply. An independent scheduler previews current complete-schedule validation, experiences a controlled rollback, retries and obtains published version 2. The faculty sees APPLIED and only its own new assignments. A later approved request binds the new revision; concurrent application transactions produce one success and one conflict, with one version 3. The original V2 result remains exactly unchanged.

Final browser cases: L01 anonymous denial; I01 preference save/reload; I02 subject catalog and ledger; I03 actual V2 generation; I04 proposal/fitness and explicit fixture publication; L02 faculty submission; L03 Chair approval/application denial; L04 valid scheduler preview; L05 rollback; L06 successful versioning; L07 owner timetable; L08 cross-faculty/private history denial; L09 rejected request blocked; L10 new current-revision request; L11 trust outage; L12 concurrent application; L13 mobile preserved history; L14 missing authority; I05 published empty state; I06 actual backend shutdown/retry state. **20 passed; zero runtime errors in final browser record.**

## 6. GA validation and compatibility

Fresh V1 fixtures create current-release checkpoints and continue real original operators, with strict input/engine validation retained. V2 tests cover actual operators, exact uninterrupted-versus-resumed continuation, fresh-process checkpoint restoration, explicit seed incompatibility, version/input corruption, last-moment trust loss and guarded publication. Existing lock/admission/fingerprint logic was not weakened.

Faculty, room and section commitments use real explicit IDs when applicable and half-open intervals: adjacency is allowed; overlap is rejected. Reset/restart tests prove all applicable reservations survive. Post-crossover/mutation candidates are admitted before they can influence populations or best-ever, with rejected candidates/backfill bounded. Conflicting/invalid inputs and bounded search exhaustion remain distinct; exhaustion is not mathematical proof of infeasibility. The new continuous example primarily exercises the section commitment; existing fresh kernel/API selections cover faculty and room commitments as well.

All three final new backend generation samples completed, and reconstructed results passed original V2 admission against the correct reduced templates and pinned constraint snapshot. This validates modeled eligibility, required meeting coverage/duration, section/faculty/room consistency and hard limits for this workload. It is not an institutional-scale feasibility or optimality study. The six retained historical checkpoints were already incompatible before D10 and remain untouched; this report does not call them resumable.

## 7. Schedule conflicts and quality

Fresh D11-D13 and V2 tests cover faculty/room/section collisions, invalid day/time/duration, adjacent intervals, laboratory duration, eligibility, current full schedule, GEC conflicts, stale mappings and verified capacity policy. Capacity/enrollment are supplied explicitly by the fictional publisher in the continuous test, not inferred from Room attributes or fabricated academic records.

Each final new GA sample returned original fitness penalty **30**, with zero unassigned subjects accepted by complete admission. The browser's actual result analysis lists teaching-load-balance contribution 30 and the other displayed contributions 0. Lower original penalty remains better. A nonzero soft penalty is retained; it is not relabeled perfect, official or globally optimal. Preferences were validated/persisted in a separate owned round trip and the browser journey; the three backend timing samples intentionally use the fixture's neutral GA preference DataFrame. They do not establish optimization quality under every preference combination. Application revalidates hard constraints but does not recalculate fitness or change numerical penalties.

## 8. Faculty request results

Fresh D11 cases cover actual account-to-faculty ownership, IDOR, assignment spoofing, origin/CSRF, idempotency, duplicate active requests, withdrawal, term/revision binding, explicit discrepancy reporting and durable fresh-process reads. Creating/submitting a request preserves the source schedule and RNG state. D14 adds actual generated-assignment selection and subsequent APPLIED visibility. Invalid importance 999 returns 422; another faculty's preferences return 403. No arbitrary client faculty identifier grants access.

## 9. Chair decision results

Fresh D12 tests cover independent mandate/department verification, no self-decision, invalid/withdrawn states, stale optimistic bindings, explanations, immutable final decisions, duplicate/concurrent commands and authority changes during a transaction. D14 uses the real current confirmation trust evaluator for the generated schedule. Valid approval preserves all schedules. Rejection cannot be applied; Chair capability alone cannot publish. Production Chair mandate lookup remains BLOCKED.

## 10. Controlled application and histories

Fresh D13 and new D14 tests demonstrate exact one-meeting change, complete-schedule revalidation, version/head compare-and-swap, idempotency and atomic rollback. The three final backend samples retain exactly two versions and one application; no unrelated assignment differs. Storage unavailability is injected as SQLite OperationalError before PublishedVersion insertion: response is sanitized 503 `APPLICATION_STORAGE_UNAVAILABLE`, no application/head/version survives, and removing the fault permits the same operation to succeed. Browser rollback injects a persistence integrity failure after audit insertion, then verifies no partial publication.

Revoking the actual confirmed GEC head after generation and Chair approval blocks the new application; original generated bytes remain unchanged. D13 regression tests cover changed authority, owner binding, capacity, complete current schedule and stale competing approvals. Version/history reads survive fresh Python processes in freshly rerun D11/D13 suites. This is process-restart persistence evidence for owned SQLite, not a physical PostgreSQL restart or production disaster-recovery exercise.

## 11. Database acceptance and outstanding plan

**No PostgreSQL connection or migration was performed.** Inspection found no authorized `PHASE4C_TEST_DATABASE_URL` in this execution process. Existing database names, ownership, server version and contents were not queried. The earlier user's PostgreSQL 18.6 observation remains historical rather than a fresh D14 finding. Neither Phase 4B database was touched. All D14 writes use owned fictional SQLite/file stores.

Static inspection of `backend/tests/academic/postgresql_safety.py` confirms the exact designated target `ccs_ga_phase4c_test`, restricted role `ccs_ga_phase4c_tester`, `127.0.0.1:5432`, dedicated `PHASE4C_TEST_DATABASE_URL`, rejected URL query overrides and no `DATABASE_URL` fallback. Connection requires explicit approval token `PHASE4C_POSTGRESQL_APPROVAL=I_APPROVE_ISOLATED_PHASE4C_POSTGRESQL_TESTS` and the helper's allow-connect gate. Initial inspection is read-only with timeouts, checking database/role/server/ownership, privilege flags and memberships, public schema/ACLs, default ACLs, objects, extensions/types/functions and pristine emptiness.

The **17 Phase 4C live cases remain NOT RUN**, not newly observed skips or passes. SQLite triggers and offline PostgreSQL DDL rendering do not prove PostgreSQL transaction/locking behavior. Migrations through `d13_0001` were inspected/rendered by existing offline tests; none was applied online. No D14 schema/table/migration was added.

Required separately approved execution sequence:

1. Verify maintenance server identity and the designated role/database's existence without modifying anything. If either exists unexpectedly, stop for ownership/data review; never reset or assume disposable.
2. Approve a new isolated disposable target and private credential setup if needed. Verify exact role ownership, nonprivileged/nonmember status, public schema rights and empty inventory through the existing SELECT-only gate. Keep credentials out of command arguments/evidence and use only the dedicated variable.
3. Run the existing 17-case academic module once against its expected pristine target using its approved gate. Record migration chain, seven-table constraints, trigger/calendar containment, upgrade/downgrade behavior, concurrency and sanitized failures. The suite leaves state; do not blindly rerun an empty-target gate on a populated database or clean it automatically.
4. Prepare an explicit reviewed D9-D13 online acceptance profile in a separately designated disposable database/state. Cover additive upgrades, populated downgrade refusal, immutable ledger/decision/version guards, foreign keys, exact revision chains, current-head row/SHARE locks, competing confirmations/decisions/applications, CAS/idempotency, rollback, fresh-process sessions/history and revocation across publication. Existing SQLite fixtures cannot simply be pointed at PostgreSQL as a substitute for this work.
5. Record actual PostgreSQL/client versions, approved target identity, exact commands, durations, all warnings/failures and artifact hashes. Retain disposable state for review; no automatic drop, reset, reseed or production credential change.

## 12. Browser evidence and visual review

Final new journey uses Edge 155.0.4283.62 at desktop 1366x1100 and mobile 390x844. Screenshots are actual CDP PNG captures, unedited, with observation records in each run directory. The final run contains 12 PNGs; three completed scenario attempts together retain 34 PNGs, 28 unique raw hashes. The wrapper-failed attempt is explicitly historical failure evidence, not substituted for the final pass. Every unique image was visually reviewed; byte-identical copies share that review. PNG CRC/chunk/text/EXIF checks are part of the audit.

Representative final originals: [actual fitness and constraint provenance](screenshots/dashboard-d14/20261024T210021246779+0800-d14-live/D14-I04-actual-fitness-analysis.png), [validated application preview](screenshots/dashboard-d14/20261024T210021246779+0800-d14-live/D14-L04-validated-application-preview.png), [applied version history](screenshots/dashboard-d14/20261024T210021246779+0800-d14-live/D14-L06-applied-version-history.png), [owner published timetable](screenshots/dashboard-d14/20261024T210021246779+0800-d14-live/D14-L07-faculty-published-timetable.png), [backend unavailable](screenshots/dashboard-d14/20261024T210021246779+0800-d14-live/D14-I06-owned-backend-unavailable.png).

Screenshots show only their captured viewport. The I01 screenshot shows the preference editor's upper portion; Compact/Very High controls are below the captured fold and verified by DOM/API assertions. I05 likewise captures the mobile page above its empty-message position; its exact published-empty wording is verified by DOM assertion. Mobile preserved-history imagery shows a horizontally scrollable Monday column, not every meeting. These captures do not independently prove the entire asserted state. No reconstructed/generated screenshot is used.

The 188 synthetic-HTTP browser scenarios (125 D1-D8 + 51 GA + 12 V2) remain explicitly separate from 80 actual HTTP scenarios (16 D9 + 6 D10 + 12 D11 + 12 D12 + 14 D13 + 20 new D14). The real HTTP category still uses fictional institutional providers and SQLite; it is not genuine institutional or PostgreSQL acceptance.

## 13. Security and privacy

Fresh tests exercise real sessions, ownership, origin/CSRF, separate Chair/application capabilities, cross-department rejection, immutable histories, current trust/revision binding, sensitive error sanitization and transaction integrity. Backend-down I06 stops only the owned fixture, confirms actual connection refusal, then navigates the real frontend to session retry without retaining the private timetable. Trust/provider outages fail closed; frontend authority controls disappear. Invalid/expired/tampered preview and missing mappings remain rejected in the D2-D13 regression selections.

Evidence is filtered before persistence using the existing sanitizer, then independently scanned for full/truncated encoded receipts, shorter fragments, sensitive log assignments/headers, credential URIs, bearer values, keys and locally compared private faculty names. No private names are exported by that comparison. Original screenshots were visually inspected and their metadata checked. Fictional faculty UUIDs, request IDs, revision IDs, source hashes and audit digests are provenance, not authentication tokens. No new evidence required additional post-write redaction; useful failed diagnostics remain retained. Automated scans cannot prove the absence of every imaginable secret; the fixtures, output filtering, structural review and visual inspection provide separate controls.

Failure/recovery coverage is explicitly bounded:

| Requested scenario | Fresh result and scope |
|---|---|
| Backend unavailable | PASS: new I06 stops owned backend, observes real connection refusal and frontend retry state |
| Database unavailable | PASS for injected SQLite OperationalError and rollback/retry; physical PostgreSQL outage NOT RUN |
| Institutional verification unavailable | PASS: actual evaluator rejection in backend selections and injected browser trust outage; real external-provider outage NOT RUN |
| Invalid confirmation | PASS: D9/D10 validation/authorization regression cases with fictional issuers |
| Revoked confirmation | PASS: new actual D9 revoke after GA/approval blocks application |
| Stale schedule version | PASS: D11-D13 bindings/competing version tests and continuous new-revision request |
| Missing faculty / room mappings | PASS: fresh V2 API/kernel and D11-D13 complete metadata rejection cases; no inferred identity fallback |
| Conflicting fixed GEC schedules | PASS: V2 duplicate/internal overlap and applicable-resource admission tests |
| GA search exhaustion | PASS: existing bounded kernel exhaustion and distinct invalid-input cases; no mathematical infeasibility claim |
| Unauthorized faculty / Chair / application | PASS: fresh role, ownership, mandate/scope, CSRF and independent publisher tests plus real browser denials |
| Duplicate submission | PASS: fresh D11/D12/D13 idempotency and duplicate-content command cases |
| Concurrent conflicting application | PASS: new real HTTP competing commands and separate-transaction D13 SQLite tests; PostgreSQL locking NOT RUN |
| Transaction rollback | PASS: new backend storage failure/recovery, browser audit-insert fault and D13 authority-loss transaction tests |
| Application restart / persisted records | PASS for fresh Python-process SQLite checkpoint/request/Chair/application history tests; full production service/database restart NOT RUN |

## 14. Performance and reliability observations

Three final backend samples use population 2, generations 2, two subjects and one confirmed GEC head. [Metrics](testing/dashboard-d14/20261024T205920068755+0800-focused/metrics/complete-workflow-1.json) are recorded separately from raw requests or institutional data.

| Observation | Actual range / result |
|---|---|
| Actual GA request through completed result | 2177.554-3308.305 ms |
| Complete application-preview GET | 291.153-394.853 ms |
| Atomic apply POST | 165.153-399.500 ms |
| Generated meetings | 4-5; three of three completed and passed hard admission |
| Final new browser journey | 49.523 seconds Node journey; 57.38 seconds pytest; 60.335 seconds runner elapsed |
| V1 fixture selection | 113.20 seconds pytest; four passed |
| CPU, peak memory, realistic institutional scaling | NOT RUN |

Preview/apply measurements are complete in-process API operations including validation and SQLite work, not isolated database latency. Three tiny samples do not estimate production success rates, tail latency, memory pressure or optimal search settings. Earlier slow fixture observations were caused by nested SQLite leases in the new test composition; fixing that test provider is not a production performance optimization. Full schedule validation, trust-provider latency, large queues/catalogs and source fingerprinting are future profiling candidates. No timeout, algorithm or penalty was increased/relaxed to obtain acceptance.

## 15. Defects found and corrected

Only two existing application files changed:

1. `frontend/src/pages/admin/ExternalSchedules.tsx`: its old header said nothing on the page was saved/confirmed, contradicting the D9 durable ledger below. The wording now distinguishes temporary intake/calendar previews from durable revisions/decisions and states confirmation does not activate a GA run. D14 I02 asserts the corrected message; D1-D8 browser regressions were freshly repeated after this change.
2. `frontend/src/pages/faculty/MySchedule.tsx`: schema-2 published schedules with no own assignments used legacy proposal-only wording. Empty state now says published schedule for schema 2, retaining schema-1 proposal wording. D14 I05 verifies the actual API/DOM condition; existing My Schedule browser regressions and build/lint passed.

No backend runtime service or security contract changed. New regression assertions reside in the new D14 browser/backend suites rather than rewriting old evidence.

## 16. Intermediate failures and remaining failures

All eight nonzero D14 command records remain hashed in the manifest. They are not removed or counted as final passes:

| Record prefix / check | Observed failure | Correction / final status |
|---|---|---|
| 203752 / focused | Three failures: nested SQLite writer lease and incorrect new fixture preference field names | Test-only source guard composes with D11/D13 transaction; actual preference keys used; final six passed |
| 203938 / focused | Three setup errors: wrong fixture GASetting import location | Uses actual router-exposed class; final six passed |
| 204038 / focused | One failed/two passed: generated late meeting outside older hand-authored fixture window | Explicit fictional windows corrected to actual model's 22:00 end; no production calendar changed |
| 204250 / focused | Two failed/one passed: window and post-generation admission reconstructed from unreduced templates | Test uses actual reduced templates required by V2; final six passed |
| 204830 / d14-live | 150-second Node timeout; early wrapper did not retain a useful partial scenario trace | Retained command failure; bounded fail-fast diagnostics added. Later reproduction identified preference-save PUT blocked by fixture CORS; exact initial timeout alone cannot establish every causal detail |
| 205255 / d14-live | Anonymous scenario passed, preference save failed: owned test CORS allowed GET/POST only | Added PUT to owned fixture CORS; production already permits it with real CSRF; final journey passed without increasing timeout |
| 205442 / d14-live | All 19 then-existing scenarios passed, pytest wrapper failed because owned Windows Proactor server thread did not stop | New D14 fixture uses local SelectorEventLoop and owned stop marker; final 20 scenarios plus clean teardown passed |
| 205455 / D9 live | All 16 browser scenarios passed, one of two pytest wrappers failed HTTP server teardown with Windows connection-reset callback | Existing D9 harness unchanged. Isolated final rerun 205820 passed both wrappers; broader teardown flakiness remains unresolved infrastructure risk |

No application failure remains in the final selected D14 run. This does not erase intermediate failures or resolve older harness reliability globally. No failing test was disabled/deleted and no arbitrary timeout increase was used. Final D14 explicit backend-down testing intentionally produces an unavailable state and is a passing negative test, not an unexpected server failure.

## 17. Unverified areas and production blockers

- **BLOCKED:** Genuine evidence issuer/verification lifecycle, independent confirmer, authoritative complete term/resource catalog, Chair mandates, publication source and application actor providers. Successful fictional providers cannot establish institutional approval.
- **NOT RUN:** 17 live Phase 4C tests and D9-D13 online PostgreSQL migrations/guards/row-lock/SHARE-lock/concurrency/restart acceptance. No physical PostgreSQL outage tested.
- **NOT IMPLEMENTED / outside D14:** A production initial GA-proposal publication/authorization workflow. The test-only designation is explicit and not deployed.
- **NOT RUN:** Accuracy/completeness of real academic datasets, institutional workload feasibility/optimality, realistic performance/peak memory, OS print rendering, production service restart/disaster recovery and cross-browser acceptance beyond the owned Edge version.
- **Known limit:** Six historical incompatible checkpoints retain their existing rejection; older D9 Windows teardown flakiness remains. Existing large-chunk/mixed-import and dependency deprecation warnings remain.
- **NOT APPLICABLE:** C++ acceleration, broad cleanup, new database schema, new academic imports or automatic GA activation in this testing milestone.

## 18. Exact created files

New source tests: `backend/tests/dashboard/test_system_acceptance.py`, `backend/tests/dashboard/test_system_acceptance_live.py`, `frontend/tests/systemAcceptance.live.mjs`.

New documentation/tooling: this report; `docs/testing/dashboard-d14/run_checks.py`, `audit_evidence.py`, `environment.json`, `preservation-baseline.json`, `manifest.json`; unique timestamped command records; public numeric metrics; screenshot/browser observation records under `docs/screenshots/dashboard-d14/`. The manifest enumerates every artifact, raw hash and size. No D1-D13 file/evidence was recreated or overwritten. Two application modifications are listed in section 15.

## 19. Preservation verification

The pre-test raw-byte baseline contains **1206 files**: tracked application/test/evidence, all 23 academic data paths, retained ignored historical stores and Git index. Final audit expects exactly the two UI files above to differ: **1204 baselined files remain byte-identical**. Protected `backend/data/faculty_preferences.json` retains its exact starting bytes and pre-existing local Git modification. It was never modified, restored, staged or committed by D14. All other academic data, UUID/code/eligibility mappings, operators, math/penalties, RNG/elitism sources, V1/V2 services, six historical checkpoints, original schedules/history, existing published artifacts, D1-D13 evidence, HEAD and index remain unchanged.

Owned test fixtures legitimately create fictional SQLite transactions and new temp GA outputs; none is an existing institutional record. In new continuous tests, original generated result bytes, old synthetic source bytes and module-global RNG state remain unchanged by request/approval/application. The Git working tree contains only that pre-existing preference modification, the two intended UI fixes and new D14 files. No staging, commit, push, fetch, migration or production/Phase 4B database operation occurred. Final manifest checks SHA-256 integrity and privacy; its hashes establish file identity rather than institutional trust.

## 20. Recommended next steps and stop

Review this bounded acceptance result and retained failures before a separate authorized Git checkpoint. Next practical release work is a reviewed institutional-provider/publication contract and isolated PostgreSQL acceptance preparation, followed by real institutional metadata verification and a realistic workload measurement plan. Retain the distinction between schedule approval, publication, current trust and GA activation. A production readiness claim requires those blockers to be resolved with evidence.

**D14 stops here.** No next feature milestone, broad cleanup, C++ work or Git checkpoint is started automatically.

## 21. Separately authorized Git checkpoint review

The acceptance report above records the pre-checkpoint D14 testing session. A later explicit user instruction authorizes two Git checkpoint commits and a normal push to `origin/main`; its inspection includes a fresh fetch against D13 baseline `7a0c3eaf32dc3cc350c04871fdb6f8dd72c43bb4`. This does not rerun application tests or change their attribution. All recorded results, the eight unsuccessful command records and the documented older D9 teardown flakiness were reviewed. Fictional institutional providers and PostgreSQL limitations remain unchanged.

The reviewed inventory is 91 paths: six implementation/testing files (two UI wording fixes, three integration test files and the runner), plus 85 documentation/evidence files including the manifest. The protected preference file is excluded. No test output or screenshot was removed or rewritten. Only this checkpoint annotation and manifest integrity metadata were added during checkpoint preparation.

The 90 original artifact hashes matched before annotation. The manifest preserves raw working-copy SHA-256 and adds Git blob SHA-1, content SHA-256 and byte length for every artifact. Git's existing `core.autocrlf=true` normalizes CRLF text to LF in committed blobs; both representations are explicitly recorded without rewriting original capture files. This report's artifact hash was refreshed after this annotation; its earlier hash is retained in checkpoint metadata. The manifest excludes itself. Post-staging and post-commit checks must compare actual Git blobs to those recorded values and verify the exact inventories before push. The original pre-test Git index baseline is historical; index/HEAD changes are now limited to the separately authorized checkpoint.
