# F2A: isolated target-relative workload fairness prototype

2026-10-30, Asia/Manila. Source `main` at `1423812e13a5791a550c893ef6b17bfef4b4ebfb`. **Target-weighted relative squared deviation is suitable for conditional consideration in F2. It is not approved or ready for production integration. No production function, policy, roster, setting or data was changed.**

The user reports adviser/department approval of fairness relative to individual teaching targets and Option B: recognized fixed administrative/research/extension allowances reduce expected teaching units, but those activities are not scheduled. This report accepts those as user-reported requirements; it does not invent documentary approval, an institutional provider or formal thesis alignment. IT remains the intended prototype/evaluation scope. The [F1](faculty-cohort-f1-implementation.md) and [F1.5](faculty-cohort-f1-5-it-qualification.md) production roster/provider blockers remain. All new people, offerings, rooms, calendars and allowances are fictional, not an expanded IT/IS/CCS cohort.

## Baseline: exact inputs and reproduced defect

Reviewed the original Faculty model, current scorer and frozen inputs, constructor eligibility/load ranking, original admission/reconstruction, [policy qualification](faculty-policy-qualification.md), its mathematical controls and the prior [functional audit](thesis-functional-correctness-audit.md). No AGENTS.md was found. Local protected settings/preferences were not parsed; synthetic `GASetting()` defaults were supplied explicitly.

For faculty i, current teaching target is `T_i=max(0,24-admin_i-research_i-extension_i)`. Actual teaching `A_i` sums offering credit units, not contact hours. Every supplied cohort member is initialized, including zero assignments. Non-teaching inputs are fixed hypothetical allowances. Underload is soft, teaching above30 is a warning/heavier soft-overload region, and40 is the hard teaching ceiling. Missing eligibility does not grant permission. These rules and source remain untouched.

With default underload weight25, normal-overload weight10, heavy-overload weight25 and three-credit overload steps, current workload contribution is:

```
if A < T: 25 * ceil(10 * (T-A)/T)
else:     10 * ceil(max(0,min(A,W)-T)/3)
        + 25 * ceil(max(0,A-W)/3)
where W = max(T,30)
```

There is no division by zero in the original branch when `T=0`; positive teaching then attracts overload. Original hard admission independently rejects above40. The experimental arithmetic helpers also reject unsupported/over-ceiling inputs; that is not a substitute for checking a complete schedule.

The counterexample uses two faculty, each target24/allowances0, two two-credit/two-hour lecture offerings, separate sections, compatible room, supported half-hour grid, no submitted preferences, default preparation threshold3 and daily limit360 minutes. F2A's fixed geometry uses adjacent Monday meetings at07:30–09:30 and09:30–11:30. A fictional section commitment begins at09:30 for the first section, so its own07:30–09:30 meeting is adjacent and valid. Both allocations pass unchanged V2 admission and independent faculty/room/section conflict checks.

| Original component | `[2,2]` | `[4,0]` |
|---|---:|---:|
| Subject preference | 0 | 0 |
| Time preference | 0 | 0 |
| Day preference | 0 | 0 |
| Schedule style | 0 | 0 |
| Lecture/lab preference | 0 | 0 |
| Preparations | 0 | 0 |
| Teaching-load balance | **500** | **475** |
| Daily load | 0 | 0 |
| Total | **500** | **475** |

Balanced: `ceil(10*22/24)=10` per person, so `25*(10+10)=500`. Concentrated: bands9 and10, so `25*19=475`. Both have total teaching4 and shortfall44. Rounding the individual ratios rewards concentration. Unrounded linear proportional shortfall ties these allocations; absolute shortfall alone also ties. Weight changes merely rescale this ordering while positive. Source constructor ranking may help coverage but cannot correct the objective's preference.

## Candidate definitions

Standalone `fairness_models.py` is never imported by production. Let `d_i=A_i-T_i`, and `h_i=max(T_i,1)` for the prototype's integer-credit domain. All candidate scores below are lower-is-better. **The one-credit denominator at target0 is an explicit unapproved convention**, not a claimed departmental rule. Fulfillment for target0 remains undefined in metrics.

