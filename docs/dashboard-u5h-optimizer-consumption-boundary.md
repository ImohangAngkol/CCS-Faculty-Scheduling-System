# U5H — verified consumption and versioned checkpoint binding

2026-11-05, Asia/Manila. Entry `main`: `d6db077793da52b7559351a5d0f8e6d54608cb77`.

**Implemented: a separate, synchronous internal fixed-run optimizer entry that actually consumes U5G bundle working copies, with technically verified consumption receipts and a new bundle-bound checkpoint envelope.** This is not a switch of the existing HTTP APIs. `/run`, `/stream`, their U5D UNVERIFIED observations, CURRENT classification and historical persistence remain unchanged. No continuous worker, institutional provider, Chair mandate or publication capability is activated.

The new boundary is `services.ga_bundle_optimizer.Session`. It is an explicitly versioned successor execution contract, `ga-bundle-consumer-v1`, using the original finite V1 function bodies and operations in private dependency environments. It does not claim the legacy engine fingerprint for changed effective behavior.

## Repository review and preservation

Reviewed U5D, U5E/R2, U5F and U5G reports, manifests and staging plans, actual engine/control/progress/receipt/bundle/checkpoint sources, operators, model constructors and validators. No AGENTS.md was found. These milestones are still uncommitted: inventories 24, 268, 80 and 34 respectively. Shared existing edits include the GA/evaluation routers, main, common test fixture and Generate/Analysis pages. U5H modifies none of those files.

The pre-edit baseline covers **3,653 paths**, all **23 academic files**, both protected JSON modifications, original GA/scoring/RNG sources, migrations, historical checkpoints/schedules, Saved Best, ignored runtime stores, existing evidence and Git index. All 33 U5G artifact hashes passed at entry. The final audit verifies every baseline byte with no intentional existing-file exceptions.

## Actual dependency and execution contract

Legacy V1 still follows:

```text
academic CSV/JSON and model defaults -> Functions cached graphs / preference frame
  -> ga_service global aliases -> initialization -> scoring / selection / swaps / mutation
  -> validation / generation monitoring -> checkpoint or best-ever finalization
  -> engine Saved Best write -> router latest/stopped result/history

FrozenInputs independently reads settings/preferences and copies Functions faculty
  -> context-local scoring; other calendar/model/global fallbacks remain independent
```

The new entry follows:

```text
server-held U5G immutable bytes + trusted run ID + explicit initial RNG state
  -> strict materialization / engine-loader identity / cohort-alias-profile validation
  -> private working graphs + private legacy preference frame + frozen scoring context
  -> versioned private dependency environment for original V1 code objects
  -> original initialization / fitness / selection / crossover / mutation / validation
  -> original finite generations and best-ever preservation
  -> in-memory result, technical receipt and optional new-version checkpoint bytes
```

| Dependency | Binding and enforcement |
|---|---|
| Subjects, sections, rooms, time blocks, faculty/eligibility/workloads | Explicitly materialized bundle graphs. Engine and Functions fallback aliases must refer to the same active working lists. Ambiguous resource IDs and inconsistent fallback aliases fail closed. |
| Scoring cohort | Must match optimizer faculty IDs and eligibility/workload profiles, and must not share mutable faculty instances with the working pool. The original zero-assignment cohort accounting and workload formula remain unchanged. |
| Preferences / fitness settings | Bundle scoring context is installed in the existing ContextVar. Original helpers and equations consume it. Its identity is checked throughout monitoring/finalization, not merely before execution. |
| Legacy DataFrame | Private materialized frame is passed into operations and bound to all fallback namespaces. Resume binds the decoded frame consistently with the restored active models. |
| Immutable resource metadata | Profile guards cover eligibility, fixed loads/limits, subjects/components, room identities/types, time grids, fixed section restrictions and declared external resources. Normal reservation/load/assignment bookkeeping stays mutable. Unauthorized profile/context/configuration changes abort without VERIFIED output. |
| RNG | A private `random.Random` has the same explicit initial state/algorithm. Original draws use that instance. Continuation restores its checkpoint state. The application's global RNG is neither reseeded nor consumed by the new path. |
| Seeds | Saved/uploaded modes use the captured seed payload, reconstructed and scored by the original code. They do not load application seed stores. Seed admission, constraint validation and fitness calculation are preserved. |
| Imported globals | No entire production namespace is inherited. Explicit model/frame aliases come from the bundle; mutable or scalar constants must be verified literal source declarations. Unknown data objects, DataFrames/arrays, unbound project modules/imports and unsupported RNG operations fail closed. Live input Path handles and builtin file opening reject use. |
| Models / libraries | Original passive model classes/methods are used, with loaded method identities in the new release fingerprint. Known scoring/observation ContextVars remain context-local. This is trusted Python dependency isolation, not a hostile-code security sandbox or process allocator isolation. |
| Progress and validation | Original generation metrics and hard-constraint/publication validators run. Callback data is copied and contains no working-model reference. Candidate validation, finite generation count, selection, crossover, mutation, scoring and best-ever ordering are unchanged. |
| Persistence | Historical Saved Best finalization is replaced only in the new private environment by a no-promotion result sink. New results/checkpoints are returned in memory; no latest/stopped/history/Saved Best store is written. Original persistence functions and APIs remain unchanged. |

