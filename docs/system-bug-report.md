# System bug report

Audit date: 2026-10-14. MSU-IIT CCS Faculty Scheduling Decision-Support System.

## Audit scope and environment

Windows / PowerShell, Python 3.14.2 in the project virtual environment, React/Vite/TypeScript and headless Microsoft Edge. Test runs use real FastAPI TestClient requests and the existing Edge DOM/pointer harness with isolated API fixtures. All test preference/settings/checkpoint/history writes go to temporary destinations.

No backend/frontend listener was available on the usual local ports at audit start. The in-app browser connection was attempted using the browser skill and failed because of unavailable sandbox metadata. This audit therefore does not claim to have reproduced failures against a currently running institutional worker or to have resumed a particular user's run. No full production GA was executed.

Seven confirmed defects are counted below: six application defects and one browser-test defect. Six are fixed after Phase 3F.2; BUG-004 remains partially fixed and blocked on real authentication. Placeholder features, missing PostgreSQL and deployment limitations are tracked as requirements in [roadmap status](implementation-roadmap-status.md), not inflated into bug totals.

The tests explicitly labelled `test_audit_...` characterize unresolved defects. They document current behavior and must be changed to enforce the desired secure/correct behavior when those defects are separately fixed. A passing characterization test does not mean the defect is acceptable.

## BUG-001

- **BUG ID:** BUG-001
- **TITLE:** GET preference/settings requests create or rewrite persistent files.
- **SEVERITY:** MEDIUM
- **AFFECTED PAGE / ENDPOINT:** Faculty Preferences; GET `/preferences/{faculty_code}`, GET `/preferences/ga-settings`.
- **ENVIRONMENT:** Actual FastAPI application, temporary empty preference/settings destinations and an existing one-record preference file.
- **REPRODUCTION STEPS:** Point preference/settings storage to temporary paths. GET a faculty without a saved preference twice. GET settings without a saved settings file. Repeat faculty GET with a pre-existing preference record for another faculty.
- **EXPECTED RESULT:** Return default values in memory; no file is created or modified until an explicit save.
- **ACTUAL RESULT:** Before fix, GET wrote the default record/settings. Reading a missing faculty rewrote the whole existing preference list.
- **ERROR MESSAGE / STACK TRACE:** No API error. Regression failed at `assert not getattr(preferences, file_attribute).exists()` and `assert PREFERENCE_FILE.read_bytes() == before`; three failures reproduced before fix.
- **ROOT CAUSE:** `get_faculty_preference` appended and called `_write_preferences`; `_read_ga_settings` called the writer when the file was missing.
- **FILES INVOLVED:** `backend/routers/preferences.py`; `backend/tests/test_system_audit.py`.
- **FIX STATUS:** FIXED. GET now returns the same default DTO without persistence. PUT remains the explicit save path. No default values/weights were changed.
- **REGRESSION TEST:** `test_default_reads_do_not_create_files` (faculty/settings parameters), `test_reading_missing_faculty_preserves_existing_preferences`, `test_explicit_save_still_persists_defaults`. All passed; existing preference validation/round trips passed.
- **REMAINING RISK:** Corrupt-read handling and simultaneous explicit PUT writes remain separate persistence risks; see BUG-005 and U-002.

## BUG-002