| Candidate | Exact raw formula | Meaning / limitation |
|---|---|---|
| A: absolute | `sum(abs(d_i))` | Measures total target mismatch, but fixed-supply all-underloaded allocations tie; distribution is not resolved. |
| B: squared units | `sum(d_i²)` | Prefers equal absolute deviations in the unconstrained interior. Unequal targets can leave a low-target faculty unassigned. |
| C: equal-person relative squared | `sum(d_i²/h_i²)` | Each positive-target person has equal weight at100% shortfall. Does not generally equalize fulfillment when supply is constrained. |
| D: target-weighted relative squared | `sum(d_i²/h_i)` | For positive targets, `sum(T_i*(A_i/T_i-1)²)`. Favors equal fulfillment ratios in an otherwise unconstrained fixed-supply problem. Target-weighting is a deliberate policy detail requiring confirmation. |

A fifth **sensitivity only**, H, is `(250/24)*D + original overload contribution`. It preserves the old overload/heavy bands explicitly while also counting excess in D. This double contribution is disclosed; it is not silently adopted. Scale250/24 makes a zero-assignment, target24 faculty contribute250 before any extra overload, but is not a calibrated tradeoff against preferences/preparations/daily load. Raw A/B/C/D have different units/scales and must not be added directly to the old total as interchangeable penalties.

The production scorer still computes all eight original terms. New scores are computed **after original admission**, offline. No experiment injects a new scorer into an operator, changes the GA's acceptance behavior, clears a calendar, alters a preference or consumes its RNG. Exact `Fraction` arithmetic avoids rounding in candidate comparisons; production numeric type, supported credit precision and rounding remain decisions, not silently selected implementation policy.

### Worked counterexample

| Allocation / targets24,24 | Original | A | B | C | D |
|---|---:|---:|---:|---:|---:|
| `[2,2]` | 500 | 44 | 968 | `121/72` (1.680556) | `121/3` (40.333333) |
| `[4,0]` | 475 | 44 | 976 | `61/36` (1.694444) | `122/3` (40.666667) |

B/C/D fix this example; A does not. Multiplying D by the illustrative250/24 gives420.138889 versus423.611111. Those are counterfactual component values, not newly produced GA fitness scores. All other components are zero in these controls and no new component has been hidden in them.

### Unequal-target disagreement

Targets12 and24, total supply12, two-credit offerings, all assignments explicitly eligible:

| Allocation | Original | A | B | C | D | Fulfillment |
|---|---:|---:|---:|---:|---:|---|
| `[12,0]` | **250** | 24 | 576 | 1 | 24 | `1,0` |
| `[0,12]` | 375 | 24 | **288** | 1.25 | 18 | `0,1/2` |
| `[8,4]` | 325 | 24 | 416 | **29/36** | 18 | `2/3,1/6` |
| `[4,8]` | 350 | 24 | 320 | `8/9` | **16** | `1/3,1/3` |

The original scorer favors fully satisfying the smaller target and leaving the other person at zero. Raw squared error instead favors equal12-unit deficits, leaving the smaller-target person at zero. Equal-person normalized squared error favors `[8,4]` on this grid. D selects equal fulfillment `[4,8]`. Merely naming a formula “normalized” does not establish which fairness interpretation it implements.

For positive targets and divisible teaching supply S, minimizing D with `sum A_i=S` gives `A_i/T_i=S/sum T_i` when no bounds/eligibility/calendar restriction is active. Its marginal derivative is `2*(A_i/T_i-1)`. By contrast B equalizes raw deficits and C has derivative `2*d_i/T_i²`. Exact rational tests verify `D(A)-D(proportional optimum)=sum((A_i-A_i*)²/T_i)` on the controls. This is a mathematical property of the continuous allocation objective, **not** a claim that fractional courses can be assigned or that the GA finds a global optimum.