### How the private dependency environment works

`ga_bundle_runtime.py` creates new function objects using the **unchanged original code objects**, with run-local globals, closure function dependencies and defaults. It does not edit bytecode or original files, replace production module symbols, modify `sys.modules`, monkeypatch a global scorer or install a tracing hook. Original nested functions inherit these private namespaces. Existing algorithm parameters/lists are passed through the original operations; global fallback names are explicitly bound to those same run-owned lists, rather than silently consulting cached modules.

Only the outer file-loading decorator is replaced by explicit bundle scoring scope; the original score-observation decorator is retained. The base progress monitor has private dependencies plus input-integrity checks. Lazy Functions imports expose only explicitly bound bundle aliases. Ordinary original model methods have no captured roster/file dependency; their loaded code/default identities are fingerprinted. Unsupported dependencies stop construction/execution rather than being treated as verified inputs.

The release identity combines the unchanged legacy **source-family** fingerprint, normalized loaded function bytecode/nested code identities, function defaults, loaded model method identities, and all three new adapter/checkpoint/session sources plus the U5G codec source. Only source filenames are normalized for cross-checkout code identity; runtime code is not rewritten. Changing loaded defaults or source contracts rejects restoration. Legacy fingerprints are never substituted for this new identity.

`dependency-closure.json` records the actually qualified function/method identity closure and private global names, without model values. Source and optimizer versions are explicit in receipts/checkpoints. All this instrumentation has functional overhead; no speedup, unchanged latency or bounded cancellation time is claimed.

## Receipt qualification

New contract: `ga-bundle-consumption-receipt-v1`. Its scope is **TECHNICAL_CONSUMPTION_OF_CAPTURED_BUNDLE_ONLY**. VERIFIED is possible only after actual execution reaches a validated completed generation/boundary and returns paused, completed or stopped successfully. Construction, restore-only, early cancellation without initialization, failure and interruption remain UNVERIFIED. Rejected repeated terminal Run calls preserve the preceding successful receipt.

Fields bind the run, immutable bundle, initial loaded representation, actual consumed-entry representation, configuration, frozen scoring context, initial/resumed RNG identity, loader/optimizer versions, loaded optimizer fingerprint and checkpoint tip/sequence/parent. The resume entry identity includes the restored working graph and legacy frame. Successful function-call counts are supporting diagnostics; merely counting calls is not the consumption proof. The proof also requires the closed bound environment, pinned data, integrity guards, original operation execution and differential tests.

**Academic source verification remains `UNVERIFIED_U5G_CAPTURE_ONLY`; institutional authorization remains NOT_ESTABLISHED; CURRENT eligibility, Saved Best promotion and publication are false.** A caller-provided source label/hash is not institutional authority. Existing U5D/U5G schemas and their UNVERIFIED-only behavior remain byte-identical; their legacy gate is not silently changed. They do not understand or automatically accept these new receipts. No new receipt is fed into Current Evaluation or the institution's approval workflow.

The new internal SDK receives a server-held bundle and run identifier. There is no HTTP input-bundle upload, public start route or user-configurable verification flag. Moving this contract into application endpoints requires a separately qualified server capture/admission boundary and scoped authorization; it is not implied by these tests.

## Versioned checkpoint and continuation

New contract: `ga-bundle-checkpoint-v1`. Canonical JSON bytes contain run ID, bundle fingerprint, optimizer version/fingerprint, configuration/scoring identities, generation, sequence, parent checkpoint hash and the original passive state graph. The graph includes population, best-ever/history, working/publication templates, legacy frame, frozen scoring context, monitor state and RNG.

Pause acknowledgment follows encoding, checksum/binding read-back and original hard validation of the decoded state. Restore requires the expected tip fingerprint, sequence and parent from **trusted server metadata**, in addition to the immutable bundle and run. Wrong/cross-run bundles, changed configuration/code/defaults, malformed/corrupted records, unsupported versions, invalid state and stale bytes against the trusted tip fail closed before RNG restoration.

The caller must retain the trusted tip/lineage pins separately. A checksum does not authenticate an attacker who can replace both the checkpoint and its trusted pin. This SDK does not implement a durable ownership/CAS registry, recover the latest tip by scanning disk, or accept client-chosen pins through HTTP. Those are required before worker/API activation. Size/node caps are format limits, not process-memory quotas.

