# Phase 5: Python GA retention and copy-graph ownership

2026-10-28, Asia/Manila. Source commit `1423812e13a5791a550c893ef6b17bfef4b4ebfb`. All additions are isolated fictional benchmark/test tooling. Production GA, workload/scoring rules, operators, checkpoint formats, GC/allocator configuration, endpoints, authority and protected data remain unchanged. No dependency installation, PostgreSQL operation, commit or push is included.

## Design and data isolation

Read Git status, the complete prior memory report/manifest and relevant tools, Phase 2/3 reports, original V2 execution/checkpoint/codec/ownership contracts and fictional fixture generators before editing. Verified the previous raw hashes and recorded a [new preservation baseline](testing/ga-retention-phase5/preservation-baseline.json) covering **1,509 paths**, including all previous evidence and all 23 academic files. No AGENTS.md was found. The pre-existing preferences/settings modifications and untracked tiny script are preserved.

A new private-process import bootstrap substitutes **seven schema-only empty CSV frames and two schema-only JSON documents** at the legacy import-data boundary. It restores those loaders before execution; scheduling is supplied exclusively by the existing explicit BENCH fictional fixtures. Institutional rows/names are not parsed or used by this study. A text/CSV guard rejects later institutional parsing; original binary file fingerprints and preservation hashes remain genuine. No engine fingerprint is spoofed. The import bootstrap is not an application configuration or authority provider. Hardcoded default source-level section/room/student objects remain in the private interpreter; their stable model counts are included in the prepared baseline but they are not scheduling inputs.

Before longer tests, all three original Phase 2 configurations reproduced seed714's exact assignment hash and complete fitness history under this bootstrap. Their original population4/generations3 parameters are separate reference checks, not pooled timing results.

Longer repeated series use **population2, one generation, one fresh chromosome, one crossover/mutation attempt, five constructor restarts and three candidate attempts**. The Small/Medium/Large dimensions and hypothetical preferences/eligibility/workload inputs are unchanged. These lower search budgets make replication bounded; results are not interchangeable with Phase 2's three-generation performance baseline. Every result retains original hard admission for every final candidate and best, assignment/history/RNG-state digests and best-ever monotonicity.

| Experiment | Fresh workers | Warm-ups per worker | Measured runs per worker | Seeds |
|---|---:|---:|---:|---|
| Original configuration reference | 3, one per scale | 0 | 1 | 714 |
| Small process counters | 2 independent cohorts | 2 | 12 | six 714, then 715/716/717/718/715/716 |
| Medium process counters | 2 independent cohorts | 2 | 12 | same sequence |
| Small/Medium traced retention | 2, one per scale | 2 | 6 | 714/714/714/715/716/717 |
| Small/Medium optional observer | 2, one per scale | 1 | 3 | 714/715/716 |
| Bounded Large counters / tracing | 2 | 1 | 2 / 1 | 714/715; 714 |
| Small/Medium light callback timing controls | 2 | 2 | 6 | three 714, then three 715 |
| Reporting-ownership prototype | 4, two policies per scale | 2 | 2 | 714/715 |

The series therefore include repeated identical seeds, varied seeds, independent interpreter cohorts, recorded cold/warm-up behavior and smaller bounded Large runs. The warm-up records are preserved and labeled, excluded from measured totals. No cross-process absolute working-set equality or memory plateau is assumed.

## Measurements and bounds

Windows process working set, OS lifetime working-set peak and private committed bytes are sampled before, during generation callbacks and after each run; a 50 ms watchdog also records the worker's sampled peak. Private commit is not resident RAM. One-frame tracemalloc runs separately, starts after warm-up, and records current/run peaks and net-live snapshot differences. [Windows counter definitions](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex), [Python allocation tracing](https://docs.python.org/3.14/library/tracemalloc.html).

