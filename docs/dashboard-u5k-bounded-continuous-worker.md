# U5K — bounded continuous GA worker foundation

Implemented 2026-11-08, Asia/Manila, on `main` at `5d4d02c52f67b30b6dec13179d0389e5dc46daf5`. **An isolated, Windows-only worker foundation is implemented. Production admission remains BLOCKED and the existing Continuous Optimization UI remains DISABLED.** No new HTTP route, deployed provider, database migration or frontend activation was introduced.

This worker advances one immutable, finite U5H optimization horizon in bounded batches. It does not repeatedly initialize fresh GA runs, extend a checkpoint's generation configuration or run indefinitely. Reaching the original generation ceiling produces COMPLETED. Any later horizon requires a separately admitted run and an approved compatibility contract; this milestone provides no extension mechanism.

## Investigation and prerequisites

The inspected execution chain is the existing fixed router → original `ga_service.run_genetic_algorithm`; U5G canonical bundles → U5H private optimizer runtime and versioned checkpoints; U5I server-generated admissions, owned SQLite storage and fencing; U5J independent scoped mandates, guarded prepared-input capture and storage inspection. U5G precedes U5H, followed by U5I and U5J in the committed baseline. Their 231 artifact-hash references were rechecked without rewriting historical manifests.

U5H already pauses after complete generation validation, persists population/best/history/private RNG, and restores that exact state with strict source, loaded-runtime, input and configuration fingerprints. Its stop-before-next-draw finalization supplies the original rich result projection without advancing the search. Those contracts permit external process supervision without modifying original operators or introducing another fitness implementation.

U5I production `configured_service()` still returns `None`. U5J has no deployed institutional issuer, source catalog or approved storage location. Administrator role alone is not scoped optimization authority or Department Chair authority. The U5F readiness endpoint and frontend remain the original blocked contract. Existing U5D HTTP receipts remain UNVERIFIED; no receipt or worker result is automatically CURRENT, approved, published or eligible to replace institutional Saved Best.

Before implementation, the [baseline](testing/dashboard-u5k/preservation-baseline.json) captured 3,856 existing paths, including the Git index, all 23 academic data files, original GA/checkpoint sources, historical artifacts, protected local JSON modifications and unfinished research/UI work. [Entry review](testing/dashboard-u5k/entry-review.json) records eleven pre-existing tracked modifications and the prerequisite findings. The two protected JSON files were hashed, never printed or edited. No existing repository file was changed for U5K.

## Architecture and ownership

Four new service modules implement the versioned internal contract `ga-bounded-worker-v1`:

| File | Responsibility |
|---|---|
| `backend/services/ga_worker_contract.py` | Immutable limits, implementation digest, fictional-source gate and Windows Job isolation. |
| `backend/services/ga_worker_store.py` | New worker tables in a newly created owned fixture store; atomic checkpoint/lineage/best/lifecycle updates and capacity checks. |
| `backend/services/ga_worker_child.py` | One bounded JSON request; original U5H session initialization or exact continuation, generation-boundary pause and original result finalization. No database or persistence credentials. |
| `backend/services/ga_bounded_worker.py` | Trusted internal lifecycle interface, scoped authorization, parent-owned subprocesses, lease heartbeats, checkpoint validation, durable transitions and cleanup verification. |

Only an owned OS-temp source snapshot with empty fictional import tables can construct the worker. Actual prepared scheduling models arrive through U5J's separately guarded CaptureAdapter into a U5G bundle. Exact ScopedAuthority and CaptureAdapter types are required; a fake role-bearing client object or unguarded source does not establish execution authority. All fixtures use explicitly fictional mandates and verifier findings. This gate is a deliberate test-only execution restriction, not a sandbox against a hostile local Python administrator or arbitrary plugin.

The server generates run identity and initial RNG through unchanged U5I admission. The worker registers its immutable limits and implementation digest separately. Request idempotency binds the existing owner, department and catalog, then rejects a changed worker-limits digest. An unsuccessful worker registration can leave an inactive U5I admission in the new fixture store; it cannot start a K worker. No automatic deletion or reseeding hides such outcomes.

Each executing batch has one durable owner UUID, a monotonically increasing fence and a ten-second renewable lease. SQLite BEGIN IMMEDIATE serializes claims and checkpoint commits. A stale owner cannot renew, save a checkpoint or mark another owner's run failed. Every lifecycle/status/result/checkpoint operation checks owner and fresh scoped authority. Heartbeats and checkpoint commits revalidate the mandate under its guard, including revocation/expiry/policy changes. Source changes after admission do not replace the already pinned immutable bundle.

