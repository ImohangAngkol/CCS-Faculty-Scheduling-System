# Phase 3B — Structured live GA monitoring

## Scope

The API now emits structured generation telemetry and the React dashboard updates
its metrics and convergence graph during execution. This phase adds no pause,
resume, stop, checkpoint, generation snapshot, export, comparison, database or
authentication implementation. The notebook and selection/crossover/mutation/
elitism/survivor algorithms are unchanged.

Lower penalty is better. The teaching requirement remains
`max(0, 24 - admin - research - extension)`. Underload remains soft, the teaching
ceiling remains 40, and explicit eligibility remains authoritative. External
Palad/ITE184 assignments, ICT3A locks, fixed reservations and continuous
three-hour laboratories remain mandatory.

## Architecture

1. `/api/ga/generate`, `/api/ga/run` and `/api/ga/stream` share one nonblocking
   process-local admission lock. Overlapping requests receive HTTP 409 before
   execution touches shared scheduling objects. Read-only routes remain available.
2. The streamed worker still runs outside the asyncio request loop in a daemon
   thread. Admission lasts until that worker exits, including after disconnection.
3. A context-local score collector records results of existing whole-chromosome
   fitness calls. Its decorator returns the original result unchanged and retains
   the object alongside its score to avoid reused Python object IDs. Per-faculty
   evaluations are excluded. There are no extra fitness calls for monitoring.
4. The generation service emits initialization metrics and one event after each
   finalized survivor population. No candidate list or mutable scheduling object
   is passed to the observer. Score references are cleared after each report.
5. A publication gate validates copied schedule representations using existing
   reconstruction/constraint checks and additional completeness/metadata/fixed
   schedule/instructor/room consistency checks. It performs no fitness evaluation,
   persistence or random operations. It validates all reported survivors and the
   final best candidate; `/generate` validates its published best candidate.
   Latest-result restoration and the existing saved-best download also validate
   stored schedules before delivery. Download bytes are read once, validated and
   returned with the original attachment filename/content.
6. The final saved-best and latest-result destinations and response payloads remain
   unchanged. Invalid stored schedules receive HTTP 422 instead of being returned
   as valid results. No generation snapshot files are written.

The score observation decorator is the only change to `FitnessFunction.py`:
its body, weights, priorities and mathematical decisions are unchanged. The
collector is inactive outside an observed run and restored in `finally`.

## Event contract

The existing POST `/api/ga/stream` remains SSE with `data: <JSON>` frames.
Every emitted event has:

```json
{
  "schema_version": 1,
  "run_id": "UUID",
  "sequence": 1,
  "type": "run_created",
  "timestamp": "UTC ISO-8601 timestamp",
  "data": { "status": "CREATED", "configuration": {} }
}
```

Run IDs use OS entropy, not the GA's Python random generator. Sequence assignment
and emission are serialized. Console logs are best effort, so sequence gaps are
possible; duplicate/stale sequences are ignored by the frontend.

| Type | Data |
| --- | --- |
| `run_created` | Requested configuration and CREATED status |
| `run_started` | RUNNING status and initializing phase |
| `initial_population_ready` | Validated generation-0 metrics |
| `generation_completed` | Validated retained-survivor metrics |
| `log` | Console message |
| `result` | Original complete GA result payload, after latest-result persistence |
| `error` | FAILED status, code and explanatory message |
| `done` | COMPLETED or FAILED terminal status |

Legacy clients can still consume `log.message`, `error.message` and `result.data`.
The old `done` type remains present. Modern clients require a successful result
and terminal event; receiving a result followed by premature EOF is not sufficient
to claim a fully observed completion. No WebSocket is needed for this phase.

## Metrics and counting definitions

At generation 0 and every completed evolutionary generation:

| Field | Definition |
| --- | --- |
| `generation` | 0 for initialization; 1 onward for completed generations |
| `generation_limit` | Requested maximum evolutionary generations |
| `population_requested` | Configured target population size |
| `population_actual` | Number of retained survivors, which can be smaller |
| `generation_best_fitness` | Minimum captured survivor penalty |
| `best_ever_fitness` | Existing GA best-ever value |
| `average_fitness` | Arithmetic mean over retained survivors |
| `worst_fitness` | Maximum captured survivor penalty |
| `best_ever_improvement` | Previous best-ever minus current best-ever, bounded below by zero; 0 at initialization |
| `generations_without_improvement` | Observational count of completed generations without strict best-ever improvement; does not terminate the GA |
| `elapsed_ms` | Monotonic elapsed time since service initialization |
| `generation_elapsed_ms` | Time since the previous generation report |
| `accepted_new_chromosomes_total` | Accepted fresh initial candidates + non-None crossover results + non-None mutation results + immigrants |
| `baseline_chromosomes` | 0 or 1 accepted saved/uploaded seed, tracked separately |
| `fitness_evaluations_total` | Always null in this phase |
| `input_fingerprint` | SHA-256 over names/content of backend/data CSV and JSON files |
| `configuration_fingerprint` | Input digest plus requested GA parameters and actual baseline schedule/subject keys |
| `metrics_comparable` | True while input fingerprints remain consistent |
| `validation_status` | passed, only after survivor validation |

The accepted count tracks new successful candidate returns, not unique schedule
contents: two independently returned candidates may have equal assignments.
It includes candidates subsequently discarded by survivor selection. It excludes
failed construction/retry attempts, `None` outcomes, baseline seeds, retained
parents, elite copies and best-ever copies. It is not a fitness-evaluation count.

Statistics use the most recent existing scores for precisely the survivors, not
the oversized candidate pool. Non-finite/missing scores fail explicitly rather
than triggering replacement scoring or inventing values.

Input hashes are checked at generation/publication boundaries. A detected change
aborts with a comparability error rather than publishing a mixed-context result.
Files are not frozen or locked: this is conservative change detection, not a
transactional input snapshot. An edit reverted between checks can escape detection.
The digest includes all dataset CSV/JSON files, including some not used by a run.
CSV templates already loaded at process startup still require a restart to reload.

## Hard-constraint publication checks

The gate checks exact required offerings, authoritative units/component hours,
unchanged preassignment declarations, immutable fixed section reservations,
meeting instructor/room consistency, and room/component compatibility.

Deep-copy reconstruction against authoritative templates additionally checks
known resources, explicit eligibility, faculty/room/section conflicts, rebuilt
teaching loads up to 40, fixed-schedule overlaps, external instructor and locked
room identity, required meeting hours, resource calendar membership, duplicates
and continuous three-hour laboratory meetings. Cached load values cannot bypass
the gate. No underload or preference requirement is added as a hard constraint.

All progress candidates are validated before their generation event. The best
candidate is validated before final saving/return. A rejected candidate produces
an explicit failure instead of a schedule. Historical `/latest`/download responses
are checked for current hard feasibility, while their original scores are not
recalculated. They retain the original successful response/file content.

## Frontend and transport behavior

`GAContext` keeps live metrics separate from the final schedule. GenerateSchedule,
Dashboard and the in-progress Fitness Analysis view share a compact monitor:
status/time, progress/population/accepted counts, penalty metrics, and a purple/
orange convergence chart. The chart plots generation best, best-ever and average,
with generation numbers, hover values and an exact-value table. Unavailable values
use an em dash, and initialization displays a descriptive state rather than fake
percentage progress. Existing completed-result analysis remains available.

The parser supports UTF-8 across chunks, CR/LF/CRLF framing, multiline data,
multiple frames, comments, legacy events and unknown future event types. It
checks run identity, sequence, envelopes, metrics and basic final-result shape,
and cancels/releases its reader on every exit. Stream failure is DISCONNECTED,
with an explicit warning that the server may still be running; it is never STOPPED.
HTTP admission rejection is REJECTED, and an explicit server failure is FAILED.

The backend queue is bounded. Console logs may be dropped for slow consumers;
structured delivery overflow raises an explicit error. Terminal events receive
delivery priority. A disconnected observer is detached, queued data is discarded,
and the worker continues to preserve its valid final result. No cancellation is
implemented. If delivery fails after final persistence, a valid saved result can
remain available even though monitoring failed.

Console streaming still redirects process stdout, but only the owning worker's
output enters that run's stream. Other thread output is forwarded to the terminal.
Replacing global stdout redirection with dedicated logging remains future work.

## Files changed

