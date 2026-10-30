# Faculty cohort, workload scope and evaluation-policy qualification

2026-10-29, Asia/Manila. Source `main` at `1423812e13a5791a550c893ef6b17bfef4b4ebfb`. Policy qualification and fictional experiments only. **No functional correction, scoring change or production integration was implemented. Adviser-approved thesis alignment is UNVERIFIED; institutional activation remains BLOCKED.**

## Outcome and evidence boundary

The preceding [functional audit](thesis-functional-correctness-audit.md) and [42-row matrix](thesis-objective-traceability.md) remain unchanged. This milestone qualifies their F01–F06, W01–W06, H04 and E03–E07 findings. The user's working objectives and planned DSRM framework are the research boundary; the approved manuscript remains unavailable. Existing comments saying a project or institutional rule is “confirmed” are implementation history, not independent evidence of current departmental or adviser approval.

Fresh evidence: **88 tests passed, zero failed/skipped: 25 new policy cases, 33 existing audit cases and 30 existing D10 engine cases.** One AnyIO assertion-rewrite warning occurred because the schema-only import bootstrap precedes collection. This is not an execution failure or evidence of institutional authorization. The [command record](testing/faculty-policy-qualification/20261029T082049947082+0800/command.json) includes command, cwd, timestamps, duration and sanitized output. The [manifest](testing/faculty-policy-qualification/manifest.json) gives exact paths, hashes, preservation and privacy results.

The tests use fictional D10 resources and schema-only substitution during legacy imports. No institutional CSV rows, protected preferences or local settings were parsed. The original scorer is invoked with synthetic GASetting defaults and explicit fictional scoring inputs. Current source/input fingerprints are genuine binary hashes. D10 continuation writes only owned temporary test stores and uses a fictional unit authority; it is not live institutional, HTTP or PostgreSQL acceptance. No browser, frontend build or lint rerun was needed for this evidence-only milestone; these categories are NOT RUN. No performance/convergence experiment was attempted.

## 1. Faculty cohort completeness

**Already verified.** The normal production legacy-loading path in `backend/genetic_algorithm/utils/Functions.py` is:

1. Read legacy preference rows and resolve their faculty labels through `build_legacy_faculty_codes` (line219); `services/identity_service.py` resolves registered UUID/numeric mappings, rejecting unknown labels rather than allocating codes.
2. Build subject/day/time/priority dictionaries from those same rows; `dct_fac_subj` begins at line318.
3. Iterate **only `dct_fac_subj.keys()`** at line395, obtain release inputs (missing row currently defaults to zero), explicit eligibility and descriptive specializations, construct Faculty objects and attach stable metadata. This list is the GA's *faculty pool*, distinct from the GA population of candidate chromosomes.
4. `services/ga_service.py` imports that pool for V1. V2 accepts a server-owned `Deployment.templates` tuple; tests supply complete explicit fictional cohorts. Production `institutional_deployment()` returns None, so V2 has no configured institutional cohort source. The V2 engine does not enumerate user accounts to fill a supplied pool.
5. Original constructor ranking checks explicit eligibility, projected hard ceiling and proportional target fulfillment. It does not require a preference submission. The scorer initializes every supplied normal faculty member, including zero assignments, from frozen system-faculty inputs. It cannot count an identity never supplied.

Account registration does **not** add a Faculty object to that pool. `routers/auth.py:17,94` validates a database identity and static registry binding and writes the user account; it does not add a legacy preference row or rebuild the GA templates. `identity_models.py` explicitly separates login accounts from GA populations. `metadata_service.resolve_normal_faculty` requires membership in the runtime pool; its metadata listing projects that pool, so using that listing as an independent authoritative roster would repeat the same omission. `AcademicRepository.read_projection` supplies identity mappings, not complete approved participation, load, eligibility and availability profiles.

Therefore a registered faculty identity **can be absent from the normal GA pool if absent from the legacy preference-derived keys**. This is a verified dependency, not a count of actually omitted people. The existing fictional test executes the original AST roster loop with two identities/load entries and one preference-derived key; only one Faculty is constructed. It was rerun here. An empty preference submission and a missing legacy row are different. Creating an account, disabling login, retiring a faculty member and opting out of a term are also different events.