Checkpoint bytes are returned in memory. Fresh-process tests persist fictional bytes only in the owned temporary test tree; application-level durable storage/recovery is **not implemented**. Existing checkpoint files are not rewritten, migrated, reinterpreted or searched. A legacy checkpoint is not silently adopted as a bundle checkpoint.

New-mode external source-file changes do not change active inputs or invalidate an identical pinned bundle continuation. This is an intentional new-version rule, **not a relaxation of V1**. Legacy V1 still enforces `GA_CHECKPOINT_INPUT_CHANGED`, its original engine fingerprint and source-drift behavior. Before any future institutional publication, independent authority/source freshness must be checked; technical continuation is not approval to publish.

Unordered primitive sets are normalized for identity comparisons only; working iteration order is not changed. Captured bundle bytes retain their observed representation. No general cross-Python-version or arbitrary hash-seed/large-dataset reproducibility guarantee is claimed beyond the qualified cases; incompatible release fingerprints reject restore.

## Validation and attribution

The [manifest](testing/dashboard-u5h/manifest.json) binds exact files, hashes, command attempts, qualified source snapshots and preservation. Final selected counts are recorded there; intermediate attempts remain separate. Independent snapshot roles may be rerun separately after changes affecting that role; auditors verify each role's actual source hashes rather than adding repeated executions as unique tests.

Final qualification includes:

**261 distinct Python cases, 210 frontend contracts and 16 browser scenarios passed in the final selected runs, with no final failures/errors/skips.** Repeated development and isolated rerun cases are not added to that distinct count. Historical failures below remain part of the evidence.

- **39 new consumption cases:** actual initialization/generations, best-ever ordering, exact resume RNG/schedule/history parity, same-session continuation and lineage, cross-run/bundle/version/hash/sequence rejection, corrupted/missing/legacy/stale checkpoints, global-cache/loader and real temporary preference/settings changes, concurrent private runs, interrupted/early-stopped execution, duplicate commands, coherent cohort/alias/resource identity, workspace/profile/context/configuration drift, pinned saved/uploaded seeds, forbidden globals/paths, loaded-default/loader version mismatch, lecture/laboratory rooms, fixed sections and preassigned external resources.
- **5 original-engine/process parity cases:** original versus new fixed generation 0/1, fresh injection 0/1, nonzero fictional preferences/weights, and fresh-Python checkpoint restoration. Differential assertions cover assignments, fitness, breakdown, history, faculty analysis and final RNG where applicable. Saved Best flags intentionally differ: the new version never promotes it.
- **10 unchanged legacy/copy-oracle cases** from U5G, including the three original current-release V1 real-checkpoint/RNG continuation cases. All existing source/fingerprint semantics remain.
- **32 U5G bundle cases**, **99 U5A–U5C compatibility cases**, **36 U5D receipt cases**, **20 U5E analysis cases**, **20 U5F readiness cases**.
- **210 frontend contracts**, TypeScript, production build, focused ESLint and **16 Edge scenarios** (Node reports 17 including the parent suite).

The independent backend source snapshots use HEAD, byte-identical U5G prerequisites and new U5H files; no U5D/U5E/U5F application dependency or institutional dataset is needed for the consumer/legacy/parity checks. Committed fictional bootstrap/release-byte-layout tools preserve the original strict engine checks. Explicit D10 models, fictional mixed-component/external-resource cases and a private initial RNG state are used. No production algorithm function is replaced to make a result pass.

The new consumer runs real Python GA code in-process. Checkpoint continuation includes reconstructed state and a fresh Python process. These are **not PostgreSQL acceptance, real institutional authorization, or browser-to-new-optimizer end-to-end evidence**. Edge exercises existing React/GAContext using intercepted fictional HTTP, confirming continuous execution remains blocked. No frontend/route changes are introduced by U5H.

The nonzero case matched fitness **455.0** and its exact component breakdown between original and new paths. It stores only aggregate fitness/breakdown and binding metadata; raw fictional bundles/checkpoints stay in OS-temp. Evidence does not claim convergence when initial fitness is zero. Runtime measurements in command records are test durations, not performance benchmarks. Fresh-process restoration is exercised at the initial validated checkpoint; next-generation and fresh-injection RNG parity are separately exercised in-process.

### Retained failures and limitations

The first new 15-case attempt had 14 passes and one failure: a pre-initialization Stop was rejected by the new session's state guard. The new entry now admits STOP_REQUESTED to the original cancellation boundary; it returns no result and no VERIFIED receipt. Subsequent 15-, 30- and 33-case development runs are historical, not added to final counts. Final 39-case qualification includes terminal-repeat receipt preservation and decoded checkpoint hard validation.

