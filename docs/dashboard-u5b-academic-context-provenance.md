# U5B: academic context provenance and version-aware evaluation

2026-11-04, Asia/Manila. Entry `main`: `2db42c396c6418e722555269354921f178628868` (U5A). **The safe implementation is complete and verified with fictional contexts; genuine institutional activation remains BLOCKED.** The server context provider is deliberately unconfigured. No institutional academic year, semester, department or dataset was invented or installed. The [manifest](testing/dashboard-u5b/manifest.json) contains exact paths, hashes, attempts, limits and preservation findings.

## Investigation and implementation plan

Before editing, inspected U5A, the execution/admission/finalization paths, monitoring/configuration/input fingerprints, checkpoints, history, Saved Best, authorization and academic models/adapters. The concise plan was presented before implementation: a strict server verification boundary; immutable separate run-start records for verified fresh V1 runs; a version-two projection; existing-panel provenance presentation; and fictional tests with owned stores. No migration or Saved Best rewrite was proposed as an implicit part of U5B.

Existing academic models provide `AcademicScope`, `AcademicYear` and `AcademicTerm`, including scoped UUID relationships, calendar status and lifecycle. The opt-in academic adapter compares explicit identities but is not an authoritative live GA term selector. Existing rows/models alone do not prove dataset stewardship or approval. No database was queried to discover or invent an active term.

V1 loads the first-semester subject CSV and consolidated section schedules through `Functions.py`. The actual subject CSV columns describe course code/title, units, weekly lecture/laboratory hours and, in the first-semester file, year level. The GEC/consolidated files have Year Level, Section, Course Number and Schedule. **Year level is not academic year**, and these files do not supply authoritative academic year, term UUID, department scope or dataset revision. Filename labels cannot establish those facts. No individual academic or faculty rows are reproduced here.

V1's existing full-input fingerprint hashes all active CSV/JSON bytes; the engine fingerprint includes GA/scoring/validation sources and supported runtime/dependency identity. History captures those fingerprints, configuration and scoring context but lacked independently verified run-start academic provenance. V2 already has a separate term/catalog/constraint contract and an unconfigured institutional deployment provider; U5B does not repurpose its publication authority for V1 context verification.

## Implemented contracts

`AcademicContext` is a frozen, strict, extra-field-rejecting server DTO with:

- Explicit academic year and term labels and canonical recorded year/term UUIDs.
- Canonical scope UUID and department/scheduling-scope label.
- Authoritative dataset ID/revision and exact input fingerprint.
- Explicit context schema version and deterministic context SHA-256.

`ContextVerification` binds that context to a nonsecret verification reference and timezone-aware issued/expiry instants. The server revalidates even constructed/copied model instances, rejects malformed/future/expired assertions and mismatched inputs, and never accepts a dictionary or HTTP query value as verification.

`ga_academic_context.verification_for` is a **server-owned integration point returning None in production**. There is no environment approval flag, context-entry endpoint, client override or generic administrator/Chair grant. Implementing a genuine provider requires separate approval of the source, stewardship and lifecycle checks. A correctly shaped DTO is not institutional evidence by itself. Fictional providers are installed only by scoped test monkeypatches.

The separate `ga-run-start-provenance-v1` record captures context plus:

- Server run UUID and established start time, capture time and original verification reference/window.
- Existing V1 engine family/version/fingerprint, scorer hash and preference policy version, constraint-implementation identity, input and result-schema identities.
- The actual fresh-run execution configuration, including existing function defaults obtained from its signature.
- The exact configuration fingerprint used by `GenerationMonitor.register_baseline(None)`; no scoring equation or baseline conversion is duplicated.

No weights, workload allowances or faculty values are copied into this new public context record. Dataset identity comes from the verifier, not a filename-derived label. Configuration/engine provenance is supplied by the server, not by academic context submitted by a client.

## Lifecycle and persistence boundaries

The existing `_execute_with_history` wrapper now invokes provenance capture after normal input validation and before history initialization/GA search. This covers the existing `/api/ga/run` and `/api/ga/stream` execution path. It does not change the algorithm, population, operator, fitness, hard-gate or best-ever implementation.

With **no verified provider**, no provenance directory/file is created. Existing legacy execution is preserved, but the run cannot become CURRENT. This is rejection from verified evaluation, not an invented new requirement that all legacy optimization must stop. With a configured **invalid or changing provider**, the wrapper rejects before calling any GA function. Existing router lifecycle/error handling remains in place; no new publication authority is granted.

