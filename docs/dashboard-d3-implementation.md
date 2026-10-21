# Dashboard-first D3: External/GEC Schedule Intake and Review Preview

Implemented **2026-10-21, Asia/Manila**, against HEAD **f3a07e5461430caab7a3998a2fd9d16b0aa1287d** on main. **D3 IMPLEMENTED; FINAL FOCUSED API, PARSER, UI, BUILD, LINT AND REGRESSIONS PASS.** The existing dirty faculty preference file is preserved. PostgreSQL operations remain paused; D4 has not started.

## Objectives and inspected boundaries

D3 implements the intake/review portion of the professor-confirmed external/GEC workflow. Administrators can record incoming meetings, preview bounded imports and review discrepancies. Nothing is durably stored, confirmed, locked, published or activated as a scheduling constraint.

Read before implementation: [D1](dashboard-d1-implementation.md), [D2](dashboard-d2-implementation.md), [confirmed scheduling workflows](phase-4c-confirmed-scheduling-workflows.md), [academic contract](phase-4c1-academic-data-contract.md), [relational architecture](architecture/phase-4c1-relational-schema.md), [documentation standard](DEVELOPMENT_DOCUMENTATION_STANDARD.md), README, roadmap and bug report; routing/layout, authentication, metadata services, schedule viewers, fixed-section and preassignment sources.

Existing subject offerings supply stable section UUIDs; existing faculty metadata and declared external preassignments supply instructor references; loaded rooms supply their current natural keys. No verified term/date registry is active. The previously empty sections router is not an existing section-list API, so the new protected metadata projection reuses the subject offerings instead of inventing a general academic section registry.

Existing fixed-section schedules reserve section blocks. Existing instructor/room preassignments do not fix meeting times. These mechanisms remain distinct and unchanged. D3 reads fixed-section intervals through the existing extractor for provisional comparisons. It never calls the fixed-block loader, preassignment writer, GA generation, fitness evaluation or checkpoint services. A review table meets D3's requested display; no second calendar renderer is introduced.

## Exact files created or modified

| File | Change |
|---|---|
| backend/main.py | Modified: registers the protected preview router. |
| backend/routers/external_schedules.py | New: administrator metadata and bounded manual/file preview routes; raw request streaming avoids multipart disk spooling. |
| backend/schemas/external_schedule.py | New: input, reference-match, discrepancy and preview-only DTOs. |
| backend/services/external_schedule_service.py | New: existing-reference projection, transient CSV/XLSX parsing, validation, conflict review and source hashing. |
| backend/tests/dashboard/test_external_preview.py | New: 61 focused validation, authorization, archive-safety and preservation cases; reuses D2's synthetic session fixture. |
| frontend/src/api/externalSchedules.ts | New: typed DTOs, strict Zod response validation and existing cookie/CSRF transport. |
| frontend/src/pages/admin/ExternalSchedules.tsx | New: manual queue/edit/remove, import preview, provenance, review table and state handling. |
| frontend/src/layouts/AdminLayout.tsx | Modified: administrator navigation item and page title. |
| frontend/src/routes/AppRoutes.tsx | Modified: guarded administrator route. |
| frontend/public/templates/external-gec-fictional.csv | New: downloadable canonical CSV template containing fictional values only. |
| frontend/package.json | Modified: adds test:external and test:external:browser; dependencies/lockfile unchanged. |
| frontend/tests/externalSchedules.fixtures.mjs | New: explicitly fictional API/UI fixtures. |
| frontend/tests/externalSchedules.test.mjs | New: eight frontend contract/transport cases. |
| frontend/tests/externalSchedules.browser.test.mjs | New: fifteen actual rendered Edge scenarios with a synthetic HTTP server. |
| docs/testing/dashboard-d3/run_checks.py | New: isolated evidence runner derived from D2, with whitelisted environment and owned temporary regression roots. |

Documentation/evidence created: this report; [preservation baseline](testing/dashboard-d3/preservation-baseline.json); [manifest](testing/dashboard-d3/manifest.json); timestamped command JSON records; and two run directories under docs/screenshots/dashboard-d3 containing original PNGs and browser-results.json. The manifest lists every new artifact and SHA-256, including failed attempts. Earlier D1/D2/Phase 4B/Phase 4C sources and evidence are not rewritten.

## UI functionality