Original GC remains enabled with unchanged thresholds/allocator settings. Collection is forced only between executions and at diagnostic ownership-release points in private workers, never as a production policy or inside the original GA loop. Each worker has a 900-second deadline, 768 MiB sampled working-set ceiling and 1,536 MiB sampled private-commit ceiling. Exceeding a ceiling terminates only that private worker, preserving completed public JSON lines. Polling may overshoot/miss brief spikes; these are safety bounds, not memory reservations or allocator tuning. Checkpoint verification workers have 300-second deadlines and the same memory watchdog.

Counts cover tracked Subject/Faculty/Room/Section/TimeBlock instances, with no names or referrer dumps. Prepared fixture/import counts are retained as a baseline, including unused hardcoded default source objects; stable absolute counts are not misreported as zero. Sampled Subject, Faculty, Room and TimeBlock weak references and a weak-referenceable reporting Lease track release. **Actual chromosomes are plain lists and cannot be weak-referenced**; the Lease is explicitly a reporting-root proxy, not a fabricated weak reference to a chromosome. Model counts cover GC-tracked Python objects, not native heaps or every Python object.

Each execution drops run-owned state, collects, measures optional-observer-held roots, clears the scoped observer, collects again and measures final release. Observers are disabled by default. Enabling one is a labeled test-only measurement, not a policy change. Numeric/history/probe dictionaries are retained by the measurement worker and can themselves grow traced memory; complete records are streamed before optional prototype buffer release. No raw MT state, object IDs, graph dump or academic record is archived.

The light callback controls omit the expensive generation census, while other inputs, callbacks and safety guards remain matched. Timing includes diagnostics and validation as labeled; it is not a new uninstrumented baseline or a causal hardware-controlled estimate. Desktop load, CPU thermals and order are not randomized.

## Results

Primary series: [retention matrix](testing/ga-retention-phase5/20261028T141153624951+0800/summary.json). [Numeric analysis](testing/ga-retention-phase5/20261028T143832395567+0800-analysis/analysis.json) retains raw samples, input hashes and matched-policy calculations.

| Fresh worker | Measured runs | Post-GC working set MiB, first to last | Working-set delta MiB | Private-commit delta MiB |
|---|---:|---:|---:|---:|
| ram-small-A | 12 | 190.672 to 191.699 | +1.027 | +0.891 |
| ram-small-B | 12 | 190.516 to 191.699 | +1.184 | +0.891 |
| ram-medium-A | 12 | 229.203 to 235.113 | +5.910 | +5.867 |
| ram-medium-B | 12 | 229.496 to 234.875 | +5.379 | +5.336 |
| ram-large | 2 | 221.625 to 226.641 | +5.016 | +5.000 |

Across every successful run, all sampled run-owned models and reporting leases were released, and post-release Subject/Faculty/Room/Section/TimeBlock counts returned exactly to the worker's prepared baseline. For example, Small's prepared baseline includes 12 Subjects and 6 Faculty; the much larger total TimeBlock count also includes the legacy module's hardcoded default student calendars. Those unused import-time objects stay constant, are not institutional records or scenario inputs, and are not misclassified as leaked run objects.

The independently started cohorts show reproducible modest working-set/private-commit growth, **not** a demonstrated process-memory plateau. The two Small workers finish near 191.7 MiB working set; Medium finishes near 234.9-235.1 MiB. Cold pre-runtime working sets were about 30.7-31.7 MiB; post-two-warm-up values were about 190.4 MiB for Small and 216.3-218.0 MiB for Medium. Those initial changes include Python/pandas/import/bootstrap/fixture preparation as well as warm-up, not just GA allocation. Complete cold and warm-up points remain in JSON.

The traced Small series (six measured runs) grew from 52,029 to 156,471 live traced bytes after release; Medium grew from 63,696 to 169,367 bytes. Snapshot differences include pandas index/block allocations, small dynamic attribute-name/runtime allocations and retained diagnostic dictionaries. No live copied-model graph accumulated by the measured model census or sampled roots. Snapshot attribution does not identify the full owner chain of every string/native block. It would be incorrect to call all residual bytes either a proven library cache or a leak.