### Proposed roster policy and options

**Recommended but unapproved; requires institutional confirmation, implementation and additional testing:** freeze an authoritative, term/scope-specific participating cohort independently of optional preferences. A person need not have a login or a preference submission to be a scheduling participant. A login alone must not establish employment, term participation, qualification or availability. Require explicit exclusion reasons and provenance; do not invent a term, infer identities by name/order, or silently remove someone because their target is zero or eligibility is missing.

| Option | Implementation boundary and risks | Qualification |
|---|---|---|
| R1: validated roster-first adapter to existing Faculty/templates | Take approved stable UUID/code participation snapshot; join verified loads, eligibility, priority and availability; overlay preferences by exact ID. Preserve supplied order explicitly for reproducibility. Reject or visibly block missing required metadata rather than manufacture zero releases. Reuses model, ranking, scorer and V2 templates. Changes cohort size, zero-load penalties, construction order and fingerprints. | Recommended but unapproved; requires institutional confirmation, implementation, additional testing. |
| R2: complete term-aware academic provider backed by existing foundation | Use academic identity repository plus independently approved participation/profile sources to build the same run snapshot. The repository alone does not supply a complete cohort or activation contract. Requires more lifecycle/provider work; no schema expansion is proposed here. | Requires institutional confirmation, implementation, additional testing. Prefer as later durable source for R1's contract. |
| R3: create blank legacy preference rows for missing people | Can make keys appear, but falsely couples participation to submission, obscures absent versus empty, and requires dataset edits. Existing zero-release/default-priority behavior could become newly active without approval. | Not recommended; not implemented; requires institutional confirmation and additional testing if considered. |

Coverage is not a guarantee of at least one assignment. Supply can be below combined targets; qualifications, fixed assignments and calendars can make zero assignments unavoidable. Report full cohort, participant/exclusion reason, known/unknown metadata, per-offering eligible candidates, target/actual/shortfall and zero assignments. Reject unknown required mappings; do not relax eligibility to improve coverage. Login status must remain a separate security concern. Confirm who qualifies as participating, including leave, part-time, visiting/external instructors and zero-target cases.

## 2. Workload scope: Option B versus teaching-only

**Already verified software behavior:** `Faculty.py:57–101` computes `T=max(0,24-admin-research-extension)` and stores raw CSV Teaching Load as reference, not authority. Underload is soft; 40 teaching units is the hard ceiling, above30 the normal warning threshold. Non-teaching allowances are fixed input credits; they are not generated activities, calendar entries or decision outputs. Model constants override overlapping settings fields for normal Faculty objects; generic GASetting fields do not make policy arbitrarily configurable. This is not proof that these numbers are institutionally approved.

All three allowances actively affect targets, ranking, fitness and analysis/report fields. Prior separate controls (rerun here) show each 22-unit allowance lowers target24→2 and workload penalty500→0 for unchanged `[2,2]` teaching. A new combined fictional control uses admin4/research3/extension1: target16 each, workload450, versus target24/workload500 in the zero-allowance control. No production settings were read or changed.

| Alternative | Rules and research statement needing confirmation | Software impact if later approved |
|---|---|---|
| W-B: Option B | “Schedule teaching only; verified fixed non-teaching allowances are exogenous inputs reducing expected teaching load. Non-teaching activities themselves are not scheduled.” This explicitly includes allowances in the model and evaluation. | Preserve current target formula and limits only if separately approved; qualify allowance authority, effective term, missing-data behavior, units/rounding, zero-target treatment and configuration precedence. Fix roster/default provenance independently. Align UI, exports, thesis scope and evaluation denominators. |
| W-T: teaching-only model | “No administrative/research/extension allowances participate in target construction, optimization or evaluation.” Specify an independently approved teaching target source and applicable limits. A uniform24 target is only an analytical assumption here, not an approved replacement. | Change model target authority and ranking/scoring inputs, projections/analysis/export definitions and tests; retain historical allowance provenance without retroactively rescoring. Review all workload aliases, settings authority and V1/V2 fingerprints. New version/compatibility plan required. Setting release values to zero in institutional files is not a safe implementation. |

