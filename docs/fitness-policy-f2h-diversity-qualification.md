# F2H: population diversity and convergence qualification

Status: **isolated computational qualification complete; production integration NOT authorized**. This report describes a fictional experiment, not a production search release, institutional evaluation or deployment approval. No combined strategy is activated. Current accepted HEAD is `52d998a3c0eb50642424dca1b2a836c95ad68143` on `main`.

## Scope and preserved baseline

Read the F2F/F2G reports, the separate F2G baseline-requalification addendum, actual experimental construction/selection/operators/replacement, exact-score admission/cache contracts, checkpoints and original V1/V2 boundaries. F2G's original blocked report is historical; its owner-authorized documentation-only Git transition was subsequently requalified. Neither document nor its old failed evidence is rewritten here.

The new [pre-edit baseline](testing/fitness-policy-f2h/preservation-baseline.json) records **2,189 pre-existing files**, including all 23 academic paths, the Git index, production source, preceding research/evidence and historical checkpoints/schedules. The two existing tracked local modifications are `backend/data/faculty_preferences.json` and `backend/data/ga_settings.json`; only their bytes are hashed. They are not parsed, printed, edited or staged. Existing untracked research is also protected.

| Identity | Value |
|---|---|
| Original current V1 | `5dccfbbad87eb42de4bc4fdac2c7a468d857b485e8d6b2149f1f29a43f2ef0b1` |
| Original V2 | `0821747e30eb56e9e4c070f369e733bc4b59ec184d2e2cb4c211ffa6fa5c1555` |
| Preserved F2F | `f2f-operator-ga-laboratory/1`, `ee72e369948d8511108bed3bba2b045f84c5649974be77170e0edb84c7eeeee7` |
| New isolated release | `f2h-diversity-ga-laboratory/1`, `d151b74789651cfe665a3307b417e53ac3ba8d7ec26a633b5a3ee77dbf430593` |

The new release verifies **77 source paths**: the preserved F2F set, its manifest and 12 new Python modules. Original operators are not edited. H's crossover and original-swap mutation are import-only derived copies verified against the original bytes. New selection/transfer/search behavior has a new release identity. Frozen strategy, supplied-pool graph digest, complete GA parameters, seed and policy configuration bind every run/checkpoint. No production module imports H or dispatches to it.

## What the baseline actually establishes

F2G's deliberately suboptimal primary trials improved in 6/12 runs; its copy-frequency control improved 6/6 and attained the known lower bound 5/6. F2F's earlier natural tiny-fixture starts already attained the workload lower bound; flat histories there were not failed convergence. These are different initial conditions, not interchangeable claims.

In the supplied unequal/surplus cases, the original tournament can choose distinct Python objects with identical faculty allocations. With two copies each of a better/worse allocation, the remaining better copy wins the second tournament. Same-allocation crossover and equal-credit faculty swaps do not redistribute teaching units; they can legitimately fail to improve target deviation. F2G's one-better/three-worse frequency control changes that selection path without changing scoring. H reproduces the original release and investigates mechanisms separately.

Duplicates enter or survive at several separate boundaries: construction has no uniqueness obligation; the selector excludes the first **object** rather than all matching allocations; elitism deep-copies elites/non-elites; the candidate pool carries parent copies, elites and another independent best-ever copy; valid operator returns need not be globally novel; and fitness-only truncation can retain several better copies while discarding a worse but different allocation. Independent copying is required for mutation/best-ever ownership and is not itself a defect. Removing copies or sharing mutable calendars is not a diversity fix attempted here.

All H timing trials use newly owned, explicitly supplied hard-valid populations. This is not an assertion about the production roster or the performance of original natural initialization. H's S0 has the original F2F search mechanics with the new input/measurement contract. A full actual F2F/S0 differential test compares assignments, population, best-ever, exact histories and RNG. Additional saved-quality/history and actual-release reproduction checks are specified below.

## Deterministic diversity measurements

`backend/experiments/fitness_policy_f2h/diversity.py` defines two equivalences on **already admitted** chromosomes:

