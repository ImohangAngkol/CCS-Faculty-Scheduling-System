# Phase 3C: Cooperative safe stop

Administrators can request a stop while a GA run is initializing or optimizing.
The worker finishes its current generation, validates the complete survivor
population, and preserves the best-ever valid result. A request is not a completed
stop. Only the worker can acknowledge STOPPED, after successful preservation.

No GA mathematics or operators were changed. Control performs no random draws or
fitness evaluations. Lower penalty remains better. Teaching target remains
`max(0, 24 - admin - research - extension)`, underload remains soft, and teaching
load above 40 remains forbidden. Explicit eligibility, resource conflicts, fixed
schedules, component patterns, continuous three-hour laboratories, external Palad
assignments and ICT3A locks still pass the unchanged Phase 3B publication gate.

## Lifecycle and ownership

`RunControl` owns one run's RLock, stop flag, timestamps, latest validated boundary,
terminal error, and final result reference. `RunRegistry` stores these records in
memory. IDs use OS UUID entropy, not the GA random generator. The SSE emitter uses
the same run ID. State changes and stop acknowledgements serialize under the run
lock; event sequencing serializes under the existing emitter lock.

Allowed transitions are enforced:

| From | To |
| --- | --- |
| CREATED | INITIALIZING, STOP_REQUESTED, FAILED |
| INITIALIZING | RUNNING, STOP_REQUESTED, COMPLETED, FAILED |
| RUNNING | STOP_REQUESTED, COMPLETED, FAILED |
| STOP_REQUESTED | STOPPING, FAILED |
| STOPPING | STOPPED, FAILED |
| STOPPED / COMPLETED / FAILED | None |

The INITIALIZING-to-COMPLETED transition covers the legacy `/generate` operation
and test adapters. Full runs become RUNNING at the first validated generation-0
boundary. INITIALIZING is sent in `run_started`; normal generation metrics retain
their Phase 3B RUNNING label. Metrics describe completed generations and do not
reset STOP_REQUESTED/STOPPING in the frontend.

The shared API admission lock still covers `/generate`, `/run` and `/stream`,
including initialization, STOP_REQUESTED, STOPPING and persistence. A second run
receives 409. The stream worker releases admission exactly once in its `finally`,
after terminal delivery attempts; thread-start failure releases admission too.
The normal synchronous route runs in FastAPI's worker thread pool, while the
stream has its own worker thread. Control/status/health requests remain available.

`/generate` only builds the legacy initial-population response and is not a
cancellable full GA run. It advertises `accepting_stop: false`; requesting its
stop returns 409. `/run` and `/stream` support cooperative stop. Direct service
and notebook calls do not acquire API admission; no notebook changes were made.

## Endpoints

### POST /api/ga/runs/{run_id}/stop

No request body is required. Example response (other lifecycle fields omitted):

```json
{
  "run_id": "a canonical UUID",
  "state": "STOP_REQUESTED",
  "status": "STOP_REQUESTED",
  "stop_requested": true,
  "accepted": true,
  "already_requested": false,
  "latest_completed_generation": 7,
  "stop_reason": "administrator_request"
}
```

- 200 / accepted true: the stop flag was latched. Repeated pending requests return
  200 / accepted true / already_requested true without emitting another request.
- 200 / accepted false: the run is already terminal; its actual terminal state is
  returned. This is an idempotent read of the outcome, not another accepted stop.
- 404 / `GA_UNKNOWN_RUN`: the ID is unknown to this server process, including after registry loss.
- 409 / `GA_PROCESS_CHANGED`: the optional `X-GA-Process-ID` header identifies
  a different process instance. No cancellation occurred.
- 409: the final generation already won the completion race and result
  finalization is underway, or this execution does not support cooperative stop.

`accepted` does not promise immediate termination. Poll state or observe SSE.
There is no thread kill, SystemExit, AbortController cancellation or pause command.

### GET /api/ga/runs/{run_id}

