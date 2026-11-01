# F4A: availability and reset consistency qualification

2026-11-02, Asia/Manila. **Qualification complete; no production reset or availability policy changed.** Ordinary faculty/room occupancy flags reopen under full reset. V2 removed-slot commitments and section fixed-calendar restrictions survive their supported restart paths. These are distinct representations, not evidence that every ordinary closure is durably enforced. Institutional integration remains **BLOCKED** and formal adviser-approved thesis alignment remains **UNVERIFIED**.

## Inspection, scope and baseline

Inspected the [functional audit](thesis-functional-correctness-audit.md), relevant D9-D14 implementation/acceptance sections, current faculty/room/section/TimeBlock models, assignment/reset/rollback helpers, V1 construction, V2 constraint reduction/admission/resume, original reconstruction/publication validation, D11 request and D12/D13 decision/application boundaries, version projections and dashboard controls. Reviewed F1.5 cross-department findings and the completed F3C baseline. No AGENTS.md was found.

HEAD remains `1199838c7532c03635ec4fc09f2cadd94bed4f1b`, branch `main`, index unchanged. Before new source, the entry check verified all 15 F3C artifact hashes and established a **2,677-path** baseline. This includes both existing protected local modifications, all 23 academic files, prior untracked work, original GA/migrations/checkpoints/schedules and historical evidence. No institutional records or protected preference/settings values were parsed for these new tests. GA imports use the existing schema-only bootstrap and fictional scoring context.

D9-D14 reports are historical: their old statements about unverified PostgreSQL acceptance do not supersede the later D15 disposable **17 Phase4C + 10 workflow** passes. D15's database and evidence are preserved; F4A performs **no database connection or operation**, including SQLite. Actual authentication/transactions, persisted Chair decisions and database rollback are therefore historical evidence, not fresh F4A claims.

## Availability input inventory

The complete machine-readable source/scope/storage/version/reset/effect/authorization inventory is `availability-inventory.json` under the evidence directory. It includes ten input/control classes; `source-inspection.json` binds twenty reviewed source paths to their actual bytes.

| ID / input | Source and storage | Version/scope and reset effect | Enforcement and authorization boundary |
|---|---|---|---|
| A01 faculty occupancy | Faculty TimeBlock availability and assignment graph in memory; run graph/checkpoint may serialize it | Ordinary boolean has no independent term/issuer/closure revision. Full reset opens retained slots and clears assignment/load metadata | Original assignment checks full free coverage before reset. Engine occupancy is not an administrative closure policy |
| A02 room occupancy | Room-owned TimeBlocks and reservations | Room/full reset and rollback release used blocks. Room identity retained | Room selection/reservation checks whole interval. No independent closure-grant workflow |
| A03 ordinary closures | A false faculty/room availability flag; a dynamic fixed flag is only a fictional control | Ordinary retained slots reopen even with a test `fixed_schedule=True`. Missing/removed slots are not recreated | Can block a direct assignment before reset; cannot serve alone as a durable closure contract. Actual persistence/issuer policy unresolved |
| A04 fixed sections | Existing consolidated CSV loader, Section calendar, fixed_schedule/fixed_course metadata | Input fingerprints bind file/graph; no independently approved term lifecycle in the CSV. Section calendar survives full reset | Existing section overlap/reconstruction checks; source identity and effective term still require institutional qualification |
| A05 confirmed external meetings | D9 immutable revisions/events, current heads, D8 evidence and independent confirmation capability; D10 snapshot and V2 envelope | Exact year/term/window, mappings, source row/hash and revision/evidence digests. V2 removes faculty/room slots; marks section fixed blocks | Initial/descendant/best/resume/publication admission plus fresh current-head/trust checks. Production providers remain unavailable |
| A06 adjustment/publication windows | Guarded D11 ReviewSchedule.windows, meetings and current commitments | Exact schedule revision/term/constraint digest; windows supplied by current provider. Request/decision/application does not run GA reset | Missing coverage blocks full application validation; faculty owner, scoped Chair decision and independent application capability remain separate |
| A07 preferences | Optional authenticated preferences, preferred flags and frozen scoring inputs; protected values not inspected | Preferred is separate from available; preference reset clears preferred marks, not a general closure authority | Soft wishes do not establish faculty absence, room downtime or permission to violate a hard commitment |
| A08 term/department restrictions | Academic foundation year/term/calendar lifecycle and trusted V2 catalog/provider | Stable term/department/resource mappings and effective revision required. Ordinary weekly grids do not attest term participation | Calendar containment and scope checks; no implicit rollover or department inference |
| A09 preassignment | Existing instructor/room declarations in protected inputs and Subject metadata | Input identity retained; declaration has no day/start/end meeting-time fields | Instructor/room restriction is not a timed closure or external commitment |
| A10 dashboard controls | RoomAssignments/FacultyManagement viewers; ExternalSchedules preview/ledger; constrained generation; Chair/application pages | UI view/filter resets do not delete ledger restrictions or choose an expiry policy | No dedicated institutional faculty/room closure editor identified. Frontend/account roles cannot grant server authority |

