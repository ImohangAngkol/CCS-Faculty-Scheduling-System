# U5P-D historical artifact coverage reconciliation

Investigated 2026-11-10, Asia/Manila. HEAD remains `3719af0734e395bf2b905a13ab6ccc1ca7dda5f9`, branch `main`, index empty and byte-identical to entry. No GA, frontend, protected runtime artifact, database or institutional source was changed by this task.

**Recommendation: eligible for a separately authorized checkpoint review with an explicitly disclosed preservation limitation. This is not full historical byte-preservation verification and is not staging/commit authorization.** If the owner requires a trustworthy pre-entry hash for every historical artifact, the checkpoint remains NO-GO under that stricter requirement. No missing hash can be reconstructed by rerunning tests.

## Root cause and preserved history

The original U5P-D baseline combined visible tracked/untracked paths with 122 ignored paths from earlier preservation references. It covered 5,121 paths but did not enumerate the complete current ignored runtime trees. One later, already-present run added eight paths outside the reused inventory. Their filesystem timestamps precede U5P-D entry, but timestamps alone neither authenticate their origin nor prove earlier bytes.

The full-directory guard correctly stopped on the omission. It was not an application failure. The original baseline, `preservation-coverage-gap.json`, failed-test evidence and original auditor remain untouched. Verbatim copies of the three documents updated by this task are retained here as `original-report.md`, `original-manifest.json` and `original-staging-plan.json`. Their hashes and prior Git blob identities are independently checked. The earlier blocked conclusion is not erased.

## Eight-file classification

All paths below belong to run namespace `e2049cdc-fa8d-460f-b505-195a1d30b07e`. This is a historical fixed-engine file association, not an authenticated person, department or institutional authority claim. Exact full paths, timestamps, sizes, ignore-rule lines, format information, raw hashes and evidence-search findings are in `investigation.json`. No schedule, receipt payload, faculty record or checkpoint contents are copied into this package.

Abbreviations: `G = backend/saved_chromosomes/generation_snapshots/e2049cdc-fa8d-460f-b505-195a1d30b07e/`; `S = backend/saved_chromosomes/stopped_runs/`; `C = backend/run_checkpoints/e2049cdc-fa8d-460f-b505-195a1d30b07e/`; `R = backend/run_input_receipts_v1/e2049cdc-fa8d-460f-b505-195a1d30b07e/`.

| Artifact | Size (bytes) | Current raw SHA-256 | Classification |
|---|---:|---|---|
| G + `analysis-cac1a8142c03384e30a6517bce0be80db1271d06cffe5007dd670a111c898fd3.json` | 30,693 | `ea51033169ff7360a8bacdd52ffbd4c26f66ca9f0c416827813a2feb3e6ceb3a` | CURRENT_STATE_PRESERVED_ONLY |
| G + `generation-000000.json` | 57,332 | `37241f4f9a6629ceb375647fbeb6a595953573766e9d1babe24317b587a41b69` | CURRENT_STATE_PRESERVED_ONLY |
| G + `index.json` | 1,798 | `8bd928aba03500ab859ed3d53eebec28f580e9878100d517f7be6c23b524433c` | CURRENT_STATE_PRESERVED_ONLY |
| S + `e2049cdc-fa8d-460f-b505-195a1d30b07e.json` | 29,729 | `b1a8a54a9d229e11e235d53e6786189fbb30a425ea95162938517aea7ddb6b48` | CURRENT_STATE_PRESERVED_ONLY |
| C + `checkpoint-0-cbf701c4-b71b-4940-8dc2-8a9a4001afb7.json.gz` | 3,242,039 | `c51852ea1f406af72dc895111e93e4edeb7bfe856752542898f1f65af513d944` | CURRENT_STATE_PRESERVED_ONLY |
| C + `status.json` | 2,438 | `ed927e40e642b868b97958bb04121eb025cee72aa4ac9eab37e99a82cbe03695` | CURRENT_STATE_PRESERVED_ONLY |
| R + `end.json` | 1,126 | `cd3545565862702afe13a35dd30e045026ca3e8eef3f01d7f578d55b2c9e4eb6` | CURRENT_STATE_PRESERVED_ONLY |
| R + `start.json` | 1,446 | `184692f17983df5af363ed55644021ff3dc7e4cbec1cceb04cae3890259a3aee` | CURRENT_STATE_PRESERVED_ONLY |

Creation/modification times reported by Windows span 2026-11-09 20:01:03 to 20:02:25 +08:00, preceding the entry baseline at 2026-11-10 07:51:40 +08:00. All eight are ignored and untracked: `.gitignore` lines 135 (stopped runs), 136 (generation snapshots), 137 (checkpoints), and 139 (loader receipts). They remain excluded from the proposed checkpoint.

## Earlier evidence search

- Searched 4,230 visible tracked/untracked text files, including 95 manifest-named files and 110 baseline-named files, excluding protected data/runtime payloads and the current U5P-D package from historical proof candidates.
- Searched all reachable relevant Git history for the run identity and eight current raw hashes, plus exact-path history. No matching commit or earlier evidence reference was found. No current artifact blob exists in the Git object database under its raw blob identity.
- Examined only safe JSON structure/association metadata and gzip format magic in the affected artifacts. Current embedded digests are not independently anchored historical inventories. Logical payload digests are not raw-file SHA-256 values and do not prove the wrapper file's prior bytes.
- The only earlier recorded raw hashes located are the original U5P-D coverage-gap observation, already after execution. All eight still match that observation. This proves stability since that recorded observation, not since pre-U5P-D entry.