**Explicit decision pending:** choose W-B or W-T (or document another precise institutional rule), separately confirm target/limits and approve wording with the adviser. Institutional confirmation governs academic rules and data authority; adviser confirmation governs thesis scope/methodology. Neither substitutes for the other. The latest working statement excludes these workloads; W-B fits only if the adviser explicitly permits fixed release inputs. No code comment or earlier prototype decision resolves this scope conflict. Source integers, fractional credits, missing rows, negative values and release sums exceeding24 need an approved data contract; current clamping must not be changed silently.

## 3. Exact fairness counterexample

**Already verified.** Both candidates have two distinct two-credit fictional offerings, two faculty with target24, empty synthetic preferences, supported two-hour lecture meetings on separate days and the same room. Both pass original V2 admission and independent faculty/room/section conflict checks (all zero). No workload/calendar repair occurs. Lower fitness is better.

| Original component | `[2,2]` | `[4,0]` |
|---|---:|---:|
| Subject preference | 0 | 0 |
| Time preference | 0 | 0 |
| Day preference | 0 | 0 |
| Schedule style | 0 | 0 |
| Lecture/lab preference | 0 | 0 |
| Number of preparations | 0 | 0 |
| Teaching-load balance | **500** | **475** |
| Daily teaching load | 0 | 0 |
| Total | **500** | **475** |

All eight original keys are recorded in [exact breakdown](testing/faculty-policy-qualification/20261029T082049947082+0800/fairness-exact-breakdown.json), not inferred from the total. Neither candidate triggers overload. Preparations/day loads stay below defaults; absent preferences contribute no preference mismatch, not a claimed satisfaction percentage.

`FitnessFunction.py:1892–2115` gives faculty i an underload contribution `25*ceil(10*(T_i-A_i)/T_i)` when `A_i<T_i`, using fictional default weight25. Balanced shortfall22/24 gives ceil9.166…=10 twice: `25*(10+10)=500`. Concentration shortfalls20/24 and24/24 give ceil8.333…=9 and10: `25*(9+10)=475`. Total teaching4 and total deficit44 are identical. Rounding awards the concentrated allocation a one-band advantage. Changing a positive weight rescales this reversal; weight0 removes the workload incentive. Constructor ranking does not change the scorer's ordering.

Default overload contribution, kept separate in the controls, is `10*ceil(max(0,min(A,max(T,30))-T)/3) + 25*ceil(max(0,A-max(T,30))/3)`. The original hard validator, not this arithmetic, enforces40. Teaching units are distinct from contact minutes; daily-load/preparation/preference penalties can trade off in other real candidates. The zero values above are controlled observations, not a universal claim.

### Unapproved analytical alternatives

`policy_experiments.py` is never imported by production. It uses exact rational arithmetic for proposed measures. These are policy comparisons, **not GA integrations or evidence that a modified search converges**. Let `r_i=max(0,T_i-A_i)/T_i` for positive targets, `q_i=A_i/T_i`, and O be the original default overload penalty.

- **L: unrounded relative deficit:** `250*sum(r_i)+O`. Removes the band reversal, but equal-target fixed-supply underload allocations tie. Not a sufficient fairness correction by itself.
- **Q: squared relative deficit:** `250*sum(r_i²)+O`. Smoothly penalizes shortfall concentration; positive-target faculty count equally in relative terms. It is not identical to minimizing fulfillment dispersion, particularly for unequal targets. The scale250 only preserves the all-zero default shortfall cost; it is not calibrated against other fitness components.
- **V: lexicographic `(O, total raw underload units, sum((q_i-mean(q))²))`:** prefer less overload, then less raw shortage, then equal fulfillment. This makes an explicit priority claim; it is not a number to add to existing fitness. Mean/spread includes positive-target cohort members even at zero assignments; zero targets are reported separately, never divided by zero. A future ordering against preferences/specialization must be approved.

Q and V both remove this counterexample but encode different definitions of fairness. The table's current column is **workload arithmetic only**, not overall fitness, except for the two originally admitted controls above. Larger allocation vectors were not constructed as timetables and do not establish feasibility, duration, eligibility, room or section validity.