Open **/admin/external-schedules**, also available as **External/GEC Schedules** in the teal/gold administrator sidebar.

Manual fields cover supplying college/department, subject code/title, one or more affected sections, unverified academic-term text, distinct weekdays, start/end, optional room/instructor, source reference, notes and Draft/Tentative intent. Current resource labels are suggested through datalists; unknown values remain unresolved. Multiple sections use | separators. Rows can be added, edited and removed from a temporary queue, then submitted together for review.

The review table displays every source row and submitted field, intake intent, derived review status, discrepancy codes/messages, affected fields and related source rows. Import previews are read-only; correct the source file and re-preview it. Adding/editing a manual row invalidates the previous review. A file preview replaces the displayed preview, while queued manual drafts remain temporary and can be reviewed separately. The interface distinguishes Draft/Tentative intent from Needs review/Invalid findings.

Loading, empty queue, metadata failure/retry, preview progress, permission denial, validation discrepancies, import rejection and retry are implemented. Old successful previews clear before a failed retry. Abort handling prevents delayed responses reappearing after clear/navigation. Refresh or leaving the route discards temporary work; no browser storage is used for intake data. The wide table scrolls inside its container on mobile. There is no Confirm, Lock, Activate or Save commitment action.

## API, authorization and data contract

| Endpoint | Input and result |
|---|---|
| GET /api/external-schedules/metadata | Current subject/section/room/instructor references, empty verified-term list, fixed-section entry count and parser limits. |
| POST /api/external-schedules/preview | application/json with rows: 1–200 manual row objects. Structural errors reject the entire request. |
| POST /api/external-schedules/preview-file?filename=… | Raw CSV/XLSX bytes, not multipart. Plain filename only; no directory/path is used. |

All three endpoints require the existing authenticated administrator role. POST uses the existing session dependency's exact Origin and valid CSRF enforcement even though preview is non-persisted. Faculty requests with valid session/CSRF are still denied. Unauthorized requests are rejected before body reading or metadata projection. Missing/invalid sessions yield 401; wrong role/Origin/CSRF yield 403. No client-selected actor, faculty owner or role is trusted.

Success responses explicitly contain schema_version 1, preview_only true, persisted false and activated false. They include parser_version d3.1; source kind/name; SHA-256 of exact uploaded bytes (null for manual input); term_verification not_configured; and all reviewed rows. Source-row numbers are one-based manual rows or physical CSV/XLSX row references. Multiline CSV fields retain the starting physical source line. Reference matches contain an existing ID only when uniquely resolved; unknown, missing and ambiguous resources receive no invented ID.

Malformed/unsafe/unsupported requests return structured code/message errors without rows or an accepted subset. Payload/format errors use 422, size rejection 413, incorrect manual media type 415 and reference metadata unavailability 503. Domain-invalid meetings instead return a complete preview with explicit Invalid rows; this is review output, never acceptance. Response middleware supplies no-store and nosniff. Raw files, batches and review responses are not written to files, databases or global caches.

## Parsing and validation policy

Limits: **1 MiB request/upload**, **200 rows**, **13 canonical columns**, **one XLSX worksheet**, **32 archive members**, **8 MiB aggregate decompressed XML**, **4 MiB per archive member**, compression ratio at most 1000:1, **30,000 XML nodes**, maximum XML depth **64**, and **5,000 discrepancy records** per preview. Exceeding conflict volume rejects the batch rather than truncating its findings.

Canonical columns, in template order: supplier, subject_code, title, sections, academic_term, days, start, end, room, instructor, source_reference, notes, status. Required columns: supplier, subject_code, title, sections, days, start, end, source_reference. Optional omitted columns use empty defaults or Draft. Unknown/duplicate headers, malformed row widths, unsupported cell types/statuses, overlong fields and over-limit row counts reject the whole file. Empty imports are rejected. Draft and Tentative are the only accepted input statuses.

CSV accepts UTF-8 with optional BOM, comma separators, proper quoting and | within day/section fields. Invalid UTF-8, binary/ZIP/OLE signatures and malformed quoting are rejected. Formula-like leading =, +, -, @ and unsafe control characters are conservatively rejected in text fields; this is an explicit prototype restriction, including notes.

