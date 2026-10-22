# Dashboard-first D6: legacy GEC intake and reconciliation

Implemented and verified **2026-10-22, Asia/Manila**, against `0850362bb56025c4aa0eb8489a688893649a6e7c` on main. **IMPLEMENTED / SCOPED AUTOMATED CHECKS PASS.** Temporary preview only. No persistence, confirmation, publication, PostgreSQL operation or external GA constraint activation.

Read with [D3](dashboard-d3-implementation.md), [D4](dashboard-d4-implementation.md), [D5](dashboard-d5-implementation.md), [confirmed workflows](phase-4c-confirmed-scheduling-workflows.md), README, roadmap, bug report and [documentation standard](DEVELOPMENT_DOCUMENTATION_STANDARD.md). Historical evidence is retained unchanged. The [manifest](testing/dashboard-d6/manifest.json) enumerates exact files, hashes, commands, timing, screenshots, preservation and limitations.

## Requirements and implemented flow

| Requirement | Behavior / verification |
|---|---|
| D6-IMPORT | Explicit Legacy GEC CSV option; canonical CSV/XLSX remains the default. Four exact unique headers; bounded whole-file rejection for structural/unsafe inputs. Backend and transport contracts; D6-B01–B03/B10. |
| D6-PARSE | Explicit 12-hour AM/PM endpoints, compact days, half-hour grid and 07:30–22:00 boundaries; parsed/invalid/unsupported/ambiguous states. No rounding, missing-meridiem inference or repeated-day deduplication. Parameterized backend cases; D6-B04. |
| D6-MAP | Administrator-supplied supplier/source reference/term/status are separately labeled unverified preview metadata. Existing D4 explicit IDs resolve sections/resources. Year Level does not manufacture identities. Backend tests; D6-B05/B06. |
| D6-PROV | Exact raw file SHA-256, physical row starts and all four original field strings survive signed receipt, fresh review and handoff. Tampered/stale references fail closed. Backend/contract tests; D6-B07–B09. |
| D6-SAFE | Real administrator/session/Origin/CSRF enforcement, no disk spooling or writes, no confirmation authority, safe React text rendering and no GA changes. Backend preservation tests; D6-B11–B15 and baseline audit. |
| D6-COMPARE | Read-only comparison of the three named local CSVs; only counts, hashes and discrepancy row references exported. No merge, source correction or approval inference. |

The existing `/admin/external-schedules` page now offers **Import format → Legacy GEC CSV (four columns)**. Administrators enter missing preview context before previewing the selected file. Blank metadata is permitted for diagnosis and remains visibly incomplete. Editing metadata or format invalidates prior results and handoff, cancels pending requests, and requires another preview. Clear resets the metadata and source; refresh discards all temporary work.

The adapter maps Section to the existing section-reference workflow, Course Number to subject code and Schedule to canonical days/start/end. Year Level remains original context only. Original strings, including surrounding whitespace and embedded newlines, are preserved separately from normalized canonical fields. No titles, faculty, rooms, semester or stable identifiers are invented. The adapter does not auto-read a repository CSV: selecting and submitting a file is an explicit administrator action. Only the separate read-only comparison utility reads the three bundled datasets.

Existing D4 calendar/filter/reconciliation and D5 complete handoff are reused. Nonparsed legacy rows remain available as original details and discrepancies but are not plotted. Syntactically supported meetings can be plotted even when metadata is invalid; plotting is not readiness or acceptance. Section IDs are selected only from recognized resources; ambiguous or unknown references remain unresolved until explicit reconciliation. Optional room/instructor resources remain missing unless an administrator selects an existing record. Duplicate and overlap checks use the existing full-batch validation and half-open intervals, permitting adjacent meetings.

All legacy rows carry `LEGACY_INCOMPLETE_METADATA`. Missing titles and required supplier/source reference produce existing `REQUIRED_FIELD` errors. Terms are `TERM_UNKNOWN` or `TERM_UNVERIFIED`; there is still no authoritative term/date registry. Consequently these source files cannot be described as ready for confirmation. D5 keeps the mandatory **REVIEW PREVIEW — NOT CONFIRMED OR ACTIVE IN GA** warning and retains invalid rows in output.

## Exact implementation files

