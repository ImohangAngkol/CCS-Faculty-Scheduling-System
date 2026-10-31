# F2F: isolated operator-aware GA integration

Recorded 2026-10-31, Asia/Manila, on `main` at `4d9ee5b4a7d84ae9eb1194e5e5eeb131622a44d2`. This is an **actual experimental GA**, with evolving populations, original tournament/elitism helpers, derived crossover/mutation, exact fitness ordering and population/RNG checkpoint continuation. It is not the F2E candidate-stream replay. No production route calls it, and no production fitness policy or institutional authority was activated.

The experiment is limited to fictional IT prototype fixtures. F1's authoritative roster dependency, full CCS coverage, production fitness weights, zero-target exception authority and positive-zero-target arithmetic remain unresolved. Passing these tests establishes the isolated execution contract, not adviser approval, institutional acceptance or production readiness.

## Preserved boundary and release identity

Before edits, the working tree already contained local modifications to `backend/data/faculty_preferences.json` and `backend/data/ga_settings.json`, plus untracked F2D/F2E work. Those changes were preserved. The new [preservation baseline](testing/fitness-policy-f2f/preservation-baseline.json) covers **1,980 existing paths**, including all 23 academic data paths, the Git index, original GA code, migrations, retained checkpoints, schedules and prior evidence. Its comparison uses file bytes without printing protected data. The final [manifest](testing/fitness-policy-f2f/manifest.json) is self-excluding and lists every new F2F path and artifact hash.

| Identity | Value |
|---|---|
| Experimental GA release | `f2f-operator-ga-laboratory/1` |
| Release digest | `ee72e369948d8511108bed3bba2b045f84c5649974be77170e0edb84c7eeeee7` |
| Pinned source paths | 64, including F2E sources/manifest and eight F2F Python modules |
| Underlying F2E scoring release | `f2e-fitness-laboratory/1.1` |
| F2E digest | `9bf3dd73296e2de27e94c7c80b97a78bb17050d6db5d3b2b5b64ce3fa1ad6fe2` |
| Preserved V1 engine fingerprint | `5dccfbbad87eb42de4bc4fdac2c7a468d857b485e8d6b2149f1f29a43f2ef0b1` |
| Preserved V2 engine fingerprint | `0821747e30eb56e9e4c070f369e733bc4b59ec184d2e2cb4c211ffa6fa5c1555` |

`release.py` verifies the exact source set, bytes, Python version, pinned F2E identity and operator derivations. The source manifest excludes itself from its source digest and is independently anchored by the owned laboratory control record. This local integrity anchor is not an institutional signature. Existing V1/V2 fingerprint functions are neither replaced nor spoofed.

The two **new** operator copies are byte-identical to the original `Swap.py` and `mutation.py` except for one scorer import in each. The [derivation record](testing/fitness-policy-f2f/operator-derivation.json) and independent tests enforce this exact replacement. Original operator validation, loops, swaps, RNG calls and preference logic remain in the copies. The new scorer can reject a hard-invalid candidate before the operator finishes; the outer experimental runner bounds subsequent attempts. That is an explicit new-release admission behavior, not a promise of identical cross-policy search trajectories. No original module symbol is monkeypatched to change production scoring.

## Actual optimization and scoring contract

`RunInputs` owns a deep copy of the F2E fictional bridge. It binds the frozen cohort, preferences, settings, eligibility, complete offering set and run-local constraint snapshot. Unavailable faculty/room blocks are physically excluded from copied construction calendars so the unchanged original reset helper cannot reopen them. Section restrictions remain in the copied section calendars. This is isolated construction-domain behavior; production availability reset logic remains unchanged.

`RunScorer` freezes the full validated GA parameters, integer seed, release, term, run identifier, input/cohort/constraint digests, exception state and explicit fitness configuration in its evaluation identity. All scores retain that identity and exact rational value. Cross-policy comparisons and cache access fail closed. Cache entries hold scores and passive projections, not mutable chromosomes. Every scoring request first repeats original complete-candidate admission, including cache hits; caching does not bypass hard validation. Caches are cleared at generation boundaries and the rule is pinned in the identity.

The experimental workload is:

`D = sum((assigned_i - target_i)^2 / target_i)` for positive targets.

