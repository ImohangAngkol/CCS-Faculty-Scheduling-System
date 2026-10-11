# Phase 3E: Generation history, inspection, comparison and exports

Administrators can inspect immutable observations from generation zero and each
completed generation of API runs started after this phase. History is separate
from Saved Best, latest-result files and Phase 3D continuation checkpoints.
Inspecting history never starts a worker, updates the live GA context, scores a
candidate, or changes faculty preferences.

## Architecture and provenance

The existing run service validates the survivor population before calling
`GenerationMonitor.report`. Its context-local score collector already contains
the actual survivor scores. `HistoryGenerationMonitor`, installed by the API
router, wraps that report callback **before the collector is cleared**. Outside
`capture_history` it delegates to the original monitor without history capture.
No engine source, fitness function, operator, checkpoint format or notebook was
edited. The existing engine fingerprint therefore remains compatible with
previously saved paused checkpoints.

At the boundary, the adapter selects the minimum already-observed survivor score,
preserving population order for ties. It copies that candidate to the project's
portable chromosome schema. Best-ever content changes only when the original
monitor reports a strict improvement. Continuation seeds best-ever directly from
the validated full checkpoint, never from Saved Best or from a guessed candidate
with a similar penalty. A disagreement between candidate and telemetry penalties
is a recording failure, not an opportunity to rescore.

The background writer receives pure JSON DTOs, never live population references.
It reconstructs copies with the existing chromosome service, runs the Phase 3B
publication gate, calculates descriptive workloads, then publishes the record.
Identical generation-best/best-ever identities share one validation pass.
Schema and integrity checks precede historical reads. No new fitness call or RNG
draw is used by capture, validation, history inspection or exports.

Workload targets are captured from the original faculty models:
`max(0, 24 - admin - research - extension)`. Subject credit units are counted once
per offering, not once per meeting. Normal faculty include those with no assigned
offerings. External preassigned instructors appear separately in schedule rows
and receive no normal workload/preference analysis. The original hard rules
remain authoritative: explicit eligibility, faculty/room/section conflicts,
teaching load above 40, institutional fixed reservations, Palad's ITE184/ICT3A
locks, component meeting patterns and continuous three-hour laboratories.

The frozen configuration is an exact provenance copy of existing settings and
can contain inactive legacy fields such as `target_teaching_load=12`. Capturing
that field does not activate it or use it as a teaching target. Workload rows
always use the faculty model's 24-minus-release target; no legacy 12-unit target
is used by the history service or viewer.

Boundary evaluations currently return totals only. Missing penalty breakdowns
and per-faculty preference satisfaction are **null with explanations**, not zero.
When the existing final evaluation returns a breakdown, it is saved as a separate
candidate analysis attachment. It is available only for an exact candidate ID,
penalty and input/engine fingerprint match. Earlier generation files are never
rewritten to attach it. This attachment is an observation under the original
frozen inputs, not a current-preference reanalysis. The live FitnessAnalysis page
and its existing calculation service remain unchanged.

## Version-one schema and identity

All documents and API DTOs have `schema_version: 1`.
`backend/schemas/ga_history.py` validates stored snapshots without modifying the
observed values. Each generation document contains:

| Field | Meaning |
| --- | --- |
| `run_id`, `generation`, `timestamp` | Original run UUID; zero-based completed boundary; UTC capture time |
| `metrics` | Original telemetry, including actual/requested population, generation-best/best-ever/average/worst penalties, cumulative accepted candidates, plateau and elapsed time |
| `ga_configuration`, `fitness_configuration` | Actual monitor parameters including retry defaults; frozen soft settings when available |
| `engine_fingerprint` | Existing continuation-engine source/runtime fingerprint |
| `metrics.input_fingerprint` | Original CSV/JSON data fingerprint |
| `metrics.configuration_fingerprint` | Original GA/input/baseline configuration fingerprint |
| `generation_best`, `best_ever` | Separate candidate IDs, upload-compatible chromosome payloads and original workload rows |
| `fitness_breakdown` | Null at current scalar-only boundaries; optional matching final attachment returned by analysis endpoint |
| `validation` | Passed publication gate, timestamp and zero hard-violation counts |
| `capture_elapsed_ms`, `validation_elapsed_ms` | Boundary copy cost and background validation cost |

Candidate IDs are SHA-256 hashes of portable schedule content and subject/section
keys. They do not contain Python memory addresses, penalty or capture timestamps.
The same content has the same ID, allowing clear identical-candidate comparisons;
its run and generation still identify each observation. Faculty numeric codes
are the engine's existing compatibility identifiers under the captured data
fingerprint. The UI uses `Faculty N`; external rows use the declaration's display
name and “Preassigned Instructor”. No normal faculty private names are introduced.