| Path | Change |
|---|---|
| backend/routers/external_schedules.py | Modified: explicit import-format selection and bounded legacy JSON envelope on the existing protected file-preview route. |
| backend/schemas/external_schedule.py | Modified: bounded legacy metadata/upload DTOs; original-row/parser provenance; optional provenance on intake/review responses. |
| backend/services/external_schedule_service.py | Modified: reuse bounded CSV reader with adapter callback; explicit legacy dispatch; attach legacy findings/provenance before signing. Canonical 13-column contract retained. |
| backend/services/external_schedule_review_service.py | Modified: sign and preserve legacy provenance; replay findings on fresh validation; prevent nonparsed legacy rows from being plotted. |
| backend/services/external_schedule_legacy_service.py | New: pure bounded four-column adapter and explicit day/time parsing. No filesystem path, identity allocator, persistence or GA invocation. |
| backend/tests/dashboard/test_external_legacy.py | New: 39 cases including actual FastAPI session/authorization and complete D3–D5 provenance flow. |
| frontend/src/api/externalSchedules.ts | Modified: typed legacy DTOs/transport and original-provenance verification on review/handoff. |
| frontend/src/pages/admin/ExternalSchedules.tsx | Modified: explicit format choice, missing-metadata mapping fields, legacy template and original-source display. |
| frontend/src/components/schedule/LegacyScheduleProvenance.tsx | New: shared original values, parse states, missing metadata and origin labels for intake and handoff. |
| frontend/src/components/schedule/ExternalScheduleHandoff.tsx | Modified: includes original legacy row and metadata origin in each printable row. Existing print gating retained. |
| frontend/public/templates/external-gec-legacy-fictional.csv | New: two fictional example rows; no copied institutional records. |
| frontend/tests/externalLegacy.test.mjs | New: six transport, compatibility, DTO and integrity contracts. |
| frontend/tests/externalLegacy.browser.test.mjs | New: fifteen real rendered Edge scenarios with explicitly synthetic HTTP API. |

Supporting files: this report; `docs/testing/dashboard-d6/run_checks.py`, `compare_legacy_datasets.py`, `preservation-baseline.json`, `manifest.json`; sixteen timestamped command records; three original screenshots and one browser scenario record. The manifest provides the complete artifact inventory. No dependency, package script, migration or previous evidence file was changed.

## API and integrity contract

`POST /api/external-schedules/preview-file?filename=<plain.csv>&import_format=legacy_gec` uses the existing administrator router and real session/Origin/CSRF enforcement. It accepts `application/json` containing `content_base64` and `metadata` (supplier, source_reference, academic_term, Draft/Tentative status). Metadata and file contents are in the bounded body, not URL parameters or request logs. Filenames cannot contain directory paths; the server never opens a client-selected path.

Limits: 2 MiB envelope, 1 MiB decoded CSV, 200 data rows, exactly four unique case-sensitive headers (order can vary), UTF-8 with optional BOM, maximum 1000 characters per raw cell, existing canonical field limits and 5000 total findings. Unsafe control/formula-like fields, malformed CSV, mismatched row widths, extra/missing/duplicate headers, invalid types or excessive rows reject the complete upload. Actual-format checks reject ZIP/OLE/binary data disguised as CSV. Legacy XLSX is deliberately unsupported; existing bounded canonical XLSX remains unchanged.

The canonical route still accepts raw CSV/XLSX bytes with `import_format` omitted or canonical. No automatic legacy detection occurs. Structural errors reject the whole operation; domain-invalid expressions instead return the full preview with explicit discrepancies. No invalid row is silently discarded or repaired.

Supported Schedule syntax: `7:30AM - 9:00AM MTH`, with explicit AM/PM on both endpoints and compact M, T, W, TH, F, S or SAT. Noon/midnight use normal 12-hour conversion, then grid/window checks. Sunday, arbitrary aliases, overnight intervals, multiple meetings per cell and inferred meridiems are unsupported or invalid. Repeated day tokens, including TTF, are ambiguous; the adapter preserves them instead of silently deduplicating. Error codes distinguish `LEGACY_INVALID_SCHEDULE`, `LEGACY_AMBIGUOUS_SCHEDULE`, `LEGACY_INVALID_TIME`, `LEGACY_INVALID_INTERVAL`, `LEGACY_UNSUPPORTED_DAY`, `LEGACY_AMBIGUOUS_DAYS`, `LEGACY_UNSUPPORTED_GRID` and incomplete metadata.

