# Phase 2 — scaled fictional Python GA performance evaluation

2026-10-28, Asia/Manila. Source commit `1423812e13a5791a550c893ef6b17bfef4b4ebfb`. This is a standalone kernel experiment using entirely fictional resources, not institutional acceptance, a production scheduling benchmark or a Python-versus-C++ comparison. No C++ was implemented. No existing source or input file was edited.

The user's tiny-fixture result (five runs averaging 0.294288 seconds, fitness zero throughout) is historical user-reported context. It was not rerun or overwritten. Its dataset, scoring inputs, parameters and observation overhead differ from this experiment, so these results must not be presented as a speedup/slowdown ratio against that number.

## Fixtures and preserved semantics

| Scenario | Faculty | Offerings | Sections | Lecture / laboratory rooms | Offered / target teaching units |
|---|---:|---:|---:|---:|---:|
| Small | 6 | 12 | 3 | 2 / 2 | 36 / 99 |
| Medium | 12 | 24 | 6 | 3 / 3 | 72 / 198 |
| Large | 24 | 48 | 12 | 5 / 5 | 144 / 396 |

Each section has four unique fictional offerings: two three-hour lecture offerings and two two-hour lecture/three-hour laboratory offerings. Each offering carries three credit units. Laboratory contact hours are not counted as additional teaching credit units. Sections, faculty codes, room names, course codes, source rows and static snapshot provenance are explicit and fictional. Eligibility is an explicit three-member pool for each course. The Small scenario deliberately includes one positive-target faculty member with no currently eligible offerings, rather than silently removing that member from underload scoring.

The benchmark retains the actual Faculty model: teaching target `max(0, 24-admin-research-extension)`, warning above 30 teaching units and hard ceiling 40. Admin/research/extension loads are fixed hypothetical inputs. Reported total workload equals assigned teaching units plus those fixed non-teaching loads. All three scenarios are intentionally underloaded; this permits examination of zero assignments and proportional target shortfall without pretending every target is achievable.

Scoring uses explicit fictional subject/day/time/style preferences, varied importance and faculty priority, plus unchanged `GASetting()` source defaults. The user's modified settings JSON and private preferences are not the experiment's scoring inputs. Original loaders read newly owned temporary fictional JSON files; their data-path aliases and the faculty universe are restored afterward. No scoring, scheduling, eligibility, operator or fingerprint function is replaced. The engine's genuine repository fingerprint remains a stability check; it is not spoofed or represented as institutional authority. A separate synthetic-input SHA-256 binds fixture configuration.

One fictional Monday 09:00–10:00 reservation per section exercises the V2 snapshot path; the first also reserves one faculty member and lecture room. These rows are time reservations outside genes, not additional teaching-credit outputs. Workload totals describe the GA offering set and fixed hypothetical non-teaching loads, not a complete institutional load including unspecified external-course credits. No enrollment/seat capacity data is fabricated.

Before each measured search, the original constructor must produce a separate admissible feasibility witness using fixed seed 10101 and at most five restarts. The witness is discarded and never used as a search seed. It establishes existence of a valid schedule for these inputs, not optimality. The measured engine then receives the requested seed. `SEARCH_EXHAUSTED` means a bounded search failed; it is not mathematical infeasibility. The original `INPUT_CAPACITY_REJECTED` remains a separate invalid-input classification. The fixtures have generous original calendar coverage; Large means larger than the smoke fixture, not representative institutional scale or high calendar utilization.

## Measurement protocol

The main experiment uses population **4**, **3** generations, one fresh chromosome per generation, two internal crossover/mutation attempts, five constructor restarts and three candidate attempts. The five search seeds are **714–718**, one repetition each, at every scale. These short searches support performance characterization and observed improvement, not a claim of convergence.

Each trial runs sequentially in a fresh Python interpreter with `PYTHONHASHSEED=0`, whitelisted OS environment and no inherited database URLs or approval flags. An additional warm-up worker per scenario is recorded but excluded. Every worker also runs its own feasibility witness in preprocessing, which warms constructor paths. This is not a cold-start benchmark. Imports are excluded from engine timing; the worker's end-to-end elapsed time is separately recorded. Desktop background load, CPU power policy, thermals and OS cache state were not experimentally controlled. Between-seed standard deviation includes algorithmic path variability as well as runtime noise; five seeds are preliminary evidence.

