# Dashboard-first D4: GEC review calendar and resource reconciliation

Implemented **2026-10-21, Asia/Manila**, against HEAD **f3a07e5461430caab7a3998a2fd9d16b0aa1287d**, branch main. **D4 IMPLEMENTED; FINAL FOCUSED BACKEND, FRONTEND, BROWSER, BUILD, LINT AND REGRESSIONS PASS.** Pre-existing uncommitted D3 work and the dirty protected preference file are retained. No PostgreSQL execution, persistence, confirmation, GA activation or Chair workflow was added.

## Objectives, sources and acceptance boundaries

D4 extends the administrator-only **/admin/external-schedules** temporary workflow with a weekly review calendar, filters, source details and explicit reconciliation to recognized resources. It preserves source rows rather than silently editing imported labels or combining adjacent meetings.

Inspected: [D1](dashboard-d1-implementation.md), [D2](dashboard-d2-implementation.md), [D3](dashboard-d3-implementation.md), [confirmed scheduling workflows](phase-4c-confirmed-scheduling-workflows.md), existing metadata/identity/authentication services, the shared weekly viewer, existing FullCalendar use, fixed-section and preassignment mechanisms, README, roadmap, bug report and [documentation standard](DEVELOPMENT_DOCUMENTATION_STANDARD.md).

| Requirement | Evidence |
|---|---|
| D4-CAL: read-only weekly patterns, separate overlapping rows, exact times and source details | Calendar/model contracts; D4-B01/B02/B08/B12/B15; reviewed screenshots |
| D4-FILTER: section, supplying college, subject, Draft/Tentative and resource-state filters | Pure filter tests and D4-B03/B04; filtering never changes full-batch validation |
| D4-MAP: recognized resources only, ambiguity preserved, explicit mappings | Real API/service tests; D4-B05–B09/B14 |
| D4-PROV: original hash/rows and stale-reference protection | Receipt tamper/restart/reference-drift tests and strict client provenance checks |
| D4-SAFE: authentication, no writes/activation and preservation | Real session/Origin/CSRF tests; no-write/RNG assertions; baseline/hash manifest |

The original WeeklySchedule component merges adjacent entries and uses half-hour placement. It would obscure import-row boundaries and round some external times. D4 therefore reuses the project's already installed **FullCalendar React/time-grid library** for a dedicated review wrapper. WeeklySchedule, faculty schedules and GA calendars are unchanged. This is a rendering adaptation, not a second scheduling engine.

## Exact implementation files

| Path | Change |
|---|---|
| backend/schemas/external_schedule.py | Modified: optional receipt on the existing intake response; bounded mapping DTOs, five resource states and version-2 review projection. |
| backend/routers/external_schedules.py | Modified: protected POST /review, 2 MiB review-body cap and shared duplicate-JSON rejection; existing intake limits remain 1 MiB. |
| backend/services/external_schedule_service.py | Modified: issues a process-signed receipt after successful intake and permits internal reuse of a captured reference context without re-signing. Parser/domain behavior retained. |
| backend/services/external_schedule_review_service.py | New: receipt verification, reference digest, explicit recognized-ID resolution, whole-batch conflict projection and original-source preservation. |
| backend/tests/dashboard/test_external_review.py | New: 32 provenance, resource-resolution, conflict, authorization and preservation cases. |
| frontend/src/api/externalSchedules.ts | Modified: optional intake receipt; strict review DTOs; cancellable authenticated review POST; original-source/hash/row checks. |
| frontend/src/pages/admin/ExternalSchedules.tsx | Modified: mounts a fresh review workspace per preview; labels original intake findings separately from reconciled findings. |
| frontend/src/components/schedule/ExternalScheduleReview.tsx | New: FullCalendar wrapper, five filters, source detail selector, explicit mapping controls and complete-batch revalidation. |
| frontend/src/components/schedule/externalReviewModel.ts | New: pure filtering/event projection; exact recurring clock times, independent source IDs and overlap styling. |
| frontend/tests/externalReview.fixtures.mjs | New: explicitly fictional review sources/metadata/projections; public synthetic receipt, not a real backend signature. |
| frontend/tests/externalReview.test.mjs | New: eleven focused API/provenance/filter/calendar contracts. |
| frontend/tests/externalReview.browser.test.mjs | New: fifteen actual rendered Edge/FullCalendar scenarios with synthetic HTTP responses. |
| frontend/package.json | Modified: adds test:external:review and test:external:review:browser; dependencies/lockfile unchanged. |
| docs/testing/dashboard-d4/run_checks.py | New: whitelisted-environment evidence runner for D4 and existing regressions. |

