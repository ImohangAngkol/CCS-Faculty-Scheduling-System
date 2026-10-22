# Dashboard D7: metadata completion and confirmation-readiness review

Implemented and verified **2026-10-22, Asia/Manila**, against `1e77993e13bf0ddb9974dd51fb79016d24eb4fe1`, main. **D7 IMPLEMENTED / SCOPED AUTOMATED CHECKS PASS.** The normal application has no institutional verification provider: completing metadata cannot make it READY. READY is verified with explicitly fictional trusted-provider backend tests and synthetic HTTP browser fixtures. Real browser-to-FastAPI smoke verifies the default BLOCKED path. No PostgreSQL, permanent tables, confirmation, GA activation or Git mutation occurred.

## Inspection and implementation plan

D3–D6 already provide bounded intake, signed source receipts, resource projection, complete handoff fingerprints and temporary React state. Reuse these services rather than creating another intake/calendar module. Existing recognized identities come from prototype metadata; the seven-table academic foundation has no active authoritative term/evidence service and stays unchanged. Existing authentication verifies sessions, role, Origin and CSRF. Current preview receipts are process-bound but not session-bound; D7 must add server-side session isolation and expiring revision markers without persisting source batches.

1. Add strict metadata/correction/readiness DTOs and a central, independently testable policy. Preserve originals; validate a detached completed candidate using the existing D3/D4 validators.
2. Add a trusted verification interface defaulting to unavailable. User-entered evidence references are claims, never verification. Production assessments remain BLOCKED until an institutional policy/provider is supplied. Test-only injected verification supports a fully fictional READY example, never institutional approval.
3. Bind HTTP-issued preview receipts to authenticated sessions and bounded, expiring process-local revision markers. Reject cross-session, replaced, expired and restarted previews. Store only opaque digests/revisions, not source rows. Reassess and compare current metadata/mappings/evidence before handoff/printing.
4. Extend the existing D4 workspace with persistent-within-page metadata state, original/proposed values, resource applicability, readiness actions and findings. Feed candidate calendar views and complete readiness output into the existing D4/D5 components. Preserve canonical CSV/XLSX and explicit legacy CSV behavior.
5. Run new backend/contracts/browser tests and D1–D6/GA regressions with fictional data, build/lint, preservation/privacy/hash checks. Keep synthetic HTTP browser evidence separate from actual FastAPI authorization; attempt an isolated live smoke only if safe and feasible. Archive failed attempts and limitations before marking completion.

The plan above was written before implementation; completion evidence follows. Read with the existing [D3](dashboard-d3-implementation.md), [D4](dashboard-d4-implementation.md), [D5](dashboard-d5-implementation.md), [D6](dashboard-d6-implementation.md), [confirmed workflows](phase-4c-confirmed-scheduling-workflows.md), [academic foundation](phase-4c2-academic-foundation.md), README, roadmap, bug report and [documentation standard](DEVELOPMENT_DOCUMENTATION_STANDARD.md). Prior reports and evidence are unchanged.

## Implemented workflow and provenance

The existing administrator `/admin/external-schedules` route now includes **Complete metadata and check readiness** inside D4's review workspace. It retains teal/gold styling, canonical CSV/XLSX and explicit legacy CSV selection. No separate GEC page, identity registry, calendar engine or confirmation control was introduced.

Metadata includes supplying college/department, document reference, optional source revision, evidence-reference claim, academic year, term, effective start/end, explicit timezone, weekly applicability, exception status/notes and per-original-row completion. Per-row fields cover title, component, single/shared commitment, explicit recognized section IDs, instructor/room applicability and evidence reference. Optional meeting proposals contain days/start/end plus reason and evidence reference. Course codes and original row identities cannot be replaced through completion.

Original imported values and file SHA-256 stay separate from administrator completion. No title/date/institution/resource is invented. Meeting proposals are shown beside their preserved original values, not written back to a source CSV. D7 validates a detached completed candidate through existing D3 and D4 services. Canonical and legacy originals, including ambiguous/invalid legacy expressions, remain in the original D4 source details and D5 handoff. Proposed corrections without evidence/reason or outside the supported grammar/grid remain blocked.