| Loads / targets | Current workload | L | Q | V `(O, shortage, spread)` |
|---|---:|---:|---:|---|
| `[2,2]` / `[24,24]` | 500 | 458.333333 | 420.138889 | `(0,44,0)` |
| `[4,0]` / `[24,24]` | 475 | 458.333333 | 423.611111 | `(0,44,0.013889)` |
| `[0,0]` / `[24,24]` | 500 | 500 | 500 | `(0,48,0)` |
| `[24,24]` / `[24,24]` | 0 | 0 | 0 | `(0,0,0)` |
| `[26,22]` / `[24,24]` | 35 | 30.833333 | 11.736111 | `(10,2,0.013889)` |
| `[30,18]` / `[24,24]` | 95 | 82.5 | 35.625 | `(20,6,0.125)` |
| `[31,17]` / `[24,24]` | 120 | 117.916667 | 66.267361 | `(45,7,0.170139)` |
| `[40,8]` / `[24,24]` | 295 | 286.666667 | 231.111111 | `(120,16,0.888889)` |
| `[6,6]` / `[12,24]` | 325 | 312.5 | **203.125** | `(0,24,0.03125)` |
| `[4,8]` / `[12,24]` | 350 | 333.333333 | 222.222222 | **`(0,24,0)`** |
| `[0,2]` / `[0,24]` | 250 | 229.166667 | 210.069444 | `(0,22,0)` |
| `[2,0]` / `[0,24]` | 260 | 260 | 260 | `(10,24,0)` |

Q favors `[6,6]` in the unequal-target pair; V favors proportional `[4,8]`. This is a genuine policy difference, not a test failure. Neither ensures everyone can teach. A `[41,7]` arithmetic negative control is flagged above the teaching ceiling and **cannot be admitted regardless of any soft score**. All-zero targets have no fulfillment denominator, not fabricated 100% satisfaction; assigned teaching at zero target retains overload cost. Eligibility/resource scarcity can force imbalance below the ceiling.

The new hard-valid forced-eligibility control permits only one instructor for both offerings. `[4,0]` remains valid and `[2,2]` is rejected by the original publication validator despite the latter's lower proposed Q score. This shows why fairness must be evaluated within the feasible set, never by silently granting permissions. It is not proof of global feasibility or optimality for arbitrary inputs.

**Recommended but unapproved:** reject band rounding as an unconditional fairness guarantee; require an approved independent equity metric and compare Q versus V (plus current scorer as baseline) on qualification-constrained, scarce-supply and unequal-target cases. Do not select a correction yet. Adviser confirmation must cover metric/weight/order and thesis evaluation; institutional confirmation must cover workload entitlements, unavoidable imbalance and exceptions. Both proposals require implementation and additional testing before any product change. Existing mutation/crossover accept only improving changes and do not directly introduce zero-assignment faculty; better scoring alone may not make all desired allocations reachable. No operator change is proposed or authorized here.

## 4. Eligibility and specialization

**Already verified:** `Functions.py:1359` checks an explicit normalized course code in `Faculty.eligible_subjects`. Only eligibility rows with status `eligible` are imported. Specialization tags (`Faculty.specializations`) and subject primary/secondary domains (`Subject.py`) are descriptive. Matching domain tags never grants permission; explicit permission with nonmatching tags remains allowed. Changing tags alone leaves the original eight-component score unchanged. Phase4C C06 makes this separation deliberate.

**Recommended but unapproved:** retain explicit eligibility as hard admission; define specialization as a separately measurable soft preference **only among eligible alternatives**. A lack of specialization match must not reject a necessary eligible assignment or relax eligibility. With only one eligible instructor, report constrained alignment opportunity rather than pretend a matching alternative existed. Multiple eligible faculty may still lack a feasible matching alternative because of calendars, workload, fixed commitments or other offerings; simple per-offering match counts do not prove a feasible global alternative.

Required institutional data: stable faculty/course/offering IDs, term validity, approved specialization/domain taxonomy, verified faculty tags and provenance, subject primary/secondary tags, explicit permissions and approved exceptions, and treatment of missing/conflicting labels. No name, title, department or preference-derived inference. Current tags do not establish that this data is complete or validated. No real tags were read for this milestone.

