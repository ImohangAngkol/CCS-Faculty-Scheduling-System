# F2G: experimental GA optimization effectiveness and performance diagnosis

**Final Git-preservation review: BLOCKED pending review of a concurrent documentation commit.** Computation, tests and evidence analysis are complete. At final review, HEAD had advanced from `4d9ee5b4a7d84ae9eb1194e5e5eeb131622a44d2` to `52d998a3c0eb50642424dca1b2a836c95ad68143` (`docs(research): record F2D-F2F experimental GA findings`, 2026-10-31 23:47:41 +08:00). It adds the three previously untracked F2D/F2E/F2F reports. This agent did not stage or commit them. All **2,075 baseline content files** still match, but the original raw `.git/index` hash and HEAD no longer match. The original baseline and fail-closed auditor are retained; no reset, restore or automatic rebaseline was performed. The manifest records this blocker and must not be described as a full preservation PASS.

This diagnostic uses the unchanged `f2f-operator-ga-laboratory/1` release. It distinguishes **algorithmic correctness**, **improvement on controlled fictional scheduling problems**, and **production readiness**. Test passes and safe execution alone do not establish optimization effectiveness. No production GA, scoring policy, workload setting, operator, source fingerprint, institutional provider or database was changed.

The [manifest](testing/fitness-policy-f2g/manifest.json) lists every new F2G file, artifact hash, command outcome, preservation check and limitation. Failed intermediate records are retained. The [F2F report](fitness-policy-f2f-operator-integration.md), its 50 executions and all earlier research evidence remain historical, byte-identical records.

## Research questions and preserved execution boundary

1. Were F2F's flat best-ever histories caused by already-good initialization, ineffective operators, inaccessible improvements, ties, collapsing diversity, cache errors or broken best-ever tracking?
2. Can the real experimental GA improve a known hard-valid suboptimal population, and when does it fail to reach a known better solution?
3. Which exclusive computational work explains its overhead? Which proposed changes could preserve ordering, identity, constraints, RNG and continuation?

Reviewed F2A-F2F reports/contracts, the original V1/V2 construction and selection paths, original and derived operators, F2D exact-score/cache contracts, F2E bridge/policy, F2F runner/checkpoint and prior benchmark source/evidence. No AGENTS.md was found. F2F's exact 64-path source set, import-only operator derivations and identity verified before investigation:

| Release | Preserved identity |
|---|---|
| F2F experimental GA | `ee72e369948d8511108bed3bba2b045f84c5649974be77170e0edb84c7eeeee7` |
| Current production V1 | `5dccfbbad87eb42de4bc4fdac2c7a468d857b485e8d6b2149f1f29a43f2ef0b1` |
| Current production V2 | `0821747e30eb56e9e4c070f369e733bc4b59ec184d2e2cb4c211ffa6fa5c1555` |

The [pre-edit baseline](testing/fitness-policy-f2g/preservation-baseline.json) covers **2,076 existing paths**, including all 23 academic paths, the Git index, original GA/scoring/RNG, migrations, six historical checkpoints, saved schedules and preceding research evidence. The two existing local tracked modifications, protected `faculty_preferences.json` and `ga_settings.json`, remain unchanged and unstaged. Existing untracked F2D/F2E/F2F work is also preserved. These protected files were binary-hashed, not parsed or printed.

All new code is diagnostic/test tooling under `docs/testing/fitness-policy-f2g/`; this report is the only new file outside that root. No new engine release is needed because **no verified engine source changed**. Python's monitoring facility observes original code objects; no GA function, scorer, factory or operator symbol is replaced. The experiment cannot enable production scoring or institutional authorization.

## Datasets, exact oracles and initial populations

All people, subjects, sections, rooms, preferences, fixed allowances and commitments are fictional F2A/F2F fixtures. These are IT prototype research controls, not supplied institutional records, IS faculty or full CCS coverage. Every domain contains **two faculty and one lecture room**. The names small/medium/larger describe offering counts in this study, not Phase 2's larger faculty cohorts.

