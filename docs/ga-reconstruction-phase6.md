# Phase 6: isolated Python reconstruction and copying feasibility

2026-10-28, Asia/Manila. Source HEAD `1423812e13a5791a550c893ef6b17bfef4b4ebfb`. This is an isolated fictional experiment, not production optimization, institutional acceptance or authority activation. The measured results, final test outcomes and preservation audit follow the methods below.

**Recommendation: NO-GO for Phase 7 production integration on this evidence.** Both caches reduce component-level work, but the varied-seed Medium/Large engine results are inconsistent and whole-engine memory peaks do not materially improve. Calendar caching increases component-local allocations. Keep production reconstruction, validation and copying unchanged; no C++ work is justified by this experiment.

## Inspection and preservation boundary

Read the Phase 2, Phase 3, memory-study and Phase 5 reports, manifests and benchmark sources, original V2 orchestration/constraint/publication/reconstruction paths, workload and fitness contracts, graph codec, constructors and D10 tests. Verified the prior artifact hashes and recorded [1,550 pre-existing raw paths](testing/ga-reconstruction-phase6/preservation-baseline.json) before new experiments. This includes all 23 academic files, the protected local preferences modification, the existing settings modification, original GA sources, migrations, six historical checkpoints, stored schedules, earlier evidence, Git index and existing untracked work. No AGENTS.md was found.

Reuse the Phase 5 schema-only bootstrap: seven empty CSV schemas and two empty JSON schemas replace legacy import-data reads in a private interpreter; loaders are restored before execution. Only explicitly constructed BENCH fictional subjects, sections, faculty, rooms, eligibility, preferences and hypothetical non-teaching loads are scheduling inputs. A guard rejects subsequent institutional text/CSV parsing. Original raw binary fingerprints remain genuine; no protected values or faculty names are parsed or printed. The import-time default calendars are not scenario inputs.

No production modules, endpoints, scoring equations, operators, RNG calls, workload settings, authority policies or database schemas were edited. Benchmark workers make no database connection, institutional-provider call, publication operation, persistent checkpoint or application-store write. New benchmark evidence is written outside the protected stores, after guarded engine execution. Regression checkpoint/SQLite fixtures use owned temporary paths; no PostgreSQL is accessed. No dependency installation, native compiler, staging, commit or push is part of this work.

## Actual call path and ownership

| Boundary | Source | Work retained by both prototypes |
|---|---|---|
| Candidate construction / original operators | `backend/services/ga_v2_engine.py:56`, `:149` | Deep-copy templates, original scheduling/reset, crossover, mutation, selection, fitness and RNG behavior. |
| Admission before selection and publication | `backend/services/ga_v2_engine.py:28` | Fixed section/faculty/room conflict checks, publication validation and authoritative faculty metadata equality. |
| Publication validation | `backend/services/ga_publication_service.py:8` | Exact offering coverage, component metadata, fixed/preassigned declarations, meeting instructor/room consistency, then serialize and reconstruct. |
| Payload-to-chromosome | `backend/services/chromosome_service.py:731` | Deep-copy subject templates, faculty and rooms; rebuild assignment/load state; original resource, eligibility, load, conflict, duration and component gates. |
| Component validation | `backend/services/chromosome_service.py:681` | Required/absent components, room types, duplicate intervals, weekly minutes, continuous three-hour labs, exact membership in all resource grids. |
| Chromosome time parser | `backend/services/chromosome_service.py:499` | Original `str(value).strip().split(':')` integer behavior, including its permissive values and exceptions. It is not replaced by the stricter external-constraint parser. |
| Fitness and preferences | `backend/genetic_algorithm/operators/FitnessFunction.py:444`, `:984` | Original effective preferences, penalties, frozen faculty universe and underload accounting. |
| Best-ever / continuation | `backend/services/ga_v2_engine.py:107`, `:214`, `:220`, `:263`, `:271` | Independent best copies, original graph codec, strict fingerprints, continuation validation and original next RNG draw. |

Faculty calendars, assignment lists, subject/room/time-block cycles and best/population ownership are mutable. A large copy is not evidence that its graph can be pruned or shared. No safe proof was found for removing complete reconstruction or replacing full chromosome copies. Those transformations were not attempted. In particular, caching a previous candidate's admission would risk missing later mutations to assignments, eligibility, availability or fixed commitments.

The actual repeated immutable work identified here is much narrower: the same exact time strings and equivalent full day/start/end calendar content are parsed and assembled repeatedly during one component-validation invocation. Availability flags are not inputs to that original membership-set calculation; all separate availability/fixed/conflict checks remain active.

## Two prototypes, neither installed in the application

Source: [reconstruction_phase6.py](../backend/benchmarks/reconstruction_phase6.py). Original function code runs in private globals dictionaries. No original module symbol, global deepcopy implementation or production fingerprint provider is replaced.