`engine_seconds` is `perf_counter` wall time around the actual unchanged `engine.run`. It includes original construction/operators/fitness, engine-internal validation, source/input fingerprint reads, in-memory boundary callbacks and lightweight call counters. It is not pure GA-operator CPU time. Preprocessing (fixture setup, temporary scoring files, snapshot and witness) and post-search hard validation/fitness-breakdown extraction are measured separately. The engine-internal validation cannot be separated by subtraction; no such subtraction is made. Persistence is absent, recorded as NONE rather than a measured zero-duration operation.

Normal timing runs have neither cProfile nor tracemalloc enabled. One extra run of seed 714 per scenario measures Python allocation peak with tracemalloc; another separately profiles cumulative/self function time. Instrumented elapsed times never enter the timing summary. Allocation peak is **not total process RSS** and does not account for every native/OS allocation. Cumulative profiler rows overlap through call nesting and must not be summed as independent costs.

Diagnostics distinguish original operator calls from admission events. `survivor:ACCEPTED` can count the same candidate again; these are not unique generated individuals. Internal operator retry iterations are not instrumented, so the harness does not invent their exact counts. Per-trial dictionaries include construction/crossover/mutation call counts, accepted/rejected/no-candidate events and construction search failures. Deadline-limited workers have unknown internal counts and no fabricated final schedule. Failed trials remain in the evidence and outside successful-time means.

## Measured results

All **15/15 uninstrumented trials passed**, with zero normal-run failures. All three excluded warm-ups and all three cProfile runs passed. The original Large allocation attempt exceeded 180 seconds; that record remains intact.

| Scenario | Mean s | Median s | Min to max s | Sample SD s | Final fitness range |
|---|---:|---:|---:|---:|---:|
| Small | 5.067062 | 4.419783 | 4.183137 to 7.881174 | 1.584963 | 4930 to 6045 |
| Medium | 9.032717 | 8.909804 | 7.929879 to 10.666816 | 1.019472 | 8640 to 11520 |
| Large | 31.435525 | 30.634870 | 28.275823 to 35.184548 | 3.058942 | 19635 to 21735 |

All histories begin above zero and all 15 final fitness values improve on generation zero. Best-ever fitness is monotone non-increasing in every successful normal/profile/allocation run. This is observed improvement over three generations, **not convergence or optimality**. Seed714 moves from 6160 to 4930 (Small), 10825 to 10290 (Medium), and 22465 to 21735 (Large). Each saved breakdown sums to its original final fitness.

| Scenario | Preprocessing s, range | Post-validation / breakdown s, range | Python allocation peak, separate run |
|---|---:|---:|---|
| Small | 0.204 to 0.218 | 0.152 to 0.182 | 97.858 MiB |
| Medium | 0.367 to 0.409 | 0.339 to 0.412 | 130.113 MiB |
| Large | 1.274 to 1.926 | 1.059 to 1.439 | 201.614 MiB in separate 300 s bounded follow-up |

The [allocation-only follow-up](testing/ga-performance-phase2/20261028T115407034419+0800-large-allocation-followup/allocation-followup.json) used the identical Large/seed714 configuration with a 300-second worker bound. It succeeded: **211,407,145 bytes (201.614 MiB)** peak traced Python allocation and **216.194390 seconds** instrumented engine time. Its history and assignment hash match the normal seed714 trial. This is not RSS or a normal timing result. The original 180-second timeout was not overwritten; no normal trial was rerun or pooled with the follow-up.

Final aggregate underload is 63/126/252 units in Small/Medium/Large, with zero overload in these trials. Small has one zero-assignment faculty member in every trial; Medium and Large have none. The unqualified Small member still contributes the full proportional shortfall penalty; tests independently verify the all-zero case gives `6 * 10 * 25 = 1500` workload penalty. These observations establish accounting correctness and residual shortfall, not optimal fairness. Preferences compete with workload in the unchanged objective.

| Seed714 / timing run | Construction calls | Crossover calls | Mutation calls | Accepted admission events | Rejected/no-candidate events | Construction exhaustion |
|---|---:|---:|---:|---:|---:|---:|
| Small | 7 | 73 | 3 | 38 | 68 | 0 |
| Medium | 7 | 67 | 3 | 34 | 64 | 0 |
| Large | 7 | 66 | 3 | 34 | 63 | 0 |

All timing trials have zero construction search failures. Operator `NO_CANDIDATE` events remain visible and are not failed whole searches. Normal successful histories/assignment hashes for seed714 match their separately successful instrumented runs. The main experiment ran 11:38:36 to 11:51:48 +08:00 on Python 3.14.2, Windows 11 build 26200, x86-64, 16 logical CPUs. Hardware model, OS power policy and background processes were not controlled or used to assert portability.

