# Phase 3E.1 — history and checkpoint verification

## Verified findings

The durable run is `d48c257b-3057-47e4-8158-c0f84f422b3c`, rather than the `4d8…` identity in the request. Its marker is PAUSED, with no active worker, generation 1 completed, and a complete population of five. Its original generation limit is five. The next generation is two.

Both recorded generations pass checksum, schema, candidate/index identity, schedule reconstruction, and the existing publication hard gate. Generation 0 has best/best-ever 20875 and average 22037; generation 1 has best/best-ever 20790 and average 20828. No snapshot, checkpoint, lifecycle marker, preference file, or saved chromosome was rewritten during diagnosis.

No backend was listening on port 8000 at the initial inspection. Starting a read-only backend and testing run listing, generation listing/detail, schedule, analysis, comparison, candidate exports and comparison export produced successful responses. The original historical HTTP 422 could not be reproduced or attributed to an endpoint from the available evidence. Do not describe the archive as corrupt or invent a historical failure cause.

The checkpoint's exact engine fingerprint matches the system Python 3.14.2 with pandas 3.0.5 and NumPy 2.5.2. The project virtual environment uses pandas 3.0.6 and NumPy 2.5.3 and correctly rejects this artifact as incompatible. This is an observed environment distinction, not proof that it caused the original timeout. Use the creating runtime to resume; do not edit fingerprints or disable compatibility checks.

## Demonstrated causes and correction

The saved graph has 417,252 nodes, including 391,386 TimeBlocks. The working templates contain calendar links into assignment graphs. Read-only reconstruction previously deep-copied those graphs repeatedly. Checkpoint verification validates each population member and best-ever against current and original templates. Simultaneous status requests repeated the entire restore and validation. Two overlapping HTTP requests using the recorded working templates reproduced the frontend's 120-second timeout. History listing remained responsive: no lifecycle/storage lock deadlock was observed. The expensive work was repeated graph traversal and validation, with CPU contention.

`ga_validation_templates` constructs detached validation templates preserving every profile field, eligibility, workload limit/target, preference, calendar shape, fixed-schedule metadata and preassignment declaration. It omits assignment references that the existing reconstruction replaces. It never modifies a population, checkpoint state, working template or RNG. Existing validators still check schedules and faculty profiles. The saved publication/working templates and complete RNG state inside checkpoints are unchanged.

`ga_checkpoint_verification` shares a single full verification for concurrent identical requests. Its bounded cache holds at most eight scalar answers, never populations. Each request hashes the compressed artifact bytes, current inputs, engine and detached template metadata; changes invalidate reuse. Verification runs outside the cache and RunControl locks. Lifecycle and checkpoint reference are reconciled again by the router before Resume can be enabled. Missing storage and invalid compression produce explicit errors. Resume independently loads and fully validates the original checkpoint; a cached status cannot supply continuation state or bypass admission.

History inspection clears a previous error only after the same request scope succeeds. Previously, a failed generation could retain its error after navigating away and returning to a successful inspection. The browser regression exercises a failed analysis, another generation, then successful reinspection. Errors now identify the operation and code, distinguishing HTTP 404/missing records, 422/corrupt schema or hard-validation failure, 409/incompatible inputs, 503/unavailable storage, transport failure and timeout. JSON reading has a finite deadline, including stalled bodies; existing timeout values were not increased. Unexpected backend failures retain an internal traceback.

Schedule inspection additionally applies the existing hard gate when the original inputs are current. Changed-input history remains explicitly labeled as an original validated observation; exports still require original inputs. A damaged schedule fails the gate even if its checksum and candidate IDs have been recomputed. No additional fitness evaluation is performed.

## Measured latency

Read-only requests only; no production GA generation or continuation was executed. These are workstation measurements, with background regression work and varying contention, not a throughput guarantee.

| Request/context | Before | After |
| --- | ---: | ---: |
| Generation 1 export against recorded working templates | 20.871 s | 1.595 s |
| Checkpoint status against recorded working templates, single request | 73.193 s | 16.806 s first / 1.315 s cached |
| Two overlapping checkpoint HTTP reads against those templates | Both timed out at 120.46 s | Both returned verified results at about 83 s under continuing contention; subsequent cached read 1.547 s |
| Current matching backend, checkpoint status | Fresh-process original validator: 11.870 s | 16.849 s first / 2.158 s cached |

After deployment to the matching local backend, generation listing took 0.181 s, schedule inspection 2.375–2.406 s including its additional hard gate, analysis 0.007 s and comparison 0.016 s. The measured improvement is strongest for dirty working templates and repeated/concurrent verification; a first pristine verification still pays full integrity and hard-validation cost.

## Acceptance procedure