1. **`parse_cache`** memoizes successful parses of exact built-in strings, length at most 32, for one component-validation call. Maximum 256 entries; overflow and non-exact/custom values use the original parser. Exceptions are never cached. Input strings are not normalized into keys. The cache clears in `finally` on success or error.
2. **`calendar_cache`** replaces precisely the original `allowed = {...}` expression in an isolated AST copy, preserving the rest of the validator. Every lookup re-reads complete current day/start/end content. Only exact dictionaries/lists/strings/plain TimeBlock fields qualify; custom classes/coercion/descriptors and oversized inputs fall back to the original comprehension. At most eight full-content keys of up to 512 blocks are held per validation. Values are immutable frozensets of original parsed triples. No model references, identity-only keys, calendars or flags are shared or retained. Changing contents changes the key; no cache survives the invocation.

These are explicitly versioned experimental engines, `phase6-reconstruction.1:parse_cache` and `phase6-reconstruction.1:calendar_cache`. Each identity hashes the genuine original engine identity, variant and actual prototype source bytes. Private `run` and `validate_state` bodies differ only in their local identity-provider binding and the private admission chain. Original operators, scoring, validation branches/defaults and RNG operations remain original. Original and cross-variant validators must reject incompatible experimental states. This is not a production checkpoint compatibility bridge or fingerprint spoof.

For **report comparison only**, the full encoded-state projection replaces the deliberately distinct identity with an explicit invalid comparison label. Actual execution, validation and continuation always use their genuine distinct identities. No saved state is edited to impersonate another version.

## Matched experiment design

| Scenario | Faculty | Offerings | Sections | Rooms |
|---|---:|---:|---:|---:|
| Small | 6 | 12 | 3 | 4 |
| Medium | 12 | 24 | 6 | 6 |
| Large | 24 | 48 | 12 | 10 |

Reuse the Phase 2 fixture generator unchanged. Subject eligibility is explicit, preferences vary, and offered units are below combined faculty targets. The unqualified Small member's zero assignment remains included in underload. Hypothetical admin/research/extension loads stay fixed inputs. Original Option B targets `max(0, 24-admin-research-extension)`, warning above 30 and hard ceiling 40 remain unchanged.

The repeated experiments use population **2**, **1** generation, **0** fresh chromosomes, one crossover/mutation attempt, five construction restarts and three candidate attempts. These bounded parameters are **not** Phase 2's population4/generations3 performance baseline. Nine separate reference workers execute the original Phase 2 parameters for seed714 across all three variants/scales and check established assignments/history; those single cold references are correctness evidence, not repeatable speedup measurements.

| Measurement | Fresh workers | Repetitions / seeds | Interpretation |
|---|---:|---|---|
| Reference | 9 | One seed714 per variant/scale | Original full-parameter correctness only. |
| Clean cProfile | 9 | One seed714 per variant/scale, after one excluded warm-up | Exclusive time, cumulative time, callers, cache counts and reconstruction counts; diagnostic, not wall baseline. |
| Fresh-process wall matrix | 54 | Three seeds714/715/716 x two independent process repetitions x three variants x three scales | No profiler or tracemalloc. Matched lightweight safety/process sampling is present and disclosed. Variant order rotates. |
| Engine allocations | 27 | Three independent seeds/processes per variant/scale | One-frame tracemalloc after an excluded untraced warm-up, process counters and separate original-copy control. Never pooled with wall timings. |
| Unobserved wall controls | 9 | Three warmed seed714 engine calls within each variant/scale process | No sampler/watchdog Python threads, tracer or profiler during the timed engine interval. Within-worker repetition, not three independent process cohorts. |
| Operation controls | Same 9 | Three calls per operation on an identical prepared best | Original deepcopy/fitness and variant component validation/reconstruction/admission. Timed and traced calls are separate. |

All worker environments whitelist ordinary OS variables and exclude connection URLs, credentials and authority flags. Each engine warm-up/trial uses the same parameters, input fixtures and seed, with RNG state restored on worker exit. Original GC remains enabled with unchanged thresholds/allocator configuration; forced collection is only outside measured engine intervals and at diagnostic release points. There is no production GC policy change.

Fresh-process workers have 600-second deadlines, 768 MiB sampled working-set and 1,536 MiB sampled private-commit bounds. Clean profiles exclude background Python threads, using foreground boundary counters and the parent deadline. Operation/control workers have 300-second parent deadlines and foreground memory checks. Sampling can miss/overshoot brief spikes. Setup, fingerprints, warm-up, post-run verification and evidence serialization are excluded from the engine interval; worker wall duration is retained separately. No persistence phase is timed because no benchmark persistence occurs.