| Domain | Offerings, two credits each | Teaching targets | Explicit initial population | Exhaustive eligible assignments |
|---|---:|---|---|---:|
| `small_equal` | 2 | `[24,24]` | Two all-first-faculty and two all-second-faculty schedules | 4 |
| `medium_unequal` | 6 | `[12,24]` | Same two/two concentrated recipe | 64 |
| `larger_surplus` | 8 | `[4,8]` | Same two/two concentrated recipe | 256 |
| `preference_swap` | 2 | `[24,24]` | Four copies of a balanced schedule with crossed, unsatisfied day preferences | 4 |

Lecture durations, half-hour grid, eligibility, available calendars, room type, fixed section commitment and hard teaching ceiling use unchanged original validation. Normal meeting geometry has at most two adjacent two-hour lectures per day. The preference domain fixes one lecture on Monday and one on Tuesday; the two fictional faculty prefer Tuesday and Monday respectively. Fixed non-teaching inputs produce Option B targets; those activities are not scheduled.

The oracle enumerates **all 328 eligible faculty-assignment combinations on these fixed geometries**. Every candidate passes original full admission and independent faculty/room/section conflict checks before scoring. A second calculation reconciles exact `25*D + other-seven-components`, with `D=sum((A-T)^2/T)` for positive targets. Complete offering coverage is mandatory. The recorded minima are known optima **within the declared fixed-geometry domain**, not an exhaustive institutional calendar search.

Initial populations are independently evaluated, sorted and encoded into **new, owned generation-zero F2F checkpoints** with the real population, exact history/counters and seeded RNG state. The existing decoder validates each one before actual evolution. The initial history records only generation zero; no earlier generations, searches or authority approvals are fabricated. No historical checkpoint is loaded as a writable seed. This is a deliberately supplied initial population, **not the natural constructor**. Natural-constructor controls are recorded separately.

This distinction matters: the supplied populations are deliberately suboptimal for the experimental objective. They are not necessarily suboptimal for legacy rounded-band scoring. Both engines receive the same fictional assignments, geometry, seed and budget, but raw policy scores have different meanings and are never compared as equivalent quality units.

Configuration: seeds **13, 29, 71**, population four, three generations, zero fresh additions, one attempt per crossover/mutation invocation, five constructor restarts and five candidate attempts. The unchanged outer crossover budget is `target*20` calls per generation. Experimental lambda **25**, `D_ONLY`, is an explicitly experimental F2E sensitivity configuration, not a production coefficient decision. Targets, zero-target Option A, maximum loads and all other academic rules are unchanged.

## Measurement and observer contract

The main study has **58 actual GA executions**: 24 uninstrumented timing trials; 24 matched operator/diversity diagnostic trials; three natural-construction controls; four separately profiled trials; two separately memory-instrumented trials; and one separate checkpoint-cost trial. The copy-frequency control is a separate input experiment. Execution `PASS` means the run completed its budget and passed hard validation, **not** that it improved or found an optimum.

