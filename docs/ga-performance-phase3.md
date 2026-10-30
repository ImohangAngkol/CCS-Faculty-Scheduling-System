# Phase 3: C++ acceleration feasibility study

2026-10-28, Asia/Manila. Source commit `1423812e13a5791a550c893ef6b17bfef4b4ebfb`. **Python feasibility analysis completed; native implementation/build/parity/performance are BLOCKED by the missing compiler.** The user explicitly confirmed: "No compiler available; document blocker". No compiler, binding package or other dependency was installed. No C++ source, binary, production integration or accelerated engine execution is presented as tested.

Recommendation: **do not integrate a scalar interval-overlap kernel** on the present evidence. Its exclusive computational share is negligible. Retain Python as the oracle and profile representation/conversion costs further before deciding whether a larger, independently specified batched operation deserves a native experiment.

## Inspection and the bound established before the experiment

Read the complete Phase 2 report, manifest, audit, fixtures, benchmark source and all retained profiler rows; verified all 16 Phase 2 artifact hashes and 1,454 original baseline paths before editing. Also reviewed the actual V2 constraint/admission/construction boundaries, `validate_publication`, `payload_to_chromosome`, `_validate_baseline_components`, original time helpers, resource conflict checks, crossover/mutation validation and D10 fixtures/tests. No AGENTS.md was found.

The [Phase 2 experiment](testing/ga-performance-phase2/20261028T113836085281+0800/results.json) remains the uninstrumented scheduling baseline: 15 successful runs, five seeds per scale, population 4, three generations. Its normal means are 5.067062 / 9.032717 / 31.435525 seconds. They were not remeasured, replaced or pooled with these instrumented runs.

The original Large profile's 56.0% cumulative `deepcopy` share includes recursive graph traversal, allocation, reconstruction and consumers nested above copying. A numeric predicate cannot remove that family. `_validate_baseline_components` was 15.53% cumulative but only 3.56% exclusive; much of its child work repeatedly parses calendar strings and constructs Python containers. Before implementation, the deliberately optimistic ceiling from making the *entire component function free* was `1 / (1 - f)` = 1.098641x / 1.186935x / 1.183889x for Small/Medium/Large. This is an impossible budget for a tiny numeric kernel, not a claimed achievable speedup.

The isolated deterministic candidate characterized here is the actual `services.ga_v2_constraints.overlap(a, b, c, d)`. It is pure comparison CPU work and has no parsing, copying, object-graph or authority responsibilities. Full profiles were needed because it did not appear in Phase 2's top 30 cumulative rows. Detailed profiling confirms that it does **not** have meaningful exclusive cost relative to the complete engine. A broader component validator was not mislabeled as a numeric-only operation or silently reimplemented.

## Python oracle and the proposed native boundary

The unchanged original function returns `a < d and c < b`. For already validated positive-duration intervals `[a,b)` and `[c,d)`, equality and adjacency at an endpoint are nonoverlapping. Containment, equal nonempty intervals and partial intersections overlap. The primitive itself does not enforce a valid range: for example `(450,450,420,480)` and `(480,450,420,510)` return True. Those outputs are retained as characterization, not repaired. Upstream validation rejects invalid commitments. There is no rounding or 30-minute snapping in this predicate.

The original primitive supports Python comparison semantics and short-circuiting; invalid incomparable types can raise TypeError. A future native proposal would have to specify a prevalidated, bounded integer-minute domain, preserve the original result there, and leave unsupported values with their original Python path. No coercing FFI wrapper, numeric conversion, exception translation or silent fallback was implemented. Out-of-domain Python behavior must not be represented as native parity without tests.

The original input parsers are intentionally distinct:

- `ga_v2_constraints.minutes`: full `\d{1,2}:\d{2}` regex, then integer conversion; hour <=23 and minute <=59. It accepts single-digit hours and Unicode decimal digits supported by those Python operations. Malformed strings raise `ConstraintError` with code `INVALID_TIME`; non-string inputs raise TypeError. Whitespace is not stripped.
- `chromosome_service.time_to_minutes`: `str(value).strip().split(':')`, two `int` values, then `hour*60+minute`. It does not itself enforce a local-day range; `24:00` produces 1440. It is used in reconstruction, not an interchangeable strict parser.
- `Functions.convert_time_to_minutes`: stripped `datetime.strptime(..., '%H:%M')`; its accepted formatting and errors differ. For example `7:3` is accepted here and rejected by the strict constraint parser.

A port must not collapse these behaviors into a new parser. The current test corpus checks differences explicitly. Higher layers retain supported days, 07:30-22:00 coverage, exact 30-minute boundaries, duration/pattern and laboratory continuity, calendar membership, faculty eligibility, workload, faculty/section/room conflicts, preassignments, fixed commitments, provenance and publication checks. Days and resource identities are outside the numeric predicate. Nothing in this experiment replaces those layers or installs an institutional provider.