Returns authoritative state, stop flag, `accepting_stop`, `finalizing`, UTC
created/started/requested/stopped/ended timestamps, elapsed milliseconds, latest
completed generation, latest validated best's generation/fitness, final result
reference, and terminal error. Elapsed time freezes when the run terminates.
The best metadata is a boundary reference, not a serialized population/checkpoint.
Phase 3C.1 also returns `process_instance_id`, requested `configuration`,
`execution_active`, and one latest validated `latest_progress` snapshot.
The state endpoint accepts the same optional process header as the stop endpoint.

### GET /api/ga/status

Preserves the existing availability response and adds `active_run`, or null after
admission is released. Phase 3C.1 advertises `control_version: "3c.1"`, a process
instance UUID, OS process ID, and `monitoring: "snapshot_polling"`. Non-stream `/run` callers can discover their active ID here
and request a stop from another request. A successful `/run` response additionally
contains its final `run` snapshot; `data` is null for an early no-result stop.

### GET /api/ga/runs/{run_id}/result

Returns a preserved stopped result as `{status: "success", data: ...}`. This route
reads disk independently of the registry and works after a server restart if the
caller retains the ID. Canonical UUID validation prevents path traversal. Missing
records return 404; unreadable, mismatched or currently invalid records return
422. Stored schedules are revalidated against current hard constraints without
rescoring. Phase 3C.1 additionally retrieves a COMPLETED run's latest result while
its registry record exists and the file still belongs to that exact run. If a
newer run supersedes that file, the identity check rejects it; no other run's
schedule is substituted. This is not normal completed-run history.

## Safe boundaries and the final race

1. Check before baseline/initial work and again immediately before expensive
   initial population construction. An accepted early stop returns no chromosome.
2. An in-flight initial population finishes construction, existing scoring and
   full publication validation. That is valid generation 0, which can be preserved.
3. Check before each new evolutionary generation and after every completed,
   sorted, selected and validated survivor population. Record the validated best
   metadata before its generation progress event. Generation count is actual work
   completed, not the requested limit.
4. A request inside crossover or mutation retries waits for the current bounded
   operator calls and whole generation to finish. The generation is atomic for
   stop purposes: no partially built child or population is exposed. The retry
   limits, survivor rules and random sequence remain unchanged. There are no
   inner operator interruption hooks in this phase; stop latency can be long.
5. The final boundary seals control under the same lock as stop requests. If the
   request won, enter STOPPING and finalize a stopped result. If completion won,
   reject late requests with 409 while finalization completes. An accepted stop at
   the final requested generation is still labeled STOPPED.

Input-comparability checks and all Phase 3B hard-validation gates remain active.
Validation, operator, input-change or persistence exceptions produce FAILED,
including during cancellation; they do not produce a misleading STOPPED result.
An acknowledged terminal state cannot be rewritten by a later transport error.

## Preservation and persistence

- **Valid stopped result:** preserve the best-ever from completed validated
  boundaries, apply the final gate, and run the existing global-best comparison.
  Save `backend/saved_chromosomes/stopped_runs/{run_id}.json`. It includes the
  original schedule, breakdown, analysis and actual history/generation count,
  plus run ID, STOPPED status, timestamps, elapsed time and stop reason.
- **Atomic stopped artifact:** write to a uniquely named temporary file in the
  same directory, flush and fsync, then `os.replace` the final JSON. Clean up the
  temporary file on failure. No reader sees a partial final record. Runtime
  stopped records are ignored by Git.
- **Stopped before valid generation 0:** no result event, no stopped schedule file,
  no global-best update and no overwrite of the latest completed result.
- **Latest completed:** `latest_ga_result.json` is updated only for COMPLETED.
  Both completed and stopped result payloads carry their run ID and status.