The same D4 calendar renders the assessed candidate with an explicit administrator-proposal banner. Original reconciliation details remain below it. Existing filters, full-batch validation and resource mappings are retained. Completed section IDs must be recognized; contradictory D4 and completion selections block readiness. Names and Year Level never generate UUIDs. Shared commitments require at least two recognized affected CCS section references in this prototype; broader institutional cross-listing is not inferred.

Metadata stays in React state while opening/closing row details, filtering, reconciling, assessing and preparing a handoff. Edits immediately remove old assessment/output and queue protected invalidation. Mapping changes invalidate readiness; D4 revalidation also invalidates server assessment state. New import, clear, navigation and refresh discard temporary completion. No local/session-storage persistence was added. Inputs provide explicit unknown/unresolved choices rather than silently declaring missing resources not applicable.

## Central readiness policy d7.1

Overall results are **READY** or **BLOCKED**, with per-finding **blocker/warning** classifications, field/row references, related rows, explanation and required action. READY requires zero blockers; warnings remain visible. Not-yet-assessed, assessing, stale/expired and unavailable are separate UI lifecycle states. No status is official confirmation, approval, publication or GA activity.

| Rule group | Blocker | Warning / permitted behavior |
|---|---|---|
| Source | Missing supplier, document reference or evidence-reference claim; contradiction with a nonblank canonical source field; absent trusted verification | Missing revision is a warning because the requirement is "when available". Source/manual-content fingerprints still bind complete originals. |
| Term/dates | Missing academic year/term/dates/timezone; nonconsecutive YYYY-YYYY label; invalid/unordered dates, dates outside the labeled year or beyond the explicit 370-day prototype bound; unsupported timezone | No dates or terms are inferred from filenames, catalogs or defaults. The bound is an implementation restriction, not a claimed institutional rule. |
| Recurrence | Unknown/unsupported weekly applicability; unknown or listed calendar exceptions; nonempty exception notes; no declared meeting day in the effective date window | Only explicit Asia/Manila weekly patterns with sourced "none reported" exception applicability are representable. A claim still needs trusted verification. |
| Subject/meeting | Missing code/title, unknown component, invalid/ambiguous day or time, off-grid/out-of-window intervals, unsupported meeting, missing completion or correction evidence | A sourced external subject outside the prototype catalog is a warning. Administrator title completion and supported proposed corrections remain attributed warnings. |
| Sections | Empty/unrecognized/ambiguous section, duplicate/conflicting identities, unresolved single/shared declaration or inconsistent section count | Existing D4 mappings or explicit completion selections may be used. No identity is allocated. |
| Resources | Unknown applicability; applicable but unresolved/ambiguous resource; not-applicable declaration contradicting supplied/mapped resource | Missing room/instructor is not a verified absence of conflict. Only source-backed not-applicable claims covered by trusted verification can avoid resource blockers. |
| Conflicts | Duplicate meetings, section/faculty/room overlap, unresolved resource conflicts and provisional overlap with loaded legacy fixed-section intervals | Adjacent half-open intervals are allowed. Different unverified term labels cannot suppress overlaps. Legacy fixed-input dates remain unresolved and cannot be assumed compatible. |
| Authority | No trusted provider/evidence for the exact original source, completed candidate, metadata and reference snapshot; mismatched or incomplete verification coverage | A typed evidence identifier is only an administrator claim. It cannot change authority status or authorize later confirmation. |

`external_schedule_verification_service.verification_for` defaults to **None**. There is no environment switch, request flag, filename rule or UI checkbox that grants authority. The trusted interface requires an exact input fingerprint, policy version, evidence reference and coverage of source, term, subjects, sections, recurrence, resource applicability and corrections. Test-only monkeypatches supply fictional evidence. The real deployment remains BLOCKED until institutional policy and an authorized verification provider are separately supplied and reviewed.

Attribution distinguishes preserved original values, administrator-provided completion, unresolved/contradictory findings and trusted evidence marked `verified_for_readiness`. This last status is deliberately narrower than approval. The policy never sets approved/persisted/activated true. Source verification is not a durable institutional audit trail, and no real college or authorized official was impersonated.

## Security, freshness and API behavior

All external routes retain actual administrator role, database-session lookup, exact Origin and CSRF enforcement. Newly HTTP-issued source receipts are HMAC-bound to the authenticated **login session**, not just account ID. A different administrator or another login session of the same administrator cannot use them, including through old review/handoff routes. Service-only parser tests still use internal unbound receipts; HTTP endpoints reject these until the synthetic test client's actual verified session explicitly binds them. No authentication principal bypass was added.