Intake retains schema 1/base parser d3.1; D4 retains schema 2/projection d4.1; D5 retains schema 3/handoff d5.1. Optional `legacy` provenance identifies adapter d6.1 and `administrator_supplied_unverified` metadata. Canonical responses have null legacy provenance. The process HMAC receipt now binds legacy originals, findings and metadata together with canonical rows and reference inventory. D4 revalidates all rows/resources; D5 calls that projector afresh. The D5 content fingerprint includes the entire legacy provenance. Client verification rejects changed or omitted provenance even if a response has a newly computed content hash. Hashing alone is not institutional attestation or authorization.

Authentication failure remains 401, wrong role/Origin/CSRF 403, malformed/unsafe/invalid format 422, oversized request/decoded file 413, incorrect legacy media type 415, stale/forged receipt 409 and unavailable metadata 503. Success remains no-store/nosniff and preview-only. Ownership means authorized access to a caller-submitted transient batch, not durable ownership of institutional schedule records. No new per-department authority or Chair workflow is claimed.

## Sanitized dataset comparison

Evidence: [read-only comparison command](testing/dashboard-d6/20261022T065705020693+0800-dataset-comparison/command.json). Values below were rechecked against current bytes; no raw academic records were exported into testing evidence. Source matching does not establish institutional approval, term or correctness.

All three files have exactly `Year Level, Section, Course Number, Schedule`, no exact duplicate rows, and no supplying college, descriptive title, faculty, room, term/date window or confirmation history.

| File | Rows | Parsed / ambiguous / invalid | Coverage |
|---|---:|---|---|
| BSIT_GEC.csv | 34 | 32 / 1 / 1 | Source row 22 repeats a day token; source row 32 has nonpositive ordering. 49 parsed day-meeting occurrences. Not loaded directly by the GA. |
| BSIT_Consolidated_Subject_Schedules.csv | 32 | 32 / 0 / 0 | 48 parsed day-meeting occurrences. Current fixed-section loader input. |
| BSIT_Consolidated_Subject_Schedules_test.csv | 34 | 33 / 1 / 0 | Source row 22 repeats a day token. 50 parsed day-meeting occurrences. Alternate input, not active. |

Source rows are one-based physical CSV lines including the header. Parsed day occurrences exclude ambiguous/invalid rows; they are not approved timetable counts.

| Comparison | Exact matching rows | Left only / right only | Shared year/section/course keys with different schedule sets |
|---|---:|---:|---:|
| GEC vs active consolidated | 31 | 3 / 1 | 3 |
| GEC vs alternate consolidated | 33 | 1 / 1 | 1 |
| Active vs alternate consolidated | 32 | 0 / 2 | 2 |

All pairs share the same 30 Year Level/Section/Course Number keys; differences include additional meetings for shared keys, rather than proving different subjects or approved replacement records. The active file is an exact-row subset of the alternate file. All academic terms remain unresolved. No dataset was merged, repaired, selected as a replacement or activated.

The existing GA still reads the active consolidated CSV through `Functions.apply_fixed_section_schedules`, reserves section TimeBlocks and validates fixed-section conflicts. Its day parser deduplicates repeated tokens; D6 intentionally flags that ambiguity for intake without changing the old loader. `PreassignedAssignment` fixes declared instructor/room, not meeting times. Faculty/room resets and fixed-section availability are unchanged. D6 never calls a reservation/reset method or changes these inputs.

## Test executions and evidence boundaries

All commands run through `.venv/Scripts/python.exe -B docs/testing/dashboard-d6/run_checks.py <selection>` from the repository root. Each JSON command record includes exact child command/cwd, +08:00 start/end times, duration, output, exit status and environment scope. Children receive a whitelisted OS environment without database URLs/credentials/approval flags. Backend pytest runs now use unique previously absent owned temporary roots.