- **Global best:** existing `save_best_if_better` rules remain unchanged: strict
  lower score for the same offering set, with its existing different-offering-set
  behavior. All incoming candidates are validated. A worse stopped result does
  not replace a valid best for the same offering set. Historical artifacts are not
  repaired or rescored automatically; the old invalid Palad baseline is untouched.

Stopped artifact creation, global-best comparison and existing latest-result
storage are not a multi-file transaction. Existing global-best/latest writes have
not been redesigned. A valid global-best update can already exist if the later
stopped artifact write fails; the run reports FAILED and emits no stopped result.
Atomic replace protects file visibility, not full machine-crash durability of all
directories or recovery of an active run.

## SSE and frontend

The version-1 Phase 3B envelope remains unchanged. `run_state_changed` is added.
Pending stop event order is:

```text
run_state_changed STOP_REQUESTED
[progress/logs from the generation already in flight]
run_state_changed STOPPING
[finalization and persistence]
run_state_changed STOPPED
result (only when a validated preserved result exists)
done {status: STOPPED, has_result: true|false, latest_completed_generation: N|null}
```

Failure instead emits FAILED state, legacy-compatible error and FAILED done.
Normal completion emits COMPLETED state, result and COMPLETED done. Event sequence
and identity checks remain in place, and legacy log/message/result events still
work. Disconnect detaches observation; the worker keeps admission and can still
receive an explicit stop request. A disconnected pending-stop client reports
DISCONNECTED, never an inferred successful stop.

The shared monitor on Generate Schedule, Dashboard and in-progress Fitness
Analysis exposes **Stop Generation** only for an identified active run. Clicking
immediately displays **Stop requested — waiting for a safe boundary**, disables
repeat clicks, sends the run ID to the endpoint, and keeps metrics updating.
STOPPING and STOPPED have separate labels. Delayed HTTP acknowledgements cannot
regress a newer SSE state or affect a different run. Request errors are explained.

A valid stopped result opens in the normal schedule/analysis views; Generate
Schedule labels it **Stopped — preserved schedule**, and Fitness Analysis labels
the interrupted result. The monitor shows the final generation, penalty and time.
An early no-result stop explicitly explains that no schedule was produced and
retains the previous completed result in the browser. Reload restores the latest
completed result and discovers an active or remembered current-process run as
described below; its stopped candidate can be retrieved after terminalization.

The stream parser requires a valid result plus STOPPED done, or explicit
`has_result: false` for a no-result stop. Missing results, contradictory completed
states, malformed lifecycle events and premature EOF fail safely.

## Phase 3C.1 diagnosis and correction

### What the reported 404 establishes

The inspected router already registered `/api/ga/runs/{run_id}/stop`. Its original
unknown-ID branch returned `Run is unknown in this server process.`, rather than
the literal `Not Found`. Stream and stop use the same frontend base URL
(`http://127.0.0.1:8000`), and the stream emitter already used the registered control
ID. A test removes only the stop route from a legacy router: even a valid
registered ID then produces exactly `{"detail":"Not Found"}`. The updated router
instead returns structured `GA_UNKNOWN_RUN` for an absent ID.

Thus the literal failure is reproduced as a missing-route response from the
contacted backend, rather than a successful cancellation or late ID registration.
There was no backend listening on port 8000 during this investigation. The
historical command, process and response log were unavailable, so the exact
outdated launch or wrong server that produced it cannot be established. A reload
or worker mismatch with the inspected route present produces an unknown-run or
process-mismatch response, not that default route-level body. This evidence does
not justify claiming a specific Uvicorn launch was observed.

The refresh failure has a separate verified cause: GAContext previously restored
only `/latest` and kept the active run solely in React memory. Refresh detached
the stream but did not query the backend registry. The server worker continued,
as expected; losing a browser connection is not a cancellation request.

### Registration, controls and process identity

- Admission and registration occur before streaming. `run_created`, containing
  the registered ID, process instance and requested configuration, is enqueued
  before worker launch. `run_started` follows from the tracked worker. No separate
  emitter UUID or unregistered worker is used.