- **BUG ID:** BUG-002
- **TITLE:** Schedule viewers expose internal external-instructor IDs and integral-float faculty codes.
- **SEVERITY:** LOW
- **AFFECTED PAGE / ENDPOINT:** Admin Faculty Management viewer, Room Assignments calendar, Generated Schedule table/filter.
- **ENVIRONMENT:** Real React UI in isolated Edge, loaded schedule fixture using the actual saved-result field shape; source inspection confirms existing saved rows carry `external:eddie-bouy-palad` plus `faculty_name`.
- **REPRODUCTION STEPS:** Load a schedule with a normal faculty code `7.0` and an external ITE184 assignment for `external:eddie-bouy-palad`. Open /admin/faculty, /admin/rooms and /admin/schedules.
- **EXPECTED RESULT:** Normal privacy label “Faculty 7”; “Atty. Eddie Bouy Palad · Preassigned Instructor”; no raw internal external identifier.
- **ACTUAL RESULT:** Before fix, selectors/calendars/table displayed `7.0` or the raw external ID. The saved result already contained a usable external name.
- **ERROR MESSAGE / STACK TRACE:** Browser assertions failed for readable faculty labels/Palad name and hidden internal identifier. No runtime exception from the application itself.
- **ROOT CAUSE:** Old formatter recognized only digit strings and returned other values unchanged. ScheduleView rendered the stored faculty identifier directly. ScheduleEntry type omitted the available optional name.
- **FILES INVOLVED:** New `frontend/src/components/schedule/facultyDisplay.ts`; `WeeklySchedule.tsx`; `FacultyManagement.tsx`; `ScheduleView.tsx`; `GenerationHistory.tsx` import adapter; `frontend/src/types/ga.ts`; frontend regression files.
- **FIX STATUS:** FIXED. Shared presentation adapter normalizes integral codes, preserves normal privacy labels, uses optional external names, provides the established CCS Palad legacy fallback, and labels unknown external IDs “Preassigned Instructor.” Stored identifiers are untouched.
- **REGRESSION TEST:** Two `facultyDisplay.test.mjs` contracts and the browser audit faculty/room/table scenarios. Failed before fix; passed after fix.
- **REMAINING RISK:** A legacy selector without name metadata cannot name an unknown external instructor; it safely uses the generic role label. Future multi-college selectors should carry authoritative display metadata instead of extending the CCS fallback.

## BUG-003

- **BUG ID:** BUG-003
- **TITLE:** Faculty schedule filter compares display labels with assignment identifiers and excludes external instructors.
- **SEVERITY:** MEDIUM
- **AFFECTED PAGE / ENDPOINT:** /admin/schedules; GET /api/faculty/ metadata consumed by the faculty filter.
- **ENVIRONMENT:** Real React browser test with non-empty faculty metadata and schedule rows using string/integral-float numeric codes plus external preassignment.
- **REPRODUCTION STEPS:** Load faculty metadata containing code 7. Load schedule rows assigned to `7` or `7.0`. Select the visible “Faculty 7” option. Inspect whether the external instructor is offered as a filter option.
- **EXPECTED RESULT:** Show Faculty 7's assignments; allow selection of the external instructor actually present in the schedule.
- **ACTUAL RESULT:** Before fix, the metadata branch used value `Faculty 7` and compared it directly to `entry.faculty`. Matching rows disappeared. Returning only normal faculty metadata also removed external filter options.
- **ERROR MESSAGE / STACK TRACE:** Browser regression timed out with “Faculty metadata label did not match schedule identity.” No HTTP error; the mismatch was local UI state.
- **ROOT CAUSE:** Human-readable labels were used as identity values, and the metadata-only branch discarded schedule-specific instructor identities.
- **FILES INVOLVED:** `frontend/src/pages/admin/ScheduleView.tsx`; new `components/schedule/facultyDisplay.ts`; `frontend/tests/gaMonitoring.browser.test.mjs`; `facultyDisplay.test.mjs`.
- **FIX STATUS:** FIXED. Options union metadata and scheduled identities, normalize legacy/integral codes into comparison keys, and display separate readable labels. Search also matches readable names. Assignment data, faculty eligibility and GA objects are unchanged.
- **REGRESSION TEST:** “audit metadata faculty filter matches schedule IDs and includes external instructors”; normal selection returns CCC121 only, external selection returns ITE184 only. Failed before fix and passed afterward; key normalization contract covers `7`, `7.0`, `Faculty 7`.
- **REMAINING RISK:** An unassigned metadata faculty legitimately has no schedule rows. Stable UUID-backed schedule assignments need an explicit adapter before future schema migration.

## BUG-004

