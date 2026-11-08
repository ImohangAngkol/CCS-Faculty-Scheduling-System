# U5L â€” Windows supervision, resource enforcement and recovery qualification

2026-11-08, Asia/Manila. Entry: `main`, `9c3cff0f7fd38c4e595e118db5b0aa4a11b31afa` (pushed U5K). **The isolated Windows supervision profile is implemented and verified. Production admission remains BLOCKED and Continuous Optimization UI remains DISABLED.** Deployment-wide resource safety, institutional storage and publication authority are not established. The existing intermittent U5D receipt path-guard failure recurred; its cause remains unconfirmed despite passing reruns. This is an explicit qualification limitation, not a repaired legacy defect.

## Preservation and prerequisite investigation

Inspected current HEAD, last-fetched origin/main, branch, index, U5Gâ€“U5K reports/contracts, original engine and checkpoint source coverage, I ownership/SQLite persistence, J independent mandate/capture/storage adapters, K batch process supervision and disabled readiness/UI contracts. Prerequisites are committed in G â†’ H â†’ I â†’ J â†’ K order. No AGENTS.md was found. All 74 K artifact hashes passed before implementation.

The [entry record](testing/dashboard-u5l/entry-review.json) and [pre-edit baseline](testing/dashboard-u5l/preservation-baseline.json) cover **3,931 existing paths**, including the index, all 23 academic files, protected local preferences/settings, original GA/scoring/RNG/version bridges, migrations, notebooks, retained checkpoints/schedules/Saved Best, previous evidence and unrelated unfinished work. Protected JSON was hashed without printing values. No existing file was changed, including all U5Gâ€“U5K implementations and evidence. No dependency installation, compiler installation, institutional/PostgreSQL connection, migration operation, Git staging, commit, push or deployment occurred. All new database operations used owned disposable SQLite fixtures.

## Implementation boundary

Three new modules provide a separately versioned internal fixture profile:

| New file | Responsibility |
|---|---|
| `backend/services/ga_windows_supervisor.py` | Explicit Win32 process/handle ownership, creation-time Job assignment, private committed-memory and process user-CPU-time limits, liveness/accounting and verified termination. |
| `backend/services/ga_supervised_storage.py` | Version-bound disposable storage adapter, SQLite page cap on each connection, free-space check, atomic physical-policy checkpoint pins, bounded metadata and read-only backup inspection. |
| `backend/services/ga_supervised_worker.py` | Extends K's internal Worker without replacing it: scoped lifecycle, durable process ledger, physical execution, authorized failed-run recovery and bounded shutdown. |

New tests are `backend/tests/test_windows_supervision.py` and `backend/tests/test_supervised_worker.py`. No route, main registration, frontend control, production provider or deployment configuration was added. The exact inventory, including tooling and every retained attempt, is in the [manifest](testing/dashboard-u5l/manifest.json) and [selective plan](testing/dashboard-u5l/staging-plan.json).

The worker still requires K's owned fictional source snapshot, J's actual ScopedAuthority/CaptureAdapter contracts, a server-generated I run/owner identity and a canonical G bundle consumed by H. Fictional test providers are never installed in normal application configuration. Administrator access is not optimization scope, Chair authority, publication permission or workload-exception approval. Original fixed endpoints, U5D UNVERIFIED receipts, CURRENT eligibility and institutional Saved Best behavior remain unchanged.

## Process topology and state machine

The trusted parent supervises one optimizer OS process per active run/batch, subject to the store cap. It starts the same K child and H optimizer, then validates the returned checkpoint/projection in the parent. Parent-side validation, SQLite and provider code are outside the child CPU/memory limits. A separate Windows service process or deployment daemon is **not** installed. This profile does not qualify whole-service RAM/CPU containment or a hostile-code sandbox.

`CreateProcessW` uses STARTUPINFOEX with an explicit inherited standard-handle list and a Job list. Store/run concurrency Jobs and a private resource Job exist before process creation; creation must attach them successfully. There is no runnable interval before Job assignment and no suspended-process assignment gap. Limits are queried back and compared before creation. Unknown/unsupported Job behavior rejects the mode. The child receives only whitelisted OS variables and the bounded canonical request, without database URLs, provider credentials or approval flags. The private Job handles are not inherited.

This uses Microsoft's documented [process-creation attributes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute), including the ordered Job list. No undocumented process-resume API, native compiler or new binding dependency was needed.

K's durable lifecycle remains:

`CREATED â†’ RUNNING â†’ PAUSING â†’ PAUSED â†’ RESUMING â†’ RUNNING`

Terminal states remain STOPPED, COMPLETED and FAILED; STOPPING is pending intent. Generation horizon, safe boundaries, original fitness comparisons, private RNG and best-ever preservation are unchanged. A validated checkpoint must commit after the physical child exits before PAUSED/STOPPED/COMPLETED is acknowledged. Forced termination is a failure, not a successful cooperative stop.