The process retains only bounded session-head digests, revision numbers, assessment fingerprints and expiry markers: **4096 heads maximum**, **1800 seconds maximum**, additionally capped by session expiry. It stores no source rows, completed metadata, files or confirmation records. Reimport replaces the session's source head even when bytes match; previous receipts then fail. Restart/key loss, expiry and eviction fail closed. One current preview per login session means a second tab's reimport invalidates the first tab. Multi-worker/distributed recovery is not implemented.

Source receipts bind the original bytes/hash, normalized rows, D6 originals and reference digest. D7's source fingerprint covers the complete original D4 projection. Its input fingerprint covers policy version, original projection, detached completed projection and metadata. The assessment fingerprint also covers findings/status/verification, excluding timestamp and receipt fields for reproducibility. A distinct HMAC assessment receipt binds receipt kind, session owner, source head, revision, expiry and assessment fingerprint. A valid source receipt cannot be substituted for an assessment receipt.

Every assessment revalidates the signed source and current reference inventory. Invalidation increments a server revision; evaluation cannot publish after a concurrent edit. Preparing/printing an assessed handoff verifies receipt/session/revision, recomputes policy and trusted verification, compares current fingerprints, and checks revision again before returning. Changed source, mappings, metadata, term, reference data or verification cannot reuse an older READY result. Frontend state/READY flags never authorize server behavior. D5 includes the complete original source and new assessment; its content ID covers both when readiness is present. Server assessment receipts are not rendered or returned in printable readiness output.

| Endpoint | Behavior |
|---|---|
| Existing POST `/preview`, `/preview-file` | Existing canonical/legacy inputs; return fresh session-bound receipts. Structural import behavior is retained. |
| Existing POST `/review` | Verifies session/source and invalidates older readiness before existing D4 projection. |
| POST `/readiness` | Receipt, mappings and strict completion metadata; returns computed status, counts, findings, candidate, provenance, timestamp/expiry and assessment receipt. |
| POST `/readiness/invalidate` | Source-specific protected invalidation; returns not_assessed, no institutional writes. |
| Existing POST `/handoff` | Old source-only body remains supported as an explicitly **not yet assessed** review. Once using D7 completion, metadata and current assessment receipt are both required; readiness is freshly recomputed before output. |

Bodies are bounded to the existing **2 MiB** review limit; at most 200 completion rows, 12 sections per row, seven days per proposal and 5000 findings. Strict DTOs reject unknown authority/READY/approval fields, duplicate JSON keys, invalid enums/types/row references and overlong fields. Existing conservative unsafe-text checks apply. No path is accepted for server file access. Authorization failures are 401/403, stale/session/replaced/receipt/revision failures 409, structural validation 422, body-size rejection 413, media-type rejection 415 and unavailable references 503. Responses retain no-store/nosniff. No permanent academic tables or migrations changed.

## Exact implementation inventory