Process working set, OS lifetime working-set peak and private commit are separate Windows observations. The sampled engine working-set peak can miss short spikes; the lifetime peak includes setup/warm-up and is not an engine-only peak. Private-commit comparisons below use end points/deltas, not an invented sampled peak. Tracemalloc excludes pre-existing fixture/setup allocations and is **not process RSS or total RAM**; tracer metadata is reported separately. Post-release traced values include measurement/reporting allocations and are not isolated cache leaks. Operation peaks are inclusive transient call peaks, not exclusive allocator churn attributed to one Python function.

## Profiler validity investigation

The three initial background-sampled profiles are retained under `20261028T154827722456+0800-baseline-profile`, with an explicit `validity.json` exclusion. Their caller graph attributed direct parser calls to unrelated thread waits/locks. They are invalid for attribution and are not pooled into results.

A retained standalone stdlib canary on Python3.14.2 reproduced the attribution problem: 200,000 leaf calls acquired impossible lock/sleep parents with a background Python thread; the single-thread control recorded only the actual caller. This establishes a local measurement limitation, **not an identified upstream bug or application regression**. No interpreter/package was changed. Clean cProfile workers run without background sampling/watchdog Python threads and assert caller/count contracts; timing, allocation and unobserved controls remain separately labeled. The canary and invalid evidence are not erased.

## Correctness criteria

Compare exact assignments, complete generation histories, final fitness/breakdown, workload including zero-assignment members, diagnostics, final RNG state and a canonical full-state graph including calendars, aliases, eligibility and frozen inputs. Original admission validates every final population member and best. Best-ever fitness is non-increasing; no convergence claim follows from one generation or an unchanged score.

Focused tests also exercise component errors, malformed values and a deterministic malformed-interval corpus, cache overflow/fallback, current-content changes, optional/custom input behavior, exact rejection fingerprints, bounded exhaustion, fixed section/faculty/room conflicts, adjacent half-open intervals, hard teaching-load rejection and graph nonmutation. Clone mutation remains isolated; best and population graphs stay disjoint. Experimental caches must not retain model roots.

Actual in-memory original-codec pause/decode/validate/continue is checked independently for each version, including final complete graph and next RNG state. For continuation reporting only, primitive set item order is canonicalized in a fresh encoded representation: the original codec preserves list/dict order and aliases, but does not promise set iteration order. Every node, ordered container, field and alias reference remains checked. This representation is never decoded, validated or continued. Primary cross-variant benchmark state hashes still use the original raw graph projection. Tampered identities/generation/fitness and cross-version states must fail closed. Existing D10 current-release V1 creation/write/load/continuation and V2 engine/API regressions run separately on owned fixtures. Six historical checkpoints are only raw-hashed for preservation, never migrated or reinterpreted.

## Reproduction on Windows 11

From the repository root, using the existing environment; no installation or database variable is needed. Run measurement commands sequentially, without concurrent test/benchmark workloads. Measurement, test and analysis commands create new timestamped evidence directories; the audit refreshes only this study's manifest. Do not remove earlier failures.

```powershell
.\.venv\Scripts\python.exe -B backend/benchmarks/reconstruction_benchmark.py --part reference
.\.venv\Scripts\python.exe -B docs/testing/ga-reconstruction-phase6/profile_canary.py
.\.venv\Scripts\python.exe -B backend/benchmarks/reconstruction_benchmark.py --part profile
.\.venv\Scripts\python.exe -B backend/benchmarks/reconstruction_benchmark.py --part timing
.\.venv\Scripts\python.exe -B backend/benchmarks/reconstruction_benchmark.py --part memory
.\.venv\Scripts\python.exe -B backend/benchmarks/reconstruction_operations.py
.\.venv\Scripts\python.exe -B docs/testing/ga-reconstruction-phase6/run_checks.py phase6
.\.venv\Scripts\python.exe -B docs/testing/ga-reconstruction-phase6/run_checks.py regressions
.\.venv\Scripts\python.exe -B docs/testing/ga-reconstruction-phase6/run_checks.py phase5
.\.venv\Scripts\python.exe -B docs/testing/ga-reconstruction-phase6/v1_fixture.py
.\.venv\Scripts\python.exe -B docs/testing/ga-reconstruction-phase6/analyze.py
.\.venv\Scripts\python.exe -B docs/testing/ga-reconstruction-phase6/audit.py
```

Do not invoke ordinary unbootstrapped pytest against these studies: the runner establishes schema-only imports before collection, rejects institutional parsing and directs the existing fresh-child tests through the unchanged fictional adapter. Its environment excludes database URLs. The original byte baseline intentionally fails closed if existing application/data/evidence/index bytes change; it is not a command to reset them. Analysis uses the newest completed primary matrices and records their input hashes. Do not rerun the preliminary `baseline-profile` part; it is retained historical diagnostic evidence only.