Evidence/documentation created: this report; [baseline](testing/dashboard-d4/preservation-baseline.json); [manifest](testing/dashboard-d4/manifest.json); timestamped command records; original PNGs and final/intermediate browser records under docs/screenshots/dashboard-d4. The manifest enumerates paths and SHA-256 hashes, including earlier failed attempts and superseded captures.

## Working UI

Run a manual/CSV/XLSX preview on the existing administrator page. With the current backend receipt, the calendar automatically requests a full source review. Older fixture/backend responses without receipts remain usable as D3 intake previews and display an honest calendar-unavailable notice.

The calendar shows Monday–Saturday weekly patterns using exact submitted times. Simultaneous meetings use separate lanes; adjacent meetings retain separate source-row identities. Resource-overlap findings receive red cards/text, including provisional unresolved-section warnings. Invalid day/time patterns remain visible in the source detail selector and an explicit not-plotted list rather than disappearing. Off-grid times may be displayed exactly, while their existing unsupported-GA-grid warning remains.

Filters cover recognized sections or literal unresolved section references, supplying college, subject, Draft/Tentative intent and resource states. “Provided resources resolved” allows missing optional resources; it does not mean verified dates, complete institutional conflict coverage or approval. Filters affect the calendar/visible-row list only; all source rows are revalidated together. Source reconciliation can intentionally select any row in the original batch independently of filters.

Click an event or its Details button to inspect original normalized subject/title, supplying college/term, days/times, intake status, notes/reference, source filename/hash and discrepancy provenance. Source-row numbers come from the original preview. Mapping menus show registered aliases or IDs beside labels so identical names can be distinguished.

Each original section reference can map to one existing section ID. Faculty/instructor and room mappings are optional and available only from the recognized metadata inventory. A mapping change aborts pending work and removes the previous calendar until **Revalidate all resource mappings** returns a full current result. Clearing a mapping restores source-key interpretation rather than retaining a hidden previous choice. New previews, navigation and refresh discard mappings. No local/session storage contains intake data.

There are no drag/resize, save, confirm, lock or activate controls. Generic weekly rendering uses a hidden internal reference week because FullCalendar requires a date anchor; date headers and date-based navigation are disabled. The projection DTO contains recurring weekdays/clock times, not invented academic dates.

## API and temporary provenance design

Existing intake endpoints remain administrator-only and return schema_version 1 with an optional review_token. New **POST /api/external-schedules/review** accepts only:

- review_token: a receipt issued by this backend process for a successfully parsed preview.
- mappings: up to 200 distinct original source-row references, with up to twelve indexed section-reference selections and optional room/instructor IDs per row.

The endpoint uses the existing real authenticated session, administrator role, exact Origin and CSRF checks. Unknown IDs, duplicate row mappings, invalid section slots, duplicate JSON keys and extra client provenance/actor fields fail closed. The body limit is **2 MiB**, receipt length at most **1,600,000 characters**; D3 upload/manual limits remain **1 MiB / 200 rows**.

A receipt encodes the D3-normalized input rows, physical source-row references, source kind/name, exact uploaded-file SHA-256, source parser version and reference-inventory digest. A process-local HMAC authenticates that bundle. The backend retains only its random process key, not source batches, uploaded files or a preview cache. Receipts are returned to the authorized caller and are never rendered in the UI, archived in evidence or used as authentication credentials. They are encoded, not encrypted, and belong to the sensitive temporary preview state.

Reconciliation verifies the receipt before reading current references. A changed reference inventory or loaded fixed-section projection returns **409 PREVIEW_REFERENCES_CHANGED**; altered/foreign-process receipts return **409 PREVIEW_RECEIPT_INVALID**. The client must preview the original source again. A process restart invalidates prior receipts; this prototype requires one backend process or returning requests to the issuing process. No shared secret, credential-file loading or durable storage was introduced.

