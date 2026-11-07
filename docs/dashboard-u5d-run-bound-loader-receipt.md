# U5D: run-bound GA input observation receipt

2026-11-05, Asia/Manila. Entry `main`: `d6db077793da52b7559351a5d0f8e6d54608cb77` (committed U5C/U5C-R1). Reviewed U5A, U5B, U5C and R1 reports/manifests and the current implementation before editing. Preserved the eleven existing tracked local modifications and unfinished research/U4/Live work.

**Classification: PARTIALLY IMPLEMENTED. Full run-bound consumption verification remains BLOCKED by unresolved loader behavior.** New fresh V1 API executions have immutable, run-bound input observations. Every receipt is explicitly **UNVERIFIED** and ineligible for CURRENT. A matching hash or an existing receipt is never treated as proof that every optimizer read used that data, nor as institutional approval.

## Investigation and implementation decision

The written plan was communicated before edits: preserve all fingerprinted engine code; capture pre-call runtime aliases and source/configuration identities in separate records; observe active frozen scoring context at existing generation callbacks; record call completion/interruption without changing optimization; test the unchanged real engine; leave complete consumption attestation unimplemented. No frame inspection, tracing/profiling hook, global input rebinding, new scorer, operator monkeypatch, new history schema or provider activation is used.

The [U5C source map](dashboard-u5c-institutional-context-qualification.md) remains applicable. U5D traced these additional execution and mutation boundaries:

| Boundary / source | Actual consumer and change window |
|---|---|
| `Functions.py` module import | Reads first-semester subjects, consolidated section schedules, legacy faculty preferences/loads, qualifications, eligibility and domains. Transforms dictionaries, constructs models and applies fixed sections/preassignments. These objects remain cached. Current files can differ from imported models. |
| Identity registry and cohort | `identity_service.py` caches stable mappings; GA cohort follows legacy preference construction. Account registration is not a complete authoritative term roster. IT/CCS scope and F1/F1.5 institutional data gaps remain unresolved. |
| Sections/rooms/timeslots | Prototype sections/student groups, hardcoded rooms and meeting patterns become model state. Section fixed blocks and faculty/room reset behavior differ. Calendar changes can be legitimate algorithm bookkeeping, not source revisions. |
| API admission | `_admit_execution` validates stored preference/settings syntax, acquires the existing single-process execution lock and allocates a server UUID/control. Other input writers are not covered by that lock. No new concurrency permission is introduced. |
| `_execute_with_history` | Revalidates input files, then U5B captures optional server context. New observation begins here, before engine decorators. Runtime-alias graph capture is not atomic with later engine-local binding. Source files may change between samples. |
| History templates | `_templates()` / `ga_validation_templates.validation_templates` build detached validation profiles/calendars and omit assignment references. They are validation inputs, not proof of the engine's actual working graph. Existing history formats remain unchanged. |
| `FrozenInputs.capture_inputs` | Reads effective settings and dashboard preferences, deep-copies `Functions.list_faculty`, checks file fingerprint before/after and installs a ContextVar. Its faculty alias can differ from the engine alias; other model families were cached earlier. ABA changes and complete source-to-transformed-model mapping are not established. |
| `ga_service.run_genetic_algorithm` | Binds module-global subject/faculty/room lists and legacy preference frame into locals; deep-copies publication templates; constructs its monitor; then creates/loads a seed and initializes chromosomes. Source verification before this point does not freeze every object it will consume. |
| Initialization/restarts | `CreatePopulation` / `Functions.create_schedule_with_minimum_load` mutate working calendars and assignments and reset resources during restarts. Observing the initial mutable graph cannot prove each subsequent read or retained authoritative closure. |
| Scoring/operators | Existing fitness calls use frozen scoring inputs plus passed legacy preferences and candidate state. Selection/crossover/mutation/fitness functions remain unchanged. The observer does not intercept these calls or certify their complete argument graphs. |
| Validated generation callbacks | Existing `GenerationMonitor.report` emits a copied metrics dictionary while frozen scoring context is active. The new local callback wrapper hashes that active context and forwards the original event unchanged. This proves an observation at this boundary, not every earlier scoring or scheduling read. |
| Pause/resume | Existing checkpoint graph restores working/publication templates, legacy preferences, scoring context, RNG and monitor state. New capture skips resume and never backfills or modifies earlier receipts. A PAUSED end record explicitly states resume is not attested. |
| History/result/Saved Best | Existing engine may save best before returning; router later publishes latest/stopped result. A receipt's `CALL_RETURNED` outcome does not mean publication, history durability, institutional approval or workflow completion. No write ordering or Saved Best selection was changed. |
| V2 / legacy helper | V2 has independent catalog/constraint/authority and storage contracts. Legacy `/generate` calls `generate_schedule` directly. Neither path is covered by this receipt integration. Direct engine calls also remain outside it. |

## Versioned contract and safe integration

`services/ga_input_receipt.py` implements `ga-run-input-observation-v1`. Its strict DTOs and reader require explicit serialized schema, stage, scope and status fields. Unknown fields, malformed/duplicate JSON, wrong IDs, invalid hashes, rehashed unsupported schemas/VERIFIED claims, oversized records and mismatched start/end binding fail closed.

