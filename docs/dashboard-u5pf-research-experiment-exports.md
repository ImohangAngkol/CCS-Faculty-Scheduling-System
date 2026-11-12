# U5P-F — Fictional research experiments and evidence exports

**Status: PARTIAL — native/export and browser qualification BLOCKED. Not ready for a complete U5P-F Git checkpoint.** U5P-F adds an opt-in experiment page and bounded read-only evidence exports over the existing fictional research bridge. It does not register a provider or execution route in ordinary `main.py`. Production admission and institutional Saved Best promotion remain **BLOCKED**; institutional Continuous Optimization remains **DISABLED**; active checkpoint restoration remains **BLOCKED**; seven-day readiness remains **NO-GO**.

The baseline is U5P-E commit `0dcc3e942d0b79c0e6358aa151208c014b307300` on `main`. All U5P-F application and tooling paths are new. The eleven existing tracked modifications and 958 unrelated untracked files remain excluded from this milestone.

## Existing path and new boundary

The unchanged execution path is authenticated session → independently scoped E operator → B admission and signed context → H bundle consumer → K bounded supervisor → L creation-bound Windows Job process → durable checkpoints and signed observations. E still owns the only Start/Stop routes, request idempotency, CSRF checks, ownership checks, uncertainty inspection and cooperative Stop. A Stop acknowledgement is never reported as worker termination.

The new factory in `backend/routers/research_experiments.py` composes that opt-in host. It adds three GET route patterns for context, run projection and format-specific exports. Its `/research/experiments` page reuses E's HTML/controller and C/D observation services, with a separate F panel. The history link opens the existing authenticated read-only run-detail projection. This does not mount the main React ResearchConsole inside the isolated host or add operational controls to its four GET-only routes.

The context selector acknowledges the single server-bound fictional permit. It cannot submit a new scope, dataset, configuration or authority. No client-selected label becomes trusted input. Ordinary application login/Administrator status does not establish the independent research mandate.

## Durable experiment identity and verification

`ga_research_experiments.Experiments` derives a UUIDv5 from its explicit schema namespace, the owned store identity and the admitted run UUID. This is a durable projection of existing ledger-backed identity; it is not a new database record or institutional identifier. Reconstructing the factory against the same owned store must preserve the experiment identity and canonical record hash.

Pending runs expose recorded checkpoint generation metadata with its limited classification, freshness and runtime state. They expose no reconstructed fitness result. A terminal export additionally requires released ownership, independently verified physical cleanup, no live supervisor, the final signed observation matching the latest worker event, the original observer's full result verification and every committed consumption proof. Proofs must match run, bundle, configuration, scoring context, optimizer, inner checkpoint fingerprint and sequence. Corrupt, missing, stale or cross-owner evidence fails closed.

The record contains fictional year/term/dataset/catalog and department UUID; context, bundle, dataset, engine, optimizer, scoring/configuration and storage-policy fingerprints; original effective fitness settings; run and physical-resource limits; admission/terminal timestamps; completed generations; original generation history; committed checkpoint observations; available soft penalties; lifecycle and termination reason. The timestamp difference includes admission, search, validation and I/O and is not optimizer-only benchmark time.

The server generates private initial RNG state. The bundle's `seed` represents a schedule baseline, not a public numeric random seed. Exports omit both private RNG state and chromosome/checkpoint payloads and explicitly do not establish exact seed replay. This milestone does not claim a statistically meaningful performance or convergence evaluation.

## Exports and metric semantics

JSON is bounded at 256 KiB; CSV and plain text are bounded at 128 KiB each. Every download revalidates authorization and evidence, uses `Cache-Control: no-store`, `nosniff` and a UUID-only attachment filename, and writes no export into the research store. There is no PDF dependency. CSV exports numeric observations and validated scalar provenance, with separate `checkpoint` and `generation` series. It does not interpolate missing observations. The original engine records generation zero as well as completed generations; a generation-zero consumption proof supplies initial fitness only when actually present.