XLSX uses installed openpyxl **3.1.5** in read-only, data_only false, keep_links false mode, following ZIP/XML inspection. No archive extraction or spreadsheet evaluation occurs. The strict OOXML member allowlist rejects macros, embedded objects, additional sheets and unsupported package parts. Duplicate members, encrypted/unsupported-compression entries, external/unsafe relationship targets, hyperlinks, defined names, formulas, XML entities/DOCTYPEs and UTF-16/NUL-bearing XML are rejected. Streaming XML inspection applies depth/node budgets before workbook loading. Worksheet coordinates/dimensions are bounded. Cells must be text, except time-only values for start/end; numeric identities and inferred academic dates are not converted.

These are bounded UTF-8 OOXML previews, not general Excel compatibility. Legacy XLS, XLSM, multisheet workbooks, arbitrary header mapping, hidden extra sheets, formulas, rich linked workbooks, numeric/date inference and unusual package structures remain unsupported. Upload MIME labels do not override actual-format validation.

Review checks:

- Required fields; empty or repeated section references; distinct M/T/W/TH/F/S or full weekday names; Sunday and overnight meetings unsupported.
- Exact HH:MM 24-hour time with start before end. Off-grid/out-of-window intervals receive UNSUPPORTED_TIME_GRID; times are never rounded to fit the existing 07:30–22:00 half-hour engine.
- Unknown catalog subjects, section/room/instructor references and ambiguous instructor names are flagged. An external subject outside the prototype catalog is a review issue, not silently fabricated or removed.
- Missing academic term gets TERM_UNKNOWN; supplied term text gets TERM_UNVERIFIED. Every row therefore remains at least Needs review in this deployment.
- Duplicate meetings are symmetric discrepancies. Half-open intervals allow adjacent meetings; shared sections or uniquely resolved room/instructor identities produce symmetric potential overlap findings with related source rows.
- Different unverified term labels cannot suppress a possible same-week clash. Comparisons with loaded legacy fixed-section intervals are marked provisional review findings. Missing date windows and unknown resources explicitly prevent claims of complete institutional conflict coverage.

This preview does not validate or modify an existing GA candidate, apply reservations, authorize confirmation or represent hard-constraint acceptance.

## Backend test results and database scope

Runtime: Windows; Python **3.14.2**, SQLite **3.50.4**, openpyxl **3.1.5**. Exact commands, cwd, ISO start/end timestamps, exit codes and elapsed times are in the artifacts. All runner children use a whitelisted OS environment with no database URLs, credential variables or approval flags; no .env credentials are loaded.

| Selection | Final result | Evidence |
|---|---|---|
| New D3 + D2 API suite | **90 passed**, 61 D3 + 29 D2; 0 failed/skipped; 18.73 s pytest; 18:15:48–18:16:09 +08:00 | [Final command](testing/dashboard-d3/20261021T181548123118+0800-backend/command.json) |
| Existing authentication + GA control regressions | **46 passed**, 0 failed/skipped; 54.37 s pytest; includes existing real HTTP auth browser wrapper and seven GA control cases | [Command](testing/dashboard-d3/20261021T180930036624+0800-backend-regressions/command.json) |

D3 tests use the actual FastAPI app, real password verification, cookies/session lookups, administrator/faculty roles, Origin and valid-CSRF negative authorization. Only storage is redirected to temporary SQLite, with synthetic registry/templates and explicit PostgreSQL/default-engine denial. Principals are not bypassed in D3 authorization cases. Parsing tests build real CSV/XLSX bytes in memory. They cover valid hashes/row references, formula/link/macro-package rejection, extra sheets, XML declarations/depth/nodes, compressed bombs, types, dimensions, streaming size limits, malformed input, missing/ambiguous identities, duplicates, adjacent/nonadjacent clashes, unknown terms, fixed-source comparisons and deterministic no-write behavior.

The existing regression suite retains its separate boundaries: SQLite authentication plus a real HTTP browser wrapper, and explicit test-administrator principals/private temporary markers for GA control cases. No GA evolution is run. No fitness, RNG or hard-constraint mathematics are changed. This selection is not a full backend GA-suite run or GA-quality evaluation.

**PostgreSQL: NOT RUN.** No PostgreSQL connection, provisioning or live migration occurred, including either Phase 4B target. The legacy auth regression includes temporary SQLite schema tests and offline Alembic SQL rendering; neither establishes PostgreSQL acceptance. Existing Phase 4C tests were preserved, not reclassified as online passes.