- Faculty-allocation genotype: sorted `(offering code, section identity, faculty identity)` tuples.
- Complete timetable assignment: those tuples plus component kind, room identity and sorted day/start/end meetings. Lecture and laboratory components remain distinct. Two separate object graphs with the same assignments are one chromosome under this rule. Cached scores and object addresses do not define diversity.

SHA-256 of canonical tuples is a stable label, not a feasibility or authority proof. Invalid/incomplete candidates are rejected before measurement. Reordering the model list or deep-copying it does not change either identity. Moving a meeting can change complete-assignment identity without changing faculty genotype. Initialization/selection/replacement deliberately target the latter because it is the redistribution bottleneck under study.

Generation zero and every completed generation record unique complete assignments, unique faculty genotypes, duplicate percentages, mean pairwise normalized genotype Hamming distance, distinct exact fitness values, exact mean/best fitness, stagnation duration and best-ever update frequency. Every fraction is explicit numerator/denominator data. No metric is added to fitness.

Effective crossover means returned fully admitted children whose faculty genotype differs from **both** parents, divided by crossover invocations. Effective mutation means an admitted return absent from the input pool's genotype set, divided by mutation invocations. These are cumulative invocation-level metrics, not inner swap-attempt rates. Parent similarity is matching faculty genes / compared genes over selected pairs. Offspring-pool similarity compares admitted returns with the recorded parent/input pool; mutation does not claim knowledge of the original helper's randomly selected parent. Empty denominators are explicitly zero, not evidence of successful diversity.

## Individually frozen strategies

| Code | Intervention | Bounds and limits |
|---|---|---|
| S0 | Original F2F tournament, derived original operators and fitness-sorted replacement | Common H input contract and pure metrics only; no diversity intervention. |
| A | Keep the first fitness-ranked representative per faculty genotype during initialization; draw additional original-constructor candidates | At most four uniqueness draws, each using the normal bounded construction path. If uniqueness is exhausted, fill from existing valid duplicates. The diagnostic says the space limit is unknown, not that the problem is infeasible. |
| B | Original first-parent tournament; restrict the second tournament to other faculty genotypes | No different genotype means an explicit no-donor count and bounded crossover stop. It does not manufacture invalid variation or loop indefinitely. |
| C | Replace the mutation proposal with one owned offering transfer to a different explicitly eligible cohort member | Original meeting geometry/rooms remain; no preassigned offering is moved. Original complete admission, workload ceiling and zero-target permission/math checks precede scoring. Only a strict exact-score improvement is returned. |
| D | After one completed stagnant generation, request one original-constructed feasible candidate | At most one restoration attempt per run, with the existing finite candidate/restart bounds. An exhausted restoration does not invalidate the retained feasible best. |
| E | Fitness-sort survivors, retain one per faculty genotype, then fill remaining slots with valid duplicates | Final population is sorted again. No unqualified minimum uniqueness is required. Best-ever remains independent and exact. |

All five interventions are separate; no A+B+C+D+E combination is tested or recommended. Common parameters are population 4, three generations, zero ordinary fresh chromosomes, one inner crossover attempt, one mutation attempt, five constructor candidate attempts and five constructor restarts. Each run always executes its configured generation budget, including when it starts at or reaches the known lower bound.

**Budget qualification:** A and D intentionally add bounded construction effort. They do not have equal evaluation counts to S0/B/C/E. Evaluation requests, component evaluations, source checks, constructor attempts and runtime accompany quality results. A better A start is an initialization result, not an evolved improvement. D's constructed candidate can help without showing that crossover itself became more effective. No matched-evaluation-budget superiority is claimed.

## Fictional domains, seeds and oracle

These reuse F2G's immutable documented domains. Every domain has two fictional faculty, one lecture room and explicit eligibility for the declared offerings; section commitments, supported durations, grid, room type and maximum-load admission are preserved. Names here indicate offering count, **not Phase 2's 6/12/24-faculty scaling scenarios**. They establish neither full IT nor CCS/IS population coverage.