- **BUG ID:** BUG-004
- **TITLE:** Backend has no authentication/ownership enforcement; preference mutations are accepted anonymously.
- **SEVERITY:** HIGH
- **AFFECTED PAGE / ENDPOINT:** All admin/faculty portals and backend resources; directly reproduced with GET/PUT `/preferences/0`. GA control/history/export routes also have no auth dependency in source.
- **ENVIRONMENT:** Actual FastAPI application, temporary preference file, client without credentials or authorization headers.
- **REPRODUCTION STEPS:** Submit PUT /preferences/0 with an empty valid preference update and no login. Read that record. Inspect OpenAPI security definitions and route dependencies. Inspect /faculty/preferences route identity wiring.
- **EXPECTED RESULT:** In an institutional multi-user application, require authenticated identity and an authorized faculty/admin role. Faculty must not edit another faculty or administrator-only priority.
- **ACTUAL RESULT:** Anonymous PUT/GET return 200. No security scheme or server role checks exist. Faculty self-service defaults to code 0; portal labels are not identity binding.
- **ERROR MESSAGE / STACK TRACE:** None; unauthorized access is accepted. Source confirms the deferred role implementation.
- **ROOT CAUSE:** Authentication/authorization is documented future work; frontend adminMode/role labels do not enforce backend permissions.
- **FILES INVOLVED:** `backend/main.py`, backend routers, `frontend/src/routes/AppRoutes.tsx`, `frontend/src/pages/faculty/Preferences.tsx`, admin/faculty layouts and editor.
- **FIX STATUS:** PARTIALLY FIXED / AUTHENTICATION INTEGRATION BLOCKED (Phase 3F.2). Anonymous preference/settings PUT and preference DELETE are denied with 401. Server-principal role/ownership rules reject other-faculty writes and faculty priority/settings/reset changes with 403. No real credential/account provider is installed; production preference writes remain locked. Other resource authorization still needs Phase 4.
- **REGRESSION TEST:** test_preference_integrity.py: spoofed headers/anonymous writes, own-vs-other faculty, administrator-only fields; updated test_system_audit.py. Real FastAPI tests use isolated trusted dependency overrides only for positive cases. Browser verifies 401 retains draft and the self-service route selects no default faculty.
- **REMAINING RISK:** No production login, account binding or full resource authorization exists. Public reads and GA controls still need Phase 4 policy. Do not claim this deny-by-default groundwork is production authentication.

## BUG-005

- **BUG ID:** BUG-005
- **TITLE:** Corrupt/unreadable preference storage is treated as empty and can be silently replaced on save.
- **SEVERITY:** HIGH
- **AFFECTED PAGE / ENDPOINT:** GET /preferences; GET/PUT /preferences/{faculty_code}; Faculty Preferences save.
- **ENVIRONMENT:** Actual FastAPI application with temporary preference file containing invalid JSON `{broken`.
- **REPRODUCTION STEPS:** Put malformed bytes in a temporary preference file. GET /preferences. PUT /preferences/0 with a valid empty update. Read the resulting file.
- **EXPECTED RESULT:** Report an explicit storage-integrity/unavailable error and preserve original bytes; saving must not treat a failed read as an empty database.
- **ACTUAL RESULT:** GET returns [] with 200. PUT succeeds and replaces the malformed contents with a fresh valid record, with no indication that prior data could not be read.
- **ERROR MESSAGE / STACK TRACE:** JSONDecodeError/OSError is caught and discarded by `_read_preferences`; no error is surfaced to the client.
- **ROOT CAUSE:** `_read_preferences` conflates missing storage with corrupt/unreadable storage. PUT subsequently rewrites the whole returned list.
- **FILES INVOLVED:** `backend/routers/preferences.py` (`_read_preferences`, `_write_preferences`, update route); `backend/tests/test_system_audit.py`.
- **FIX STATUS:** FIXED (Phase 3F.2). Malformed/unreadable/duplicate/invalid storage fails with 503 and keeps original bytes. Updates validate merged records under a process lock, atomically replace fsynced temporary files, preserve omitted and unrelated fields, and reload after commit.
- **REGRESSION TEST:** test_preference_integrity.py: corrupt/invalid/duplicate records, denied reads, malformed and extra-field payloads, invalid IDs, fsync/replace failure, partial updates, unrelated-record preservation, concurrent writes and reload. Updated test_system_audit.py verifies preserved corrupt bytes.
- **REMAINING RISK:** The lock covers one backend process. Multiple independent writers remain unsupported. An external editor or power-loss/storage issue still needs backup/recovery procedures; no automatic reset or destructive repair is provided.

## BUG-006