The exact score is `existing_seven_components + lambda * D + explicit_overload_supplement`. Existing binary64 component values are converted to their exact represented rational values, not rounded decimal approximations. `D_ONLY` and `D_PLUS_LEGACY_BANDS` remain explicit F2E sensitivity configurations. The GA pilot uses **lambda 25, D_ONLY**, an experimental choice rather than a production policy selection. No float conversion is used for ordering. Existing Option B targets and the 40-unit hard ceiling remain enforced; non-teaching allowances are fixed hypothetical inputs, not scheduled activities.

| Stage | Experimental behavior |
|---|---|
| Initialization | Original V2 constructor on owned reduced templates; bounded construction and original hard admission; exact initial ranking |
| Parent selection | Complete typed score-vector check before original tournament RNG draws |
| Elitism | Original elitism helper with the same exact score objects |
| Crossover | Import-only derived original operator calls the bound experimental scorer internally |
| Mutation | Import-only derived original operator calls the same scorer internally; verbosity off only suppresses diagnostics |
| Replacement/survivors | Mandatory original hard admission, bounded fresh backfill, exact sorting |
| Best-ever | Strict exact improvement only; independent deepcopy; carried into the replacement pool |
| Termination | Explicit generation budget; zero initial fitness does not falsely imply convergence |
| Reporting | Exact ratios, per-generation best/current, per-stage requests, component evaluations, cache hits/misses and diagnostic counts |

The original operators use module-level `random`. The isolated runner therefore leases it within a worker process, restores the caller's state in `finally`, and rejects nested/concurrent experimental execution. This is not a thread-safe production integration contract for unrelated application threads using `random`; production use is not authorized.

Zero target/zero assignment is allowed. Unauthorized positive teaching is rejected before scoring. A valid fictional approval does **not** supply missing arithmetic: authorized positive teaching stops the affected run with `AUTHORIZED_ZERO_TARGET_ARITHMETIC_UNRESOLVED`. Expired/invalidated permission remains rejected. The Department Chair publication role is not treated as workload-exception authority.

Preflight proves only narrow necessary impossibilities (no eligible instructor, missing required room availability, offered units exceeding aggregate hard capacity). Other bounded unsuccessful searches return `SEARCH_EXHAUSTED`, feasibility `UNKNOWN`. Exhaustion is not proof that the academic problem is infeasible. No evaluated chromosome is repaired to force acceptance.

## Actual GA checkpoint continuation

New format: `f2f-actual-ga-checkpoint/1`, kind `POPULATION_GENERATION_AND_RNG_NOT_CANDIDATE_REPLAY`. The codec reuses the unchanged passive allowlisted model-graph codec. It stores:

- Release/evaluation identity, full fitness/GA configuration, seed and generation.
- Actual current population, exact scores, generation-best and independently owned best-ever.
- Actual Python RNG state, exact fitness history, diagnostic/scorer counters and cache-boundary policy.

Decoding requires a SHA-256 obtained independently from the owned control record, then validates envelope checksum, strict fields, source/input identity, size/node bounds, graph types, score tags, recomputed hard admission/scores, sorted population, history bindings and best-ever ownership. No executable module or path is selected by checkpoint data. Resuming restores the saved population and next RNG draw; it does not regenerate prior generations or replay an evaluation stream. Validation uses a separate scorer so audit work does not change the continued run's counters.

The [smoke record](testing/fitness-policy-f2f/20261031T190429538275+0800-smoke/actual-ga-smoke.json) records a real 222,188-byte checkpoint written/read in owned temporary storage. Its hash is `2c0209d82977a3d3a9fbbdca46516189d39b859b9a216b6008558a3b5614c197`. A two-generation uninterrupted run equalled a pause after generation one followed by **one** resumed generation, including assignments, history, counters and final RNG state. Tests also cover pauses at generations zero/two and an independent child process. Existing checkpoints were not opened for rewriting, migrated or reinterpreted. The six historical incompatible artifacts remain a pre-existing limitation; fresh supported V1 continuation remains the legacy baseline.

## Verification and retained unsuccessful attempts

| Fresh selection | Passed | Failed/errors/skipped in final selection |
|---|---:|---:|
| New operator, full GA, constraints and section checks | 33 | 0 |
| New actual checkpoint/continuation checks | 23 | 0 |
| Preserved F2D/F2C foundation | 178 | 0 |
| Legacy boundary, D10 V2, thesis hard-constraint and reporting regressions | 90 | 0 |
| Actual current V1 checkpoint mirror | 4 | 0 |
| **Python total** | **328** | **0** |
| Existing frontend contracts | 42 | 0 |