| Domain | Two-credit offerings | Individual teaching targets | Supplied population | Known exact objective lower bound |
|---|---:|---|---|---:|
| small_equal | 2 | 24,24 | Two all-first and two all-second allocations | 3025/3 |
| medium_unequal | 6 | 12,24 | Same multiplicity; initial best 450 | 400 |
| larger_surplus | 8 | 4,8 | Same multiplicity; initial best 300 | 75/2 |
| preference_swap | 2 | 24,24 | Four copies of a balanced crossed-day-preference allocation | 3025/3 |

Working score remains the approved **experimental** F2F contract: `25 * sum((assigned-target)^2 / target)`, plus the unchanged other seven component penalties, D_ONLY mode. It is not a newly approved production weight. Fixed hypothetical non-teaching allowances reduce Option B targets; non-teaching activities are not scheduled. No new specialization data or objective is invented.

All 328 previously enumerated fictional allocations (4+64+256+4) are hash-verified and their scores, deviations and minimum recomputed from saved evidence. They are **reviewed oracle evidence, not 328 newly executed GA runs**. Their fixed-geometry optima achieve the least discrete target-weighted deviation with zero other penalties; the nonnegative-other-term objective lower bound also applies when A/D's original constructor chooses another valid geometry. This is not an exhaustive enumeration of all timetable arrangements or a theorem about institutional feasibility.

Seeds **13, 29, 71** and all six strategies were declared before measurement. Strategy order rotates across seeds; every worker is a fresh Python process. There are three different-seed ordinary observations per domain/strategy, not three repeats of a single deterministic input. Means/medians/sample SD/min/max are descriptive seed-and-runtime variation; they are not statistical significance or a success probability of one.

## Measured ordinary-trial results

All 72 ordinary trials completed and passed final full admission plus independent faculty/room/section conflict checks. All have zero unassigned offerings. Every best-ever history is monotone non-increasing. Trial PASS does not mean an optimum was found.

| Strategy | Improved after initialization | Starts at known bound | Final known bound | Completed suboptimal |
|---|---:|---:|---:|---:|
| S0 | 6/12 | 0/12 | 6/12 | 6/12 |
| A | 3/12 | 9/12 | 11/12 | 1/12 |
| B | 12/12 | 0/12 | 9/12 | 3/12 |
| C | 9/12 | 0/12 | 6/12 | 6/12 |
| D | 12/12 | 0/12 | 12/12 | 0/12 |
| E | 6/12 | 0/12 | 6/12 | 6/12 |

These are pooled descriptive counts across four different domains, not identically distributed estimates of general success probability. A started nine workload trials at the bound; calling their flat histories failed evolution would be incorrect. B improved every deliberately suboptimal start but missed the surplus optimum in all three seeds. C reached the same total number of optima as S0 while changing which domains succeeded. E had no quality benefit on these cases. D attained all twelve bounds with explicitly additional bounded construction effort.

Times below are seconds, with three different-seed observations in each cell. Exact final scores are in seed order 13/29/71. The full records retain per-generation fitness, diversity, parent/offspring similarity, requests, actual component evaluations, cache counts and constructor attempts.