## Wall-time results: independent process matrix

Primary evidence: [20261028T160251173619+0800-timing/summary.json](testing/ga-reconstruction-phase6/20261028T160251173619+0800-timing/summary.json). Six runs per variant/scale: three seeds, each repeated in two fresh processes. Safety sampling is present; cProfile and tracemalloc are absent. Values are engine seconds. SD is sample standard deviation across these mixed-seed runs, not a confidence interval. Paired ratios use the same seed/repetition; values below 1 mean the prototype was slower.

| Scenario | Variant | Median s | Mean s | Sample SD s | Min-max s | Paired speedup median | Paired speedup min-max |
|---|---|---:|---:|---:|---|---:|---|
| Small | baseline | 2.351325 | 2.310426 | 0.242529 | 1.964216-2.603008 | 1.0000x | 1.0000-1.0000x |
| Small | parse_cache | 2.032444 | 2.033049 | 0.229679 | 1.674316-2.384008 | 1.1269x | 0.9980-1.3022x |
| Small | calendar_cache | 2.205870 | 2.174036 | 0.141139 | 1.965348-2.357020 | 1.0627x | 0.8858-1.2659x |
| Medium | baseline | 4.430402 | 5.485756 | 1.866425 | 4.033738-8.321216 | 1.0000x | 1.0000-1.0000x |
| Medium | parse_cache | 4.433612 | 5.262209 | 1.858102 | 3.558371-7.967012 | 1.0347x | 0.9077-1.2716x |
| Medium | calendar_cache | 4.605907 | 5.288433 | 1.543958 | 3.927493-7.508246 | 1.0467x | 0.8738-1.1083x |
| Large | baseline | 8.321042 | 8.544934 | 0.645077 | 7.973911-9.683783 | 1.0000x | 1.0000-1.0000x |
| Large | parse_cache | 8.280556 | 8.609199 | 0.980893 | 7.541739-9.910522 | 0.9926x | 0.9111-1.0807x |
| Large | calendar_cache | 8.209694 | 8.285601 | 0.899089 | 7.125286-9.253411 | 1.0415x | 0.9614-1.1438x |

Median-time changes relative to baseline: Small parse **-13.56%**, calendar **-6.19%**; Medium parse **+0.07%**, calendar **+3.96%**; Large parse **-0.49%**, calendar **-1.34%**. These ratios of pooled medians differ from paired ratios; they must not be interchanged. Medium varies substantially with seed/search path. Every prototype has a matched pair slower than baseline. No outliers or slow trials were discarded.

The process order rotates by seed/repetition, but desktop CPU load, thermals and operating-system scheduling are uncontrolled. Only three distinct seeds are represented. There is no formal significance or population-level speedup claim. One Large diagnostic profile, or Small's stronger result, cannot establish a general Medium/Large benefit. Separate thread-free controls below address observation overhead without pooling different protocols.

### Excluded warm-up engine durations

| Scenario | Variant | Median warm-up s | Min-max s |
|---|---|---:|---|
| Small | baseline | 2.381801 | 2.111641-2.721215 |
| Small | parse_cache | 2.276913 | 1.967955-2.397121 |
| Small | calendar_cache | 2.043822 | 1.916688-2.319344 |
| Medium | baseline | 4.835916 | 4.429437-8.076066 |
| Medium | parse_cache | 4.498804 | 3.918489-8.108621 |
| Medium | calendar_cache | 4.208672 | 3.978532-7.710859 |
| Large | baseline | 8.542170 | 7.808670-10.342735 |
| Large | parse_cache | 8.440628 | 7.211183-9.806275 |
| Large | calendar_cache | 7.859452 | 7.423380-9.611516 |

## Clean exclusive-time and reconstruction evidence

Primary profiles: [20261028T155719422228+0800-profile/summary.json](testing/ga-reconstruction-phase6/20261028T155719422228+0800-profile/summary.json). Single-thread caller/count contracts passed. The following Large baseline times come from a separately profiled run, not the 54-run wall matrix.

| Original function | Calls (including recursion) | Exclusive s | Cumulative s |
|---|---:|---:|---:|
| `deepcopy` | 4,760,991 | 3.611736 | 12.175605 |
| `_reconstruct` | 219,520 | 1.493027 | 12.120387 |
| `_deepcopy_dict` | 219,682 | 2.194895 | 12.107737 |
| `admit` | 15 | 0.004234 | 10.477587 |
| `validate_publication` | 15 | 0.032687 | 10.353608 |
| `payload_to_chromosome` | 15 | 0.071609 | 10.094017 |
| `_validate_baseline_components` | 15 | 0.789439 | 3.199479 |
| `time_to_minutes` | 1,140,720 | 1.728531 | 2.346554 |
| `faculty_preference_fitness` | 18 | 0.102761 | 0.612326 |
| `_build_effective_preferences` | 18 | 0.001453 | 0.301399 |

