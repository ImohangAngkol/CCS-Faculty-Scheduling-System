# Dashboard-first D5: validated GEC review handoff

Implemented and verified **2026-10-21, Asia/Manila**, against HEAD **3b83c8bef0a62a151a58e7a5fae770dc94977eec**, branch main. **IMPLEMENTED / SCOPED AUTOMATED CHECKS PASS. Native print-dialog, paginated PDF and physical-printer acceptance: NOT RUN.** This is a temporary administrator review feature, with no persistence, confirmation or GA activation.

## Resumed work and completion status

The user resumed D5 after a usage-limit interruption. Inspection found the implementation, tests, original screenshots and fifteen command records intact. The final browser rerun had already completed successfully at **21:00:27.395212 +08:00**: fifteen scenarios passed, with one passing parent wrapper. Final build and focused ESLint also passed. The missing deliverables were this report and the [evidence manifest](testing/dashboard-d5/manifest.json).

The resumed work inspected the retained source/results, visually reviewed screenshots, checked privacy, parsed Python/JSON, checked whitespace and preservation, and created only those two missing documents. It did not restart development, alter implementation files, overwrite evidence or repeat already-passing runtime checks. The manifest records hashes of every retained pending D5 file inspected on resume and confirms they remain unchanged. Results below are the actual retained executions, not newly invented or rerun results.

Read with [D1](dashboard-d1-implementation.md), [D2](dashboard-d2-implementation.md), [D3](dashboard-d3-implementation.md), [D4](dashboard-d4-implementation.md), the [confirmed academic workflows](phase-4c-confirmed-scheduling-workflows.md), [Phase 4C foundation](phase-4c2-academic-foundation.md), [documentation standard](DEVELOPMENT_DOCUMENTATION_STANDARD.md), README, historical roadmap and bug report. Their historical acceptance boundaries remain unchanged.

## Objectives and requirements

| Requirement | Implemented behavior and evidence |
|---|---|
| D5-AUTH | Administrator router/session/Origin/CSRF guards; real FastAPI tests with isolated SQLite identities; D5-B13 tests route denial using synthetic HTTP. |
| D5-FRESH | Preparation and printing each request fresh full-batch D4 validation; forged/process-expired/stale receipts fail closed. Backend freshness tests; D5-B01/B06–B09. |
| D5-PROVENANCE | Source file hash, physical source rows, original normalized fields, recognized IDs, resource states, full discrepancy set and deterministic preview fingerprint. Backend source tests; eight frontend contracts; D5-B02–B05. |
| D5-PRINT | Print-specific complete-row document, mandatory preview warning, browser print call after successful revalidation, blocked ordinary-print output while the handoff workspace is mounted. D5-B08–B10/B14. |
| D5-SAFE | Invalid/unresolved rows retained, imported markup rendered as text, no schedule/identity/session/storage mutation, protected files/index unchanged. No institutional data fixture. |

D5 does not grant confirmation authority. “Validated” means processed by the current prototype preview validator, including reported errors; it does not mean all rows passed, academic dates are verified, or institutional hard constraints are fully covered.

## Exact implementation files