## Storage, durability and retention

```text
backend/saved_chromosomes/generation_snapshots/<canonical-run-UUID>/
  index.json
  generation-000000.json
  generation-000001.json
  ...
  analysis-<candidate-SHA256>.json       # optional existing final breakdown
```

Each file is an envelope `{sha256, data}`. The checksum covers canonical JSON
data. Writes use the existing safe atomic-write helper: same-directory temporary
file, file fsync, atomic replacement and POSIX directory fsync where supported.
The generation file commits before its index entry. An index never points to a
partially written new file. Readers can see the previous complete index while a
write is in flight. One process-local lock serializes index updates.

Generation identities are immutable. Duplicate identical observations are a
no-op; conflicting replays are rejected. An unindexed generation file left by a
crash is checked before any compatible replay can index it and is never silently
overwritten. No automatic orphan reconciliation is provided. Terminal and paused
lifecycle metadata are persisted independently of checkpoint files on admission
release. Current registry lifecycle is authoritative while a run is known. A
restart without a resumable checkpoint remains INTERRUPTED, not resumable history.

The two-entry writer queue bounds queued generations; each DTO is limited to
16 MiB. Finalization drains the writer before execution admission is released.
Capture, queue pressure, validation, capacity, disk and lifecycle-write failures
are explicitly reported through history warnings/logs and run history. Failed
records are never advertised as successful generations. Older valid records are
preserved. A completely unavailable disk may prevent a durable error record;
the live in-process warning and run-scoped log remain the fallback.

| Environment variable | Default | Policy |
| --- | --- | --- |
| `GA_HISTORY_INTERVAL` | `1` | Capture every generation including zero; larger positive integers record zero and multiples of the interval |
| `GA_HISTORY_MAX_RUN_BYTES` | `268435456` (256 MiB) | Per-run generation/analysis payload budget; metadata/index bytes are additional |

Retention is fixed when a new history run is created and retained on resume.
Skipped generations and capacity failures remain visible. Sampling can omit the
last non-multiple generation; the existing final live result is still preserved
by the unchanged GA result service. At capacity, history recording reports gaps
and optimization continues. **No automatic deletion occurs**. Administrators
must explicitly archive/manage runtime artifacts outside this implementation.
This is a per-run limit, not a global disk quota. The runtime directory is ignored
by Git. Existing checkpoints, preferences, baselines, latest and global-best files
are not migrated, deleted or overwritten by the history service.

## Read-only API

Routes use `/api/ga`. They do not replace the existing run/status/log/control
endpoints. `candidate` is `generation_best` (default) or `best_ever`.

| GET route | Contract |
| --- | --- |
| `/runs?offset=0&limit=20` | Run summaries, newest first; max limit 100; total and archive-index error list |
| `/runs/{id}/generations?offset=0&limit=50` | Run summary and ascending generation summaries; max limit 200 |
| `/runs/{id}/generations/{g}` | Immutable full observation including both candidates |
| `/runs/{id}/generations/{g}/schedule?candidate=...` | Original validated schedule, candidate ID, capture validation and current-input-match flag |
| `/runs/{id}/generations/{g}/analysis?candidate=...` | Original total, matching available breakdown, workloads, null preference results with explanation |
| `/runs/{id}/compare?left=0&right=2&candidate=...` | Same-run compatible-generation comparison |
| `/runs/{id}/generations/{g}/export?candidate=...&format=json` | Validated portable chromosome JSON with observation metadata |
| `/runs/{id}/generations/{g}/export?candidate=...&format=csv` | Validated schedule CSV |
| `/runs/{id}/history/export` | Fitness history CSV |
| `/runs/{id}/compare/export?left=0&right=2&candidate=...` | Validated comparison JSON |

Unknown/unsafe IDs and missing records receive 404; invalid query values receive
422; corruption/schema/candidate identity inconsistencies receive 422 with a
specific history code; incompatible comparisons or original-input-unavailable
exports receive 409. Error responses never expose raw storage paths. Archived
COMPLETED, STOPPED, PAUSED and interrupted runs remain readable after restart.

Historical values remain viewable when current inputs change, clearly labeled
as original capture observations. Export reconstructs each included schedule
and passes the existing hard gate again. Because this phase does not archive
complete historical validation input datasets, export requires an exact match
to the original data fingerprint. Preferences are included in that fingerprint;
even a soft-only change conservatively blocks export. Restoration of the
original inputs permits export without recalculating historical fitness.

## Comparison and downloads

Each reduction is `left penalty - right penalty`: positive is improvement,
negative is worse, zero is unchanged. Generation-best, best-ever and population
average reductions are independent. Accepted counts are cumulative observations,
not attempted crossover/mutation counts or fabricated fitness-evaluation counts.