With a valid provider, a new fresh run receives a complete immutable side record under `backend/run_provenance_v1/<canonical-run-id>.json`. Capture refuses existing history, a progressed run, repeated creation, unsupported saved/uploaded seed mode, input/engine drift or context drift. It never retrofits a historical snapshot. The deployment path must remain server-controlled; tests redirect it to a new temporary directory.

The writer flushes/fsyncs its own temporary file and publishes with an exclusive hard link, so readers see a complete record and an existing name is never replaced. Only the newly owned temporary file is removed in `finally`. Storage failure stops this capture/search path. Windows hard-link support was exercised in the tests; unsupported storage fails closed. A process crash may leave a temporary orphan for review; no automatic cleanup of existing artifacts is implemented.

The reader checks bounds, duplicate JSON keys, envelope digest, schema/run/context/configuration bindings, timestamp awareness/order and containment. Version-two classification also requires exact matching recorded start time, metric population/generation limits and configuration fingerprint. Hashes provide local integrity, **not cryptographic institutional signatures**. The append-only application contract assumes protected server storage; enabling a genuine provider also requires an approved storage ownership, retention and recovery policy.

Resume never creates or rewrites a run-start record. A retained valid record can qualify subsequent same-run observations through ordinary read checks; a missing/corrupt record cannot be regenerated from a checkpoint. **Checkpoint continuation admission, graph/format, strict fingerprints and legacy compatibility policies are unchanged.** U5B does not claim an atomic provenance binding inside existing checkpoint bytes or use a missing record to bypass their checks.

The legacy `/api/ga/generate` helper does not use the monitored history wrapper and remains unqualified for this projection. Saved/uploaded-seed provenance requires a separate approved contract because the existing configuration fingerprint includes actual seed identity. U5B does not reinterpret that fingerprint, reconstruct a seed for metadata, or change Saved Best persistence. No database migration or database-backed provenance table was created.

## Version-aware Current Evaluation

The protected GET endpoint now returns response schema 2 / `ga-result-compatibility-v2` with:

| Classification | Required evidence |
|---|---|
| `CURRENT` | Existing validated/integrity-checked U5A history and scoring provenance; immutable matching run-start record; fresh server-verified context with the same context digest; matching source/input/configuration/start/metric identities. |
| `LEGACY_INCOMPATIBLE` | Explicit established engine/scorer/policy/input difference, or a verified captured context that differs from the currently verified context. This denotes comparison incompatibility, not chronological age or institutional disapproval. |
| `UNKNOWN_COMPATIBILITY` | Missing/unavailable context or run-start proof, unsupported/inconsistent metadata, corruption, mismatched start/configuration or unreadable records. Raw academic labels in a history snapshot alone cannot establish CURRENT. |

The U5A index traversal, recorded-candidate validation, input drift checks, bounds, incomplete-coverage handling and best-selection rules are reused through explicit internal function arguments. No global runtime monkeypatch or duplicate schedule evaluator is introduced. Only completed qualified runs supply a best; different configuration fingerprints cannot supply one raw-penalty best. Zero, finite negative and decimal observations retain their actual values. No historical chromosome is rescored to manufacture comparability.

Current authority/context is rechecked on each projection; a context revision change invalidates equality, and revocation/unavailability prevents CURRENT. The original record remains unchanged. Read-time context/source drift rejects the projection. An academic verification assertion does not authorize a schedule, a workload exception, a Chair decision or institutional publication; `institutional_authorization` remains `NOT_ESTABLISHED`.

The frontend supports both old schema-1 U5A responses and new schema-2 responses, rejecting mixed classification vocabularies and unknown academic-context schemas. Schema 2 requires nested context/start-record bindings, not just an arbitrary compatible flag. Current Evaluation displays academic year/term, department, dataset revision, original run context, start-record/context/configuration hashes and history links. Loading, error, retry, empty and unavailable states remain. No decorative context selectors or new write controls were added. The existing archive and Saved Best guard remain intact.

## Fresh verification