The original chromosome parser's exclusive share is **7.989%** of this instrumented Large run. A conditional, zero-cost removal of that exclusive work would bound this particular profiled interval at **1.086828x**; real caching is not free, some parser calls are outside the replaced component path, and cProfile overhead is call-dependent. This is not a predicted uninstrumented speedup. Nested cumulative times must not be summed. Deepcopy's approximately 56% cumulative share contains reconstruction and recursive helpers; it is not an exclusive numeric kernel or safely removable budget.

The wrapper itself has little exclusive cost; reconstruction's cumulative cost includes the required model graph copies, calendar rebuilding and validation. Preference construction's own exclusive cost is small; its cumulative cost includes other work. Neither is justification for skipping checks or changing scoring.

| Scenario | Variant | Payload reconstructions | Recursive deepcopy calls | Chromosome parser calls |
|---|---|---:|---:|---:|
| Small | baseline | 15 | 1,295,587 | 284,826 |
| Small | parse_cache | 15 | 1,295,587 | 1,163 |
| Small | calendar_cache | 15 | 1,295,587 | 24,278 |
| Medium | baseline | 17 | 4,249,626 | 646,046 |
| Medium | parse_cache | 17 | 4,249,626 | 1,997 |
| Medium | calendar_cache | 17 | 4,249,626 | 31,458 |
| Large | baseline | 15 | 4,760,991 | 1,140,720 |
| Large | parse_cache | 15 | 4,760,991 | 3,029 |
| Large | calendar_cache | 15 | 4,760,991 | 34,784 |

For Large, parse caching records 1,137,691 hits and 525 misses across 15 validator calls; calendar caching records 3,180 hits and 60 misses. That is repeated immutable token/full-grid content, not proof that the whole candidate was immutable. Every original reconstruction and deepcopy call remains. Counts are from seed714 at this budget, not invented counts for other seeds.


## Retained intermediate failures and corrections

The first focused run, [20261028T164602526157+0800-phase6/command.json](testing/ga-reconstruction-phase6/20261028T164602526157+0800-phase6/command.json), records **62 passed, 5 failed, 4 warnings**. These results remain intact. All five were independently reproduced as test-contract/fixture errors against the unchanged original oracle:

- Three full-versus-resumed raw-byte graph assertions failed, including `baseline`. The original codec serializes primitive sets in their iteration order; decoding can reconstruct the same membership with a different order. The original-only diagnostic found precisely **one differing node (7879), a primitive set permutation**. Root, node count, every other node/alias reference and RNG state matched. The corrected reporting comparator sorts only primitive set items in a newly encoded representation, never in an engine/checkpoint. Ordered containers, metadata and all alias references remain strict. This is not a codec or GA fix.
- Two adjacency fixtures constructed a candidate from unreduced templates, then validated it against reduced templates. The original publication validator correctly returned `Publication rejected: ('SYN101', 'SYN-A') fixed institutional schedule changed.` The fixture now constructs the adjacent candidate from the reduced authoritative templates, as the existing D10 test does. Fixed-metadata and half-open conflict checks remain unchanged.

The [original-only diagnosis](testing/ga-reconstruction-phase6/20261028T165028694021+0800-contract-diagnosis/diagnosis.json) records both findings without model dumps. Its first parent invocation also had a JSON-output protocol failure: original fictional scheduling console messages preceded the JSON. That failure's metadata is retained in the preceding contract-diagnosis directory. The diagnostic now suppresses unstructured scheduling console output while retaining its structured findings; no application output policy changed.

The rerun, [20261028T165110121110+0800-phase6/command.json](testing/ga-reconstruction-phase6/20261028T165110121110+0800-phase6/command.json), records **67 passed, 0 failed, 1 warning**. Three warnings introduced by the new test's empty `pytest.raises` message pattern were removed from that test. The remaining PytestAssertRewriteWarning for already imported AnyIO results from the required pre-collection fictional bootstrap. No warning suppression or package change was used. The two prototype source bodies were unchanged throughout these test corrections, so the primary performance evidence was not invalidated by a prototype fix.

## Allocation and process-memory results

[Complete numeric analysis](testing/ga-reconstruction-phase6/20261028T170140885904+0800-analysis/analysis.json) records every sample, median, mean, sample SD, min/max and input hash. Three independently started seed workers per allocation cell; process observations without tracing use six timing workers per cell. Matched Phase 6 comparisons only: lower absolute peaks than prior phases are not optimization savings, because the budgets/callbacks differ.

