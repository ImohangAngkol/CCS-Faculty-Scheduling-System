# Thesis objectives and functional correctness audit

2026-10-28, Asia/Manila. Source HEAD `1423812e13a5791a550c893ef6b17bfef4b4ebfb`. Evidence gathering only; no production implementation or performance integration.

**Conclusion: the system partially fulfills the supplied working research requirements. Formal alignment with adviser-approved objectives and methodology is UNVERIFIED.** Hard-constraint and decision-support mechanisms have substantial fictional functional evidence. Faculty-roster coverage, operational specialization matching, workload equity, workload scope and a complete thesis-quality evaluation protocol remain material gaps. Passing regression tests do not resolve those findings.

The user confirmed that the formal manuscript is outside this repository. The five working requirements below are not a verbatim approved thesis specification. DSRM is the planned framework. In particular, the user states that administrative, research and extension workloads are excluded from the latest thesis scope. This audit does not rewrite that scope or silently remove the software's existing release-load policy.

## Working objectives and overall assessment

| Working requirement | Assessment |
|---|---|
| WR1: generate conflict-free faculty, room and section schedules | Implemented and verified on bounded fictional fixtures for supported patterns and declared inputs. Persistent room/faculty closure lifecycle and authoritative catalog integration remain incomplete. A valid output does not establish completeness of the sourced input dataset. |
| WR2: consider specialization, eligibility and preferences | Explicit eligibility and preferences work. Specialization tags are descriptive, not an optimization criterion or permission source. Full roster coverage is coupled to legacy preference rows. |
| WR3: promote balanced teaching workload under academic policy | Fixed Option B and workload penalties exist, but the scorer admits a verified concentration-favoring counterexample. Current non-teaching release inputs conflict with the stated exclusion unless explicitly permitted by an adviser clarification. |
| WR4: preferences, adjustments and decisions with final Chair approval | Verified with real authentication, FastAPI and owned SQLite plus fictional providers. Chair approval and scheduler application are separate. Genuine institutional mandates and the initial authorized publication source remain unconfigured. |
| WR5: evaluate conflicts, preference satisfaction, workload balance, time and unassigned courses | Descriptive reports, validators and fictional timing evidence exist. A standardized all-attempts quality campaign, agreed denominators, independent equity/specialization metrics and approved comparison protocol are missing or incomplete. |

The [42-row traceability matrix](thesis-objective-traceability.md) maps every finding to current code, named tests and limitations. Its [JSON counterpart](testing/thesis-functional-audit/traceability.json) records working-objective IDs and research-alignment qualifiers. IDs are assigned by this audit, not invented adviser-approved objective numbers. The requested classification "Conflicting with thesis methodology" is not asserted as a formal verdict without the manuscript. Confirmed conflicts with the **working** scope or documented balance intent are explicitly identified instead. Some implemented behaviors are verified while the larger requirement remains partial; a passing characterization of a gap is not an acceptance pass for that requirement.

## Evidence and inspection boundary

Inspected the current README, roadmap, documentation standard, Phase 4C academic/workflow contracts, D9-D16 reports, relevant current routes/pages, metadata/identity models, academic repository, authority boundaries, immutable decision/application models, GA constructors/operators/scoring/publication/checkpoint paths, and existing tests. Read the Phase 2, Phase 3, memory, Phase 5 and Phase 6 reports/manifests and relevant fixture/benchmark sources. No AGENTS.md or formal thesis manuscript was found in the inspected repository. Old roadmap/architecture sections are historical, not instructions to restore placeholders or repeat provisioning.

The pre-edit [preservation baseline](testing/thesis-functional-audit/preservation-baseline.json) covers **1,691 pre-existing paths**, including all 23 academic data files, source, migrations, checkpoints, schedules, previous evidence, Git index, existing untracked studies and both tracked local data modifications. Prior Phase 6's 140 artifact hashes were independently checked before starting.

New execution uses the existing schema-only fictional import bootstrap: seven empty CSV schemas and two empty JSON documents substitute only legacy import reads; original loaders are restored before execution. Institutional text/CSV parsing is then denied. Raw binary fingerprints remain genuine. Existing read-only source inspection and preservation hashing are distinct from parsing institutional rows. All new scheduling objects, preferences, release loads and resource examples are fictional. No faculty names, real row payloads, database URLs, credentials, cookies or signed receipts are included in new evidence.