Candidate choices requiring adviser and institutional confirmation: binary any-domain match; distinct primary/secondary weights; or preference/tie-break reporting only. Unknown metadata must be reported separately from verified nonmatch; excluding unknowns from a denominator requires a visible coverage rate so missing data cannot improve the measured rate. A soft term must not create new mandatory qualification rules. Retaining the current descriptive-only behavior is also a valid choice if scope wording is narrowed explicitly.

Proposed evaluation metrics (not product fields): eligibility validity = explicitly eligible GA-managed assignments / GA-managed assignments; alignment = verified aligned assignments / known-domain GA-managed assignments; unknown coverage and approved exception counts separately; optional credit-unit weighting must not be mixed with offering-count weighting. Externally preassigned instructors must be separately scoped. Report aligned opportunity among eligible candidates, distinguishing metadata opportunity from proven feasible alternatives. Zero denominators mean NOT APPLICABLE. Any scoring scale/order, its tradeoff with workload/preferences, and any Chair-approved exception process require confirmation before implementation.

## 5. Availability ownership and persistence

**Already verified source path:** `schedule_is_available` and `room_schedule_is_available` (`Functions.py:813,825`) require all expected half-hour blocks present and available. Assignment marks retained blocks unavailable; rollback releases occupancy. `reset_complete_schedule:1269` zeros teaching state, clears subject assignments and sets **every retained faculty block** available; `reset_room_schedules:1254` does the same for rooms. The reset does not distinguish a maintenance/leave closure from a temporary occupancy flag, even when `fixed_schedule=True`. Constructor restarts call this reset (V1 `create_schedule_with_minimum_load`, V2 `construct`). Copying templates into a new run does not change that behavior. The new clone test confirms the input remains intact while the run-local closure is reopened.

| Kind | Current reset/reconstruction behavior | Policy implication |
|---|---|---|
| Temporary assignment occupancy | Cleared/released during reset/rollback | Expected run state; retaining it would strand calendars and break future attempts. |
| Room/faculty closure represented only as `is_available=False` | Reopened on restart, even with synthetic fixed flag | A legitimate restriction **could disappear if encoded this way**. No actual institutional lost closure was established. Persistent closure source/lifecycle is incomplete. |
| Missing faculty/room blocks in V2 reduced calendar | Not recreated by reset; matching requires complete blocks | D10 commitments survive; tests exercise repeated restarts and final admission. Missing intervals are not a general approval workflow. |
| Fixed section calendar blocks | Section availability is retained; fixed-block checks continue | Existing section enforcement must remain, including separate checks against current chromosome meetings. |
| Preferences (preferred day/time) | Soft scoring inputs | Never reinterpret as authoritative unavailability. |

**Recommended but unapproved; requires institutional confirmation, implementation, additional testing:** separate immutable, sourced, term-effective room/faculty availability from temporary occupancy, preserving both checks. Reuse V2 snapshot/reduction/admission principles where applicable, but do not repurpose a boolean, PreassignedAssignment, or GEC trust as authority for all closures. Confirm recurrence, effective dates, holidays/exceptions, owners, revocation and freshness rules first. Guard rollback, clone/reconstruction, seed admission, restart, checkpoints and publication against reopening or losing authoritative restrictions. Resetting all flags to false is equally unsafe. No reset logic or constraints changed here.

## 6. Decisions, research alignment and implementation order

The [policy decision matrix](faculty-policy-decision-matrix.md) identifies status and decision owners for every proposal. **No policy is approved by this report.** Formal alignment for every row remains UNVERIFIED. The machine-readable [matrix](testing/faculty-policy-qualification/decisions.json) uses only the requested classification vocabulary.

For DSRM, this milestone refines the problem/objective and evaluation contracts; functional tests demonstrate behavior of an artifact. They do not establish adviser acceptance, stakeholder utility, workload fairness in the institution, comparative scheduling quality or generalization. The 42-row matrix remains the working requirement trace. Update the thesis objectives/scope, conceptual inputs/outputs, fitness equations, hard/soft constraint definitions and evaluation method consistently only after decisions are approved. Version any changed policy; do not rewrite old reported schedules or claim historical scores were computed under new rules.

