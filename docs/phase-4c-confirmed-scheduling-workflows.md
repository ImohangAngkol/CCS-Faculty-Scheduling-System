# Phase 4C: confirmed external schedules and faculty adjustment workflows

Requirements/design update: **2026-10-20, Asia/Manila**. Baseline HEAD: `3167cda2bd2d86011b50ea582026a4c39accb529`. Status: **TWO PROFESSOR REQUIREMENTS CONFIRMED; MODULES DESIGNED, NOT IMPLEMENTED**.

This document extends [C14/C15 in the academic contract](phase-4c1-academic-data-contract.md#10-confirmed-professor-requirements-c14-and-c15) and the [future relational dictionary](architecture/phase-4c1-relational-schema.md#9-confirmed-requirement-extensions-2026-10-20). The approved [seven-table 4C.2 implementation](phase-4c2-academic-foundation.md) and `4c_0001` are unchanged. Its historical offline results are not rerun or reused as proof of these workflows. No PostgreSQL connection, real source import, service operation, migration or application-code edit occurred.

## 1. Confirmed outcomes and scope boundaries

**R-GEC:** Other colleges prepare GEC/non-CCS schedules first and send them to CCS. CCS administrators enter/import them, review and confirm them, and generate CCS schedules around the resulting fixed commitments. Section, faculty and room conflicts must be prevented where applicable; the GA cannot move or overwrite confirmed external meetings. Manual entry, CSV/Excel import, review, separate tentative/confirmed states and revision history are required.

**R-ADJ:** Faculty review their assigned proposed GA schedules and submit change requests. Every change requires the Department Chair's scoped approval. Rejection leaves the selected schedule unchanged; approval produces a new hard-valid schedule revision while retaining the original GA schedule and all earlier revisions. Unauthorized edits, concurrent double approval, stale-base overwrites and hard-constraint overrides must be rejected.

These requirements are confirmed. The detailed entity names, capability model, transition policies and milestone labels below are design proposals requiring implementation review. They do not authorize additional tables in 4C.2, institutional data access, new GA behavior or a third authentication role.

## 2. Inspected implementation: reuse and gaps

Only source text was inspected; no scheduling modules were imported or executed and no faculty/source rows were read into this design.

| Existing source/component | Reusable behavior | Gap / safe adaptation boundary |
|---|---|---|
| [Functions.py](../backend/genetic_algorithm/utils/Functions.py): `_parse_fixed_section_days`, `apply_fixed_section_schedules`, `get_fixed_section_schedule_entries`, `validate_fixed_section_conflicts` | Explicit day parsing, fixed section occupancy, fixed meeting extraction and a final section conflict guard; uses 30-minute resource blocks | Current consolidated loader represents section occupancy, not a managed tentative/confirmation workflow or a comprehensive external instructor/room calendar. Some rows/days can be skipped with warnings. Future import must quarantine discrepancies atomically, not treat warnings as complete success. |
| [PreassignedAssignment.py](../backend/genetic_algorithm/models/PreassignedAssignment.py) | Separate external instructor identities, shared resource objects and locked instructor/room validation | Its validator explicitly does **not** fix meeting times. Time-free preassignments must not stand in for externally pre-plotted meetings. Keep both concepts distinct and avoid duplicate reservations for the same meeting. |
| `Functions.py`: `find_resource_conflicts`, section/room/eligibility/preassignment validators | Existing overlap and resource constraints provide regression oracles | The generic conflict helper ignores missing/Unknown resources and skips identical same-class entries. It is insufficient alone for confirmation: unknown required identities and duplicate meetings must be rejected explicitly. Cross-department/date-effective external coverage is not established by existing helpers. |
| [ga_publication_service.py](../backend/services/ga_publication_service.py) and [chromosome_service.py](../backend/services/chromosome_service.py) | Non-scoring publication validation; compares required offerings, metadata, fixed blocks and declarations; reconstructs detached resources for validation | Current templates originate in legacy file-backed globals. A future pinned-input adapter and complete candidate validator need independent tests before reuse in database approval. Never mutate the working chromosome, overwrite saved best/latest, or call fitness/GA search during approval. |
| [identity_service.py](../backend/services/identity_service.py), [identity_models.py](../backend/identity_models.py), [preference_authorization.py](../backend/services/preference_authorization.py) | Stable faculty UUID/code bridge, verified user binding and server ownership checks | Existing role CHECK is admin/faculty only; no Department Chair capability, department membership, approval authority or scoped appointment workflow exists. Existing admin guard does not prove Chair authority. |
| [main.py](../backend/main.py), [auth_service.py](../backend/services/auth_service.py), [apiSession.ts](../frontend/src/services/apiSession.ts) | Verified sessions, mutation Origin/CSRF checks and browser session-aware requests | Apply the real server mutation protections to all future import/confirm/request/decision endpoints. No principal/header bypass or independent raw credential transport. |
| [ScheduleView.tsx](../frontend/src/pages/admin/ScheduleView.tsx), [WeeklySchedule.tsx](../frontend/src/components/schedule/WeeklySchedule.tsx), [ScheduleTable.tsx](../frontend/src/components/schedule/ScheduleTable.tsx), [ScheduleFilters.tsx](../frontend/src/components/schedule/ScheduleFilters.tsx), [facultyDisplay.ts](../frontend/src/components/schedule/facultyDisplay.ts) | Existing schedule rendering/filter/display patterns | Admin view reads current GA context, not term/revision/approval-aware records. Weekly view currently supports faculty/room modes; section overlays, stable revision DTOs and confirmed/tentative semantics need explicit adapters and rendering tests. Do not expose all department assignments through an own-faculty API. |
| [PreferenceCalendar.tsx](../frontend/src/components/faculty/PreferenceCalendar.tsx) and [preferenceModel.ts](../frontend/src/components/faculty/preferenceModel.ts) | Day/time/component form and calendar interaction patterns, paired meeting handling | Preference editing is an expression of wishes, not an approved schedule write. Reuse visual/form ideas through a separate proposal model; never connect request actions to preference persistence or enable direct schedule dragging. |
| [AppRoutes.tsx](../frontend/src/routes/AppRoutes.tsx), [ProtectedRoute.tsx](../frontend/src/routes/ProtectedRoute.tsx) | Existing authenticated layout and denial/error states | `/faculty/schedule` is a routed placeholder and `pages/faculty/MySchedule.tsx` is empty. No Chair portal, request queue, import/review page or request workflow exists. A new scoped-capability route guard will need reviewed server-supplied capabilities; the current admin/faculty guard cannot supply it. |

Existing fixed/preassignment tests such as [test_ga_hard_constraints.py](../backend/tests/test_ga_hard_constraints.py) and [test_preassigned_assignments.py](../backend/tests/test_preassigned_assignments.py) are regression references, not new acceptance evidence. Saved schedule/chromosome/history endpoints do not implement institutional schedule versioning or Chair decisions. No existing Excel schedule-import UI/service was established in this review.

## 3. GEC / External Schedule Management module

### Operator workflow

1. Choose an explicit confirmed academic term and owning CCS department. Record supplying college/unit, received reference and source kind. A provider-confirmed schedule remains distinct from a **system-confirmed active constraint**.
2. Manually enter a commitment or upload a private CSV/XLSX file. Preview column mappings, course label, affected sections, applicable instructor/room identities, weekday, start/end and effective dates. The file must not create faculty accounts or automatically promote descriptive labels to verified catalog records.
3. Stage as draft/tentative. Validate every row, duplicates, resource reconciliation, term/grid/date compatibility and coverage. Preview shows original row references and discrepancies. No active constraints or GA globals change.
4. Submit for review. The proposed confirmation actor is a CCS administrator with a separately assigned `external.confirm` capability for this department; who may receive that authority is an institutional decision. The faculty-request Chair approval requirement does not automatically imply that all external confirmations need Chair approval.
5. Confirm the complete validated replacement, pin immutable meeting rows/resource links, and atomically select a new constraint-set revision. An unresolved required resource, unsupported pattern, missing date interpretation or unexplained skipped row blocks confirmation.
6. Display confirmed commitments as locked overlays and tentative commitments separately with visible text/status, not color alone. Tentative records must neither silently constrain generation nor disappear from the review queue.
7. Correct or withdraw by a reviewed successor revision with reason and source provenance. A confirmation supersedes the selected head, not the old record contents. Withdrawal is a confirmed historical operation contributing no active intervals in the new set; deletion of the old commitment is unavailable.

### Input/import contract

Canonical staged meetings use term UUID, department scope UUID, stable external record/meeting keys, provider/course labels, zero or more explicit section/instructor/room links, local day, minute bounds and effective local date bounds. At least one applicable affected resource is required. Multiple sections sharing one real meeting use links on that one meeting, not independent duplicate bookings. Repeated weekly occurrences and date-window interpretation must be explicit; semester dates are not inferred from filenames.

Each resource category has an explicit resolution state: resolved, unknown, or institution-approved not-applicable with reason. Unknown is never treated as an empty resource that passed a conflict check. Default policy blocks activation while any required applicable mapping is unresolved. Whether section-only confirmation is legitimate when faculty/room details genuinely cannot affect CCS/shared resources remains an institutional decision; until decided, do not claim full coverage.

Initial file support is proposed as bounded UTF-8 CSV and XLSX with selected sheet and explicit header/date/time mapping. Do not evaluate spreadsheet formulas, macros, external links or active content; reject/quarantine relevant formula cells and unsupported formats. Define file/row/column/decompressed-size limits before implementation, retain originals privately with SHA-256 and parser version, and keep raw files and private reconciliation outside Git. Legacy XLS or unusual workbooks require explicit format policy; Excel compatibility is not a promise to execute Excel. Manual rows retain actor/time/reference provenance without an invented upload hash.

Duplicate keys/conflicting rows are discrepancies, not last-row-wins upserts. Source replay must identify a matching reviewed batch without activating again; a different source/hash or changed row set requires explicit reconciliation. No partial confirmation: imports cannot publish their valid subset while silently skipping bad rows. CSV export, if later added, must prevent spreadsheet formula execution in exported free text.

### External constraint coverage

Use half-open intervals `[start,end)` with intersecting effective dates and matching weekday. Adjacent meetings are permitted; all overlapping applicable section, canonical instructor and canonical room reservations are hard conflicts. Include collisions between external commitments themselves and between external and CCS meetings. Stable resource IDs govern matching; neither department-local names nor unknown/blank strings prove two resources differ.

The current GA supports specific day/time grids and component patterns. Unsupported external intervals (for example those not representable without rounding to the existing 30-minute resource grid), Sunday/overnight patterns or date exceptions stay staged until an exact adapter/validation policy is approved. Do not widen blocked periods, round away conflicts, change engine grids or pretend date-aware protection already exists. Rooms/faculty shared across departments require an authoritative shared identity mapping and conflict visibility/locking contract before cross-department protection can be accepted.

### Activation during/after a run

Pin the exact external constraint set and mappings in the future academic input snapshot, then compile detached calendars without changing operators, equations, RNG consumption or old checkpoint formats. Existing section reservations can be a target representation; applicable instructor/room reservations also need coverage. Assert input immutability and preserve confirmed commitments in accepted schedule output.

A run or preview using an old external head cannot publish silently after confirmation changes that head. Reject stale publication and retain its original output/provenance. New external commitments must not be injected into a paused population or historical saved artifact.

For late incoming external revisions conflicting with a selected schedule, preserve the incoming/provider-confirmed facts in staging and show the blocking discrepancy. Proposed default is **no conflicting activation and no silent schedule edit**. Mark review readiness as blocked while authoritative incoming commitments remain unresolved; do not describe the current schedule as revalidated against them. A coordinated new constraint-set plus validated schedule replacement may be needed; its publication/approval policy requires explicit design approval. Receiving authoritative external facts is not erased merely because activation is blocked.

## 4. Faculty Change Request module

Faculty access a server-filtered view of their own assigned CCS meetings, showing term, selected schedule revision, original GA provenance and fixed external overlays relevant to their resources. Preferences remain a separate workflow.

The proposed initial request allows day/time/room changes to that faculty member's own existing CCS assignments only. Preserve offering, section, instructor, lecture/lab component identity, required hours and complete paired-meeting groups. Removing offerings, changing instructors, swapping with another faculty member, moving external commitments or changing workload/eligibility is unavailable. Those would require a separate multi-party policy and workflow, not a larger request JSON payload.

State flow: `draft -> submitted -> approved | rejected | needs_rebase`; draft/submitted may be withdrawn before decision according to the reviewed policy. Submitted payloads are immutable. A rebase creates an explicit new reviewed proposal linked to the previous request; no automatic merge. An approved request is not silently editable or withdrawable; reversal requires another Chair-approved change producing a further revision.

The request captures requester user/faculty identity from the authenticated account, term/scope, exact base schedule revision, constraint-set-at-submit, per-meeting before hashes, complete proposed component groups and private reason. Client-supplied faculty/department identity is a selection hint, not authorization. Preview may report hard failures and soft preference/workload impacts; it never writes the active schedule or computes new GA fitness.

Faculty can view their own request/decision history, including clear pending/rejected/stale reasons. They cannot view colleagues' private requests through guessed IDs, approve anything, or submit a change by editing schedule/head fields directly. Deciding actors must have the current Chair authority even where the requester is an administrator or Chair.

## 5. Department Chair Approval module

### Permission model

Keep the existing account role CHECK (`admin`, `faculty`) and UUID binding intact. Propose effective-dated, revocable `academic_scope_grants` with separate `external.manage`, `external.confirm`, `schedule.review` and `schedule.change.decide` capabilities. Chair appointment gives the last two in the appointed department. Department membership/assignment determines request scope; no interface-supplied `is_chair`/role/header can establish it.

| Actor | External records | Schedule/request access | Decision power |
|---|---|---|---|
| Faculty | Read authorized relevant confirmed overlays; tentative exposure subject to policy | Own assignments and own drafts/submissions/history | None |
| CCS administrator without Chair grant | Scoped manual/import/review functions only with matching external grants | Scoped operational review only if separately authorized | Cannot approve/reject faculty changes merely because role=admin |
| Current Department Chair with scoped grant | External confirmation only if separately granted | Assigned department queue and needed candidate/conflict context | Approve/reject within that department after validation; no hard override |
| Chair from another department | No implied access | No out-of-scope queue/candidate access | Denied |
| Appointment administrator | Separately governed grant administration | No implicit schedule write authority | Cannot fabricate a Chair decision |
| Anonymous, inactive/revoked session, expired/revoked Chair grant | Denied | Denied as applicable | Denied |

Proposed safe default prohibits self-approval, including a Chair requesting changes to their own schedule. Alternate/acting Chair and delegation need institutional confirmation; an ordinary administrator is not the automatic fallback. There is no forced-approval button or special hard-constraint bypass for any role. Appointments and scope grants need a reviewed granting authority and audit; this design does not implement identity/account administration.

### Atomic approval/rejection protocol

1. Authenticate the live session and apply Origin/CSRF protections. Load the requested scope and current grant from server storage; fail closed if missing, expired, revoked or mismatched. Confirm allowed review window and term lifecycle.
2. Load the immutable submitted request, base schedule/input snapshot and current head references. Verify every target is still owned by the requester and that affected parents/resources belong to the permitted term/department.
3. Build the full candidate as a detached copy of the base revision plus the allowlisted proposed changes. Include all unchanged CCS meetings and the entire applicable confirmed external resource set. Do not validate only the moved row or run GA/fitness during review.
4. Before commit, acquire a documented common lock order for term/schedule/external heads, request and authority grant, plus any canonical shared-resource coordination required across departments. Grant revocation and external confirmation must follow that same protocol. Re-read current authority/heads after locking; use bounded lock/statement limits. Preview-time validation never replaces this step.
5. If the selected schedule changed, return stale conflict and require explicit rebase/resubmission. If external/input/validator context changed, invalidate the preview receipt and revalidate against current context; block/rebase where proposal meaning changed. Do not automatically update the selected schedule or use an old validation hash.
6. Validate all hard constraints again under the pinned current transaction context. Bind result to full candidate hash, base/input IDs, selected external set hash and validator version. Outside-transaction expensive preparation is advisory only; authoritative commit-time verification must use the locked context.
7. For approval, atomically create the full immutable child schedule revision/meetings, record exactly one Chair decision plus audit event, update request state and advance the schedule head using compare-and-swap. Exactly one decision may reference the new adjusted revision. An idempotent replay returns the original decision; a conflicting replay gets 409, never a second revision.
8. For rejection, record the scoped Chair's reason/decision and request state/audit only. The head and every schedule meeting/revision remain unchanged. A hard-invalid request may be rejected without treating that validation failure as an approved change.
9. On authorization/storage/validation/lock failure, roll back the entire transaction. No partial approved state, orphan revision, decision without schedule, or head without audit. Notify users only after commit; outbox/delivery implementation is a separate decision, not a reason to send messages now.

All validators enforce existing hard rules: required offering completeness; no duplicate/lost meeting; component duration/count/continuity and legal templates; section/faculty/room overlaps; confirmed external reservations; room type/calendar; explicit faculty eligibility; existing hard workload ceiling and declared locked assignments; same faculty across an offering's components; permitted term/date/grid and lifecycle. Preserve current formulas and threshold semantics; tentative preferences are not hard rules by default. Unknown capacities/enrollment are not invented hard constraints. Unknown required external resource mapping blocks the coverage claim rather than bypassing validation.

## 6. Proposed API contracts (not existing endpoints)

Base namespace: `/api/academic/terms/{term_id}` with explicit server-validated department scope. Normal academic dataset IDs and schedule/external revision IDs are included in DTOs; requests cannot fall back to another term or legacy global head. All mutation DTOs are allowlisted. No endpoint described here is implemented.

| Relative endpoint | Proposed operation / authority |
|---|---|
| `GET /external-commitments` and `GET /external-commitments/{id}/revisions` | Scoped list/history, with status, coverage and authorized provenance visibility |
| `POST /external-commitments` | Manual draft creation; `external.manage`; creates no active constraint |
| `POST /external-imports/preview` | Private bounded CSV/XLSX staging/preview with discrepancies; `external.manage`; never implicit confirm |
| `POST /external-commitments/{id}/revisions` | Draft correction/withdrawal successor referencing the previous revision and expected row version |
| `POST /external-revisions/{id}/submit-review` | Freeze review candidate; `external.manage` |
| `POST /external-revisions/{id}/confirm` or `/reject` | Reviewed confirmation/rejection; `external.confirm`; expected revision and current constraint-head version; no hard override |
| `GET /external-constraint-sets/current` | Selected immutable set ID/hash and coverage, filtered to caller's rights |
| `GET /schedules/current` and `GET /schedules/{series_id}/revisions/{revision_id}` | Faculty receive own assignments only; scoped reviewer receives necessary department context; explicit immutable revision DTO |
| `POST /schedule-change-requests` | Own allowlisted draft against explicit base revision; requester identity server-derived |
| `POST /schedule-change-requests/{id}/validate` | Own draft or scoped reviewer preview; returns candidate hash/context, hard violations and advisory impacts; no head mutation |
| `POST /schedule-change-requests/{id}/submit` or `/withdraw` | Requester's permitted state transition with expected request/base versions; no decision power |
| `GET /schedule-change-requests/mine` and `GET /schedule-change-requests/{id}` | Own history or scoped Chair review; no arbitrary faculty impersonation |
| `GET /chair/schedule-change-requests` | Queue filtered by current server-side departmental Chair grants |
| `POST /schedule-change-requests/{id}/decision` | Chair only; approve/reject, reason, expected request/head versions and idempotency key; server recomputes authority and validity |

GET is read-only. No generic `PATCH schedule`, direct `PUT selected-head`, `DELETE history` or `force=true` is exposed. Proposed errors: 401 unauthenticated, 403 unauthorized, non-disclosing 404 where appropriate, 409 stale/state/idempotency conflict (or documented 412 If-Match failure), 422 domain/hard-constraint violation, 413 oversized import, sanitized 503 storage unavailable. Use bounded pagination and privacy-filtered conflict DTOs; never disclose another department's private records simply to explain a collision. No raw cookie/token/connection dumps.

## 7. Database dependencies and versioning

The [schema extension dictionary](architecture/phase-4c1-relational-schema.md#9-confirmed-requirement-extensions-2026-10-20) lists eighteen future relation candidates. They require later approved academic profiles/instructors/rooms/input snapshots/import/audit dependencies from the broader draft; none is silently added to the seven-table foundation.

Stable external commitment identity is distinct from its immutable confirmed revisions and selected constraint-set snapshot. Stable schedule series is distinct from immutable full schedule revisions and a selected head. Base/root meeting lineage survives moves without using the mutable day/time as identity. Requests reference exact base rows and proposed before hashes; decisions link a request one-to-one to its approved revision where applicable.

Future input snapshots must pin a relational external-constraint-set FK, not merely a JSON name/hash. Schedule revision's input snapshot and external set must agree through same-context composite keys and aggregate validation. An approval against a newer external set needs a new `approval_validation` context snapshot with explicit lineage; the root `ga_input` snapshot is never rewritten or presented as having used different constraints. Relevant academic dataset changes instead require explicit rebase/replanning. Academic input, external set and schedule publication must be captured/advanced using a consistent transaction protocol. Cross-department physical room/shared faculty aliases need a canonical resource model before those FKs and locks can be finalized. Current department-scoped room/instructor drafts alone do not establish globally shared identity.

Retain old payloads and audit lineage; do not delete requests, confirmed revisions or the GA root to free keys. Confirmed external facts are not directly editable through `academic_fixed_section_blocks` as a second source of truth. The future fixed-block view/adapter derives from the chosen set; existing time-free preassignments remain separate. Do not copy private upload files or new schedule payloads into fingerprinted `backend/data`, saved best/latest, history or checkpoint locations.

## 8. Recommended milestones (proposed labels only)

| Milestone | Deliverable and prerequisites | Acceptance gate |
|---|---|---|
| 4C.2 acceptance | Finish separately approved PostgreSQL validation of the existing seven-table foundation | Actual isolated PostgreSQL evidence; no scope expansion |
| 4C.3 policy/resources and external staging | Resolve department grants, shared-resource IDs, calendar/grid policy; review minimal later migrations; build manual + CSV/XLSX draft/preview/review UI | Synthetic imports, permission matrix, discrepancy/privacy tests; zero activation during preview |
| 4C.4 confirmed external constraints | Immutable revisions/sets, confirmation/withdrawal/history, deterministic detached adapter and stale-publication gate | Exact section/faculty/room fixed protection; unsupported inputs block; legacy engine/fingerprint/continuation compatibility separately reviewed before activation |
| 4C.5 immutable proposed schedules / My Schedule | Persist pinned GA proposal revisions without changing old artifacts; own-assignment view and provenance/history | Exact baseline meeting equivalence, server-filtered ownership, original GA root retained |
| 4C.6 faculty requests and Chair decisions | Explicit scoped authority, request forms/queue, full hard validation and atomic one-time decisions | Positive/negative, concurrency, stale-input, rejection/rollback and real UI acceptance |
| 4C.7 integration and institutional pilot | Resolve late external revisions/cross-department publication and backup/retention policies; separately approve institutional import/cutover | Full end-to-end synthetic evidence first, then private approved reconciliation/pilot; no production or GA-continuation claim by inference |

These labels are sequencing recommendations, not a renumbering of an already approved roadmap. A later review must choose each migration's smallest dependency closure. GEC confirmation should precede GA activation; immutable schedule baseline should precede request approval. No future milestone is implemented here.

## 9. Proposed acceptance tests: NOT RUN

| ID | Required result / evidence later |
|---|---|
| EXT-01 | Manual, CSV and XLSX equivalent synthetic inputs yield the same normalized meetings; manual provenance has no fake file hash; source replay is nonduplicating. |
| EXT-02 | Missing headers, malformed dates/times, formulas, unsupported grids, oversized/archive-bomb files, duplicate/conflicting keys and unknown resource aliases produce row-specific discrepancies; no partial active writes. |
| EXT-03 | Tentative rows are separately visible but reserve no hard blocks; unconfirmed/draft revisions cannot become a selected constraint member. |
| EXT-04 | Confirmation/withdrawal/replacement creates new immutable set/history; valid old records and source hashes remain; direct edit/delete and wrong-context FKs fail. |
| EXT-05 | Overlapping external and CCS meetings conflict on each applicable section/instructor/room, including several sections sharing one meeting and cross-department canonical resources; adjacency remains valid. |
| EXT-06 | Confirmed external times/resources survive generation/publication unchanged. Compare payload/hash, original input fingerprints, RNG state/call counts, hard constraints and old artifacts under synthetic fixtures; no soft fitness changes. |
| EXT-07 | Constraint changes during generation, pause or approval reject stale publication/preview; conflicting late confirmation blocks activation and exposes review status without rewriting any schedule/checkpoint. |
| REQ-01 | Faculty see own assignments and may submit only allowlisted changes to own complete component groups; no colleague/external/offering/instructor/priority edits through guessed IDs or extra fields. |
| REQ-02 | A submitted request does not change schedule head, meetings, original GA payload, preferences or checkpoints; submitted proposal is immutable and an explicit rebase retains lineage. |
| CHAIR-01 | Correct department Chair can decide; ordinary admin, requester, other department Chair, anonymous/inactive session and expired/revoked grant are denied with valid CSRF in ownership tests. Verify self-approval default and appointment/delegation policy. |
| CHAIR-02 | Approval validates the whole candidate, all unchanged assignments and confirmed external resources; bad room type, overlaps, missing hours/meetings, eligibility, workload ceiling and unsupported component patterns block approval. No override parameter works. |
| CHAIR-03 | A valid approval creates exactly one full child revision/decision/audit and advances head once; root and all prior schedule payloads/hashes remain unchanged. |
| CHAIR-04 | Rejection records the reason/decision but preserves schedule/head hashes and original GA revision exactly. |
| CHAIR-05 | Concurrent approve/approve and approve/reject, Chair revocation, external confirmation and competing schedule-head change cannot double decide, lose updates, validate stale context or bypass scope. Use real isolated PostgreSQL interleavings, not only mocks. |
| CHAIR-06 | Failure between revision, decision, audit and head updates rolls back everything; idempotent retry returns the original decision; conflicting retry returns 409. Sanitized unavailability preserves the original session/schedule state. |
| UI-01 | Genuine browser tests cover separate tentative/confirmed overlays, preview errors, own-schedule view, request submission, Chair denial/approval/rejection, stale refresh and revision history. Capture actual screenshots/times/browser/version with synthetic data only; none exist for these modules yet. |

Tests must use synthetic data and separately approved isolated storage. Snapshot/rollback/concurrency correctness requires actual PostgreSQL evidence. No new test counts, browser passes or screenshots are claimed by this documentation-only update.

## 10. Decisions still requiring institutional confirmation

| ID | Open decision before implementation/activation |
|---|---|
| P01 | Who is the appointed Chair per department, who grants/revokes authority, whether several/acting Chairs are allowed, and how self-requests/delegation are routed. Default deny until resolved. |
| P02 | Who confirms external commitments, what supplier attestation is required, and when an externally confirmed incoming revision must block generation/publication while reconciliation is pending. |
| P03 | Authoritative faculty/external-instructor/physical-room identities shared across colleges, resource visibility, cross-department locking and whether another department's approval is required for a shared change. |
| P04 | Required external fields and legitimate not-applicable resources, section-only confirmation policy, actual term/effective dates, holidays/date exceptions and unsupported day/grid handling. |
| P05 | Initial request field allowlist (proposed day/time/room), deadlines, selected proposal versus officially published schedule, reopened/locked-term policy, withdrawal and rejection/rebase/resubmission behavior. |
| P06 | Faculty transfers, swaps, co-teaching/cross-listing and multi-department changes: currently excluded, requiring a separate joint approval model if needed. |
| P07 | Institution-supplied CSV/Excel templates, sheets, encoding/date conventions, file limits, legacy XLS support, private upload retention and source confidentiality. |
| P08 | How to atomically reconcile late external confirmation with already selected schedules, who authorizes coordinated replacement/regeneration, and how users are informed of temporary review blockage. |
| P09 | Schedule retention/export/privacy policy, historical correction visibility, backup/restore owner, decision reasons, notifications and reliable post-commit delivery. |
| P10 | Reviewed deterministic adapter/validator boundaries that preserve legacy GA semantics and checkpoint compatibility; unsupported formats remain blocked rather than changing the engine implicitly. |

Confirmation of R-GEC/R-ADJ does not resolve P01-P10 or earlier institutional calendar/workload/room decisions. The next action is review of these decisions and proposed milestone boundaries, not a migration, data import or service restart.

## 11. Documentation change and verification record

| File | Actual change in this update |
|---|---|
| [phase-4c1-academic-data-contract.md](phase-4c1-academic-data-contract.md) | Added dated confirmed-requirement boundary and C14/C15 without deleting the historical design |
| [architecture/phase-4c1-relational-schema.md](architecture/phase-4c1-relational-schema.md) | Added dated future dictionary/ER extension and snapshot-context requirements; seven-table implementation untouched |
| `docs/phase-4c-confirmed-scheduling-workflows.md` | New inspection findings, three module designs, APIs/permissions, milestone/test proposals and open decisions |
| [Original contract snapshot](testing/phase-4c/design-history/2026-10-19/docs/phase-4c1-academic-data-contract.md) | New byte-identical archive of the pre-update document; preserves its original SHA-256 |
| [Original schema snapshot](testing/phase-4c/design-history/2026-10-19/docs/architecture/phase-4c1-relational-schema.md) | New byte-identical archive of the pre-update dictionary; preserves its original SHA-256 |
| [Requirements-update manifest](testing/phase-4c/phase-4c-confirmed-requirements-manifest.json) | New current/snapshot hashes, supersession mapping, static validation and preservation record |

Archive copies preserve the old Markdown bytes and their original relative-link context. They are provenance snapshots, not newly relocated, self-contained navigation sites; resolving their links requires the original repository layout. Earlier 4C.1/4C.2/4B manifests are not rewritten. A historical manifest's old path/hash resolves to the matching snapshot through the new manifest's explicit mapping, not to an assertion that today's extended document is byte-identical to the old one.

Verification is static documentation review only: current relative links/anchors, JSON, artifact/snapshot hashes, dictionary/ER names, seven unchanged model declarations, whitespace and protected-file/Git comparisons. The new manifest records exact counts/results. Of 418 pre-update files, only the two authorized design documents changed; original code, seven-table model/migration, all existing evidence, protected preference bytes and Git index remain unchanged. The pre-existing uncommitted implementation files and preference modification are retained.

Application/unit/PostgreSQL/browser tests: **NOT RUN for this documentation-only update**. No new screenshots, original testing timestamps, manual passes or automated browser evidence are claimed. The 4C.2 offline counts remain their original historical evidence and do not verify R-GEC/R-ADJ. No new schema, API, page, appointment, data import, notification, service operation, migration, staging, commit or push occurred. This design is ready for requirement/policy review with P01-P10 outstanding; implementation needs a separately approved bounded scope.