| Required fact | Recorded evidence / limit |
|---|---|
| Run identity | Canonical server run UUID, server start time and aware capture time. Existing start files cannot be overwritten or reused for another run. |
| Academic context | Optional hash reference to the same run's existing U5B server record/context; never a client-supplied label. Missing/invalid references remain explicit. No new provider is queried or configured. |
| Loaded-model fingerprint | Hash of the observed pre-call engine runtime aliases plus legacy preference-frame state. Explicit scope: `PRE_CALL_ALIASES_NOT_CONSUMPTION_PROOF`. It is not called a consumed-input attestation. |
| Source dataset | Existing fingerprint of all CSV/JSON bytes. This file set includes sources not consumed by the active loader; the fingerprint is not a semantic model or institutional dataset identity. |
| Configuration | Exact six effective scalar parameters from the existing function signature/kwargs; separate canonical fingerprint. Observed monitor configuration is baseline-aware and checked for drift for fresh runs. Saved/uploaded seed contents are not read for receipt purposes and are flagged `SEED_INPUT_NOT_BOUND`. |
| Engine / observer identity | Existing strict engine fingerprint, plus an observer **source-file** fingerprint. The latter is not proof of the loaded Python code object; source/import races remain part of the unresolved complete-loader boundary. |
| Scoring observation | First/last hashes of active frozen context, generation range/count and monitor fingerprint from existing callbacks. This includes active settings/preferences/system-faculty/policy context, not a new evaluation. No callback is added when the original callback was None. |
| Verification | Schema permits only `UNVERIFIED`, `eligible_for_current=false`, `institutional_authorization=NOT_ESTABLISHED`. Mandatory `CONSUMPTION_NOT_ESTABLISHED` remains even for all matching observations. |
| End status | `CALL_RETURNED`, `CALL_INTERRUPTED`, `PAUSED` or `STOPPED_WITHOUT_RESULT`. Missing end means INCOMPLETE: active versus crashed cannot be inferred from files alone. Missing start/end means MISSING, not a reconstructed legacy receipt. |

The graph hash reuses the unchanged passive checkpoint encoder in memory only; it never decodes, scores, saves a checkpoint or exports graph contents. It preserves aliases, cycles, values and ordering, including set iteration order. It is **not a cross-process semantic normalization**: equivalent sets/graphs can have different representations. No cross-run fitness or dataset equivalence is inferred from this hash. Graph observation is capped at 100,000 encoded nodes / 16 MiB serialized data, after the existing encoder has allocated its graph; this is not a proven hard peak-RAM bound. Generation sampling stops after 32 successful observations with an explicit limit reason. Runtime/memory overhead has not been benchmarked; elapsed time and external stop-arrival timing are not claimed identical.

Separate runtime storage is `backend/run_input_receipts_v1/<run-id>/start.json` and `end.json`, now ignored by Git. Only hashes, typed numeric configuration, lifecycle metadata and fixed source/reason labels are written; no faculty records, preference values, calendars, raw candidates, passwords or signed session receipts are stored. Each complete bounded record is published atomically without replacement through an exclusive hard link, with a checksum. Only a newly owned temporary file is removed. Directory aliases are rejected. Checksums provide integrity/binding under the existing trusted-server filesystem assumption, not cryptographic authorship against an administrator who can rewrite both records and code.

Failure to create a new immutable start record prevents the new engine invocation. In-progress observation failures become explicit failure reasons; end-record failure does not replace the original engine result/exception. It leaves an incomplete unverified receipt. No receipt outcome grants publication or alters the older compatibility contract.

The fresh V1 `/run` and `/stream` paths use the existing wrapper. Resume, histories that already exist and direct/legacy/V2 execution remain unobserved rather than silently backfilled. The existing execution lock still admits only one API optimization; concurrent receipt-service tests do not assert that concurrent optimization is supported.

## Read-only administrator API

`GET /api/ga/runs/{run_id}/input-receipt` uses the existing administrator dependency. It rejects unauthenticated, faculty and Chair access; POST is unsupported; query parameters cannot assert verification. Responses expose the bounded metadata/status only. Missing records are explicit and malformed ones return sanitized errors. No frontend approval or receipt editing UI is added.

Current Evaluation is **unchanged**. It does not consume this receipt as eligibility evidence. The genuine academic provider remains unconfigured. The earlier hypothetical trusted-provider U5B tests remain conditional contract tests, not proof that an unverified U5D observation satisfies institutional source qualification.

## Tests and evidence

The [manifest](testing/dashboard-u5d/manifest.json) contains exact attempts, final counts, raw artifact hashes and selective checkpoint paths. All evidence uses fictional fixtures. New focused tests forbid `Engine.connect` and redirect preferences/settings, history, provenance, checkpoints, Saved Best and new receipt stores to temporary paths. Existing regressions use their established temporary fixtures; the common test fixture now also redirects the new receipt path.