| Domain | Strategy | Final scores (13/29/71) | Mean s | Median s | Sample SD s | Min-max s |
|---|---|---|---:|---:|---:|---:|
| small_equal | S0 | 3025/3, 3025/3, 3025/3 | 13.5426 | 13.8537 | 0.7331 | 12.7053-14.0689 |
| small_equal | A | 3025/3, 3025/3, 3025/3 | 16.4944 | 15.7879 | 2.1770 | 14.7584-18.9370 |
| small_equal | B | 3025/3, 3025/3, 3025/3 | 13.8741 | 13.8993 | 5.0750 | 8.7866-18.9365 |
| small_equal | C | 3025/3, 3025/3, 3025/3 | 13.7683 | 12.2891 | 2.6960 | 12.1357-16.8801 |
| small_equal | D | 3025/3, 3025/3, 3025/3 | 14.4912 | 14.3263 | 3.1031 | 11.4738-17.6733 |
| small_equal | E | 3025/3, 3025/3, 3025/3 | 16.5105 | 16.7703 | 1.3722 | 15.0270-17.7342 |
| medium_unequal | S0 | 450, 450, 450 | 15.0421 | 14.2073 | 2.2298 | 13.3502-17.5689 |
| medium_unequal | A | 400, 400, 400 | 24.0484 | 22.0890 | 4.1437 | 21.2478-28.8084 |
| medium_unequal | B | 400, 400, 400 | 17.2095 | 15.9429 | 2.3508 | 15.7636-19.9219 |
| medium_unequal | C | 825/2, 400, 400 | 15.5072 | 13.6083 | 3.3609 | 13.5256-19.3878 |
| medium_unequal | D | 400, 400, 400 | 17.2631 | 17.9094 | 1.3791 | 15.6795-18.2004 |
| medium_unequal | E | 450, 450, 450 | 15.8886 | 16.1137 | 0.8258 | 14.9736-16.5786 |
| larger_surplus | S0 | 300, 300, 300 | 24.2516 | 27.2057 | 5.6457 | 17.7418-27.8074 |
| larger_surplus | A | 75/2, 75/2, 75/2 | 38.4579 | 38.7905 | 1.6860 | 36.6304-39.9528 |
| larger_surplus | B | 50, 50, 50 | 31.3722 | 31.7283 | 2.0559 | 29.1614-33.2268 |
| larger_surplus | C | 275/2, 50, 75/2 | 28.4018 | 26.9459 | 3.5325 | 25.8299-32.4296 |
| larger_surplus | D | 75/2, 75/2, 75/2 | 28.3493 | 31.7882 | 7.3489 | 19.9114-33.3482 |
| larger_surplus | E | 300, 300, 300 | 27.2765 | 26.7586 | 1.6252 | 25.9734-29.0975 |
| preference_swap | S0 | 3025/3, 3025/3, 3025/3 | 18.0955 | 17.9523 | 1.8690 | 16.3022-20.0320 |
| preference_swap | A | 3040/3, 3025/3, 3025/3 | 19.1049 | 18.2210 | 1.5731 | 18.1726-20.9212 |
| preference_swap | B | 3025/3, 3025/3, 3025/3 | 17.6545 | 17.8260 | 0.8827 | 16.6987-18.4389 |
| preference_swap | C | 3055/3, 3055/3, 3055/3 | 16.1972 | 16.4628 | 0.6399 | 15.4673-16.6615 |
| preference_swap | D | 3025/3, 3025/3, 3025/3 | 17.8728 | 16.8138 | 2.4139 | 16.1695-20.6353 |
| preference_swap | E | 3025/3, 3025/3, 3025/3 | 18.3339 | 18.4015 | 0.5466 | 17.7566-18.8435 |

All domains are known feasible. No measured trial was classified mathematically infeasible or unsupported. Expected infeasible-input, malformed-candidate, bounded-search and unsupported zero-target behavior are tested separately. Starting below target supply does not make the academic schedule infeasible; it leaves unavoidable underload.

In the unequal case, S0/E retain `[0,12]` units; B/A/D attain `[4,8]`. C produces `[2,10]`, `[4,8]`, `[4,8]`. In surplus, S0/E retain `[0,16]`; B ends `[4,12]` for all three seeds, C ends `[2,14]`, `[4,12]`, `[6,10]`, and A/D attain `[6,10]`. All targets and offered units remain fixed. Zero-assignment faculty are included in D and coverage metrics.

B first improves at generation 1 in every domain/seed, but that is not the same as reaching the optimum. D first improves at generation 2 in the unequal/surplus cases and generation 1 in the small/preference cases. A has no post-initialization improvement in its nine already-optimal workload starts. All exact first-improvement and full objective progressions are archived; three generations do not establish long-run convergence.