| File | Change |
|---|---|
| backend/schemas/external_schedule.py | Modified: schema-version-3 ReviewHandoff, mandatory warning, false approval/persistence/activation flags, preview identity, validation timestamp and nested complete D4 review. |
| backend/routers/external_schedules.py | Modified: shared bounded request parser for review/handoff and administrator-only POST /handoff. Existing intake/review semantics retained. |
| backend/services/external_schedule_handoff_service.py | New: calls the existing D4 projector for every request, fingerprints the complete projection and adds actual UTC validation time; no storage/cache/export operation. |
| backend/tests/dashboard/test_external_handoff.py | New: fifteen focused cases, counting parameterized cases, covering integrity, full-row provenance, resources, freshness, authorization, payload bounds, safe JSON text and preservation. |
| frontend/src/api/externalSchedules.ts | Modified: reusable original-source verifier, strict handoff schema, cancellable authenticated handoff request and matching ASCII-JSON content fingerprint calculation. |
| frontend/src/components/schedule/ExternalScheduleReview.tsx | Modified: mounts the handoff within the current administrator review workspace; mapping changes remount/cancel it and discard old output. |
| frontend/src/components/schedule/ExternalScheduleHandoff.tsx | New: preparation/print controls, complete source/resource/discrepancy document and temporary print portal. |
| frontend/src/components/schedule/externalHandoff.css | New: teal/gold screen document and A4-oriented browser print stylesheet; no fixed-height row clipping. |
| frontend/package.json | Modified: adds test:external:handoff and test:external:handoff:browser scripts only. Dependencies and lockfile unchanged. |
| frontend/tests/externalHandoff.fixtures.mjs | New: explicitly fictional handoff responses; no real backend receipt or validation claim. |
| frontend/tests/externalHandoff.test.mjs | New: eight transport, provenance, complete-row, schema, Unicode fingerprint and error contracts. |
| frontend/tests/externalHandoff.browser.test.mjs | New: fifteen rendered Edge scenarios with fictional HTTP responses and intercepted printing. |
| docs/testing/dashboard-d5/run_checks.py | New: existing evidence-runner pattern, whitelisted child environment, unique synthetic fixture roots and owned browser profile. |

Documentation/evidence: this report; [baseline](testing/dashboard-d5/preservation-baseline.json); [manifest](testing/dashboard-d5/manifest.json); fifteen original timestamped command records; two browser-results.json files and six original PNGs under docs/screenshots/dashboard-d5. The manifest enumerates every created/modified path and SHA-256. No existing report or artifact was replaced.

## UI and request flow

The existing administrator page **/admin/external-schedules** now has a **Validated review handoff** section below reconciliation. It reuses the current D3 preview receipt and D4 mapping choices. There is no new application route or alternate identity selector.

1. Preview manual/CSV/XLSX input using the existing workflow. A response without a current receipt remains a D3-only preview and cannot produce a D5 handoff.
2. Optionally choose existing recognized section, room or faculty/instructor IDs. D4 handles resolution and overlap findings; D5 does not allocate identities or interpret names as stable IDs.
3. Select **Prepare validated review**. The server rechecks the entire signed source and current reference inventory. During loading, any previous handoff is removed. Errors leave no partial or previous handoff.
4. Inspect the complete document. Calendar filters do not change its row set. All original rows remain, including invalid time patterns, unresolved references, ambiguity, missing optional resources and duplicate/overlap findings.
5. Select **Revalidate and print review**. This makes another server request; success renders a synchronous print snapshot and invokes browser printing. A stale/error response prevents the print call. The print snapshot is removed when the call returns, including a thrown printing error.

The document shows supplier, subject/title, original section references, recognized/mapped resource IDs and labels, mapping method, unselected candidate IDs for ambiguity, recurring day/time, optional room/instructor, unverified term, Draft/Tentative intent, Invalid/Needs review findings, original source row, source reference/notes, exact uploaded-file SHA-256, reference-inventory digest, preview fingerprint and validation timestamp. Manual input explicitly has no uploaded-file hash. “Original” refers to D3-normalized input fields; raw file bytes are not retained.

Every document header, source-row section and footer carries **REVIEW PREVIEW — NOT CONFIRMED OR ACTIVE IN GA**. It explicitly says reviewing/printing/exporting is not approval and no commitments are saved, locked or supplied to the GA. No successful-print, approval or publication acknowledgement is fabricated. Canceling the native dialog does not create a stored result.

Changing mappings, replacing/clearing a source, navigating away or refreshing removes the temporary workspace or cancels pending work. No browser local/session storage is added. A visible prepared document is a dated snapshot; later source/reference changes require another validation. A fingerprint is not a durable receipt of institutional approval.

## API and integrity

**POST /api/external-schedules/handoff** uses the existing administrator dependency and exact session Origin/CSRF behavior. It accepts only the existing ReviewRequest shape: a current preview receipt plus bounded explicit mapping IDs. It does not accept a client projection, filtered rows, actor/role, approval flag or substitute source hash.