| Path | Purpose |
|---|---|
| backend/routers/external_schedules.py | Modified: bind HTTP sources, protect all review sessions, readiness/invalidate routes and assessed handoff dispatch. |
| backend/schemas/external_readiness.py | New: completion/proposal, assessment/finding and assessed handoff DTOs. |
| backend/services/external_schedule_preview_lifecycle.py | New: bounded expiring opaque session/revision heads. |
| backend/services/external_schedule_readiness_service.py | New: central policy, detached validation, reproducible fingerprints and fresh assessed handoffs. |
| backend/services/external_schedule_verification_service.py | New: trusted read-only verification interface, unavailable by default. |
| backend/tests/dashboard/readiness_support.py | New: binds service-test receipts to actual synthetic login sessions; no principal bypass. |
| backend/tests/dashboard/test_external_readiness.py | New: 52 policy, authority, identity, conflict, integrity, lifecycle, race and actual API security cases. |
| backend/tests/dashboard/test_external_readiness_live.py | New: owned Uvicorn/Edge smoke using real authentication and isolated SQLite. |
| backend/tests/dashboard/test_external_preview.py | Modified: fresh reimport receipts expected; original storage/session/RNG assertions retained. |
| backend/tests/dashboard/test_external_review.py | Modified: bind API test sources to the client's actual synthetic session. |
| backend/tests/dashboard/test_external_handoff.py | Modified: same session-binding adaptation for existing API tests. |
| frontend/src/api/externalReadiness.ts | New: strict completion/assessment DTOs, transport, count/fingerprint/provenance/expiry verification. |
| frontend/src/api/externalSchedules.ts | Modified: optional assessed handoff input/output, strict dynamic assessment verification and complete content hashing. |
| frontend/src/components/schedule/ExternalScheduleReadiness.tsx | New: metadata/row completion, original/proposed values, applicability and readiness controls. |
| frontend/src/components/schedule/ReadinessDocument.tsx | New: shared screen/print findings, counts, authority, fingerprints and action explanations. |
| frontend/src/components/schedule/ExternalScheduleReview.tsx | Modified: retain completion state, invalidate edits/races, show assessed candidate in existing calendar and wire handoff. |
| frontend/src/components/schedule/ExternalScheduleHandoff.tsx | Modified: assessed output or explicit not-assessed label; fresh print revalidation retained. |
| frontend/tests/externalReadiness.test.mjs | New: eight DTO/transport/provenance/fingerprint and assessed-handoff contracts. |
| frontend/tests/externalReadiness.fixtures.mjs | New: explicitly fictional HTTP assessment provider simulation. |
| frontend/tests/externalReadiness.browser.test.mjs | New: eighteen actual Edge scenarios with synthetic HTTP. |
| frontend/tests/externalReadiness.live.mjs | New: five real HTTP/Edge scenarios; private credentials via stdin only. |

Supporting additions: this report; `docs/testing/dashboard-d7/run_checks.py`, preservation baseline, manifest, 33 timestamped command records and one sanitization sidecar; 19 original PNGs and six browser-results records under `docs/screenshots/dashboard-d7/`. The [manifest](testing/dashboard-d7/manifest.json) enumerates every exact path/hash. No dependencies, route/layout files, GA models/operators, academic foundation, datasets or previous evidence were changed.

## Actual validation results

All commands use `.venv/Scripts/python.exe -B docs/testing/dashboard-d7/run_checks.py <selection>` at repository root. Command JSON files record exact child commands, cwd, sanitized stdout/stderr, +08:00 timing, elapsed time and exit code. Children receive a whitelisted OS environment, UTF-8 output and no DB URLs/credential variables/approval flags. Pytest uses new owned roots and disables cache/bytecode output.

| Selection | Final result | Evidence |
|---|---|---|
| backend | **228 passed, 0 failed/skipped**, 2 warnings; 52 D7 + 176 existing. | [Command](testing/dashboard-d7/20261022T221623886262+0800-backend/command.json) |
| backend-regressions | **46 passed, 0 failed/skipped**, 4 warnings. | [Command](testing/dashboard-d7/20261022T221626041684+0800-backend-regressions/command.json) |
| ga-resource-regressions | **3 passed, 0 failed/skipped**, existing synthetic reset/rollback/resource cases. | [Command](testing/dashboard-d7/20261022T221626123852+0800-ga-resource-regressions/command.json) |
| contracts | **132 passed, 0 failed/skipped**, eight D7 + 124 existing. | [Command](testing/dashboard-d7/20261022T220956812698+0800-contracts/command.json) |
| browser | **18 D7 scenarios + one parent PASS**, no runtime exceptions. | [Command](testing/dashboard-d7/20261022T222945753979+0800-browser/command.json) |
| D1–D6 / GA browser | **16 / 13 / 15 / 15 / 15 / 15 / 51 scenarios PASS**, seven parents, total 140 distinct scenarios. | Final per-selection records in manifest |
| live | **5 live scenarios + one Node parent PASS**; one pytest wrapper PASS, 2 warnings. | [Command](testing/dashboard-d7/20261022T222444863847+0800-live/command.json) |
| build | **PASS**, 225 modules; JS 899.48 kB / gzip 251.59 kB. | [Command](testing/dashboard-d7/20261022T222942011136+0800-build/command.json) |
| focused lint | **PASS**, nine selected TypeScript/TSX files. | [Command](testing/dashboard-d7/20261022T222945829317+0800-lint/command.json) |

