# Accelerated Increment 3: bounded continuation and recovery qualification

16 November 2026, Asia/Manila. Baseline: WIP `2839631b770dbf7debc65e36028d1c8ae481d211`; main remains `0dcc3e942d0b79c0e6358aa151208c014b307300`. This increment adds isolated code and evidence only. Previous increments, failed attempts and unrelated work are preserved.

**Outcome: native GA acceptance BLOCKED; Edge acceptance BLOCKED; finite offline continuation and fresh-process metadata bootstrap verified; seven-day release NO-GO.** No native worker, browser or seven-day experiment was launched. This report does not qualify the prototype as fully operational.

## Preflight and exact remaining access action

One initial sample found **5.338 GiB available of 15.711 GiB RAM**, above the 3 GiB gate, and **57.1 GiB free disk**. This is a point-in-time observation, not continuous monitoring or a future reservation. Initial `Get-Process` found no Python processes and two Node processes whose executable paths identify Codex runtimes. No process was stopped; full command-line/owner-token inspection was not established.

Direct **`os.scandir('backend/.pytest_cache')` still fails with PermissionError, errno 13, WinError 5**. An initial `Path.rglob` returned zero entries because that API can suppress traversal errors; that result was explicitly rejected and never treated as proof that the cache was empty or preserved. Historical operator evidence remains internally consistent but unauthenticated. No new owner attestation was generated or promoted. RAM recovery alone does not authorize native/Edge acceptance.

The remaining action is **approval of a narrow, independently observed normal-user measurement of the five cache files**, or approved direct read access. A suitable proposed method is a trusted host-tool invocation of the pinned existing script under the operator's normal, non-elevated token, with a fresh challenge and tool-recorded command, identity/integrity verification, script hash, baseline hash and complete two-snapshot output. It must be explicitly accepted as the measurement source for these five files, then combined with fresh direct verification of all other baseline paths. It is not a historical-preservation exception. A self-reported identity, another saved JSON, a screenshot alone or the same command run unobserved is insufficient.