- **BUG ID:** BUG-006
- **TITLE:** Disabled preferred-day/time checkboxes do not disable scoring for subject-specific calendar blocks.
- **SEVERITY:** MEDIUM
- **AFFECTED PAGE / ENDPOINT:** Faculty Preferences “Consider preferred days/times”; fitness interpretation for exact subject blocks.
- **ENVIRONMENT:** Existing scorer helper invoked outside optimization with a Monday 09:00–11:00 lecture, a Tuesday 10:30 preferred subject block, both enable flags false, day importance 4/time importance 3, existing weights 5/10 and priority multiplier 1.
- **REPRODUCTION STEPS:** Retain a subject calendar placement and nonzero importance. Disable both day/time preferences. Evaluate the existing subject-block scoring helper with a placement mismatch.
- **EXPECTED RESULT:** Checkbox language implies those disabled preferences no longer contribute, or the UI must explicitly state that subject placements have independent scoring semantics.
- **ACTUAL RESULT:** The exact-block path adds day penalty 20 and time penalty 30 despite both flags being false. General preferred periods respect the flags. The reporting documentation already acknowledges this difference.
- **ERROR MESSAGE / STACK TRACE:** None; observed helper result is `{has_exact_blocks: true, day_penalty: 20, time_penalty: 30}`.
- **ROOT CAUSE:** `_score_exact_subject_schedule_blocks` checks importance but not use_day_preference/use_time_preference. General day/time paths are skipped when exact blocks exist.
- **FILES INVOLVED:** `backend/genetic_algorithm/operators/FitnessFunction.py`; `frontend/src/components/faculty/FacultyPreferenceEditor.tsx`; `preferenceModel.ts`; fitness reporting adapter/documentation.
- **FIX STATUS:** FIXED for corrected policy 2 in Phase 3F.2. Explicit false day/time flags independently produce zero exact-block contribution. Missing legacy flags retain their previous exact-block influence; general preference defaults are unchanged. Existing checkpoints intentionally continue policy 1 to preserve their recorded scoring/RNG trajectory.
- **REGRESSION TEST:** test_preference_toggles.py: independent flags, normalization, missing flags/zero importance, full breakdown reconciliation, legacy source fingerprint and exact legacy pause/resume/RNG/call equivalence. test_fitness_reporting.py verifies corrected vs original reporting and preserved observations after unsupported future source changes.
- **REMAINING RISK:** Policy-1 paused runs retain original behavior and are labelled legacy. No historical scores are rewritten. New scores can differ by precisely the removed disabled contributions; new evolution can consequently choose different candidates.

## BUG-007

- **BUG ID:** BUG-007
- **TITLE:** Browser stop regressions click Generate Schedule before asynchronous discovery enables it.
- **SEVERITY:** LOW
- **AFFECTED PAGE / ENDPOINT:** Test harness for Generate Schedule; not a reproduced product lifecycle defect.
- **ENVIRONMENT:** Isolated Edge GA browser suite; latest result loads before discovery completion.
- **REPRODUCTION STEPS:** Reload after stopped-result scenario. Wait only for “Generations Completed” text. Immediately find/click the exact “Generate Schedule” button. The dependent disconnect scenario repeats the same assumption.
- **EXPECTED RESULT:** The test waits for the UI's start action to be present/enabled before clicking.
- **ACTUAL RESULT:** During discovery the exact button label is absent; test throws and the next dependent test also fails.
- **ERROR MESSAGE / STACK TRACE:** `TypeError: Cannot read properties of undefined (reading 'click')`, initially at browser test lines 232/246.
- **ROOT CAUSE:** Result-load readiness was mistaken for independent backend-discovery readiness. Product correctly prevents starting before discovery settles.
- **FILES INVOLVED:** `frontend/tests/gaMonitoring.browser.test.mjs`.
- **FIX STATUS:** FIXED. Added condition-based waits for the enabled Generate Schedule button in both scenarios. No arbitrary sleeps, weakened assertions or product control changes.
- **REGRESSION TEST:** Existing “stop before initialization…” and “disconnect after a stop request…” cases. Both failed in the first reproduction run and passed after synchronization correction in subsequent runs, including the final 52-result suite.
- **REMAINING RISK:** Browser timings still vary; retain bounded condition waits and report actual product failures independently of setup races.

## Earlier unconfirmed findings and current follow-ups — excluded from confirmed bug totals