| Scenario | Variant | Engine Python peak median MiB | Sample SD MiB | Min-max MiB | Post-release traced KiB | Original copy incremental peak MiB |
|---|---|---:|---:|---|---:|---:|
| Small | baseline | 29.143191 | 1.361358 | 27.381181-30.059790 | 54.691 | 2.424601 |
| Small | parse_cache | 29.636640 | 1.447202 | 27.368642-30.059984 | 53.739 | 2.424702 |
| Small | calendar_cache | 29.225362 | 1.334344 | 27.512479-30.141191 | 51.744 | 2.424717 |
| Medium | baseline | 48.029318 | 14.746760 | 45.376986-72.141796 | 64.761 | 4.854472 |
| Medium | parse_cache | 48.015307 | 14.754454 | 45.361887-72.140538 | 63.723 | 4.854572 |
| Medium | calendar_cache | 48.157383 | 14.717817 | 45.505206-72.219617 | 58.561 | 4.854673 |
| Large | baseline | 71.808174 | 5.767628 | 71.806955-81.797389 | 73.630 | 9.328414 |
| Large | parse_cache | 71.807451 | 5.762544 | 71.805707-81.787598 | 72.337 | 9.328205 |
| Large | calendar_cache | 71.892101 | 5.790331 | 71.891977-81.921187 | 64.967 | 9.328013 |

| Scenario | Variant | Untraced sampled WS peak MiB | Untraced end private commit MiB | Traced sampled WS peak MiB | Traced end private commit MiB |
|---|---|---:|---:|---:|---:|
| Small | baseline | 190.551 | 647.492 | 212.336 | 670.312 |
| Small | parse_cache | 191.580 | 648.174 | 212.508 | 669.875 |
| Small | calendar_cache | 191.828 | 648.203 | 212.609 | 670.176 |
| Medium | baseline | 210.930 | 667.887 | 247.867 | 706.594 |
| Medium | parse_cache | 211.154 | 667.598 | 247.867 | 706.473 |
| Medium | calendar_cache | 210.875 | 667.650 | 248.004 | 706.184 |
| Large | baseline | 237.949 | 694.289 | 302.559 | 744.305 |
| Large | parse_cache | 236.959 | 693.369 | 301.156 | 752.027 |
| Large | calendar_cache | 238.654 | 695.492 | 301.766 | 749.340 |

There is no material whole-engine Python peak reduction. Small parse caching increases the median peak by about 0.493 MiB; Medium/Large differences are tiny relative to their peaks and seed variation. Calendar caching increases component-local storage and whole-engine peaks slightly. Native process figures include Python/libraries/setup and, in traced runs, tracer metadata. Sub-MiB to several-MiB process differences are not demonstrated cache savings or leaks. Private commit is not resident RAM. All 99 primary workers release the three sampled final model references; post-release traced bookkeeping is small and is not a long-run leak test.

## Separate thread-free engine controls

One fresh process per variant/scale, seed714 only, one excluded engine warm-up and three timed repetitions. These intervals have no tracer, profiler, Python sampling/watchdog thread or in-loop census. They are distinct from the varied-seed process matrix; the three repetitions are not independent process cohorts.

| Scenario | Variant | Median s | Sample SD s | Min-max s | Excluded warm-up s |
|---|---|---:|---:|---|---:|
| Large | baseline | 8.297390 | 0.395648 | 8.112229-8.871067 | 8.956743 |
| Large | calendar_cache | 8.239288 | 0.439121 | 8.179474-8.968195 | 7.657726 |
| Large | parse_cache | 8.400743 | 0.287278 | 7.930152-8.450919 | 8.154794 |
| Medium | baseline | 6.758307 | 0.247115 | 6.339102-6.775416 | 6.177896 |
| Medium | calendar_cache | 5.771929 | 0.120904 | 5.635640-5.876765 | 5.779149 |
| Medium | parse_cache | 5.994261 | 0.374627 | 5.817559-6.536480 | 6.308435 |
| Small | baseline | 2.138757 | 0.056379 | 2.093221-2.205322 | 2.603572 |
| Small | calendar_cache | 1.916516 | 0.278654 | 1.830886-2.350613 | 2.007606 |
| Small | parse_cache | 1.963245 | 0.138546 | 1.759652-2.024228 | 1.797227 |

These controls do not rescue the Large result: parse caching is slower and calendar caching is close to baseline at this one seed. Medium/Small show better local numbers, but different seed coverage, process order, warm state and desktop conditions prevent pooling or attributing differences between protocols to sampling overhead.

## Separate operation allocation and latency controls

Three untraced timing calls and three separately traced calls per operation, after an excluded operation warm-up. All operate on the same prepared best for their variant/scale. State graph and RNG remain unchanged across probes. These transient peaks are inclusive of callees; snapshot/net-live bytes are not total allocation churn. Full distributions are in the linked analysis.