- Imports, fixture preparation, supplied-population scoring and initial encoding occur before the engine window. Post-run original admission, independent conflicts and quality measurements occur afterward; their durations are retained separately.
- The F2F supplied-state engine window includes its existing checkpoint decode and entry validation plus evolution. The V2 control uses its existing in-memory state validation plus evolution. These entry mechanisms differ. The reported times are **entry-plus-GA timings**, not isolated search-only times or a pure scorer comparison. Separate checkpoint and profiler observations identify some entry costs; instrumented components are not subtracted from normal wall time.
- Diagnostics use CPython `sys.monitoring` events enabled only on the relevant code objects, with original call/return frames. The observer reads existing scores and signatures, never calls the scorer to obtain missing values. Legacy population scores come from observed original scorer returns. Exact per-generation mean, unique assignment signatures, unique graph hashes, fitness ties and operator outcomes are recorded. Graph hashes can distinguish model ownership/state that a logical schedule signature does not; assignment-signature diversity is reported separately.
- Operator invocations, actual inner attempts, returned children, assignment-changing returns and strict improvements are separate metrics. Invalid counts are **hard-gate rejection events**, not deduplicated invalid chromosome counts. A `None` return can mean no differing donor, too few assigned faculty, a tie, non-improvement or hard rejection; it is not automatically an invalid offspring.
- cProfile runs are separate from diagnostics and normal timings. Exclusive time is partitioned once by file/function category. Cumulative rows overlap and **must not be added**. A verification function's exclusive time excludes child hashing/I/O; a copying function's cumulative time includes recursion and called work.
- Tracemalloc and nominal 20 ms process sampling are used only in separate memory runs. Python allocation peak, sampled working set and private commit are distinct. Imports, the supplied initial state and protocol objects affect process memory. One memory sample per policy/domain is not a repeatable saving or leak measurement. No GC or allocator policy changed.
- Normal and instrumented runs must match logical populations, assignments, history, counters, diagnostics and actual final RNG state within each policy/seed. Cross-policy RNG paths may legitimately differ.