Backend tests exercise real FastAPI ASGI password/session/role/Origin/CSRF, isolated SQLite and fictional resources. They test wrong-admin and same-admin/different-session access, malformed/oversized requests, all import formats, unknown applicability, missing source/term/dates, unsupported recurrence/grid, duplicates/overlaps/adjacency, explicit correction provenance, conflicting mappings, exact verification coverage, source/reference/provider changes, expiry, restart, invalidation races and receipt substitution. Fictional READY uses an explicitly injected trusted verifier covering the exact candidate; no production authority is configured.

Synthetic browser tests render real React/Edge, but their HTTP policy/authority responses are fabricated fixtures, not backend authorization evidence. Their canonical XLSX fixture is a real in-memory workbook; actual bounded parsing is independently tested through FastAPI. Eighteen scenarios cover canonical/legacy import, metadata, blocked/fictional READY, edit/mapping invalidation, proposed corrections, candidate calendar, handoff/print revalidation, tamper/stale/error states, mobile containment, clear/cancellation and role denial.

The separate live smoke uses actual React → Uvicorn/FastAPI HTTP → isolated SQLite, real password login, cookies, Origin and CSRF. Academic references are synthetic and the real default verifier returns None. It verifies real canonical intake, BLOCKED findings, handoff and invalidation; it does **not** prove real institutional READY, real PostgreSQL or all live import/error/role permutations. The test-only outer CORS wrapper admits exactly its new ephemeral frontend origin because the production middleware was constructed before that origin existed; inner authorization remains unchanged. Backend/frontend consistently use localhost for SameSite cookies. Credentials travel via child stdin only and are never put in a file, command argument, environment, screenshot or report. Only owned servers/browser/profile are stopped.

Parent/pytest wrappers are not counted as additional distinct acceptance scenarios. No full backend/GA suite, production GA evolution, performance or usability study ran. Existing auth regressions include isolated SQLite and **offline SQL rendering**, not execution of PostgreSQL migrations. **The 17 Phase 4C PostgreSQL cases remain paused/unverified.**

Warnings are the existing Starlette/httpx and AnyIO BlockingPortal deprecations, plus two Alembic path_separator warnings in auth regressions. Build warns about the existing large bundle and the readiness module being statically and dynamically imported (the dynamic boundary validates after module initialization; it is not a code-splitting optimization). No global cleanup was performed to suppress warnings.

## Retained failures, corrections and evidence scope

1. First backend: **225 passed, one failed**, 2 warnings. An old D3 HTTP test expected identical receipts for identical reimports. It now compares identical source content while asserting different session revisions; no storage/security assertion was removed. The next run passed 226; two additional guard regressions raised final coverage to 228. Opaque synthetic receipts in the first failure output were redacted; the sanitization sidecar preserves original/sanitized hashes and reason without retaining the sensitive original.
2. First D7 browser: **16 scenarios passed, two failed**, plus failed parent. A generated test expectation had ? instead of an em dash; it now checks the stable phrase. Metadata controls and the unwrapped source hash also caused horizontal overflow. Second browser: **17 passed, one failed**, parent failed. The remaining hash wrap was fixed; final 18 pass. D4/D5/D6 first regression runs each had **14 passed, one mobile failure**, plus failed parent; their reruns each pass 15. No original failed record/image was deleted.
3. First live attempt: **one pytest failure** from Windows stdout encoding; complete child outcome counts were not captured and are not reconstructed. The fixture was also corrected to use an exact ephemeral-origin CORS wrapper. Second live: **one child scenario passed, four failed**, failed parent and pytest wrapper. Login succeeded but subsequent requests lost SameSite cookies because the API used 127.0.0.1 while the UI used localhost; consistent localhost fixes this. Failed sidecar-directory creation was also corrected. Third live: all five pass. These were isolated fixture failures; production authentication/CORS configuration was not weakened or changed.
4. A successful browser capture initially framed the intake viewport in B03 rather than the assessment below it. Those originals remain accurately scoped; a fresh successful run reframed the actual BLOCKED assessment. Later final captures show the added visible source/input fingerprints. Earlier successful live capture predates those final display-only fingerprint/unassessed-label additions; authentication/API behavior is unchanged. Final D7 and D5 browser/build/lint checks cover the final UI.

Full failed/successful command records and original scenario results are indexed in the manifest. The historical bug report was not rewritten and no failed run was relabeled PASS.

## Browser captures and manual reproduction