The shared parser requires application/json, rejects duplicate JSON keys and extra fields, and caps the body at **2 MiB**. Existing limits remain 200 source/mapping rows, twelve section mapping slots per source row and at most 1,600,000 receipt characters. Existing D3 intake remains 1 MiB.

The service calls D4 project for every request. That service verifies the process HMAC receipt before projecting; rechecks the current recognized-resource/fixed-input digest; validates all mappings; reuses D3 domain checks; and recomputes same-resource, duplicate and weekly overlap findings. Its half-open interval semantics and fixed-section behavior are unchanged. It neither treats PreassignedAssignment as fixed meeting times nor activates external constraints.

The response has schema_version 3, handoff_version d5.1, literal preview label, preview_only true, persisted/activated/approved false, preview_id, revalidated_at and the full schema-version-2 review. The ID is **d5- plus SHA-256 of sorted, compact, ASCII-escaped JSON for the complete review projection**. The timestamp is excluded, so identical projections have identical IDs. Changing a mapping, discrepancy, row or reference inventory changes the fingerprint. This is a content identity, not a random allocation, authentication token, digital signature or permanent schedule ID.

The TypeScript boundary validates both schemas, source name/kind/hash, original row identities/content, complete row count and uniqueness, then recomputes the fingerprint. Browser and server use compatible Unicode escaping, including surrogate pairs. Neither the receipt nor signing key is rendered in the document. SHA-256 checking alone does not authenticate an arbitrary externally edited document; the authorized server request and existing signed source remain the validation boundary.

| Condition | Expected / tested API result |
|---|---|
| Missing session | 401 |
| Faculty session with valid CSRF, spoofed role header, wrong Origin or missing CSRF | 403 |
| Valid administrator request | 200, complete preview-only response, no-store and nosniff |
| Forged/process-invalid receipt or changed reference inventory | 409; no partial review |
| Invalid explicit IDs, client projection/approval fields, duplicate keys or malformed DTO | 422 |
| Body over cap | 413 |
| Unsupported manual media type | 415 |

The underlying unavailable-resource path remains inherited from D3/D4; frontend 503 handling is contract-tested. D5 adds no public download endpoint, upload persistence, background job, preview cache, migration or write repository.

## Printing and its verification boundary

The screen document uses the current teal/gold style and a responsive resource/detail layout. Print CSS requests A4 portrait with 12 mm margins, black text, natural page flow and no calendar scroll-box clipping. The printable summary uses the same React document component as the screen view. Imported text uses React text rendering, never raw HTML or an imported URL link.

While the D5 workspace is mounted, the body print portal hides the dashboard chrome. Ordinary Ctrl+P has only a blocked-output notice, rather than a cached handoff. The validated print branch briefly renders the freshly revalidated snapshot and calls window.print; it then clears that snapshot. The existing D3/D4 calendar renderer is reused on screen, not copied into a fixed-height print layout.

**What was actually checked:** real Edge rendering, print-media CSS, synchronous document content/style/row-count checks inside an intercepted window.print call, dashboard suppression, absence of horizontal overflow, complete four-row fixture output, missing/invalid resources, stale print denial, snapshot cleanup and printing exceptions. D5-B10 captures the real blocked ordinary-print view.

**NOT VERIFIED:** native print-dialog selection/cancellation, physical paper output, real PDF pagination, maximum 200-row pagination, other browsers, or nonblocking implementations of window.print. The print cleanup relies on the browser's synchronous print-call behavior; this is a remaining manual Edge acceptance item. No PDF dependency or permanent generated PDF was added. An experimental in-memory Page.printToPDF call appeared only in the failed earlier harness, checked a PDF byte header, and was removed from the final test after a following screenshot timeout. Its old scope string does not establish PDF content/layout acceptance.

## Actual retained test executions

