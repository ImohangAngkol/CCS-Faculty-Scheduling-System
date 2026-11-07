# U5F — controlled continuous optimization foundation

2026-11-05, Asia/Manila. Base: `main`, `d6db077793da52b7559351a5d0f8e6d54608cb77`.

**PARTIALLY IMPLEMENTED: mode selection, protected read-only readiness, lifecycle contract and fixed-run qualification. Continuous optimization is NOT EXECUTABLE for either institutional or fictional datasets.** This uses the request's explicit Phase 4 fallback: complete the UI and lifecycle foundation when trustworthy immutable consumption cannot be established safely. No continuous engine, worker, checkpoint or optimization progress is fabricated.

## Investigation and implementation decision

Before editing, inspected the existing `/run` and `/stream` lifecycle, V1/V2 execution, progress and control services, Saved Best finalization, checkpoint engine/input fingerprints, frozen scoring inputs, U5D receipts, U5E analysis, Generate Schedule, authentication and Chair capability services. No AGENTS.md was found. U5D (24-path inventory) and U5E-R2 (268-path inventory, 267 artifact hashes) remain uncommitted. Their current source and evidence are preserved separately.

The implementation plan was: retain fixed execution; add a strictly blocked, administrator-readable continuous readiness contract; add mode selection and honest loading/error/retry; qualify existing fixed controls with fictional inputs; prepare an independently testable selective source snapshot. Do not extend the optimizer until consumption, authority, versioning and resource ownership are proven.

| Boundary | Observed current behavior | Continuous consequence |
|---|---|---|
| Loading and preprocessing | `genetic_algorithm/utils/Functions.py` constructs module-level faculty, subject and room models and transformed preference data. `ga_service.py` consumes cached model lists and `df_faculty_pref`; scheduling mutates calendars. | Hashing files is not an immutable consumed-model bundle. File/model/alias changes and reset/reconstruction boundaries need an explicit run-local ownership contract. |
| Scoring freeze | `FrozenInputs.py` supplies a run-local scoring context for selected preferences/settings. | Useful existing protection, but does not prove that every faculty, subject, section, room, slot and transformed dependency consumed by optimization is frozen. |
| U5D | Captures run-bound observations; receipts remain UNVERIFIED, with no proof of full optimizer consumption. | No promotion to VERIFIED or CURRENT. Receipt existence cannot authorize continuous execution. |
| V1 loop | `run_genetic_algorithm` iterates a finite generation range; checkpoint parameters include the exact generation limit. | A large limit is still fixed execution. Repeating fixed runs changes run identity/RNG/population/finalization behavior and cannot implement continuation. |
| Best and finalization | Original engine retains best-ever by copying and elitism, validates publication and calls `save_best_if_better` before router finalization. | Reusing finite runs would invoke historical Saved Best behavior. Continuous needs separate run-local eligible-best persistence before any new execution is enabled. |
| Worker | Existing stream/resume paths use a daemon thread, one process-local execution lock and a bounded 1,024-event queue. Browser disconnect detaches monitoring rather than proving worker termination. | No new worker was added. Process-local admission is not a distributed run-ownership guarantee; continuous shutdown/join, recovery and storage budgets are absent. |
| Cancellation | Existing run control is cooperative at validated generation boundaries. | A stop request is not STOPPED until acknowledged; it cannot interrupt a single in-progress fitness/operator call. No bounded continuous cancellation latency is claimed. |
| Checkpoints | Strict input/engine fingerprint and parameter checks reject incompatible restoration. Fingerprinted sources include GA/orchestration/control/persistence services. | Those sources and checks stay byte-identical. Continuous requires explicit versioning, not altered fingerprints, reinterpretation of old checkpoints or runtime replacement of engine symbols. |
| Authority | `require_admin` protects the existing Generate route; Chair authority uses a separate scoped institutional mandate. The institutional Chair directory/provider is unavailable. | Administrator access to readiness does not grant Chair optimization authority. No run-to-department optimization mandate or institutional provider was activated. |

## Implemented API and frontend

`GET /api/ga/continuous/readiness` is the **only new route**. It uses existing `require_admin`; anonymous requests fail authentication and non-administrators fail authorization. Query parameters, GET bodies and activation/context inputs are rejected. There is no start, pause, resume or stop route under this prefix, no provider/environment switch and no read-side persistence or admission.

Response contract `ga-continuous-foundation-v1`, schema 1:

- `availability: BLOCKED`, `executable: false`, `supported_datasets: []`.
- `input_consumption: NOT_ESTABLISHED`, `receipt_capability: UNVERIFIED_ONLY`, institutional authorization NOT_ESTABLISHED.
- Five explicit requirements: immutable consumption; scoped authority; versioned worker; enforced resource limits; run-local persistence.
- Lifecycle vocabulary: IDLE, STARTING, RUNNING, PAUSING, PAUSED, RESUMING, STOPPING, STOPPED, COMPLETED, FAILED, INTERRUPTED. **Contract vocabulary only; no continuous state machine or command execution is installed.**
- Safeguards explicitly NOT_IMPLEMENTED. They specify scoped admission, CPU/private-memory budget, wall deadline, bounded retries/cooperative cancellation, checkpoint/history quotas, free disk and atomic writes, owned shutdown/join and checkpoint/input revalidation. They are not advertised as active protections.

Generate Schedule defaults to Fixed Generations. Its existing parameters, starting population choices, V2 panel, validation and execution functions remain. Continuous selection fetches only readiness, hides/disables fixed submission and displays existing draft population/fresh values as read-only context. Switching back preserves parameter state. Selection or refresh never starts a run. An explicit handler guard also prevents hidden fixed submission. Start Optimization is always disabled, including for malformed or forged executable responses. Readiness requests are abortable and responses are attempt-bound; loading/error/retry are accessible. Teal/gold styling is retained, including mobile layout.

The existing fixed monitor remains visible and clearly separate. Pause/resume/stop use its original backend-confirmed states and run identity. **Intentional UI addition:** stopping from this page now requires native browser confirmation before the existing `stopGA` call. Cancel sends no command. Accept still requires backend acknowledgment. Backend control protocol and optimizer behavior do not change. Earlier unfinished Live Center browser expectations that assumed no confirmation are not asserted as fresh passes.

An available existing run ID can link to `/admin/analysis?view=advanced&run=...&candidate=best_ever`. Current U5E work supports the advanced query; the independently staged HEAD application retains its existing analysis route. The new foundation does not require U5E source, create analysis observations or promise advanced plots in a release without U5E. No fabricated subject/day/time/faculty satisfaction metrics are added.

## Best-so-far and checkpoint semantics

No continuous chromosome exists. Current-generation best, original fixed run best-ever and historical Saved Best remain distinct. No discovery generation, evaluated-candidate count or satisfaction history is invented when unavailable. Existing U5E projections retain their recorded-data limitations and metric definitions; lower fitness is not claimed to improve every faculty member's satisfaction.

The three original D10 current-release V1 continuation cases are invoked unchanged in an isolated fictional source snapshot. They create/load real JSON checkpoints and compare uninterrupted versus resumed assignments, histories, fitness breakdown, faculty analysis, RNG state and fingerprint equality at pause generations 0, 1 and 2. API qualification separately covers registry replacement (simulated backend restart), discovery, actual resume, duplicate controls, concurrent admission, cancellation and injected worker failure. Strict drift checks reject changed fictional preference bytes and changed fitness settings with `GA_CHECKPOINT_INPUT_CHANGED`; no fingerprint is mocked or spoofed.

These are fixed-engine tests, not evidence for a continuous worker. Existing historical checkpoints and their pre-existing compatibility limitations are preserved, not migrated or reinterpreted. The read-only foundation never calls Saved Best. Fixed engine qualification may write a fictional best result only inside the owned disposable source snapshot; application Saved Best and history are untouched.

## Validation and attribution

All commands and unsuccessful intermediate records are retained under [dashboard-u5f](testing/dashboard-u5f/). Final counts and artifact identities are sealed by the [manifest](testing/dashboard-u5f/manifest.json); repeated worktree/snapshot executions are not added together as unique tests.

| Verification | Result / scope |
|---|---|
| New backend readiness/control contracts | 20 passed; actual FastAPI TestClient, fictional principals; SQLAlchemy connection forbidden; concurrent read-side effect guards. |
| Existing U5D receipt tests | 36 passed; fictional temporary fixtures/owned loopback tests. No receipt promotion. |
| U5A–U5C source/context/compatibility backend regressions | 99 passed; legacy roster-backed suites excluded from qualification. No PostgreSQL. |
| Fixed-engine source-snapshot qualification | 9 passed, including the 3 original real-checkpoint/RNG parity cases. 147.88 seconds pytest time. |
| New frontend contracts | 14 passed. |
| Existing frontend compatibility/dashboard/auth/GA monitoring/history regressions | 166 passed. |
| U5E analysis and interaction contracts | 30 passed. |
| Worktree browser | 16 scenarios passed; Node reports 17 including the parent suite. Actual Edge/React; fictional intercepted HTTP acknowledgments, no live FastAPI/GA browser execution. |
| U5F-only proposed source snapshot | All 8 groups passed: backend, fixed qualification, frontend contracts/regressions, TypeScript, bundle, lint and 16 browser scenarios. It excludes U5D, U5E and unfinished Live Center source. |
| TypeScript, production build, focused ESLint | Worktree passed. Existing bundle warnings concern mixed static/dynamic imports and chunk size. No dependency changes. |
| PostgreSQL, genuine authority, continuous execution | NOT RUN / BLOCKED. D15 database and acceptance evidence untouched. |

