# U3: evaluation views, faculty coverage, workload and academic authority

2026-11-02, Asia/Manila. **Safe frontend improvements implemented; persistent evaluation reset, preparation preferences and Chair designation are not activated.** Main remains at `f5262637acfb2d4d063cad1b0de80779a10bcba3`. Existing U1/U2 and unrelated local work are preserved. Read the exact inventory, hashes and replayable checks in [the U3 manifest](testing/dashboard-u3/manifest.json).

## Delivered behavior and boundaries

| Area | Status | Result |
|---|---|---|
| Saved Chromosomes default | IMPLEMENTED | Current Runs: 0; Current Best Fitness: —; Saved Chromosome: None. Historical penalty is absent from this view. |
| Historical Archive | IMPLEMENTED | Explicit `?view=archive` navigation retains original saved values, inspection and downloads. A real zero remains zero. Saved-baseline reuse remains disabled without verified compatibility. |
| Persistent Start Fresh Evaluation | BLOCKED | Disabled, explained control; no reset, deletion, namespace or pointer update occurs. |
| Faculty selector and empty results | IMPLEMENTED | Available metadata, recorded result analysis and assigned instructors are merged by existing faculty keys, naturally sorted, including zero-assignment members. Missing metadata has an explicit warning and retry. |
| Workload chart | IMPLEMENTED | Actual versus recorded target, zero, under/at/above target, exact values, keyboard access, bounded scrolling and responsive layout above the retained table. |
| Complete semester participation / minimum assignment | REQUIRES APPROVAL AND DATA | The selector is not an authoritative roster or proof that every faculty member participated in generation. No minimum-one-subject rule was introduced. |
| Preferred maximum preparations | PROPOSED | UI and versioned persistence/authority design below; no live control, API field, migration or scoring change. |
| Chair designation | PROPOSED / INSTITUTIONAL AUTHORITY BLOCKED | Technical account roles do not confer academic mandates. No designation, override or permission change was made. |

## Current evaluation and historical records

`ChromosomeViewer.tsx` now separates the current summary and archive instead of displaying the archive's large saved penalty immediately beneath the current empty message. Navigation changes only the URL. U1's fail-closed `resultPresentation.isVerifiedCurrent` remains unchanged: the existing API does not expose a trusted current engine/fitness-policy compatibility contract. Consequently zero is the count of **verified compatible classified records**, not a claim that the storage is empty. Newly saved results also cannot be classified as current yet. An error fetching saved status remains an error, rather than evidence of no history.

U1's saved-baseline gate and Generate Schedule default remain intact. A previous saved-baseline browser preference cannot implicitly select an incompatible record. Explicit file upload remains the existing separate workflow: the backend reconstructs assignments and recalculates baseline fitness (`ga_service.py`, baseline reconstruction), rather than trusting the uploaded fitness number. This does not establish current-evaluation membership or authorize institutional publication. No historical chromosome was uploaded or used for generation in U3.

**BLOCKED persistent reset design:** introduce a server-owned immutable evaluation identity bound to engine, fitness-policy and frozen-input provenance. Specify authorized creation, idempotency and current-evaluation selection; filter runs and compare saved bests only within a compatible evaluation. Review initial seed admission, atomic publication, checkpoint continuation and historical reads together. Existing `save_best_if_better` compares saved numbers without this evaluation contract. A frontend toggle, clearing browser storage, generating a new population or relabeling a timestamp cannot reset that storage. Do not rewrite legacy records or counterfeit compatibility. This requires a separately reviewed backend/persistence milestone before enabling Start Fresh Evaluation.

**Separate future deletion procedure — NOT EXECUTED OR AUTHORIZED BY U3:**

1. Identify one specific record, artifact type, canonical contained path, immutable identifier and raw SHA-256. A saved best (`backend/saved_chromosomes/best_chromosome.json`), uploaded baseline (`uploaded_baseline.json`) and run under `generation_snapshots/<validated run UUID>/` are different artifacts. Check linked snapshots, exports, sidecars, indexes, checkpoints and research-retention obligations. Do not treat a run directory as a single disposable file.
2. Present the exact deletion set and dependency consequences for separate explicit owner approval. Protected datasets, checkpoints and immutable approval/publication ledgers are excluded from an ordinary saved-record deletion. No automatic cascading or bulk reset.
3. In an approved implementation, pause only owned writers, reverify containment/identity/hash and authorization immediately before removal, and stop on any mismatch. Delete only specifically approved artifacts; do not automatically follow aliases or recursively remove unrelated records.
4. Record the approved reason, actor, time, removed hashes and references in an approved retention/audit mechanism; verify all remaining artifact hashes and truthful archive/current-state behavior. Releasing a saved pointer is distinct from deleting a published schedule. No deletion command, endpoint or database operation was executed here.