Focused coverage includes matching observations; faculty/subject/section/room/eligibility changes; preference/settings/cohort changes in active scoring context; stale cache versus changed source fingerprint; configuration drift; cross-run events/record copying; missing/invalid receipts; rehashed forged VERIFIED/missing-field claims; incomplete/interrupted writes; exclusive-start collisions; two independent observer threads; bounded sampling; server-only academic reference; authorization; callback absence; seed limitations; real V1 parity and actual checkpoint pause/resume.

Real-engine tests compare the same fictional fixture/seed with and without the wrapper: schedule, fitness, history, breakdown, faculty analysis and final RNG state match; original engine fingerprints remain unchanged. Pause/resume uses real checkpoint creation/loading, preserves strict validation and leaves receipt bytes unchanged. These are bounded examples, not a proof over every possible GA input or interleaving.

One owned loopback Uvicorn/FastAPI test serves only the read endpoint, uses explicit fictional principal dependency overrides, temporary receipts and no database. It verifies real HTTP admin GET, faculty denial and no read side effects, then shuts down only its owned server/socket. This is **live isolated receipt-read HTTP evidence**, not a browser-to-optimizer end-to-end journey, real authentication/session acceptance, PostgreSQL acceptance or institutional authorization. The real engine executes separately in the focused in-process tests. No new browser suite is run: this milestone changes no frontend; U5C-R1's browser evidence remains historical.

Fresh final results are recorded in the manifest: focused backend **36 passed**; existing U5A/U5B/U5C and current V1/V2 backend regressions **133 passed**; frontend **13 + 166 passed**; TypeScript, production bundle, focused ESLint and Git integrity/whitespace checks passed. Earlier successful 29-, 32- and 35-case development runs remain retained, not added to the final test count. All selected final tests have zero failures/errors/skips. Existing TestClient/httpx and anyio deprecation warnings, Vite mixed-import/chunk warnings and existing Git dangling objects are retained; no dependency was installed or changed.

Reproduce from the repository root, using an isolated fixture-capable environment with installed project dependencies:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5d/run_checks.py backend
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5d/run_checks.py backend-regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5d/run_checks.py focused
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5d/run_checks.py regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5d/run_checks.py build
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5d/run_checks.py bundle
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5d/run_checks.py lint
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5d/audit_evidence.py
```

The runner allowlists ordinary OS variables, excludes database credentials/approval flags, disables bytecode/pytest cache writes and allocates unique temporary test roots. Every command writes a new timestamped record. After sealed signoff, further runs need a separately reviewed manifest supplement. Existing private import CSV dependencies and the pre-existing mixed-newline strict legacy release prerequisite documented in U5C-R1 remain; no claim of ordinary clean-checkout reproduction is added here.

## Exact implementation scope and preservation

Existing files modified:

- `.gitignore` — ignore only the new runtime receipt tree.
- `backend/routers/genetic_algorithm.py` — begin/observe/finalize around the existing V1 wrapper; preserve callback absence, original events/results/exceptions and resume behavior.
- `backend/routers/ga_evaluation.py` — protected GET projection.
- `backend/tests/conftest.py` — redirect new receipt writes for all tests.

New source/tests: `backend/services/ga_input_receipt.py`, `backend/tests/test_ga_input_receipt.py`. New documentation/evidence: this report and `docs/testing/dashboard-u5d/` (entry baseline, runner, audit, exact staging plan, manifest and command records). The staging plan lists every literal approved path; no broad staging or partial hunk selection is needed for these changes. Exclude all eleven pre-existing tracked modifications and all unrelated untracked research/U4/Live work.

The entry baseline covers **3,248 paths**. All **3,244 paths outside the four intentional existing-file edits** remain byte-identical, including all 23 academic data files, both protected local JSON modifications, original GA/scorer/RNG/engine fingerprint and checkpoint code, migrations, Saved Best, retained checkpoints, schedules and prior evidence. The actual Git index and HEAD remain unchanged. No receipt tree was created in the real application store by testing. The manifest raw-hashes evidence; use per-command `core.autocrlf=false` for any later separately approved selective staging, then verify index blobs against those raw bytes. No staging, commit, push, PostgreSQL operation, existing SQLite connection, migration, institutional activation or cleanup was performed.

## Remaining blocker and next milestone

Full VERIFIED consumption requires a separately reviewed, versioned loader/execution contract that passes an exact immutable run bundle into every actual consumer, or an equally strong validated call-boundary design. It must bind transformed faculty/cohort/eligibility/subjects/sections/rooms/calendars/patterns, fixed commitments, effective scoring context, legacy preferences, configuration and selected seeds; preserve mutable scheduling bookkeeping separately; address cache lifecycle/ABA races and concurrency; and define versioned checkpoint/resume compatibility **before** editing fingerprinted code. A pre-call graph plus callback samples is insufficient.

Recommended next milestone: **explicit run-input-bundle and consumption-boundary compatibility qualification using fictional data**, followed by approved implementation only if supported V1/V2 and strict continuation policies are preserved. Institutional owner/year/term/scope/dataset approval, cohort completeness and authoritative availability sources remain separate blockers. No new policy, source approval, CURRENT promotion, GA activation or subsequent milestone is automatically started.