| Scenario | Variant | Component ms / peak KiB | Reconstruction ms / peak KiB | Admission ms / peak KiB | Original fitness ms / peak KiB | Original deepcopy ms / peak KiB |
|---|---|---|---|---|---|---|
| Large | baseline | 93.846 / 71.771 | 286.630 / 3021.546 | 316.324 / 3065.583 | 11.570 / 123.173 | 255.493 / 9552.496 |
| Large | calendar_cache | 35.839 / 200.320 | 252.960 / 3155.828 | 252.625 / 3196.033 | 11.617 / 123.221 | 301.969 / 9552.496 |
| Large | parse_cache | 31.923 / 52.668 | 246.274 / 3005.632 | 234.524 / 3050.301 | 9.792 / 122.742 | 259.330 / 9552.496 |
| Medium | baseline | 32.390 / 66.699 | 181.206 / 1587.586 | 185.055 / 1613.174 | 5.671 / 67.146 | 156.050 / 4970.973 |
| Medium | calendar_cache | 14.847 / 203.707 | 148.332 / 1723.487 | 123.012 / 1743.859 | 6.528 / 67.338 | 125.117 / 4970.973 |
| Medium | parse_cache | 14.043 / 54.400 | 144.476 / 1570.743 | 142.125 / 1595.607 | 6.284 / 67.338 | 124.226 / 4970.973 |
| Small | baseline | 31.503 / 66.467 | 116.988 / 865.079 | 86.917 / 876.895 | 9.402 / 37.371 | 105.447 / 2483.254 |
| Small | calendar_cache | 9.657 / 200.718 | 106.891 / 998.217 | 126.396 / 1012.438 | 4.197 / 37.371 | 93.951 / 2483.254 |
| Small | parse_cache | 9.051 / 52.199 | 91.144 / 848.323 | 98.776 / 860.627 | 5.244 / 37.371 | 109.541 / 2483.254 |

The selected component computation itself is measurably cheaper in these controls, but savings are diluted by required reconstruction/copy/operator work. Large parse component peak falls from 71.771 to 52.668 KiB; calendar component peak rises to 200.320 KiB. Large payload peaks are about 2.951 / 2.935 / 3.082 MiB (baseline / parse / calendar). Original Large deepcopy remains about 9.328 MiB transient peak for every variant; fitness remains approximately 123 KiB. The unchanged deepcopy and fitness timing controls also vary across workers, underscoring environmental/microbenchmark variability. They are not accelerated by either cache. No copy or fitness memory reduction is claimed.


## Final verification and limitations

| Suite | Fresh result | Evidence |
|---|---|---|
| phase6 | 67 passed, 0 failed | [20261028T165110121110+0800-phase6](testing/ga-reconstruction-phase6/20261028T165110121110+0800-phase6/command.json) |
| regressions | 81 passed, 0 failed | [20261028T170127456771+0800-regressions](testing/ga-reconstruction-phase6/20261028T170127456771+0800-regressions/command.json) |
| phase5 | 11 passed, 0 failed | [20261028T170352147163+0800-phase5](testing/ga-reconstruction-phase6/20261028T170352147163+0800-phase5/command.json) |
| v1-mirror | 4 passed, 0 failed | [20261028T171211756299+0800-v1-mirror](testing/ga-reconstruction-phase6/20261028T171211756299+0800-v1-mirror/command.json) |

**Final successful suites: 163 passed, 0 failed.** These are freshly executed results. The earlier 62-pass/5-fail focused run and direct V1 1-pass/3-fail attempt remain historical attempts, not erased or relabeled as successful. No benchmark trial or worker timed out. All 9 reference, 9 clean profile, 54 fresh-process timing, 27 allocation and 9 operation/control workers completed their intended comparisons. The latter also supply 27 separately timed thread-free engine calls. None of these categories is pooled into one speedup estimate.

### V1 archival isolation finding

The direct workspace V1 attempt, `20261028T170426978967+0800-v1/command.json`, records **1 passed, 3 failed**. Each pause case stopped in original `ga_checkpoint_service.save_checkpoint`, line297: the `source_inputs` comprehension reads text from the real `backend/data` directory. The privacy guard rejected that access with `INSTITUTIONAL_TEXT_PARSE_REJECTED` before checkpoint-envelope serialization/write. The original guard and writer were not weakened, removed or edited.

A new [V1 fixture runner](testing/ga-reconstruction-phase6/v1_fixture.py) creates an owned temporary mirror with **133 byte-identical source/test files**, the genuine policy-compatibility manifest and eleven explicitly fictional input files. CSVs contain only the reviewed empty schemas; JSON contains empty identity/preassignment/preferences catalogs and default hypothetical settings. Original D10 test templates supply the two fictional faculty/subjects/room. Source and test bytes are unchanged. The child denies all original academic reads, original-repository writes and database/network operations.