Edge **155.0.4283.62**, Node v24.11.1, Python 3.14.2, SQLite 3.50.4, Vite 8.2.2. Final synthetic URL: **http://localhost:49867/admin/external-schedules** (the scenario JSON is authoritative for the actual ephemeral URL); live URL and capture times are recorded in its separate scenario JSON. Synthetic assessed timestamps/fingerprints and 2099 expiry are fixture content, not capture times or lifetime guarantees.

Final synthetic originals (1600×1200 except mobile 390×844): [BLOCKED](screenshots/dashboard-d7/20261022T222945753979+0800-browser/D7-B03-completed-but-unverified.png), [fictional READY](screenshots/dashboard-d7/20261022T222945753979+0800-browser/D7-B04-fictional-ready.png), [assessed handoff](screenshots/dashboard-d7/20261022T222945753979+0800-browser/D7-B08-assessed-handoff.png), [mobile completion](screenshots/dashboard-d7/20261022T222945753979+0800-browser/D7-B16-mobile-completion.png). Real HTTP capture: [live FastAPI BLOCKED](screenshots/dashboard-d7/20261022T222444863847+0800-live/D7-L03-live-fastapi-blocked.png), 1600×1200.

All 19 unedited PNG originals were privacy/correctness reviewed, including byte-identical repetitions whose hashes match visually reviewed images. No real faculty records, passwords, cookies, receipts, private account lists or generated screenshots are included. Initial B03 images show the intake viewport and do not themselves demonstrate the below-fold blocked assessment. Printing evidence is intercepted `window.print` plus actual print-media DOM/styles; native dialogs, printer output, PDF pagination, 200-row printing and other browsers remain NOT RUN.

Safe reproduction: use the D7 runner's backend/contracts/browser/live/build/lint selections and existing regression selections. The live selection requires permission to launch its owned loopback servers/Edge. Never configure an institutional DB or alter source datasets to obtain a screenshot. In an independently isolated administrator environment, import a fictional canonical/legacy file, reconcile resources, complete term/source/row fields, assess and inspect blockers/actions. Unknown applicability stays blocked; entered evidence alone cannot grant READY. Propose a sourced correction, reassess and compare original/candidate, then prepare/print a BLOCKED review. Edit a term/mapping and verify old output disappears. Refresh/reimport should discard the prior revision. READY requires the explicitly fictional test provider; no real authority setup is supplied or authorized by these instructions.

## Preservation, limitations and D8 boundary

Baseline: **651 files; 644 unchanged; exactly seven intended existing changes** in routing, API/components and three session-adapted tests. Every backend/data file, the pre-existing protected preferences byte contents, faculty UUID/codes/account mappings, section/room identifiers, GA operators/fitness/selection/RNG, chromosome/checkpoint formats, active fixed-section input, schedules/history, Phase 4C and prior evidence remain unchanged. Git HEAD/index are unchanged; nothing staged/committed/pushed. Evidence hashes and exact file inventory are in the manifest.

Remaining institutional inputs: authorized verification policy/provider and evidence trust, correct source revisions/attribution, verified academic calendars/exception semantics, subject descriptions, all affected sections/cross-listings and shared-resource applicability/identities. Current recognized catalogs remain prototype metadata. Manually typing these values does not resolve authority. The seven-table academic foundation is preserved and neither provides nor is misused as an active confirmation store.

D7 is complete for temporary completion, conservative readiness, session isolation and scoped validation. It does not supply durable authority, multi-worker receipt coordination, confirmation/revision history, official schedules, immutable GA constraints, Chair approvals, faculty requests/weighting, optimization or C++ changes. The UI currently states no verifier is configured, matching this deployment; READY browser fixtures deliberately simulate a future trusted-provider response and are not institutional evidence.

Recommended **D8 boundary**: agree and review the institutional source-verification policy, evidence/provider trust and authoritative calendar/resource contracts, then implement the smallest separately approved durable provenance/confirmation design with its own database authorization and outstanding PostgreSQL acceptance. Actual immutable external constraint compilation and GA activation should follow a separately reviewed acceptance gate preserving reset behavior, checkpoints and RNG. No D8 work began.

Thesis claims supported here: metadata completion, conservative explainable readiness, original/proposed separation, session/freshness rejection, preview calendar/handoff, real authentication under synthetic storage and accurately scoped browser evidence. No institutional verification, GA-quality improvement, production readiness or actual approval is claimed.