Observed, derived and unavailable values are explicit. Minimization improvement is `initial - final best` only within the bound run/context. Exact zero is preserved. Percentage improvement is unavailable for zero or negative initial fitness and for invalid/non-finite operands. Original soft-penalty breakdowns are not described as hard-conflict counts. Preference satisfaction and explicit hard-conflict counters remain unavailable because this path does not record those metrics. An offline standard-library verifier checks JSON content hashes and CSV/text consistency; that check establishes content consistency, not institutional authority or exact replay.

The UI renders imported/server text with `textContent`, uses finite GET timeouts, removes export links when verification fails, offers an independent refresh, rejects stale responses and does not store credentials. The original E controller continues to distinguish connection state, Stop requested and independently verified terminal state.

## Validation status

Final successful selections are **79 backend tests** and **425 frontend contracts**. They are not a claim that the complete workflow passed. Exact commands, timestamps, source hashes and outcomes remain in the evidence directories and `qualification-summary.json`.

| Selection | Fresh result | Evidence and limits |
|---|---|---|
| F offline | 11 passed, 1 native case deselected | `20261112T081053658493+0800-offline`; pure metrics, independently mocked formatter, actual in-process ASGI/session/private-SQLite authorization, pending/missing/stale evidence. No real network or successful native export claimed. |
| D continuity | 32 passed | `20261112T081236134550+0800-continuity`; includes existing native completion/interruption cases under their original regression bounds, not E's 60-second demonstration budget. |
| D/M receipt regressions | 36 passed | `20261112T081936128911+0800-receipts`; original guard/concurrency cases. Earlier historical failed attempts remain unchanged. |
| Frontend contracts | 425 passed | Final `20261112T074053406140+0800-contracts-all`: 417 committed contracts plus eight F contracts. Earlier duplicate contract runs are retained but not added to this count. |
| TypeScript / production bundle / focused ESLint | PASS / PASS / PASS | `20261112T074110173986+0800-build`, `20261112T074128993786+0800-bundle`, `20261112T074131804238+0800-lint`. Build/TSC check the committed React application; standalone F JavaScript is additionally covered by contracts/lint, not a fabricated React integration. |
| Finite handoff probe | PASS | `20261112T082543652212+0800-handoff-probe`: host lifecycle, owned worker quiescence and private-login-file removal. No Start, Edge or human handoff. |
| Complete F native/export acceptance | NOT PASSED | Three attempts below. One generation completed in the second attempt, but the assertion failed before JSON/CSV/text round-trip acceptance. The final corrected completion/export case remains unqualified. |
| F real Edge / HTTP / SQLite workflow | NOT RUN — 11 scenarios planned | The queued live selection was never reached after the failed focused test. No screenshots, browser cleanup or real HTTP export evidence is fabricated. F API-listener reconstruction is also not executed. |
| Fresh F original 455.0/parity, legacy continuation, operator and physical suites | NOT RUN | The queued sequence stopped on the focused failure. Existing E proofs and original sources are byte-preserved, historical evidence; they are not fresh F passes. |

The independent serializer unit test injects a mock `view` and is explicitly not consumption or authorization evidence. Its temporary exports never enter the research ledger or archived worker evidence. It verifies all three formats, exact zero, each size cap, content hashes and tamper rejection without pretending a worker produced its input. The native test still requires real generation-one completion, all format round-trips, unchanged store bytes, cross-owner denial, size rejection and signed-proof corruption rejection; that assertion was not relaxed to accept generation zero or `RESOURCE_LIMITED`.

Two existing dependency warnings (Starlette/httpx TestClient and anyio BlockingPortal deprecations) are retained. No dependencies were installed. Final RAM observation after all test subprocesses finished was 93% memory load with about 1.06 GiB available. Additional F native/Edge retries were deferred; no worker ceiling was raised and no unrelated process was stopped.

Retained intermediate attempts:

| Record | Actual outcome | Attribution |
|---|---|---|
| `20261112T074350827106+0800-experiments` | 10 passed, 1 failed | Native generation budget expired after the generation-zero checkpoint. The original worker recorded `GA_WORKER_TIME_BUDGET`; the public projection correctly reported `RESOURCE_LIMITED`. Both child exits were verified. CPU was below its cap; the evidence does not isolate the cause of elapsed-time pressure. No limit was raised. |
| `20261112T075704426168+0800-native-export` | 1 failed | The unchanged-limit worker completed generation one and both children exited successfully. The test incorrectly expected the original generation history to begin at one; the actual original history begins at zero. Only the new test expectation and new report wording were corrected. This record remains a failed test, not a passing export-acceptance result. |
| `20261112T080259124174+0800-experiments` | 10 passed, 1 failed | The corrected history expectation was not reached because the unchanged 60-second worker budget again expired after generation zero. Both child exits were verified. The queued browser/operator/parity/legacy checks were not executed after this failure. Subsequent formatter coverage was added independently; the native completion assertion was not weakened. |

The second run proves that the first timeout was not an inevitable fixture incompatibility. It does not establish resource reliability or erase the first failure. The new diagnostics retain public lifecycle/physical-exit facts without bundles, RNG state, signed receipt values or authentication artifacts.

## Preservation boundary

Before write-capable tests, a fresh full traversal captured 5,594 paths including all 23 academic files, 295 ignored files and raw Git index/HEAD/config identities. Dependency/environment trees, Git object storage and `frontend/dist` are excluded by the recorded rule. Historical runtime trees, Saved Best, fixed-engine checkpoints, receipt/index artifacts, Python bytecode and historical frontend cache images are included conservatively. `entry.json` enumerates ignored files; `ignored-runtime-inventory.json` separately lists their containing directories and historical runtime roots against that immutable entry. The final audit verifies complete membership as well as byte hashes.

The eight U5P-D historical artifacts matched reconciliation hashes at entry. Their present preservation does not retroactively establish earlier historical bytes or checkpoint recoverability, and U5P-D's one-time exception is not reused. All 1,793 prior artifact references must still verify, using the original authorized U5P-C commit for its three legitimately superseded source references. No existing evidence is rewritten. PostgreSQL is never contacted; D15 evidence is byte-checked, not rerun, and no database-state inspection is claimed.

The final auditor seals evidence only after every baseline byte hash, complete workspace membership, prior artifact reference, privacy scan, whitespace check and Git integrity check passes. It preserves raw index/HEAD/config identity and the exact eleven tracked/958 untracked exclusions. A successful preservation seal does not change the partial functional qualification into a pass.

## Exact inventory and selective checkpoint proposal

The current U5P-F inventory is **45 new files, zero existing-file modifications**: nine Python, four JavaScript modules/tests, one HTML panel, two Markdown documents and 29 JSON files. There are no F screenshots because F browser acceptance was not executed. `staging-plan.json` enumerates every literal path, exclusions and raw blob proposals; `manifest.json` contains 44 artifact SHA-256 hashes and excludes itself. The plan's blob table excludes the two seal files to avoid circular identities; their raw blobs must be calculated independently at any later checkpoint. No paths are staged.

New application/test files:

- `backend/services/ga_research_experiments.py`
- `backend/routers/research_experiments.py`
- `backend/tests/test_research_experiments.py`
- `backend/tests/test_research_experiments_live.py`
- `frontend/src/researchExperiments/panel.html`
- `frontend/src/researchExperiments/console.mjs`
- `frontend/src/researchExperiments/model.mjs`
- `frontend/tests/researchExperiments.test.mjs`
- `frontend/tests/researchExperiments.live.mjs`

New tooling under `docs/testing/dashboard-u5pf/`: `run_checks.py`, `frontend_checks.py`, `serve_experiment.py`, `verify_export.py` and `audit_evidence.py`. The remaining files are this report, the preimplementation workflow contract, entry/baseline and ignored-runtime inventories, resource/failure/preservation reviews, timestamped command/worker evidence, qualification summary and two seals. The full 45-path list is the authority for review; do not stage the directory wholesale.