| Check | Final result | Evidence scope |
|---|---|---|
| New backend tests | 34 passed, zero failed/errors/skipped | Context validation/freshness, no-provider behavior, immutable/no-clobber capture, atomic failure, drift, no retroactive/resume capture, semantic tampering, revocation, ASGI auth/query rejection and actual fictional execution-hook parity. |
| Backend regressions | 54 passed, zero failed/errors/skipped | U5A 20, current V1 checkpoint creation/load/continuation and strict-loader checks 4, fictional V2 engine 30. No SQLite API workflow suites selected. |
| New frontend contracts | 14 passed, zero failed/cancelled/skipped | Versioned context/proof, zero/precision, scope/dataset mismatch, no mixed versions, unknown/legacy states, baseline protection and unsupported schemas. |
| Existing frontend contracts | 198 passed, zero failed/cancelled/skipped | U5A, U1-U4, Live Center, auth/session, preferences, metadata, history and fitness reporting. |
| New browser scenarios | 17 passed (18 Node tests including parent) | Actual Edge/React, explicitly fictional intercepted HTTP. |
| Existing browser scenarios | 133 passed | U5A 14, U1 12, U3 15, U4 21, Live Center 20, existing GA 51. Total including U5B: 150 child scenarios / 157 Node tests including seven parents. |
| TypeScript / production build / focused ESLint | Exit 0 / 0 / 0 | Existing mixed-import/large-chunk warnings retained; final main JavaScript approximately 1019.76 kB. |
| Git fsck / whitespace / privacy / hashes / preservation | See manifest | Read-only checks; dangling Git objects retained, no corruption reported or cleanup performed. |

The new focused backend fixture rejects **every SQLAlchemy Engine.connect call**, restores all dependency overrides, and redirects provenance/history/checkpoint stores into fresh pytest temporary storage. The actual V1 parity test uses the existing fictional D10 resource fixture, temporarily bypassing only institutional-loader validation for those supplied fictional templates; it uses the real engine, operators and scorer, and compares assignments, fitness/breakdown/history and RNG state. It does not establish institutional input-loader acceptance. Existing V1/V2 source-byte fingerprints and continuation behavior are preserved.

Final backend commands use a verified, previously nonexistent UUID `--basetemp`, no cacheprovider, a whitelisted child environment and `-B`. No production/institutional PostgreSQL, existing SQLite database, disposable D15 database or migration was accessed. No database writes occurred in U5B. No production GA run occurred. No dependency was installed. Test fixture metadata is explicit fiction; it is never installed as a production authority source.

Two existing dependency deprecations remain: TestClient/httpx and anyio BlockingPortal. No warnings were hidden by an upgrade. Earlier successful 28/33-case and 13-contract records predate additional cases and are retained with their actual counts.

### Retained failed GA browser attempt

`20261104T174126655606+0800-ga-browser` recorded **32 passed, 18 failed, 2 cancelled** including the parent. First failure: `checkpoint verification timeout reports a specific error and preserves paused metrics`, with `Checkpoint timeout did not settle`; later scenarios cascaded and the 180-second parent deadline was reached. Runner elapsed was approximately 202.55 seconds, with `timed_out:false` for the separate 300-second runner limit.

An unchanged rerun at `20261104T174549348130+0800-ga-browser` passed **all 51 scenarios / 52 Node tests**, zero failures/skips/cancellations. No GA source, recovery code, original browser assertions or timeout was changed. Frontend work overlapped part of the unsuccessful attempt, but that does not independently establish the cause of the first timeout. The root cause remains unconfirmed; this is a retained, non-reproduced test-run timing/synchronization limitation, not a claim that it was harmless. No failure evidence was deleted or converted into a pass.

## Screenshots and privacy

Final unedited fictional captures: `testing/dashboard-u5b/20261104T174338566561+0800-browser/`:

- [Current result and academic context](testing/dashboard-u5b/20261104T174338566561+0800-browser/U5B-B01-current-best.png)
- [Implementation provenance](testing/dashboard-u5b/20261104T174338566561+0800-browser/U5B-B02-provenance.png)
- [Missing run-start record](testing/dashboard-u5b/20261104T174338566561+0800-browser/U5B-B05-unknown.png)
- [Mobile current result](testing/dashboard-u5b/20261104T174338566561+0800-browser/U5B-B13-mobile.png)
- [Unavailable server context](testing/dashboard-u5b/20261104T174338566561+0800-browser/U5B-B15-unavailable-context.png)
- [Expanded start-record details](testing/dashboard-u5b/20261104T174338566561+0800-browser/U5B-B17-run-start-provenance.png)

All sixteen unique image contents were visually reviewed; seventeen retained PNGs have raw hashes and metadata/structure checks. Narrow viewport captures show only part of the scrollable table/details; DOM assertions verify full provenance text and keyboard-accessible expansion. Desktop/mobile responsive tests establish no horizontal document overflow, not full WCAG/screen-reader/device conformance. Browser responses are mocked; they are not live browser-to-FastAPI, PostgreSQL or institutional acceptance. Backend ASGI tests are separate real in-process HTTP tests with fictional principal/provider overrides.