The monitoring API supports local code events and a callee frame at function start/return; events are released on exit and existing profile/trace hooks remain untouched. [Python monitoring documentation](https://docs.python.org/3.14/library/sys.monitoring.html). This is instrumentation on the pinned Python release, not a new dependency or a source-fingerprint workaround.

## Actual call paths and overhead hypotheses

The inspected path is:

```text
F2F engine.run
  -> parent/elite/survivor/best comparisons
  -> derived crossover and mutation -> bound scorer facade
     -> RunScorer.evaluate
        -> FictionalLegacyBridge.inspect
           -> deepcopy complete candidate graph
           -> complete offering-set check
           -> original ga_v2_engine.admit
              -> fixed-commitment checks
              -> validate_publication
                 -> payload_to_chromosome and component/resource validation
           -> full graph serialization/digest and workload projection
        -> identity-bound cache lookup
        -> cache miss: original components -> exact F2E workload/aggregation
        -> tagged exact score used by every ordering path
  -> entry/generation-boundary source and input verification
  -> independent best-ever copy and generation reporting
```

Relevant preserved sources: `backend/experiments/fitness_policy_f2f/{engine,scoring,checkpoint,release}.py`, F2E `legacy_bridge.py`/`policy.py`, `backend/services/{ga_v2_engine,ga_publication_service,chromosome_service,ga_checkpoint_service}.py`, original selection helpers and the two import-only derived operators. A cache hit deliberately **does not skip original full hard admission**. Fewer full scorer bodies therefore do not imply faster execution. The measured exclusive results below determine which hypotheses are supported; CPU cumulative shares are not assumed to be allocation shares.

## Results

**Completed:** 58 main full-GA executions plus six separate initial-copy-frequency controls, all hard-valid with complete offering coverage. There are 31 exact within-policy instrumented/uninstrumented state-and-RNG matches. These execution passes are distinct from optimization success. All three seeds are reported; no unsuccessful optimization trial was discarded.

### Known optima and improvement outcomes

| Domain | Supplied initial best (F2F) | Known fixed-geometry optimum | F2F improved / trials | F2F reached optimum / trials | Legacy improved its own score / trials |
|---|---:|---:|---:|---:|---:|
| small_equal | 3050/3 | 3025/3 | 3/3 | 3/3 | 0/3 |
| medium_unequal | 450 | 400 | 0/3 | 0/3 | 0/3 |
| larger_surplus | 300 | 75/2 | 0/3 | 0/3 | 0/3 |
| preference_swap | 3055/3 | 3025/3 | 3/3 | 3/3 | 3/3 |

F2F improved and reached the known optimum in **6/12** primary supplied-start timing trials. The six unequal/surplus starts did not improve despite strictly better hard-valid schedules. This is evidence of effectiveness on the two successful controlled cases, and a reproducible stagnation counterexample on the others. Legacy improvement counts refer to its own objective, not to the experimental score. Its supplied best was already favorable under legacy bands in several cases; win-rate comparison would be misleading.

Seed 71 experimental best-ever history, including generation zero:

| Domain | G0 | G1 | G2 | G3 |
|---|---:|---:|---:|---:|
| small_equal | 3050/3 | 3025/3 | 3025/3 | 3025/3 |
| medium_unequal | 450 | 450 | 450 | 450 |
| larger_surplus | 300 | 300 | 300 | 300 |
| preference_swap | 3055/3 | 3025/3 | 3025/3 | 3025/3 |

The improved cases first reached a better best in generation one. Reaching this enumerated optimum is more specific than merely observing a decreasing curve. A flat curve at the known minimum is successful attainment followed by stagnation; a flat curve above it is not convergence. No broad asymptotic convergence or institutional scheduling optimum is claimed.

All three natural-constructor controls were flat at their attained workload lower bounds. Retrospective reconciliation of all **15 F2F** timing starts also verifies minimum eligible workload score with zero other-seven penalty. Those old flat histories do not establish ineffective operators: the tiny initializer already supplied the final best objective value.

### Population and operator evidence

For the unequal-target seed-71 supplied case, assignment diversity was **2, 2, 1, 1** across G0-G3; exact unique-fitness counts were also 2, 2, 1, 1. The mean score decreased while best-ever remained 450, showing replacement of worse copies without discovery of a better best. All 180 crossover invocations had **zero inner attempts** and no invalid-gate events. The original three-way tournament selected distinct objects containing identical best assignments, leaving no differing donor. Mutation selected a single assigned faculty or swapped equal-credit offerings; it could not redistribute teaching units.

Aggregates over the three supplied-start diagnostic trials for each policy/domain:

| Domain | Policy | Crossover calls / inner attempts / strict children | Mutation calls / inner attempts / strict children | Hard-gate rejection events |
|---|---|---|---|---:|
| small_equal | legacy | 0 / 0 / 0 | 0 / 0 / 0 | 0 |
| small_equal | experimental | 371 / 218 / 9 | 9 / 9 / 0 | 0 |
| medium_unequal | legacy | 0 / 0 / 0 | 0 / 0 / 0 | 0 |
| medium_unequal | experimental | 540 / 0 / 0 | 9 / 9 / 0 | 0 |
| larger_surplus | legacy | 0 / 0 / 0 | 0 / 0 / 0 | 0 |
| larger_surplus | experimental | 540 / 0 / 0 | 9 / 9 / 0 | 0 |
| preference_swap | legacy | 0 / 0 / 0 | 0 / 0 / 0 | 0 |
| preference_swap | experimental | 540 / 180 / 0 | 9 / 9 / 6 | 0 |

Every returned child in these records changed assignments and strictly improved the required parental score. Returned-child counts are not best-ever-update counts: multiple accepted improvements can have equal scores and only one can establish a new best. All final and intermediate boundary populations remain hard-admitted. Exact population tie/comparison counts, per-generation means, unique graph/assignment counts and native cache-hit/miss histories are retained in the JSON rather than inferred from a no-child return.

### Initial-copy-frequency control

Both initial conditions have two distinct assignments and the same initial best. The control changes only their multiplicity: **two best + two worse** versus **one best + three worse**. It does not increase the unique-assignment count, and does not establish a universal diversity policy. With population four and tournament size three, removing the first parent object leaves another best copy in the original condition; the second tournament includes all three remaining objects and chooses it. With only one best copy, the selected pair must span the two assignments. Direct use of the actual selector recorded **0/100 versus 100/100 differing-assignment pairs**, while all pairs remained distinct objects.

| Domain | Seed | Initial best | Final best | Known optimum attained | Final teaching units |
|---|---:|---:|---:|---|---|
| larger_surplus | 13 | 300 | 75/2 | Yes | [6, 10] |
| larger_surplus | 29 | 300 | 75/2 | Yes | [6, 10] |
| larger_surplus | 71 | 300 | 50 | No | [4, 12] |
| medium_unequal | 13 | 450 | 400 | Yes | [4, 8] |
| medium_unequal | 29 | 450 | 400 | Yes | [4, 8] |
| medium_unequal | 71 | 450 | 400 | Yes | [4, 8] |

All **6/6** copy-frequency controls improved; **5/6** attained the fixed-geometry optimum. Surplus seed 71 ended at score50 / `[4,12]`, above optimum75/2 / `[6,10]`. That unsuccessful optimum search is retained without increasing its three-generation budget. It is not proof of infeasibility. These controls establish that original crossover can exploit reachable better assignments when donor variation remains accessible, but also show that correcting one initial-frequency trap does not guarantee optimum attainment.

### Observable scheduling quality, separate from fitness scale

| Domain | Legacy final units, seeds 13/29/71 | F2F final units, seeds 13/29/71 | Legacy common D | F2F common D |
|---|---|---|---|---|
| small_equal | [4, 0]; [4, 0]; [4, 0] | [2, 2]; [2, 2]; [2, 2] | 122/3, 122/3, 122/3 | 121/3, 121/3, 121/3 |
| medium_unequal | [12, 0]; [12, 0]; [12, 0] | [0, 12]; [0, 12]; [0, 12] | 24, 24, 24 | 18, 18, 18 |
| larger_surplus | [0, 16]; [0, 16]; [0, 16] | [0, 16]; [0, 16]; [0, 16] | 12, 12, 12 | 12, 12, 12 |
| preference_swap | [4, 0]; [0, 4]; [4, 0] | [2, 2]; [2, 2]; [2, 2] | 122/3, 122/3, 122/3 | 121/3, 121/3, 121/3 |

Every main/control final schedule has zero independently counted faculty/room/section conflicts, zero unassigned offerings and original explicit-eligibility coverage for all offerings. In the crossed-preference timing case, legacy ended at **50%** and F2F at **100%** of the two applicable lecture blocks on their preferred fictional days for all three seeds. This narrowly defined day metric is not an overall preference-satisfaction or specialization score. The primary unequal case still leaves one faculty unassigned under both policies; the successful `[4,8]` controls include both faculty but cannot remove the fixed 24-unit aggregate shortfall. Supply and academic eligibility are never changed to improve the score.

### Runtime distributions

Normal entry-plus-GA seconds, three fresh-process seeds per cell; sample SD, min and max are shown. This compares the documented entry contracts and actual search outcomes, not policy arithmetic in isolation. Imports and preparation are outside the window. Historical F2F ratios are not recalculated or overwritten from these different G3/supplied-start workloads.

| Domain | Policy | Mean | Median | Sample SD | Min | Max |
|---|---|---:|---:|---:|---:|---:|
| small_equal | legacy | 3.177067 | 3.196271 | 0.089733 | 3.079287 | 3.255644 |
| small_equal | experimental | 17.398885 | 17.204338 | 0.660905 | 16.857090 | 18.135228 |
| medium_unequal | legacy | 2.413306 | 2.475295 | 0.121075 | 2.273789 | 2.490834 |
| medium_unequal | experimental | 21.846063 | 21.574377 | 0.833067 | 21.182755 | 22.781056 |
| larger_surplus | legacy | 2.684839 | 2.673891 | 0.088753 | 2.602068 | 2.778558 |
| larger_surplus | experimental | 26.682187 | 26.923948 | 0.555507 | 26.046766 | 27.075847 |
| preference_swap | legacy | 2.375657 | 2.400942 | 0.128356 | 2.236540 | 2.489490 |
| preference_swap | experimental | 15.936876 | 15.866811 | 0.740305 | 15.234095 | 16.709723 |

No optimized engine exists to benchmark against this baseline. These timings demonstrate continuing experimental overhead, not a speedup. Three seeds, one machine, uncontrolled OS/cache conditions and different policy-dependent trajectories preclude a population-level superiority claim.

### Exclusive performance diagnosis

| Domain / policy | Profiled total s | Copy self % | Serialization / metadata self % | Exact arithmetic self % | Original fitness self % |
|---|---:|---:|---:|---:|---:|
| small_equal / legacy | 6.473188 | 38.0711 | 0.1723 | 0.0000 | 3.2189 |
| small_equal / experimental | 34.204540 | 36.6643 | 16.5923 | 0.0286 | 0.0221 |
| medium_unequal / legacy | 4.916871 | 28.4633 | 0.5540 | 0.0000 | 6.0735 |
| medium_unequal / experimental | 46.607368 | 36.4913 | 15.3663 | 0.0185 | 0.0122 |

In the small experimental profile, `FictionalLegacyBridge.inspect` ran412 times and contained24.787954s cumulatively; `payload_to_chromosome` also ran412 times and contained7.610197s. The original full scorer body ran only20 times. Exact workload calculation ran20 times with0.000343s exclusive work. Complete admission, deep copying and graph hashing therefore still recur on cache hits; reduced original fitness calls do not remove that work.

For that same profile, run-input verification ran eight times and contained4.592743s. This includes nested release checks, hashing and graph verification; its exclusive function-body category is much smaller. **Do not add these cumulative containers to copying, serialization or reconstruction totals.** The categories are disjoint exclusive classifications, while targeted-function cumulative values describe containment. Library/builtin work remains in `other`; cache and source-verification function self times are not their complete end-to-end costs. Native cProfile filename marker `~` can appear as a synthetic `backend/~` label; it is not an application source file.

Selection, crossover and mutation exclusive bodies, exact rational arithmetic and cache lookup self times are small relative to graph handling in these profiles. Their children can dominate their cumulative costs. This supports further ownership/reconstruction investigation, not removal of validation or a claim that the entire cumulative deepcopy share is removable. The measured exact arithmetic share does not justify compromising precision.

### Memory and checkpoint costs

Separate medium-domain memory runs at seed71, MiB:

| Policy | Python traced peak, not RSS | Sampled working-set peak | Sampled private-commit peak, not RSS |
|---|---:|---:|---:|
| legacy | 17.808 | 200.113 | 657.121 |
| experimental | 40.277 | 268.258 | 726.668 |

The tracer/sampler adds overhead; sampled peaks may miss spikes. Raw before/after and OS lifetime peaks are separate fields. Protocol differences and retained supplied-input objects affect process baselines. These two runs do not establish sustained retention, leak freedom or reproducible memory savings, and copying CPU time alone does not identify the largest allocator.

The separate small-domain checkpoint trial encoded and decoded the real final population, exact scores, history and RNG three times, with an externally supplied digest and owned temporary file writes/reads. All decoded logical states matched, and all three checkpoint hashes were identical. These costs are outside that trial's GA window:

| Operation | Mean s | Median s | Sample SD | Min s | Max s |
|---|---:|---:|---:|---:|---:|
| Encode and validate | 1.687113 | 1.666598 | 0.060363 | 1.639681 | 1.755059 |
| Decode and validate | 2.174755 | 2.181093 | 0.075756 | 2.096030 | 2.247143 |
| Owned file write + read | 0.025576 | 0.024609 | 0.002256 | 0.023965 | 0.028154 |

Checkpoint size: **526,458 bytes**. This is final-state encode/decode validation, not an additional resumed search trial. Actual split/uninterrupted and fresh-process continuation are covered by the unchanged F2F and V1/V2 regressions. No historical checkpoint, application store or institutional database is written.

The full raw statistics, targeted function locations/call counts, per-generation diagnostics and failure records are in the exact manifest inventory. No mathematical fitness policy, production weight or search operator was altered to obtain these observations.


## Diagnosis of the twelve flat-history hypotheses

| Hypothesis | Evidence and qualification |
|---|---|
| A. Already-good initialization | All 15 preserved F2F timing starts attain the exhaustive eligible workload lower bound and have zero remaining component penalty. Separate natural-construction controls test current behavior. This supports already-optimal objective values for those tiny fixtures, not global institutional effectiveness. |
| B. Search spaces too small | The new domains have 4/64/256/4 eligible assignments on fixed geometry. They are intentionally exhaustive controls; they cannot establish broad scheduling generality. |
| C. Insufficient selection pressure | Tournament size three is fixed in the unchanged selector. No pressure sweep was run. Selecting distinct objects can still select identical assignments; copy-frequency controls isolate that mechanism rather than declaring a universal best pressure. |
| D. Unchanged/ineffective crossover | Measured separately: useful returned children, no differing donor and non-improving returns are distinguished where exposed. A distinct parent object does not guarantee different alleles. |
| E. Unchanged/ineffective mutation | Equal-credit swaps preserve faculty unit totals, so neutral-preference mutation cannot improve D. The crossed-day fixture provides a real improving preference mutation. No mutation rule is changed to force an improvement. |
| F. Invalid offspring rejected | Original gates remain active; rejection event counts and final independent hard checks are recorded. No-child returns without a hard-gate event must not be called invalid offspring. |
| G. Frequent fitness ties | Exact per-generation unique fitness counts, tied pairs and experimental comparison events are measured. Ties do not by themselves prove a comparison bug. |
| H. Diversity collapse | Assignment-signature counts distinguish initial duplicate frequency from later loss of variation. Separate copy-frequency controls keep the selector/operators unchanged. |
| I. Cache conceals comparison defect | Repeated identical-identity/graph returns are checked for equal exact scores, exhaustive scores reconcile, and observed/unobserved full-state/RNG parity plus preserved F2F cache tests pass. This is evidence against the tested cache-defect hypothesis, not proof against every possible cache bug. |
| J. Best-ever malfunction | Known-improvable whole-GA tests produce strict best-ever updates; unchanged split/resumed continuation matches. Flatness on an attained minimum is not a best-ever failure. |
| K. Constraints block reachable improvements | Every known better fixed-geometry solution is independently admitted. Selection/operator reachability can still exclude it from a particular population; search stagnation is not mathematical infeasibility. |
| L. Objective fails to distinguish schedules | Exact oracle scores distinguish the supplied worse/better examples. Different valid timetables with equal workloads/preferences can still legitimately tie. No unsupported specialization objective is invented. |

## Safe opportunities and changes deliberately deferred

No optimized GA variant was implemented. The mathematical score, comparisons, checks, calendars, copied ownership graphs, original selection and operator mechanics remain unchanged. **There is no before/after engine-speedup claim.** Before/after quality means initialization versus final schedule under one policy.

Evidence supports separately qualifying these possibilities before any integration:

1. Investigate repeated complete reconstruction/graph serialization at cache hits. A safe alternative needs an independently reviewed immutable candidate representation, mutation invalidation, ownership checks and rejection/continuation parity. Skipping admission merely because a score is cached would weaken the current contract and is not proposed as a ready fix.
2. Reuse genuinely immutable policy descriptors/canonical metadata only after measuring their exclusive cost and proving binding/invalidation. Do not memoize live source hashes or authority findings in a way that removes required entry/boundary checks.
3. Profile copy ownership by stage before proposing selective copying. Do not prune resource calendars, share mutable best-ever state or change global deepcopy behavior. Earlier memory studies and current profiling are different measurements.
4. Evaluate diversity using supported frozen run parameters or explicit new experimental search contracts. The input-copy-frequency control is not a new production initialization policy. Genotype-aware parent exclusion, different mutation moves, relaxed strict-improvement admission or new immigrants would change search behavior and require separate approval/versioning. They were not implemented.
5. Retain exact rational ordering. No measured result justifies lossy floating conversion, relaxed identity checks, reduced validation, fingerprint spoofing or old-checkpoint reinterpretation.

Institutional roster integration, approved production weight/overload composition, zero-target exception authority and authorized-positive-zero-target arithmetic remain blocked/unresolved. Workload-exception authority is not inferred from Chair publication authority. Genuine providers, production publication and full CCS/IS coverage remain outside this study.

## Tests, failures, preservation and reproducibility

Fresh final tests: **342 Python tests** (14 new F2G, 178 F2D/F2C, 90 legacy/reporting, 33 F2F operator, 23 F2F checkpoint and four genuine current V1 mirror cases), plus **42 frontend contracts**. Final selections have zero failed, errors or skipped cases. V1 creates/verifies three real fictional checkpoint archives in an owned byte-identical source mirror. Original V2 and F2F current continuation, exact ordering, identity/cache isolation, best-ever ownership, RNG, hard constraints, incompatible contexts and zero-target safety remain under test. The six historical incompatible checkpoints remain untouched with their prior limitations.

Four unsuccessful intermediate records are retained in [diagnoses](testing/fitness-policy-f2g/intermediate-diagnostics.json):

- A new oracle incorrectly used the strict metadata codec on tuple-bearing schedule signatures. The schedule codec is now used; production codecs were not loosened.
- Two broad `sys.setprofile` pilot attempts hit the unchanged 300-second deadline. Filtering/caching within the Python callback was insufficient. Local code monitoring replaced the observer only. Those deadlines are **not measurements of uninstrumented GA performance**, and no completed outcomes are reconstructed for them.
- The first pytest bootstrap loaded another `run_checks.py` through fixture path setup and raised `AttributeError` before collection. The new wrapper now imports the preserved helper by exact path.

Early tooling hashes were recorded at completion; the corrected runner captures them before launching workers. Critical F2F source verification remained independent. All primary experiment workers pin the same executed F2G core-tool hashes. No assertion was disabled, no worker deadline increased, no dependency installed and no old evidence removed. Known warnings are the existing AnyIO rewrite warning and Starlette/httpx/BlockingPortal deprecations.

The final full auditor stopped at the `.git/index` mismatch before creating a success manifest. Separate read-only checks verify all 2,075 baseline content files, all 23 academic paths, protected preference/settings bytes, original production source fingerprints and **682 prior artifact entries**. HEAD/index preservation remains blocked by the concurrent commit documented above. New privacy checks cover complete/truncated encoded receipts, credential URIs, private keys and sensitive logs/headers. Evidence contains fictional structural/numeric observations, source/artifact hashes and sanitized test output. This agent performed no database connection, migration, institutional provider activation, staging, commit or push. Frontend checks are Node contracts, **not browser acceptance**; no UI change, production build or new browser scenario is claimed.

From the repository root, Windows PowerShell and the existing pinned Python virtual environment:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2g/run_study.py oracles
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2g/run_study.py qualification
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2g/run_study.py foundation
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2g/run_study.py legacy
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2g/run_study.py operators
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2g/run_study.py checkpoints
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2g/verify_v1.py
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2g/run_study.py frontend
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2g/run_study.py experiment
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2g/analyze_g.py
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2g/diversity_control.py
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2g/audit_evidence.py --verify
```

Use sequential benchmark commands on an otherwise quiet machine. Each worker has a 300-second cap; new timestamps and exclusive writes preserve earlier runs. Environments exclude credentials/database/approval variables. Workers bootstrap empty schemas before imports, reject institutional text reads, deny network/database operations and prevent writes to pre-existing repository paths. Only new owned evidence/temporary stores are writable. No new dependency or compiler is needed. **The final auditor currently fails closed on the preserved original Git baseline; this is intentional.** It must not be bypassed merely to obtain a success result. Review the concurrent documentation commit before authorizing an explicitly recorded Git-baseline decision. A fresh rerun needs a separately reviewed new manifest, not silent replacement of old evidence.

## Recommendation

**GO for further isolated search-diversity and larger mixed-component evaluation; NO-GO for production integration or an effectiveness claim for real CCS scheduling.** The controlled results separate a functioning exact-score GA from an effective general search strategy. Retain hard constraints, policy/source identity, exact ordering and checkpoint/RNG behavior in any future experiment. Approve a specific search-contract change before modifying protected selection/operator behavior. No next milestone, performance integration, C++ work or Git checkpoint was started.