- A process instance UUID changes whenever a registry is constructed. It uses
  OS entropy, never GA random state. The frontend checks the capability/version
  before starting a stream and sends that process identity on stream, state and
  stop requests. A process change between preflight and start is rejected before
  admission. This detects process boundaries; it does not make multiple workers
  safe or provide authentication.
- A successful stop latches the same RunControl used by the worker. Pending
  requests are idempotent; STOPPED still comes only from validated preservation.
  Unknown IDs, missing routes and process mismatches produce distinct actionable
  errors. A 404 never marks the worker stopped. HTTP acknowledgements and older
  polling snapshots cannot move a pending/STOPPING UI back to RUNNING.
- Shared admission spans initialization, every atomic generation and
  finalization. Release occurs in worker cleanup, after all GA/persistence work
  and terminal delivery attempts. No further GA work runs after release.
  `execution_active` becomes false on cleanup, and the state callback is detached
  so terminal registry records do not retain stream queues.

### Refresh and bounded monitoring recovery

On mount the frontend checks `/status` while loading the last completed result.
It adopts the current active run, including its authoritative ID, state,
configuration, elapsed time and latest validated progress. Start remains disabled
until discovery finishes and while that execution is active. A pre-start discovery
that finds a run adopts it instead of posting a second stream.

Browser session storage contains only `{run_id, process_instance_id}`. It is not a
population checkpoint. If the worker has just terminated, the same-process
remembered ID allows querying its terminal state and fetching its validated
result. If the process changed or the run disappeared, the UI reports
**Previous run interrupted or unknown**, with an explicit statement that its
population was not restored. It does not assert cancellation, completion, or
recoverability of the lost worker. Durable stopped results remain readable by ID.

Recovery uses serialized read-only state polling: one request at a time, then a
one-second delay. There is no new SSE replay queue, no second GA start, no new
background worker, and no population restore. The backend caches only one latest
validated metric per run. The UI explicitly says **Earlier events may be missing**
and plots only observed snapshots. Normal SSE disconnect also attempts this
polling fallback when its run/process identity is known. Unmount cancels timers
and ignores late replies. Failed polling reports DISCONNECTED or INTERRUPTED and
offers honest guidance to refresh for rediscovery.

The original SSE queue remains bounded at 1024 events; disconnect detaches it.
Slow structured-event delivery retains the existing fail-safe behavior. A browser
disconnect does not release admission or stop the worker. Terminal registry
retention is still unbounded over the lifetime of the process; TTL/pruning is a
future lifecycle task. HTTP polling has no automatic transport retry after a
failed request, and full historical graph replay is outside this phase.

### Development launch and manual verification

Run one backend worker **without reload during an active GA**. From the backend
directory, using the project's virtual environment:

```powershell
..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
```

Restart the updated backend before a new manual test. Verify
`GET http://127.0.0.1:8000/api/ga/status` advertises `control_version: "3c.1"` and
the stop path exists in `/openapi.json`. Existing README commands with `--reload`
can discard this volatile registry when files change. Multiple workers have
separate registries and admission locks and remain unsupported.

Use an isolated development dataset/output directory for acceptance. The
automated integration tests use small deterministic fixtures and temporary
artifact paths; they do not run or save a full production GA.

1. Start a bounded run with enough generations to allow stopping; verify the
   displayed server run ID matches the first SSE `run_created` and GET state.
2. During generation 1, click Stop. Inspect the separate POST URL and process
   header, verify accepted STOP_REQUESTED, then STOPPING and STOPPED. The current
   atomic generation may finish; no subsequent generation begins.
3. Retrieve the stopped schedule and verify hard validation passes. Verify the
   latest completed result's bytes remain unchanged. A repeated terminal stop
   returns accepted false and the actual STOPPED state.
4. Start another bounded run, refresh the browser while it is running, verify
   the same run ID/configuration/progress and the missing-history notice. Verify
   no second stream POST occurs. Stop the recovered run and inspect its result.
