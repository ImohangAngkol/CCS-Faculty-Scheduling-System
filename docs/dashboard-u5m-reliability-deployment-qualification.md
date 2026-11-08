# U5M: concurrency reliability and deployment qualification

2026-11-09, Asia/Manila. Entry: `main`, `b4c8da7942bddfec63564a1e1f8de31e1db3e491` (committed U5L). **The recurring receipt guard defect is reproduced, explained and repaired. Isolated qualification passes; production admission remains BLOCKED and continuous execution UI remains DISABLED.** No deployment, institutional approval or new continuous HTTP execution path is established.

## Preservation and prerequisites

Inspected U5D through U5L reports, original receipt observer and persistence, immutable capture/materialization, H optimizer/checkpoint binding, I ownership, J scoped authority/capture adapters, K worker, L Windows/process/storage contracts, existing authentication, Chair/application authority and the development launcher. The committed prerequisite sequence is G before H, then I/J/K/L. The [prerequisite record](testing/dashboard-u5m/prerequisite-review.json) retains each report's original scope, including earlier partial implementation and blocked deployment claims. No AGENTS.md was found.

The [entry record](testing/dashboard-u5m/entry-review.json) verifies 11 pre-existing tracked modifications and 958 unrelated untracked files. The pre-edit [baseline](testing/dashboard-u5m/preservation-baseline.json) covers 4,139 paths, including the index, all 23 academic data files, protected local preferences/settings, original GA/scoring/RNG and version bridges, migrations, notebooks, checkpoints, Saved Best, schedules, historical evidence and unfinished work. **4,138 baseline paths remain byte-identical; only `backend/services/ga_input_receipt.py` intentionally changes.** Its two modified functions are `directory` and `write`; every other receipt AST node remains unchanged. All 33 original engine fingerprint source inputs remain unchanged; the receipt observer is outside that source coverage. No fingerprint is spoofed or disabled. See [repair scope](testing/dashboard-u5m/repair-scope-review.json).

No protected JSON values, academic rows, credentials, cookies or signed receipts are printed or archived. No PostgreSQL operation, institutional database connection, dependency installation, staging, commit, push or deployment occurred. New database tests use newly owned disposable SQLite. No existing database, D15 acceptance state, runtime store or historical receipt was opened for mutation. The eleven pre-existing modifications and 958 unrelated untracked files are excluded from the proposed checkpoint.

## Receipt race: observations and cause

The historical failure is `test_distinct_thread_observations_are_isolated_not_a_concurrent_engine_claim`, recorded in U5L's `20261108T105011696880+0800-snapshot/receipts-command.json` (35 passed, one failed). Two independent ContextVar-backed observers should each write immutable start/progress/finish records under distinct server UUIDs. This test does not run two full GA engines. The rejection occurs inside `directory`, before start-record publication; no shared mutable fitness defect was demonstrated.

The original guard compares `target.resolve().parent` and `RECEIPTS_DIR.resolve()` as lexical WindowsPath values while writer directories are being created. Instrumentation of the actual original guard reproduced **54 false rejections in 6,000 checks**, seed 17501. Captured reparse checks were false, while one parent resolved to a normal DOS path and the root to its equivalent extended-namespace spelling (`C:\...` versus `\\?\C:\...`). Lexical inequality incorrectly rejected the same directory. Subsequent observations after creation resolved consistently. This is a production receipt helper filesystem-observation defect exposed by concurrent directory construction, not merely a timeout or a suppressed flaky assertion.