The `l_processes` ledger binds attempt, run, executor, fence, PID, creation FILETIME, heartbeat, exit/cleanup status and bounded accounting. PID alone never identifies a process for recovery, and recovery never kills a process by a stored PID. A read-only PID-plus-creation-time check rejects live old owners; access uncertainty fails closed. Only owned handles/private Jobs can be terminated. Same-session named store/run Jobs prevent duplicate optimizer execution even if a lease is stale. Cross-session/service-account coordination is not qualified.

Normal executions prohibit descendants through active-process limits. A separate two-process non-GA primitive probe verifies whole-owned-tree termination; it does not enable multi-process optimizer execution. Process-handle operations are synchronized to avoid shutdown/cleanup races. Closing waits for actual process exit and zero active Job processes, then closes owned pipes and handles. Accounting may briefly show an active process after its process handle signals; cleanup waits for the Job count rather than treating the first signal as complete.

## CPU and memory guarantees

| Boundary | Qualified behavior |
|---|---|
| Private committed memory | OS process commitment limit; default 768 MiB. Resource requests outside the supported fixture range reject. It is **not RSS/working-set measurement or a whole-host RAM ceiling**. |
| CPU user time | OS per-process user-mode execution threshold; default 60 seconds per batch process. It excludes kernel CPU, resets for each new batch and is not a total-run CPU budget. |
| CPU rate/utilization | Unqualified. Any non-None percentage rejects; no utilization cap is implied by CPU time. |
| Wall deadline | Inherited K finite registration-time deadline and monotonic child budget. Time while paused counts. Parent filesystem/provider/validation operations are not hard-real-time preemptible. |
| Graceful/forced shutdown | Fresh stop authorization is required before shutdown can terminate owned children. Cooperative stop is attempted, followed by owned Job termination when the bounded grace is exhausted. Failure never becomes STOPPED without a valid checkpoint. |
| Parent/supervisor resource usage | Not physically capped by this profile; deployment-wide mode remains unavailable. |