Final distinct selections total **164 Python tests** (20 + 36 + 99 + 9), **210 frontend contracts** (14 + 166 + 30), and **16 browser scenarios**. Snapshot repeats of the same cases are additional independent executions, not additional unique requirements. Earlier failed/timeout attempts remain failed historical evidence. `git fsck --no-reflogs` returned exit 0; existing dangling objects were reported, with no integrity error or cleanup performed.

Test environment: Windows, existing Python 3.14 environment, Node v24.11.1, Edge 156.0.4314.50. Backend warnings: Starlette TestClient `httpx` deprecation and AnyIO `BlockingPortal` alias deprecation. Neither is a new GA failure; no dependency was installed. Temporary child environments whitelist OS variables and exclude database URLs, credentials and activation flags.

The earlier legacy `test_ga_safe_stop`, `test_ga_pause_resume` and `test_ga_monitoring` fixtures import `small_population` from a suite that loads actual academic offerings/faculty. They are **excluded from new U5F qualification**. One additional inherited backend regression selection was mistakenly started before noticing that `test_fitness_reporting` and `test_ga_generation_history` reuse these fixtures. It exceeded the 300-second harness bound; only 30 progress dots and timeout text were retained publicly. Its two owned pytest processes were identity-verified and stopped; the failed record remains, with its overly broad fictional-scope metadata corrected by an explicit addendum in `tooling-failures.json`. It receives no fictional acceptance credit. The final regression selection excludes both suites. No private faculty output is archived, and all 3,539 baseline paths outside the two intended integrations were verified unchanged afterward.

The new source-snapshot qualification uses the original operators with explicitly fictional D10 models and empty fictional import tables. The fixed API fixture explicitly sets supported mutation attempts to 1 and restarts to 5; original crossover attempts and all algorithm functions remain unchanged. Its final measured completion case took 24.44 seconds; the three original continuation/parity cases took 38.84, 35.75 and 33.62 seconds. These are functional test durations, not performance guarantees or continuous cancellation benchmarks.

### Preserved unsuccessful attempts

- Harness generation initially failed to match an existing `finally` anchor; a missing test-file command then failed before any browser scenario. A new standalone harness was generated; original unfinished files remain unchanged.
- First actual browser attempt passed B01–B03, then selected a radio before React finished mounting after navigation. The test now waits for the mounted selector.
- Next attempt passed B01–B09, then counted intercepted CORS OPTIONS together with POST pause commands and timed out. The assertion now counts POST only. Cancelled cases were not passes.
- Two proposed-source fixed qualifications each reported **8 passed, 1 failed** at `test_real_pause_restart_discovery_and_checkpoint_resume`: the test's 25-second completion assertion expired during original finite crossover work. Both logs retain eventual `GENETIC ALGORITHM COMPLETED`; the worker relinquished admission. Reducing only test mutation attempts did not resolve the second attempt. The unchanged engine can perform 40 × 100 crossover attempts per generation; the final fixture uses a bounded 90-second functional wait and records per-case durations, without a claim of 25-second responsiveness or any production timeout change.
- Two preliminary proposed-snapshot setups had differing HEAD/worktree JSX anchors. Exact insertion transforms now support both while checking all entry bytes. No test success was claimed for setup failures.
- The inherited legacy backend selection described above timed out and was stopped; it is not a passing or fictional-only suite. Its failure and corrected attribution remain separate from the final safe selection.

No historical failure was deleted or replaced. [tooling-failures.json](testing/dashboard-u5f/tooling-failures.json) attributes setup issues; raw browser/pytest records retain actual failed outcomes. Slow original crossover is a future performance/cancellation consideration, not proof of safe continuous operation.

## Preservation, exact inventory and selective checkpoint plan

The pre-edit baseline hashes **3,541 paths**, including all **23 academic files**, protected preference/settings JSON, original GA/scoring/RNG sources, fingerprinted services, migrations, historical checkpoints/schedules, ignored runtime stores, prior research/U5D/U5E evidence and Git index. Only `backend/main.py` and `frontend/src/pages/admin/GenerateSchedule.tsx` have U5F additions; all other **3,539** baseline paths must match. Both mixed files are also checked against exact insertion transforms of archived entry bytes.