Assignment differences group schedule meetings by subject, section and component,
then compare faculty, room, day, start and end. Added/removed subject/section
components are explicit. Exact identity equality is labeled “Identical schedule
candidates”. Workloads and any available captured breakdowns accompany the
comparison. No cross-run comparison or changed-fingerprint reanalysis is allowed.

Candidate JSON reuses `ccs-ga-chromosome` version one, retaining subject/section
keys and engine identifiers for valid reconstruction. Added `history` metadata
contains run/generation/kind/metrics and validation. CSV uses the existing
`start`/`end` schedule fields and human-readable faculty labels. Formula-leading
cells (`=`, `+`, `-`, `@`, including leading whitespace; leading control characters)
are apostrophe-prefixed and correctly CSV-quoted. Comparison JSON includes
schedule rows, so **both** selected candidates are validated before download.
Fitness-history CSV contains metrics only. Names contain canonical UUIDs,
generation numbers and candidate kind. Failed validation returns JSON errors,
not a misleading downloaded schedule. No PDF/Excel exports are added.

## Frontend

Admin navigation has “Generation History”; live monitors link to the current
run's history. The page has paginated run and generation selection, original
metrics, explicit missing-history warnings, inspection of both candidate kinds,
workload tables, eligible export actions and same-run comparisons. Existing
`WeeklySchedule` and `ConvergenceChart` render historical DTOs without editing
controls. No `loadChromosomeData`, generation start, pause/resume/stop, or live
context replacement occurs during inspection.

The run UUID is retained in the page URL through refresh. Requests reject schema
or identity mismatches, settle into actionable errors, and use finite request
timeouts. Late inspection responses for a different selected run/generation are
ignored. Missing breakdowns/preferences are explained without empty percentage
bars. The convergence chart explicitly shows the **current page** of up to 50
recorded generations; it does not pretend to show unseen pages.

## Performance, equivalence and verification

Initial five-offering / three-candidate fixture measurements (generations 0–2):
boundary capture 0.30–0.33 ms, snapshot envelopes 6.55–6.88 KB, background validation
2.32–8.03 seconds under concurrent GA execution. These initial measurements
included redundant validation of equal candidate IDs; that duplicate pass was
subsequently removed. Measurements are fixture observations, not a claim about
production throughput. The writer still competes for CPU/GIL time; it is not a
distributed worker. Terminal/pause cleanup may wait for queued validation/I/O.
Use interval/cap settings if measured workloads exceed available resources;
queue pressure is reported explicitly instead of using unbounded memory.

Deterministic integration compares observed and uninstrumented runs for final
schedule, evolution history, total, breakdown, faculty analysis, RNG state and
fitness-call counts. A Python call profiler covers the original fitness function
body, including tournament and final per-faculty analysis calls. Small real-model
fixtures preserve eligibility, fixed calendars, external ITE184 locks and labs;
controlled operators bound run length. No production GA workload is executed.

After removing duplicate validation, an unprofiled pause/resume fixture measured
0.34–0.40 ms boundary copy time, 7.38–7.55 KB snapshot envelopes (now including
the original soft configuration), and 3.72–7.29 seconds background validation
while other regression tests ran. The full call-profiler fixture measured
0.42–0.45 ms capture and 4.09–13.57 seconds validation; profiler/GIL contention
makes those validation times unsuitable for production throughput estimates.
These measurements confirm that repeated hard validation, rather than DTO
serialization, is the expensive stage.

Verification commands (pytest at workspace root; npm in `frontend`):

```text
.venv/Scripts/python.exe -m pytest backend/tests/test_ga_generation_history.py -q
.venv/Scripts/python.exe -m pytest backend/tests/test_ga_monitoring.py backend/tests/test_ga_safe_stop.py backend/tests/test_ga_refresh_recovery.py backend/tests/test_ga_pause_resume.py backend/tests/test_ga_paused_recovery.py backend/tests/test_ga_control_conflicts.py backend/tests/test_ga_logs.py -k "not real_browser" -q
npm.cmd run test:ga
npm.cmd run test:ga:browser
npm.cmd run build
```

Focused frontend lint covers changed TypeScript modules, with the existing
mixed-export exemption only for LiveGAMonitor's reusable chart. Backend fixtures
redirect all history/checkpoint/result storage to temporary directories. Source
hash checks verify unchanged GA engine files, institutional data, notebooks and
existing user artifacts. Final measured results and totals are recorded below.

| Verification | Result |
| --- | --- |
| Existing Phase 3B/3C/3D/3D.3 backend suite | 99 passed; real-browser case run separately |
| New history backend suite | 19 distinct cases passed across verification runs (17-case suite plus two added cases); latest focused five-case run passed |
| Existing real FastAPI/browser start/pause/refresh/resume integration | Passed |
| Frontend GA contracts including history | 37 passed |
| Browser monitoring/recovery/history suite | 40 passed, including the parent suite |
| TypeScript/Vite build and focused ESLint | Passed; existing bundle-size warning retained |
| Protected source/data/artifact hashes | 62 unchanged |
| Git whitespace check | Passed |

