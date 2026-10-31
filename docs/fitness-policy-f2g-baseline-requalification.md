# F2G Git baseline requalification addendum

2026-11-01, Asia/Manila. **F2G research/content preservation is requalified against the verified current `main` state, with an existing documentation-whitespace warning.** This addendum resolves only the owner-confirmed Git transition. It does not change F2G's research results, approve production scoring or establish institutional readiness.

The repository owner explicitly confirmed that the concurrent commit was intentional and requested requalification. The [original blocked report](fitness-policy-f2g-optimization-evaluation.md), [original manifest](testing/fitness-policy-f2g/manifest.json), baseline, failed auditor, preservation-stop record and all intermediate failures remain byte-identical. They correctly describe the earlier stop. This separate addendum supersedes the Git-preservation blocker; it does not rewrite history or make the old raw-index comparison pass.

## Exact accepted Git transition

| Item | Previous baseline | Verified current state |
|---|---|---|
| HEAD | `4d9ee5b4a7d84ae9eb1194e5e5eeb131622a44d2` | `52d998a3c0eb50642424dca1b2a836c95ad68143` |
| Branch | `main` | `main` |
| Raw index SHA-256 | `04bbc3004021bfa9b3682cb6d64b099a59b49d90ab5b8683ccb0745780cfee0a` | `6c05dc5f8da3b1f2ed5a55e1ab214314ace8fa1b82cda46acd088f7af0ad92f7` |
| Staged changes | None | None |

The accepted commit has one parent, exactly the previous HEAD. Subject: `docs(research): record F2D-F2F experimental GA findings`; recorded commit date: 2026-10-31 23:47:41 +08:00. Its exact changes are three regular `100644` file additions:

1. `docs/fitness-policy-f2d-architecture.md`
2. `docs/fitness-policy-f2e-release-qualification.md`
3. `docs/fitness-policy-f2f-operator-integration.md`

Tree comparison verifies that every previously tracked path, mode and blob remains unchanged. The three reports were already included as untracked content in F2G's original byte baseline. Their committed blobs are **byte-identical** to those original working-tree bytes and SHA-256 hashes. Names and commit subject alone were not used as proof. The current index matches the current tree at stage zero, contains exactly three more entries than the parent tree, has no unusual assume-unchanged/skip-worktree flags, and has no pending staged changes.

The commit advances the `main` ref/resolved HEAD and its reflog history, references the new tree, and records the three added report entries in the index. The raw index therefore intentionally differs from the pre-commit index; it is not described as an unchanged cache. Exact tree/blob identities, entry counts and index-entry digest are in the [new baseline](testing/fitness-policy-f2g-requalification/baseline.json). No Git metadata was reset, restored, rewritten or staged during requalification.

## Preservation and immutable evidence

The new baseline layers the explicitly authorized Git state onto the preserved content:

- **2,075 original content paths:** all still match their original hashes, including all 23 academic data files, protected local preferences/settings, production GA/scoring/RNG, migrations, retained checkpoints, schedules and research evidence.
- **107 original F2G paths:** all preserved, including the old manifest itself; its 106 self-excluding artifact hashes verify.
- **One current index:** pinned to the accepted hash above, with current HEAD/tree/index consistency checked independently.
- **2,183 paths total** in the requalified baseline. The original 2,076-path baseline is neither replaced nor edited.

All **682 preceding artifact entries** also verify. The two protected local modifications remain exactly as supplied at F2G entry, unstaged and uncommitted. No application, academic or experimental engine file was changed by this task.

The 64-path F2F release/source set verifies. Current V1/V2 identities were also freshly recomputed using the exact read-only fingerprint function bodies extracted from their verified source, actual file bytes and installed Python/pandas/NumPy versions. No application/GA module execution, fingerprint replacement or fabricated version value was used.

| Identity | Verified unchanged |
|---|---|
| V1 | `5dccfbbad87eb42de4bc4fdac2c7a468d857b485e8d6b2149f1f29a43f2ef0b1` |
| V2 | `0821747e30eb56e9e4c070f369e733bc4b59ec184d2e2cb4c211ffa6fa5c1555` |
| F2F release | `ee72e369948d8511108bed3bba2b045f84c5649974be77170e0edb84c7eeeee7` |