Exact operator authorization needed: “Authorize the reviewed five-file read-only attestation through a trusted normal-user execution channel, without administrator elevation, ACL/ownership changes or cache writes, and accept that authenticated measurement as the narrowly scoped cache source.” This increment did **not** make that permission change or execute outside its existing read context. The pinned command for that separately observed verification is:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pf/cache-access-diagnosis/attest_backend_cache.py --read-only
```

Reviewed tool SHA-256: `4ddebabd40d474b499ac7e57a32ec219f2a3aa064143d1ca1b7e06cb517e653d`; original baseline SHA-256: `a301e0821f6d025e0ae39e8231051d6233665c4f5f4ff59255cb05c6a50ff04b`. Recheck those pins before any future invocation. The command alone does not authenticate origin. If direct Codex traversal is mandatory, delegated evidence cannot substitute; the operator must authorize a compatible direct-read mechanism separately.

## Implemented finite supervisor

`backend/services/prototype_continuation_supervisor.py` adds `fictional-finite-supervisor-v1` in a **new owned SQLite namespace**. It reuses the exact existing Cycle and original Session/checkpoint codec. No GA code, fitness coefficient, workload rule, operator, RNG operation, ordinary endpoint, institutional authority or historical store changes.

- An immutable, hash-chained intent precedes dispatch. Explicit owner, nonce, fence, original sequence/tip and lease prevent duplicate dispatch. Mutable claim rows are checked against immutable intent and acknowledgement records; eight tamper cases cover nonce, owner, fence, prior sequence/tip, observed sequence, lease and state.
- The only executor is an explicitly enabled **offline in-process oracle** calling existing `Cycle.step_offline`. Defaults fail closed. There is no native transport, launch route, Start button, automatic loop or deployment activation.
- After each segment, the unchanged original codec verifies the full population, best-ever, generation and next-generation counters, complete history, RNG, bundle, configuration, optimizer and scoring identities. Captured preference/minimum/weight provenance is fingerprinted. The supervisor never reconstructs a candidate from a witness or changes its score.
- Checkpoint/result persistence remains the Cycle's atomic SQLite transaction with the existing separate tip witness. A supervisor acknowledgement is a later transaction, **not** a distributed atomic commit across all stores. If interrupted after the checkpoint commit, the pending intent blocks another dispatch. Explicit reconciliation verifies the existing committed successor and records it without another generation or RNG draw. No checkpoint means no fabricated fresh-run “recovery.”
- Cooperative Stop uses the existing immutable command. Replays do not duplicate the supervisor event. Stop remains a request, never verified worker exit. Offline finalization is labeled `NOT_APPLICABLE_IN_PROCESS_ORACLE`; physical termination remains `NOT_VERIFIED`.
- Primary failures are preserved. When possible, a separate failure event is durable; audit-write failure is retained separately in memory if durable storage itself is unavailable. That last-resort memory signal is not restart-durable, and storage failure is not represented as successful recovery.
- The new journal has a 4 MiB logical-event budget, approximately 8 MiB SQLite page cap and 64 events per run. It retains all events with **no automatic deletion**. These are not filesystem quotas or permission guarantees. Original Cycle limits remain unchanged.

The supervisor and local HMAC witness are not externally anchored deployment identity. Corruption and primary-store rollback checks do not establish protection against coordinated rollback/replacement of every store and key. The supervisor journal still needs an independently trusted freshness/ownership anchor and approved reconciliation/custody policy before deployment.

## Private bootstrap and recovery evidence

`backend/services/prototype_recovery_bootstrap.py` adds `fictional-cold-bootstrap-v1`. It atomically creates a **new private descriptor** containing the original base bundle, scope, exact store roots, implementation identities and bindings. A separately retained pin binds the descriptor hash, run, Cycle identity and witness key fingerprint. No private bundle, checkpoint, RNG tuple, key or descriptor is archived in repository evidence.

Reopening requires fresh workload, input and workflow authority providers. Stored actor/department labels never create authority. The current caller is checked by those providers, the prepared input is reread, and its fingerprint must match the exact run. Implementation, descriptor, engine, input, configuration and witness changes reject recovery. Default reopening cannot execute or recover a worker. Missing metadata is rejected rather than inferred from a filename or time.

Verified boundaries:

| Boundary | Evidence |
|---|---|
| Same-process reconstruction | ALL workload/input/Cycle/witness objects reconstructed, not merely an HTTP listener; source objects are distinct. |
| Exact continuation | Actual original GA full run equals segmented execution in assignments, fitness, breakdown, faculty analysis, history and final RNG. Global RNG unchanged. |
| Genuine inputs | Explicit three-unit minimum, Chair-approved day coefficient 17 and a faculty day/subject preference frozen before execution; no post-capture repair. Original fitness is 450. |
| Fresh process | A separate Python **read-only metadata helper** reopens all private services with fresh fictional server providers and decodes the same original checkpoint. All private store hashes remain identical. |
| Fresh-process GA resume | **NOT RUN**. The helper calls Session.run zero times, launches no worker/API/browser and proves no process supervision or native continuation. |
| Lost acknowledgement | Injected interruption reconciles the single committed generation; no repeated generation. This is a simulated crash window, not OS/power-loss acceptance. |
| Corruption/ownership | Missing/corrupt checkpoints, descriptor/pin mismatches, cross-owner and revoked grants, concurrent dispatch, immutable events and mutable-claim tampering fail closed. |
| Physical recovery/termination | **NOT VERIFIED** for this prototype path. Existing Windows Job Object code is preserved, not newly qualified here. |

The descriptor and private SQLite files currently live in new owned temporary directories. They are not approved seven-day deployment storage, backups or key escrow. An external pin and fresh providers must survive independently; losing them must fail closed. A pinned descriptor alone does not recover a lost witness key or whole-host rollback.

## Measured storage and limits

The final `storage-measurement.json` records actual sizes and exports. For the tiny two-offering case, two checkpoints are **1,176,666 and 1,177,581 bytes**, the Cycle database **2,715,648 bytes**, and the witness database **12,288 bytes**. The two-point history is 114 JSON bytes; actual JSON/CSV/text exports are **11,050 / 252 / 3,537 bytes**. These are not measurements of Medium/Large or native execution. Complete histories repeat inside checkpoints.

At a purely hypothetical checkpoint every 600 seconds, seven days has **1,008 checkpoint intervals**. Repeating the largest observed size unchanged would use **1,187,001,648 bytes (1.11 GiB)** for raw checkpoints alone. This is a conditional illustration, **not a proven lower bound, capacity forecast or measured generation rate**; future graphs/history can differ. Multiplying the 8 MiB per-checkpoint cap by 1,008 is 7.875 GiB, excluding databases, result copies, journals, backups, exports and archive overhead.

The current eight-checkpoint/64 MiB profile and **600-second entire-run lifetime** cannot host that campaign. The original worker limit remains at most 600 seconds per guarded worker; it was not increased or bypassed. Current generation caps remain 20 for the existing fixture admission and 2 for the offline oracle. No throughput extrapolation or expected seven-day generation count is justified without representative native measurements. Actual physical recovery time and a time-based interruption-loss bound remain unmeasured. Only “work since the last verified boundary” is established. A generation may itself exceed a segment budget; that requires native measurement, not an assertion that checkpoints can occur mid-generation.

Required separate operational decisions: fixed generation horizon before input capture; experiment versus physically bounded segment clocks; immutable archive and storage reservations; independently anchored run/tip ownership; key/pin custody; recovery after uncertain commits; and Stop/termination evidence. These are not authorization to alter the original equation, RNG or operators. Original finite checkpoints cannot be relabeled, rebound to a new native run or resumed with enlarged parameters. Repeated fresh experiments are a different research campaign.

## Tests and limitations

Final result details and exact source identities are recorded in the manifest. The selected tests are offline in-process GA, temporary SQLite, TestClient HTTP and a fresh read-only metadata subprocess. No claim of Edge, native worker, physical restart or a fully green repository-wide suite is made.

- Final new supervisor/bootstrap suite: **26 passed**. Earlier 17- and 18-case successful iterations remain evidence, not additional distinct passes.
- Scheduling/review regressions: **5 passed**, including real original-engine 24-unit output, generated minimum violation rejection, 24-versus-12 pre-dispatch rejection and the actual session/CSRF/Chair/export/timetable TestClient workflow.
- Original V1/bundle deterministic parity and in-process checkpoint continuation: **5 passed**. Exact schedule/history/RNG behavior remains unchanged.
- Targeted original checkpoint-integrity/configuration tests: **12 passed**, including corrupt binding/sequence/parent/run/version, configuration drift, legacy/missing/cross-run/stale checkpoint rejection, and frozen preference/weight continuation.
- One regression attempt: **4 passed, 1 failed** because the NEW test snapshot omitted existing frontend assets. The unmodified API test correctly raised FileNotFoundError. The runner now copies the preserved prototype assets; the full five-case rerun passed. No existing application or historical test was changed to hide it.
- Two existing Starlette/httpx and AnyIO deprecation warnings remain. No dependency installation.
- Frontend contracts, TypeScript, build and browser tests were **not rerun**: no frontend/React input changed. Prior passes remain historical.

There are **48 distinct passing selected Python cases** (26 + 5 + 5 + 12), executed as separate groups rather than one combined-suite claim. The collection and earlier successful reruns are not extra passes.

Reproduce permitted checks, from the repository root:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/scheduling-first-accelerated-3/run_checks.py core
.\.venv\Scripts\python.exe -B docs/testing/scheduling-first-accelerated-3/run_checks.py regressions parity integrity
.\.venv\Scripts\python.exe -B docs/testing/scheduling-first-accelerated-3/audit_evidence.py
```