All dates below are **2026-10-21 +08:00**. Command records contain exact commands, cwd, environment, start/end timestamps, duration, stdout/stderr, warnings and exit codes. The runner removes database URLs, credential variables and approval flags from children. Python uses -B and pytest disables cacheprovider. No PostgreSQL operation was performed.

| Check | Time interval | Result / evidence |
|---|---|---|
| Focused backend D2–D5 | 20:53:47.011425–20:54:15.987267 | **137 passed, 0 failed/skipped; 2 warnings; pytest 24.21 s**. Includes 15 D5 + 32 D4 + 61 D3 + 29 D2. [Command](testing/dashboard-d5/20261021T205347010603+0800-backend/command.json) |
| Backend authentication/GA control | 20:57:43.902317–20:59:19.784445 | **46 passed, 0 failed/skipped; 4 warnings; pytest 83.21 s**. [Command](testing/dashboard-d5/20261021T205743898331+0800-backend-regressions/command.json) |
| Frontend contracts | 20:54:25.735158–20:54:28.318758 | **118 passed, 0 failed/skipped**: eight D5 + 110 existing. [Command](testing/dashboard-d5/20261021T205425733991+0800-contracts/command.json) |
| D5 rendered browser | 21:00:16.898942–21:00:27.395212 | **15 scenarios + one parent PASS, 0 failed/skipped**, no recorded runtime exceptions. [Command](testing/dashboard-d5/20261021T210016898305+0800-browser/command.json), [scenario record](screenshots/dashboard-d5/20261021T210016898305+0800-browser/browser-results.json) |
| D1 browser regression | 20:57:41.646709–20:58:26.932652 | **16 scenarios + parent PASS**. [Command](testing/dashboard-d5/20261021T205741644195+0800-d1-browser/command.json) |
| D2 browser regression | 20:57:42.794951–20:58:23.877428 | **13 scenarios + parent PASS**. [Command](testing/dashboard-d5/20261021T205742793775+0800-d2-browser/command.json) |
| D3 browser regression | 20:57:41.623321–20:58:24.038529 | **15 scenarios + parent PASS**. [Command](testing/dashboard-d5/20261021T205741622365+0800-d3-browser/command.json) |
| D4 browser regression | 20:57:42.877117–20:58:26.305641 | **15 scenarios + parent PASS**. [Command](testing/dashboard-d5/20261021T205742876072+0800-d4-browser/command.json) |
| GA monitoring browser regression | 20:57:44.037148–20:59:31.681444 | **51 scenarios + parent PASS**, synthetic HTTP GA state; no real evolution. [Command](testing/dashboard-d5/20261021T205744036223+0800-ga-browser/command.json) |
| Production build | 21:00:12.127800–21:00:23.473774 | **PASS**, 221 modules, JS 876.14 kB / gzip 245.97 kB; existing >500 kB chunk warning. [Command](testing/dashboard-d5/20261021T210012127069+0800-build/command.json) |
| Focused ESLint | 21:00:13.533983–21:00:22.297405 | **PASS**, five selected TypeScript/TSX files, no findings. [Command](testing/dashboard-d5/20261021T210013532677+0800-lint/command.json) |

Do not add parent wrappers to scenario totals or claim focused passes as a full-suite pass. Backend regressions include the existing real-HTTP authentication browser wrapper with isolated SQLite; that is not an end-to-end D5 browser-to-FastAPI test. D5 backend tests exercise real password/session/role/Origin/CSRF checks via FastAPI ASGI, with synthetic identity storage and patched fictional metadata. There is no principal bypass. D5 browser tests run actual React/Edge against synthetic HTTP responses; they do not execute the real D5 backend validator or prove live database authorization.

Runtime: Python 3.14.2, SQLite 3.50.4, Node v24.11.1, Vite 8.2.2, Edge 155.0.4283.62. The two focused backend warnings are Starlette/httpx TestClient and AnyIO BlockingPortal deprecations. Backend regressions additionally report two existing Alembic path_separator warnings during offline SQL rendering. There are no newly failed final checks.