## Recorded results reviewed, not rerun

| Evidence | Recorded result reverified |
|---|---:|
| Python tests: 14 + 178 + 90 + 33 + 23 + 4 | 342 passed |
| Frontend contracts | 42 passed |
| Main/control GA executions: 58 + 6 | 64 completed |
| Exhaustive fictional assignments: 4 + 64 + 256 + 4 | 328 |
| Instrumented/uninstrumented parity comparisons | 31 matched |
| Original F2G artifact hashes | 106 matched |

Command records, collected/outcome counts and stored summaries were reconciled. Fixed-geometry scores and minima, timing distributions, control outcomes and parity summaries were recomputed from saved numeric data. Four unsuccessful intermediate attempts and the original Git stop remain preserved. Successful execution is not equated with optimum attainment: the primary experimental cases improved in 6/12 timing trials; copy-frequency controls improved in 6/6 and reached the known optimum in 5/6. No result was promoted or hidden.

**Fresh GA runs: zero. Fresh backend/frontend tests: zero. Browser scenarios: zero.** The fresh work consists only of integrity, source identity, Git metadata, privacy and whitespace checks. It is not a rerun of the scheduling acceptance suite, and it gives no new institutional or PostgreSQL authorization.

## Whitespace and comparison-method qualification

Original F2G artifact text checks, current `git diff --check` and staged `git diff --cached --check` pass. A separate check of the owner commit range exits 2 with **198 trailing-whitespace warnings**, all in the F2F report's existing CR-CR-LF formatting. The committed file and preserved baseline are identical. No whitespace or line endings were repaired: the owner commit is not claimed to be whitespace-clean.

An initial comparison that transformed CRLF sequences before comparing blobs was an incorrect assumption for this already-identical F2F file. Direct raw-byte comparison, original hashes and Git canonical object hashes establish identity. The [entry record](testing/fitness-policy-f2g-requalification/entry-verification.json) preserves this explanation and the successful replay of the original blocked verifier before addendum files were created. This was a comparison-method issue, not an artifact content mismatch.

Privacy rescans cover original F2G artifacts and the new addendum, including complete/truncated encoded receipt patterns, credential URIs, private keys and sensitive logs/headers. Evidence contains fictional results, hashes and repository metadata; protected academic/preference contents were not printed or copied into reports.

## Current state and reproduction

Current branch is `main`; HEAD is the accepted commit above. Nothing is staged. The only tracked unstaged changes remain:

- `backend/data/faculty_preferences.json`
- `backend/data/ga_settings.json`

Existing untracked experimental packages and F2D-F2G evidence remain in place. The exact existing untracked paths are recorded in [verification.json](testing/fitness-policy-f2g-requalification/verification.json). This task creates only six separate files: this addendum and `verify_requalification.py`, `entry-verification.json`, `baseline.json`, `verification.json`, `manifest.json` under `docs/testing/fitness-policy-f2g-requalification/`.

Reproduce read-only verification from the repository root with the existing environment:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2g-requalification/verify_requalification.py --verify
```

The verifier fails closed on a changed HEAD, branch, accepted index, unexpected commit path/blob/mode, staged or unrelated unstaged changes, unexpected untracked path, protected content change, artifact/source fingerprint mismatch or changed saved result. It verifies the explicit transition rather than skipping Git or modifying the old auditor. `--create` is exclusive initial archive creation and must not overwrite an existing addendum. No baseline/audit bypass, Git reset/restore/checkout/clean, staging, commit, push, database operation or dependency installation occurred.

## Qualification and F2H recommendation

**F2G is now qualified for its completed, bounded fictional research and current-state preservation scope.** The existing F2F documentation-format warning remains disclosed; this is not an all-whitespace-clean repository declaration or a production-readiness claim.

**GO for a separately scoped, isolated F2H search-diversity qualification**, including initial-copy frequency, existing frozen fresh-candidate parameters, donor accessibility, larger cohorts and mixed components. **NO-GO for production scoring integration, institutional activation or unreviewed operator changes.** Keep exact policy identities, hard admission, source fingerprints and checkpoint/RNG guarantees. Production weight/overload composition, authoritative cohort integration, workload-exception authority and authorized positive-zero-target arithmetic remain unresolved. F2H was not started by this requalification.