The final scan checks complete/truncated encoded-receipt patterns, credential URLs, private keys, real header/token values and private faculty names in memory without exporting them. New records/evidence contain no institutional faculty rows, passwords, cookies or signed session receipts. Existing records and earlier evidence were not redacted or rewritten.

## Exact source inventory

Modified from U5B entry state:

1. `backend/routers/genetic_algorithm.py` - two-line server execution-wrapper hook before GA search.
2. `backend/routers/ga_evaluation.py` - select the version-two read-only projection; existing admin dependency preserved.
3. `backend/services/ga_result_compatibility.py` - reuse traversal with explicit identity/classifier arguments; U5A defaults preserved.
4. `frontend/src/services/currentEvaluation.ts` - versioned DTO/validation and nested provenance consistency.
5. `frontend/src/components/ga/CurrentEvaluation.tsx` - verified scope/dataset and per-run start/context/configuration details.

New implementation/tests:

- `backend/services/ga_academic_context.py`
- `backend/services/ga_run_provenance.py`
- `backend/services/ga_evaluation_v2.py`
- `backend/tests/test_ga_academic_context.py`
- `frontend/tests/academicContext.fixtures.mjs`
- `frontend/tests/academicContext.test.mjs`
- `frontend/tests/academicContext.browser.test.mjs`

New report/tooling/evidence: this report; `docs/testing/dashboard-u5b/run_checks.py`, `audit_evidence.py`, `preservation-baseline.json`, `manifest.json`; and every timestamped command/browser-result/PNG path explicitly enumerated in the manifest. The exact inventory excludes unrelated U4/Live/research files and protected local modifications.

The entry baseline includes **3,108 paths**, all **23 academic files**, protected local preference/settings raw bytes, original GA/math/operator/RNG sources, migration/checkpoint/schedule trees, historical evidence and Git index. Only the five listed source extensions are allowed to differ: **3,103 existing paths remain byte-identical** in the final audit. No provenance file was created in the repository's default runtime store during testing. Generated build output remains ignored.

Git remains on `main` at `2db42c396c6418e722555269354921f178628868`, with nothing staged. No commit, push, reset, restore, clean, branch switch, deletion of historical artifacts or protected-data normalization occurred. Existing unrelated U4, Live Center and research changes remain present. LF/CRLF notices are recorded separately from actual whitespace errors.

## Reproduction

From the repository root in Windows PowerShell, using existing dependencies:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5b/run_checks.py backend
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5b/run_checks.py backend-regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5b/run_checks.py focused
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5b/run_checks.py regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5b/run_checks.py browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5b/run_checks.py u5a-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5b/run_checks.py u1-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5b/run_checks.py u3-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5b/run_checks.py u4-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5b/run_checks.py live-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5b/run_checks.py ga-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5b/run_checks.py build
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5b/run_checks.py bundle
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5b/run_checks.py lint
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5b/audit_evidence.py
```

Each runner creates a new evidence directory without replacing earlier records. The audit replays a frozen inventory; new executions require a separately reviewed evidence addendum. U5B's regression selection deliberately excludes SQLite workflow/API suites. Only owned temporary file stores and isolated browser profiles are used.

## Blocked portions and recommended next milestone

**REQUIRES APPROVAL:** a genuine context provider and its stewardship/lifecycle rules. The provider must verify scope/year/term UUID relationships, authoritative dataset revision, effective IT cohort/offerings/resources, and correspondence between the actual loaded GA model set and approved input bytes. File hashing alone does not establish that mapping, complete semester data or full CCS coverage. In-memory academic objects are constructed by existing loaders; U5B does not silently repair/reload them or resolve the F1/F1.5 roster gap. No database reads or authority activation are authorized merely by the existence of academic models.

**PROPOSED:** a controlled provider-qualification milestone using an approved institutional source, read-only identity/dataset mapping, lifecycle/revocation tests and owned deployment-storage policy. The current provider remains None until that approval and source are available. Do not infer approval from an administrator login, adviser-supplied file, filename, timestamp or fictional verification.

**SEPARATELY BLOCKED:** Saved Best producer persistence/comparison and saved/uploaded seed provenance. Any future write-format change, retention/backfill policy or checkpoint/provenance admission binding requires a reviewed version-aware contract and separate authorization. Do not migrate historical artifacts, spoof engine identities, reinterpret old scores or bypass strict checkpoint checks. V2 aggregation/publication remains in its existing authority-protected workflow.

U5B is ready for review of the conditional, tested foundation, with the retained browser timing limitation disclosed. It does not establish production institutional readiness. No next milestone, persistent Saved Best change or Git checkpoint was started automatically.
