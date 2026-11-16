# Accelerated Increment 4: frozen-input native adapter and acceptance gates

16 November 2026, Asia/Manila. Branch `wip/u5pf-experiment-exports`, HEAD `2839631b770dbf7debc65e36028d1c8ae481d211`. Main remains `0dcc3e942d0b79c0e6358aa151208c014b307300`. No Git checkpoint or deployment is authorized or performed in this increment.

**Outcome: the isolated adapter and versioned API are implemented and exercised with the genuine GA worker protocol IN PROCESS. Real Windows worker execution, physical termination/recovery and Edge acceptance remain BLOCKED. Seven-day readiness remains NO-GO.** No in-process or HTTP result is presented as native/browser acceptance.

## Preservation recovery: exact blocker and decision

The initial preflight measured **4.314 GiB available RAM** (15.711 GiB total) and **59.76 GiB free disk**. RAM passed the retained 3 GiB gate at that observation; it must be rechecked before a future permitted launch. Strict `os.scandir` still fails on `backend/.pytest_cache` with PermissionError, errno13/WinError5. No repeated access workaround, permission elevation, ACL/ownership change, cache deletion/rename/write or unauthenticated “success” was used.

The reviewed original tool and baseline hashes remain:

- Tool: `4ddebabd40d474b499ac7e57a32ec219f2a3aa064143d1ca1b7e06cb517e653d`.
- Original baseline: `a301e0821f6d025e0ae39e8231051d6233665c4f5f4ff59255cb05c6a50ff04b`.

Historical operator execution cannot be authenticated retrospectively from the retained unsigned evidence. Its hashes/metadata are preserved; no historical origin or continuous-preservation claim is invented. The smallest proposed recovery is a **separately approved prospective operator-controlled baseline for exactly five cache files**. It retains that historical uncertainty and does not amend the general preservation policy or reuse U5P-D's one-time exception. Proposal, challenge and all five pinned expected hashes are in `docs/testing/scheduling-first-accelerated-4/preservation-proposal.json`. Status is **PROPOSED_NOT_APPROVED_NOT_ADOPTED**.

Two distinct operator actions are required:

1. Explicitly approve using a fresh operator-controlled measurement to establish a **forward-looking** five-file baseline, while acknowledging that it does not independently authenticate old execution. A suitable approval is: “Approve the prospective five-cache-file baseline method for this isolated acceptance session; retain historical authentication uncertainty. Do not infer native or seven-day qualification.” Approval of the method alone does not qualify the snapshot.
2. Run the following read-only check from the owner's existing **normal, non-elevated PowerShell**, then allow review of the actual complete new JSON. The record labels its identity as a claim, not independent authentication. After review, explicit approval must identify the exact new file SHA-256 and challenge before any prospective baseline is adopted. All other readable paths still require direct verification, and a current server admission finding must be supplied. A new unauthenticated JSON alone changes nothing.

The block below checks pins before calling the existing read-only tool. It writes only a **new evidence file**, never cache contents, credentials or an old artifact. It does not change policy or launch an application. No execution-policy change is needed when pasted directly into the existing terminal.