## Frontend, browser and build results

Run from repository root via .venv/Scripts/python.exe -B docs/testing/dashboard-d3/run_checks.py followed by the selection below. Child commands/cwd and timestamps are recorded exactly.

| Selection | Result | Evidence |
|---|---|---|
| contracts | **99 passed**, 8 D3 + 91 existing, 0 failed/skipped | [Command](testing/dashboard-d3/20261021T180649240181+0800-contracts/command.json) |
| build | **PASS**, TypeScript and Vite 8.2.2 production build, 217 modules | [Command](testing/dashboard-d3/20261021T180444482420+0800-build/command.json) |
| lint | **PASS**, no findings in four changed/new TS/TSX files | [Command](testing/dashboard-d3/20261021T180651152173+0800-lint/command.json) |
| browser | **15 D3 scenarios passed**, plus one parent wrapper | [Final command](testing/dashboard-d3/20261021T181109118902+0800-browser/command.json) |
| d1-browser | **16 scenarios passed**, plus one parent wrapper | [Command](testing/dashboard-d3/20261021T180942367522+0800-d1-browser/command.json) |
| d2-browser | **13 scenarios passed**, plus one parent wrapper | [Command](testing/dashboard-d3/20261021T180954769004+0800-d2-browser/command.json) |
| ga-browser | **51 scenarios passed**, plus one parent wrapper | [Command](testing/dashboard-d3/20261021T181006615455+0800-ga-browser/command.json) |

Node **v24.11.1**; actual headless Edge **155.0.4283.62**, driven through Node/CDP with owned temporary profiles and loopback ports. D3 scenarios verify loading/empty, manual entry/edit, discrepancy/provenance display, invalid-row correction, duplicates/conflicts, actual CSV file selection/raw-byte transfer, rejection/retry, unsupported extensions, metadata retry, denied preview, unauthorized route isolation, mobile containment, refresh data loss, delayed-response cancellation and unresolved references.

The D3/D1/D2/GA rendered scenarios use **synthetic HTTP responses**. They prove actual frontend behavior under those fixtures, not FastAPI authorization or a browser-to-real-parser round trip. Real FastAPI authorization and actual CSV/XLSX parsing are separately verified by the ASGI suite. The existing real HTTP auth browser wrapper covers legacy auth/preferences, not D3 file import. XLSX selection was not separately exercised in the D3 browser; real XLSX byte parsing/safety was tested in the backend. Parent wrappers are not extra functional/security cases.

No D3 activation/GA mutation requests or browser runtime exceptions occurred. Existing deprecation warnings remain: Starlette/httpx and AnyIO in the focused backend suite; additionally two Alembic path_separator warnings in legacy regressions. Build retains its existing >500 kB chunk warning: JS **852.81 kB**, gzip **240.42 kB**. Full-project lint and performance benchmarking were not performed.

## Actual screenshots and failed-attempt history

The [final browser record](screenshots/dashboard-d3/20261021T181109118902+0800-browser/browser-results.json) contains every scenario's start/end timestamp and capture metadata. Actual URL: **http://localhost:59273/admin/external-schedules**, owned Vite development fixture, 2026-10-21. All four final PNGs and the four earlier-run PNGs were visually/privacy reviewed. Only fictional/synthetic records and the target application appear; no credentials, real faculty profiles, developer tools or raw authenticated headers. Originals were not edited/generated/redacted.

| Scenario | Final original image | Capture (+08:00), viewport |
|---|---|---|
| D3-B02 | [Manual intake](screenshots/dashboard-d3/20261021T181109118902+0800-browser/D3-B02-manual-intake.png) | 18:11:12.427, 1600×1200 |
| D3-B03 | [Review findings](screenshots/dashboard-d3/20261021T181109118902+0800-browser/D3-B03-review-findings.png) | 18:11:12.616, 1600×1200 |
| D3-B06 | [CSV preview/provenance](screenshots/dashboard-d3/20261021T181109118902+0800-browser/D3-B06-csv-preview.png) | 18:11:13.685, 1600×1200 |
| D3-B12 | [Mobile intake](screenshots/dashboard-d3/20261021T181109118902+0800-browser/D3-B12-mobile-intake.png) | 18:11:15.306, 390×844 |