## Faculty coverage investigation

The previous selector already combined `getAllFaculty()` metadata and assignment faculty codes; it was not built solely from assigned rows. However, it did not include captured `gaData.faculty_analysis.faculty`, silently logged metadata failures and hid the selector for an empty schedule. Those gaps could hide a zero-assignment faculty member who appeared only in the recorded analysis.

The new pure `facultyCoverage` helper preserves existing UUID/code/display normalization, adds captured members, counts actual schedule rows without inventing assignments and excludes external metadata from the unassigned optimization-cohort list. Actual external assignments remain selectable. Numeric order is Faculty 0, 1, 2, 10. A selected member with zero rows sees **No assigned subjects**; a loaded empty schedule still retains the selector and coverage explanation. Search/day/section filters do not redefine whether the original result contained assignments. If no result is loaded at all, the existing no-result screen remains.

**Backend cohort limitation remains:** `metadata_service.list_faculty_metadata()` exposes `Functions.list_faculty`. In `Functions.py`, the normal faculty pool is constructed from `dct_fac_subj.keys()` derived from the legacy preference CSV, not from registered accounts or a verified semester roster. Account creation/binding does not add someone to that pool. A faculty member without a legacy preference record can therefore be absent from both generation and metadata. The frontend union mitigates display omissions; it does not repair the F1/F1.5 institutional cohort dependency. Current metadata and historical result membership are explicitly distinguished in the on-screen explanation. Workload chart membership stays limited to the selected report, so current metadata does not retrospectively alter historical totals.

Available adviser-supplied data is the IT prototype scope, not a verified complete semester IT roster or full CCS/IS deployment. Account `is_active` governs access, not teaching participation, leave or employment. Missing institutional participation data must not be inferred from login status, zero assignments or lack of preferences. U3 did not inspect or export individual institutional schedules to diagnose a particular faculty member.

| Possible cause of zero assignments | Evidence needed before concluding it applies |
|---|---|
| No eligible offering / specialization restriction | Complete authoritative eligibility graph and applicable qualification policy. |
| Too few offerings / shared eligibility bottleneck | Full offering set and capacity/matching analysis; offering count at least cohort size is necessary but insufficient. |
| Unavailable time / fixed conflicts | Current authoritative faculty, room, section and outside commitments on a common term/calendar. |
| Workload restriction / zero target | Verified target/allowance provenance and any independently authorized exception. |
| Inactive, nonteaching, leave or outside cohort | Explicit semester participation/exclusion record, independent of account activity. |
| Search did not find a covering solution | Reproducible run inputs, seed, bounded-search diagnostics and independent feasibility analysis. Search exhaustion is not proof of impossibility. |

**Recommendation: coverage as a reporting metric now.** Report full verified participant count when available, assigned/unassigned counts, eligibility and unknown/exclusion reasons. A later approved soft coverage objective may reward wider participation while retaining hard eligibility and availability; it needs versioned shared fitness dispatch and tradeoff validation against workload and preferences. A hard minimum-one-subject constraint can make feasible schedules impossible and needs an approved cohort, feasibility checks and explicit exceptions before introduction. Neither soft nor hard coverage guarantees balanced teaching units. No GA coverage constraint or objective was added.

## Workload visualization and scope

The application chart reads only the selected real report's `teaching_units` and `required_teaching_load`. Fictional observations exist only in tests. Teal bars show actual; gold outlined bars show target, on a common scale including the largest recorded actual or target. Bar width is display geometry, not normalized academic units. Exact raw numbers remain visible and in title/accessible labels. Zero has a labeled baseline marker; missing/invalid observations are **Not captured**, never coerced to zero or filled from current settings. Recorded status/value disagreement and values above 40 are warned about without clipping or silently legitimizing them. The above-ceiling test deliberately supplies a malformed fictional observation; it is not a valid GA result.

Rows are naturally sorted on copies; the original report and schedule data remain unchanged. Faculty/workload filters apply identically to chart and table. A bounded, keyboard-focusable chart list supports many faculty; the detailed table retains its horizontal scroll. A browser-found mobile header overflow was corrected by allowing the two analysis actions to wrap, preserving U2's document-owned page scrolling.