The original engine fingerprint in this mirror **matches the workspace current-release engine fingerprint**. The input fingerprint is independently computed from the actual fictional files and checked against the unmodified original function. It is intentionally not the institutional/workspace input fingerprint. No fingerprint function or stored identity is replaced, and strict loader checks remain active. All four original tests pass. All three actual compressed checkpoint archives are verified for checksum, genuine engine identity, actual fictional input identity and exact `source_inputs` equality to the generated fictional files. No archive, run UUID or model dump is copied into repository evidence. The temporary mirror/checkpoints are disposed only as owned fixtures.

This demonstrates current-source V1 creation/load/continuation on fictional inputs, not continuation of institutional inputs or historical checkpoints. The direct workspace command remains guard-blocked by design; use `v1_fixture.py`, not an unguarded rerun, to reproduce this verification.

### Warnings and scope

The focused and Phase 5 suites each record one pre-bootstrap AnyIO assertion-rewrite warning. The 81-regression suite records that warning plus the existing Starlette/httpx TestClient deprecation and AnyIO BlockingPortal alias deprecation. The fictional V1 mirror records no warnings. These are identified from actual retained logs; no dependency was installed and no warning was suppressed.

No frontend/browser or full D1-D16 acceptance rerun was needed for these isolated files. Original application bytes are preserved; this does not turn earlier acceptance into fresh Phase 6 results. No PostgreSQL connection or test was executed; retained D15 evidence and database contents were not operated on. Institutional authorization/publication remains blocked. This study does not establish production performance, feasibility for real catalogs, long-run memory plateaus, mathematical infeasibility from search exhaustion or compatibility of the six historical checkpoints.

## Decision and remaining work

| Candidate | Correctness within tested scope | Measured benefit / cost | Recommendation |
|---|---|---|---|
| Validation-local parse cache | Exact tested original behavior, graph ownership, rejection and V2 continuation preserved | Clear component reduction and stronger Small timing; Medium median ties, Large median differs less than 0.5%, paired Large median is below 1x, whole-engine allocation peak unchanged | **NO-GO for production integration on current evidence.** |
| Full-content calendar membership cache | Exact tested original behavior, graph ownership, rejection and V2 continuation preserved | Local computation cheaper; Large pooled-median gain about 1.34% with slower matched pairs; component peak increases from 71.8 to 200.3 KiB; no material engine-peak reduction | **NO-GO for production integration.** |
| Removing full reconstruction / sharing chromosome copies | Ownership/mutability requirements not proven safe for such a change | Not prototyped; original copy peaks and copy counts remain | Leave unchanged. |

Keep the production GA and deepcopy paths unchanged. If more performance work is authorized, first repeat matched Medium/Large wall measurements under controlled CPU conditions and the full Phase 2 population4/generations3 budget, retaining all seeds/failures and negative controls. Stronger evidence is needed before proposing production integration. Do not infer that a local cache win implies an application win, or that a recursive cumulative profile identifies removable memory. No Phase 7 implementation or C++ work is started.

## Exact new-file inventory and preservation

New standalone modules:

- `backend/benchmarks/reconstruction_phase6.py`
- `backend/benchmarks/reconstruction_benchmark.py`
- `backend/benchmarks/reconstruction_operations.py`
- `backend/tests/performance/test_reconstruction_phase6.py`

New report: `docs/ga-reconstruction-phase6.md`.

New tooling under `docs/testing/ga-reconstruction-phase6/`: `run_checks.py`, `profile_canary.py`, `diagnose_contracts.py`, `v1_fixture.py`, `analyze.py`, `audit.py`. The same directory contains the preservation baseline, all successful/failed/invalid evidence, numeric analysis and final manifest. The [manifest](testing/ga-reconstruction-phase6/manifest.json) lists every new path and raw artifact hash, excluding its own hash. No prior evidence was overwritten.

Final audit compares all **1,550 pre-existing paths** and all **23 academic files**, checks unchanged HEAD/index and the original two tracked local data modifications, validates analysis input hashes, JSON/Python syntax, whitespace and complete/truncated receipt/credential patterns. It records exact new-file counts. Both protected preferences and existing settings changes remain byte-identical to their initial local state, unstaged and uncommitted. No existing application/test/migration/data/checkpoint/schedule/evidence file is modified by Phase 6. All additions remain untracked; no staging, commit, push, installation, PostgreSQL operation or production optimization occurred.


Final inventory: **141 new files: 10 Python, 130 JSON and one Markdown report**. The manifest hashes **140 artifacts** and excludes itself. Privacy scan: zero findings; preservation: 1,550/1,550 paths and 23/23 academic files; new-file whitespace/syntax and Git whitespace checks pass. Git emitted its existing LF-to-CRLF advisory for the protected preferences path during read-only diff inspection. No normalization, staging or file rewrite was performed; the subsequent raw-byte verification remains authoritative.