## Fictional scenario results

Nine bounded scenarios enumerate every explicitly eligible assignment **on one fixed meeting geometry per scenario**. There are470 original-hard-valid assignments and45 distinct workload vectors. Timing geometry is spread at most two adjacent two-hour meetings/day; the same course appears across sections except two distinct eligibility groups where needed. Preparation count stays below3 and daily teaching stays below360 minutes. No preparation/daily limit, weight, preference or other production setting was changed to obtain equality: all seven non-workload contributions are checked to be zero in every accepted control. There is no GA search with a candidate formula or whole-system evaluation here.

| Scenario | Targets / supply | Original winning allocation(s) | D winning allocation | Interpretation |
|---|---|---|---|---|
| Equal-target shortage (A/B/E/J) | `[24,24]` /4 | `[4,0]`, `[0,4]` | `[2,2]` | Corrected distribution, unavoidable underload remains44. |
| Unequal targets (C/E/I/J) | `[12,24]` /12 | `[12,0]` | `[4,8]` | Equal1/3 fulfillment; shortage24 remains. |
| Explicit non-teaching allowances (D/E) | `[4,8]` /6 | `[4,2]` | `[2,4]` | Allowances `(admin8,research8,extension4)` and `(8,4,4)` produce targets4 and8 through unchanged Option B. Both have1/2 fulfillment; shortage6 remains. |
| Supply above targets (F) | `[4,8]` /16 | `[8,8]`, `[6,10]`, `[4,12]` | `[6,10]` | Overload4 is unavoidable within this complete fixed offering set. D selects nearest feasible proportional allocation on the two-unit grid. C selects `[4,12]`; no soft score authorizes exceeding40. |
| Included member with no eligible offerings (G/I) | `[12,24,6]` /12 | `[12,0,0]` | `[4,8,0]` | Third member remains in metrics/scoring with shortfall6 and zero assignments; no eligibility fabricated. Total shortfall30. |
| Limited eligibility (H) | `[12,24]` /12 | `[12,0]` | `[8,4]` | Four offerings are exclusive to the first faculty; only two are shared. Numerically better `[4,8]` cannot be admitted. |
| One indivisible offering (I) | `[12,24]` /2 | `[2,0]` | `[0,2]` | Some eligible faculty must remain unassigned. This exposes an opportunity/coverage policy decision, not a reason to split a course or grant permissions. |
| Targets exactly reachable | `[4,8]` /12 | `[4,8]` | `[4,8]` | All four candidates select the same on-target allocation. |
| Zero-target member | `[0,4]` /4 | `[0,4]` | `[0,4]` | No divide-by-zero; zero-target fulfillment is undefined. Does not prove a universal no-teaching policy for target0. |

The [analysis](testing/workload-fairness-f2a/20261030T120717945343+0800-analysis/analysis.json) links the exact source hashes, complete winning sets and pairwise ranking counts. Together, the nine scenario JSON files contain all45 distinct-vector score/metric observations, exact rational values, original eight-component breakdowns, allowances, eligibility coverage, signed/relative deviation, underload/overload distributions, zero assignments, fulfillment spread/variance, unassigned offerings and hard-conflict checks. Duplicate assignment arrangements with the same vector are counted in470, not falsely counted as new workload evidence.

Across115 within-scenario unordered vector pairs, D and the original agree strictly on60, reverse40, resolve seven original ties, create seven candidate ties and retain one tie. This is descriptive ranking change, **not an accuracy percentage** against the old defective scorer or a trusted policy oracle. D's sampled winners are unchanged by illustrative extra eligible-zero penalties0/1/5/25 in raw D units; that does not prove such penalties have no effect elsewhere.

## Underload, overload, zero assignments and eligibility are different