Full-project lint, the full backend/GA suite, production GA generation, performance profiling and PostgreSQL acceptance were not executed in D5. Existing auth regression machinery uses isolated SQLite/offline SQL only; no live migration or PostgreSQL connection occurred. The **17 Phase 4C PostgreSQL cases remain unverified and paused** under their separate approval boundary.

## Browser scenarios and original screenshots

Final browser URL: **http://localhost:61409/admin/external-schedules**, owned temporary Edge profile and ephemeral synthetic API/Vite services. The rendered validation timestamp 12:00Z is fixture content, not an observation timestamp. Actual capture times below have +08:00 offsets. Raw fictional CSV bytes were checked by the fixture. No confirmation or GA mutation request was made.

| Scenario | Action / required observed result |
|---|---|
| D5-B01 | Hold validation response: no document until fresh response arrives. |
| D5-B02 | Filter calendar to one subject: handoff still contains all four original rows, invalid/resource findings and both intake statuses. |
| D5-B03 | Inspect source filename/hash/fingerprint/row details; private receipt absent. |
| D5-B04 | Change mappings: old handoff disappears; newly prepared output retains original labels and mapped canonical IDs/conflicts. |
| D5-B05 | Render literal image/script-looking text and Unicode: no injected elements or script execution. |
| D5-B06 | Return stale preparation: prior document removed and Print disabled. |
| D5-B07 | Return truncated/tampered response: no partial document; retry succeeds. |
| D5-B08 | Make print revalidation stale: another server call occurs, no print invocation. |
| D5-B09 | Fresh print call under print media: all four rows, errors and literal notes present; dashboard hidden; no horizontal overflow. Print call intercepted. |
| D5-B10 | Inspect ordinary-print portal after print cleanup: only blocked-output notice, no old rows. |
| D5-B11 | Clear during delayed preparation: cancellation prevents later document/printing. |
| D5-B12 | Mobile handoff remains contained and readable at 390×844. |
| D5-B13 | Anonymous/faculty route denial: no handoff request or administrator document. |
| D5-B14 | Simulated printing exception: print state cleared and actionable error displayed. |
| D5-B15 | Reload discards temporary handoff; no confirmation, locking or activation controls/requests. |

Final captures, all visually inspected and privacy reviewed:

| Capture | Actual capture time (+08:00) | Viewport |
|---|---|---|
| [D5-B02 complete handoff](screenshots/dashboard-d5/20261021T210016898305+0800-browser/D5-B02-complete-review-handoff.png) | 21:00:21.495 | 1600×1200 |
| [D5-B05 mappings and safe literal text](screenshots/dashboard-d5/20261021T210016898305+0800-browser/D5-B05-mappings-and-safe-text.png) | 21:00:21.846 | 1600×1200 |
| [D5-B10 ordinary printing blocked](screenshots/dashboard-d5/20261021T210016898305+0800-browser/D5-B10-unvalidated-print-blocked.png) | 21:00:22.580 | 1600×1200 |
| [D5-B12 mobile handoff](screenshots/dashboard-d5/20261021T210016898305+0800-browser/D5-B12-mobile-handoff.png) | 21:00:23.104 | 390×844 |

Two earlier captures remain under the 20:56:41 failed-run directory, with original timestamps and scenario records. All six originals are unedited and hash-indexed. They contain only fictional data, not credentials, session headers, backend receipts or institutional faculty records. No screenshot was reconstructed or substituted.

## Earlier failures retained

1. [First contracts](testing/dashboard-d5/20261021T205346958091+0800-contracts/command.json): **117 passed, one failed**. The synthetic response shared nested objects with its source; mutating a response in the test also mutated the expected input. The D5 fixture now clones the projection. Final 118-case rerun passes. This was a fixture issue, not a bypass accepted by the server.
2. [First browser](testing/dashboard-d5/20261021T205641205922+0800-browser/command.json): **seven scenarios passed, eight failed**, with a failed parent wrapper: Node reports 7 pass / 9 fail. A generated test warning contained ? instead of the em dash; it now imports the shared label constant. Tampered-response and print-error messages also lacked a consistent Handoff unavailable heading; the component now has that heading while retaining the detailed message. Several later checks failed after earlier failures. An experimental PDF-buffer step was followed by a screenshot timeout; the exact cause of that timeout was not established. The final harness omits the PDF step and makes its narrower print-evidence boundary explicit.