C has a real search-neighborhood limitation in the preference case. The wrong balanced allocation has workload term `3025/3` plus day penalty 10, total `3055/3`. A one-offering transfer keeps hard validity but yields workload term `3050/3` plus day penalty 5, total `3065/3`, which is worse. A simultaneous eligible balanced swap preserves the lower workload term and removes the day penalty, attaining `3025/3`. Transfer-only strict-improvement mutation cannot take that two-offering move. Replacing the original mutation with it is therefore **not recommended**. No scoring rule is changed to conceal this result.

A also misses the preference optimum for seed 13 (`3040/3`, 50% of the two applicable blocks preferred) while the original S0 reaches `3025/3` and 100%. Its new constructor geometry, allocation multiplicity and the fixed-geometry variation neighborhood must be qualified together. A targeted actual-state replay below checks this failure rather than assuming that additional unique genotypes always help.

Saved ordinary records: [predeclared plan](testing/fitness-policy-f2h/20261101T012250786617+0800-study/plan.json), [89-run completion](testing/fitness-policy-f2h/20261101T012250786617+0800-study/completion.json) and [independent saved-result analysis](testing/fitness-policy-f2h/20261101T012250786617+0800-study/analysis.json).

### Interpreting diversity and unsuccessful strategies

Replacement E illustrates why a count alone is insufficient. In all three unequal-target trials its genotype history is `2,2,1,1`, its selected-parent similarity is 1, and effective crossover/mutation novelty is zero. The first sorted pool contains three copies of the better allocation and one worse allocation. On the next generation, the preceding 50% non-elite parent truncation removes the worse genotype before replacement sees candidates. E can retain only genotypes present in its admitted candidate pool; it cannot recreate the lost allocation. Its duplicate-fill rule and original tournament therefore do not solve the F2G stagnation mechanism.

Conversely, B can legitimately end with one genotype after attaining an optimum. Reduced diversity is not by itself a regression, and maintaining four distinct assignments is not a hard academic requirement. The independently eligible single-genotype test retains a valid size-four population by bounded duplicate fill; B reports no donor instead of looping or inventing a faculty assignment. That proves only one **faculty genotype** in this restricted fixture, not one possible timetable.

The separate [targeted diagnostic](testing/fitness-policy-f2h/20261101T021923505231+0800-diagnostic/command.json) continues real E/unequal and A/preference states through three checkpoint stages each. Both final population/best/history/metrics/counters/RNG hashes equal their ordinary trial. E's copy frequencies are exactly `[2,2] -> [3,1] -> [4] -> [4]`. A's seed-13 best changes from the original Monday/Tuesday geometry to Saturday/Monday at generation 1 and retains a five-point day penalty. Neither faculty prefers Saturday; the existing faculty-swap neighborhood cannot turn that Saturday meeting into a preferred day. This is a soft-objective reachability/selection issue in the experimental initial pool, not a hard-invalid schedule or altered fitness.

Four additional deterministic score evaluations (original, two individual transfers and the balanced swap) reproduce the C preference barrier numerically: both transfers score `3065/3`, while the swap scores `3025/3`; all are independently hard-conflict-free. These two targeted state replays and neighbor evaluations are **separate from the 89 measured executions**, not extra independent timing samples. No phenotype is repaired, time slot changed or result substituted in the measured experiment.

## Timing, memory and call-path interpretation

The ordinary H window includes owned supplied-pool cloning, initialization validation, strategy work, three generations and pure boundary metrics. Fixture/scorer preparation, final independent quality checks and persistence are measured separately or excluded. No cProfile, tracemalloc or process-memory sampler runs in ordinary timing windows. Four current F2F reproductions and one separate F2F allocation run retain its original checkpoint decode/entry mechanism; those times are **not** a pure H-overhead or algorithm speed comparison.

Six separate medium/seed-71 cProfile runs quantify exclusive costs and overlapping cumulative call boundaries. Copying, exact arithmetic, canonical serialization, cache operations and admission/reconstruction use the preserved disjoint filename/function classification; total exclusive categories sum to the measured profile total. Initialization/constructor, selection, crossover, mutation, replacement and metrics call rows expose call counts and exclusive versus cumulative time. Cumulative rows are not summed or assumed removable. All `fractions.py` work includes exact metric arithmetic as well as fitness; it is not a fitness-arithmetic-only attribution.