Existing modified files:

1. `backend/main.py`: new router import/registration only, preserving the uncommitted U5E router.
2. `frontend/src/pages/admin/GenerateSchedule.tsx`: mode integration, disabled/hidden fixed form, execution guard and Stop confirmation, preserving unfinished U4/Live Center edits.

New implementation/tests:

- `backend/services/continuous_readiness.py`
- `backend/routers/continuous_optimization.py`
- `backend/tests/test_continuous_readiness.py`
- `backend/tests/test_continuous_fixed_qualification.py`
- `frontend/src/services/continuousOptimization.ts`
- `frontend/src/components/ga/OptimizationMode.tsx`
- `frontend/tests/continuousOptimization.test.mjs`
- `frontend/tests/continuousOptimization.browser.test.mjs`
- `frontend/tests/continuousOptimization.fixtures.mjs`
- `frontend/tests/continuousOptimizationRun.fixtures.mjs`
- `frontend/tests/continuousOptimization.scenarios.mjs`

This report and every exact new tooling, entry-byte, patch, JSON and PNG path are enumerated in `exact_checkpoint_inventory` in the manifest and [staging-plan.json](testing/dashboard-u5f/staging-plan.json). Raw artifact hashes include failed evidence. PNG dimensions/CRCs/metadata and original visual privacy review are recorded. Text is scanned for complete/truncated encoded session fragments, credential URLs/headers and private faculty names locally without exporting those records. No cookies, receipt values, institutional rows or DB artifacts are archived.

**No actual staging, commit, push or fetch.** Current HEAD and index must match entry. U5D and U5E remain separate uncommitted milestones. Both mixed files require partial staging; do not add either whole working file. The two exact HEAD-based integration patches pass `git apply --check --cached` without changing the index. The source-snapshot rehearsal copies HEAD plus only proposed U5F blobs into an owned OS-temp directory, bootstraps fictional data, uses installed dependencies and retains strict original engine byte/fingerprint checks. Source hashes and proposed Git blob OIDs bind those results to the selective checkpoint.

After separate authorization and fresh upstream/inventory verification, recommended commits are:

1. `feat(ga): add blocked continuous-mode readiness foundation`
2. `docs(testing): archive U5F foundation and fixed lifecycle qualification`

Only literal paths in the staging plan plus its two partial patches are eligible. Preserve every other working-tree change. No broad add, reset, restore, clean or original artifact rewrite is permitted. Checkpoint readiness is for the accurately labelled foundation, **not for shipping continuous execution**.

## Reproduce safely

From the repository root in PowerShell, using existing dependencies:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5f/run_checks.py backend
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5f/run_checks.py receipts
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5f/run_checks.py backend-regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5f/run_checks.py focused
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5f/run_checks.py regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5f/run_checks.py u5e-contracts
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5f/run_checks.py build
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5f/run_checks.py bundle
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5f/run_checks.py lint
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5f/run_checks.py browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5f/checkpoint_snapshot.py
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5f/audit_evidence.py
```

Tests create new run directories and do not overwrite sealed evidence. A later rerun adds artifacts outside the sealed inventory; audit requires a separately versioned addendum rather than silently re-sealing history. The snapshot script refuses changed HEAD/index assumptions and writes only new owned temporary paths. Do not regenerate the already-created browser harness or run the real fixed qualification directly against academic data (it skips outside the owned snapshot).

## Remaining blockers and next milestone

1. Define and prove a run-owned complete consumed-input bundle, including transformed caches, resource/calendar ownership, scoring configuration and drift checks through restart/reconstruction. Keep U5D UNVERIFIED until that proof exists.
2. Establish the genuine scoped Chair optimization mandate and department/run binding; administrative UI access alone is insufficient.
3. Implement a separately versioned managed worker with explicit continuous admission, cooperative lifecycle, durable ownership/restart semantics, bounded resource/history/checkpoint/disk usage, shutdown join and audited safety termination. Preserve supported fixed checkpoint fingerprints and reject incompatible continuation explicitly.
4. Specify continuous run-local best-ever/provenance and persistence without historical Saved Best promotion. Validate checkpoint recovery and interruptions before adding real controls/progress.
5. Qualify the above first with isolated fictional inputs and live browser-to-backend acceptance, then seek separately authorized institutional data/provider evaluation.

Stop here. No continuous activation, institutional publication/approval, new database work, GA optimization change, C++ work or next milestone has been performed.
