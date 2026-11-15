# Scheduling-first Increment 2: run-bound minimum qualification

Inspected and implemented on 2026-11-15, Asia/Manila, on `wip/u5pf-experiment-exports` at `2315689196875621288939fde4a3268932305d8d`. **PARTIALLY IMPLEMENTED: the guarded adapter, isolated host, durable records and prototype page are implemented and non-native tests pass. Genuine supervised-worker execution and Edge acceptance are NOT RUN.** This is not a qualified milestone checkpoint or an institutionally authorized scheduling service.

The operator explicitly requested **“Keep native acceptance blocked.”** Initial available RAM was 0.85 GiB; the later recorded measurement was approximately 0.86 GiB, below the retained 3 GiB gate. No native worker or Edge was launched. The completed earlier investigation and Increment 1 were reused, not repeated. Their historical failures, U5P-F's unresolved 60-second worker failures and unauthenticated cache attestation remain intact.

## Implemented execution contract

The separate `routers.prototype_scheduling.create_app(service, identity_db)` wraps Increment 1's opt-in host. It includes its real cookie authentication, CSRF enforcement, scoped minimum configuration and isolated assets. Nothing is registered in ordinary `main.py`. An unconfigured host returns 503; role claims do not confer scoped execution rights. Only explicit fictional authority and a server-prepared immutable bundle are supported.

1. `MinimumRuns.context` exposes the trusted server scope, current minimum revision/digest, prepared bundle/configuration fingerprints and the existing operator's limits. `Submission` accepts only those selectors plus a request nonce; clients cannot submit a chromosome, fitness, authority, limits or arbitrary configuration.
2. `MinimumRuns.snapshot` requires the exact year, term, catalog, revision, digest and input/configuration identities. It captures the full immutable minimum document, eligible-capacity rows, individual minimum/soft-target/maximum distinction, original engine identity and scoring policy label in a new run record. No term or policy is inferred from filenames or timestamps.
3. Before dispatch, minimum > eligible units produces durable `INPUT_INFEASIBLE` with `MINIMUM_WORKLOAD_INFEASIBLE`, available units and the exact shortage. Faculty 2's fictional fixture gives **24 minimum − 12 eligible = 12 shortage**, zero original worker admissions and zero physical-process records. Joint feasibility is not established by passing individual capacity bounds.
4. Sufficient capacity proceeds only through the retained resource gate and unchanged `Operator.control(..., 'start')` → `ResearchBridge.admit` → trusted `Coordinator`/`CaptureAdapter` → `ResearchWorker` → Windows supervision → U5H bundle consumer → unchanged finite original engine. The adapter does not call the legacy HTTP generation endpoint, change admission of GA descendants, alter fitness, repair candidates or silently substitute a mock.
5. Original E limits remain two total worker generations and 60 seconds. The existing general 600-second ceiling remains unchanged; this increment does not raise any worker or test timeout. The fixture's prepared engine configuration remains separately fingerprinted rather than rewritten by the new adapter.
6. The actual admitted bundle is re-bound by the existing capture adapter to the server-generated worker run UUID. The run ledger checks its `prepared` link, configuration and nonce against the captured snapshot. It records both the prepared and admitted bundle fingerprints, actual optimizer identity and a hash of the original private initial RNG state. An admission link alone is labeled **worker admitted**, not proof that a child executed.
7. Status reconciliation never starts or resumes a worker. It can recover an existing original nonce mapping after a lost acknowledgement. Terminal candidate qualification requires the original operator's recorded cleanup, an exited supervisor, and `ResearchBridge.qualified_result`/`candidate`, including the original committed child proof, checkpoint and reconstruction checks. This exact native path is implemented but remains unexecuted in Increment 2.
8. The supplemental qualifier applies original `validate_publication`, reconstructs the candidate with authoritative fictional templates and counts teaching credit units once per normal GA-managed offering. Fixed external/preassigned offerings are excluded under Increment 1's explicit definition. It compares against the **captured** minimum revision, even if the policy head later changes. It preserves the candidate, exact original fitness (including zero), breakdown, history and generation count. No new score is substituted.

`input_fingerprint` retains the bundle's source-dataset fingerprint convention; for these fixtures it identifies empty fictional bootstrap source files. The **prepared bundle fingerprint** identifies the actual captured synthetic model graph/configuration; the **admitted bundle fingerprint** identifies the run-bound graph. Source-file fingerprints alone are not treated as consumption proof. The original child proof is required before a genuine result can be labeled technically consumed. No result is promoted to CURRENT or institutional authorization.

## Durable status and frontend

`prototype_run_store.RunStore` creates a **new** `executions.sqlite3` under the existing owned prototype policy root. It uses bounded append-only request/event records, SQLite transactions, synchronous FULL, immutable-row triggers, snapshot digests and an event hash chain. Existing policy tables, application databases and historical stores are not migrated or rewritten. This provides ordinary corruption detection; it is not a hostile-OS signature or institutional ledger.

The prototype page is `/prototype/scheduling`; its service is opt-in, not an ordinary production frontend route. It displays the server term/minimum revision, eligible capacity, original fitness, actual result schedule, per-faculty deficits, provenance and execution status. It distinguishes:

| Recorded state | Meaning |
|---|---|
| INPUT_INFEASIBLE | Proven individual eligible-unit shortage; no worker dispatch. |
| RESOURCE_BLOCKED | No dispatch; the RAM gate failed. |
| EXECUTION_REQUESTED / EXECUTION_UNCERTAIN | Request recorded; no execution/termination claim. |
| RUN_FAILED / INTERRUPTED | No qualified candidate; preserve failure/uncertainty. |
| CANDIDATE_CONSTRAINT_VIOLATING | Original-hard-valid candidate violates captured mandatory minima; not fully feasible. |
| CANDIDATE_FULLY_FEASIBLE | Candidate passes original hard validation and captured explicit minima, within this prototype's policy scope. |

The nonce is stored in the page URL before Start. A refresh can look up that nonce without repeating Start, including after a lost response. Busy actions are serialized, output uses text rendering, and a separate new request requires an explicit action after a recorded terminal result and refreshed context. No Pause, Resume, Restore, promotion or institutional approval controls exist here. These page behaviors have contract/static checks; they have **not** been exercised through Edge.

Terminal reads expose that current authority and the latest policy are **not rechecked for the stored terminal assessment**. Stored qualification refers to the captured policy, not permission for future publication. Fresh requests still require fresh explicit authority and an exact policy selector. Reconstructing a service instance against the same owned store is tested; independent OS-process restart/worker recovery acceptance is not established by those tests. Public metadata hashes the private initial RNG state; it does not contain enough information for an exact public replay. Private original worker checkpoints retain the existing continuation mechanism.

## Fresh validation and evidence

Final evidence and source identities are in [the manifest](testing/scheduling-first-increment-2/manifest.json) and [source qualification review](testing/scheduling-first-increment-2/source-qualification-review.json).

| Check | Result and scope |
|---|---|
| Final Python | **42 passed**, zero failures/skips: 19 new adapter/qualification tests, 18 Increment 1 regressions, 5 original-engine parity/continuation tests. 148.39 seconds reported by pytest. |
| Original GA parity | Fresh original-engine vs bundle-path assignment, fitness, history and final RNG equality at zero/one generations and fresh injection; checkpoint continuation and separate-process restoration remain passing in the five existing tests. No original source changed. |
| Final frontend | **32 passed**, zero failures/skips: 12 new contracts plus 20 existing workload/fitness-reporting contracts. |
| TypeScript / production build | PASS for the existing React application in an owned snapshot. Standalone `.mjs`/HTML assets are qualified by final contracts/lint, not by the React bundle. |
| Focused ESLint | PASS against final new standalone source/test bytes. |
| Native test source | Syntax checked; **NOT RUN**, as explicitly requested and required by the resource gate. |
| Edge scenarios | **NOT RUN**, resource/operator gate. No screenshots or browser passes fabricated. |
| PostgreSQL / migrations | NOT RUN; no database connection or operation. |

The two Python dependency deprecation warnings concern FastAPI/Starlette TestClient's httpx integration and AnyIO's BlockingPortal alias. No dependency was installed. The build retained dynamic/static import and chunk-size warnings. No repository-wide green-suite claim is made.

Acceptance coverage:

| Requirement | Evidence |
|---|---|
| A: 24 minimum, 12 eligible | Real server policy/store/admission gate; original dispatch is a failure spy. Zero worker/process rows verified. |
| B: 24 eligible, zero assigned | Manually arranged fictional candidate passes original hard validation and reports 24-unit deficit. Diagnostic, not generated. |
| C: 24 eligible, 24 assigned | Manually arranged fictional candidate passes original hard validation and reports zero deficit. Diagnostic, not generated. |
| D: unspecified minimum | Zero assigned faculty remains unconstrained by a new minimum; original soft target is not reinterpreted. Original GA parity also passes. |
| E: independent faculty/terms | Sparse individual minima; new term has its own empty revision chain; wrong scope/input selectors rejected. |
| F: changed policy head | Original captured revision remains bound and qualified; stale new submissions fail. |
| G: parity/continuation | Five genuine in-process original/bundle engine parity and checkpoint tests; these are not Windows child-worker acceptance. |
| H: authentication/authorization | Real FastAPI TestClient cookie sessions and disposable SQLite identity DB, CSRF checks, unscoped denial, cross-owner denial and extra-field rejection. No actual Edge/TCP browser claim. |

Additional diagnostic tests use **mocked lifecycle/proof boundaries** to verify durable failed/interrupted statuses and qualification serialization (including an injected exact zero fitness). Their mocked results are never exported as genuine optimizer observations. Actual server admission and capture binding are exercised without child execution. Malformed candidates, changed inputs, nonce reuse, event corruption and immutable-row protection are tested.