No external backup, cloud history, OS write audit or unreachable arbitrary Git content is claimed to have been searched. The evidence source inventory is recorded in `investigation.json`; matching names, timestamps and unverified copied manifests were not accepted as prior-byte proof.

## Could U5P-D have written these artifacts?

The review covers 26 recorded command attempts and the referenced runner/fixture sources. The backend runner excludes data and runtime stores from the committed archive, rejects archive links, prepares an owned temporary source snapshot and invokes tests from its backend directory. Fictional loader files are created only after the bootstrap verifies the owned temporary-root marker. Research stores are separately created under private `ga-u5i-` temporary roots. Fixture database engines are explicitly allowlisted; institutional best/checkpoint persistence is blocked. Legacy continuation fixtures direct their saves to disposable snapshot/pytest paths.

The frontend runner copies only frontend source, redirects its dependency cache and uses intercepted HTTP or private fixture API URLs. The lint diagnostic uses the already-owned snapshot. The resource tool queries host state; the auditor reads hashes/text/PNG structures without importing application services. The optional handoff wrapper was not executed. No recorded command or reviewed call path resolves a write to the eight historical artifacts. The new reconciliation tool has no application imports, database calls, restore operation or Git write commands.

These findings provide **no evidence of a U5P-D modification**. They are not a complete operating-system file-access trace or a proof of all possible concurrent activity. No artifact is classified POSSIBLY_MODIFIED or CONFIRMED_MODIFIED; none is classified VERIFIED_UNCHANGED because trustworthy pre-entry hashes are absent. CURRENT_STATE_PRESERVED_ONLY is the explicit limited classification, not a replacement label for complete historical assurance.

## Eligibility and risk

The latest reconciliation task expressly permits consideration with disclosed uncertainty. No applicable AGENTS.md or separate rule requiring universal pre-entry hash proof was found. The original blocked report was a conservative response to missing coverage; it is retained and superseded only for the conditional checkpoint recommendation.

| Requirement | Finding |
|---|---|
| No evidence of U5P-D historical writes | Satisfied within the recorded/static investigation scope |
| Original baseline unchanged except intended source edits | 5,119 of 5,121 unchanged; the same two qualified research frontend files are the authorized differences |
| Eight current states recorded and stable | All match original gap hashes; verified again on final audit |
| Historical uncertainty disclosed | Explicit in this report, main report, updated manifest and staging plan |
| No POSSIBLY_MODIFIED / CONFIRMED_MODIFIED / UNKNOWN classification | All eight CURRENT_STATE_PRESERVED_ONLY |
| Application/test qualification retained | Original source/test/proof artifacts unchanged; prior test results reviewed, not rerun |
| Privacy, whitespace, Git integrity, artifact/blob hashes | Rechecked by the reconciliation audit before resealing and independently replayed |

No historical artifact is identified as damaged or at risk from a new write. However, undetected pre-observation replacement/corruption cannot be ruled out. No checkpoint was loaded or resumed, and checkpoint validity/recoverability is not established by a preservation hash. The eight paths are neither committed nor repaired. Production authority, Saved Best promotion, active restore, Continuous Optimization and seven-day execution remain blocked/disabled as before.

The original functional results remain **297 selected Python passes plus one unchanged historical assertion failure, 391 frontend contracts, nine real Edge/FastAPI/SQLite scenarios and 28 intercepted-HTTP browser scenarios**. TypeScript/build/focused lint results remain historical U5P-D passes. This task adds no fresh application-test passes and does not erase the timeout, encoding defect screenshots or frozen no-research-routes assertion failure. All application/test source bytes still match the qualified original package.

## Reproduction and evidence contract

Read-only final verification from the repository root:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pd/preservation-reconciliation/reconcile.py
```

The no-argument command checks the current seals, archived original documents, original baseline, exact protected membership (including the explicit eight), original 958 unrelated untracked paths, 11 original tracked modifications, prior 1,495 artifact references, qualified source/evidence hashes, privacy and Git integrity. It does not rerun GA/browser tests or write evidence. `--collect` and `--seal` are one-time completed preparation operations; do not rerun them or overwrite their evidence. The original `audit_evidence.py` remains historical and tied to the earlier blocked snapshot; use this additive verifier for the updated package.

The current `manifest.json` and `staging-plan.json` enumerate the exact expanded proposal, including this addendum, its tool, investigation record and three original document archives. Their own Git blob identities are verified separately after sealing, avoiding self-hash recursion. No staging has occurred. Current evidence eligibility does not authorize Git actions; a separately reviewed selective checkpoint is required.

## Future controls

1. Enumerate complete protected directories, including ignored paths, at entry rather than relying on an earlier path list. Record both membership and raw hashes before any imports/tests.
2. Keep inherited coverage and new observations distinct. Do not rewrite an old baseline to absorb later discoveries.
3. Recheck protected membership and bytes before every evidence seal and Git checkpoint. Stop on any new unreviewed path or changed digest.
4. Keep fixture storage outside the repository and reject unexpected resolved paths. Preserve explicit fictional-source guards, fixture-engine allowlists, finite resource limits and no-publication spies.
5. For stronger historical assurance, obtain separately authorized immutable pre-run inventories/backups or OS audit records. Do not create retrospective approval from timestamps or embedded hashes.

Recommended next action: review this disclosed limitation and updated selective inventory before separately authorizing a Git checkpoint. U5P-E remains a proposed bounded operator/storage qualification milestone, not started by this task.
