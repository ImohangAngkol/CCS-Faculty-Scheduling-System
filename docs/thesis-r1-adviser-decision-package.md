# R1: adviser and department decision package

2026-11-02, Asia/Manila. **Ready for policy review; not yet ready for institutional thesis validation or production activation.** This package consolidates **32 decision items** across eight areas. Repeated questions from earlier reports appear once here, with detailed alternatives, consequences, evidence and implementation gates in the [technical register](thesis-r1-implementation-readiness.md). The [institutional checklist](thesis-r1-institutional-data-checklist.md) specifies what must be supplied privately.

The working research goal is a Genetic Algorithm-Based Faculty Scheduling Decision-Support System for MSU-IIT CCS. Available prototype data is user-reported IT data; it is not a complete verified CCS or semester IT roster. No IS faculty are invented. The formal approved manuscript is outside the repository, so **adviser-approved thesis alignment remains UNVERIFIED**. Institutional activation remains **BLOCKED**. No policy is marked institutionally approved by R1.

## What already exists and what remains undecided

The application has tested fictional scheduling, preference, request, Chair-decision and controlled-application workflows. Disposable PostgreSQL acceptance passed earlier. These establish technical behavior within their fixtures, not genuine mandates, complete institutional inputs or improved real scheduling quality.

Three distinctions require explicit review:

- **Participation is not preference submission.** The current legacy faculty list derives from preference records. The test-only roster-first adapter has not been connected to an approved semester roster.
- **Teaching targets are not scheduled non-teaching activities.** Current Option B subtracts fixed administrative, research and extension allowances from expected teaching units; it does not timetable those activities. The manuscript must clarify whether those inputs fit its stated scope exclusion.
- **A sound timetable is not proof of fair or preferred allocation.** The original score can favor a concentrated teaching allocation. Specialization is descriptive in production. Institutional availability persistence, formal metrics and an approved historical comparison remain unresolved.

Developer direction already recorded: roster-first participation is user-reported approved; Option B and fairness relative to individual teaching targets are user-reported adviser/department requirements; the developer selected zero-target admission Option A. These statements are retained, **not treated as reviewed institutional approval documents**. Option A means zero teaching is allowed at target zero, while positive teaching needs valid explicit authorization, preserves the original target and cannot override eligibility or other hard limits. The actual issuer/workflow and exceptional scoring mathematics remain unresolved.

## Decisions for review

All items below await the indicated evidence or formal scope choice. Selecting a supported, narrower scope can resolve a conditional item without adding a feature. Existing verified hard constraints are not offered for relaxation.

### A. Faculty cohort and identities — 4 decisions

| ID | Decision requested |
|---|---|
| R1-A01 | Identify the official IT semester cohort, participants/exclusions and source owner. Confirm IT-only evaluation and outside dependencies without claiming full CCS coverage. |
| R1-A02 | Approve stable identity reconciliation and distinguish account access, employment, semester participation, administrative priority and teaching eligibility. |
| R1-A03 | Confirm the complete term offering, section, room and academic-calendar source, including required meeting patterns and capacity/enrollment applicability. |
| R1-A04 | Identify who issues course eligibility and how missing eligibility or academically justified exceptions are reviewed. No specialization or preference automatically grants permission. |

### B. Teaching workload and allowances — 5 decisions

| ID | Decision requested |
|---|---|
| R1-B01 | Reconcile Option B fixed allowance inputs with the manuscript's scope, or explicitly authorize a different teaching-only target model. |
| R1-B02 | Confirm target, warning and maximum-load rules and which source/configuration controls them. Current software uses base 24, warning above 30 and hard maximum 40 teaching units. |
| R1-B03 | Approve allowance evidence, units, fractional/missing/invalid-value handling and the authoritative workload revision. Unknown allowances must not silently become approved zero allowances. |
| R1-B04 | Define how teaching outside the optimized IT offerings counts toward an IT faculty member's target and maximum, without double counting. |
| R1-B05 | Establish zero-target exception authority, scope, expiry and audit, and approve a defined scoring treatment for any authorized positive assignment. |

### C. Workload fairness — 4 decisions

| ID | Decision requested |
|---|---|
| R1-C01 | Confirm the independent meaning of fair target-relative teaching distribution, including unequal targets, shortages, eligibility-forced imbalance and zero assignments. |
| R1-C02 | Decide how workload, overload, specialization and preferences compete: separate reporting, a priority order or explicitly calibrated weights. |
| R1-C03 | Approve deterministic numeric representation and display rules for a selected new scoring policy; rounded displays must not decide rankings. |
| R1-C04 | Approve the scope of any new scoring release and supported continuation policy, preserving existing engines and historical artifacts. |

### D. Faculty specialization — 4 decisions

| ID | Decision requested |
|---|---|
| R1-D01 | Define acceptable specialization evidence, the verifier and correction/revocation procedure. Past teaching or preferences alone do not establish verified expertise. |
| R1-D02 | Approve the subject-domain taxonomy, primary/secondary meaning, multiple-domain interpretation and explicit equivalences. |
| R1-D03 | Choose the alignment measurement and its role: descriptive, tie-break or optimization; decide any domain/offering weights separately. |
| R1-D04 | Choose treatment of incomplete, contradictory or expired specialization data, including when comparisons must stop for verification. |