## New measurements

Evidence: [full study JSON](testing/ga-performance-phase3/20261028T121013926009+0800/study.json). Each full profile uses a fresh worker, seed 714, the same Phase 2 fixture/parameters, original constructor/operators/scorer/admission and the existing nonpublishing boundary. Only the *benchmark's profile serialization helper* is temporarily extended to retain every function's statistics; no production symbol is replaced. Original data-only synthetic scoring aliases are restored as in Phase 2. File/network/database guards remain active during kernel execution. All three histories and assignment hashes match Phase 2 seed714 exactly.

| Scenario | Profiled engine s | Overlap calls | Overlap exclusive s | Profiled share | Conditional infinite-kernel ceiling |
|---|---:|---:|---:|---:|---:|
| Small | 38.117979 | 3,169 | 0.0007859 | 0.002062% | 1.000021x |
| Medium | 46.138422 | 12,802 | 0.0026649 | 0.005776% | 1.000058x |
| Large | 88.583294 | 38,026 | 0.0075915 | 0.008570% | 1.000086x |

These are cProfile observations, one per scale. Instrumentation and desktop variability affect the fractions; they are not precise uninstrumented CPU budgets. The model is `T_new = T * (1-f+f/s) + B`, where `B` includes binding/packing/unpacking and `s` is actual kernel acceleration. Setting `s` to infinity and `B` to zero gives the table's optimistic conditional estimate, not a rigorously measured end-to-end bound. Applying Large's fraction to the historical 31.435525-second mean would imply only about 2.7 milliseconds saved under those assumptions. No accelerated GA run was executed and no actual GA speedup is claimed.

In the new Large profile, copying is 50.243414 cumulative seconds (56.72%), including 15.095548 exclusive seconds in `deepcopy` itself; its recursive helpers have separate exclusive costs. `_validate_baseline_components` is 3.148674 exclusive / 13.375483 cumulative seconds. `chromosome_service.time_to_minutes` is 7.349311 exclusive / 10.010755 cumulative seconds over 5,019,222 calls. That parser performs Python string conversion/splitting and integer/object allocation, not just interval arithmetic. `external_conflict` including its descendants is only 0.523800 seconds. These nested costs must not be summed as independent percentages or offered as removable numeric-kernel time.

Separate timing-only Python microbenchmarks use the saved seed714 schedules at each scale: 96 / 192 / 384 meeting slots. Each parsed slot is compared to the explicitly fictional 09:00-10:00 reservation. This constructs a controlled predicate workload; it is **not** a day/resource-aware conflict validator. Nine repetitions of 200 identical batches follow profiling, without concurrent tests, cProfile or tracemalloc. Every sample is retained. Scalar observations include the Python loop and argument unpacking. Batched observations include Python list construction. Text conversion uses the original strict parser plus fixture-wrapper/import overhead; it is not native marshaling cost.

| Scenario | Warm scalar ns/pair, mean +/- sample SD | Python batch microseconds, mean +/- SD | Text-to-numeric batch microseconds, mean +/- SD |
|---|---:|---:|---:|
| Small | 115.03 +/- 58.11 | 14.32 +/- 6.29 | 395.66 +/- 109.37 |
| Medium | 132.70 +/- 55.82 | 31.42 +/- 14.75 | 722.21 +/- 104.34 |
| Large | 124.08 +/- 35.14 | 60.05 +/- 6.91 | 1442.67 +/- 158.55 |

The first observed scalar costs were 1.0 / 2.2 / 1.6 microseconds; first observed conversion costs were 307.8 / 946.0 / 1545.2 microseconds. These occur **after runtime import**, are single noisy observations and are not fresh-process cold-start measurements. They cannot support a native cold/warm claim. Desktop load, CPU power/thermals and cache state were not controlled; repetitions are consecutive observations, not independent hardware experiments or confidence intervals.

The boundary budget is tiny: a scalar FFI call would have to beat the Python predicate's roughly 70-270 ns observed range while also paying conversion overhead. Whether it can do so is **not measured**. A batch might amortize that boundary but still cannot remove parsing, copying or authoritative checks. Cases where C++ is slower, standalone native throughput, native batch cost, cold library loading, Python-to-native packing and build time are all **NOT MEASURED**, not zeros. No performance claim substitutes an assumed ctypes cost or a Python batch result for C++ evidence.

## Validation and compiler blocker