| Selection | Final result | Evidence |
|---|---|---|
| backend | **176 passed, 0 failed/skipped; 2 warnings**. 39 D6 + 137 existing D2–D5. | [Command](testing/dashboard-d6/20261022T065514186302+0800-backend/command.json) |
| backend-regressions | **46 passed, 0 failed/skipped; 4 warnings**. Existing auth/GA control. | [Command](testing/dashboard-d6/20261022T065323266427+0800-backend-regressions/command.json) |
| ga-resource-regressions | **3 passed, 0 failed/skipped**. Existing synthetic resource overlap/reset/rollback cases, no GA generations. | [Command](testing/dashboard-d6/20261022T065708926599+0800-ga-resource-regressions/command.json) |
| contracts | **124 passed, 0 failed/skipped**. Six D6 + 118 existing. | [Command](testing/dashboard-d6/20261022T065141435567+0800-contracts/command.json) |
| browser | **15 D6 scenarios + one parent PASS**, no runtime exceptions. | [Command](testing/dashboard-d6/20261022T065343486367+0800-browser/command.json), [scenarios](screenshots/dashboard-d6/20261022T065343486367+0800-browser/browser-results.json) |
| d1/d2/d3/d4/d5-browser | **16 / 13 / 15 / 15 / 15 scenarios PASS**, five separate parent wrappers. | Timestamped command records in manifest |
| ga-browser | **51 scenarios + one parent PASS**; synthetic HTTP, no evolution. | [Command](testing/dashboard-d6/20261022T065357403854+0800-ga-browser/command.json) |
| build | **PASS**, 222 modules; JS 881.24 kB / gzip 247.30 kB; existing chunk-size warning. | [Command](testing/dashboard-d6/20261022T065145934015+0800-build/command.json) |
| lint | **PASS**, six selected TypeScript/TSX files. | [Command](testing/dashboard-d6/20261022T065147778779+0800-lint/command.json) |

Previous browser regressions total **125 distinct scenarios**, separately from the 15 new D6 scenarios. Parent wrappers are not added to scenario counts. This is a focused selection, not a full backend suite, full-project lint, production GA-quality or performance result.

Backend D6 tests exercise actual FastAPI ASGI routes, password verification, SQLite-backed synthetic sessions, role checks, exact Origin and valid-CSRF wrong-role denial. Only storage and metadata are isolated; no administrator principal bypass is used. The existing auth regression includes its own real HTTP browser wrapper with isolated SQLite; it is not D6 browser-to-FastAPI deployment acceptance. No PostgreSQL connection or live migration ran; existing Alembic checks only render offline SQL. **The 17 Phase 4C PostgreSQL cases remain paused and unverified.**

D6 browser tests run real React/Edge against synthetic HTTP responses. They prove rendering, input selection/upload encoding, route guards, stale/tampered response handling, mappings, output and temporary-state behavior under that fixture. They do not execute the real legacy parser in the browser server or independently prove real backend authorization. Synthetic discrepancy wording, validation timestamps and IDs are fixture values. Print calls are intercepted and print-media DOM/style checks are real; native dialog, physical printer, PDF pagination and large-batch print acceptance remain NOT RUN.

Warnings: existing Starlette/httpx and AnyIO BlockingPortal deprecations; the auth regression additionally reports two Alembic path_separator warnings. No application change was made to suppress them.

## Earlier failures and resolution

1. [First backend attempt](testing/dashboard-d6/20261022T065144198785+0800-backend/command.json): **175 passed, one failed**, two warnings. The new envelope-size assertion omitted application/json. The endpoint correctly returned 415 before body-size inspection; the test now supplies the required media type and verifies 413. No validation bypass was introduced.
2. [Second backend attempt](testing/dashboard-d6/20261022T065323496903+0800-backend/command.json): **123 passed, 53 setup errors**, two warnings. Windows denied access to an existing `pytest-of-User` temporary root. The D6 evidence runner now gives every backend selection a fresh owned root; no old directory, ACL or service was modified. The final 176-case run passes.

These original failed records remain intact. The historical system bug report was not rewritten. No other final checks failed.

## Actual browser scenarios and screenshots

Browser **Edge 155.0.4283.62**, Node v24.11.1; actual URL **http://localhost:51849/admin/external-schedules**, owned ephemeral Vite/synthetic API and temporary browser profile. Backend Python 3.14.2 with isolated SQLite; Vite 8.2.2. Browser results record exact steps, timestamps, expected scenario descriptions and outcomes.