One unchanged U5D run reported 35 passes/1 failure in `test_distinct_thread_observations_are_isolated_not_a_concurrent_engine_claim`: `ga_input_receipt.directory` rejected a concurrent target path during its Windows resolve/junction checks. The isolated case then passed and the full 36-case suite passed on rerun. Its precise intermittent cause is **not established**; no U5D source or safety guard was changed or weakened. The initial failure/traceback is retained and remains a legacy regression warning to investigate before broader deployment.

Early copied runner scope strings described bundle capture only. The addendum in `attempt-notes.json` corrects their attribution: unchanged legacy APIs remain unverified, while those new tests executed the separate opt-in consumer. Counts/commands/outcomes are unchanged. No historical evidence is deleted or overwritten.

Existing Starlette/httpx and AnyIO deprecation warnings, Vite mixed-import/chunk warnings and Git dangling-object notices are retained. No dependencies were installed. Original faculty/room reset behavior remains exactly as before; this milestone does not resolve F4B's institutional availability-authority policy. Technical consumption is not certification of institutional data completeness or every academic policy.

## Preservation, inventory and checkpoint plan

**Existing files modified: none. All 3,653 baseline paths must match.** This includes both protected local JSON modifications, all academic data, GA/scoring/operator/RNG sources, V1/V2 compatibility code, migrations, retained checkpoints, schedules, Saved Best, U5D–U5G/research/unfinished UI work and Git index. No original data, legacy marker or runtime store was written by the new consumer.

New implementation/tests:

1. `backend/services/ga_bundle_runtime.py`
2. `backend/services/ga_bundle_checkpoint.py`
3. `backend/services/ga_bundle_optimizer.py`
4. `backend/tests/test_ga_bundle_optimizer.py`
5. `backend/tests/test_ga_bundle_parity.py`

New report: this file. New tooling/evidence: `docs/testing/dashboard-u5h/` (preservation/entry/source qualification, runner, snapshot verifier, audit, manifest, selective plan, attempt notes, command/protocol JSON and original screenshots). The manifest enumerates every literal new file. No raw institutional graph, preferences, checkpoint, session cookie or signed authentication receipt is archived. Hash, private-name/token/URL/header scans, PNG CRC/metadata checks and visual inspection cover the evidence.

The [selective plan](testing/dashboard-u5h/staging-plan.json) uses only new whole-file paths, with no partial staging. **U5G's uncommitted `ga_input_bundle.py` is a required source prerequisite**; its qualification tests are also prerequisites for the full snapshot tooling. Do not accidentally recommit or stage that baseline work as U5H. Commit/qualify prerequisites separately or obtain explicit approval for a combined exact inventory. SDK source qualification is independent of unfinished U5D/U5E/U5F application edits; their working-tree regression tests naturally require their files.

Checkpoint readiness is conditional on prerequisite ordering, review of the new internal execution scope and the retained intermittent U5D warning. Suggested messages: `feat(ga): bind fixed optimization to immutable run bundles` and `docs(testing): archive U5H consumption and checkpoint qualification`. No staging, commit, fetch, push, deployment or broad Git operation was performed.

## Reproduction

Use existing dependencies from the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5h/checkpoint_snapshot.py
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5h/run_checks.py backend-regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5h/run_checks.py receipts
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5h/run_checks.py analysis
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5h/run_checks.py backend
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5h/run_checks.py frontend
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5h/run_checks.py build
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5h/run_checks.py bundle
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5h/run_checks.py lint
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5h/run_checks.py browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5h/audit_evidence.py
```

The snapshot tool also accepts one qualification role: `consumption`, `parity`, `legacy` or `bundle-tests`. It uses a fresh owned temporary tree, strict original release byte checks and no database connection. The original-engine oracle skips outside that verified fictional tree; use this tool rather than running it against academic inputs. Child environments whitelist OS variables and exclude credentials/database URLs/authority activation. Reruns create new artifacts and require a separately versioned manifest addendum after sealing; never overwrite old evidence.

## Next milestone

Before a continuous worker, qualify server-owned atomic bundle capture/admission, explicit run/department authority, durable private bundle/checkpoint storage, trusted latest-tip CAS/ownership and publication-time source/authority revalidation. The synchronous SDK does not provide distributed ownership, durable restart discovery, resource budgets, storage quotas or institutional approval.

Then implement a bounded managed worker using this explicitly versioned contract: owned start/pause/resume/stop, cooperative safe points, shutdown/join/interruption handling, CPU/private-memory/wall-time/disk/history limits and run-local best-so-far persistence. Keep legacy routes and Saved Best protected until separate integration approval. Continuous Mode remains disabled; no subsequent worker milestone was started here.