Working set and private commit increased together in several workers. Thus simply invoking OS resident-page caching is not a complete verified diagnosis. Native/runtime allocator retention, fragmentation and untraced caches remain possible explanations. There is no subtraction of traced bytes from working-set bytes to invent a native-memory total. More or longer runs and allocator-specific evidence would be required for an unbounded-leak conclusion. Results also do not establish stability at the larger original three-generation budget or in a long-running application server.

With the optional observer enabled, Small retained 10/11/13 scored candidate roots for seeds714/715/716; Medium retained 21/10/12. While held, tracked Subject counts rose to 132/144/168 and 528/264/312 respectively, and sampled model references remained alive. After clearing/resetting the original observer and collecting, Subject counts returned to 12/24 and all other modeled types and sampled roots returned to baseline. This is confirmed **scoped owner retention**, not an accumulating leak after release, and does not imply the production observer should be disabled. The direct benchmark default is observer-off.

Large is deliberately limited to two untraced measured runs and one traced measured run. All passed parity and release checks; one traced point cannot support a trend or a plateau claim. Absolute values must not be pooled with the previous memory study: import isolation and search budgets differ. Original Phase2 reference parity separately passed at all three scales.

Matched seed714 descriptive means (12 counter runs, three light-callback runs, three traced runs per scale):

| Scenario | Light callback s | Counter/census callback s | Traced s | Counters / light | Tracing / counters |
|---|---:|---:|---:|---:|---:|
| Small | 2.367562 | 2.821849 | 13.226212 | 1.192x | 4.687x |
| Medium | 6.674682 | 7.460220 | 39.143211 | 1.118x | 5.247x |

These timings cover the original `engine.run` plus the respective measurement callback. The light case still has a safety watchdog, history/root sampling and final-state ownership; it is not an instrumentation-free timer. GC censuses themselves allocate temporary object lists. Tracing and records add large overhead. Cohorts ran sequentially in fixed order on an uncontrolled desktop; ratios are observations, not precise isolated causal overhead estimates or production speedups. Every sample, mean, median, min/max and sample deviation is retained in the analysis.

## Copy ownership, prototype and checkpoint correctness

Inspection and the prior actual-final census found no extra off-root Subject objects or duplicate offering objects within these final chromosomes. Required graph edges include Subject -> Faculty/Section/Room, component lists -> TimeBlocks, TimeBlock -> Subject/Faculty/Section, and Faculty/Room/calendar/assignment lists back into the graph. These aliases/cycles explain why shallow copies or calendar removal are not safe substitutions. Large unassigned calendars are still used for exact allowed-slot, fixed-reservation, reset and mutation behavior.

The isolated prototype changes **only benchmark reporting ownership**: retain the latest full callback state versus retain only the final state, while processing the same history/measurements. It does not change engine selection, copies, fitness, best-ever isolation or any production checkpoint/authority action. A second diagnostic drops already-streamed numeric report buffers and comparison digests. These are not chromosome-pruning or production RAM optimizations.

[Paired ownership records](testing/ga-retention-phase5/20261028T143243221229+0800/summary.json), two seeds per scale, preserved exact assignments, histories, final fitness, hard admission and final RNG state. Traced peaks below cover execution, final validation and probes, not a pure detached kernel:

| Scenario | Seed | Retain-last peak MiB | Final-only peak MiB | Prototype minus prior KiB |
|---|---:|---:|---:|---:|
| Small | 714 | 29.144590 | 29.285702 | +144.498 |
| Small | 715 | 29.569045 | 29.292596 | -283.084 |
| Medium | 714 | 72.246211 | 72.216858 | -30.058 |
| Medium | 715 | 62.928085 | 62.928864 | +0.797 |

The direction changes between seeds. **No consistent peak-memory saving is established**, and no production integration is recommended. The experiment changes benchmark roots, not the engine's required population/best copies. Production publication/authority/checkpoint actions must still occur at their original boundaries; this prototype does not authorize omitting them.