`Faculty.py` computes:

`non_teaching_load = admin_load + research_load + extension_load`

`required_teaching_load = max(0, 24 - non_teaching_load)`

Teaching above 30 triggers the existing warning; 40 is the existing hard ceiling. These fixed allowances reduce the expected teaching target under Option B; administrative/research/extension activities themselves are not scheduled. Source load fields and target aliases have distinct meanings; U3 did not reinterpret them or change the current workload scorer. Prior fairness counterexamples and experimental F2 policies are not solved or activated by a chart.

**REQUIRES ADVISER/INSTITUTIONAL CONFIRMATION:** [R1](thesis-r1-adviser-decision-package.md) records developer-reported direction supporting Option B, while the working thesis scope excludes non-teaching workloads. Clarify whether the exclusion concerns scheduling those activities or also using their allowances as target inputs. A strict teaching-only alternative needs an independently approved target source and new versioned scoring/input/reporting/checkpoint review; zeroing protected allowance data is not a solution. The approved manuscript remains outside the repository, so formal thesis alignment is UNVERIFIED. No academic equation, target, warning, ceiling or settings value was changed.

## Preferred maximum preparations — proposal only

Inspected `schemas/faculty_preference.py`, `models/faculty_preference.py`, the preference router/validation, frontend API/model/editor and U2 controls. There is no per-faculty maximum-preparation field. The production scorer (`FitnessFunction.py`, preparation accumulator and excess-preparation penalty) uses distinct normalized subject numbers (`strip().upper()`) per faculty and a global `settings.max_preparations`. Excess preparations receive the existing configured penalty and faculty priority multiplier. Multiple sections and lecture/laboratory rows with the same subject code count once; distinct codes count separately. Cross-listed aliases or pedagogically equivalent courses are not automatically merged.

**Proposed academic definition:** one approved canonical course/version in the effective term is one preparation across its sections, with lecture/laboratory combined only if that is the department's adopted definition. Confirm cross-listings, differently numbered components, co-teaching, substantially different syllabi and cancelled offerings. Until that definition and authoritative course mappings exist, do not infer equivalence from names.

**Proposed U2-style UI (not an active form):**

`Preferred maximum preparations: [No preference] [1] [2] [3] [4]`

Use a native labeled single-choice radio/segmented group or select with keyboard arrows, visible selected/focus states and a mobile wrapping layout. Help text: “Advisory preference, subject to authorized academic review. Eligibility, availability and teaching limits still apply.” Show saved versus unsaved state, validation errors, existing dirty/discard/save/reload behavior and reviewed override rationale. No preference is an explicit null advisory choice; it does not silently disable the existing global preparation term or transfer academic authority.

**Proposed versioned contract, requiring review before persistence:** faculty identity derived from the authenticated binding; authoritative academic year/term and scheduling context; definition/policy version; `preferred_max_preparations: null | 1 | 2 | 3 | 4`; revision/effective timestamps, source and advisory status. Validate the exact enum and scope, preserve unrelated preferences and require expected revision for edits. Do not silently append fields to existing DTOs or protected JSON. Approve a durable schema/storage plan, migration/compatibility policy and API version before implementation. If approved for scoring later, use the F2 shared versioned dispatch across initialization/operators/comparisons/best-ever/checkpoints/reports; define weights and feasibility behavior, never introduce a hidden reward or penalty.

**Proposed Chair exception contract:** an independently verified preparation-review capability, not inferred from the existing schedule-decision mandate. Bind faculty, term, course/context, preference revision, original/requested value, reason, actor, mandate/policy reference, time, expiry/revocation and immutable decision history. Require stale-version rejection, idempotency, separation/recusal, current-authority rechecks and revalidation after invalidating changes. An override cannot relax eligibility, room/section/faculty conflicts or maximum teaching limits. No preparation override, authority provider or live field was added.

## Department Chair designation and permissions

**Can the Administrator designate Chair privileges now? No.** The existing Accounts interface assigns technical `admin` or `faculty` roles. `identity_models.User`, auth DTOs and routes permit only those values. Authenticated users with independent Chair mandates can access the Chair workflow; there is no third database account-role value that an Admin can select to create academic authority.