These commands create fresh owned empty-import snapshots, use only fictional model data and new private SQLite stores, disable pytest cache/bytecode, sanitize output and retain timestamped attempts. The core includes a metadata-only child; no selector launches a native worker or browser. New executions require a new evidence addendum, not silently rewritten historical results.

## November 22 critical path

| Date | Exit condition |
|---|---|
| November 16 | Offline finite continuation, pinned full-service reconstruction, read-only fresh-process bootstrap and storage/journal failure checks completed. Cache access still blocks acceptance. |
| November 17 | Resolve authenticated preservation; recheck RAM immediately before permitted native work. Bind a fresh, correctly owned native admission to exact frozen preferences/weights/minima and the existing guarded worker. No migration of offline checkpoints or spoofed fingerprints. |
| November 18 | Genuine native output, physical exit, crash/resume and exact prepared-input consumption acceptance; then actual Edge scheduling/review/export/timetable workflow. |
| November 19–20 | Only after explicit operational-policy review: long-run clocks/horizon, external anchor, persistent storage/archive and cold-start ownership qualification; representative bounded stability/fault tests. |
| November 21 | Freeze verified release/input/weight identities and perform explicit prototype and seven-day GO/NO-GO handoff. |
| November 22 | Demonstrate only qualified functionality. Start seven days only after all gates pass; a start then ends around November 29. Otherwise preserve NO-GO. |

The native frozen-input transport and genuine Start/progress control path are **not implemented by this supervisor**. Existing native bridge/control code must be reused through a reviewed versioned adapter with correct run/bundle identity and physical resource proof. Merely clearing the cache gate does not make the admission-only prototype page start a worker. This is a distinct implementation/acceptance dependency, not an institutional-source dependency.

Next increment: authenticated cache verification and the finite prepared-input native adapter, followed by one bounded genuine execution and actual exit proof. Leave the seven-day release policy, institutional providers and cosmetic changes separate. November 22 remains conditional.

## Preservation and inventory

Exact new paths, artifact SHA-256 hashes and raw Git blob identities are in [the manifest](testing/scheduling-first-accelerated-3/manifest.json). All **5,822 readable baseline paths**, including all 23 academic files, both protected JSON files, original GA/scoring/RNG/fingerprint sources, migrations, notebooks, historical schedules/Saved Best/checkpoints and previous evidence must match at sealing. The authorized prior WIP commit's index identity is the new entry baseline, explicitly distinguished from content drift. Original eleven tracked modifications and 972 unrelated untracked files remain untouched.

Full preservation qualification remains **false** for the inaccessible backend cache. No earlier exception was reused. No ACL/ownership/cache changes, permission elevation, institutional PostgreSQL operation, migration, dependency installation, staging, commit, push or deployment occurred. No earlier file was edited; all current additions are new isolated services, tests, tooling, documentation and sanitized evidence.

Production admission and institutional Saved Best promotion **BLOCKED**. Institutional Continuous Optimization **DISABLED**. Active institutional restore **BLOCKED**. Seven-day experiment **NO-GO**.