Dropping four already-streamed worker records/comparison digests reduced live traced allocations by 14,676-15,228 bytes depending on scale/policy. This is a directly measured, small **instrumentation-buffer release**, not GA memory savings or proof that the larger process-memory residual has been explained. Substantial residual traced bytes remain after that release.

Checkpoint verification uses the **original** graph codec, strict validator and resume path, entirely in memory. The callback encodes a real generation-zero state immediately, retains only its encoded bytes, and releases sampled paused models after returning. Decoding/validation must then resume to exact uninterrupted assignments, history, final score and RNG state. A deliberately changed engine fingerprint must be rejected by original validation. No historical checkpoint is opened or altered, no format is migrated and no fingerprint is bypassed. Original persisted-checkpoint regressions separately use owned temporary stores.

Both [Small and Medium checkpoint/ownership cases](testing/ga-retention-phase5/20261028T143822354811+0800-checkpoint-ownership/) passed. Mutable-node intersections were zero between original and deepcopied best, and between best and population. Internal Subject/Faculty/TimeBlock aliases were preserved; changing clone availability and assignment-list bookkeeping did not mutate the source and was restored before original hard admission. This is a controlled clone test, not a new mutation operator.

The immediately encoded callback released sampled paused model roots. Original graph decoding/validation resumed to exact uninterrupted assignment/history/fitness and RNG digests. Engine-fingerprint tampering was rejected. No checkpoint file was written by these diagnostics and no historical checkpoint was opened. Existing persisted-checkpoint tests are reported separately below.

## Assessment and recommendation

**Recommendation: leave production GA copying unchanged and investigate further before optimizing.** The controlled series do not demonstrate sustained post-release GA model-graph retention. They do reproduce smaller process working-set/private-commit drift and residual traced growth whose complete cause is not established. Those observations are compatible with several allocator/cache/ownership mechanisms; they do not prove absence of every Python/native leak.

Necessary mutation isolation, cyclic aliases, best-ever independence and strict continuation remain intact. No unnecessary copied offering graph has been demonstrated here. The safe reporting-root prototype preserves behavior but provides no consistent peak reduction. Streaming/releasing diagnostic buffers can keep the measurement harness lean, yet the measured release is only about 15 KiB.

A useful next investigation would hold search parameters/import context constant for longer replicated runs, measure reporting/progress/checkpoint ownership in an owned fictional application process, and obtain allocator-specific evidence before attributing native/private-commit growth. Do not remove calendars, alter copying inside operators or add production GC/allocator changes based on the current data. This study stops before any such integration.

No production optimization is implemented or recommended from a large-object census alone. Do not remove unassigned slots, share mutable calendars across candidates, discard zero-assignment faculty, disable score-observer identity protection, change best-ever ownership, soften constraints or alter checkpoint validation. Teaching targets and warning/hard ceilings remain unchanged. Production institutional authority/publication remain blocked where unconfigured.

## Validation, historical failure and preservation

The initial reference job stopped **before any GA execution** because the new GC census assumed every object's type exposed a string `__module__`; one exposed a descriptor. The [failed record and diagnosis](testing/ga-retention-phase5/20261028T140646547233+0800/) are retained. The new-tool correction checks the module attribute's type and has a focused regression test. No production defect was claimed or patched. Subsequent reference/matrix results are separate artifacts.

Fresh tests: **92 passed, zero failed or skipped**. [11 new Phase5 tests](testing/ga-retention-phase5/20261028T143944126822+0800-phase5/command.json) passed in 30.30 pytest seconds. [81 existing regressions](testing/ga-retention-phase5/20261028T143945215287+0800-regressions/command.json) passed in 127.22 seconds: 21 Phase2 benchmark tests, 12 prior memory tests and 48 D10 engine/API/checkpoint tests. These are fresh executions under fictional import isolation, not reused historical passes or a full application acceptance suite.