```powershell
& {
    $cacheRepo = 'C:\Users\User\Desktop\Genetic-Algorithm Dashboard'
    $cacheProposalPath = Join-Path $cacheRepo 'docs/testing/scheduling-first-accelerated-4/preservation-proposal.json'
    $cacheProposal = Get-Content -LiteralPath $cacheProposalPath -Raw | ConvertFrom-Json
    $cacheTool = Join-Path $cacheRepo 'docs/testing/dashboard-u5pf/cache-access-diagnosis/attest_backend_cache.py'
    $cacheBaseline = Join-Path $cacheRepo 'docs/testing/dashboard-u5pf/preservation-baseline.json'
    if ($cacheProposal.challenge -ne 'A4-CACHE-d75898c4-d364-4a2a-9f45-5190d878d96d') { throw 'Proposal challenge mismatch' }
    if ((Get-FileHash -LiteralPath $cacheTool -Algorithm SHA256).Hash.ToLowerInvariant() -ne '4ddebabd40d474b499ac7e57a32ec219f2a3aa064143d1ca1b7e06cb517e653d') { throw 'Tool pin mismatch' }
    if ((Get-FileHash -LiteralPath $cacheBaseline -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'a301e0821f6d025e0ae39e8231051d6233665c4f5f4ff59255cb05c6a50ff04b') { throw 'Baseline pin mismatch' }
    $cacheIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $cachePrincipal = [Security.Principal.WindowsPrincipal]::new($cacheIdentity)
    if ($cachePrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) -or $cacheIdentity.Name -match 'CodexSandbox') { throw 'Use the owner normal non-elevated terminal' }
    $cacheStart = [DateTimeOffset]::Now.ToString('o')
    $cacheRaw = @(& (Join-Path $cacheRepo '.venv/Scripts/python.exe') -B $cacheTool --read-only)
    if ($LASTEXITCODE -ne 0) { throw 'Read-only cache check failed; do not retry acceptance' }
    $cacheResult = ($cacheRaw -join [Environment]::NewLine) | ConvertFrom-Json
    if ($cacheResult.status -ne 'SCOPED_CACHE_CONTENT_MATCH' -or $cacheResult.files_read -ne 5 -or -not $cacheResult.exact_membership_verified -or -not $cacheResult.two_snapshots_identical) { throw 'Incomplete cache result' }
    $cacheRecord = [ordered]@{
        schema = 'a4-operator-prospective-cache-sample-v1'
        challenge = $cacheProposal.challenge
        started_at = $cacheStart
        ended_at = [DateTimeOffset]::Now.ToString('o')
        claimed_execution_identity = $cacheIdentity.Name
        origin_independently_authenticated = $false
        forward_baseline_approved = $false
        historical_authentication = 'UNVERIFIED'
        native_acceptance_authorized = $false
        measurement = $cacheResult
    }
    $cacheOutput = Join-Path $cacheRepo ('docs/testing/scheduling-first-accelerated-4/operator-cache-sample-' + (Get-Date -Format 'yyyyMMddTHHmmssfffffff') + '.json')
    $cacheBytes = [Text.UTF8Encoding]::new($false).GetBytes(($cacheRecord | ConvertTo-Json -Depth 12) + [Environment]::NewLine)
    $cacheStream = [IO.File]::Open($cacheOutput, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $cacheStream.Write($cacheBytes, 0, $cacheBytes.Length); $cacheStream.Flush($true) } finally { $cacheStream.Dispose() }
    [pscustomobject]@{ File=$cacheOutput; SHA256=(Get-FileHash -LiteralPath $cacheOutput -Algorithm SHA256).Hash; Challenge=$cacheProposal.challenge; Status='REVIEW_AND_SEPARATE_APPROVAL_REQUIRED' }
}
```

This is an **unexecuted operator handoff**, not an accepted attestation. No production preservation provider has been installed. The typed server finding is only an integration contract; constructing a dataclass or sending a client label is not authentication. If the operator retains the direct/independently authenticated read requirement instead, that gate remains blocked until an approved read channel exists; this proposal does not silently relax it.

## Implemented frozen-input adapter

New `prototype_native_adapter.py` composes the existing Cycle and finite supervisor. It opens a **new private namespace**; its release marker binds the adapter/transport/source identities, resource policy, Cycle and supervisor. An immutable `NATIVE_ADAPTER_OWNERSHIP` audit event registers exactly one journal root/release for a fresh run. A new root cannot adopt a prior run/checkpoint. Reopening requires the exact retained root and release. Existing checkpoints, old engine fingerprints and prior supervisor files remain unchanged.

The path is:

1. Fresh scoped server authority checks the actual principal and immutable preparation.
2. The exact bundle bytes, configuration, preferences, approved coefficients, minimum snapshot and original initial RNG are bound to a finite run. The original optimization run ID and logical run ID remain distinct and recorded; neither is rewritten to fit another checkpoint.
3. An immutable segment intent, nonce, owner, fence, lease and source tip precede dispatch. Duplicate requests replay their existing result; concurrent controllers cannot transfer root ownership or overwrite a newer owner.
4. The adapter calls the **unchanged `ga_worker_child.batch` protocol**. One batch targets one original generation boundary, including initial population at generation0. The child receives no credentials, authority providers or database access. Original Session performs the actual optimization.
5. The parent uses the original strict checkpoint codec, verifies sequence/parent/run/input/configuration/scoring/optimizer/RNG identities and independently checks the original complete report against that checkpoint. Parent Stop-before-another-draw finalization is reporting verification, not a replacement optimizer. Exact zero values and original lower-is-better behavior are unchanged.
6. Original hard validation and captured-minimum qualification are applied to the actual generated assignments. A minimum deficit remains a constraint violation even if original fitness is low. No repair, new penalty or ineligible/conflicting assignment is inserted.
7. A successful physical exit is required before a native candidate can commit. Checkpoint and result commit together in the existing new Cycle store, followed by the separate tip witness and supervisor acknowledgement. Uncertain commits quarantine; no silent witness advancement or recomputation.
8. Existing Chair decisions, immutable prototype versions, timetable and exports can consume the qualified candidate. Institutional approval, Saved Best promotion and CURRENT classification are not activated.

`prototype_native_transport.py` has two deliberately different server-owned transports:

| Transport | Execution / evidence |
|---|---|
| `WindowsTransport` | Reuses existing creation-time Windows Job binding, memory/CPU policies, restricted handle/environment transport, owned process handles and PID+creation identity. Default preservation provider is **None**, so launch fails closed. This branch is implemented but **not executed/qualified** here. |
| `InProcessQualification` | Calls the real unchanged worker batch in the test process. It never creates a Windows worker, never invents a PID/exit code, and cannot set native verification true. It is an explicit offline test capability unavailable through ordinary main.py. |

The native branch records the current server preservation finding at start and exit, actual process identity, resource/exit observation and separate cleanup failure. Parent exceptions are not overwritten by cleanup/audit errors. A response cannot be persisted as native unless its owned-process exit was verified and successful. Recovering an old PID uses a read-only PID+creation-time check; it never kills a stored or unrelated PID.

The original **600-second entire-run lifetime** and worker maximum are preserved. This adapter retains a **60-second segment profile**, not an increased limit. CPU/private-memory policies are inherited unchanged from U5L. Parent verification is outside the child Job; it has cooperative elapsed/lease checks, not a claimed physical parent-memory quota. Generation horizon is never enlarged. At one checkpoint per boundary, the eight-checkpoint profile permits at most seven optimization generations; larger captured requests are rejected, not silently shortened. Original Cycle admission's wider finite maximum is not permission to exceed adapter storage limits.

## API and provenance boundaries

New opt-in factory `routers.prototype_native.create_app` adds authenticated, scoped `/api/prototype/native-v1/runs/{run}` GET plus bounded segment/recovery POST and JSON/CSV/text export GET. Existing cookie/CSRF, no-store and loopback restrictions apply. Client input is a strict request nonce, not a role, bundle, score, transport or authorization finding. Ordinary `main.py` and legacy routes are untouched.

The versioned native projection reports the actual execution kind and process assessment. Existing Cycle projections remain conservatively legacy/offline; they have not been silently redefined. New native consumers should use the versioned status/export contract. Generated nested candidate provenance is retained in approved prototype versions. There is **no new frontend Start control or automatic multi-segment loop** in this increment. Browser integration with the versioned execution path remains work after genuine native acceptance, not a completed user journey.

The endpoint executes one bounded segment synchronously; status can observe its durable lifecycle from another request. Only genuine completed-boundary fitness is available. No intermediate fitness, satisfaction percentage or worker termination is fabricated. Native-route presence does not configure a preservation provider or enable institutional optimization.

## Recovery and test boundaries

The new tests exercise real batch inputs/output and original GA state through the **in-process transport**, new private SQLite stores, and actual TestClient HTTP. They verify frozen coefficients/preferences/minima, full result/RNG parity, ownership, root binding, idempotency, source/exit-record corruption, response tampering, approval denial for deficits and qualified review/application/export.

Recovery distinguishes:

- A committed checkpoint with a lost acknowledgement: acknowledge that exact existing boundary without generating it again.
- A failed next batch with a prior verified checkpoint: explicitly return to that prior boundary with unchanged initial seed, population, RNG and history. The recovery record says **no new work**; it is not a fresh experiment labeled continuous.
- No committed checkpoint: recovery is rejected instead of inventing state.
- An active/unverifiable old native process: recovery is rejected; no PID-based kill.
- A lost response after a durable acknowledgement: the old exception cannot poison the acknowledged result; retry returns the existing result.

The root/release-bound cold object graph is rebuilt with fresh providers using Increment3's bootstrap. Increment3's fresh-process **metadata-only** probe is rerun as a regression; it is not native restart/resume acceptance. Native process startup, actual physical exit, cooperative worker Stop and cold-process GA resume have **not** run. Lost-ack and interrupted-batch tests are injected fault cases; their observations are not real crash/power-loss measurements.

### Failures retained, not hidden

1. Initial adapter run: **22 passed, 1 failed**. The broad-eligibility, jointly underprovided minimum case exceeded the unchanged qualification batch budget. The exception occurs after `batch` returns, so the measured span includes restore/search/finalization/serialization; no exclusive CPU, native timing or host-contention diagnosis was obtained. This is not proof that a search budget establishes mathematical infeasibility. The old test remains intact and is explicitly **deselected** in routine runs to avoid repeatedly spending the same budget. It can be selected separately as `budget-diagnostic`; it is not counted as passed or fixed. A new, explicitly generations0 initialization-only negative case checks rejection of a genuinely generated deficit; it does not qualify the old generation1 case.
2. Next adapter run: **23 passed, 1 failed, 1 deselected**. The new adapter assumed every original command had an `action` key; original Stop records do not. Only the adapter lookup was corrected to respect the existing heterogeneous command contract. Original Stop records/code were not changed.
3. Increment3 regression attempt: **25 passed, 1 failed** because the new runner omitted the preserved metadata helper. The runner now copies that exact helper. No old test or application source was modified to hide the fixture failure.