The complete final fifteen-scenario run passes. Initial and final records/screenshots remain intact. The historical [system bug report](system-bug-report.md) totals were not rewritten to count these scoped D5 findings.

## Preservation and safe reproduction

The pre-D5 baseline contains **587** files, including ignored local data, saved schedules/checkpoints and the Git index. **582 remain byte-identical**, with exactly five approved existing-file changes: the external router, external schema, frontend API, review component and package scripts. No baseline files are missing or unexpectedly modified.

Protected faculty_preferences.json retains raw SHA-256 **72a5f4f239b5cf99cfb6d7159d443375f8496b69c6b3d1d67ad42e449fd2d8a9** and its pre-existing dirty state. Existing faculty UUID/code mappings, account bindings/authentication sources, Phase 4C models/migration/tests, GA operators/fitness/RNG/checkpoints, fixed-section/availability/preassignment behavior, current inputs, schedules/history and all Phase 4B/D1–D4 evidence are unchanged. HEAD and Git index are unchanged from the start of D5. No staging, commit or push occurred.

For repeatable synthetic checks from the repository root, use the existing evidence runner, selecting backend, contracts, build, lint, browser, backend-regressions, d1-browser, d2-browser, d3-browser, d4-browser or ga-browser:

    .\.venv\Scripts\python.exe -B docs/testing/dashboard-d5/run_checks.py <check>

Browser checks need permission to launch the owned Edge renderer and available designated fixture ports; they stop only their own services/profile. The runner uses a fresh evidence directory and strips database configuration. Never change protected data, reuse a private production session, rerun PostgreSQL tests or stop unrelated services to reproduce a screenshot.

For manual native printing acceptance, use an independently isolated, authorized synthetic application environment with current backend receipts. Preview fictional rows including invalid/unresolved cases, prepare the complete handoff, then use Revalidate and print review. Inspect the warning, every row and multi-page layout; cancel once and retry; change mappings/references and confirm revalidation; verify ordinary printing cannot reuse old output while D5 is mounted. This has not been performed against a live D5 backend/browser deployment and does not authorize provisioning or real data entry.

## Limitations and next milestone recommendation

D5 is complete for its implemented temporary-preview scope and the scoped automated checks above. It is **not fully verified across native printing, live browser-to-FastAPI deployment or PostgreSQL**. No usability study, GA-quality result, durable audit trail or production certification is claimed.

Metadata still covers recognized prototype resources rather than every college's authoritative directory. Academic dates, recurrence exceptions, shared-resource policies and confirmation authority remain unresolved. Receipts are process-bound and invalidate on restart/reference drift; there is no durable record, approval/revision history or multi-worker receipt coordination. The content fingerprint can identify an equivalent normalized projection, not a unique institutional transaction. Printing produces a local review copy only; no spreadsheet/PDF export service was implemented.

Recommended next milestone, under a new separately approved task: **durable external-confirmation readiness and the smallest reviewed confirmation scope**. Resolve authority/grants, verified calendar/shared-resource policy and provenance/revision requirements first; obtain separate approval for any minimal later migration and the outstanding isolated PostgreSQL acceptance. Then implement immutable confirmed revisions/constraint sets with atomic stale/conflict rejection, no partial confirmation and no edits to historical records. Only after that acceptance should a separate milestone connect a deterministic detached fixed-meeting adapter to GA inputs, with explicit immutability, hard-constraint, fingerprint/continuation and RNG-preservation tests. Do not equate time-free preassignments with fixed external meetings. None of that work began in D5.

This evidence supports complete temporary review handoff, original/resource provenance, negative access handling and print-gating behavior under the stated fixtures. It does not establish actual GEC confirmation or GA constraint integration.