| ID | Suspected issue / environment | Evidence and what was not reproduced | Next verification |
|---|---|---|---|
| U-001 | Production-sized pause/checkpoint/history CPU/memory/latency contention | Docs admit large graph/cold validation cost. No active backend or production-size run was available; current tests are bounded fixtures. This is not proof of a present timeout/deadlock. | Isolated pinned-runtime benchmark, concurrent status/log/history/checkpoint reads, memory profiles; no timeout-only workaround. |
| U-002 | Concurrent explicit preference PUT lost updates / interrupted direct JSON writes | Original direct writes were unconfirmed for races. Phase 3F.2 now verifies serialized concurrent updates and interrupted atomic replacement in temporary storage. Multiple independent processes remain unsupported. | Temporary-file concurrency/atomic-failure tests before changing persistence adapter; never interrupt production writes. |
| U-003 | History queue/budget gaps and orphan file after index-commit interruption | Limits/gaps/orphans are documented design limitations, not an observed new corruption incident. Existing tests exercise index failure. Current user archive was not altered. | Define retention/completeness requirements, inspect existing archives read-only, non-destructive repair/backup policy. |
| U-004 | Original Phase 3E.1 “History could not be read or validated” 422 | That incident's original response/traceback was unavailable; its documentation explicitly does not establish the original failing request/root cause. Do not report an invented corrupted checkpoint/history cause. | Capture operation, response code/traceback and fingerprints if it recurs against the correct process. |
| U-005 | Settings JSON parse error silently uses defaults | RESOLVED in Phase 3F.2: malformed settings now return 503 and remain byte-for-byte preserved on an authorized attempted save (test_corrupt_settings_cannot_be_reset_by_an_authorized_save). | Isolated settings corruption/read/write tests and fail-closed policy review; do not change live weights while diagnosing. |

## Historical incidents and verified correction evidence

These are prior milestones, not additional newly reproduced bugs counted above:

- Phase 3D.1 paused-refresh hydration: correction documented; current browser scenarios recover identity/metrics/history and require verified resume.
- Phase 3D.2 conflicting stop/pause states: current control/browser tests reject resuming STOPPING and reconcile authoritative status.
- Phase 3D.3 stale paused console after resume: run-scoped cursor logs and reconnect tests pass, including ordering/duplicates/epoch/truncation.
- Phase 3E.1 costly history/checkpoint validation: bounded verification reuse/detached templates documented; original historical 422 remains U-004.
- Phase 3E.2 Unicode diagnostic failure: current cp1252/charmap tests complete real validation and preserve real errors.

Other confirmed non-product findings: README still describes preference resizing and older architecture documents list six fitness components; current Phase 2/3F source has duration locks/eight terms. Dedicated management/faculty routes are placeholders. Database dependencies do not implement PostgreSQL. Build retains the large-chunk warning, and existing unrelated hook lint findings remain. These are documentation/implementation-quality findings, not additional runtime defect totals.

## Audit fixes and files changed

Audit-specific changes (distinct from pre-existing Phase 3F working-tree changes):

1. `backend/routers/preferences.py` — read-only default GET behavior.
2. `backend/tests/test_system_audit.py` — eight real API/source-rule reproductions/regressions, with temporary storage.
3. `frontend/src/components/schedule/facultyDisplay.ts` — shared display/comparison adapter.
4. `frontend/src/components/schedule/WeeklySchedule.tsx` — external name rendering and formatter import; calendar geometry/merging untouched.
5. `frontend/src/pages/admin/FacultyManagement.tsx` — formatter import only.
6. `frontend/src/pages/admin/ScheduleView.tsx` — faculty keys vs labels, external option union, readable names/search.
7. `frontend/src/pages/admin/GenerationHistory.tsx` — shared formatter import only during this audit.
8. `frontend/src/types/ga.ts` — optional existing `faculty_name` payload field.
9. `frontend/tests/facultyDisplay.test.mjs` — identity/privacy contracts.
10. `frontend/tests/gaMonitoring.browser.test.mjs` — five audit checks, plus synchronization waits.
11. `frontend/package.json` — include display contract tests in test:ga; no dependency changes.
12. `docs/phase-3f-fitness-analysis.md` — clarify absence of backend authorization.
13. `docs/implementation-roadmap-status.md` — reconstructed scope/status matrix and sequence.
14. `docs/system-bug-report.md` — this report.