- **Target satisfaction:** shortage/excess relative to each fixed target. With supply below combined targets, some shortfall is inevitable even if all assignments are valid. Do not classify it as a hard failure.
- **Distribution:** D seeks proportional fulfillment among feasible choices; it neither maximizes mean unweighted fulfillment nor guarantees a minimum assigned course per person. Do not use weighted score alone as the research equity metric.
- **Eligibility:** mandatory and independent. The adversarial limited-eligibility candidate is constructed with the low-level assignment helper but rejected by the unchanged original V2 admission gate before candidate scoring/selection. No penalty compensates for missing permission.
- **Coverage:** all required offerings are assigned in successful controls, while some participating faculty can remain unassigned. Report both counts with their own denominators. An eligible offering does not prove a feasible scheduling opportunity across all calendars/resources.
- **Underload penalty:** no additional standalone underload term is mathematically necessary for A–D to detect deviation; positive-target zero assignments are included already. Extra terms would represent an additional priority and can double count.
- **Overload penalty:** A–D penalize excess symmetrically. Original policy uses asymmetric bands and heavier teaching above30. If these priorities must remain, a separately approved overload supplement or asymmetric coefficient is needed; H demonstrates one explicit option, not a free preservation guarantee. The40-unit hard ceiling remains unchanged regardless of scoring. Symmetry, warning severity and tradeoffs require confirmation before integration.
- **Zero-assignment penalty:** not recommended unconditionally. Unqualified or supply-limited people can have unavoidable zeros. Count them visibly; an opportunity-aware coverage floor or time-horizon fairness policy requires separate approval and feasibility analysis. Adding a flat count cannot decide which of two people gets a single indivisible offering when both options have one zero.
- **Target0:** current hard rules allow teaching up to the normal ceiling with overload cost. The prototype's denominator1 can still prefer teaching at target0 under surplus: an arithmetic-only `[2,14]` versus `[0,16]`, targets`[0,4]`, scores29 versus36. This is not a generated timetable or approved policy. Zero target as a hard exclusion versus permission to overload must be decided explicitly.

## Measured execution cost

Pure arithmetic timings were measured separately from tests, cProfile and tracemalloc. Each cell below is median microseconds/call over seven batches of1000 identical inputs, after100 warm-up calls; sample standard deviation is shown. Formula order is shuffled with a private fixed-seed RNG. Common argument checks and exact rational construction are included. Cohort sizes12/24 are arithmetic vectors, not larger generated schedules. Cold measurements and all samples/min/max/means are retained in [timing evidence](testing/workload-fairness-f2a/20261030T120720971631+0800-timing/timing.json).

| Function | 2 faculty median ±SD | 12 faculty median ±SD | 24 faculty median ±SD |
|---|---:|---:|---:|
| Original workload reference arithmetic | 5.418 ±0.919 | 14.491 ±2.675 | 24.238 ±4.189 |
| A absolute | 2.596 ±0.853 | 6.720 ±2.094 | 8.918 ±0.309 |
| B squared | 2.892 ±0.901 | 6.118 ±1.770 | 8.514 ±0.608 |
| C equal-person relative | 4.879 ±1.426 | 24.945 ±5.755 | 40.065 ±6.252 |
| D target-relative | 4.789 ±0.808 | 25.554 ±5.719 | 35.702 ±2.910 |
| H D plus explicit original overload | 10.367 ±1.404 | 30.561 ±8.785 | 58.340 ±11.123 |

D is slower than the arithmetic reference at12/24; at24 its median is35.702 versus24.238µs. This is a correctness-first exact-arithmetic prototype, not performance optimization. The reference uses float/ceil and validates again in its overload helper; candidates compute different functions and numeric types. These timings do not isolate a removable production bottleneck or predict GA execution speed.

A separate real call to the **original full eight-component scorer**, with two faculty/two offerings and already frozen fictional inputs, has median91.730µs, SD7.056, min85.437, max101.998 over seven batches of100. Cold call883µs;100 calls warmed it. It returns the unchanged500 breakdown. [Record](testing/workload-fairness-f2a/20261030T120920440938+0800-original-timing/original-fitness-timing.json). Construction, input freezing, validation, file I/O and persistence are excluded from that timed region. No integrated replacement or full-engine speedup was measured. These are one-machine, one-process microbenchmarks with observed variability, not hardware-controlled general performance claims.