The V1 mirror verifies 156 source-byte-identical files and three real fictional checkpoint archives without replacing fingerprint functions. Its input fingerprint is `b803fa98ae3a527e7c020e17173063e190a1c55ca37f3de17c7c6f1f61415e95`. The legacy selection includes actual V2 fresh-process continuation. Frontend checks are Node contracts, **not browser acceptance**. No browser, PostgreSQL or institutional workflow test was run for F2F. No application build was needed because no application UI changed.

Tests independently demonstrate real crossover acceptance changing from legacy `[4,0]`/`[0,4]` preference to exact balanced `[2,2]`, and a real mutation improvement under crossed day preferences. Whole-GA tests cover equal/unequal targets, restricted/no eligibility, unavoidable underload, zero assignments, overload, indivisible offerings, exact targets and a preference tradeoff. Corrupt candidates cover faculty/room/section conflicts, invalid time, missing offerings and altered eligibility. Identity, source, cache, best-ever, exact near-tie ordering, source tampering, checkpoint alteration and zero-target boundaries are tested.

Two unsuccessful records remain archived:

1. The original combined qualification selection exceeded its unchanged 300-second cap. Its parent initially discarded partial captured output, so completed test counts and the exact case at timeout are **not established**. That evidence cannot be reconstructed. The selection was split into independent operator/checkpoint commands, the immutable paused prefix was reused across corruption tests with per-case copies, and per-test progress/timeout-output retention was added. No test was disabled and no deadline increased. The split selections passed within the same cap; that supports a harness runtime limitation, but does not prove which test was active during the original timeout.
2. The first split checkpoint selection recorded **22 passed, one failed**. The negative checksum case set an invalid digest and immediately recomputed the unchanged valid digest, so it passed original bytes to the decoder. The new test was corrected to preserve that alteration and assert changed bytes. The decoder and pinned release were unchanged. The complete rerun passed 23/23.

Intermediate passes are not added to the 328 final total. Known warnings are pytest's already-imported AnyIO assertion-rewrite warning and the existing Starlette/httpx and AnyIO BlockingPortal deprecations. No dependencies were installed or changed to suppress them.

## Matched GA pilot

Results and distributions are recorded below after the bounded pilot. Timing runs use fresh workers with imports and fixture preparation outside the engine window. There is no GA warm-up; OS cache state is uncontrolled. Timing, call-count instrumentation and tracemalloc/process-memory sampling use separate executions. The same scenario, seed, parameters, fictional preference/settings inputs and constraint snapshot are supplied to each policy. Source verification, exact arithmetic, repeated admission and cache behavior are part of their actual engine cost.

The pilot uses population four, two generations, zero fresh additions, one crossover/mutation attempt per operator invocation, five constructor restarts and five candidate attempts. Original V2 orchestration and original scoring form the legacy control. F2F's orchestration follows that population sequence but adds policy-tagged admission/validation and boundary verification; it is not simply a scorer microbenchmark. Different policy decisions can change later RNG paths. Only **within-policy** instrumented/uninstrumented executions and split/uninterrupted continuation are expected to match assignments and RNG exactly.

Raw legacy and experimental fitness values have different scales. Compare teaching-unit vectors, common post-hoc `D`, conflicts, coverage and other component penalties instead. Three seeds per timing cell are a pilot, not evidence of statistical superiority. Four scenarios have neutral preferences; the fifth includes a fictional Tuesday preference. Preference-satisfaction percentage and specialization alignment are **NOT MEASURED**. No specialization dataset or invented institutional evidence was supplied.

Data: [50 trial records and summary](testing/fitness-policy-f2f/20261031T192439411494+0800-benchmark/summary.json). **30 timing, 10 separately counted and 10 separately memory-instrumented full GA runs passed; zero failed.** All 20 instrumented runs matched the corresponding timing run's schedule/RNG digest. The audit also compares exact histories, workloads and counters. All final populations and best-ever outputs passed original admission; every final best had zero independently counted faculty/room/section conflicts and zero unassigned offerings.

Uninstrumented engine seconds, three seeds per cell. SD is sample standard deviation. These distributions include actual engine verification/validation; they exclude imports, fixture preparation and post-run audit. Preprocessing and post-validation times are separately retained in each trial, and persistence is not measured.