1. Start a single backend process using the runtime that created the paused checkpoint. For this particular artifact, that is `C:/Users/User/AppData/Local/Python/pythoncore-3.14-64/python.exe`, not `.venv/Scripts/python.exe`.
2. Refresh Generate Schedule so discovery adopts the current process ID. Confirm the original `d48…` run, PAUSED state, generation 1, population 5/5, best-ever 20790 and average 20828. Do not treat saved best as a population.
3. Open Generation History for that same identity. Inspect generations 0 and 1, both candidate kinds, workload data, comparison and exports. There should be no validation warning for this archive.
4. Request checkpoint status concurrently with history inspection. It must return authoritative PAUSED state and `resumable: true`, with no new worker or artifact rewrite. A repeated unchanged request should reuse verification.
5. If continuing the actual run is desired, choose Resume Generation. It must keep the same identity/population and continue at generation 2. Diagnosis deliberately left this production run PAUSED.
6. In isolated fixtures, repeat refresh/restart, stop-versus-pause races, incompatible runtime/input changes, byte tampering with preserved mtime, malformed snapshots, missing storage and transport/body timeouts. Failures must disable continuation or schedule publication without losing valid metrics/history.

## Tests and scope

New backend regressions cover detached templates, concurrent history/checkpoint access, single-flight reuse, byte/input/engine/profile invalidation, restart/refresh/same-run continuation, stop-state reconciliation, hard-invalid schedules and storage-versus-corruption errors. Browser tests cover successful reinspection after a transient analysis failure and real HTTP history/checkpoint reads during paused refresh before resuming the isolated fixture. Existing monitoring/control/logging, checkpoint continuation, RNG and complete fitness-call equivalence checks remain required.

Phase 3E.1 changed the GA router, history router/service, two new validation/verification services, GenerationHistory and gaHistory, three frontend test files, a new backend test module and this documentation. The seven fingerprinted services, all GA source files, institutional data and this run's saved artifacts retained their original SHA-256 hashes. Checkpoint schema remains version 1. No commits, pushes, PostgreSQL changes or Phase 3F features are included.

The existing paused-recovery tests now mock the route's new verification provider when exercising synthetic lifecycle transitions. The existing `wait_finished` test helper waits for admission cleanup as well as inactive execution, so temporary fixtures cannot be torn down while the asynchronous worker is finishing history lifecycle persistence. Production admission logic was not altered.

## Files changed in Phase 3E.1

- Backend: [GA router](../backend/routers/genetic_algorithm.py), [history router](../backend/routers/ga_history.py), [history service](../backend/services/ga_history_service.py), [detached validation templates](../backend/services/ga_validation_templates.py), [checkpoint verification](../backend/services/ga_checkpoint_verification.py).
- Frontend: [GenerationHistory](../frontend/src/pages/admin/GenerationHistory.tsx), [history API client](../frontend/src/services/gaHistory.ts).
- Tests: [history/checkpoint recovery](../backend/tests/test_ga_history_checkpoint_recovery.py), [paused recovery](../backend/tests/test_ga_paused_recovery.py), [pause/resume helper](../backend/tests/test_ga_pause_resume.py), [history contracts](../frontend/tests/gaHistory.test.mjs), [browser monitoring/history](../frontend/tests/gaMonitoring.browser.test.mjs), [real HTTP/browser recovery](../frontend/tests/gaPausedRecovery.integration.mjs).
- Documentation: [Phase 3E](phase-3e-generation-history.md) and this report.

## Verification results

- 129 distinct backend cases passed across regression runs and focused reruns: 43 generation-history/pause-resume cases, 75 monitoring/stop/recovery/control/logging cases, 10 new history/checkpoint cases, and one real HTTP/browser integration. Synthetic verification tests were updated to the new provider, and asynchronous teardown was corrected before the focused reruns passed.
- 39 frontend contract cases and 41 browser-suite checks passed. The real browser integration also passed against the isolated FastAPI fixture, exercising start, pause acknowledgement, refresh, concurrent history/checkpoint inspection and same-population resume.
- Frontend production build and focused ESLint passed. The existing large-bundle build warning remains. `git diff --check` passed.
- A union of 67 protected file hashes, including the original paused artifact files and prior protected GA/data/saved/notebook files, remained unchanged. The exact RNG state and complete fitness-call count equivalence regressions passed.
- The production run was never resumed, stopped or regenerated; final read-only verification reported PAUSED, generation 1 completed, `resumable: true`, next generation 2.

## Limitations

- The original historical 422's failing request remains unverified because its response/traceback was unavailable; successful current reads prove neither that it never occurred nor that the archive was corrupt. Future failures now identify the operation and retain backend diagnostics.
- Full first verification remains CPU-intensive and synchronous in a FastAPI worker thread. Concurrent identical reads share work, but unrelated large checkpoints can still compete for resources. The cache is process-local and is discarded on restart.
- Compatibility requires the original engine, inputs and package versions. Changed inputs can be inspected as original observations but cannot be exported or resumed as though they were current.
- This remains a single-backend-process prototype. History reads do not control execution, and inspection does not imply that a population can be resumed from a generation-best snapshot alone.