D6-B01–B03: canonical default, explicit legacy selection, missing-metadata prompts/template, exact uploaded-byte decoding, complete original rows/hash. B04: ambiguous/invalid rows retained but not plotted. B05: explicit recognized section mapping and overlap visibility. B06: metadata edit invalidates output and requires re-preview. B07: complete legacy D5 handoff. B08/B09: altered provenance/stale receipt rejected. B10: whole-import failure, old results cleared, retry. B11: imported script/image-looking text stays literal. B12: revalidated intercepted print contains every original and metadata origin. B13: mobile containment. B14: clear/refresh discard state with no confirmation action. B15: anonymous/faculty route denial without intake requests.

All three originals were visually inspected for correctness and privacy, with no edits/redaction or generated screenshots:

| Capture | Actual time (+08:00) | Viewport |
|---|---|---|
| [D6-B04 originals and parsing](screenshots/dashboard-d6/20261022T065343486367+0800-browser/D6-B04-originals-and-parsing.png) | 2026-10-22 06:53:49.622 | 1600×1200 |
| [D6-B07 complete legacy handoff](screenshots/dashboard-d6/20261022T065343486367+0800-browser/D6-B07-complete-legacy-handoff.png) | 2026-10-22 06:53:50.790 | 1600×1200 |
| [D6-B13 mobile legacy provenance](screenshots/dashboard-d6/20261022T065343486367+0800-browser/D6-B13-mobile-legacy.png) | 2026-10-22 06:53:51.941 | 390×844 |

Only fictional subjects/resources/source text appear. The markup-looking Schedule value is intentionally literal test input, not an executable element. No passwords, backend receipts, cookies or real faculty records are displayed. The handoff validation timestamp is synthetic fixture content, distinct from actual capture times.

## Preservation and safe manual reproduction

Baseline: **620 files; 613 byte-identical; exactly seven intended existing application-file changes**, listed above. Protected preferences, every other backend/data file (including ignored workbooks), identity sources, account bindings, GA operators/fitness/RNG/checkpoints, scheduling inputs, saved results/history, Phase 4C foundation/tests and historical evidence remain unchanged. `.git/index` and HEAD are unchanged. No staging, commit or push occurred. The manifest records hashes and an explicit exclusion for the pre-existing protected preference modification.

To reproduce with isolated synthetic fixtures: run the D6 evidence runner's backend/contracts/build/lint/browser selections; regression selections are listed in the runner. It creates new evidence directories, strips DB configuration and stops only its owned browser/services/profile. Do not launch an unisolated institutional backend or write preferences to reproduce a screenshot.

For an authorized administrator in an independently isolated application environment: open External/GEC Schedules; choose Legacy GEC CSV; use the fictional legacy template; leave missing metadata blank once and inspect findings, then supply fictional context and preview again. Inspect original values and hash, map a section to a recognized identity, revalidate all mappings, inspect the calendar and prepare the complete handoff. Repeat with malformed headers, missing AM/PM, repeated days and reversed time. Refresh to verify temporary loss. Native printing still needs its separately identified manual check. Selecting a real file does not authorize durable storage or activation.

## Remaining institutional information and D7 boundary

Required before reliable confirmation: supplying authority and provenance/reference, verified academic term/date window, subject descriptions, authoritative section mappings, clarified ambiguous/invalid source expressions, applicable shared instructor/room identities, recurrence exceptions and confirmation/revision policy. Administrator-entered text is not independent verification of these facts. Existing prototype resource catalogs do not establish complete institutional coverage.

D6 changes neither section reservations nor faculty/room reset logic. Future GA integration must compile a separately approved immutable confirmed revision into detached calendars, preserve it through resets/reconstruction, cover faculty/room conflicts where applicable, reject stale input/publication and preserve RNG/checkpoint compatibility. Time-free preassignments cannot stand in for fixed external meetings.

Recommended **D7 boundary: authoritative metadata completion and confirmation-readiness validation**, retaining a review-only workflow until authority/calendar/resource and persistence decisions are approved. Define evidence-backed metadata enrichment and source clarification, durable provenance/revision requirements and the minimum later persistence plan. Any database migration, actual confirmation or immutable GA constraint adapter needs separate authorization and acceptance; do not activate a legacy file directly. Chair approval remains a later separate workflow. D7 was not started.

Thesis scope: this evidence supports usable temporary legacy intake, original-source provenance, explicit reconciliation, discrepancy-preserving calendar/handoff and scoped negative-access behavior. It does not establish institutional data verification, confirmation, official schedules, GA integration, usability validation or production readiness.