Successful review responses have **schema_version 2**, projection_version d4.1, source_parser_version d3.1, preview_only true, persisted false, activated false, reference digest and all reviewed rows. They retain the source hash/name/kind and D3-normalized original fields without mapping substitutions. Raw file bytes are not retained, so the hash is not a reconstruction/archive of the original file. A receipt establishes continuity of this preview operation, not authenticity or approval by the supplying college.

The frontend validates the response and verifies the original row set/values, source kind/name/hash and non-activated flags before rendering. It never sends rewritten original rows or a client-selected source hash to the review endpoint.

| Condition | Result |
|---|---|
| Valid administrator/session/Origin/CSRF and current receipt | 200, complete transient projection |
| Anonymous, expired/invalid session | 401 before review |
| Faculty or failed Origin/CSRF | 403 |
| Unknown/ambiguous selected ID, duplicate mapping/slot, malformed JSON/structure | 422, no partially applied mappings |
| Oversized review request | 413 |
| Wrong content type | 415 |
| Tampered/restarted receipt or reference drift | 409, source must be re-previewed |
| Recognized-reference service unavailable | Existing sanitized 503 |

## Resource identity and conflict semantics

Resource states are explicit:

| State | Meaning |
|---|---|
| Resolved | Existing canonical ID uniquely recognized or explicitly selected |
| Unresolved | Unknown reference or an instructor-name suggestion requiring selection; no ID assigned |
| Ambiguous | Several recognized candidates, or a non-unique canonical lookup; no first-match selection |
| Unsupported | A nonempty reference has no available authoritative inventory for that resource category |
| Missing optional resource | Optional room/instructor omitted; absence is not identity resolution |

Section codes resolve only through existing recognized section metadata, rooms through their current natural keys, and instructors through canonical IDs or registered display-code aliases. Instructor names alone never select/generate a faculty UUID, even if only one name candidate currently exists. Explicit selections must identify exactly one current metadata record. No resource is created from a label, row order or alias, and existing account bindings and legacy UUID formulas are unchanged.

The existing D3 parser/domain validator is reused with a captured context. D4 replaces resource-dependent findings with fresh canonical checks. Known section/faculty/room overlaps compare real recognized IDs; identical unresolved section text yields a clearly provisional POSSIBLE_UNRESOLVED_SECTION_OVERLAP without inventing an identity. Duplicate meetings and repeated mappings to the same section are flagged. Half-open intervals permit adjacency.

The loaded fixed-section comparison is also performed using mapped section IDs, without modifying blocks. PreassignedAssignment remains an instructor/room declaration and is never treated as a fixed meeting time. D4 does not check a new GA candidate or compile external reservations. Faculty/room availability behavior is unchanged.

Academic terms, effective dates, exceptions and shared cross-college directories remain unverified. Different unverified term labels cannot suppress potential same-week clashes. This is conservative weekly review, not accepted institutional hard-constraint validation.

## Tests and environment

Runtime: Windows, Python **3.14.2**, SQLite **3.50.4**, Node **v24.11.1**, Vite **8.2.2**, existing FullCalendar **6.1.21**, headless Edge **155.0.4283.62**. Exact command arrays, child cwd, ISO start/end timestamps, durations and exit codes are retained in the linked artifacts.

Invoke from repository root via .venv/Scripts/python.exe -B docs/testing/dashboard-d4/run_checks.py followed by a selection:

