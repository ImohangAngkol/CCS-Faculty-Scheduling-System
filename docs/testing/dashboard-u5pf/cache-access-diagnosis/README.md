# U5P-F: targeted backend cache execution-context diagnosis

12 November 2026, Asia/Manila. **Acceptance preflight remains NOT QUALIFIED.** No pytest, native worker, Edge or database operation was launched. All earlier F/R1/R2 evidence remains unchanged.

## Actual identity and access

Read-only `whoami /user`, `/groups` and `/priv` identify the current execution account as **CodexSandboxOffline**, with **Medium** integrity, CodexSandboxUsers/Users membership and no Administrators group in the reported token groups. The only reported privilege is enabled SeChangeNotifyPrivilege. That privilege bypasses traverse checking; it does not supply file-read, directory-list or ACL-read access. Raw SIDs and machine-qualified account identifiers are omitted from saved evidence.

This is a different account from the repository owner's normal PowerShell identity. The owner's successful five-file reads, Medium integrity and deny-only Administrators membership are user-reported evidence, not an independently inspected external token. Medium integrity alone does not make two processes' discretionary access equivalent.

The exact target is `backend/.pytest_cache`, not the repository-root cache. Current results:

| Operation | Result |
|---|---|
| `Get-Item -Force` | Succeeds; directory, no reparse point reported. |
| `Get-Acl` | System.UnauthorizedAccessException: Attempted to perform an unauthorized operation. |
| Recursive `Get-ChildItem -Force -File` | System.UnauthorizedAccessException: access to the target path is denied. |
| Individual Python `open('rb')` for each known file | Five PermissionError failures, errno 13. |
| Strict attestation-tool traversal | PermissionError, WinError 5, exit 1; no file match claimed. |

The denial is **reproducible in the current Codex context**. Different identities plus the operator's external success support execution-context dependence. Repeated local failures do not support treating it as transient. The exact denying ACL entry or sandbox mechanism remains unresolved because target ACL/owner inspection is itself denied. The root cache's known ACL must not be substituted for this target's ACL. No automatic elevation, ownership change, permission repair, exclusion, deletion or cache write was used.

## Hashes and preservation

[probe.json](probe.json) contains complete expected SHA-256 hashes for all five files. The original pre-U5P-F baseline and R1 baseline agree on every expected value. **No current Codex hash was obtained**, so none of the five can currently be called a content match or preserved by this execution.

Fresh scoped checks verified all 60 artifact hashes referenced by the preceding R2-continuation manifest and 32 selected known-file hashes, including all 23 academic files, both protected JSON files and all eleven original tracked modifications. The index remains empty, `main`/HEAD remain `0dcc3e942d0b79c0e6358aa151208c014b307300`, and original eleven tracked/958 unrelated untracked path membership is unchanged. These are scoped checks, not a new complete baseline. The preceding 5,634 readable baseline matches remain historical results from the R2 continuation, not newly rerun full-audit results here.

Because direct cache reads still fail, the conditional full audit, complete ignored-runtime enumeration and native/export/browser acceptance were not attempted. No inaccessible content is silently substituted, marked preserved or excluded.

## Independently checkable owner attestation: proposed, not accepted

A cache-owner read-only measurement **could support** preservation verification without deleting or ignoring historical files. A mere statement that hashing succeeded is insufficient. It must provide actual current full hashes and exact recursive membership, bind to the trusted baseline and reviewed tool, and have an authenticated, explicitly accepted operator origin. It must also be refreshed at the relevant final preservation boundary; a point-in-time observation does not prove uninterrupted preservation or future state.

The new standalone tool pins the original baseline SHA-256 to `a301e0821f6d025e0ae39e8231051d6233665c4f5f4ff59255cb05c6a50ff04b`, verifies the five frozen expectations, rejects unexpected/missing files and directories or reparse links, compares two complete cache snapshots including file identity/size/mtime, and emits only safe metadata and full hashes. It writes no files and uses no application imports or extra dependencies. Its SHA-256 is recorded in the local diagnostic output and manifest. Two snapshots detect sampled changes; they are not a filesystem lock or proof against all concurrent modification.

Run from the repository root in the owner's existing normal, non-elevated PowerShell terminal:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pf/cache-access-diagnosis/attest_backend_cache.py --read-only
```

Expected successful status is `SCOPED_CACHE_CONTENT_MATCH` with all five complete actual/baseline hashes, exact membership and identical snapshots. **Success has not been observed here.** Codex's actual diagnostic invocation failed closed with PermissionError, as saved in `probe.json`. The external success path is not yet executed or qualified.

The JSON deliberately leaves `acceptance_preflight_qualified` and `full_preservation_audit` false and states that origin authentication requires separate verification. An unsigned JSON record or tool hash alone cannot authenticate execution, prove the account that ran it or give Codex direct read coverage. No attestation has been accepted and the direct-read requirement has not been silently relaxed.

Before using delegated evidence, the owner must explicitly approve that narrow evidence source and supply the actual complete machine-readable output from the reviewed tool. Its tool/baseline identities, exact membership, full matching hashes, origin and timing must be reviewed. All other required paths must still pass a fresh complete audit, with scoped owner measurements bound to that audit and final verification. If the existing preservation requirement demands direct Codex traversal, an external attestation cannot meet that requirement: access must be provided through an approved mechanism before continuation. No permission change is requested or performed by this tool.

## Inventory and status

Four new documentation/diagnostic files only: `attest_backend_cache.py`, `probe.json`, this `README.md` and `manifest.json`. The addendum manifest enumerates the combined 65-path proposal and excludes itself from its 64 artifact hashes. Earlier staging plans remain frozen historical proposals; nothing is authorized or ready for staging. No production functionality changed, and no tests are claimed as freshly passed.

Production admission remains BLOCKED. Institutional Continuous Optimization remains DISABLED. Institutional Saved Best promotion and active checkpoint restoration remain BLOCKED. Seven-day readiness remains NO-GO. No staging, commit, push or deployment occurred.