Prioritized plan **for later authorization**, not implementation in this milestone:

1. **P0: decide scope and cohort contracts.** Obtain department participation/qualification/availability owners and adviser workload-scope interpretation. Resolve W-B/W-T, targets/ceilings, zero-target/missing-data cases, fairness definition and specialization role. Record effective term/provenance and approval separately. No new database schema is assumed necessary.
2. **P1: roster completeness and diagnostics.** Implement approved R1 contract using existing identity mappings and V2 templates. Overlay optional preferences; preserve absent versus empty/disabled. Add per-offering coverage/blocker diagnostics and reproducible cohort ordering without inventing records. Fail on missing required metadata rather than silently excluding people/defaulting authority. Keep login security and scheduling participation separate.
3. **P1: immutable availability contract.** After owners/semantics confirmed, qualify run-local closure projection through reset/reconstruction/admission. Preserve existing fixed-section and GEC mechanisms and temporary occupancy semantics.
4. **P2: evaluation first, scoring only after approval.** Add independent cohort/shortage/equity/alignment metrics and all-attempt outcomes. Compare current, Q and V on frozen fictional inputs and approved comparators. If a scoring policy is selected, explicitly version settings, reports, saved-result interpretation and V1/V2 checkpoint compatibility. Never spoof fingerprints or silently migrate the six historical artifacts. Current continuation behavior is the protected baseline.
5. **P3: production authority readiness as a separate milestone.** Complete genuine provider/institutional approvals and a term-aware academic input/publication contract only with authorization. Passing disposable PostgreSQL, fictional authority or policy tests cannot enable these providers.

### Regression suite required before any correction

These are **requires implementation / requires additional testing** proposals, not freshly completed feature tests:

| Area | Required acceptance cases | Existing reuse / likely future code boundary |
|---|---|---|
| Cohort | Two registered identities, one/no preferences: both approved participants supplied; no-account participant; inactive login versus term exclusion; explicit leave/zero target/external cases; missing/duplicate/ambiguous UUID/code, stale cohort; unknown load/eligibility blocks visibly; no order-dependent remapping; frozen roster includes unassigned members. | `identity_service.py`, `metadata_service.py`, `academic_repository.py`, `ga_service.py` template construction, V2 Deployment; `tests/audit/test_thesis_correctness.py`, D10 support/API, identity/auth tests. Never grant participation from a client ID. |
| Scope | Each allowance independently and together; sums0/24/>24, approved fractional/invalid handling; chosen teaching-only/OptionB target authority; warning30/31 and hard40/41; consistent model/settings/report definitions; fixed inputs never become scheduled non-teaching outputs. | `Faculty.py`, `GASetting`, scorer, `faculty_analysis_service.py`, `fitness_reporting_service.py`; selected `tests/test_fitness_reporting.py` controls. Any future edits require separate authorization. |
| Fairness | Exact eight components; equal/unequal targets; balanced/concentrated, all-zero, scarce/indivisible units; zero targets; eligibility-forced imbalance; overload/ceiling; preference tradeoffs; independent equity metric; stable deterministic arithmetic; scale/weight sensitivity. | New analytical controls plus original audit/D10 admission. Require actual bounded GA runs for any future scorer, not only allocation arithmetic. |
| Specialization | Eligible+matching/nonmatching both allowed; match+ineligible rejected; primary/secondary taxonomy; unknown/conflicting evidence; all/one/no matching alternatives; external/preassigned scope; metric denominators; no global feasibility inference from per-offering opportunities. | Existing qualification loader/hard gate, metadata and fitness reporting; new versioned scorer only if approved. |
| Availability | Occupancy clears but trusted closures survive clone/restart/rollback/reconstruction; adjacent intervals, all days and grid boundaries; independent room/faculty/section exclusions; changed/revoked snapshots; seeds and descendants cannot reopen blocks; copied graph independence. | `Functions.py` availability/reset/release helpers, `ga_v2_constraints.py`, `chromosome_service.py`, publication validation; D10 reset/admission tests. |
| Cross-cutting | Same fixture/seed reproducibility and RNG restoration; independent hard validity/subject completeness; best-ever/fitness history and graph isolation; V1 and V2 creation/continuation/rejection; changed-policy fingerprints reject clearly; authority/ownership/CSRF/Chair/application restrictions; historical schedule bytes unchanged. | D10/benchmark/retention/reconstruction suites and D11–D16 workflows. Rerun relevant integration and browser/build checks only when implementation is authorized. |

