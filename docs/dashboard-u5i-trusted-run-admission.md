# U5I — trusted server admission and durable checkpoint ownership

2026-11-05, Asia/Manila. Base `main`: `d6db077793da52b7559351a5d0f8e6d54608cb77`.

**The isolated foundation is implemented and independently verified. Production admission remains BLOCKED.** A separate synchronous, finite U5H execution path now has server-generated run identities, independently scoped optimization grants, immutable captured inputs, idempotent admission, persistent ownership fencing and atomic SQLite checkpoint/tip persistence. No continuous worker, institutional provider, deployment storage, CURRENT promotion or publication is activated.

## Interrupted work and preservation

The resumed work contained three new services (`ga_owned_store.py`, `ga_run_authority.py`, `ga_trusted_runs.py`) and a fourth new implementation file, `routers/ga_trusted_runs.py`. There were also two new registration lines in the already mixed `backend/main.py`. Thus the complete application integration spans **four new files and one existing mixed file**. The partial implementation was reviewed rather than assumed complete.

The pre-U5I preservation baseline covers 3,730 paths, including all 23 academic files, both already-modified protected JSON files, GA sources, scoring/RNG/operators, migrations, Saved Best, retained checkpoints/schedules, historical evidence and the Git index. The final audit requires 3,729 paths to remain byte-identical and verifies that removing only the two U5I registration lines from main reproduces its exact archived entry bytes, including mixed line endings. No protected content is printed, restored or staged.

U5D–U5H are still uncommitted prerequisites. Their recorded inventories are 24, 268, 80, 34 and 77 paths respectively. U5G must precede U5H; U5I depends on both. All 76 prior U5H artifact hashes are rechecked. Existing unrelated U4/Live Center/research work is preserved. Nothing is staged, committed, pushed or deployed.

## Admission and independent authority

| Boundary | Implemented contract |
|---|---|
| Principal | The route uses the existing authenticated session through `require_principal`. Actor identity is the server-side account UUID. Client role, faculty ID, run ID, config, bundle and grant fields are not accepted as admission authority. |
| Scope | A requested department UUID is only a selector. Both the independent grant and trusted capture provider must establish that exact actor/department/catalog scope. |
| Capability | `department_optimization_control`, explicitly separate from account Administrator access and the existing Chair review/decision mandate. No Administrator-to-Chair inference. |
| Grant | Exact context digest binds actor, department, action, run/bundle/config identities when established, and catalog reference. Policy digest, issuance, expiry and a maximum 300-second grant window are checked. Invalid or unavailable authority fails closed. |
| Provider coherence | An independent trusted provider must implement a lifecycle guard and fresh authorization checks. The guard must prevent incoherent policy/revocation changes across commit. Provider acquisition failures are sanitized. No such institutional provider is installed. |
| Input capture | A server-owned capture provider must guard its source, create the immutable U5G bundle for the newly generated run UUID and return an exact typed scope/catalog binding. U5H validates the bundle, loaded dependency version, configuration and model graph before admission commits. |
| Idempotency | Canonical request UUID unique within actor/department, plus a request-content digest. Same authorized request returns the existing run without capture or RNG recreation. Reusing a key with different catalog content rejects. SQLite `BEGIN IMMEDIATE` serializes concurrent admission. |
| Identity/version | Server UUID, server-created initial private RNG state, immutable bundle bytes/hash, config hash, U5H optimizer identity and separate U5I persistence-release fingerprint are committed together. |

`Context`, `Grant` and `Capture` are internal server interfaces, not public proof formats. No HTTP body can install a provider, submit a grant or inject a bundle. Tests use an explicitly named FICTIONAL issuer/catalog. A trusted Python provider is part of the server trust boundary, not a sandbox for hostile plugins.

Run ownership requires **both** the exact owning account and a current grant for the stored department and requested operation. Another Administrator receives 404 for the owner's run; a known owner without the required current scoped grant is denied. There is no delegation/transfer or global administrator inspection override in this release.

## Versioned HTTP boundary

New prefix: `/api/ga/bound-runs`. Existing fixed-generation, stream, V2 and history endpoints are unchanged and never redirected here.

| Method/path | Behavior |
|---|---|
| GET `/capabilities` | Authenticated, read-only; explicitly reports unavailable production issuer/storage and no continuous worker. |
| POST prefix | Admit `{department_id, request_id, catalog_reference}` only; unknown fields reject. Requires trusted capture/store/authority dependencies. |
| GET `/{run_id}` | Authorized owner status; expired active leases project INTERRUPTED rather than successful completion. |
| POST `/{run_id}/execute` or `/resume` | Synchronous finite execution. Resume uses only the stored bundle and trusted checkpoint tip; there is no checkpoint upload or client-supplied recovery pin. Control bodies are rejected. |
| POST `/{run_id}/pause` or `/stop` | Authorized cooperative request; active requests are distinguished from completed acknowledgements. Idle stop fences the old executor. |
| GET `/{run_id}/checkpoint` | Authorized owner, full chain/hash/binding and U5H restore preflight, raw versioned checkpoint bytes; no-store. |
| GET `/{run_id}/result` | Authorized owner, checksum-verified run-local proposal. Never updates historical Saved Best. |