[Microsoft's limit contract](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information) specifies periodic CPU checks. The one-second native CPU probe terminated with exit code `3221225540` and **3.6875 seconds of measured user CPU** in the latest probe. This demonstrates OS enforcement with overshoot, not an exact one-second budget guarantee. Independent wall supervision remains necessary. The [extended memory limit](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information) constrains process commitment; exceeding it denies allocation and does not necessarily terminate a process that catches the failure.

The real memory probe used a 64 MiB commitment limit and rejected a 256 MiB bytearray with MemoryError. The busy-loop CPU probe was terminated by Windows. Actual parent death killed its owned native child, descendants were rejected in worker mode, and the separate allowed-tree probe reaped both processes. Six native OS cases and six invalid-configuration unit cases passed. These are real Windows 11 process tests, not mocked resource enforcement.

The final workflow suite contains **31 non-null ended-process observations**, each reporting zero active processes and a peak below its configured limit. The largest recorded private-commit peak was **705.69140625 MiB**, below the fixture's 768 MiB limit. These records include fault-injection children as well as actual optimizer children. The supervisor-crash child, whose parent could not write an exit observation, was separately checked dead before recovery. These small fictional fixtures are not a production capacity plan, memory optimization benchmark or guarantee for larger academic workloads.

## Durable storage and checkpoint ownership

Only a NEW private U5I `ga-u5i-*` OS-temp store can receive the additional L tables and policy marker. Existing databases or historical checkpoints are not upgraded. Reopening requires the unchanged I owner marker/limits, unchanged K contract, the L three-source implementation digest and exact physical/storage policy. Windows root DACLs are verified through J's existing inspection. Changing the physical policy rejects continuation rather than reinterpreting old checkpoints.

Every coordinator and K worker connection is routed through an explicit per-instance LimitedStore adapter. No production class/module global is replaced and no old fingerprint is spoofed. Connections enforce foreign keys, FULL synchronous behavior, DELETE journal mode and the configured SQLite main-database page cap. ATTACH and attempts to change the page cap/journal mode after setup are rejected. Default database cap is 64 MiB. [SQLite's max_page_count contract](https://www.sqlite.org/pragma.html#pragma_max_page_count) is a database-page boundary, **not a filesystem quota**.

The real quota test attempted a zeroblob larger than the remaining capped database space, received a SQLite failure and verified transaction rollback, unchanged old checkpoint/tip/best, database integrity and file size within the cap. This is actual SQLite quota exhaustion; it is not a full-volume or NTFS quota experiment. Another test set only a newly owned fixture database file read-only, verified write rejection and restored that temporary file's writable attribute. No protected file or existing ACL was altered. A separate injected zero-free-space observation rejects before writing. Free-space checks are not reservations and cannot prevent other processes consuming the volume.

K's run-payload, checkpoint-byte, checkpoint-count and generation limits remain active. L adds conservative charges for its run metadata, bounded process records and checkpoint pins; all normal transaction commits check the combined per-run/store accounting. Process attempts are capped at 64. The actual main-database page limit provides an additional shared database bound. Journal files, temporary libraries/snapshots and filesystem allocation overhead are outside that page cap. Requesting a filesystem-wide byte quota rejects; deployment storage is not qualified.

`l_runs` pins the L policy; `l_pins` binds each K checkpoint tip/sequence to it. These pins and the unchanged K checkpoint/best/lifecycle write commit in the same SQLite transaction. Inner H graph/optimizer/configuration/RNG validation and outer K ownership/bundle/lineage checks remain strict. A partial transaction cannot leave a new tip without its L pin. Reads/recovery reject mismatched pins, and changed resources or source versions fail closed.

Backups are limited to one private new fixture snapshot. SQLite's consistent backup API is followed by hash, owner/department/run/bundle/policy, tip/sequence/fence, read-only database integrity and outer checkpoint-chain inspection. Malformed manifest fields, tampering and stale snapshots reject. No backup data is exposed as a client download or archived in repository evidence. **Writable backup restoration is disabled**: restoring a database image safely needs an independent anti-rollback/ownership anchor and approved restore authority. Fresh-process continuation from the same validated retained store is implemented; it must not be confused with installing an old database backup.

Checkpoint retention exhaustion fails without deleting lineage. The retention interface checks owner, exact tip/fence and inactive terminal state, but returns cleanup disabled. There is no independently established deletion authority, so it never deletes checkpoint/history rows or files. Repeated backups do not rotate or erase the first image. Stable deployment roots, service identities, physical volume/journal/backup quotas and retention deletion remain blocked.

## Failure, recovery and GA parity

Recovery is explicit and scoped, never automatic. A failed or interrupted run requires its expected tip/fence, a validated K/H checkpoint, exact L policy, proof old process identities are dead and fresh resume authorization. The recovery transaction fences the previous owner and records a PAUSED recovery decision before normal continuation claims a newer fence. It does not reset the original horizon, RNG, target fitness, wall budget or immutable bundle. Missing checkpoint, stale decision, live old owner, policy drift or corruption rejects. COMPLETED/STOPPED runs cannot be silently restarted.

Acceptance covers a real supervisor process exiting without cleanup while its native child is active and its process identity is durably recorded. The child dies through non-inherited Job ownership. Heartbeat expires; a fresh Worker in the retained store verifies the old child is dead, validates the checkpoint and resumes only after an explicit recovery decision. Other tests forcibly terminate a blocked owned child, preserve its prior best/checkpoint, reject stale recovery arguments and recover successfully. A two-generation resumed run matches uninterrupted schedule, fitness/history/breakdown/faculty analysis and final private RNG exactly.

The nonzero original fixed-GA comparison still produces **455.0** in both paths, with identical assignments, scores, histories, breakdowns, faculty analysis and RNG; caller-global RNG is unchanged. Zero fitness remains a real value. The history staying at 455.0 establishes parity and best-so-far preservation, not new convergence. No academic policy, fitness mathematics, selection, crossover, mutation, workload, chromosome encoding or existing checkpoint compatibility policy changed.

## Results and retained unsuccessful attempts

| Latest selected suite | Passed |
|---|---:|
| U5L supervised fixture workflows, unit validation and fault injection | 41 |
| U5L native process probes / invalid-policy units | 12 |
| Unchanged U5K worker | 32 |
| U5J authority/capture/storage | 49 |
| U5I admission/ownership | 50 |
| U5H consumption | 39 |
| U5H parity | 5 |
| Fixed legacy checkpoint regression | 10 |
| U5G bundle tests | 32 |
| U5D receipt suite, latest rerun | 36 |
| U5E analysis | 20 |
| U5F blocked readiness | 20 |
| U5A/U5B/U5C read-only regressions | 99 |
| **Latest selected Python cases** | **445** |
| Frontend contracts | 210 |
| Actual Edge / intercepted fictional HTTP scenarios | 16 |

The browser runner reports 17 passing tests including its parent wrapper, not 17 scenarios. TypeScript, Vite production build and focused ESLint pass in a committed-source temporary frontend snapshot. Six real PNGs were viewed individually and checked for privacy and embedded metadata. The screenshots verify the unchanged blocked Continuous UI and original fixed-mode behavior under fictional HTTP interception. There is no live browser â†’ L worker endpoint and no institutional/PostgreSQL acceptance. Unrelated working-tree UI work was preserved and is not qualified by snapshot checks.

Some K assertions are deliberately reused with the L fixture; the table counts distinct execution-path cases, not 445 independent algorithms. Native invalid-policy tests are unit checks; quota/termination probes use actual OS processes. Heartbeat/parent interruption, real process death, real SQLite FULL/read-only failures and injected transaction faults are distinguished in test names and records.

Preserved attempts include:

1. Initial integrated smoke: one failure before optimizer input because the new ledger INSERT had ten placeholders for nine columns. Corrected in new L source; smoke subsequently passed.
2. First broad L suite: 36 passed, one failed backup inspection. It used base I admission checkpoint fields instead of K worker tip/sequence. The new adapter now reads the authorized worker row. A later 39-case suite passed; then strict backup-manifest binding tests were added and the final 41-case suite passed. Earlier evidence was not rewritten.
3. A U5D regression run: 35 passed, one failed `test_distinct_thread_observations_are_isolated_not_a_concurrent_engine_claim`, with HistoryError from the original receipt directory/symlink/resolve guard before start-record creation. This matches the previously documented class of intermittent U5H/I/J failure. Two isolated reruns and the later full 36-case suite passed. **The exact race/root cause is still unconfirmed; no U5D correction or relaxed guard is claimed.** Passing reruns do not erase this failure or establish that production receipt concurrency is reliable.

The two existing Starlette/httpx and anyio BlockingPortal deprecations remain recorded where emitted. Existing build chunk/dynamic-import advisories remain. No dependency changes were made. Git integrity reports dangling objects without corruption and no cleanup was performed.

## Reproduction and checkpoint plan

Use the existing venv/dependencies from the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5l/checkpoint_snapshot.py native
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5l/checkpoint_snapshot.py supervised
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5l/checkpoint_snapshot.py backup
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5l/checkpoint_snapshot.py worker
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5l/checkpoint_snapshot.py parity
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5l/checkpoint_snapshot.py legacy
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5l/checkpoint_snapshot.py consumption
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5l/checkpoint_snapshot.py bundle-tests
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5l/checkpoint_snapshot.py admission
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5l/checkpoint_snapshot.py qualification
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5l/checkpoint_snapshot.py backend-regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5l/checkpoint_snapshot.py receipt-isolation
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5l/checkpoint_snapshot.py receipts
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5l/checkpoint_snapshot.py analysis
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5l/checkpoint_snapshot.py readiness
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5l/frontend_snapshot.py
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5l/audit_evidence.py
```

Each execution creates new evidence; it never overwrites prior attempts. Backend tests use the unchanged release-byte snapshot preparation, restore committed current main before execution, copy the five new L implementation/test files and use empty fictional import tables. Protected/academic data and runtime stores are excluded from source archives. No original source fingerprint is replaced. New stores/backups/checkpoints stay private in OS-temp and are not copied into evidence. Native probes use standard-library Win32 bindings only. The [environment record](testing/dashboard-u5l/environment.json) identifies Windows 11 build 26200, 64-bit Python 3.14.2 and no dependency installation.

The [audit](testing/dashboard-u5l/audit_evidence.py) verifies all 3,931 baseline paths, 305 prior Gâ€“K artifact references, exact new-file inventory, final suite proof/source hashes, recorded process cleanup/commitment bounds, six PNGs, privacy patterns, whitespace and Git integrity. The manifest excludes itself from artifact hashing. No raw database, protocol, bundle, checkpoint, signed receipt, cookie, credential or actual academic row is archived. Technical process IDs/creation times and fictional run UUIDs are not authentication secrets or institutional identities.

The [selective staging plan](testing/dashboard-u5l/staging-plan.json) contains three new service modules, two new test modules and the exact new report/tool/evidence paths. There are no mixed existing files to stage. It is a proposal only; any later Git checkpoint requires separate authorization, a fresh HEAD/remote/index check, exact byte-preserving staging and acknowledgement of the retained legacy receipt regression limitation. Nothing was staged, committed, pushed or deployed.

## Readiness and U5M recommendation

**Isolated Windows child supervision, supported resource limits and same-store checkpoint recovery are qualified. Overall institutional deployment readiness is NOT established.** The legacy receipt concurrency recurrence prevents an unqualified all-regressions-reliable signoff. The latest suites pass, but checkpoint review must retain that limitation explicitly.

U5M should first qualify an approved deployment/service identity and storage/restore/retention policy, independently anchored restore freshness and cross-session ownership. Decide how to contain trusted parent validation/provider/SQLite resource use, enforce actual volume/journal/backup quotas, and investigate the receipt path guard without weakening it. Continue fictional service-restart, disk-pressure and recovery tests before considering any HTTP/UI activation. Genuine scoped optimization, academic source and institutional approval/publication providers remain absent and BLOCKED. No U5M implementation is included.