| Selection | Final result | Evidence |
|---|---|---|
| backend | **122 passed**, 32 D4 + 61 D3 + 29 D2; 0 failed/skipped; pytest 22.18 s | [Command](testing/dashboard-d4/20261021T193048577215+0800-backend/command.json) |
| backend-regressions | **46 passed**, 0 failed/skipped; existing real HTTP authentication browser wrapper plus seven GA control cases included | [Command](testing/dashboard-d4/20261021T192949768046+0800-backend-regressions/command.json) |
| contracts | **110 passed**, 11 D4 + 99 existing; 0 failed/skipped | [Command](testing/dashboard-d4/20261021T192850190990+0800-contracts/command.json) |
| browser | **15 D4 scenarios passed**, plus one parent wrapper | [Final command](testing/dashboard-d4/20261021T193418759578+0800-browser/command.json) |
| d1-browser | **16 scenarios passed**, plus one parent wrapper | [Command](testing/dashboard-d4/20261021T192952905704+0800-d1-browser/command.json) |
| d2-browser | **13 scenarios passed**, plus one parent wrapper | [Command](testing/dashboard-d4/20261021T192951721172+0800-d2-browser/command.json) |
| d3-browser | **15 scenarios passed**, plus one parent wrapper | [Command](testing/dashboard-d4/20261021T192951865651+0800-d3-browser/command.json) |
| ga-browser | **51 scenarios passed**, plus one parent wrapper | [Command](testing/dashboard-d4/20261021T192955321225+0800-ga-browser/command.json) |
| build | **PASS**, TypeScript/production Vite build, 219 modules | [Final command](testing/dashboard-d4/20261021T193415632019+0800-build/command.json) |
| lint | **PASS**, no findings in four changed/new TS/TSX modules | [Final command](testing/dashboard-d4/20261021T193416872014+0800-lint/command.json) |

The backend suite exercises actual FastAPI ASGI requests, real password verification/session lookup, role/Origin/CSRF enforcement and no-write behavior with **temporary SQLite and synthetic metadata**. PostgreSQL/default identity engines are explicitly denied by the existing dashboard fixture. D4 cases cover tampered/restarted receipts, reference drift, deterministic receipt generation, preserved hashes/physical CSV rows/original inputs, ambiguous names, unsupported versus missing optional resources, invalid mappings, canonical section/faculty/room overlaps, adjacency, invalid/off-grid times, fixed-section preservation, body limits, duplicate JSON and RNG/session/file preservation.

D4/D1/D2/D3/GA browser scenarios run actual React rendering against **synthetic HTTP responses**, not the live D4 API. Browser receipt/projection fixtures are explicitly fictional and do not test HMAC or real authorization. Those behaviors are independently tested by the ASGI suite. The legacy real HTTP auth browser wrapper covers authentication/preferences, not D4 reconciliation. No real-browser-to-FastAPI D4 acceptance is claimed. Parent wrappers are not extra independent functional/security cases.

The evidence runner strips database URLs, approval flags and credentials from child environments and does not read .env files. **PostgreSQL operations and live migrations: NOT RUN.** Existing legacy regressions include temporary SQLite schema tests and offline SQL rendering only. No GA evolution, re-scoring or fitness mathematics change occurred; original lower-penalty-is-better semantics remain intact.

Existing warnings remain: Starlette/httpx and AnyIO deprecations in focused backend tests; two Alembic path_separator deprecations additionally in legacy regressions. The production JS chunk remains above the 500 kB warning threshold: **867.58 kB**, gzip **243.97 kB**. Full-project lint, the entire backend GA suite, performance profiling and deployment qualification were not performed.

## Browser acceptance, screenshots and earlier attempts

The final [browser record](screenshots/dashboard-d4/20261021T193418759578+0800-browser/browser-results.json) contains exact scenario/capture timestamps. URL: **http://localhost:59212/admin/external-schedules**, owned temporary Vite/HTTP fixture. Desktop viewport **1600×1200**, mobile **390×844**.

| Scenario | Final original screenshot | Capture time, 2026-10-21 +08:00 |
|---|---|---|
| D4-B02 | [Weekly overlap calendar](screenshots/dashboard-d4/20261021T193418759578+0800-browser/D4-B02-weekly-overlap-calendar.png) | 19:34:23.211 |
| D4-B05 | [Explicit reconciliation](screenshots/dashboard-d4/20261021T193418759578+0800-browser/D4-B05-explicit-resource-reconciliation.png) | 19:34:24.070 |
| D4-B08 | [Invalid-time source details](screenshots/dashboard-d4/20261021T193418759578+0800-browser/D4-B08-invalid-source-details.png) | 19:34:24.582 |
| D4-B12 | [Mobile filters/calendar](screenshots/dashboard-d4/20261021T193418759578+0800-browser/D4-B12-mobile-review.png) | 19:34:25.674 |

All **eleven** PNGs from the initial, intermediate and final runs were visually/privacy reviewed. They show only fictional records and the application, with no credentials, receipts, real faculty data or unrelated chrome. Images are actual unedited browser captures. The three initial failed-run images have no persisted individual capture timestamps; their containing command interval is recorded, and no missing timestamp is reconstructed.