The initial working tree already contained Phase 3F implementation changes and a modified `backend/data/faculty_preferences.json`. Those existing changes were preserved; they are not changes made by this audit.

## Phase 3F.1 verification and preservation (historical)

- Initial API reproduction: **3 failed / 4 passed** before the read-only correction; later capability test raises the final audit set to 8 cases.
- Initial browser reproduction: three label failures plus a test readiness race; a second reproduction isolated the broken metadata filter as well. Failures were investigated, not relabelled as success.
- Final current backend: **207 distinct tests passed** (108 + 96 + 3); final audit-only rerun **8 passed**, not double-counted.
- Frontend contracts/models: **48 GA/report/display + 19 preference passed**.
- Browser: **52 GA/audit + 22 preference results passed**, including parent results.
- Build passed. Focused helper/calendar/schedule/history/type lint had **0 errors**, existing schedule dependency warnings. FacultyManagement's import-only change retains its pre-existing set-state-in-effect lint error; full-project lint is not claimed clean.
- Observation/logging equivalence verifies unchanged RNG state, fitness-call counts, scores and schedules. No new optimization-loop fitness evaluations were introduced.
- SHA-256 baseline verification: **136/136 protected files unchanged**, covering engine source, seven fingerprinted services, notebooks, all current source data, checkpoints and saved artifacts.
- No institutional schedules/preferences/history/checkpoints were overwritten, migrated or deleted. No GA equations, weights, operators, hard gates, checkpoint format or RNG behavior were changed.
- No commit/push and no Phase 3G implementation.


## Phase 3F.2 verification and current closure

The preceding audit verification/file list is historical Phase 3F.1 evidence. Current implementation and complete changed-file/manual acceptance details are in [Phase 3F.2](phase-3f2-data-integrity-report.md).

- **370 distinct backend tests passed**: 131 metadata/preference/report/integrity/toggle/audit cases, 96 domain/operator regressions, 142 Phase 3B–3E monitoring/control/checkpoint/history/log/Unicode regressions and one genuine isolated FastAPI/Edge integration. Focused reruns are not added again.
- **70 frontend contracts/models passed**; **23 preference + 52 GA browser results passed**. One initial GA browser run had recovery timeouts; its application root cause remains unconfirmed, and the same implementation passed on rerun with diagnostics.
- Build and focused changed-file lint passed; pre-existing unrelated lint and bundle warnings remain.
- **133/136 protected files unchanged**. Exactly three authorized source exceptions: FitnessFunction.py, FrozenInputs.py and ga_checkpoint_service.py for minimal flag gating and versioned compatible continuation. Existing data/configurations/notebooks/saved artifacts/checkpoints/history remain unchanged.
- Corrected policy 2 changes only explicitly disabled exact day/time contributions. Legacy policy 1 continuation matches uninterrupted legacy results, RNG and counted service fitness calls. No additional optimization-loop scoring/RNG draw or operator/hard-rule change was introduced.
- New checkpoints add only an optional frozen scoring-policy marker under existing schema 1; no old checkpoint/history is rewritten and compatibility/integrity checks remain mandatory.
- BUG-005/006 are corrected; BUG-004 remains partially fixed/blocked on real Phase 4 authentication. No production credential provider exists, so preference/settings writes remain locked; positive identity tests use isolated server overrides.
- No commit/push, database migration, C++ implementation, notebook editing or Phase 3G work.

## Totals and next actions

| Confirmed bug category | Count |
|---|---:|
| Application defects confirmed | 6 |
| Test-harness defect confirmed | 1 |
| **All confirmed defects** | **7** |
| **Fixed** | **6** |
| **Unresolved / partially fixed and blocked** | **1** |

Prioritize completing BUG-004 with real Phase 4 account/role/ownership integration. BUG-005 now preserves corrupt data and BUG-006 uses corrected policy 2 with legacy policy 1 continuation. Then proceed through identity/term/database design, authorized management, faculty portal/publishing/class lists, and evaluation/deployment qualification. This report recommends those stages; it does not start Phase 3G.