Named Windows Jobs additionally enforce the store-wide process count and one optimizer child per run across supervisors in the same Windows session. The child receives its request only after both jobs have accepted it. Parent death closes the owned job handles; the child is killed. Unsupported job policies fail closed. This is not qualified cross-session, multi-host or deployment-service coordination.

## Lifecycle and safe acknowledgements

The persisted lifecycle is:

`CREATED → RUNNING → PAUSING → PAUSED → RESUMING → RUNNING`

`STOPPING → STOPPED`, `COMPLETED` and `FAILED` are also persisted. A state/event record includes the current fence and checkpoint tip. Resume emits RESUMING and, after validated ownership/heartbeat, RUNNING. Existing I control mutation of a worker-owned run is rejected by the K base-ownership guard; it does not silently switch execution contracts.

- Start is legal only for CREATED; repeated start while a valid owner is active returns its current state without launching another supervisor.
- Pause and stop requests record intent. A running command returns PAUSING/STOPPING, never a premature PAUSED/STOPPED acknowledgement. The child finishes a validated generation boundary, exits, and is reaped before the corresponding checkpoint and lifecycle commit.
- PAUSED requires a durable checkpoint. Resume restores its exact population, best-ever state, history and private RNG, with unchanged total generations and configuration. Repeated pause on PAUSED is idempotent.
- Stop preserves the latest validated best projection. Stopping CREATED records no invented chromosome or fitness; stopping an already PAUSED run preserves its existing durable best. Repeated terminal stop returns the existing outcome. Terminal runs cannot resume.
- An expired owner requires an explicit authorized `recover=True` decision. No background restart or silent reinitialization occurs. Missing checkpoints fail recovery; corruption or mismatched lineage fails before launch.
- Failures retain the previous committed checkpoint and best projection. A failed new SQLite transaction rolls back all of its checkpoint/tip/history/lifecycle writes. Cleanup uncertainty is recorded and blocks further claims in the store when a failure can be durably recorded; it is never reported as successful cancellation.

## Resource contract

| Resource | Enforced isolated behavior / default |
|---|---|
| Generations per batch | 1; next target is bounded by the bundle's original horizon. |
| Total generations | Limit 4, configurable through 20; admission rejects a larger immutable bundle. Initialization generation 0 also checkpoints. |
| Population | Fictional fixture cap 8; no production default is changed. |
| Wall budget | 120 seconds, configurable through 600. Deadline begins at worker registration and includes time spent paused. Monotonic child deadlines and accumulated batch time supplement persisted wall time; clock rollback before admission time is rejected. |
| Checkpoint bytes | 8 MiB maximum canonical outer checkpoint, including encoded inner payload. |
| Retained checkpoints | 8. Exhaustion fails without deleting older checkpoints or silently dropping lineage. |
| Active optimizer children | 1 by default; explicitly configured fixture stores can use at most 2. SQLite admission fencing plus same-session Windows store/run Job limits. |
| Stored run bytes | 64 MiB logical serialized payload budget, plus bounded metadata accounting: 4 KiB per run and 1 KiB per event. Event encoding must fit its slot. Lifecycle, claim, heartbeat transition and checkpoint transactions check capacity; normal writes reserve a failure-event slot. Store-wide logical capacity is checked too. |
| Protocol | At most 64 MiB per request/response, further bounded by the run's configured byte budget. |
| CPU and private-memory quota modes | **UNAVAILABLE**. Any requested CPU/memory quota rejects execution. No thread-level RAM/CPU isolation claim. |
| Physical database/journal size | **Not a disk quota.** SQLite pages, journals, filesystem metadata, temporary source snapshots and dependency memory are outside the logical payload budget. Production storage remains unqualified. |

Native-compute timeout testing uses a real Windows `Sleep(60000)` child and a five-second worker budget. The supervisor closes the job, terminates/reaps only its owned process and verifies I/O thread cleanup. It does not claim that cancelling a Python thread stops native computation. Job attachment failure prevents input delivery and fails the run.

Parent-side checkpoint validation, process creation, filesystem and SQLite operations are not preemptible hard-real-time operations. Deadline checks reject late commits, but do not promise a total host-operation latency ceiling or bounded physical RSS. Unsupported OS/job isolation, CPU/RAM quotas and production storage modes remain unavailable. Production activation requires a separately qualified supervisor and resource policy.