Failed/superseded attempts are retained:

1. Initial contracts: **109 passed, one failed** because the fictional unsupported-room fixture still supplied a recognized room. The fixture was corrected to provide an empty room inventory; no production resolution rule was weakened. [Record](testing/dashboard-d4/20261021T192416412281+0800-contracts/command.json).
2. Initial browser: **14 scenarios passed, one failed**, plus a failed parent audit. A generated test string contained ? instead of the UI's middle dot; the request audit also compared the full upload URL against a pathname allowlist, rejecting its legitimate filename query. Both harness checks were corrected. [Record](testing/dashboard-d4/20261021T192854352300+0800-browser/command.json). Three original captures remain; the failed final audit prevented a browser-results.json for that run.
3. The next browser run passed all fifteen cases. Visual review then found clipped overlap text on narrow cards and indistinguishable mapping labels for duplicate names. Compact event content and alias/ID selection labels improved readability; final build/lint/browser reruns pass. [Intermediate command](testing/dashboard-d4/20261021T193051605221+0800-browser/command.json). Earlier captures are preserved, not replaced.

These are scoped D4 findings; the historical [system bug report](system-bug-report.md) and its earlier totals are unchanged.

## Preservation

The [pre-D4 baseline](testing/dashboard-d4/preservation-baseline.json) includes **544** files, ignored local datasets/schedules/checkpoints and Git index. **538 are byte-identical**, with exactly six intended existing-file edits: the D3 router/schema/service, frontend API/page, and package scripts. There are no missing or unexpected baseline changes. New D4 source/evidence paths and hashes are in the [manifest](testing/dashboard-d4/manifest.json).

Protected faculty_preferences.json retains SHA-256 **72a5f4f239b5cf99cfb6d7159d443375f8496b69c6b3d1d67ad42e449fd2d8a9** and its pre-existing dirty state. Faculty UUID/code mappings, account/authentication source, GA operators/fitness/RNG/checkpoints, all existing scheduling inputs, saved schedules/history, fixed-section/preassignment source, Phase 4C foundation/tests, Phase 4B evidence, D1–D3 reports/manifests/screenshots and Git index remain unchanged. D3 source hashes are superseded only for the approved extension files; historical evidence is not rewritten.

No database contents were queried for preservation verification. No staging, commit, push, PostgreSQL provisioning, live migration or retained database operation occurred.

## Reproduction, limitations and next milestone

Run the evidence selections above to reproduce with synthetic fixtures. Edge renderer permission is needed for the browser harnesses; the existing GA harness requires its designated frontend port available. Tests stop only owned fixture servers/processes and remove owned browser profiles. Disposable SQLite regression roots may remain for review. Do not stop another service or use institutional credentials merely to reproduce evidence.

In an already authorized application deployment: preview a temporary batch; select a source row; inspect resource states; choose only existing IDs; revalidate the complete batch; inspect conflicts and filters; clear a mapping to restore source interpretation. Editing the source or re-previewing creates a new workspace. Refresh/restart intentionally loses temporary work or invalidates receipts.

Remaining limitations: metadata covers recognized prototype resources, not an authoritative directory for every college; room identities are current natural keys; external instructors may have declared resource IDs without login accounts. No new identity is allocated. Unverified terms/dates/exceptions prevent full cross-term conflict claims. Receipt continuity is process-local, requires current references, and provides no durable audit/revision/approval record. Small calendar cards truncate text; exact times, original labels/status and full validation remain available in details/tooltips and source navigation. No persistence, confirmation, locked constraints, GA input adapter or Chair approval exists.

Recommended next milestone: **D5 — validated review handoff and printable preview report**, subject to a new task. Reuse the current verified projection to print/export the weekly pattern, selected resource mappings, source hash/row references and unresolved/conflict warnings, with prominent preview-only status and safe export handling. Acceptance should preserve provenance, authorization and the full unresolved/invalid set without saving/activating schedules. Institutional term/shared-resource policies and separately approved persistence/PostgreSQL acceptance remain prerequisites for later durable confirmation and GA integration. D5 has not started.

This evidence supports prototype calendar review, explicit reconciliation, source continuity and negative access handling. It is not a usability study, GA-quality evaluation, institutional confirmation or production-readiness certification.