Six separate H allocation runs and the separate F2F reproduction use tracemalloc plus 20 ms Windows process-memory sampling. Python allocation peak is **not total process RAM**. Working set and private commit are distinct OS observations. These are single seed-71 allocation observations per strategy, not replicated memory-saving claims. Instrumented elapsed times are not mixed into normal timing distributions. Fresh-process cold entry is controlled; no within-process warmed throughput claim is made.

Cache hits still perform original full hard admission and frozen/source verification before reuse. A high hit rate is not evidence that reconstruction/copying became cheap. This milestone does not optimize copying, serialization, validation, fitness arithmetic or production performance.

### Separate medium-profile observations

Each row is a separately profiled seed-71 execution, not normal engine timing. Copy/serialization columns are **exclusive** classified time; overlapping cumulative stage rows remain in the raw artifacts. Cache requests are not constant-cost operations.

| Strategy | Profile total s | Copy exclusive s | Canonical serialization exclusive s | Exact-arithmetic class s | Evaluation requests | Component evaluations | Cache hits |
|---|---:|---:|---:|---:|---:|---:|---:|
| S0 | 47.8055 | 16.9630 | 7.1001 | 0.0087 | 444 | 7 | 437 |
| A | 69.1244 | 26.4717 | 10.2036 | 0.0167 | 589 | 39 | 550 |
| B | 54.5240 | 20.8079 | 9.5848 | 0.0091 | 315 | 20 | 295 |
| C | 52.5746 | 19.4229 | 7.5683 | 0.0104 | 419 | 12 | 407 |
| D | 57.1029 | 21.4718 | 8.5767 | 0.0096 | 507 | 11 | 496 |
| E | 49.3333 | 17.6176 | 7.3195 | 0.0088 | 456 | 7 | 449 |

All six profiled final states match ordinary same-seed actual population, best-ever, history, strategy/metric state, counters and RNG. B reduces total requests yet introduces more scored graph variants and higher copying cost in this profile. That observation does not establish the isolated reason for the cost difference or an end-to-end speedup. E retains the original plateau while adding requests. Exact arithmetic remains a very small exclusive classification here; no result justifies lossy comparisons, bypassed admission or C++ work.

### Separate medium allocation observations

All figures below are MiB except instrumented elapsed seconds. These are one fresh-process seed-71 observation per strategy. Working set is a sampled resident measure; private commit is not RSS. The old F2F row has a different checkpoint-entry/preparation boundary and is retained as a reproduction, not a clean H-overhead comparison.

| Strategy | Python traced peak (not RSS) MiB | Sampled working-set peak MiB | Sampled private-commit peak MiB | Instrumented seconds (not normal timing) |
|---|---:|---:|---:|---:|
| F2F | 41.344 | 273.156 | 733.156 | 102.514 |
| S0 | 39.796 | 267.648 | 726.762 | 106.256 |
| A | 42.676 | 272.941 | 732.109 | 169.465 |
| B | 50.588 | 291.898 | 752.574 | 139.758 |
| C | 40.523 | 267.332 | 726.645 | 109.532 |
| D | 39.836 | 268.648 | 728.625 | 135.508 |
| E | 39.072 | 268.262 | 727.000 | 89.499 |

B's observation has a higher traced peak than S0 (50.588 versus 39.796 MiB), despite fewer scorer requests. This is another reason not to equate request counts with cost. D's traced peak is close to S0 in this observation; it is not a replicated memory-saving result. Process measurements include interpreter, libraries, native/allocator state and retained fixtures. Their difference from traced allocations is not evidence of a leak. No process allocator, production GC setting or copy-ownership rule is changed.