| Question | Observed contract |
|---|---|
| Administrator role changes | Admin-protected create/update; faculty bindings validated; last active admin protected. Account changes revoke login sessions. |
| Audited designation history | Account timestamps and session revocation exist; no immutable Chair appointment/replacement/revocation ledger or designation UI was found. D12 decisions are a different audit trail. |
| Department scope | `chair_authority_service.Mandate` carries verified department IDs/labels; request scope binds faculty/subject/section and year/term to a department. |
| Term-scoped role assignment | Request department binding checks year/term; the mandate has no first-class effective-term appointment field or Admin-managed term designation workflow. |
| Expiry and revocation | Current ACTIVE independently verified mandate required; changed grant/scope is rejected on recheck. The at-most-300-second assertion lifetime is provider freshness, not necessarily the length of a Chair appointment. |
| Multiple Chairs | No global one-Chair-per-department uniqueness or approved acting/delegate/overlap policy is established. Provider capability does not establish institutional policy. |
| Approve or return | D12 approves/rejects eligible submitted faculty adjustment requests, scoped and versioned with self-decision protection and immutable history. There is no general return-for-revision action or general final-schedule approval workflow established by those endpoints. |
| Applying a decision | D12 approval reports `schedule_changed: false`. D13 requires a separate current `schedule_application` mandate, trusted publication context, current Chair decision and revision/conflict checks; it appends an immutable published version. |
| Production authority | Both institutional Chair and application provider factories return None. Admin/faculty roles, fictional tests and page access cannot replace genuine mandates. |

**PROPOSED designation workflow:** an authorized administrator selects an existing verified account, records stable department/effective year-term and independently validated appointment/issuer reference, then registers that mandate through an approved institutional service. Replacement/revocation requires authorized verified evidence, reason, immutable audit, expected version/idempotency and immediate capability/cache/session revalidation as applicable. No self-appointment or generic role dropdown can manufacture a mandate. Confirm who may register versus approve an appointment, delegation/acting dates, overlapping Chairs, recusal, term changes and retention with the institution.

Chair preference review, preparation exceptions, final academic schedule approval and return-for-revision each need explicitly scoped authority and state transitions. Do not assume D12 adjustment-decision authority grants all of them. Administrator operations and separate application/publication authority must preserve the Chair's academic decision boundary. U3 changes no Accounts interface, authentication, mandate, decision, application or database permission.

## Validation and evidence attribution

All counts below are freshly executed frontend checks, not backend authorization or PostgreSQL acceptance. Browser tests render the actual React application in isolated headless Edge (`Edg/156.0.4314.50`) with intercepted fictional HTTP responses. U3's own suite records GET requests only. Existing preference regressions use their isolated mock save; nothing is persisted to application storage or institutional data. Existing GA-monitoring tests reuse their retained test fixtures without accessing live academic data; U3 exports no individual institutional records.

| Check | Final result |
|---|---|
| U3 focused helpers/contracts | 15 passed |
| U1/U2 and relevant existing frontend contracts | 121 passed |
| U3 browser | 15 child scenarios + parent = 16 Node tests passed |
| U1 browser | 12 child scenarios + parent = 13 Node tests passed |
| U2 browser | 17 child scenarios + parent = 18 Node tests passed |
| Preference browser | 22 child scenarios + parent = 23 Node tests passed |
| GA monitoring browser | 51 child scenarios + parent = 52 Node tests passed |
| TypeScript / production bundle / focused ESLint | Passed; existing Vite mixed-import and large-chunk warnings retained |
| Backend/GA execution, database/authority acceptance | Not run; backend/GA/application data bytes preserved |

The first U3 browser attempt passed 13 child scenarios and failed the mobile page-overflow assertion; the parent also failed. The header wrapping correction passed the full rerun. The first GA-browser attempt passed 50 Node tests and failed the saved-candidate navigation child plus parent because the test still expected archive actions on the default page. Only that navigation was updated to explicit archive; all scoring-request and loaded-result assertions remain. The full rerun passed. Failed command records and the first attempt's three genuine screenshots are retained, not replaced with success evidence.

Final genuine captures (fictional data; no backend scheduling/authority claims):

- [Current evaluation](testing/dashboard-u3/20261102T140919507156+0800-browser/U3-B01-current-evaluation.png)
- [Unassigned faculty](testing/dashboard-u3/20261102T140919507156+0800-browser/U3-B06-unassigned-faculty.png)
- [Desktop workload and retained table](testing/dashboard-u3/20261102T140919507156+0800-browser/U3-B09-workload-comparison.png)
- [Mobile workload](testing/dashboard-u3/20261102T140919507156+0800-browser/U3-B14-mobile-workload.png)

