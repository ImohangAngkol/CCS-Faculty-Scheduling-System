# U5P-F recovery R1 — preflight stop

Reviewed 12 November 2026, Asia/Manila. **STOP: insufficient RAM and incomplete read-access coverage. U5P-F is not ready for checkpointing.** No native worker, Edge acceptance, PostgreSQL connection, migration or new test suite was launched in this recovery attempt. No implementation was restarted or changed.

## Git and existing evidence

`main` remains at `0dcc3e942d0b79c0e6358aa151208c014b307300`, with an empty index. The original eleven tracked modifications and 958 unrelated untracked files match the earlier entry. All 45 existing U5P-F paths remain byte-identical, including the report, manifest, staging plan and every failed attempt. All 44 artifact SHA-256 hashes and 43 raw blob proposals were rechecked. The old seal files independently match the previously recorded SHA-256 values.

A fresh traversal verified hashes for 5,639 known paths: the original 5,594 plus 45 U5P-F paths. This includes all 23 academic files, protected preferences/settings, GA/scoring/RNG sources, migrations, checkpoints, schedules, Saved Best and prior research work. The 295 known ignored files across 54 containing directories and all eight reconciled historical artifacts match. All 1,793 prior artifact references verify, with the original authorized U5P-C commit supplying its three superseded source blobs. No U5P-D exception is applied, and no earlier checkpoint recoverability is asserted.

**Coverage qualification:** the initial traversal used the existing walk convention and verified known membership, but Git subsequently warned that `.pytest_cache` could not be opened. The standard and escalated read-only probes both failed; Windows returned `UnauthorizedAccessException`. The directory was not excluded, assumed empty, deleted or repaired. Its unknown contents prevent a complete fresh preservation signoff. `preservation-baseline.json` is retained as a known-file hash baseline, not evidence that unreadable contents were inventoried. The earlier report/seals are historical evidence and are not rewritten to conceal this finding.

## Resource review

The first observation found 1,486,311,424 bytes available physical RAM (about 1.38 GiB), 91% memory load and roughly 16.7 GiB free disk. The subsequent ownership snapshot recorded 1,644,720,128 bytes available (about 1.53 GiB). These point observations do not measure total process-RAM demand or establish paging as the cause of past latency.

The sanitized inventory records 31 active Python/Edge processes. All belong to the same Windows user, but none has an isolated-source-snapshot marker in its command. Same-account ownership does not establish milestone ownership or permission to terminate it. No process was terminated. No raw command lines, account names, SIDs, credentials or browsing URLs are archived.

Both AC/DC idle sleep and idle hibernation timeout indices are zero. No settings were changed. This does not prove manual sleep/hibernation, lid actions or service recovery safe.

The unchanged supervisor source and prior actual child observations specify a 768 MiB private-commit cap, 60 seconds user CPU, five-second shutdown grace and one normal active child process. The parent validator and Edge are outside that child's private-commit cap; private commit is not working set. The E run wall budget remains 60 seconds and the harness bound 600 seconds. No new Job was created or existing unrelated Job queried. Disk space is not the present preflight blocker; RAM headroom is inadequate for another justified native-plus-Edge attempt under the observed conditions.

## Native failure classification from retained evidence