All twelve H profile/allocation outcomes match ordinary same-seed actual logical state. Five fresh actual F2F executions match their preserved F2G output/history/counters/RNG. Twelve S0 ordinary outcomes match saved exact quality and generation fitness. The [analysis](testing/fitness-policy-f2h/20261101T012250786617+0800-study/analysis.json) independently recomputes those comparisons and the 328 oracle allocation scores.


## Checkpoints, exact ordering and failure handling

The separate `f2h-diversity-ga-checkpoint/1` format binds the H release, input/initial-pool and evaluation identity, strategy/budgets, population, independent best-ever, exact scores/history, scorer counters, boundary cache policy, diversity/operator history, stagnation/restoration state and actual RNG state. It retains passive bounded graph decoding, mandatory externally pinned SHA, hard admission, source/input verification and mutable graph isolation. Old F2F checkpoints are not reinterpreted as H checkpoints.

Six actual split/uninterrupted cases verify the same final population/best, histories/counters, strategy/restoration state and RNG for S0 and A-E; a fresh-process continuation verifies actual state rather than replayed initialization. Missing pins, source/context/seed/strategy changes, altered scores/history/search metrics and invalid graphs fail closed. Mutation of a current population member does not alter independent best-ever. The original current V1 mirror creates/verifies three owned fictional archives using 164 byte-identical source paths and passes four real creation/load/continuation cases. Original V2 and F2F regressions remain separate.

The six old incompatible historical checkpoints remain byte-identical with their existing rejection policy. No old fingerprint is spoofed, disabled or migrated. Caller global RNG is leased/restored by the H runner; within-run RNG paths intentionally differ between new strategies, while fixed-strategy same-input continuation remains deterministic. No global function replacement, production GC or allocator change is introduced.

Zero-target assignments without approval fail closed. An explicitly fictional valid exception still stops at the preserved unsupported positive-zero-target arithmetic boundary; H does not invent its formula or institutional workload-exception authority. Original room/faculty/section/time/eligibility/coverage restrictions are never relaxed to manufacture diversity.

Two intermediate harness failures are retained: shared exclusive-create outcomes paths after a passing continuation assertion, corrected with separate per-worker directories; and a post-run result serializer using an absent public release attribute, corrected to the existing stored attribute. The failed trial has no admitted measurements and its unchanged complete plan was repeated. Neither correction changes the pinned H release, old source or mathematical result. There are no hidden retries, discarded unfavorable seeds or erased diagnostics.

## Tests and evidence scope

Final unique selections: **375 Python cases passed** (47 new H identity/strategy/admission/checkpoint cases, 178 F2D/F2C foundation, 90 original legacy/reporting/V2, 33 F2F operator, 23 F2F checkpoint and four current V1 mirror cases); **42 frontend Node contracts passed**. The final selections have no failed/errors/skipped cases. The extra early passing S0 and incomplete evidence-bookkeeping attempt are historical, not extra unique tests.

Warnings are retained: pytest cannot rewrite the already bootstrap-imported anyio plugin; legacy imports report Starlette's deprecated httpx TestClient usage and anyio's deprecated BlockingPortal alias. No dependency is installed or changed. These do not substitute for warning-free future qualification.

No application UI changed. Node contracts are **not browser acceptance**; no new browser, institutional HTTP or PostgreSQL acceptance scenario, production build or genuine authority result is claimed. Prior D15 disposable PostgreSQL acceptance/evidence and retained database are untouched. No database connection is made in H workers; their audit guard rejects network/database events and repository writes outside their new evidence root. Test/checkpoint scratch files use owned temporary directories.

## Files, preservation and remaining blockers

New experiment code is confined to `backend/experiments/fitness_policy_f2h/` (12 Python modules plus its manifest), with standalone support/tests/runner/analyzer/auditor and sanitized records under `docs/testing/fitness-policy-f2h/`, and this report. The [verification manifest](testing/fitness-policy-f2h/manifest.json) contains the exact new-file inventory, self-excluding hashes, source identities and complete result reconciliation. No pre-existing source, test, migration, data, old research report or evidence is edited.