5. Restart the backend with a remembered active ID. Verify interrupted/unknown,
   rather than a resumed population. Start controls must first recheck the new
   process. Confirm saved results still require validation before display.
6. Simulate a legacy backend or missing stop route: verify an actionable error
   and continued monitoring, with no STOPPED inference.

### Incremental Phase 3C.1 files

- Backend: `routers/genetic_algorithm.py`, `services/ga_control_service.py`, new
  `tests/test_ga_refresh_recovery.py`.
- Frontend: `context/GAContext.tsx`, `services/gaService.ts`,
  `services/gaMonitoring.ts`, new `services/gaRecovery.ts`,
  `components/ga/LiveGAMonitor.tsx`, `pages/admin/GenerateSchedule.tsx`,
  `pages/admin/Dashboard.tsx`, `pages/admin/FitnessAnalysis.tsx`, `package.json`,
  `tests/gaMonitoring.browser.test.mjs`, new `tests/gaRecovery.test.mjs`.
- Documentation: this file.

GA service mathematics, scorer, operators, validation rules, notebooks, faculty
preferences and existing saved artifacts were not changed by Phase 3C.1.

### Phase 3C.1 verification results

- **199 targeted backend tests passed** in 705.94 seconds (two existing warnings),
  including the original 22 safe-stop tests and five new recovery/integration tests.
  Actual Uvicorn/HTTP streaming tests capture the registered first-frame ID and
  stop through a separate HTTP client, both with and without disconnect. They
  prove no generation beyond the current safe boundary, repeated-stop behavior,
  duplicate-start rejection, hard-valid stopped results and unchanged latest
  completed storage. Other tests distinguish missing-route 404 from unknown-run
  404, reject stale process headers before starting a worker, and retrieve a
  completed result only by its exact identity.
- **16 frontend stream/recovery tests** and **11 GA browser tests** passed. Browser
  cases cover live metrics, stop ordering, missing-route errors, legacy capability
  rejection, remount discovery, polling after refresh, stop from the recovered
  page, no duplicate stream POST, mismatched result rejection, and process loss.
- **19 preference model tests** and **22 preference browser tests** passed. The
  first concurrent preference browser run missed its transient 120 ms saving
  assertion; the unchanged test passed when rerun after the CPU-intensive backend
  suite ended. No preference implementation or test file was edited.
- TypeScript/production build and focused changed-file lint passed. The existing
  large-bundle warning remains. GAContext's pre-existing mixed component/hook
  export rule was excluded for its focused lint check. `git diff --check` passed.
- Hashes of `faculty_preferences.json`, `latest_ga_result.json` and
  `best_chromosome.json` match the pre-task values. All integration artifacts
  were written to temporary test destinations. No full production GA was run,
  and no commit or push was made.

## Tests and manual verification

All new backend tests use small real-offering fixtures and isolated storage.
They cover no-op control equivalence (random state, scorer-call counts, schedules,
history, breakdown and analysis), early no-result stopping, initialization and
crossover/mutation boundaries, bounded rejected-child retries, final-generation
stop, concurrent stop/completion, repeated/unknown/terminal/conflicting requests,
admission during STOP_REQUESTED/STOPPING, worker/persistence failure, disconnect,
atomic write failure, valid global-best preservation, stopped-result validation,
and retrieval after registry loss.

Frontend tests cover pending stop progress, no-result STOPPED, disconnect during
cancellation, contradictions and failure. Browser scenarios exercise the real
React UI with mocked SSE/control responses; no production GA is run or saved.
Existing Phase 2 preference model/browser regressions remain required.