| Scenario | Policy | Mean | Median | SD | Min | Max |
|---|---|---:|---:|---:|---:|---:|
| equal_shortage | legacy | 1.326701 | 1.196260 | 0.367437 | 1.042280 | 1.741563 |
| equal_shortage | experimental | 9.925614 | 10.441427 | 1.082876 | 8.681263 | 10.654153 |
| unequal_shortage | legacy | 2.540193 | 2.504461 | 0.103934 | 2.458839 | 2.657280 |
| unequal_shortage | experimental | 21.440510 | 21.446758 | 0.819643 | 20.617762 | 22.257012 |
| limited_eligibility | legacy | 1.942869 | 1.710747 | 0.456779 | 1.648764 | 2.469096 |
| limited_eligibility | experimental | 14.957587 | 14.766733 | 0.513508 | 14.566834 | 15.539194 |
| above_combined_targets | legacy | 3.917881 | 3.971260 | 0.122753 | 3.777475 | 4.004908 |
| above_combined_targets | experimental | 25.549808 | 25.521043 | 0.231274 | 25.334262 | 25.794119 |
| preference_tradeoff | legacy | 1.140717 | 1.151132 | 0.080149 | 1.055870 | 1.215149 |
| preference_tradeoff | experimental | 9.330646 | 9.445719 | 0.717923 | 8.562136 | 9.984082 |

F2F was **6.52 to 8.44 times slower by mean engine duration** in this pilot. This is not a performance improvement. Different search decisions, identity/source checks, repeated graph admission, exact arithmetic and cache behavior are present; this experiment does not isolate their individual time shares. No claim that cache savings eliminate validation costs is supported.

Teaching-unit vectors below are in seed order 71, 72, 73. `D` is a common post-hoc workload metric, not the raw cross-policy fitness total.

| Scenario | Targets | Legacy assigned vectors | F2F assigned vectors | Legacy D | F2F D |
|---|---|---|---|---|---|
| equal_shortage | [24, 24] | [4, 0]; [2, 2]; [0, 4] | [2, 2]; [2, 2]; [2, 2] | 122/3, 121/3, 122/3 | 121/3, 121/3, 121/3 |
| unequal_shortage | [12, 24] | [6, 6]; [6, 6]; [6, 6] | [4, 8]; [4, 8]; [4, 8] | 33/2, 33/2, 33/2 | 16, 16, 16 |
| limited_eligibility | [12, 24] | [8, 4]; [8, 4]; [10, 2] | [8, 4]; [8, 4]; [8, 4] | 18, 18, 41/2 | 18, 18, 18 |
| above_combined_targets | [4, 8] | [6, 10]; [6, 10]; [6, 10] | [6, 10]; [6, 10]; [6, 10] | 3/2, 3/2, 3/2 | 3/2, 3/2, 3/2 |
| preference_tradeoff | [24, 24] | [2, 2]; [4, 0]; [0, 4] | [2, 2]; [2, 2]; [2, 2] | 121/3, 122/3, 122/3 | 121/3, 121/3, 121/3 |

All 15 experimental timing histories were **flat at their initial best-ever score** through generations one and two. The initialized populations already contained the final best found by this bounded pilot. This does not demonstrate convergence improvement, broader GA search effectiveness or an optimal timetable proof. The separate real-operator tests demonstrate an improving crossover and mutation on deliberately constructed parental candidates; those controls must not be presented as end-to-end benchmark improvements.

Restricted eligibility limited feasible allocations: legacy seeds 71 and 72 and all F2F seeds returned `[8,4]`, while legacy seed 73 returned `[10,2]`. Above-target supply produced `[6,10]` under both policies. In equal-target and unequal-target cases, some legacy outcomes had a larger common D than F2F. In the preference scenario, legacy seed 73 retained a five-point day-preference penalty; the other legacy timing seeds and all experimental timing seeds had zero other-seven-component penalty. This is a small illustrative tradeoff, not a production weight recommendation.

Separate counted executions at seed 71:

| Scenario | Legacy full scorer body calls | F2F full scorer body calls | F2F requests | F2F cache hits |
|---|---:|---:|---:|---:|
| equal_shortage | 210 | 27 | 373 | 346 |
| unequal_shortage | 233 | 44 | 397 | 353 |
| limited_eligibility | 274 | 11 | 301 | 290 |
| above_combined_targets | 386 | 48 | 413 | 365 |
| preference_tradeoff | 276 | 13 | 303 | 290 |

Full scorer body calls were independently counted using a separate Python profiling callback and matched native component-evaluation counters. A cache hit still performs full original hard admission. Counting-run durations are instrumented and are not substituted for the normal timing distributions.