Backend:
- `genetic_algorithm/utils/FitnessObservation.py` — score observation/context cleanup.
- `genetic_algorithm/operators/FitnessFunction.py` — observation decorator only.
- `schemas/ga_events.py` — versioned event envelope.
- `services/ga_progress_service.py` — telemetry, counts, fingerprints and sequencing.
- `services/ga_publication_service.py` — non-mutating publication gate.
- `services/ga_service.py` — optional observer, boundary validation and counting.
- `routers/genetic_algorithm.py` — shared admission and structured SSE transport.
- `routers/chromosomes.py` — validates the existing saved-best download.
- `tests/test_ga_monitoring.py` — focused regression tests.

Frontend:
- `services/gaMonitoring.ts` — metric/event types and incremental SSE parser.
- `services/gaService.ts` — compatible stream API with optional observer callback.
- `context/GAContext.tsx` — live progress/status and connection-failure semantics.
- `components/ga/LiveGAMonitor.tsx` — grouped metrics and live graph.
- `pages/admin/GenerateSchedule.tsx`, `Dashboard.tsx`, `FitnessAnalysis.tsx` — monitoring views.
- `tests/gaMonitoring.test.mjs`, `tests/gaMonitoring.browser.test.mjs` — parser and browser checks.
- `package.json` — GA test commands.

This document is also new. Existing user edits to faculty_preferences.json were
preserved; that data file is not a Phase 3B change.

## Validation

Focused backend checks cover generation/event order, requested/actual population,
ascending statistics, best-ever behavior, accepted counts, baseline/None handling,
equivalence with observation disabled, no added scorer calls, unchanged random
state, gate non-mutation, invalid publication, underload, ITE184 locks, input edits,
observer errors, shared admission and unchanged final-result persistence.

Commands:

```text
.venv/Scripts/python.exe -m pytest backend/tests/test_ga_monitoring.py -q
.venv/Scripts/python.exe -m pytest backend/tests/test_ga_api_crossover.py backend/tests/test_ga_hard_constraints.py backend/tests/test_ga_monitoring.py backend/tests/test_metadata_api.py backend/tests/test_preassigned_assignments.py backend/tests/test_preference_validation.py backend/tests/test_tournament_selection.py -q
npm.cmd --prefix frontend run test:ga
npm.cmd --prefix frontend run test:ga:browser
npm.cmd --prefix frontend run test:preferences
npm.cmd --prefix frontend run build
```

The targeted backend regression run passed 171 tests. A final focused/API rerun
passed 25 tests, including the added stored-result publication checks and explicit
no-extra-scoring assertion. Frontend stream tests passed
7 tests, preference model checks passed 19 tests, and live browser checks passed
all 3 scenarios (4 tests including their parent). The existing Faculty Preferences
browser suite also passed all 22 tests. Browser fixtures mock API/SSE
responses and do not run or save a production GA. The build passed. Whole-project
lint reports existing errors/warnings in unrelated pages and the existing mixed
GAContext component/hook export; the changed monitor/parser/pages pass focused lint.

The broad backend test command was interrupted upon entering legacy whole-dataset
GA smoke tests; it is not reported as a completed full-suite pass. Those old API
tests also use global persistence destinations. Existing saved-best/latest files
remain unchanged. The targeted regressions use isolated persistence destinations.

## Known limitations and next phase

- The admission guard is process-local, not cross-process or distributed.
- Direct service/notebook callers do not acquire API admission.
- Run IDs and progress history are volatile; there is no replay or run registry.
- A browser reload restores the last completed result, not an active connection.
- Live average/counter history is not added to historical persistence; existing
  completed fitness history still restores its previous best-series graph.
- Backend elapsed metrics are generation-boundary samples; the browser animates
  elapsed seconds between events, so temporary client timing drift is possible.
- Full validation adds copy/reconstruction overhead, without changing selection.
- Input snapshots, atomic persistence, worker supervision and user ownership are
  not implemented. There are no authentication or authorization changes.
- No pause/resume/stop, restart recovery or persistent generation snapshots exist.
- The existing best_chromosome.json predates the current external assignment
  rules and fails the ITE184::4A locked-instructor check. It was not changed or
  deleted; download and baseline use reject it. The existing latest completed
  result passes current hard validation. This phase does not automatically repair
  old artifacts or alter the across-run saved-best fitness comparison policy.

Phase 3C should introduce an authoritative run lifecycle and cooperative stop
requests checked at safe generation boundaries. It must persist the last valid
generation/best-ever before acknowledging STOPPED and retain admission until the
worker exits. The current events and publication gate provide the foundation;
disconnecting monitoring must continue to mean only loss of observation.