## 7. Confirmation questions

The following decisions remain **requires institutional confirmation** and/or **requires adviser confirmation**, not approval requests to mutate data now:

1. Department: which roster and effective term determine participants? Which exclusions (leave, visiting, zero target) are valid, and who attests them? Is a login irrelevant to participation, as recommended?
2. Adviser: does the excluded non-teaching scope mean W-B (fixed allowances permitted, activities not scheduled) or W-T (allowances excluded from the model entirely)? Supply approved wording, not an inferred interpretation.
3. Department: what authoritative teaching targets, allowance credit units/rounding, warning/hard limits and missing-data rules apply to each cohort category? Adviser: how will these be bounded in the thesis?
4. Adviser and department: does fairness mean equal teaching units, equal target fulfillment, minimizing relative shortfall, avoiding zero assignments where feasible, or an explicit priority order? Is unavoidable concentration permitted when eligibility/calendars demand it? How should preferences trade off?
5. Department: who verifies specialization/domain taxonomy, eligibility and any exceptions? Adviser: descriptive reporting, tie-breaker or weighted soft objective, with which primary/secondary and unknown-data rules?
6. Department: which room/faculty closures are authoritative, with which recurrence/dates, freshness/revocation and ownership? Which flags are only transient occupancy? Preferences must remain distinct.
7. Adviser: approve all-attempt metric denominators, cohort/external/unknown scope, comparators, seeds/budgets, infeasibility versus search-exhaustion labels and acceptance thresholds. Functional regression counts are not a substitute for that evaluation protocol.

## Files, reproduction and preservation

All additions are under `docs/`; no existing source, test, report or evidence file was edited. **28 new files: four Python, two Markdown and22 JSON; 27 artifacts hashed, excluding the manifest itself.** New files: this report; `docs/faculty-policy-decision-matrix.md`; `docs/testing/faculty-policy-qualification/{preservation-baseline.json,policy_experiments.py,test_policy_qualification.py,run_checks.py,audit_evidence.py,decisions.json,manifest.json,audit-attempt-01.json}`; and the timestamped command plus 17 numeric observation JSON files. The manifest gives the exact inventory and raw hashes, excluding itself.

One unsuccessful verifier attempt is preserved in `audit-attempt-01.json`: its report-link check initially required the manifest before creating it. No preservation check failed and no policy/GA test failed. The new verifier now permits only its own output manifest during the pre-write link check and verifies its existence after creation. The corrected audit passes. This is a new evidence-tooling correction, not an application or scoring correction. Git's existing LF-to-CRLF advisory for protected preferences appeared during read-only diff inspection; raw bytes were rechecked unchanged, with no normalization or staging.

From the repository root in Windows PowerShell (existing venv, no installation):

```powershell
.\.venv\Scripts\python.exe -B docs/testing/faculty-policy-qualification/run_checks.py
.\.venv\Scripts\python.exe -B docs/testing/faculty-policy-qualification/audit_evidence.py
```

Runs create a new timestamped directory; no earlier observations are overwritten. The audit verifies **1,739/1,739 existing paths and all23 academic files**, including prior audit/performance work, original GA/scoring/RNG, migrations, checkpoint/schedule/history trees, Git index and both pre-existing data modifications. New privacy checks cover encoded complete/truncated receipt patterns, credential URI/key patterns and sensitive log fields; no private faculty records were copied. Raw hashing is preservation, not parsing protected data. Git whitespace checks are non-mutating. The existing `faculty_preferences.json` and `ga_settings.json` modifications remain byte-identical, unstaged and uncommitted. No database operation, settings change, installation, staging, commit or push occurred.

This milestone qualifies decisions and plans. It does not fix roster inclusion, fairness scoring, specialization or closure persistence, establish thesis compliance, or qualify production deployment.