Final audit verifies all **2,189 baseline files**, all **23 academic paths**, **793 prior artifact entries**, the original V1/V2 fingerprints, preserved F2F identity and the new 77-path H release. The Git HEAD and raw index hash remain unchanged, with no staged changes. Existing protected preference/settings modifications remain byte-identical and unstaged; pre-existing untracked research remains intact. Current Git whitespace and new text/privacy checks pass. The pre-existing owner-committed F2F report's 198 CR-CR-LF whitespace warnings remain documented and untouched. Final verification is reproducible with the manifest command below; a mismatch must stop signoff rather than repair a baseline.

There are no production/application file edits. Exact inventory is in the manifest: the new experiment package, ten standalone support/runner/test/analyzer/auditor/V1 tools plus the additional targeted-diagnostic tool, this report and all successful/failed evidence. No PostgreSQL operation, dependency installation, staging, commit, push, institutional provider activation or next milestone occurs.

## Recommendation and remaining research limits

**GO only for a separately authorized larger fictional, matched-evaluation-budget search qualification. NO-GO for production integration or a claim of general optimization superiority.**

- B is a useful next qualification candidate: it directly addresses genotype-identical parent selection, improves all twelve suboptimal starts, and preserves the original preference swap. It still misses all three surplus optima under the current three-generation/one-attempt budget. More generations and larger, more constrained cohorts require fresh evidence.
- D is promising as bounded stagnation recovery: it reaches 12/12 known bounds here, with additional constructor work and runtime. Compare it with equal-effort ordinary fresh-candidate controls before attributing superiority to the trigger. It does not prove crossover convergence or infeasibility handling on real semesters.
- A reaches 11/12 bounds but spends extra initialization work and harms the preference case for one seed. Test allocation diversity with controlled meeting geometry before considering it as a default. More unique genotypes alone is insufficient.
- C is **NO-GO as a replacement for original mutation**: it helps workload redistribution but loses all three crossed-preference improvements. A future separately versioned move portfolio could be investigated; none is implemented here.
- E is **NO-GO in this replacement-only form**: it adds cost without improving the studied plateau. Fixing an upstream selection mechanism is more directly supported than layering a duplicate count onto the same candidate pool.

No combination has been qualified. Next work should predeclare more seeds, budgets and time-to-target criteria; include larger faculty/section/room cohorts, laboratory patterns, restrictive eligibility, room/faculty closures and mixed preference tradeoffs; compare matched construction/evaluation effort; and replicate allocations across processes/seeds. Keep full hard admission, exact comparison, independent best-ever, caller RNG restoration, same-strategy continuation and explicit source/input identities. Do not tune only against these four controls or start that work automatically.

Institutional cohort qualification, actual authority providers, zero-target positive-assignment arithmetic and calibration of the experimental policy remain unresolved deployment boundaries. IT is the current prototype scope; full CCS/IS coverage is not established. No result here establishes thesis/adviser approval, institutional readiness or genuine publication authority. Production institutional activation remains **BLOCKED**.

## Reproduction in Windows PowerShell

From the repository root, use the existing environment; install nothing:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2h/audit_h.py --verify
```

The command above is the repeatable integrity/result review, without GA execution. To reproduce tests or measurements, each command creates a new timestamped evidence directory and refuses to overwrite old records:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2h/run_h.py metrics
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2h/run_h.py operators
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2h/run_h.py regressions
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2h/verify_v1.py
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2h/run_h.py study
$hStudy = Get-ChildItem -LiteralPath docs/testing/fitness-policy-f2h -Directory -Filter '*-study' |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'completion.json') } |
    Sort-Object Name | Select-Object -Last 1
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2h/analyze_h.py $hStudy.FullName
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2h/run_h.py diagnostic
```

Do not rerun `prepare` against the already sealed release or overwrite an existing analysis/manifest. New runs require a separate reviewed evidence addendum/inventory; `audit_h --verify` intentionally rejects an unreviewed expanded inventory. Each worker has a 300-second deadline and the batch stops at its first failure. No D16/D15 service or database is started, no Git mutation is performed, and no next milestone is automatically begun.