The manifest records actual timestamps, commands, outcomes, all raw artifact hashes, PNG metadata checks, visual privacy review and baseline comparisons. A screenshot/hash establishes an observed fixture rendering, not institutional correctness or authority.

## Exact implementation scope and preservation

Existing files changed relative to the U3 entry state:

- `frontend/src/pages/admin/ChromosomeViewer.tsx` — default/archive separation and explained unavailable reset.
- `frontend/src/pages/admin/ScheduleView.tsx` — coverage union, empty-member selection and metadata retry.
- `frontend/src/pages/admin/FitnessAnalysis.tsx` — chart, natural ordering and mobile action wrapping.
- `frontend/tests/resultPresentation.browser.test.mjs` — two U1 scenarios explicitly enter the archive; assertions remain.
- `frontend/tests/gaMonitoring.browser.test.mjs` — one existing loaded-candidate scenario explicitly enters the archive.

New frontend files: `src/services/facultyCoverage.ts`, `src/services/workloadPresentation.ts`, `src/components/ga/WorkloadChart.tsx`, `src/components/ga/workloadChart.css`, `tests/evaluationCoverage.test.mjs`, `tests/evaluationCoverage.fixtures.mjs` and `tests/evaluationCoverage.browser.test.mjs` (all under `frontend/`). New report: this document. New tooling/evidence: `docs/testing/dashboard-u3/`, including baseline, runner, auditor, manifest and every timestamped command/result/PNG named in the exact manifest inventory. The baseline already contained the U1 browser file as an untracked user artifact; it is an existing entry-state file, not newly created by U3.

Of 2,857 baselined paths, five explicitly authorized frontend/test paths changed and **2,852 remain byte-identical**. All 23 academic paths, both protected local preference/settings modifications, backend, original GA/math/RNG, migrations, retained checkpoints/schedules, existing research evidence, U1/U2 manifests and Git index remain unchanged. U2's 84 hashed artifacts remain intact. U1 source hashes for intentionally extended pages/test no longer match the historical U1 source snapshots; those four exact overlaps are explicit exemptions, not altered historical evidence. All other U1 hashed artifacts match. Full tracked status also contains pre-existing U1/U2 and protected modifications; none is discarded or staged. The U3 manifest distinguishes its exact inventory from the larger pre-existing working tree.

No reset, deletion, migration, database connection, generation, scoring change, preparation limit, assignment fabrication, institutional role grant, new dependency, staging, commit or push occurred. Existing D15 evidence/database are untouched; no claim is made about independently inspecting live database state.

## Reproduce from the repository root in PowerShell

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u3/run_checks.py focused
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u3/run_checks.py regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u3/run_checks.py build
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u3/run_checks.py bundle
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u3/run_checks.py lint
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u3/run_checks.py browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u3/run_checks.py u1-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u3/run_checks.py u2-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u3/run_checks.py preferences-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u3/run_checks.py ga-browser
```

Each test execution creates a new evidence directory; it never overwrites a retained attempt. Browser checks require installed Edge and a rendering-capable session. To replay the finalized hash/privacy/preservation audit without new tests:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u3/audit_evidence.py
```

The finalized manifest is a frozen inventory. Later reruns produce additional artifacts and require a separately reviewed addendum; they must not silently rewrite this record.

## Decisions and next work

1. Approve the server-owned evaluation/provenance design before enabling persistent Start Fresh or classifying saved results as current. No historical deletion is needed to implement a new evaluation namespace.
2. Obtain authoritative IT semester participation, eligibility, workload and availability records before roster-first integration or an academic coverage guarantee; retain reporting without forcing assignments meanwhile.
3. Adviser confirms Option B versus teaching-only thesis wording; institutional owner confirms allowance/target sources and exceptions. Do not change settings to settle a documentation conflict.
4. Department/adviser approve preparation definition, choices and advisory-versus-scored semantics; approve versioned persistence/fitness integration separately.
5. Institutional issuer approves appointment lifecycle, scope, delegation and academic capabilities before Admin-managed Chair designation. Production institutional activation remains BLOCKED.

U3 stops at these boundaries. No next milestone, academic authority or destructive operation is automatically authorized.
