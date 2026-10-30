# Isolated Python GA memory investigation

2026-10-28, Asia/Manila. This follows the completed scalar-overlap feasibility study. No scalar acceleration, compiler installation, production optimization, database operation or Git checkpoint is included. All inputs and exported identifiers are fictional. Source commit remains `1423812e13a5791a550c893ef6b17bfef4b4ebfb`.

The question is allocation and retention, not whether an expensive CPU function must be a large allocator. Measurements are collected before proposing any change. Existing Phase 2/3 evidence is preserved rather than reclassified as new memory results.

## Measurement boundaries

Reuse the original Phase 2 Small/Medium/Large fixtures, seed 714, population 4, three generations, one fresh chromosome and two operator attempts. Full engine runs use the original V2 implementation, scorer, operators, constraints and best-ever rules. Their schedules and complete fitness histories must match the existing seed714 evidence. No API publication, persistent checkpoint write or institutional provider is invoked. Original GA imports can read existing inputs internally; output is suppressed and only synthetic scoring inputs and model objects are used in experiments. Repository fingerprint reads remain genuine.

Four primary experiments run sequentially in fresh, environment-whitelisted workers:

1. **Process RAM without tracemalloc:** Windows `K32GetProcessMemoryInfo`, foreground checkpoints and a 50 ms sampler. `WorkingSetSize` measures the process working set; `PeakWorkingSetSize` is the OS lifetime high-water mark, not a resettable per-engine peak. PrivateUsage is private commit, **not resident RAM**. Whole-process values include Python, imported libraries and runtime overhead. The sampled interval covers fixture preparation through final validation and can miss brief spikes. [Microsoft structure contract](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex), [query function](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getprocessmemoryinfo).
2. **Full Python allocations:** one-frame tracemalloc starts after fixture preparation, immediately before `engine.run`. Record current/peak allocation bytes, tracer metadata, generation snapshots and post-release collection. Capture the engine peak before additional final validation. Snapshots/report construction add observer overhead; their working set is not the untraced RAM baseline. No forced collection is inserted into the generation loop.
3. **Focused operations:** eight-frame tracing, original seed10101 constructive witness, one operation at a time. Measure templates/chromosome deepcopy, frozen scoring input capture, full fitness, preference-map construction and single-record normalization. Inputs exist before tracing. Return values stay alive until the snapshot. Peaks include temporaries; snapshot differences show **net live allocations**, not total allocation churn. Repeating a function 25 times does not turn its live delta into a total-allocated-byte count. [Python tracing contract](https://docs.python.org/3.14/library/tracemalloc.html).
4. **Repeated executions:** five identical Small runs in one interpreter with one tracer; discard each output and collect cycles afterward. Record process RAM, traced live bytes, global peak and representative model weak references. Probe summaries and caches remain. Five repetitions do not establish the absence of every application leak.

No cProfile is enabled. Instrumented elapsed times are diagnostic runtime, not new performance baselines. The earlier 5.067062 / 9.032717 / 31.435525 second means remain historical timing results. These allocation trials have different instrumentation and cannot be compared as speedups.

Additional diagnostics separate facts that would otherwise be conflated:

- The focused witness graph is not assumed to represent the final GA chromosome. A separate original-engine execution inventories the actual final best and population, then measures an unmodified deepcopy of that final best.
- `graph_summary` visits only built-in data containers and explicit GA model attributes, with identity deduplication. It never follows arbitrary GC referents into modules/classes/functions or exports attribute values. Its shallow-size sum is not RSS and omits native buffers and hidden runtime overhead. Cycles are counted once.
- The original optional score observer intentionally keeps `(chromosome, score)` references to avoid object-ID reuse. Direct V2 benchmark scoring leaves it disabled. A separate diagnostic explicitly enables/disables it, scores three cloned candidates, collects cycles while the result is held, then clears the observer and collects again. This distinguishes deliberate strong references from uncollected cyclic garbage. It does not change the observer's production policy.

The main benchmark callback retains the most recent state, as Phase 2 does, including the previous population while the next generation is being built. That root can affect live memory. Reported peaks are for this benchmark lifecycle, not guaranteed FastAPI server peaks. The actual-graph diagnostic retains only the final callback state and checks identical scheduling output; it is not presented as a measured memory optimization. Best-ever state inside the engine is unchanged in every experiment.

## Measured results

Primary evidence: [ten-worker study summary](testing/ga-memory-study/20261028T123029720068+0800/summary.json), with separate per-worker JSON records. All values below are measured; MiB = 1,048,576 bytes and KiB = 1,024 bytes.

| Scenario | Untraced process lifetime peak working set MiB | Untraced working set after release/GC MiB | Engine Python allocation peak MiB | Traced live after release/GC KiB |
|---|---:|---:|---:|---:|
| Small | 258.164 | 241.723 | 100.389 | 109.126 |
| Medium | 294.656 | 244.223 | 118.927 | 107.160 |
| Large | 371.320 | 279.211 | 197.127 | 110.705 |

The respective untraced working sets immediately before engine execution were 164.082 / 166.258 / 172.363 MiB. Representative final Subject, Faculty and Room weak references were all gone after collection in every scale. These are sampled model references, not an exhaustive proof that every application object was freed. Small remaining traced blocks include runtime/import/pandas caches and numeric probe summaries. The process working set remaining above its pre-engine value does not, by itself, identify a Python object leak. Allocator/runtime pages and resident libraries are not the same metric as live traced objects.

Allocation profiling increased the process footprint: lifetime peak working sets in traced workers were 336.551 / 490.891 / 649.406 MiB. Those values include tracing/snapshot/report overhead and are **not** the untraced RAM baseline. At the Large engine-return point, tracemalloc's own metadata was 65,838,960 bytes; this is distinct from the 206,703,110-byte traced allocation peak. Private commit is retained in JSON and is not relabeled as RAM. No subtraction of these quantities is used to claim an exact native allocation total.

Large's generation-3 snapshot held 184,144,645 traced bytes. The leading allocation sites were `copy.py:249` (`y.__dict__.update(state)`, 117,201,536 bytes) and `copyreg.py:104` (instance reconstruction, 48,708,464 bytes). Together these two sites account for about 158.224 MiB, or 90.1% of that snapshot's traced current bytes. This is live allocation-site evidence, not a CPU-time inference, exclusive function percentage, cumulative churn count or a snapshot taken exactly at the transient high-water instant.

The focused operations use separately constructed seed10101 witnesses, not the engine's final best:

| Operation | Small peak KiB | Medium peak KiB | Large peak KiB |
|---|---:|---:|---:|
| Deepcopy templates | 1652.246 | 3107.363 | 6009.621 |
| Deepcopy witness chromosome | 2483.238 | 4971.449 | 9550.066 |
| Freeze scoring inputs | 913.650 | 1825.707 | 3647.332 |
| Original fitness once | 36.639 | 65.329 | 125.670 |
| Original fitness 25 times, scores discarded | 79.489 | 100.993 | 156.725 |
| Effective preferences once | 29.660 | 37.143 | 51.817 |
| Effective preferences 25 times, last result kept | 75.123 | 87.705 | 110.742 |
| Normalize one preference record | 1.422 | 1.422 | 1.422 |

Live copied-witness allocations immediately after the copy were 1305.055 / 2605.352 / 4989.648 KiB, all attributed to tracebacks containing `copy.py` within the retained eight frames. Peak is higher than live return size because it includes temporary reconstruction/memo/container work. These are one controlled operation per scale, not statistical distributions or allocation-throughput measurements. Each full score remained equal to its original witness score.

Repeated normalization/construction exists: the original scorer calls `_build_effective_preferences`, and frozen preference loading still deepcopies the map before normalization. But these targeted measurements do **not** make preference construction the dominant memory peak. Twenty-five discarded scores or preference maps do not produce 25 simultaneously retained complete maps. The 25-call cases are temporary/retained-peak experiments, not total bytes allocated over all calls.

The [post-GC observer follow-up](testing/ga-memory-study/20261028T124927091993+0800-observer-followup/observer.json) explains why the initial three-copy cases looked similar before collection:

| Scenario | Observer disabled: traced live after GC, MiB | Observer enabled: traced live after GC, MiB | Clone roots alive while enabled | Clone roots after clear/GC |
|---|---:|---:|---:|---:|
| Small | 0.004965 | 3.792965 | 3 | 0 |
| Medium | 0.005759 | 7.594912 | 3 | 0 |
| Large | 0.007068 | 14.575204 | 3 | 0 |

When disabled, all three sampled clone roots are already dead after collection. When enabled, the dictionary deliberately retains all three; clearing it and collecting releases all sampled clones. Final live trace summaries after clearing are 29-34 KiB, including diagnostic data, rather than zero. This demonstrates scoped strong-reference retention in this controlled original observer, **not an active leak in direct V2 runs**, where the observer is disabled. The initial pre-GC evidence remains intact instead of being overwritten to hide the distinction.

The [actual final-graph records](testing/ga-memory-study/20261028T125041818961+0800-actual-graphs/) come from three additional original-engine executions, not reconstruction of a saved signature. All schedules and histories match Phase2 seed714. Original final hard admission passed.

| Scenario | Final best Subjects | Reachable TimeBlocks | Unassigned TimeBlocks | Extra off-root Subjects | Final-best copy peak / live MiB |
|---|---:|---:|---:|---:|---:|
| Small | 12 | 2084 | 1892 | 0 | 2.425 / 1.274 |
| Medium | 24 | 4172 | 3788 | 0 | 4.854 / 2.543 |
| Large | 48 | 8000 | 7232 | 0 | 9.329 / 4.876 |

"Unassigned" in this census means `TimeBlock.subject is None`; it does not mean the slot is available, unconstrained or unnecessary. Fixed reservations can be outside Subject genes and still require calendar enforcement.

Each best has exactly one Subject object per offering key, with no additional off-root Subject objects found by the bounded data-graph walk. The four-member populations contain 48 / 96 / 192 Subject objects, respectively, as expected from four distinct chromosomes. Census and copied-census type counts agree. Large's estimated unique shallow graph size is 4,596,779 bytes; this is neither its traced copy peak nor process RAM.

Small's best reaches five assigned faculty identities; the sixth unassigned faculty member remains in the separate frozen scoring universe and contributes underload under the unchanged policy. The census therefore does not authorize removing zero-assignment faculty from scoring. The calendar objects are extensive, but they are not shown to be irrelevant: allowed-slot membership, reservations, resets and later assignment operations use them. No unnecessary duplicated offering graph was demonstrated in these tested final individuals. Whether a different representation could share immutable calendar definitions safely remains a new design/parity question, not an implemented pruning opportunity.

Repeated-run evidence: [five Small executions](testing/ga-memory-study/20261028T123029720068+0800/retention-small.json), all in one interpreter, all seed714 outputs/history matching the original baseline. The worker finished within its 600-second bound (437.142 seconds total). It was not a timing benchmark.

| Run | Traced live after drop/GC KiB | Process working set after GC MiB | Sampled model weak references alive |
|---|---:|---:|---:|
| 1 | 819.626 | 270.633 | 0 |
| 2 | 827.334 | 279.051 | 0 |
| 3 | 833.322 | 284.090 | 0 |
| 4 | 838.049 | 289.961 | 0 |
| 5 | 841.831 | 291.738 | 0 |

Post-GC traced bytes increased by 22,738 bytes (22.205 KiB) from run1 to run5, not zero. The final positive snapshot is dominated by lazy-import allocations (617,179 and 84,339 bytes at the two leading import sites), followed by pandas/runtime caches and retained numeric diagnostic records. This does not demonstrate growth proportional to retained chromosome graphs; representative model weak references are dead. It is not an exhaustive native/Python leak proof.

The process working set increased by 21.105 MiB between those same post-GC points. Its exact cause is **not established** by tracemalloc. Allocator/page retention, fragmentation, runtime/native caches and other untraced memory are possible explanations, not independently verified diagnoses. No process-RAM plateau is claimed over five runs, no working-set trim was used, and no blanket production collection policy is proposed. Longer controlled repetitions and deeper allocator measurements would be needed to distinguish those causes.

## Interpretation and proposed next experiments

The measured priorities are graph copying/reconstruction and object lifetime, rather than a scalar C++ kernel or preference normalization as a RAM fix. The full-run snapshot allocation sites and the focused copy peaks independently support that priority. They do not identify a safe production rewrite by themselves.

Recommended separately reviewed experiments, in order:

1. **Audit roots and lifetimes before reducing data.** Quantify the benchmark callback's previous-state retention and the copied graphs' cycles; compare identical-output runs with reporting roots scoped differently. Keep the engine's required best-ever chromosome and original candidate isolation. Do not infer an application-server leak from this benchmark callback.
2. **Explore copy representation only after defining required data.** Calendar grids and resource metadata dominate reachability, but unused slots can still be required by validators and later operators. A future immutable/static-calendar sharing prototype must preserve exact availability, mutation independence, faculty workload/eligibility, fixed commitments and checkpoint fingerprints. Blindly shallow-copying candidates or removing empty blocks is unsafe and is not recommended as a patch.
3. **Review optional observation ownership separately.** If an application path enables retained score observations, measure that path's complete lifecycle and reset boundary. Removing strong references without replacing the object-ID reuse protection would change its contract. Direct V2 memory results here use the observer disabled.
4. **Treat preference caching as a separate CPU/churn hypothesis.** Frozen preferences are repeatedly copied and normalized, but their measured peak is much smaller than chromosome copying. Any cache needs an immutable, correctly versioned key covering frozen preferences, settings, scoring version and faculty universe, plus mutation/checkpoint parity. No cache or scoring change is implemented.
5. **Extend retention tests before diagnosing a leak.** Use more runs/seeds and, separately, an owned application process with the real reporting lifecycle. Compare post-release traced bytes, live model roots and OS counters together. Do not trim working sets or add production `gc.collect()` calls merely to make a RAM graph fall; that would conceal or alter the measured lifecycle.

No proposed optimization is implemented. Do not remove calendar blocks solely because their `subject` is None: original component admission uses those calendars for exact permitted-slot membership, and resets/availability depend on them. Do not remove eligibility, fixed reservations, per-faculty non-teaching loads or zero-assignment faculty. Teaching target remains `max(0, 24-admin-research-extension)`, warning threshold above 30 and hard ceiling 40; best-ever behavior and all original numerical penalties remain untouched.

Any later representation-sharing, caching or lifecycle change needs its own parity and checkpoint/version review. A synthetic memory result does not authorize changing the production scheduler or institutional authority. No automatic GC policy, weak-reference replacement, cache or pruning is introduced here.

## Tests, preservation and exact inventory

Fresh validation: **117 tests passed, zero failed/skipped**. The [12 new memory tests](testing/ga-memory-study/20261028T125227703737+0800-memory/command.json) passed in 24.10 pytest seconds; [105 existing regressions](testing/ga-memory-study/20261028T125228493190+0800-regressions/command.json) passed in 147.83 pytest seconds (21 Phase2 tests, 48 D10 engine/API tests, 36 fitness/resource tests). The two existing Starlette/HTTPX and AnyIO BlockingPortal deprecations remain recorded without dependency changes. These are fresh executions; historical Phase2/3 passes are not added to this total.

The primary study completed **10/10 workers**, including all six full-engine RAM/allocation runs and five repeated Small executions inside the retention worker. Three observer follow-ups and three actual-final-graph workers also passed. In total, the 14 measured complete engine executions (six scale/mode runs, five retention runs, three graph runs) matched the baseline seed714 schedule and history and used original hard admission. The successful Small preparation pilot is retained separately and is not pooled as another primary trial. No timeout or failed memory trial was discarded.

The new tests verify Windows counter definitions/invariants; bounded sampler storage and thread shutdown; cycle-safe, module-bounded graph traversal; net-live snapshot summaries; peak-versus-live distinction and tracer cleanup; identical copied signatures and hard admission; fresh/equal preference maps and unchanged fitness/RNG; observer strong-reference cleanup; a real original-engine RAM run with exact baseline output and released sample models; and continued write rejection while reading OS memory counters.

New source/report paths:

- `backend/benchmarks/memory_study.py`
- `backend/benchmarks/memory_observer.py`
- `backend/benchmarks/memory_graphs.py`
- `backend/tests/performance/test_memory_study.py`
- `docs/testing/ga-memory-study/run_checks.py`
- `docs/testing/ga-memory-study/audit.py`
- `docs/ga-memory-study.md`

All other new files are the individually inventoried JSON baseline, measurements, test records and manifest. Existing files modified by this task: **none**.

Before editing, verified the previous manifests and captured a new raw-byte baseline covering **1,481 paths**: all 1,454 original paths plus all 27 Phase 2/3 additions. This covers all 23 academic data files, protected local preferences, the user's modified settings and tiny script, original GA/scoring/RNG/model sources, migrations, checkpoints, saved schedules, historical evidence and Git index. No existing file is edited or restored. All study additions are standalone benchmark/test/report/evidence files. No compiler or dependency is installed, no PostgreSQL connection is made, and nothing is staged, committed or pushed.

The [manifest](testing/ga-memory-study/manifest.json) lists exact new paths, raw artifact hashes, privacy findings and preservation checks. Raw snapshots, heap dumps, model reprs, faculty rows, credentials, cookies and receipts are not exported. Allocation records contain only file/line locations and numeric aggregates. Private names are compared locally during the audit without printing them. Existing D10 regression fixtures use owned fictional SQLite and stores; they do not activate institutional authority or write to retained databases.

Final audit passed: all **1,481 baseline paths** and **23 academic data paths** are byte-identical; **27 artifact hashes**, privacy inspection and whitespace checks passed. The manifest is the twenty-eighth new file and excludes its own hash. There are six new Python files, twenty-one JSON files and this Markdown report. The only tracked local changes remain the two pre-existing preferences/settings modifications, unchanged and unstaged. All prior evidence and the user's tiny baseline script remain intact.

## Windows 11 reproduction

From the repository root using the existing virtual environment. Run measurements sequentially, then tests:

```powershell
.\.venv\Scripts\python.exe -B backend/benchmarks/memory_study.py --part all --scenario all
.\.venv\Scripts\python.exe -B backend/benchmarks/memory_observer.py
.\.venv\Scripts\python.exe -B backend/benchmarks/memory_graphs.py
.\.venv\Scripts\python.exe -B docs/testing/ga-memory-study/run_checks.py memory
.\.venv\Scripts\python.exe -B docs/testing/ga-memory-study/run_checks.py regressions
.\.venv\Scripts\python.exe -B docs/testing/ga-memory-study/audit.py
```

Use `--part ram`, `alloc`, `focused` or `retention`, and `--scenario small`, `medium` or `large` for a bounded subset of the primary study. Retention uses Small by design. Every run creates new evidence and refuses to overwrite existing directories. Primary workers have 600-second limits; observer/actual-graph workers have 300-second limits. Failure/timeout records are retained honestly. Windows process memory APIs are required; unsupported platforms fail instead of substituting Python allocations for RAM. No external package is needed.

No browser/build run is required for these Python-only measurement tools. Production institutional authorization and publication remain unchanged and blocked where unconfigured. No later implementation phase starts automatically.