## Fresh tests and retained failure

Final [backend record](testing/workload-fairness-f2a/20261030T120606394976+0800-backend/command.json): **118 passed**, zero failed/skipped, three warnings:32 new F2A cases,33 original audit cases,30 D10 engine/continuation cases and23 selected pure fitness-reporting cases. The existing scorer agrees with workload reference arithmetic on every generated control. Tests cover exact formulas, malformed/over-ceiling inputs, zero targets, balancing/permutation properties, RNG/input preservation, all A–J scenario requirements, unqualified/limited eligibility, original hard validity and current checkpoint/best-ever rules. Existing operators/scoring remain under test, not replacements.

Final [frontend record](testing/workload-fairness-f2a/20261030T120658774259+0800-frontend/command.json): **42 Node contracts passed**, zero failed/skipped/cancelled. Reporting, preference, faculty display and constrained-GA contracts remain compatible. These are not browser scenarios. No new UI, API or institutional data flow exists to browser-test; browser/build/lint and live database acceptance are NOT RUN. No PostgreSQL or other database connection was made. Temporary original checkpoint regression writes stay in owned test stores; historical artifacts are not used as writable fixtures.

The initial backend run had **117 passed, one failed**: the new negative test incorrectly expected `assign_schedule_to_faculty` itself to enforce explicit eligibility. That helper enforces resources/load; original ranking and final admission enforce qualification. The test now deliberately constructs the adversarial candidate and requires original admission to reject `INVALID_CANDIDATE`. It passes. No production fix, disabled assertion, timeout increase or score on an invalid candidate was used. The [diagnosis](testing/workload-fairness-f2a/initial-test-diagnosis.json), initial command and all useful intermediate observations remain. The final118 is not added to the117 intermediate passes. Warnings are the existing AnyIO rewrite bootstrap, Starlette/httpx TestClient and BlockingPortal deprecations; no dependencies were installed or warnings suppressed.

## Recommendation and remaining confirmation

**Recommend D for further F2 consideration under the proportional-fulfillment interpretation, with no production integration now.** It corrects the equal-target example, handles unequal targets more consistently with equal fulfillment than A/B/C, and chooses the best permissible control under limited eligibility. Its recommendation is supported by mathematical structure plus several hard-valid bounded fixtures, not solely the two-person example. Neither user-reported broad policy approval nor these tests approves the exact function, target weighting, scale or institutional data source.

Confirm before a production proposal:

1. Does “relative to individual targets” specifically mean proportional fulfillment (D), equal-person normalized-error weight (C), max-min fulfillment, or another explicit objective? The documented disagreement must be acknowledged.
2. How should shortage and excess be weighted? Must current normal/heavy overload bands remain, become separate objectives or be replaced? Confirm warning30, ceiling40 and zero-target teaching treatment rather than inferring permission from a score.
3. What scale/order trades workload fairness against submitted preferences, preparation and daily-load penalties? A lower synthetic workload score alone is not improved overall scheduling quality.
4. Should an eligible person receive at least one offering when globally feasible, or should fairness extend across terms? Define treatment of indivisible offerings, zero-target/no-eligible members and unavoidable underload before adding a coverage penalty.
5. Approve independent evaluation metrics/thresholds, comparator, exact input cohort and shared external teaching accounting. F1/F1.5 roster and institutional-source limitations still prevent real IT/CCS readiness claims. Formal manuscript alignment remains UNVERIFIED.

### Proposed F2 integration plan, requiring separate authorization