The [complete JSON](testing/ga-performance-phase2/20261028T113836085281+0800/results.json) contains every trial, history, score breakdown, fictional assignment signature, workload/target/underload records, engine/input identities, phase timings, allocation peaks and top 30 cumulative profiler rows. The [pilot](testing/ga-performance-phase2/20261028T113222652314+0800/results.json) uses only Small/seed714/population4/generations2 and is not pooled with the main experiment.

## Validation, isolation and evidence

**105 tests passed:** 21 new benchmark tests, 48 existing D10 engine/API tests, and 36 existing fitness/resource tests. Zero failures/skips in these selections. Earlier 15-test and 20-test preparation selections are retained, not added to that total. No frontend, production database or institutional acceptance was inferred. The earlier benchmark selection and both regression suites completed before normal timing runs; the final 21-case benchmark suite was executed afterward, outside the timing experiment. Starlette TestClient/HTTPX and AnyIO BlockingPortal deprecations remain recorded in the existing regression suites.

The new tests exercise deterministic fixture generation; identical seed histories, assignments and diagnostics; RNG restoration; nonzero scoring; original hard admission and exact coverage at all scales; scoring-source isolation with an unrelated sentinel; workload/zero-assignment underload; separation and cleanup of measurement modes; Option B target clamping; distinct invalid-capacity versus bounded-exhaustion errors; and worker wall-limit reporting. The exact commands, timestamps, exit codes and sanitized output are retained in per-run `command.json` files under the [evidence directory](testing/ga-performance-phase2/).

The benchmark kernel runs under write/network/database guards: file mutations, socket connections, SQLite connections and psycopg2 connections are rejected. The only boundary callback keeps summaries in memory. It never calls API routes, publication, save-best, history or checkpoint writers. The existing D10 regressions separately use owned fictional SQLite/provider/store fixtures; those tests are not benchmark publication or production authority activation. Production D8/D9 providers/gates remain unchanged and blocked where unconfigured.

No new frontend/backend API, database schema, migration, model/workload rule, production GA operator, numerical scoring, versioned orchestration or checkpoint policy was changed. No dependency was installed. Frontend build/browser tests are NOT APPLICABLE to these standalone Python-only additions; previous UI evidence is historical. No PostgreSQL operation or institutional workflow was run. Existing dependency deprecations in the D10/fitness suites remain recorded, not repaired as unrelated cleanup.

The [manifest](testing/ga-performance-phase2/manifest.json) lists exact new paths, artifact hashes, privacy findings and preservation. The pre-edit baseline covers 1,454 paths, including all 23 academic data paths, original GA/model/migration source, retained checkpoints/results/history, Git index, both pre-existing modified data files and the user's untracked tiny script. Final audit passed: every baseline byte is unchanged; all 16 artifact hashes are recorded, and the manifest is the seventeenth new file (excluded from its own hashes). Private faculty names are compared locally during privacy inspection without exporting them; JSON/profile output contains fictional identifiers only. No raw protected file, credential, receipt, cookie, database dump or real faculty row is archived. No staging, commit, push or general cleanup occurred.

## Files and Windows 11 reproduction

New sources:

- `backend/benchmarks/__init__.py` — package boundary; not imported by application routes.
- `backend/benchmarks/scenarios.py` — deterministic fictional fixture generator and static unit snapshot.
- `backend/benchmarks/scaled_python.py` — standalone coordinator/worker, guarded kernel measurement and reporting.
- `backend/tests/performance/test_scaled_python.py` — focused correctness/safety tests.
- `docs/testing/ga-performance-phase2/run_checks.py` — whitelisted, sanitized regression evidence runner.
- `docs/testing/ga-performance-phase2/audit.py` — file/Git-only audit and manifest writer.
- This report and the inventoried JSON evidence. Existing files modified: **none**.