Windows semantics were checked against [Microsoft's Job limit documentation](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information) and [nested Jobs contract](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs). The child invokes the base interpreter with the existing venv library path because the [CPython Windows venv launcher](https://github.com/python/cpython/blob/main/PC/venvlauncher.c) can create an additional process; the one-process Job limit was preserved rather than relaxed. No dependency was installed.

## Checkpoint and best-so-far contract

New `worker_meta`, `workers`, `worker_checkpoints` and `worker_events` tables exist only in newly created private disposable U5I fixture stores. No existing migrations, schema version or historical store is upgraded. The original I checkpoint table remains unchanged. New stores may be reopened only with their exact ownership marker and configured limits.

Each canonical outer checkpoint binds contract, the digest of all four K service files, run, owner, department, immutable bundle/configuration/optimizer fingerprints, limits digest, sequence, outer parent hash, inner parent/hash, fencing token, lifecycle state and completed generation. The embedded unchanged H checkpoint contains the complete population, best-ever chromosome/fitness, fitness history, private RNG and strict optimizer/input/runtime identities. All outer links and hashes are verified before H reconstruction; H validates the full inner graph and fingerprint contract. Cross-run reuse is rejected. Source-version drift blocks continuation rather than spoofing an old fingerprint.

The child reports an original-engine projection. The parent independently restores the inner checkpoint, performs stop-before-next-draw original finalization, and compares schedule, exact fitness, history, breakdown and faculty analysis. RNG equality is checked. Only then can the checkpoint, tip, best, lifecycle and event commit atomically. Lower penalties remain better; a worse best or regressing generation is rejected. A SHA-256 identifies the durable best projection; this is a worker-local identity, not a replacement institutional chromosome or approval identity.

Fresh-process acceptance reopens the actual owned SQLite store, validates its checkpoint, resumes a real optimizer child and reaches COMPLETED. A separate process-death test terminates an actual supervisor process and verifies its native child has exited through a Windows process handle. Stale-owner recovery/fencing is tested with an expired lease independently. These are separate complementary checks, not a claim of a production service crash/reboot certification or power-loss filesystem test.

## Validation and historical failures

Final results and exact command records are indexed in the [manifest](testing/dashboard-u5k/manifest.json). Source snapshot proofs record the six new service/test file hashes and proposed Git blob identities without staging. The final worker suite proof must match the delivered six source/test files; unchanged G–J regressions qualify committed baseline bytes. No fixture imports the checkout's institutional data.

| Fresh final selection | Passed |
|---|---:|
| U5K worker lifecycle/process/storage/parity | 32 |
| U5J scoped authority/capture/storage | 49 |
| U5I admission/ownership | 50 |
| U5H consumption | 39 |
| U5H original-engine parity | 5 |
| Legacy fixed checkpoint qualification | 10 |
| U5G immutable bundles | 32 |
| U5D receipts, including thread-observation isolation | 36 |
| U5E read-only analysis | 20 |
| U5F blocked readiness | 20 |
| U5A/U5B/U5C evaluation/context/source regressions | 99 |
| **Unique Python tests** | **392** |
| Frontend contracts | 210 |
| Edge intercepted-HTTP browser scenarios | 16 |

The Node browser runner counts 17 passing tests including its parent wrapper; that is **16 scenarios**, not 17 browser scenarios. TypeScript, production Vite build and focused ESLint pass against committed frontend source in an owned temporary snapshot. Unrelated working-tree UI changes were preserved and are not qualified by those snapshot checks. Six actual PNGs were individually viewed and privacy-reviewed; they show blocked Continuous Mode and existing fixed-mode behavior with fictional intercepted responses. They do not show a live FastAPI-to-worker journey, which is intentionally absent. No new HTTP or institutional PostgreSQL acceptance was executed.

The nonzero original fixed-engine versus process-batched case uses seed 710, two fictional offerings, population 2 and one generation, with subject preference penalty 91 in temporary fixture files. Both finish at **455.0**. Full schedules, fitness, history, breakdown, faculty analysis and final private RNG match exactly; caller-global RNG remains unchanged. Its history is `[455.0, 455.0]`: parity and non-regression are demonstrated, **not convergence improvement**. The zero-fitness case retains actual `0` rather than treating it as unavailable. These fixtures do not establish throughput or fairness performance at institutional scale.

All unsuccessful intermediate records remain intact:

1. Three early smoke attempts failed: first a truncated assertion diagnostic, then a child response failure caused by the Windows venv redirector under the strict Job limit, then an ownership check performed after deliberately releasing a terminal lease. The interpreter launch and terminal commit check were corrected in new K code; the former limit remained strict. Subsequent smoke passes are retained too.
2. The first full worker attempt recorded **26 passed / 4 failed**. Two test reopen paths omitted the original fixture's `max_runs=4`, correctly triggering the existing owned-store limit guard. Another test exposed the CREATED→resume transition diagnostic; K now explicitly rejects it. The nonzero oracle initially hit its own forbidden-persistence spy; the test now binds the unchanged original Saved Best function only to its isolated temporary oracle destination. No institutional Saved Best path was accessed.
3. Later full suites recorded 30 passes, then 31 passes after cross-supervisor Job-limit coverage, before the final metadata-capacity regression was added. These are historical passes, not additional unique tests.
4. The first frontend snapshot attempt recorded **193 passes / 1 failed module** because its required committed fictional DTO fixture was not copied. The new snapshot tool now includes that exact fixture. No application correction was needed; the full 210 contracts then passed.

Two dependency warning categories remain in HTTP-related regressions: Starlette's deprecated httpx TestClient integration and the anyio BlockingPortal alias. Their actual messages remain in the command records. No dependency changes or speculative warning attribution were made. The Vite build's existing bundle-size warning, if emitted, is a build advisory, not a test failure. Git integrity reports existing dangling objects without corrupt-object errors; no cleanup was performed.

## Reproduction and selective checkpoint

From the repository root in Windows PowerShell, with the existing venv and dependencies:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5k/checkpoint_snapshot.py worker
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5k/checkpoint_snapshot.py parity
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5k/checkpoint_snapshot.py legacy
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5k/checkpoint_snapshot.py qualification
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5k/checkpoint_snapshot.py admission
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5k/checkpoint_snapshot.py consumption
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5k/checkpoint_snapshot.py bundle-tests
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5k/checkpoint_snapshot.py receipts
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5k/checkpoint_snapshot.py analysis
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5k/checkpoint_snapshot.py readiness
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5k/checkpoint_snapshot.py backend-regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5k/frontend_snapshot.py
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5k/audit_evidence.py
```

Snapshot runners require the reviewed baseline HEAD and an empty Git index, reuse installed dependencies and create new uniquely named evidence directories. The backend runner reconstructs the unchanged U5C release-byte layout in an owned fictional snapshot, temporarily using the historical `main.py` required by that layout recipe, then restoring exact committed current `main.py` bytes before tests. It never replaces production engine fingerprints or stages anything. Test imports receive empty source tables; actual fictional models come from D10/J fixtures. No database URLs or approval flags are inherited. Worker stores and test outputs stay in owned temporary locations. Retained source snapshots, fixture databases and dependency junctions are not archived as acceptance evidence and were not recursively deleted.

The exact file inventory and two proposed selective groups are in [staging-plan.json](testing/dashboard-u5k/staging-plan.json). Group 1 contains four service modules and two test/support modules. Group 2 contains this report and the exact new K tooling/evidence paths. All are new; there are no mixed existing files to partially stage. Prerequisites G–J are already committed. A future checkpoint must recheck HEAD, index, hashes, privacy and the isolated source snapshot, then explicitly select only those paths under separate authorization. No staging, commit, fetch, push or deployment occurred here.

## Preservation and remaining blockers

The final audit verifies all 3,856 baseline file hashes, all 23 academic paths, original GA/fitness/RNG/workload/versioned engine sources, migrations, historical checkpoints, Saved Best, schedules, previous evidence, protected local JSON bytes and Git index. Eleven unrelated tracked modifications and all previous untracked work remain intact. No PostgreSQL connection, migration, authority activation or institutional data write occurred. The exact manifest excludes itself from artifact hashing to avoid a recursive hash claim.

**U5K is an isolated execution foundation, not institutional scheduling readiness.** Production still needs a genuine independently scoped optimization mandate/verifier, authoritative upstream prepared-input loader, approved deployment storage/backup/retention policy, physical disk and process memory/CPU safeguards, cross-session/service ownership qualification, monitored cleanup/recovery procedures and a separately authorized HTTP/UI integration milestone. Restoring a technical checkpoint proves technical continuity, not current institutional approval or valid publication authority.

Recommended U5L: qualify one controlled deployment-supervisor contract and its storage/resource limits, using fictional data first. Define explicit cleanup quarantine/recovery and source/authority lifecycle policies before considering any route or UI activation. Keep the original fixed APIs, U5D receipts, historical archives and institutional Saved Best unchanged. No institutional provider, workflow approval, unbounded worker or next-milestone implementation is included here.