1. Freeze approved formula, data domain/precision, workload scope, coefficients and policy identifier in a versioned specification. Preserve historical equations/scores and original protected settings.
2. Build version-aware dispatch using the existing frozen-input/scoring-policy seam. **All call sites must use the same pinned objective:** initialization, crossover/mutation internal improvement tests, selection, admission, best-ever, reports and publication. Changing only orchestration scoring would leave operators comparing the old objective. Do not monkeypatch global symbols or modify protected operator implementations to disguise mixed semantics.
3. Design explicit engine/input/policy/checkpoint compatibility. Keep supported V1/V2 continuation behavior and all six historical artifacts byte-identical; reject mismatches rather than spoofing hashes or rescoring old history. Demonstrate legacy and new-policy round-trips before enabling any new mode.
4. Keep the complete sourced cohort (including zero assignments) and original qualification, coverage, fixed-resource, day/time/room/section and hard-load gates. Do not implement roster fallback, eligibility relaxation, calendar reset changes or specialization scoring as part of F2.
5. Run differential constraints/RNG/ownership tests, seeded full GA campaigns under unchanged operator budgets, preference/workload tradeoff and unavoidable-scarcity tests, new-policy checkpoint/resume, reporting/API/frontend/browser and authority regressions. New scores legitimately change accepted candidates and random-call paths; do not promise identical new-policy trajectories to the old policy. Require truthful search-exhaustion diagnostics and all-attempt metrics.
6. Authorize a limited versioned fictional rollout only after tests/policy review. Production institutional use remains separately gated by genuine IT roster/profile/authority qualification. No F2 integration, production activation, code cleanup or C++ work begins from this report.

## Files, reproduction and preservation

All changes are new documentation/test/experiment files under `docs/testing/workload-fairness-f2a/`, plus this report. Standalone modules: `fairness_models.py`, `fictional_schedules.py`, `test_fairness.py`, `run_checks.py`, `analyze_results.py`, `measure_kernels.py`, `measure_original_fitness.py`, `audit_evidence.py`. JSON includes preservation baseline, all command/scenario/analysis/timing records, negative-test diagnosis, zero-target arithmetic control and manifest. The [manifest](testing/workload-fairness-f2a/manifest.json) lists every exact path and raw hash, excluding itself.

Final inventory: **39 new files (eight Python, one Markdown, thirty JSON)**. All38 artifact hashes verify, with the manifest excluded from its own hash list. All418 prior artifact entries independently verify. Privacy findings: zero; new-file syntax/whitespace and Git whitespace checks pass. Git's existing LF-to-CRLF advisory for protected preferences did not change its raw bytes; no normalization or staging occurred.

The audit compares all **1,806 pre-existing paths and23 academic files**, original GA/operator/scoring/RNG/roster/migration sources, protected settings/preferences, checkpoint/schedule/history trees, prior evidence and Git index/HEAD. Existing files modified: none. Both original local data modifications remain unchanged, unstaged and uncommitted. New evidence contains only fictional numerical/structural observations; credential/receipt/privacy/hash/whitespace checks apply. No academic/private preference records were parsed or exported. No database operation, installation, staging, commit or push occurred.

From the repository root in Windows PowerShell with the existing venv/Node:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/workload-fairness-f2a/run_checks.py backend
.\.venv\Scripts\python.exe -B docs/testing/workload-fairness-f2a/run_checks.py frontend
.\.venv\Scripts\python.exe -B docs/testing/workload-fairness-f2a/analyze_results.py
# Run timing commands after test processes finish, separately from profilers.
.\.venv\Scripts\python.exe -B docs/testing/workload-fairness-f2a/measure_kernels.py
.\.venv\Scripts\python.exe -B docs/testing/workload-fairness-f2a/measure_original_fitness.py
.\.venv\Scripts\python.exe -B docs/testing/workload-fairness-f2a/audit_evidence.py
```

Each command creates a fresh timestamped evidence directory; prior records are retained. Test workers inherit only whitelisted OS variables and bootstrap empty legacy schemas before original imports. Original data text parsing is then blocked; binary fingerprints stay genuine. Checkpoint child execution uses the existing reviewed fictional bootstrap. The audit writes only this new manifest and stops on mismatches without restoring existing files. No production optimization or scoring integration is implied by completion of F2A.