The first run passed 37 Python tests; the final run adds five diagnostic lifecycle/storage cases and passes 42. Frontend grew from 31 to 32 with a lost-ack/reload guard check. Both intermediate records are retained, not added together as independent final totals. There were no failed Increment 2 test attempts. The first new evidence-auditor invocation failed because it treated Git's automatic LF/CRLF conversion warnings as whitespace errors; the failure is separately retained. Its raw-byte whitespace subprocess was corrected to use `core.autocrlf=false` while retaining `cr-at-eol` checking. No application bytes were changed for that correction. Earlier milestone failures remain historical and unchanged. Final backend/frontend/lint source hashes match their recorded tested bytes. Earlier type/build snapshots differ in later test and standalone-asset additions only; those files are outside their TypeScript/React build scope. This is explicitly recorded rather than pretending all snapshot hashes are identical.

## Preservation and exact checkpoint proposal

All **5,703 readable baseline paths** match their entry SHA-256 values, including all **23 academic data files**, protected preferences/settings, original GA/operator/scoring/RNG sources, existing migrations, Saved Best, historical schedules/checkpoints and all prior readable evidence. Increment 1's **28 artifact hashes** still match. The original 11 tracked modifications and 1,001 entry-untracked files are preserved (958 unrelated + 14 investigation + 29 Increment 1). HEAD, branch, Git index and config remain unchanged. No file was staged, committed, pushed, restored, reset or deleted.

`backend/.pytest_cache` remains inaccessible to this execution context. Its owner attestation remains unauthenticated WIP evidence. **Full preservation qualification remains UNRESOLVED.** No U5P-D exception is reused; no assertion of full historical checkpoint recoverability is made. The current increment does not repair or qualify U5P-F. Read-only process inventory through CIM was denied; no process was terminated and no process-ownership assurance is inferred from that failed query.

No existing repository file was edited. Exact new paths, artifact SHA-256 values and prospective raw Git blob identities are enumerated in the manifest. [The selective staging proposal](testing/scheduling-first-increment-2/staging-plan.json) is informational only: **staging is not authorized and checkpoint readiness is NO-GO** while native/browser acceptance and full preservation remain unresolved. It excludes the original 11 tracked changes, all unrelated work, protected data and all prior milestone paths. Newly generated evidence contains fictional inputs, public statuses and hashes; no private RNG state, receipt signatures, passwords, cookies or institutional faculty rows are exported.

Application/test files created:

- `backend/routers/prototype_scheduling.py`
- `backend/services/prototype_scheduling.py`
- `backend/services/prototype_run_store.py`
- `backend/tests/test_prototype_scheduling.py`
- `backend/tests/test_prototype_scheduling_native.py`
- `frontend/src/prototypeScheduling/index.html`
- `frontend/src/prototypeScheduling/console.mjs`
- `frontend/src/prototypeScheduling/model.mjs`
- `frontend/tests/prototypeScheduling.test.mjs`

The other new paths are this report and the increment's isolated runner, auditor, baseline, command records and reconciliation metadata under `docs/testing/scheduling-first-increment-2/`. The manifest is the exact inventory, including unsuccessful/intermediate evidence where applicable, and excludes itself from its artifact hash map.

## Reproduction and Increment 3

From the repository root in PowerShell, these commands create fresh owned empty-import source snapshots with fictional bundles/private SQLite. They do not use protected academic inputs or existing application stores:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/scheduling-first-increment-2/run_checks.py backend frontend types build lint
.\.venv\Scripts\python.exe -B docs/testing/scheduling-first-increment-2/audit_evidence.py
```

The manifest freezes this completed evidence set; later reruns produce additional command records and require a new evidence addendum/requalification rather than silently rewriting the frozen inventory. Do not use `--create` against an existing manifest.

**Not authorized/executed in this session:** after a separately agreed resource requalification, at least 3 GiB available RAM and resolved preservation gate, the prepared native selector is:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/scheduling-first-increment-2/run_checks.py native
```

It retains the original 60-second E worker limit and original 90-second outer supervisor join; it fails, rather than substitutes a mock, when the gate or original worker fails. It should not be launched while the operator's current block remains in force. Edge acceptance still requires a separately qualified real-browser test harness; no Edge implementation/pass is implied by this command.

Recommended Increment 3: resolve the preservation attestation origin requirement, establish resource headroom, run the genuine worker test once and investigate any original timeout without raising limits, then exercise the actual prototype page/refresh/nonce recovery in Edge. Independently verify process restart persistence and real candidate qualification against durable observations before claiming a complete repeatable workflow.

If search-time enforcement is desired later, it requires a separately reviewed design: jointly constrained initialization/admission/retry or another explicitly versioned constraint mode changes the search trajectory. It cannot be introduced as a hidden fitness term or operator edit. The present unchanged GA may return a hard-valid candidate that violates the new mandatory minimum; it is preserved and labeled not fully feasible. Individual capacity does not prove joint feasibility, and bounded search exhaustion is not mathematical infeasibility.

Production admission **BLOCKED**; institutional Saved Best promotion **BLOCKED**; institutional Continuous Optimization **DISABLED**; active institutional restore **BLOCKED**; seven-day readiness **NO-GO**. No institutional approval, migration, deployment, dependency installation, Git checkpoint or optimization-policy activation occurred.