New [Python oracle tests](../backend/tests/performance/test_native_feasibility.py) cover deterministic edge cases; 20,000 randomized numeric inputs with an independent valid-range formulation; every 30-minute adjacency boundary; original malformed-time/type errors and parser differences; faculty/section/room identities on multiple days; invalid fixed times; nonmutation; and honest unavailable-native metadata. This is a future parity corpus, **not C++ parity**. Existing original D10 tests cover full admission, constructor/operator behavior, resource reservations, seed rejection and checkpoint continuation.

Fresh results: **151 Python tests passed, zero failed or skipped**. The [46 new oracle tests](testing/ga-performance-phase3/20261028T121346399006+0800-oracle/command.json) passed in 4.25 pytest seconds. The [105 existing regressions](testing/ga-performance-phase3/20261028T121347399973+0800-regressions/command.json) passed in 148.59 pytest seconds: 21 Phase 2 tests, 48 D10 engine/API tests and 36 fitness/resource tests. These are new executions, separate from Phase 2's historical results. Two existing Starlette/HTTPX and AnyIO BlockingPortal deprecations remain recorded; no dependency was changed. All three full profiles completed and matched their original outputs. Native parity cases executed: **zero**. Frontend, PostgreSQL and institutional acceptance were not run or inferred.

The toolchain inspection found no `cl`, `clang++`, `g++` or `cmake` on PATH, no compiler in the checked LLVM/MinGW locations, and neither Visual Studio root nor vswhere at the checked locations. The user confirmed that no compiler is available. Accordingly native source implementation, compilation, native parity and native timings were stopped. No substitute compiler was downloaded and no prebuilt binary was used.

For a later authorized native build, the requirement is a supported Windows x64 C++ toolchain and SDK (for example an approved MSVC Build Tools C++ setup), with compiler version/flags captured. A small exported C ABI DLL could use Python's existing stdlib ctypes without installing pybind11. That is a proposed interface, not a built or benchmarked one. An actual native phase would need source/binary hashes, explicit checked types and ABI, scalar/batch parity on this corpus, output/error compatibility, conversion-only and in-native timings, fresh-process loading tests and finally equivalent end-to-end runs before integration is justified. This phase provides no imaginary build command or tested-binary claim.

## Preservation, inventory and reproduction

The new [baseline](testing/ga-performance-phase3/preservation-baseline.json) preserves all 1,454 original paths plus all 17 Phase 2 paths: **1,471 paths**. It includes the Git index, all 23 academic data paths, protected preferences, the user's modified settings and tiny script, original GA/operators/scorer/RNG/workload rules, migrations, checkpoints, saved schedules and historical evidence. Phase 2 files and its manifest are not rewritten by the Phase 3 audit. No existing file is modified, no database or publication operation occurs, and no staging/commit/push occurs. Existing regression tests separately use owned fictional SQLite/store/provider fixtures; that does not constitute production authority or institutional publication.

New files are `backend/benchmarks/native_feasibility.py`, `backend/tests/performance/test_native_feasibility.py`, this report, and the inventoried Phase 3 JSON/tooling under `docs/testing/ga-performance-phase3/`. The [manifest](testing/ga-performance-phase3/manifest.json) contains the exact inventory, fresh test outcomes, privacy findings and raw artifact hashes; it excludes itself from its own artifact hashes. It is separate from the immutable Phase 2 manifest.

Final audit passed: **10 new files** (four Python, five JSON, one Markdown), **nine artifact hashes**, zero privacy findings, whitespace checks passed, and all **1,471 entry paths** unchanged. The only tracked local modifications remain the pre-existing protected preferences and settings changes; the user's untracked tiny script and all Phase 2 additions remain intact. Nothing is staged.

From the repository root with the existing virtual environment, run profiling and reference timings before tests, not concurrently:

```powershell
.\.venv\Scripts\python.exe -B backend/benchmarks/native_feasibility.py --scenario all
.\.venv\Scripts\python.exe -B docs/testing/ga-performance-phase3/run_checks.py oracle
.\.venv\Scripts\python.exe -B docs/testing/ga-performance-phase3/run_checks.py regressions
.\.venv\Scripts\python.exe -B docs/testing/ga-performance-phase3/audit.py
```

Each execution creates new owned evidence rather than overwriting a past run. All workers have finite deadlines. Unexpected baseline changes stop the audit without resetting any file. Secrets, partial tokens/receipts, credential URIs and private names are checked locally without printing private faculty data. No PostgreSQL test or database migration is invoked.

The next decision should be **further profiling of batched representation and time conversion**, with unchanged Python as the oracle, rather than integrating this scalar predicate or rewriting the scheduler. Copy-graph changes would be a materially different architecture/compatibility task. This study does not authorize that change. Production institutional authority remains unchanged and blocked where unconfigured. No later phase is started automatically.