All new route responses request no-store caching. Real session verification still enforces Origin and CSRF for unsafe operations. Tests exercise the actual session lookup and CSRF/Origin code against a separately created fictional identity SQLite database; most other route tests explicitly inject fictional principals. An owned Uvicorn loopback test verifies real HTTP transport with the real session dependency. No production database or real account is used.

`configured_service()` returns `None`. In normal application operation, authenticated requests to execution/storage endpoints return `GA_TRUSTED_RUNS_UNAVAILABLE` (503). There is no environment bypass, demo activation switch, installed fictional issuer or production-created directory. The readiness response intentionally describes this deployed default rather than pretending that test injection activates production.

## Durable storage, schema and recovery

Store contract: `ga-owned-sqlite-store-v1`, SQLite user_version 1. Only a **newly owned `ga-u5i-*` directory directly under OS-temp** can be created. Reopening requires the exact owner marker/store UUID, namespace and recorded retention limits. Symlink/junction targets, missing files and unsupported schema versions reject. SQLite opens in `mode=rw`, so missing storage is not silently recreated.

Windows setup modifies only the new directory's DACL: inheritance protected, access limited to the current user, SYSTEM and Administrators; the actual rules are verified. It does not change ownership, SACLs or cluster settings. The security module is loaded from the installed Windows PowerShell's own module path. ACL child processes receive a whitelist of OS variables, without database URLs or application approval settings. POSIX uses mode 0700; POSIX operation was not separately exercised here.

| Table/field group | Binding |
|---|---|
| `runs` immutable admission | UUID, owning actor/department, request key/digest, catalog/policy digest, creation/expiry, bundle bytes/hash, config/optimizer/persistence identities, initial RNG state. |
| `runs` lifecycle | State/desired command, executor UUID, increasing fence, lease expiry, trusted tip/sequence/parent, result bytes/hash, last technical consumption receipt and neutral error code. |
| `checkpoints` | Run FK, monotone sequence, checksum, parent checksum and exact U5H envelope bytes. Unique per-run sequence and global checksum. All prior checkpoint rows remain retained. |

U5H checkpoint bytes already bind run, bundle, optimizer version/identity, config, scoring graph, RNG, population/best-ever and lineage. U5I additionally pins their trusted tip in the private database, with owner/scope and its independently versioned persistence release. Raw downloaded bytes cannot authorize restoration. No endpoint accepts them back as authority, and no historical fixed-engine checkpoint is migrated or reinterpreted.

Each append verifies the executor/fence/unexpired lease, exact next sequence and parent, hash and limits. Checkpoint bytes and the trusted tip update commit in **one SQLite transaction**, before the wrapped U5H checkpoint callback acknowledges pause. `synchronous=FULL`, closed handles and SQLite transaction recovery provide local durability. The subprocess acceptance deliberately exits inside an uncommitted checkpoint/tip transaction and verifies that reopening preserves the previous committed pair. This demonstrates process-abort recovery, not arbitrary hardware, network-filesystem or power-loss certification.

The schema retains checkpoints in run-specific logical namespaces within one private database; there are no application-store paths or client-selectable filenames. SHA-256 detects corrupted bytes and broken lineage. It does not defend against an administrator/OS owner maliciously rewriting the private database and all associated checksums; OS access control and trusted server code are the root of trust. This is not cryptographic remote attestation.

Execution claims are serialized and fenced. A second active executor is refused. The lease is renewed at existing validated generation boundaries, not by a background heartbeat. If a generation takes longer than 120 seconds, the next boundary fails closed rather than claiming continued ownership. Explicit authorized resume after lease expiry restores only the trusted tip. An interrupted run without a checkpoint cannot be automatically reconstructed or restarted under the same identity. There is no automatic recovery worker.

Fresh restore validates the entire chain and U5H state before claiming, then compares the expected tip/sequence during claim. A newer tip or owner fence wins. Old executors cannot write a checkpoint or result. Failures mark only the still-owned claim INTERRUPTED; cleanup failure adds a neutral note without replacing the primary exception. Current scoped authority/policy is checked before commit. A Stop arriving during checkpoint serialization is preserved and cannot be overwritten by a pause acknowledgement.

Retention defaults: seven-day accessibility, at most 64 runs, 16 checkpoints per run and 256 MiB logical payload budget. Limits must be positive integers and match the store marker on reopen. Expiry blocks access; capacity blocks writes. No automatic deletion, pruning, migration, archival or cleanup of retained records is installed. Payload quotas are conservative logical budgets, not a certified physical database/journal/process-memory bound. Production retention, backup, disk quotas and operator disposal policy remain separate work.