| Attempt | Established facts | Classification and limits |
|---|---|---|
| `20261112T074350827106+0800-experiments` | Worker event elapsed from creation to failure: 60.196151 seconds. Generation-zero checkpoint committed; then `GA_WORKER_TIME_BUDGET`. Child exits 0 and 137; active-process counts zero and both exits verified. Child user CPU 2.6875 / 9.828125 seconds; peak private commit 623,640,576 / 699,043,840 bytes. Command elapsed 158.095797 seconds; pytest 10 passed, 1 failed in 148.87 seconds. | The worker's own wall-time guard fired, not the 600-second harness timeout. CPU cap exhaustion and delayed cleanup are not supported by these observations. Exact startup/search/validation/paging contributions remain unresolved. |
| `20261112T080259124174+0800-experiments` | Same worker failure reason after generation zero; exits 0 / 137, active processes zero, both verified. User CPU 2.890625 / 5.875 seconds; peak private commit 622,841,856 / 661,479,424 bytes. Command elapsed 198.711630 seconds; pytest 10 passed, 1 failed in 191.54 seconds. | Worker wall-budget rejection is established. The retained diagnostic does not contain an exact per-worker elapsed timeline; command/pytest durations must not be called worker runtime. Host pressure is a plausible contributor, not a proven exclusive root cause. |
| `20261112T075704426168+0800-native-export` | Worker completed generation one; both children exited 0. The new test expected the first history generation to be one, but the original engine records zero and one. Command elapsed 100.444531 seconds; one failed test in 95.05 seconds. | Incorrect test expectation, already corrected in the existing F test. No GA/history change was needed. The failure occurred before full export acceptance, so it is not a passing JSON/CSV/text result. |

These were completion cases, not Stop-acknowledgement cases. No successful Stop assertion is inferred from them. Private RNG is newly generated per admission; retries reuse fictional fixture dimensions and limits, not identical private RNG state. A completed retry does not establish host reliability or deterministic replay. No independent reproductions were attempted in R1 because preflight stopped first. No worker limit, assertion, scoring rule or production source was changed.

## Verification still pending

The previous 79 selected backend passes, 425 frontend contracts, TypeScript/build/lint passes and finite no-worker handoff probe were reviewed as retained results, not rerun or counted as new R1 tests. Full native export acceptance, all 11 planned real Edge scenarios, F API reconstruction and fresh original 455.0/RNG-continuation qualification remain pending. No screenshots or passing browser results are fabricated. No production readiness follows from the preserved disposable evidence.

## Minimum operator action

1. Save work and close unused applications/browser tabs manually. Aim for at least **3 GiB available physical RAM** before the native-plus-Edge stack is reconsidered. This is a conservative preflight target, not a guarantee of success, an academic rule or a change to worker limits. The agent will remeasure before launch.
2. Arrange read-only access to `.pytest_cache` through its owner so its contents can be inventoried. Do not delete it or change permissions merely to make an audit pass. No broad privilege or automatic exclusion is assumed.

Optional read-only checks from the repository root in the operator's PowerShell terminal:

```powershell
(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
Get-ChildItem -LiteralPath '.pytest_cache' -Force -Recurse -File -ErrorAction Stop | Measure-Object
```

The first value is available GiB because the CIM property is KiB and PowerShell `1MB` is 1,048,576. The second inventories file count only; it changes nothing. An access error is a blocker, not evidence that the folder is empty. Do not paste credentials or private records into chat.

After both blockers are resolved, establish a strictly fail-closed full traversal, reproduce the two native cases independently with stage timing and owned-process diagnostics, requalify the corrected assertion, then execute actual exports and all 11 Edge scenarios. Preserve every old failure and record each new result separately. Do not increase limits or continue automatically to a later milestone.

## Inventory and safety state

This recovery creates six evidence-only files under `docs/testing/dashboard-u5pf/recovery-r1/`: `preservation-baseline.json`, `entry.json`, `resource-diagnostics.json`, this `README.md`, `manifest.json` and `staging-plan.json`. Combined F inventory: 51 new paths, zero existing tracked-file modifications attributable to F/R1. The new plan is an explicit proposal with `checkpoint_ready: false` and no staging authorization. It preserves the original 45-path plan unchanged.

Production admission and institutional Saved Best promotion remain **BLOCKED**. Institutional Continuous Optimization remains **DISABLED**. Active checkpoint restoration remains **BLOCKED**. Seven-day readiness remains **NO-GO**. Nothing is staged, committed, pushed or deployed. No institutional or PostgreSQL operation occurred.