The installed CPython 3.14.2 `ntpath.realpath` implementation has non-strict resolution/fallback paths that can retain an extended prefix. [CPython source](https://github.com/python/cpython/blob/v3.14.2/Lib/ntpath.py) and [Windows path naming documentation](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file) explain why both spellings can identify one object. The exact internal Win32 error sequence was not instrumented and remains an explanation inferred from implementation, rather than a directly measured trace.

A deterministic regression uses an actual regular Windows directory and proves `samefile` for its two spellings, then replays the captured `Path.resolve` return pair. The exact original `directory` function is extracted from the trusted Git source (SHA-256 `2b418773be9ba119ff39fc87157e28d364462d139eb46b4c12f4a99f18fb5c5e`) into the owned test snapshot. It rejects; the repaired function accepts. This is a deterministic return-value replay with real filesystem identity, not a claim to force the OS race deterministically.

### Repair and failed attempts

The minimal final change:

1. Capture one receipt root value. Continue rejecting root/target symlinks and junctions.
2. When resolved parent/root spellings differ, require actual filesystem identity via `samefile`. Missing/inaccessible/different identities fail closed; no arbitrary prefix stripping is used. Recheck reparse flags after resolution.
3. In the writer, validate the canonical UUID first, then synchronously create the intended root before checking its physical identity. Check the returned parent against the captured root before creating the run directory. Reads do not create a missing store.
4. Keep canonical envelopes, size limits, exclusive hard-link publication, fsync, immutable winner semantics and V1 validation unchanged. No global serialization or retry loop is added.

An initial identity-fallback-only repair was insufficient: **3/6,000 checks still failed**, all in the missing-root group. The final writer initialization order addresses that second observation. The initial trace did not record the specific low-level exception for those three cases; it must not be reported as a proven particular Win32 error.

| New evidence directory | Recorded outcome |
|---|---|
| `20261109T002246911259+0800-snapshot` | Original guard stress: one failing diagnostic, 54/6,000 false rejections. First ten failure traces retained; no full per-group aggregate was recorded. |
| `20261109T002717548994+0800-snapshot` | Before repair: one characterization passed, desired behavior failed, one deselected. |
| `20261109T002921265545+0800-snapshot` | Incomplete first repair: ten passed, one failed; 3/6,000 guard failures. |
| `20261109T003404904734+0800-snapshot` | Final repair's first suite: 15 passed, 6,000 writer checks without rejection. |
| `20261109T003947046169+0800-snapshot` | Expanded final suite: 19 passed, 6,000 writer checks without rejection, 200 complete observers. |

All unsuccessful command records, traces and snapshot proofs remain intact. The historical U5L unresolved finding remains unchanged as a statement about that earlier milestone. U5M supplies later evidence and a repair rather than rewriting it.

Final coverage includes existing versus initially absent roots, genuine Windows junctions, simulated symlinks/reparse changes, outside-parent resolution, inaccessible/missing identity, invalid UUIDs, non-writing missing reads, one immutable winner under same-run write contention and historical observer source identity remaining readable/UNVERIFIED. Stress checks are bounded evidence, not proof of every filesystem interleaving or a hostile local filesystem attacker security boundary. Existing private-directory ownership remains necessary.

**U5D receipts remain `ga-run-input-observation-v1`, UNVERIFIED and ineligible for CURRENT.** Fixing record reliability does not prove optimizer consumption, genuine academic identity, authority, approval or eligibility for Saved Best.

## Identity, scope and approval qualification

The application resolves opaque session cookies through a hashed LoginSession record and current active User. Server-side account role and verified faculty binding override client claims. The 16 new actual FastAPI ASGI/SQLite tests exercise forged headers/query/cookies, server faculty binding, unauthorized administration, expiry, disablement, logout, CSRF, session rotation, password/role-change revocation, attempted self-promotion and blocked optimizer admission/recovery. Secrets exist only in test process memory; fixture representations and failure messages withhold them.

An account currently carries administrator/faculty role and faculty binding, **not an authoritative department mandate**. Existing J scoped authority checks require independently current actor/department/action grants and do not interpret an administrator label as optimization permission. Existing I/K/L tests verify cross-owner/scope denial and authorized recovery using prepared fictional providers. That adapter is test-only; no institutional provider is installed.

Chair final decisions require the separate D12 Chair directory, scope, term and lifecycle findings. D13 controlled application requires its own authority. Defaults remain absent: `institutional_chair_directory()`, `institutional_application_directory()` and `ga_trusted_runs.configured_service()` return None. A real fictional-fixture administrator receives a blocked Chair response and cannot activate bound runs. **Administrator, Department Chair, optimization operator, publication authority and zero-target workload exception authority are not interchangeable.** The 34 Chair review, six Chair trust and five application trust regressions pass, without creating any real mandate.

The development launcher is not an institutional SSO/service account contract. No approved deployment identity, departmental grant issuer, genuine term/cohort/resource catalog or institutional restore operator was supplied. These are explicit blockers, not application permissions inferred from the Windows user running this qualification.

## Windows containment

Re-executed all 12 L primitive cases (six native process cases and six configuration cases) and 41 supervised workflow cases using unchanged L source. Creation-time Job assignment, nested store/run/resource jobs, limited handle inheritance, descendant denial, parent-death child cleanup and separate owned-tree termination pass. Process ownership is PID plus creation time and private handles, never a bare stored PID. Same-session duplicate-worker prevention, stale fence rejection, supervisor crash/reopen and prior-owner liveness checks remain enforced; no automatic process reattachment is introduced.

The latest one-second CPU probe terminated at **1.09375 seconds user CPU**, exit `3221225540`. This is periodic user-mode CPU enforcement with overshoot, not exact CPU-rate or total-run budgeting. The 64 MiB private-commit probe rejects a 256 MiB allocation. Memory limits constrain commitment, not working set/RSS. The 31 ended supervised-process observations report zero active processes and peaks within their configured limits; maximum observed commitment was **705.5234375 MiB** under the 768 MiB fixture cap. A primitive pre-close accounting record may still report an active process after termination; its test separately requires zero after `close`.

Parent-side provider calls, reconstruction/validation, SQLite and orchestration remain outside child resource quotas. Parent death safely kills owned children in the tested topology but does not bound parent resource use. Whole-service/host RAM, CPU-rate, RSS and cross-session/service-account recovery remain unqualified and unavailable. No Windows service was installed, no deployment-wide containment was activated, and these processes are not a hostile-code sandbox.

## Storage, backup and recovery

The unchanged I/J/K/L contract accepts only newly owned private OS-temp stores with verified ownership/DACLs, strict versions, immutable bundles and owner/configuration/optimizer/lineage bindings. Disposable SQLite tests exercise transaction atomicity, locking, interrupted writes, rollback, checkpoint pins, corruption, stale fences/configuration, changed sources and fresh-process same-store continuation. The baseline historical checkpoints and schedules remain untouched.

The SQLite main-database page cap, per-run bytes/counts, process-attempt cap and storage-exhaustion rollback pass. A real oversized zeroblob transaction fails without replacing the old checkpoint/tip/best. A temporary fixture file's read-only test and a simulated zero-free-space test pass. These do not establish NTFS/volume, journal, backup or parent-memory quotas. Free-space inspection is not a reservation.

Private consistent backups and read-only integrity/owner/bundle/policy/chain inspection pass. **Writable backup restoration remains disabled**, pending independent anti-rollback freshness/ownership anchoring and approved restore authority. Reopening the same validated store in a fresh process is not restoration of an old image. Retention validates owner/tip/fence/terminal state but deletion remains disabled; exhaustion fails rather than erasing history. Approved service roots/accounts, physical storage policy and cross-session coordination remain institutional/deployment blockers. No existing ACL or database was altered.

## Integration readiness

The complete 23-row [readiness matrix](testing/dashboard-u5m/readiness-matrix.json) separates Implemented, Verified in isolation, Requires integration, Blocked and Unsupported. Key boundaries:

| Capability | Qualification |
|---|---|
| Fixed-generation execution and continuation | Existing workflow preserved; original nonzero parity and checkpoint/RNG continuation pass. |
| G bundle/H consumption/I owner/K-L lifecycle | Verified internally with isolated fictional data; not institutional HTTP deployment. |
| Continuous mode selector/readiness/retry | Implemented read-only UI; execution controls remain disabled. |
| Continuous start/pause/resume/stop/status/history/best | Internal worker contracts qualified; separate versioned HTTP/UI bridge still required. |
| Fitness breakdown, faculty satisfaction, teaching balance | Existing read-only analysis tested; continuous worker transport requires integration. Metrics are not approval or policy validation. |
| Chair decisions and controlled application | Independent authorization contracts exist; genuine institutional providers remain BLOCKED. |
| Parent resources, cross-session recovery, approved durable root | Unsupported/unqualified deployment modes. |
| Writable restore/retention deletion | Disabled pending authority and independent freshness/fencing policy. |
| CURRENT or historical Saved Best promotion | Unchanged; a U5D receipt is insufficient. |

No original fixed request is silently redirected, no legacy history is reclassified and no continuous optimizer route/control is activated. The browser's fictional readiness messages describe that public UI contract; they are not claims that the later internal H/K/L capabilities are absent.

## Fresh validation and evidence limits

| Selected Python suite | Passed |
|---|---:|
| U5M receipt qualification | 19 |
| U5M actual ASGI/session/SQLite identity | 16 |
| Original U5D receipts | 36 |
| L supervised workflow / native plus configuration | 41 / 12 |
| K bounded worker | 32 |
| H consumption / nonzero parity / legacy continuation | 39 / 5 / 10 |
| G bundle | 32 |
| I trusted admission / J qualification | 50 / 49 |
| U5A-C source/context/compatibility | 99 |
| E analysis / F readiness | 20 / 20 |
| D12 review / Chair trust / application trust | 34 / 6 / 5 |
| **Latest selected Python cases** | **525** |

These are selected cases across separate isolated executions, not 525 independent end-to-end institutional workflows. Earlier smaller successful suites and the three failed diagnostic invocations are retained, not added again to the final count. Two existing TestClient/httpx/AnyIO deprecation warnings remain in applicable suites; no warning was repaired by a dependency change.

Fresh frontend: **210 contracts passed; TypeScript, production build and focused ESLint passed.** Vite retains bundle-size/dynamic-import advisories. **16 actual Edge/React scenarios passed** (17 Node runner entries including the parent suite); six genuine PNGs were visually/privacy reviewed. Edge `156.0.4314.50`, Node `24.11.1`, 64-bit Python `3.14.2` on Windows 11. These use intercepted fictional HTTP acknowledgements, not a live continuous worker or institutional authorization. Frontend checks use committed source, deliberately excluding unrelated working-tree UI edits.

The original receipt suite also starts a real loopback Uvicorn server for a fictional read with an overridden principal; this is limited real HTTP evidence, not session/worker deployment acceptance. New identity tests use real application code through TestClient with disposable SQLite, not a browser-to-server network. L tests use native Windows processes and actual SQLite alongside explicit fault injections. Original/worker nonzero fitness remains **455.0**, with assignment, history, RNG and continuation parity assertions. No original GA operator, scoring, workload policy or optimizer source changed.

No fresh PostgreSQL acceptance was run. D15's earlier successful disposable PostgreSQL evidence is historical and preserved; it neither grants production authority nor qualifies this milestone's deployment. No genuine institutional acceptance is claimed.

## Reproduction and selective checkpoint plan

From the repository root in PowerShell, using existing dependencies:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5m/checkpoint_snapshot.py race
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5m/checkpoint_snapshot.py identity
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5m/checkpoint_snapshot.py receipts
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5m/checkpoint_snapshot.py native
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5m/checkpoint_snapshot.py supervised
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5m/checkpoint_snapshot.py parity
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5m/checkpoint_snapshot.py legacy
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5m/frontend_snapshot.py
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5m/audit_evidence.py
```

Other recorded selections are `worker`, `consumption`, `bundle-tests`, `admission`, `qualification`, `backend-regressions`, `analysis`, `readiness`, `chair`, `chair-trust` and `application-trust`. Run each separately; each creates a new timestamped evidence directory. Regeneration requires an explicit new manifest review; the sealed audit never silently includes new results. The source snapshot excludes academic/runtime data, reuses the unchanged U5C release-byte preparation and restores committed current main before testing. No fingerprint check is bypassed. Its generic consumption-proof field records prerequisite capability, not proof that every selection runs an optimizer; actual per-suite scope is documented above.

The exact new/modified inventory and raw SHA-256 hashes are in the [manifest](testing/dashboard-u5m/manifest.json). It excludes its own hash. The [audit](testing/dashboard-u5m/audit_evidence.py) rechecks 4,138 unchanged baseline paths, one intended source edit, 512 prior G-L artifact hash references, final tested source identities, all new artifacts, six PNG CRC/metadata/visual reviews, complete/truncated receipt/credential patterns, whitespace and Git integrity. Raw worker protocol, checkpoint files, SQLite databases, signed receipts and auth/session dumps are not archived. Technical process IDs, fictional run UUIDs and temporary paths are diagnostic identifiers, not institutional identities or access credentials.

The [staging plan](testing/dashboard-u5m/staging-plan.json) proposes two later groups: the repaired service and two new test files; then the report, tooling and complete evidence. No partial staging is needed for the receipt module because it was clean at entry. Exclude all eleven pre-existing modified files, including both protected JSONs, and all 958 prior untracked files. Use literal NUL-delimited exact paths and byte-preserving `core.autocrlf=false` after separate authorization and fresh remote/index/blob/hash checks. Nothing has been staged or committed.

## Remaining blockers and U5N recommendation

The reproduced legacy defect no longer requires an unexplained-flake waiver: deterministic replay, actual stress, full observer isolation and security negatives support the repair. This remains bounded local Windows qualification, not a universal filesystem-race proof.

Recommend U5N qualify an explicitly approved service identity/root and a server-owned scoped authority/capture configuration, independently anchored restore freshness and cross-session ownership. Specify and test parent/whole-service resource boundaries and physical journal/backup/volume budgets before exposing a separately versioned worker HTTP/UI bridge. Keep true institutional approval/publication, CURRENT promotion, writable backup restore and retention deletion blocked until their own requirements are met. No U5N, production activation, code cleanup or performance integration is implemented here.