Changed external source data does not silently replace an admitted immutable bundle. Resume deliberately uses the frozen snapshot. Config/bundle/optimizer/persistence mismatches reject before an execution claim. Grant revocation or policy change rejects further operations. Determining whether an external institutional update invalidates a pinned catalog requires the still-missing trusted provider policy; continuing a technical snapshot is not evidence that it is the latest authoritative institutional source.

## U5H integration and legacy preservation

The coordinator subclasses only the new U5H Session checkpoint callback; original operations and runtime modules remain byte-identical. The wrapped callback first performs U5H encode/decode and hard-state validation, then commits bytes and lineage in the isolated store. Final results and receipts go to that same run row only. Existing scorer, initialization, selection, crossover, mutation, hard constraints, termination, best-ever behavior and private RNG operations remain unchanged.

U5I never calls the legacy GA publication, Saved Best or checkpoint-writing sinks. Differential tests compare exact schedules, fitness including zero, complete histories, breakdowns, faculty analyses and checkpoint RNG continuity. U5H original-engine parity is rerun independently. The separate U5I persistence fingerprint includes the coordinator, authority and store source; changed orchestration cannot masquerade as a compatible persisted release. U5H and legacy fingerprint checks are not disabled, spoofed or rewritten.

Technical U5H receipts can become VERIFIED only after that exact optimizer path reaches a validated boundary. They remain ineligible for CURRENT, with institutional authorization NOT_ESTABLISHED and academic source verification UNVERIFIED. Existing U5D HTTP observations remain UNVERIFIED. No receipt is promoted because a durable row exists.

## Fresh verification and retained unsuccessful evidence

All backend selections run in newly created **source-only snapshots with fictional import tables** and existing installed dependencies. The archive excludes academic/runtime stores before creation. The committed U5C-R1 release-byte fixture recreates unchanged source line endings; real engine fingerprint verification still runs. U5I's minimal proposed snapshot contains HEAD plus U5G/U5H and U5I sources and a HEAD-only two-line main integration, without U5D/U5E/U5F application dependency. Compatibility selections separately overlay their preserved existing work.

| Selection | Fresh final result |
|---|---|
| U5I admission, ownership, persistence, recovery and HTTP | **50 passed** |
| U5H consumption, actual optimizer and checkpoint guards | **39 passed** |
| U5H exact original-engine and fresh-process/RNG parity | **5 passed** |
| U5G original fixed-engine continuation/qualification | **10 passed** |
| U5G immutable bundle regressions | **32 passed** |
| U5D receipt regressions | **36 passed** |
| U5E analysis regressions | **20 passed** |
| U5F readiness regressions | **20 passed** |
| U5A–U5C provenance/compatibility/source qualification | **99 passed** |
| Unique Python cases in the above selections | **311 passed** |
| Additional isolated repeat of the existing U5D concurrency case | **1 passed**, already counted among the 36 unique cases |
| Frontend contracts | **210 passed** |
| Actual Edge UI regression | **16 scenarios passed**; Node reports 17 tests including the wrapper |
| TypeScript, production bundle and focused ESLint | **PASS** |
| Git fsck, whitespace, hashes, privacy and preservation | **PASS**, details in the manifest |

The 50 U5I cases include duplicate and concurrent admission, invalid scoped grants, cross-owner/scope access, real session/CSRF/Origin checks, owned loopback HTTP, exact continuation parity, actual fresh-process recovery, forced process exit during a transaction, old-executor fencing, changed source snapshots, stale bindings, missing/corrupted/cross-run checkpoints, revocation, commit-time denial/rollback, stop races, missing storage, schema and retention limits. A successful test proves the stated isolated path, not institutional acceptance.

Historical attempts are retained intact:

- Initial snapshot creation was blocked by the sandbox's redirected OS-temp permissions before pytest; recorded in `attempt-notes.json`.
- First admission suite: **37 setup errors**, no assertions executed, because the Windows security module did not autoload. Second: **37 setup errors** after explicit module loading exposed a `SeSecurityPrivilege` request from Set-Acl. Both failed closed before creating the store. DACL-only setup resolved those two observed causes; privileges were not broadened.
- An earlier complete suite passed **37** cases; an expanded suite passed **45**. They are supporting history, not additional unique final passes. The final 50-case run qualifies the final implementation source hashes.
- Review before test execution corrected the partial schema/INSERT mismatch, checked authority again before committing claim/checkpoint/result, and ensured a pending Stop cannot be discarded by checkpoint completion. Primary execution failures and cleanup notes remain separate.