## Verified hard constraints and their limits

Original publication admission reconstructs against current templates and rejects missing/duplicate offerings, invalid intervals, wrong room types, ineligible faculty, incorrect component duration and excessive teaching load. Required laboratory meetings remain continuous three-hour components. Faculty/room/section conflicts are checked separately; adjacent half-open intervals are allowed. Source metadata and fixed-section declarations cannot be silently substituted. New independent slot-pair checks also detect a deliberately duplicated half-hour for each shared resource.

V2 fixed commitments are outside Subject genes, retain revision/term/resource provenance and are checked before candidate admission, selection and best-ever updates. Reduced faculty/room calendars remove committed intervals, so restart resets do not reopen those slots. Fresh D10/workflow tests exercise actual operators and trusted fictional GEC ledger checks, including revocation and constraint rejection. None of this supplies genuine institutional authority.

**Persistent room/faculty closures are a different requirement.** `Functions.reset_room_schedules` (line1254) and `reset_complete_schedule` (line1269) reopen every retained room/faculty block, even a block carrying a synthetic fixed flag. Section blocks retain their flags. A fresh test then assigns a meeting into the previously closed room interval after reset. This is a confirmed limitation of using ordinary occupancy flags as durable closure inputs, not proof that V2's removed-slot commitments can be bypassed. A general institutional closure/calendar lifecycle is not implemented. Define which absences are persistent constraints before changing reset behavior.

Room capacity and enrollment are validated during complete schedule application when an authoritative publication policy marks them required. The ordinary GA Room model has no capacity field. Default runtime student counts are not evidence of real enrollment. Do not claim capacity-aware GA construction from publication-stage checks, and do not invent missing capacity metadata.

## Faculty coverage, preferences and specialization

**Covered runtime members:** missing dashboard preferences do not exclude an already supplied Faculty object. Ranking filters explicit eligibility and load, not preference submission. The scorer initializes the complete supplied faculty universe at zero load, so an unassigned member remains in underload accounting. This is verified for a supplied fictional universe; it does not guarantee every registered faculty member is in that universe or must receive an assignment when supply/eligibility prevents it.

**Roster gap:** the legacy loader resolves identities from `df_preferences['Faculty']` (line219), builds subject-preference keys from those rows (line318), and creates Faculty objects only for `dct_fac_subj.keys()` (line395). The new probe executes that exact original AST roster loop with fictional dictionaries and a test-only metadata resolver. Two supplied identities/load entries but one preference-derived member yield only one runtime member. This is not a complete replay of institutional imports and does not establish an actual excluded-person count. It demonstrates a dependency that can exclude a registered, load-bearing person absent from the legacy preference source. A blank legacy row and a missing legacy row are materially different. No actual institutional roster was read or reconciled.

**Specialization gap:** `faculty_is_explicitly_eligible_for_subject` (line1359) deliberately treats specialization/domain tags as descriptive. Matching tags without eligibility are rejected; mismatching tags with explicit eligibility are allowed. Changing specialization alone does not change fitness. The eight current fitness components contain no specialization term, and no standardized alignment metric was found. This follows current C06 policy but only partially meets working WR2 if "consider specialization" requires actual selection/scoring effects. Do not silently grant eligibility by matching names or domain tags.

There is no strict-specialization optimization stage to relax when infeasible. Missing explicit eligibility fails closed. Aggregate capacity preflight can pass when every offering has zero eligible instructors; bounded construction then reports `SEARCH_EXHAUSTED`. In that fixture the qualification gap is directly known, but the generic error does not explain it. Search exhaustion elsewhere still does not prove mathematical infeasibility. A reviewed exception/qualification process and per-offering coverage diagnostics require department policy, not automatic fallback.

## Workload correctness, fairness and scope discrepancy

Current normal Faculty objects use:

- Teaching target: `max(0, 24 - admin_load - research_load - extension_load)`.
- Underload: soft; unassigned members of the supplied universe remain counted.
- Heavy-overload warning: above 30 teaching units.
- Hard teaching ceiling: 40; the direct validator accepts 40 and rejects 41, and reconstruction rejects an adversarial over-ceiling payload.
- Non-teaching values: fixed input allowances, not generated activities or additional teaching assignments. Credit units and contact minutes are distinct.

The scorer's underload contribution is `ceil((target-actual)/target * 10) * underload_weight`; overload uses separate three-unit bands by default, with heavy bands above the warning threshold. Source inspection and named unit/report tests verify the implemented arithmetic/accounting scope. This audit uses synthetic default settings; it does not parse or publish the user's modified local settings file or claim that its weights equal these defaults.

### Verified fairness counterexample

Two explicitly eligible faculty, each with a 24-unit target, teach two different two-unit offerings. Both schedules pass original hard admission and have zero independent faculty, room and section slot-pair conflicts:

| Allocation | Teaching units | Underload bands | Workload penalty at fictional weight25 | Overall penalty in this control |
|---|---|---|---:|---:|
| Balanced | `[2, 2]` | `[10, 10]` | 500 | 500 |
| Concentrated | `[4, 0]` | `[9, 10]` | 475 | 475 |

The unchanged scorer prefers the concentrated valid schedule. For any positive underload weight, this rounded-band reversal remains in the workload component; zero weight supplies no workload incentive. Constructor proportional-fulfillment ranking helps initial coverage but does not make the optimization objective monotone in fairness. Other preferences can introduce further tradeoffs. This is not proof that every GA run produces concentration; it is a concrete counterexample to an unconditional balanced-workload claim. It requires an explicit adviser/department fairness definition before any scoring-policy revision. No formula or weight was changed.

### Administrative, research and extension inputs are actively included

This is confirmed in the model, metadata API and analysis fields, and now independently in the scorer. Three separate fictional controls hold `[2, 2]` teaching assignments fixed. Giving each faculty a 22-unit **administrative**, **research** or **extension** release separately reduces each teaching target from24 to2 and the workload penalty from500 to0. These fields therefore affect optimization; they are not unused labels.

As written, this inclusion is inconsistent with the user's latest working thesis exclusion. It is not resolved merely by observing that the GA does not schedule those activities. Two possible scope interpretations require adviser confirmation:

1. Exclude optimization/timetabling of non-teaching activities but explicitly permit verified fixed release allowances as external teaching-target inputs.
2. Exclude those loads from the model entirely; then the current target policy is outside scope, and any replacement needs institutional policy approval, explicit scoring/version/checkpoint review and new evidence.

Neither interpretation is chosen here. DSRM itself does not prescribe a 24-unit formula or authorize changing academic policy. Formal manuscript alignment remains UNVERIFIED.

**Configuration ambiguity:** synthetic GASetting values accept target18/ceiling20, while a normal Faculty object remains target24/ceiling40. Normal model attributes govern the implemented policy; generic settings fields are not authority to replace them. Clarify authoritative configuration and legacy/fallback fields before claiming arbitrary workload-policy configurability.

## Actual GA behavior

Initialization constructs candidates within bounded attempts, preserves explicit qualifications and known external commitments, and fills the requested population or fails rather than publishing a partial population. Tournament selection favors lower penalties and distinct parent objects; elitism copies rather than shares mutable chromosomes. Crossover starts from the better parent and replaces a faculty assignment from the donor; mutation swaps faculty between existing offerings. Both accept only improving children under their original criteria. None was edited.

The new deterministic mutation control produces a genuine improved child (**640 to500**) with unchanged subject/section/day/time/room geometry, zero independent conflicts, original publication validity and an unchanged parent. There is no direct time/room mutation operator; alternative timetable geometry comes from initial/fresh construction. A zero-assignment faculty member is not a direct mutation swap partner because mutation selects faculty already teaching a subject. These are search-space limitations to describe accurately, not authorization to rewrite professor-provided operators.

Best-ever is independently copied, admitted and never replaced by a worse score. Checkpoint continuation revalidates source/input/constraint fingerprints and original hard rules. Fresh V2 tests perform actual checkpoint creation/read/continuation, corruption rejection and actual operator execution. Supported V1 fictional source-identical continuation is preserved **historical Phase 6 evidence**, not freshly rerun here. The six historical checkpoints remain unchanged with their existing documented compatibility limitations; none was loaded or migrated by this audit.