The first browser attempt had **14 passed scenarios, one failed scenario** (plus failed parent wrapper): the test searched for role denial inside main, while the shared route guard correctly renders denial outside the dashboard layout. The selector was corrected; no application permission behavior was weakened. The complete [failed command](testing/dashboard-d3/20261021T180849851957+0800-browser/command.json), [scenario record](screenshots/dashboard-d3/20261021T180849851957+0800-browser/browser-results.json) and four original images remain.

Backend passes progressed from 84 to 88 as additional archive/streaming cases were added. A subsequent XML stress test produced **89 passed and two setup/teardown errors** because pytest used the enormous synthetic payload as PYTEST_CURRENT_TEST, exceeding Windows' 32,767-character environment-variable limit. [Failed command](testing/dashboard-d3/20261021T181359114595+0800-backend/command.json). Explicit short test IDs fixed the harness issue; the final 90 cases pass. The intentionally large failed log is retained and contains only synthetic XML. No application/parser failure is claimed from that setup error. See the historical [bug report](system-bug-report.md) for earlier unrelated defects; its counts are unchanged.

## Preservation verification

Of **507** pre-D3 baselined files, **503 are byte-identical**, with exactly four intended existing-file edits: backend/main.py, frontend/package.json, frontend/src/layouts/AdminLayout.tsx and frontend/src/routes/AppRoutes.tsx. There are no missing/unexpected baseline changes. The [manifest](testing/dashboard-d3/manifest.json) records new files and raw SHA-256 hashes, commands, failed attempts, fixtures, images and preservation results.

Protected faculty_preferences.json retains SHA-256 **72a5f4f239b5cf99cfb6d7159d443375f8496b69c6b3d1d67ad42e449fd2d8a9** and its pre-existing dirty status. Faculty UUID/code registry and formulas, account bindings/authentication source, GA operators/fitness/RNG/checkpoints, scheduling inputs, all stored schedules/history, Phase 4C foundation and tests, Phase 4B evidence, D1/D2 reports and Git index are byte-identical. No database contents were queried for this preservation check. No staging, commit or push occurred.

## Safe reproduction and remaining functionality

Use the evidence runner selections listed above. Tests use synthetic resources and temporary storage; browsers require the installed Edge executable and renderer permissions. The existing GA browser harness needs its designated frontend port available; never stop an unrelated service to obtain it. Owned fixture servers/browser profiles are cleaned by their tests, and temporary SQLite regression roots may remain for review. No database or institutional artifact disposal is authorized.

In an already authorized application deployment, an administrator can open the new route, add a temporary row, review findings, download the fictional template, replace its example values with verified references, and preview a CSV/XLSX. This milestone itself does not authorize importing real institutional files or configuring credentials. Refresh should intentionally discard the workspace.

Still absent: durable draft/batch/provenance storage; verified term/effective dates and exceptions; authoritative cross-college resource mapping; selected constraint-set revisions; approval/confirmation authority; source retention policies; stale-source publication protection; locked GA overlays/inputs; schedule revision history; faculty change requests and Chair decisions. Unknown dates/resources prevent an assertion of complete hard-constraint correctness. This prototype has not been load-tested or certified for arbitrary Excel files.

## Thesis relevance and recommended D4

D3 supports evidence for administrator intake, safe parser rejection, reviewable discrepancies, negative access control, explicit uncertainty and preservation. It does not support a claim of confirmed commitments constraining GA output, production acceptance, a usability study or scheduling-quality improvement.

Recommended D4 is a bounded **external review calendar and reference reconciliation** milestone:

1. Add a read-only meeting/calendar review and discrepancy navigation beside the existing table, reusing the shared schedule/calendar rendering where its supported day/time semantics apply; keep unsupported intervals explicit.
2. Allow explicit mapping of unresolved labels to existing canonical resources, with a new server revalidation of the full batch and stale-response protection. Suggested files: a dedicated frontend review-calendar component, the existing ExternalSchedules page/API DTOs, and the external preview validation service/tests.
3. Acceptance: mappings resolve only to existing IDs; conflicts remain visible; tentative/unverified rows stay distinct; remapping cannot hide overlaps; no activation, persistence or GA/RNG/checkpoint mutation occurs.

Durable confirmation/constraint activation needs a separately reviewed persistence/schema scope, verified terms/resource policies and explicitly approved isolated PostgreSQL acceptance first. D4 is a recommendation only and has not been implemented.