From the repository root, with the existing virtual environment/dependencies:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/ga-performance-phase2/run_checks.py benchmark
.\.venv\Scripts\python.exe -B docs/testing/ga-performance-phase2/run_checks.py d10
.\.venv\Scripts\python.exe -B docs/testing/ga-performance-phase2/run_checks.py fitness
```

Run tests before the benchmark, not concurrently with timing workers:

```powershell
.\.venv\Scripts\python.exe -B backend/benchmarks/scaled_python.py --scenario all --seeds 714,715,716,717,718 --repetitions 1 --population 4 --generations 3 --fresh 1 --operator-attempts 2 --restarts 5 --candidate-attempts 3 --trial-timeout 180 --memory --profile
```

Each execution creates a new timestamped evidence directory and refuses overwrite. Use `--scenario small`, `--seeds`, `--population`, `--generations` and `--repetitions` for a bounded follow-up. Omit `--memory --profile` for timing-only runs. A timeout is retained as `WALL_DEADLINE_EXCEEDED`, not a successful fast run or an infeasibility conclusion. Existing PostgreSQL variables are unnecessary and not inherited by worker/test processes. The experiment does not require institutional authority credentials.

To reproduce the separate allocation-only Large follow-up without retiming the normal trials:

```powershell
@'
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
sys.path.insert(0, 'backend')
from benchmarks.scaled_python import run_worker
source = 'docs/testing/ga-performance-phase2/20261028T113836085281+0800/results.json'
parameters = json.loads(Path(source).read_text(encoding='utf-8'))['parameters']
zone = timezone(timedelta(hours=8))
started = datetime.now(zone)
directory = Path('docs/testing/ga-performance-phase2') / (started.strftime('%Y%m%dT%H%M%S%f+0800') + '-large-allocation-followup')
directory.mkdir(exist_ok=False)
result = run_worker('large', 714, parameters, 'memory', 300)
record = dict(scope='Separate allocation-only follow-up; original evidence retained',
              original_experiment=source, started_at=started.isoformat(),
              finished_at=datetime.now(zone).isoformat(), same_configuration=parameters,
              deadline_seconds=300, result=result)
(directory / 'allocation-followup.json').write_bytes((json.dumps(record, indent=2) + '\n').encode('utf-8'))
print(directory.as_posix(), result['status'], result.get('peak_python_allocated_bytes_NOT_RSS'))
'@ | .\.venv\Scripts\python.exe -B -
```

After a completed experiment and test execution:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/ga-performance-phase2/audit.py
```

## Interpretation and next profiling target

The scaled profile changes the priority suggested by the tiny smoke fixture. In the Large seed714 cProfile run (83.295 instrumented seconds), the leading nested costs were:

| Function / path | Cumulative s | Profiled engine fraction | Calls / interpretation |
|---|---:|---:|---|
| `copy.deepcopy` | 46.680 | 56.0% | 2,561 primitive / 20,621,165 recursive calls; overlaps the consumers below |
| `ga_v2_engine.admit` | 42.214 | 50.7% | 66 original hard-admission calls |
| `validate_publication` | 41.668 | 50.0% | 66 complete validation calls |
| `payload_to_chromosome` | 40.675 | 48.8% | Original detached reconstruction underneath validation |
| `_validate_baseline_components` | 12.938 | 15.5% | Component pattern/duration validation, nested in reconstruction |
| `Functions.convert_time_to_minutes` | 12.883 | 15.5% | 411,076 calls, much of this in `strptime` |
| `faculty_preference_fitness` | 6.466 | 7.8% | Full original scorer; lower cumulative cost than reconstruction here |

These are **instrumented, overlapping cumulative times**, not independent percentages of uninstrumented wall time. Small's profile is more crossover-heavy (73 crossover calls, 11.058 s cumulative); Medium/Large reconstruction dominates. The previously suggested effective-preference hotspot is not supported as the first scaled C++ target by these top cumulative results. Preference-related work remains part of the scorer, but a scorer-only port cannot remove the dominant object copying/reconstruction.

**Recommended next C++ profiling target:** a narrow, detached numeric calendar/interval/component-validation microkernel underneath candidate validation, first measuring data-conversion cost. Use integer minute values and explicit resource indices derived from fictional fixtures, preserve half-open overlap/adjacency and every original duration/eligibility/workload rule, and compare against unchanged Python validation as the oracle. This is a recommendation for a separately approved experiment, not an implemented replacement or justification to bypass `admit`.

Object-graph copying is the largest measured family. A native prototype needs to establish whether marshaling and repeated Python reconstruction would erase a kernel gain; wholesale Faculty/Subject graph replacement would require a new compatibility/design decision. Time parsing/precomputation may also merit a separately reviewed Python control measurement before attributing gains to language choice. No source change or promised speedup follows from this profile alone.

This phase supplies a reproducible Python oracle for any later acceleration experiment. A future native microkernel needs the same fixture/seed/configuration, conversion-cost accounting, hard-constraint and fitness parity, complete zero-assignment faculty accounting, and version/checkpoint policy review. Python object-graph copying or rewriting the scheduler in C++ is not automatically justified by a profiler ranking. No native implementation, algorithmic change or acceleration claim is authorized or included here. Stop after Phase 2.