The two observed dependency warnings are Starlette's deprecated httpx TestClient integration and anyio's deprecated BlockingPortal alias. No dependency was installed to remove warnings. Production build retains existing dynamic-import and chunk-size warnings. Git fsck exited zero and reported existing dangling objects; no cleanup was performed.

### U5D concurrency investigation

The U5H record of the intermittent U5D path-guard failure remains unchanged. U5I inspected the actual guard (`target.resolve().parent != RECEIPTS_DIR.resolve()`), reran the complete 36-case suite and the isolated concurrency case, and independently tested 500 concurrent pre-directory-creation path comparisons. All fresh tests passed; the probe found zero mismatches. **Root cause remains UNCONFIRMED; no fix is claimed or made to U5D.** The independent path probe is not a full observer/engine reproduction. Continue retaining and investigating any recurrence rather than relaxing the guard.

### Browser scope

Edge `156.0.4314.50`, Node `24.11.1`; the existing U5F UI suite uses intercepted fictional HTTP responses. Six genuine PNGs were visually reviewed, hashed and checked for metadata/CRC integrity. They contain no private faculty records, credentials or real account sessions. They establish unchanged blocked-continuous/fixed-control presentation, not live U5I execution. U5I adds backend APIs, not a new frontend. Backend transport/session/SQLite acceptance is independently labeled and does not claim browser-to-live-GA or PostgreSQL acceptance.

## Files and selective checkpoint plan

Application scope:

- New `backend/services/ga_run_authority.py` — independent scoped grant contract.
- New `backend/services/ga_owned_store.py` — owned temporary SQLite store and atomic checkpoint ownership.
- New `backend/services/ga_trusted_runs.py` — admission, state/commands, bounded execution and recovery coordinator.
- New `backend/routers/ga_trusted_runs.py` — separate authenticated versioned API, default unavailable.
- Existing mixed `backend/main.py` — only one import and one include-router line attributable to U5I.

New tests: `backend/tests/test_trusted_runs.py` and `backend/tests/trusted_run_support.py`. New report and tooling/evidence are under this report path and `docs/testing/dashboard-u5i/`, including baseline, entry main, command records, snapshot proofs, parity artifacts, path-probe findings, screenshot review, audit, manifest and staging plan. The manifest's `exact_changed_and_new_file_inventory` is the exhaustive inventory; no other application file is part of this milestone.

**Checkpoint readiness: ready for review of the isolated foundation, conditional on prerequisite ordering and selective staging.** Nothing has been staged. Commit/review U5G before U5H before U5I, preserving the prior milestone inventories. Select the six new U5I implementation/test paths explicitly. For main, select only the two U5I lines; never stage the entire mixed file containing earlier U5E/U5F work. The staging plan includes the exact HEAD-only reference patch/blob and every documentation path. Requalify that patch after prerequisite commits. Historical failed evidence remains included. Protected JSON files and unrelated work are excluded.

## Reproduction

From the repository root in PowerShell, using existing installed dependencies:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5i/checkpoint_snapshot.py admission
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5i/checkpoint_snapshot.py consumption
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5i/checkpoint_snapshot.py parity
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5i/checkpoint_snapshot.py legacy
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5i/checkpoint_snapshot.py bundle-tests
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5i/checkpoint_snapshot.py receipts
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5i/checkpoint_snapshot.py receipt-isolation
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5i/checkpoint_snapshot.py analysis
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5i/checkpoint_snapshot.py readiness
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5i/checkpoint_snapshot.py backend-regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5i/investigate_receipt_race.py
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5i/run_checks.py frontend
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5i/run_checks.py build
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5i/run_checks.py bundle
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5i/run_checks.py lint
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5i/run_checks.py browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5i/audit_evidence.py
```

Each test command creates a new evidence directory; it never overwrites earlier records. Snapshot and fixture creation require ordinary user OS-temp permissions, Windows DACL access to newly owned directories and owned browser/child-process execution. These are not database privilege requests. Evidence holds no database files, bundle payloads, raw checkpoints, bearer/session tokens or provider secrets. Do not copy retained fixture databases into evidence. Audit replay is non-writing; creating a new manifest uses a separate explicit `--record` mode that refuses overwrite.

## Remaining blockers and next milestone

No live PostgreSQL operation or migration was executed. Prior D15 acceptance is historical and untouched; it does not certify this new SQLite storage contract. Institutional academic catalogs, roster/term qualification, optimization mandate issuer, zero-target authority and publication restrictions are not solved by technical input consumption.

Next: qualify a real scoped optimization authority/capture contract and an approved deployment storage/retention/backup policy. Specify resource budgets, cancellation latency and supervisor ownership before proposing a bounded continuous worker. Do not activate continuous execution, add a worker, promote CURRENT/Saved Best or infer publication authority from this milestone. Any production integration needs its own approval and independently isolated acceptance.