```text
.venv/Scripts/python.exe -m pytest backend/tests/test_ga_safe_stop.py -q
.venv/Scripts/python.exe -m pytest backend/tests/test_ga_api_crossover.py backend/tests/test_ga_hard_constraints.py backend/tests/test_ga_monitoring.py backend/tests/test_ga_safe_stop.py backend/tests/test_ga_refresh_recovery.py backend/tests/test_metadata_api.py backend/tests/test_preassigned_assignments.py backend/tests/test_preference_validation.py backend/tests/test_tournament_selection.py -q
npm.cmd --prefix frontend run test:ga
npm.cmd --prefix frontend run test:ga:browser
npm.cmd --prefix frontend run test:preferences
npm.cmd --prefix frontend run test:preferences:browser
npm.cmd --prefix frontend run build
```

Phase 3C baseline results: **194 targeted backend tests passed**, including **22 safe-stop
tests**; **12 stream/parser tests**, **6 GA browser tests**, **19 preference model
tests** and **22 preference browser tests** passed. The frontend production build
passed (the existing large-bundle warning remains). Focused changed-file lint
passed; GAContext also passed with its pre-existing mixed component/hook export
rule excluded. `git diff --check` passed. No whole-production GA or broad legacy
smoke suite was run. Faculty preference bytes and existing saved artifacts were
preserved; no commit or push was made.

Manual acceptance in a development environment with isolated data/output paths:

1. Start a short run, verify INITIALIZING then live generation metrics.
2. Click Stop Generation; verify immediate pending text and a disabled button.
3. Verify another generation request receives 409 until the first worker exits.
4. Verify STOPPED appears only after the worker finishes a validated boundary and
   saves its artifact; inspect the preserved schedule and interruption label.
5. Verify the latest completed file remains unchanged, and repeated stop calls
   return the actual terminal state with accepted false.
6. Disconnect while pending; verify snapshot polling recovers authoritative
   monitoring when the same process remains reachable, or reports disconnected
   when status polling also fails. Reconnection is not a population resume.
7. Retain the run ID, restart the server, and retrieve its stopped result. Active
   state is lost, and no active optimization can be resumed.

## Files changed and limitations

Backend: `routers/genetic_algorithm.py`, `schemas/ga_events.py`,
`services/ga_service.py`, `services/ga_progress_service.py`, new
`services/ga_control_service.py`, and new `tests/test_ga_safe_stop.py`.

Frontend: `context/GAContext.tsx`, `services/gaService.ts`,
`services/gaMonitoring.ts`, `types/ga.ts`, `components/ga/LiveGAMonitor.tsx`,
`pages/admin/GenerateSchedule.tsx`, `Dashboard.tsx`, `FitnessAnalysis.tsx`, and
`tests/gaMonitoring.test.mjs`, `tests/gaMonitoring.browser.test.mjs`.

Also changed: `.gitignore` and this document. Faculty preference data, notebook,
GA operator/scorer files, hard-validation service, eligibility and preassignments
are untouched. No commit or push is performed.

- Run registry/admission are single-process and volatile. Deploy with one backend
  worker. Multiple workers, process/server restarts and daemon-thread shutdown do
  not preserve active work. Stopped artifacts survive; active population and RNG
  state do not. Registry retention/TTL cleanup remains future work.
- Authentication/ownership enforcement is outside this phase. The existing admin
  UI exposes controls, but the backend is not newly authenticated. Anyone with
  endpoint access and a run ID can request stop.
- No event replay (Phase 3C.1 adds snapshot-polling reconnection), historical generation snapshots, full population,
  checkpoint, pause/resume, PostgreSQL, PMX, exports or notebook refactoring.
- Input files are fingerprinted, not transactionally frozen. Stop latency depends
  on completing existing initialization/operator/retry/validation work.
- Existing global-best/latest persistence is not newly atomic or transactional;
  only the new stopped artifacts use the atomic writer.

Phase 3D can build on the run identity, lifecycle, admission and safe-boundary
ownership. It still requires a distinct checkpoint design preserving the entire
survivor population, best-ever, generation/plateau counters, input/configuration
snapshot and all random state, with validated reconstruction and recovery. A
saved best schedule or this registry alone is insufficient for pause/resume.