Repeated runs with identical fictional settings/input/seed reproduce tested assignments, histories and RNG state. Ordinary UI runs remain stochastic and must not be described as deterministic without a controlled seed protocol. Routes serialize the global RNG execution boundary; that is not proof of distributed multi-worker deployment safety.

The engines stop at configured generations or explicit pause/stop boundaries and report bounded construction failures. Stagnation telemetry is not automatic stagnation termination. No global optimum/convergence proof, automatic target-quality stopping policy or validated search-diversity measure is established. Phase 2's short histories showed improvement, not convergence.

## Decision support and authority

Fresh real-service fixtures exercise GEC confirmation/revocation, actual V2 generation, owned preferences, faculty requests, current scoped Chair trust, exact approved application, rollback/recovery, immutable versions and history. They use real password/session/Origin/CSRF checks and owned SQLite. One request is read through an actual fresh Python process with its private test session transferred through stdin, never evidence.

An account's administrator role is not a Chair mandate or a publication grant. Chair approval and scheduler application are separate; application requires the exact approved revision and complete hard-valid result. Approval alone does not silently mutate the original GA result. All earlier versions remain, stale heads and authority loss reject actions, and requests/receipts are not institutional authorization.

Production verification, confirmation, constrained-deployment, Chair, application and publication providers return unavailable by default. The initial proposal-to-authoritative-publication source has no complete production handoff. D16 explicitly supplied a fictional provider/file handoff, not an institutional approval action. Subject/faculty/room pages are chiefly viewers; Phase4C repository/foundation is not a full term-aware academic-management UI or automatically activated GA input source. These blockers remain distinct from application bugs and must not be bypassed for demonstration.

## Thesis evaluation metrics and DSRM

Existing reports provide descriptive preference outcomes, per-faculty target/actual/fulfillment and recorded penalties. These are useful observations, not stakeholder satisfaction or a single approved research metric. Disabled/missing preferences must not count as 100 percent satisfied, weighted penalty is not a percentage, and specialization eligibility is not specialization alignment.

The following are **proposed evaluation contracts**, not new product metrics or approved methodology:

| Metric | Definition/decision needed |
|---|---|
| Conflicts | Report separate faculty/room/section conflicts. Specify whether an observation is a conflicting meeting pair, half-hour pair or affected offering; never mix denominators. Also report hard-valid accepted schedules / accepted schedules. Zero eligible pairs means not applicable, not fabricated 100 percent performance. |
| Preference satisfaction | Freeze submitted/absent/disabled states and eligible denominators per faculty/component; keep descriptive matches separate from weighted penalties and human survey responses. |
| Specialization alignment | Agree primary/secondary domains, matching rules, unknowns and approved exceptions first. No current standardized formula exists. Explicit eligibility remains a separate hard predicate. |
| Workload balance | Publish the complete approved cohort, targets, actuals, zero assignments, shortfalls/excess and normalized fulfillment spread. Specify zero-target and unavoidable-shortage treatment. A rounded fitness penalty alone is insufficient. |
| Generation time | Record seed, input/engine identity, budget and environment; keep engine, preprocessing, validation, persistence and instrumented timings distinct. |
| Unassigned courses | Compare exact required offering/component multisets with actual valid assignments. Distinguish missing, duplicated and unscheduled components; report failed attempts, not only accepted complete outputs. |
| Feasibility | Distinguish an admitted candidate, a proven input conflict and bounded search exhaustion. Record all attempts and reasons rather than reporting failure as infeasibility or dropping failed seeds. |

The audit's independent duplicate-slot control produces one conflicting pair for each shared resource. Its denominator is explicitly **unordered same-resource/day half-hour slot pairs**, not an implementation of a standard thesis conflict rate. The complete-control fixture has two required offerings and zero missing offerings. No real institutional quality dataset or private records were imported.