### E. Faculty preferences — 2 decisions

| ID | Decision requested |
|---|---|
| R1-E01 | Confirm term applicability, revision and carry-forward of submissions, while distinguishing absent, empty and disabled preferences. |
| R1-E02 | Confirm the meaning of rankings/importance and who controls administrative priority; keep wishes separate from hard availability and qualifications. |

### F. Availability and persistence — 4 decisions

| ID | Decision requested |
|---|---|
| R1-F01 | Classify occupancy, run-wide restrictions, term closures and fixed commitments; define expiry at reset, pause, run end and new term. |
| R1-F02 | Name faculty/room restriction owners and approvers/revokers; define missing information, recurrence, exceptions and conflicting assertions. |
| R1-F03 | Approve immutable availability history and rules for invalidating checkpoints or pending approvals after a relevant change. |
| R1-F04 | Verify the complete external/shared-resource commitment set and exact identities affecting IT. Do not infer confirmed IS schedules from tentative records. |

### G. Approval and administrative authority — 4 decisions

| ID | Decision requested |
|---|---|
| R1-G01 | Establish actual scoped mandates for data verification, GEC confirmation, Chair decisions, application and exceptions. Account role alone is insufficient. |
| R1-G02 | Define the initial authoritative schedule approval/publication and academic-input activation process; a GA proposal or printout is not official publication. |
| R1-G03 | Confirm correction, withdrawal, rejection, re-request, revocation and version-history rules, including whether an appeal/replacement-decision workflow is needed. |
| R1-G04 | Approve private data access, permitted research use, retention, deidentification and evidence custody. |

### H. Thesis evaluation methodology — 5 decisions

| ID | Decision requested |
|---|---|
| R1-H01 | Supply the approved manuscript/objectives, confirm DSRM activities and reconcile scope and actual algorithm claims. |
| R1-H02 | Approve metrics, denominators, unknown handling and acceptance thresholds before confirmatory testing. |
| R1-H03 | Identify an approved historical IT comparator and determine whether term, population, demand and available preferences are comparable. |
| R1-H04 | Preregister seeds, budgets, repetitions, stopping/search-space claims, timing conditions and failed-run reporting. |
| R1-H05 | Approve the demonstration and stakeholder-evaluation protocol, including who reviews results and what evidence supports usefulness. |

## Proposed evaluation, subject to approval

Use one frozen, verified IT term/cohort/offering set with the same confirmed outside commitments for each comparison. Report independent schedule-quality measures rather than treating the optimizer's total penalty as the research outcome:

- Faculty, room and section conflict counts; accepted schedules must satisfy all hard constraints.
- Full-cohort teaching targets, actual loads, shortages/excess and zero assignments, plus an approved independent fairness measure.
- Verified specialization alignment, subject-domain coverage and unknown-data coverage together.
- Subject/day/time preference matches over applicable submissions; not a claim of human satisfaction.
- Missing/duplicate offering-components and incomplete offerings against the complete required set.
- Uninstrumented generation time and failure/exhaustion rates over **all** preregistered attempts.
- A separately approved historical IT schedule, evaluated with the same definitions only where the scopes genuinely match.

Fictional illustration: one known aligned assignment and one unknown assignment is not proof of 100% whole-schedule alignment. It is 100% among the assessable half, with 50% data coverage and overall binary bounds of 50–100%. A historical schedule without archived preferences cannot support a preference-improvement claim. The detailed proposed formulas, comparisons and exclusions appear in the [implementation/evaluation plan](thesis-r1-implementation-readiness.md).

## Requested approval sequence and decision record

1. Adviser and institutional owners confirm the manuscript scope, IT population/term and who can approve each kind of fact or action.
2. Owners reconcile and version roster, workload, eligibility, offerings, specialization, preferences and shared-resource availability; authorize private research use.
3. Adviser and relevant policy owners approve fairness/alignment/unknown conventions, objective priorities, limits and any exception treatment. Record unresolved choices rather than supplying convenient defaults.
4. Approve the evaluation protocol and historical comparator before confirmatory data collection. Technical maintainers then qualify the corresponding versioned implementation under separate authorization.
5. Run isolated acceptance, approved real-data evaluation and scoped stakeholder review. Institutional activation remains a separate decision.

For each R1 ID, record the chosen alternative, rationale, named approver and verified mandate, decision date/reference, applicable term/scope, effective revision and evidence location, conditions and review/revocation date. **No signature or approval is supplied by this package.** Adviser endorsement of a research method does not itself grant room, employment, workload-exception or publication authority.

R1 adds only three Markdown documents. It changes no production functionality, policy setting, academic source, checkpoint or database and makes no fresh GA-quality claim. Preservation details and the source-to-decision crosswalk are in the technical checklist.