Separate memory executions at seed 71, MiB (bytes / 1,048,576):

| Scenario | Policy | Python traced peak (not RSS) | Sampled process working-set peak | Sampled private-commit peak (not RSS) |
|---|---|---:|---:|---:|
| equal_shortage | legacy | 12.675 | 186.621 | 643.988 |
| equal_shortage | experimental | 33.502 | 242.961 | 705.348 |
| unequal_shortage | legacy | 30.573 | 216.586 | 674.164 |
| unequal_shortage | experimental | 40.203 | 265.688 | 725.047 |
| limited_eligibility | legacy | 12.016 | 186.953 | 643.809 |
| limited_eligibility | experimental | 37.604 | 254.250 | 712.715 |
| above_combined_targets | legacy | 46.159 | 243.551 | 701.180 |
| above_combined_targets | experimental | 43.572 | 272.523 | 732.121 |
| preference_tradeoff | legacy | 5.027 | 174.355 | 630.566 |
| preference_tradeoff | experimental | 32.147 | 243.344 | 702.555 |

These are **single observations per policy/scenario**, not memory distributions or a retained-memory/leak study. Tracemalloc and a nominal 20 ms sampler were enabled together only in memory runs. Sampled peaks can miss spikes; actual sample timing depends on scheduling. Process working set and private commit include imports and native allocations, while traced peaks cover the measured window plus instrumentation. OS lifetime peak values and before/after samples are retained separately in raw evidence; lifetime peak is not used as an engine-window peak. No total-RSS or statistically repeatable memory-saving claim is made. No GC or allocator policy was changed.


## Files and reproduction

All F2F files are new. Existing tracked files modified by F2F: **none**. The exact inventory is in the manifest; the implementation group is:

- `backend/experiments/fitness_policy_f2f/__init__.py`
- `backend/experiments/fitness_policy_f2f/release.py`
- `backend/experiments/fitness_policy_f2f/inputs.py`
- `backend/experiments/fitness_policy_f2f/scoring.py`
- `backend/experiments/fitness_policy_f2f/engine.py`
- `backend/experiments/fitness_policy_f2f/checkpoint.py`
- `backend/experiments/fitness_policy_f2f/crossover.py`
- `backend/experiments/fitness_policy_f2f/mutation.py`
- `backend/experiments/fitness_policy_f2f/release-manifest.json`

The evidence root adds isolated fixtures, three test modules, runner, fresh-process resume helper, V1 verifier, benchmark, audit, baseline/anchor/derivation metadata, per-attempt records/progress and pilot JSON. No generated checkpoint is placed in an application checkpoint store.

From the repository root in Windows PowerShell, with the existing virtual environment and dependencies:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2f/run_checks.py foundation
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2f/run_checks.py legacy
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2f/verify_v1.py
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2f/run_checks.py operators
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2f/run_checks.py checkpoints
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2f/run_checks.py frontend
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2f/benchmark.py
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2f/audit_evidence.py --verify
```

Run benchmark commands sequentially on an otherwise quiet machine. Workers use whitelisted environment variables, schema-only import bootstrap, synthetic scoring file contexts, network/database denial and repository-write guards. No credential-bearing environment is propagated. New runs create new timestamped evidence directories; they do not overwrite old runs. The final audit pins this completed evidence inventory and will intentionally reject additional/unreviewed files until a new separately reviewed manifest is prepared. Do not rerun `prepare` or use `rebuild-unpublished` to disguise a source change under this release ID.

## Decision and production blockers

**GO for further isolated, larger-cohort policy evaluation; NO-GO for production activation.** Actual operator dispatch and population/RNG continuation are demonstrated on the bounded fictional fixtures. This is not permission to switch V1/V2 scoring or resume their checkpoints under F2F.

Production integration still requires an explicitly approved weight/overload composition, resolved authorized-positive-zero-target arithmetic, trusted exception authority/lifecycle, an authoritative semester-specific cohort, larger multi-seed and mixed-component scheduling evaluation, concurrency-safe application dispatch and a separately reviewed version/provenance/API integration plan. Source-verification and validation costs need profiling before any performance change; no optimization or reduced validation was introduced here. Institutional providers remain blocked, and prior D15 disposable PostgreSQL acceptance does not authorize production publication.

Preservation/privacy/hash results are recorded in the manifest. No staging, commit, push, database operation, dependency installation, institutional activation or next-milestone work was performed.