The academic foundation supports scoped calendar records, not a deployed general room/faculty closure management service. No authoritative list of real absences, room maintenance or IS meetings is extracted or fabricated. Constructor-generated available weekly blocks are defaults, not proof that all those times are institutionally available.

## Current reset and lifecycle semantics

Relevant original code: [room/full reset](../backend/genetic_algorithm/utils/Functions.py#L1254), [section checks](../backend/genetic_algorithm/utils/Functions.py#L895), [V2 reduction](../backend/services/ga_v2_constraints.py#L188), [V2 construction](../backend/services/ga_v2_engine.py#L49), [full application validator](../backend/services/published_schedule_source.py#L55).

| Event | Observed or source-established behavior | Limitation / required interpretation |
|---|---|---|
| Scheduling begins | V1 population constructors and V2 construct use original assignment/reset helpers on copied templates. Direct assignment honors unavailable flags; construction restart invokes full reset | A copied ordinary closure flag can be reopened before searching. No approved general durable-closure semantics exists |
| Candidate/run reset | All retained room/faculty blocks become available; metadata and loads clear. Section fixed flags remain. Slots absent from calendars stay absent | Synthetic fixed flags on faculty/room blocks are ignored by those reset loops. Do not generalize the Section contract to other resource models |
| New run | Rebuild detached run-local calendars from current templates and the current verified snapshot. The new test performs two bounded original constructions and two fresh reductions with three resets each | Source templates stay unchanged, but mutable occupancy is not a persisted administrative restriction. Rollover requires a term/source decision; do not reuse stale snapshots |
| Checkpoint continuation | Current V1 strict engine/input/graph validation remains. V2 checks engine/input/catalog/term/snapshot, frozen scoring calendars, full population/best and fresh trust; reconstructs reduced templates before admission | A checkpoint is not permission to bypass current trust or silently adopt changed restrictions. Six historical incompatible checkpoints remain byte-identical with their accepted old rejection limitation |
| Confirmed GEC revision | D9 new proposal does not replace the current confirmation until authorized confirmation; supersession/revocation changes the current set. V2 stale digest/head comparison blocks instead of substituting a new set | Fresh source/trust required. Confirmed does not mean permanently irrevocable or automatically active in every run |
| Schedule version revised / Chair application | D13 changes one approved meeting into a new immutable published version after full validation, exact revision checks and independent authority. Original GA result is not mutated; no GA reset or automatic regeneration occurs | F4A executes full validation and the approval-prerequisite gate without a DB. Actual transaction/head updates and authenticated application are not rerun |

Rollback of a temporary Subject assignment releases its faculty and room reservations and updates teaching load. That is appropriate for transient occupancy. It must not be confused with revoking a separately authorized closure. The current TimeBlock boolean does not encode issuer, lifecycle, expiry or cause, so merely inspecting it cannot establish whether an unavailable slot was supposed to be temporary or durable.

A previously approved/published CCS schedule is also not automatically the next run's fixed-commitment set. V1 copies its existing runtime templates; V2 receives a server-owned Deployment and current D9 snapshot. No inspected generation path automatically converts every D13 published meeting into a new hard reservation. A requested saved/uploaded seed is separately validated, not equivalent to permanently freezing every meeting. Whether some published meetings should be frozen across a new generation is an additional explicit scope/authority decision, not behavior to infer from approval alone.

### Publication availability provenance boundary

`schedule_version_store.base_content` stores meetings, term, origin, revision and constraint digest. `current()` overlays retained meetings/revision onto the current guarded provider context; it does **not independently persist a complete historical availability-window revision**. `published_schedule_views` checks source/current publication revision, and full application validation rechecks the provider's current windows.

This is not a claim that current application validation ignores availability: the fresh tests prove it rejects missing coverage and fixed conflicts. It is a qualification gap for reproducing exactly which general closure/windows policy applied to an older approval/version. A provider must maintain coherent version/authority guards; an approved future contract should bind availability revision/term/digest and historical evidence explicitly. Do not assume the existing GEC digest covers every general faculty/room closure, or invent a new storage schema now.

## Fictional hard-constraint and reset evidence

Twenty-one new cases run original code using fictional D10 subjects, faculty, sections and rooms. None changes a production function, substitutes a fitness equation or writes an application GA store. All sampled global RNG state is restored after each test. Characterizations of reopening are expected findings, **not passes for a durable institutional-closure requirement**.

| Test family | Actual result |
|---|---|
| Faculty/room boolean flags, with/without synthetic fixed flag | Four controls reject the direct assignment before reset; full reset reopens the retained slot and the same direct assignment succeeds |
| Section fixed calendar | Closed section interval remains closed after three full resets and section-availability queries reject it |
| Missing faculty/room slots | Missing slot fails full-coverage checks before/after repeated resets; no implicit creation or open fallback |
| Temporary assignment rollback | Faculty/room occupancy released and teaching load returned to zero |
| Repeated construction | Two bounded original constructions preserve source template bytes/graph; source inspection and reset controls establish the restart behavior |
| V2 removed faculty/room reservations | Two fresh reductions per resource and three resets per run never recreate committed intervals; original templates remain unchanged |
| Revised commitment identity | Original pinned snapshot rejected by the actual D10 fictional authority boundary after head version changes; no implicit replacement |
| Full application availability | Original complete detached schedule validates; removing faculty, room or section windows causes BLOCKED with the corresponding MISSING availability finding |
| Fixed commitment at application | Proposed overlapping meeting blocked; original meetings unchanged. Valid original ends exactly at commitment start, preserving half-open adjacency |
| Stale schedule and wrong term | Original request validator rejects both with 409; no rebase or record write |
| Chair prerequisite | Actual application eligibility function rejects draft/no-decision/rejected-decision controls. Decision lookup is a local fake, **not authentication or durable authorization evidence** |

The unchanged 30-case D10 engine suite adds actual original crossover/mutation/initial admission, faculty/room/section conflicts, adjacent boundaries, duplicate/internal conflicting commitments, invalid/off-grid times, unsupported/missing mappings, reset persistence, bounded failure, actual current V2 checkpoint creation/resume including a fresh Python child, corruption/input/profile tampering and authority loss before atomic write. These checks use the existing fictional authority fixture; they do not install institutional authority or query the ledger database.

Current V1's four continuation cases run in an owned fictional source-identical mirror: 202 backend source files, three actual newly created owned checkpoint archives, unchanged engine fingerprint and verified fictional input fingerprint. Actual creation/load/continuation occurs; historical archives are never opened for rewriting or migrated. Old F2 releases remain hash/anchor verified rather than rerunning all prior research campaigns.

## Persistence policy alternatives — all unapproved

These can form a typed policy together; they are not necessarily mutually exclusive. No policy is selected or activated.

| Alternative | Expected behavior | Required data/authority | Scheduling and compatibility implications |
|---|---|---|---|
| P-A temporary restrictions expire after a run | Run-scoped restrictions expire only at a declared boundary; ordinary assignment occupancy may clear on candidate restart | Kind/cause, run ID, owner, interval and declared expiry; distinguish transient reservation from administrative run restriction | Current reset represents occupancy, not every possible temporary restriction. If run-wide closures must survive candidate restarts, a new qualified representation is needed; do not change reset semantics silently |
| P-B term closures persist until removed | Approved closure remains across new runs/resets until authorized removal or explicit expiry | Exact resource ID, term/effective dates, recurrence/exceptions, issuer mandate, revision, reason, revocation | Reapply the pinned set to every detached construction and validation boundary. Missing information fails visibly. New input/policy identity may reject incompatible continuation |
| P-C approved commitments persist across resets | Current commitments remain hard while applicable; revision/revocation needs fresh checks | D9/D8-style provenance for genuine meetings, current heads and independent authority; not borrowed Chair status | Existing V2 mechanism supports confirmed meetings. Generic room maintenance/faculty leave is not automatically that same contract; no fake subject/section should be invented to fit it |
| P-D versioned term restriction sets | Every run/approval/result binds a coherent immutable snapshot and lifecycle, with historical retention | Kind/resource/term/revision/hash, validity, capability and complete external scope; availability provenance in evaluation/publication | Best auditable design direction **recommended but unapproved**. Requires explicit release/input/checkpoint compatibility and lifecycle tests; never spoof legacy fingerprints or rewrite old artifacts |

V2 commitments require real original row/head provenance and nonempty affected sections under their existing validation. Do not disguise a room-only closure as a fabricated GEC meeting/Subject gene to reuse that path. A future generic availability adapter needs its own approved semantics and resource applicability contract while retaining original hard validation.

## IT and cross-department dependencies

IT is the prototype/evaluation cohort. F1.5's workbook/resource cooccurrences are **historical dependency indicators**, not confirmed IS meetings or an authoritative IS roster. No real institutional rows are imported into these new artifacts.

External commitments affecting an IT faculty member, shared physical room or IT student section require one stable identity per shared person/room, exact term/effective window/timezone, day/start/end/recurrence/exceptions, source revision/row/hash, supplying owner, confirmation scope, expiry/revocation and an explicit completeness statement. Department-specific aliases cannot create two copies that evade a conflict check. Verify mappings privately; do not infer institutional identity from a title, course prefix or tentative workbook row.

General room/faculty closures require a separately identified issuing authority; a Chair schedule decision or GEC confirmer mandate is not automatically a campus-room/leave-management capability. Existing current V2 reservations can protect genuine verified external meetings with required mappings. They do not supply missing source data, official term calendars, generic closure policy, full CCS coverage or external teaching-credit accounting. All genuine institutional providers remain blocked/unconfigured.

## Decisions required before F4B corrections

1. Which unavailable states represent transient occupancy, run-wide restrictions, term closures or confirmed meetings? What expires on candidate restart, run end, term end or revocation?
2. Who issues, verifies, edits/removes and delegates each resource restriction, within what department/resource scope? Do not infer authority from account/Chair labels.
3. Is missing availability unknown/blocked or explicitly not applicable for each resource? What constitutes an attested complete calendar rather than a constructor default?
4. How are recurrence, holidays, partial terms, exceptions, adjacency and simultaneous/conflicting restrictions represented and reconciled? Unknown conflicts cannot be silently omitted.
5. Which shared outside commitments are complete/current, and how are IT versus wider CCS claims bounded?
6. Must availability/window revisions be immutably retained with Chair approvals and published versions for historical reproduction? How should changed closures invalidate pending approvals or constrain existing schedules?
7. Which new engine/input/policy release and checkpoint continuation rules are approved? Preserve legacy behavior, reject incompatibility explicitly, never reinterpret old scores/snapshots.
8. What audit retention, private evidence custody and authorized correction/revocation process applies?

Named institutional role mandates, actual complete data and approved expiry/persistence rules are unavailable. That blocks implementation of a general durable closure correction, not this qualification. No production fix is attempted or disguised as an input repair.

## Fresh validation, evidence and limitations

| Selection | Fresh result | Meaning |
|---|---:|---|
| New characterization/application core + existing D10 | **51 passed**, 0 failed/errors/skipped | 21 new cases plus 30 original V2 cases; no database operations |
| Current supported V1 mirror | **4 passed** | Actual original-operator checkpoint creation/load/continuation, 202 byte-identical sources, three owned archives |
| **Unique Python total** | **55 passed** | Count each final case once |
| Frontend Node contracts | **42 passed**, 0 failed/skipped | Constrained-GA, Chair and application DTOs; no rendered browser/real HTTP acceptance |

The backend worker reports one existing `PytestAssertRewriteWarning` for already-imported anyio after schema bootstrap. It is retained; no dependency is changed or warning hidden. No new attempt failed or timed out. Useful failures from earlier milestones remain in historical evidence and are never deleted. Fresh original-code observations are in the backend `observations.jsonl`; command records preserve exact command/cwd/timestamps, bounded runtime, exit code, source hashes and sanitized output.

Database-backed Chair authorization/transactions, persisted version/history application, real browser scenarios and institutional sources are **NOT freshly tested**, because this milestone prohibits database operations and adds no UI/provider. D13-D16/D15 successful fictional/database evidence is reviewed history, not extra fresh passes. No production build/lint is claimed. No actual institutional closure correctness, full CCS conflict freedom, performance improvement or approved thesis compliance follows from these fictional tests.

All **16 new files** are this report and `docs/testing/availability-f4a/`: **four Python, nine JSON, two JSONL and one Markdown**. The [manifest](testing/availability-f4a/manifest.json) lists the exact inventory and **15 raw artifact hashes**, excluding itself: new test, guarded runner, V1 mirror entry and audit; availability/source inventories, preservation/entry records and timestamped command/outcome/progress/observation evidence. Existing files modified by F4A: **zero**.

Final replay verifies all **2,677** baseline paths, **23** academic paths, **1,276** historical artifact entries, original engine fingerprints, existing experimental release anchors, retained checkpoints/schedules/migrations and HEAD/index/staged state. Both owner modifications to protected preferences/settings remain byte-identical, unstaged and uncommitted; neither content is printed or parsed. Privacy checks compare private registry labels only in memory and scan new artifacts for credentials, complete/truncated encoded tokens/receipts, keys, URLs and sensitive output. No institutional profile or row is archived. Git and new-file whitespace checks are non-mutating.

## Reproduction and stop

Integrity-only replay, without GA/database execution:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/availability-f4a/audit_evidence.py --verify
```

For separately reviewed fresh evidence (creates new timestamp directories, never overwrites the manifest or old artifacts):

```powershell
.\.venv\Scripts\python.exe -B docs/testing/availability-f4a/run_checks.py backend
.\.venv\Scripts\python.exe -B docs/testing/availability-f4a/verify_v1.py
.\.venv\Scripts\python.exe -B docs/testing/availability-f4a/run_checks.py frontend
```

Use the existing Python environment and Node installation; no credentials, database setup or new dependency is required. Fresh evidence needs its own reviewed addendum/inventory. Preserve old observations and the baseline. Workers deny database/network operations, schema-bootstrap fictional inputs and keep generated checkpoint storage in owned temporary directories, away from all existing stores.

**GO for separately authorized F4B policy/contract design or further isolated qualification. NO-GO for production reset/closure changes until persistence, authority and compatibility decisions are approved.** Recommended next step is to approve a typed availability lifecycle and provenance contract, especially general term closures versus occupancy and historical window revision retention. Then separately authorize the smallest adapter/validation change with explicit release compatibility and tests. No automatic F4B, schema/provider implementation, PostgreSQL operation, install, stage, commit or push occurs.