Successful intermediate runs, final source identities, actual counts and all failures are in the manifest. Counts are distinct selected cases across groups, not a repository-wide all-green claim. The budget diagnostic remains a known failed observation. Two existing TestClient dependency deprecation warnings remain; no dependency was installed.

| Final selection | Actual result |
|---|---|
| Adapter | **31 passed, 1 deselected**, 123.91 seconds. Seven cases use mocked read-only PID/identity probes, not OS termination evidence. Retained over-budget generation1 case is the deselected case. |
| New versioned API | **1 passed**, 20.48 seconds, with two existing warnings. |
| Original GA parity/continuation | **5 passed**, 44.70 seconds; unchanged original source identities verified. |
| Increment3 recovery/bootstrap | **26 passed**, 31.10 seconds, including the fresh read-only metadata subprocess. |
| Original checkpoint integrity/configuration | **12 passed**, 26.96 seconds. |

**75 distinct passing selected Python cases**, run as separate groups. These are not additional counts for reruns or individual HTTP assertions, and do not erase the known failed/deselected diagnostic. The genuine adapter-protocol 24-unit case assigns `[12,24]` and is qualified against original hard constraints and the captured sparse minima. Its exact original fitness and assignments are in `genuine-minimum24-protocol.json`.

No frontend source changed; TypeScript, production build and frontend contract results remain historical rather than being recounted as fresh. Real TCP/browser acceptance was not run. New HTTP evidence is **TestClient + cookies/CSRF + SQLite + genuine in-process GA protocol**, not Edge or a real Windows worker.

## Seven-day and November 22 assessment

**Seven-day readiness remains NO-GO.** No lifetime, generation, storage or retention cap was raised. The previous measured 1.18 MB tiny-fixture checkpoints and conditional 1,008-checkpoint ten-minute cadence illustration are retained; no new native throughput or seven-day storage forecast is claimed.

Minimum remaining critical path:

1. Operator decision and actual review of the prospective cache measurement, or a compatible authenticated read mechanism. Recheck all readable preservation and RAM before any launch; install a reviewed current server finding only after that gate is genuinely qualified.
2. One finite, deterministic **real Windows** adapter run; record exact consumption, genuine assignments/minima/hard constraints and actual owned-process exit. Investigate the retained slow profile with native CPU/private-memory/elapsed observations; do not enlarge limits to obtain a pass.
3. Real worker interruption, cold-process exact resume, corruption rejection, duplicate ownership and cooperative Stop/verified exit acceptance.
4. Actual Edge workflow through the versioned bounded execution path, including Chair decisions, timetable refresh and exports. Existing browser-control code can be reused; no unqualified decorative Start control is added now.
5. Explicitly review the experiment horizon, distinct experiment/segment clocks, independent ownership/freshness anchor, persistent storage/archive/key custody and uncertain-commit recovery. Current temporary roots, eight checkpoints and 600-second lifetime do not authorize seven days. Repeated fresh runs are not continuous GA continuation.

November17 should resolve the preservation decision and finite native acceptance; November18–19 should prove native recovery and Edge; November20–21 should qualify any separately approved long-run policy and freeze the tested release. **November22 remains conditional, not a promised acceptance date.** A seven-day start then ends around November29 and is permitted only after an explicit GO. No seven-day run is launched here.

## Reproduction and preservation

Permitted offline commands, from repository root:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/scheduling-first-accelerated-4/run_checks.py core api
.\.venv\Scripts\python.exe -B docs/testing/scheduling-first-accelerated-4/run_checks.py parity inc3 integrity
.\.venv\Scripts\python.exe -B docs/testing/scheduling-first-accelerated-4/audit_evidence.py
```

The runner only supports fictional offline selectors; none launches Windows workers or Edge. `budget-diagnostic` is a separate known-cost investigation, **not** a required routine rerun. New attempts require a new evidence addendum, not rewriting sealed manifests.

[The manifest](testing/scheduling-first-accelerated-4/manifest.json) is the exact modified/new inventory and artifact/raw-blob map. No earlier repository file is changed. All **5,853 readable baseline paths**, including Increment3's 31 uncommitted files, all23 academic files, protected preferences/settings, original GA/scoring/RNG/fingerprint/migration/notebook sources, Saved Best, checkpoints, historical schedules and prior evidence must match at sealing. Original11 tracked modifications and all1,003 entry-untracked paths are preserved. The inaccessible five cache files are not called directly verified; older historical limitations remain disclosed.

No ACL/ownership/cache change, permission elevation, institutional database operation, migration, dependency installation, staging, commit, push or deployment. Production admission/institutional promotion **BLOCKED**; institutional Continuous Optimization **DISABLED**; active institutional restore **BLOCKED**; seven-day **NO-GO**.