There are 119 distinct passing backend cases across the verification runs:
99 existing non-browser cases, one existing real-browser integration, and 19
history cases. The late scoped-warning/index-rollback changes were checked by a
focused five-case run that also repeats full original-fitness call-count/RNG
equivalence. The invalid-candidate case recomputes its tampered content ID so
rejection exercises hard validation rather than merely failing identity checks.

## Changed files

| Area | Files |
| --- | --- |
| History contracts/storage | `backend/schemas/ga_history.py`, `backend/services/ga_history_service.py` (new) |
| API | `backend/routers/ga_history.py` (new), `backend/routers/genetic_algorithm.py`, `backend/main.py` |
| Runtime exclusion | `.gitignore` |
| Backend verification | `backend/tests/test_ga_generation_history.py` (new), `backend/tests/conftest.py` |
| History UI/contracts | `frontend/src/pages/admin/GenerationHistory.tsx`, `frontend/src/services/gaHistory.ts` (new) |
| Navigation/live entry point | `frontend/src/layouts/AdminLayout.tsx`, `frontend/src/routes/AppRoutes.tsx`, `frontend/src/components/ga/LiveGAMonitor.tsx` |
| Frontend verification | `frontend/tests/gaHistory.test.mjs` (new), `frontend/tests/gaMonitoring.browser.test.mjs`, `frontend/package.json` |
| Documentation | `docs/phase-3e-generation-history.md` (new) |

Seventeen files in total. The existing schedule/chromosome/fitness-analysis
services and views were inspected and reused where appropriate; their engine
source and current result behavior were not replaced.

## Known limitations and next-phase boundary

- Single-process execution/storage coordination; no PostgreSQL, distributed
  ownership, authentication or role enforcement is added. Keep the existing
  institutional prototype deployment/access boundary.
- Existing pre-Phase-3E runs are not backfilled from metrics or Saved Best. A
  resumed old checkpoint can record subsequent generations only.
- No complete archived validation-input dataset; changed inputs block exports.
- Per-faculty historical preference satisfaction/penalties are unavailable when
  not originally captured. Final matching total breakdowns are available, not
  invented historical analyses. Reporting can build on this provenance later.
- Per-run payload budget and bounded queue can create explicit history gaps;
  overall disk usage needs administrator monitoring and manual archival.
- Atomic file/index publication is not a multi-file database transaction.
  An abrupt process/power loss can leave a complete unindexed file; conflicting
  replay is reported and no automatic destructive repair is performed.
- Content IDs describe schedule equality, not genetic lineage or parent origins.
- The graph is paginated; full-run metrics are available in history CSV.
- Existing frontend bundle-size warning remains. No unrelated bundling redesign
  or PDF/Excel/reporting framework is included.

## Manual acceptance

1. Start a small API run. Open its “View recorded generation history” link and
   refresh history after a boundary. Verify generation zero, each successful
   later generation, actual/requested population, accepted counts and penalties.
2. Inspect a generation; switch generation-best/best-ever. Verify candidate ID,
   meetings, normal privacy labels, external preassignment name/role, original
   workload targets, fixed laboratory duration and explained unavailable fields.
3. Pause after a completed generation, refresh the browser, inspect its immutable
   snapshot, then resume from the live page. The original bytes remain unchanged
   and later generation numbers append without duplicate workers or rows.
4. Stop a run safely. Verify STOPPED history and all already recorded generations
   remain accessible. Restart the backend; inspect completed/stopped/paused history
   without starting another run or changing the active result.
5. Compare identical candidates and different generations. Check independent
   generation-best, best-ever and average signs, assignment fields and workloads.
6. Download candidate JSON, schedule CSV, history CSV and comparison JSON. Check
   filenames, retained ITE184 locks, continuous labs and formula protection.
7. On isolated copied test data, corrupt a snapshot or change original inputs:
   corruption must fail safely; original-input-unavailable exports must be rejected
   while original observations remain explicitly labeled and viewable.
8. On isolated test storage, lower the payload budget. Verify an explicit history
   capacity warning/gap, preserved earlier files, and unaffected GA correctness.

Phase 3E provides the persistence and read-only inspection foundation for later
reporting. No Phase 3F reporting implementation, checkpoint redesign or new GA
behavior is started here.
# Phase 3E.1: history inspection and checkpoint verification recovery

See [the diagnosis, latency measurements, validation safeguards, and acceptance procedure](phase-3e1-history-checkpoint-recovery.md).