**Checkpoint recommendation: NO-GO for a complete U5P-F checkpoint.** The selective list is a proposal, not staging authorization or approval of unexecuted live code. Finish native/export and browser acceptance first. After separate owner authorization and updated evidence review, use only literal reviewed paths with `core.autocrlf=false`; exclude all eleven original tracked modifications and all 958 original untracked files. No partial-index patch is necessary because F modifies no existing tracked file. Suggested eventual message: `feat(ga): add fictional experiment evidence exports (U5P-F)`.

## Resource and handoff limits

The existing E envelope remains two total generations, one generation per batch and 60 seconds of run wall time. The general K contract's 600-second ceiling is unchanged. Defaults bound each checkpoint to 8 MiB, retain eight checkpoints, bound a run to 64 MiB and admit one active worker. The isolated store has its own byte/run/retention limits; these are not a host-wide disk quota or an automatic cleanup authorization. Export caps are additional read-response bounds, not changes to worker limits. Signed telemetry and original generation histories retain their existing caps; F also rejects more than 256 observation entries instead of silently dropping them.

Actual child observations record a 768 MiB private-commit limit, 60 seconds of user CPU and five-second shutdown grace. Neither working set nor total host RAM is bounded by the private-commit setting. Admission acknowledgement, parent validation and export reconstruction can remain slow under host pressure. Cooperative Stop latency includes the worker's current safe boundary; it is not a promise of immediate termination.

The host initially had about 821 MiB available RAM. After the operator freed applications, the read-only point observation recorded 2,064 MiB available and 87% memory load. Both AC/DC idle sleep and idle hibernation indices were zero at inspection. No power configuration or unrelated process was changed. These observations do not qualify manual sleep, lid actions, updates, loss of power, process failover or continuous service safety. Native wall-time failures remain evidence even if later unchanged-limit trials pass.

## Reproduction and finite handoff

From the repository root in PowerShell, with the existing dependencies only:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pf/run_checks.py experiments
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pf/run_checks.py live
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pf/run_checks.py operator parity legacy continuity receipts handoff-probe
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pf/frontend_checks.py contracts-all build bundle lint
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pf/audit_evidence.py
```

The runners create new owned disposable snapshots, empty fictional import inputs, isolated SQLite/authentication stores and timestamped sanitized evidence. They do not execute against repository datasets or application stores. Repeated qualification creates new artifacts and requires a separately reviewed seal; do not silently rewrite the manifest.

Optional finite operator handoff: `run_checks.py handoff`. The private terminal displays the local page URL and the path of an ACL-protected login file outside the repository. Never paste or archive its password. Review the one fictional context, select it, Start once, inspect an uncertain request instead of repeating it, observe actual state, request cooperative Stop if needed, wait for verified exit, and download JSON/CSV/text. The host expires after five minutes and checks owned-worker shutdown; normal completion removes the private login file. Do not change its limits, register it in ordinary `main.py` or point it at an existing database. An automated two-second no-worker probe is distinct from a human handoff.

## Remaining blockers and proposed U5P-G

Genuine institutional authority, production input trust, deployment identity/storage, host-wide resource admission, multi-process service operation and active recovery remain unqualified. Public export hashes detect content changes; they are not independently signed institutional attestations. A technical tiny-fixture demonstration cannot establish scheduling-quality generalization or host-wide resource safety.

First resume the incomplete F native/export and live selections under improved host headroom; if the unchanged-limit timeout persists, investigate stage timing rather than weakening the assertion or raising the ceiling. Then run the remaining relevant original 455.0/parity, operator, legacy continuation and physical regressions. Preserve all failed records and add separately reviewed new qualification evidence instead of silently rewriting this partial seal.

Only after F is qualified, recommended U5P-G is a separately authorized reliability qualification of acknowledgement latency, native batch duration and resource-pressure sensitivity, followed by a finite independent operator handoff. Retain unchanged worker ceilings and truthful failure states. Define operational escalation and deployment ownership before considering longer execution. No U5P-G work, deployment, active restore or seven-day experiment is part of U5P-F.