The published DSRM model separates problem framing, solution objectives, artifact construction, demonstration, evaluation and communication. This audit maps repository evidence to those activities; it does not certify that the thesis executed its approved methodology. [Peffers et al., Journal of Management Information Systems (2007)](https://www.jmis-web.org/articles/765).

| DSRM activity | Evidence and remaining gap |
|---|---|
| Problem and motivation | Working CCS scheduling context and professor-confirmed GEC/Chair workflows are documented; approved problem statement/stakeholder evidence is outside the reviewed inputs. |
| Solution objectives | User supplied five working requirements and a scope exclusion; formal approved objectives/acceptance thresholds remain UNVERIFIED. |
| Design/development | D1-D16 source, schemas, immutable workflows and tests exist. This audit identifies defects/gaps without changing the artifact. |
| Demonstration | Fresh in-process FastAPI/SQLite workflows; historical D16 real Edge demonstration remains separately attributed. Fictional authority is not institutional acceptance. |
| Evaluation | Functional tests, descriptive metrics and fictional performance studies exist; comparative scheduling-quality protocol, approved equity/specialization definitions and stakeholder evaluation are incomplete. |
| Communication | Linked implementation reports, this matrix/audit and reproducible evidence exist; formal manuscript/defense claims were not reviewed. |

Phase 2-6 evidence remains performance/ownership/parity research: five-seed bounded scaled Python runs, rejected scalar C++ feasibility, allocation/retention investigations and a Phase 6 production-integration NO-GO. These do not establish academic policy correctness, representative institutional quality, convergence, absence of every leak or a completed comparative thesis evaluation. No native implementation or compiler is involved here.

## Priority gaps and next milestone

1. **P1 - Resolve scope and workload equity before claiming objective fulfillment.** Obtain the manuscript and adviser/department decisions on non-teaching release allowances, authoritative target/ceiling policy, and what balanced allocation must prefer. Retain the `[2,2]` versus `[4,0]` counterexample as an acceptance case; do not silently tune weights or rewrite the formula.
2. **P1 - Qualify the scheduling cohort independently of preference participation.** Define active/term-eligible faculty, approved zero-target exclusions and explicit qualifications. Add roster/eligibility coverage diagnostics and a reviewed adapter only in a separately authorized implementation milestone. Do not auto-enroll all identities or invent qualifications.
3. **P1 - Agree specialization and infeasibility handling.** Decide whether matching is descriptive, soft, hard or governed by an explicit exception process; define its measurement and approval authority. Current explicit eligibility must remain fail closed.
4. **P1 - Specify durable resource availability and institutional integration.** Separate closures from transient occupancy, retain V2 fixed constraints, and obtain actual term/catalog/issuer/Chair/publication mandates. Complete initial publication and resource management only within authorized policy and data sources.
5. **P2 - Build the approved offline quality-evaluation campaign.** Use frozen fictional/authorized datasets, all-attempt accounting, approved denominators, independent conflict/completeness checks, equity/alignment metrics and a stated comparator. Document generations/seed diversity; do not claim convergence from short improvements.
6. **P2 - Reconcile documentation and search-space claims.** Older architecture lists six soft components; current scorer has eight. Old roadmap placeholders are superseded by D1-D16. Explain fixed faculty-swap operators and fresh construction accurately. Do not edit historical evidence to hide drift.

Recommended next milestone: **Faculty Cohort, Workload Scope and Evaluation-Policy Qualification**. Begin with signed-off requirements and policy decisions, then authorize only the selected functional corrections and a versioned scoring/checkpoint plan if math must change. This recommendation is not Phase 7 performance integration, C++ work, production activation or authority to implement any fix now.

## Verification, failure attribution and reproducibility

Detailed command records are under [testing/thesis-functional-audit](testing/thesis-functional-audit/manifest.json). Each records the expanded command, cwd, timestamps, elapsed time, exit code and sanitized output. Fresh final selections: **33 audit probes, 83 engine/selection/benchmark regressions, 23 pure reporting tests, 48 workflow tests; 187 backend pytest cases total**. **99 frontend contracts** pass separately. No skipped cases are silently counted as passes.

Audit probes include gap characterizations; e.g. fairness reversal and closure reopening PASS as observations of current behavior, not as successful fairness/closure requirements. The matrix remains partial for those requirements.

Two earlier workflow records are retained, each **47 passed, 1 failed**. First, the new harness rejected an unreviewed fresh-process module. After reviewing the child, a new isolated bootstrap allowed only that exact child with its exact owned SQLite path. Second, an over-restrictive network guard denied Windows asyncio's stdlib loopback self-pipe; its secondary cleanup raised a ProactorEventLoop error. A separate stdlib-only diagnostic reproduced the primary `NETWORK_REJECTED` call from `_fallback_socketpair` and successful loop creation with only that exact owned listener/client pair permitted. PostgreSQL/native-driver and unowned SQLite guards remain active. No application code, timeout, failing test or protected data was changed to obtain the final **48 passed** rerun. Earlier 23- and 30-probe passes are superseded by the expanded 33-case audit selection, not added to its count.

Warnings: required pre-collection schema bootstrap produces an AnyIO assertion-rewrite warning; legacy TestClient selections also record the existing Starlette/httpx and AnyIO BlockingPortal deprecations. No package was installed or warning hidden. The restart child uses its original private stdin transfer; no session value is archived.

Actual browser verification/screenshots: **NOT RUN in this audit**. Frontend evidence is model/API contract testing, not a rendered browser or real backend request. Historical D16's 21 Edge/FastAPI/SQLite scenarios and 188 synthetic-HTTP scenarios are not fresh audit passes. Build/TypeScript/lint: **NOT RUN**, since no frontend or production application code changes. Database scope: owned temporary SQLite only; D15's verified 17+10 PostgreSQL cases remain historical and unchanged, not rerun and not production readiness.

From the repository root in the existing Windows environment:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/thesis-functional-audit/run_checks.py audit
.\.venv\Scripts\python.exe -B docs/testing/thesis-functional-audit/run_checks.py engine
.\.venv\Scripts\python.exe -B docs/testing/thesis-functional-audit/run_checks.py workflow
.\.venv\Scripts\python.exe -B docs/testing/thesis-functional-audit/run_checks.py metrics
.\.venv\Scripts\python.exe -B docs/testing/thesis-functional-audit/run_checks.py frontend
.\.venv\Scripts\python.exe -B docs/testing/thesis-functional-audit/audit_evidence.py
```

Use the runner rather than unbootstrapped pytest, which could import real legacy data. The runner whitelists OS variables, excludes database URLs/credentials/authority flags, redirects test storage to owned temp paths and sanitizes before archival. It never invokes the D15 runner or changes retained databases. No deployment provider is installed.

## Files and preservation

The three Python files first shown as changes were verified **new and untracked**, absent at audit entry: `backend/tests/audit/test_thesis_correctness.py`, `docs/testing/thesis-functional-audit/run_checks.py`, `docs/testing/thesis-functional-audit/restart_child.py`. No existing application files were among those three.

Additional new files are this report, `docs/thesis-objective-traceability.md`, the audit evidence verifier, machine-readable matrix, preservation baseline, sanitized command/observation/diagnosis records and manifest. The [manifest](testing/thesis-functional-audit/manifest.json) provides the exact final path list and artifact hashes; earlier records are retained.

All 1,691 pre-existing paths and all 23 academic files must match their initial raw hashes. The only tracked local modifications remain the **pre-existing** `backend/data/faculty_preferences.json` and `backend/data/ga_settings.json`; both local byte states remain unchanged, unstaged and uncommitted. Original GA/scoring/RNG, academic/migration data, checkpoints, schedules, D15 state/evidence and earlier user work are preserved. No institutional data was parsed into new evidence, no PostgreSQL operation or dependency installation occurred, and no staging/commit/push or next implementation milestone was performed.

Final audit inventory: **48 new files: four Python, two Markdown reports and 42 JSON evidence/manifest files**. The verifier hashes **47 artifacts**, excluding the manifest itself, and rechecks **307 historical artifact entries**. Privacy findings: zero. Git emits its existing LF/CRLF advisory for the protected preference path during read-only diff inspection; no normalization or rewrite is performed, and raw-byte comparisons remain unchanged. No existing tracked or untracked user file was modified by this audit.
