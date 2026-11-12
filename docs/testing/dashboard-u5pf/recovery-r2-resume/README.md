# U5P-F R2 continuation: RAM passed, backend cache access blocked

Reviewed 12 November 2026, Asia/Manila. **STOP before native acceptance. Checkpoint readiness remains NO-GO.** This addendum preserves the original F report, R1/R2 seals and all failed attempts. It does not replace their historical findings or restart implementation.

## Resource and cache findings

At 21:55:47 +08:00, available physical RAM was **4,176,592,896 bytes (3.89 GiB)**, exceeding the required 3 GiB. Total RAM was 15.71 GiB, memory load 75%, and free repository-volume disk space **110.48 GiB**. These are preflight point observations, not measurements of worker demand or proof of future headroom.

The root `.pytest_cache` is now readable without elevation: directory metadata, ACL and all five files were read. It is not a reparse point. Its ACL disables inheritance and grants inheritable FullControl to OWNER RIGHTS, SYSTEM and Administrators; its owner is the offline sandbox account. No ACL, ownership or system setting was changed. The restricted owner-based ACL is consistent with identity-dependent access, but the previous process identity and any intervening ACL transition are unverified. Therefore the historical denial's exact cause is not established.

Strict traversal then failed at a different exact path:

`C:\Users\User\Desktop\Genetic-Algorithm Dashboard\backend\.pytest_cache`

Python `os.walk(..., onerror=raise)` returned **PermissionError / WinError 5: Access is denied**. `Get-Item -Force` can inspect the directory and identifies no reparse point, but `Get-Acl` and `Get-ChildItem -Force` independently return **System.UnauthorizedAccessException**. All five known file reads also fail. Ownership, ACL entries and inheritance for this backend cache remain unavailable; no precise permission cause is invented.

The inability to inventory and hash this required directory blocks a complete fresh preservation baseline. It is not excluded, assumed empty or marked preserved. No administrator shortcut, cache deletion, ownership change, permission repair or process termination was attempted.

## Scoped preservation results

The separate read-only [review](review.json) checks the R1 known-file baseline and current Git state:

- 5,639 known paths checked: **5,634 byte hashes match, five are inaccessible, zero readable paths differ**.
- All 23 academic files match, including both protected JSON files. Original GA sources, settings, migrations, Saved Best, histories and checkpoints in the readable baseline match.
- All eight reconciled historical artifacts match their recorded current-state hashes. This does not establish earlier historical bytes or checkpoint recoverability, and no prior one-time exception is reused.
- All **54 artifact hashes** referenced by the R2 manifest match. Existing F/R1/R2 evidence is retained; the prior 55-path proposal is unchanged.
- `main` remains at `0dcc3e942d0b79c0e6358aa151208c014b307300`. The index is empty and its baseline hash matches. Git HEAD/config hashes also match.
- The original eleven tracked modifications retain their paths and matching local bytes; all 958 unrelated untracked paths retain their expected membership and readable-baseline bytes.
- Strict enumeration records the ignored directories observed before the access failure and the six dependency/build exclusions. That partial list is explicitly not complete historical-runtime coverage.

No full fresh baseline is claimed. The five inaccessible known paths are exactly `backend/.pytest_cache/.gitignore`, `CACHEDIR.TAG`, `README.md`, `v/cache/lastfailed` and `v/cache/nodeids`.

## Acceptance status and next action

**No new tests, native workers, export acceptance or Edge scenarios were executed.** All eleven planned Edge scenarios, the two independent native latency reproductions, corrected native completion/export qualification and fresh original 455.0/RNG parity remain pending. The existing 79 selected backend passes, 425 frontend contracts and TypeScript/build/lint passes remain historical. Neither former worker wall-budget failure nor the separate history-expectation failure is erased or reclassified as passing. The improved RAM measurement does not establish the root cause of the two 60-second failures.

The next operator action is to have the backend cache owner establish why the current execution context cannot read/list the directory and its ACL. Read-only inspection in the owner's existing terminal can use:

```powershell
Get-Item -LiteralPath 'backend\.pytest_cache' -Force
Get-Acl -LiteralPath 'backend\.pytest_cache' | Format-List Owner,AreAccessRulesProtected,AccessToString
Get-ChildItem -LiteralPath 'backend\.pytest_cache' -Force -Recurse -File -ErrorAction Stop | Measure-Object
```

Do not paste private account details or cache contents into chat. No permission change is authorized by these commands. If a change is required, it needs a separately reviewed, narrowly scoped authorization for read/list access; do not run broad repairs, take ownership, clear the cache or elevate automatically. Resume only after access is available, remeasure RAM and establish a strict complete baseline before any worker or browser launch.

## Exact new files and selective proposal

This continuation adds only six files under `docs/testing/dashboard-u5pf/recovery-r2-resume/`: `verify.py`, `preflight.json`, `review.json`, this `README.md`, `staging-plan.json` and `manifest.json`. `verify.py --record` uses exclusive file creation; a no-argument run is read-only. It imports no application modules and never launches tests, databases or workers.

The combined proposal is **61 new files, zero existing tracked-file changes attributable to F**. The new manifest records 60 artifact hashes; the plan records 59 raw Git blob proposals, excluding the two new seals to avoid circular identity. The plan remains unauthorized and not ready for staging. Nothing was staged, committed, pushed or deployed.

Production admission and institutional Saved Best promotion remain BLOCKED. Institutional Continuous Optimization remains DISABLED. Active checkpoint restoration remains BLOCKED. Seven-day experiment readiness remains NO-GO.