Warnings are retained: an AnyIO `PytestAssertRewriteWarning` in each selection comes from importing the isolation bootstrap's framework dependencies before pytest assertion-rewrite configuration. It concerns rewriting that already imported dependency, not disabled assertions or failing parity. The regression selection additionally retains the existing Starlette/HTTPX and AnyIO BlockingPortal deprecations. No dependency update or warning suppression was used.

The new tests cover schema-only import counts, rejection of institutional text/CSV parsing, the original census descriptor failure, explicit plain-list/Lease weakref limitations, fail-closed memory/query guard termination, bounded replicated matrix design, real repeated-run output/root/model-count parity, unchanged RNG/GC settings, mutable-copy isolation, original checkpoint resume/fingerprint rejection and reporting-callback parity. Original persisted-checkpoint/child-process tests ran with a bootstrap adapter around their unchanged entrypoints and temporary stores; they did not parse institutional rows or write retained checkpoints.

All **19 successful series workers** passed, with **92 measured and 28 warm-up complete engine executions**. Two additional in-memory checkpoint/ownership scenarios passed. The initial pre-execution census failure remains archived separately. No runtime deadline or sampled memory-watchdog stop occurred in successful measurements. The matched-seed audit checks assignment hashes, complete histories and final RNG digests across independent cohorts, observer settings and prototype policies.

New Python files are `backend/benchmarks/retention_runtime.py`, `retention_phase5.py`, `retention_ownership.py`, `retention_child.py`, `backend/tests/performance/test_retention_phase5.py`, and `docs/testing/ga-retention-phase5/run_checks.py`, `analyze.py`, `audit.py`. This report and the individually inventoried JSON records complete the new scope. Existing files modified: **none**.

Final audit passed: **1,509 existing paths** and all **23 academic files** remain byte-identical. There are **41 new files** (eight Python, thirty-two JSON and this report), with **40 artifact hashes** verified; the manifest excludes its own hash. Privacy and whitespace checks passed. The only tracked local changes remain the pre-existing protected preferences/settings modifications, unchanged and unstaged.

The [manifest](testing/ga-retention-phase5/manifest.json) records the exact new-file inventory, raw hashes, privacy checks, baseline preservation and all unsuccessful/successful evidence. The audit does not parse institutional faculty names; it checks secret/receipt patterns, sanitized test output and structurally fictional/numeric exports. All source/application/data/checkpoint/history bytes from the 1,509-path entry baseline must match; an unexpected mismatch stops review without resetting any file. Nothing is staged, committed or pushed.

## Windows 11 reproduction

From the repository root, with the existing virtual environment. Run experiments sequentially before tests:

```powershell
.\.venv\Scripts\python.exe -B backend/benchmarks/retention_phase5.py --part reference
.\.venv\Scripts\python.exe -B backend/benchmarks/retention_phase5.py --part retention
.\.venv\Scripts\python.exe -B backend/benchmarks/retention_phase5.py --part ownership
.\.venv\Scripts\python.exe -B backend/benchmarks/retention_ownership.py
.\.venv\Scripts\python.exe -B docs/testing/ga-retention-phase5/analyze.py
.\.venv\Scripts\python.exe -B docs/testing/ga-retention-phase5/run_checks.py phase5
.\.venv\Scripts\python.exe -B docs/testing/ga-retention-phase5/run_checks.py regressions
.\.venv\Scripts\python.exe -B docs/testing/ga-retention-phase5/audit.py
```

Every run creates new evidence rather than overwriting history. Analysis/audit perform no GA or database execution. Tests bootstrap schema-only data **before collection**. Existing child-process checkpoint and benchmark test entrypoints are wrapped by `retention_child.py` to apply the same isolation; original child/test sources, algorithms, persisted bytes and fingerprint checks remain unchanged. Regression SQLite/checkpoint fixtures are owned and fictional. No PostgreSQL test, production application, browser or deployment is invoked. No C++ toolchain is installed or used. Stop before production integration.
