# D10: versioned confirmed-GEC orchestration and candidate admission

Updated 2026-10-24, Asia/Manila, against D9 baseline `d6446d0757b91e1b3b17d650fcb49e896f51203b`.

**Implemented and verified with isolated fictional resources/providers. Genuine institutional authority and production constrained scheduling remain BLOCKED.** Supported current-release V1 checkpoint continuation is preserved. No PostgreSQL operation, migration, staging, commit or push was performed. D11, D12 and C++ work were not started.

## Architecture decision and supported V1 baseline

The user approved **Option B**: the six retained historical checkpoints were already incompatible with the unchanged D9-era engine; their existing `GA_CHECKPOINT_INPUT_CHANGED` rejection is an accepted historical limitation. All six remain byte-identical. None was deleted, migrated, overwritten, reinterpreted or made resumable by bypassing a fingerprint.

The original investigation stopped at reset/admission/publication/fingerprint boundaries. The user then approved a separate constrained V2 orchestration mode with immutable snapshots and pre-admission rejection. The later historical-checkpoint stop was resolved by Option B. Those decisions and the six original diagnostic findings are retained in the [initial investigation](testing/dashboard-d10/initial-investigation/report.md), [pre-Option-B report](testing/dashboard-d10/before-option-b-implementation/report.md), their archived manifests and the [original six-check command](testing/dashboard-d10/20261023T215141091867+0800-boundary/command.json). They are history, not current instructions to stop or rerun setup.

The earlier three V1 tests at pause generations 0, 1 and 3 genuinely wrote, loaded and resumed JSON checkpoints, but controlled crossover/mutation returns. They were reviewed, not represented as fresh original-operator acceptance. The new [supported fixture tests](../backend/tests/d10/test_v1_baseline.py) use fictional faculty/sections/rooms, the original population construction, selection, crossover, mutation and fitness implementations, real checkpoint I/O and pause generations 0, 1 and 2. Only fixture metadata, preference tables and owned output paths are supplied; algorithm functions are not replaced. **4 fresh tests passed**, including three original-operator continuation cases.

The [fixture record](testing/dashboard-d10/20261023T234234124363+0800-v1-fixtures/command.json) contains three `fixture-*.json` side records with exact engine/input fingerprints, reproducible seed 710, parameters, fictional-template hash and actual checkpoint hashes. Raw checkpoints/source-input snapshots are kept out of repository evidence. After V2 implementation, [verify_supported_v1.py](testing/dashboard-d10/verify_supported_v1.py) loaded byte-identical temporary copies of those actual pre-V2 supported checkpoints and resumed all three with the unchanged V1 loader/operators. Schedule, history, original fitness/breakdown, analysis and RNG matched an uninterrupted fixture. **3 standalone continuation checks passed**; they are not additional pytest cases. [Post-integration record](testing/dashboard-d10/20261024T001541404572+0800-supported-v1/command.json).

All fingerprinted V1 source bytes, original penalties/equations, chromosome classes, RNG implementation, checkpoint schema and engine verification remain unchanged. V2 has a separate identity; no legacy fingerprint spoofing, compatibility bypass, runtime module-symbol replacement or historical-data restoration was used.

## Immutable constraints and fresh authority

[ga_v2_constraints.py](../backend/services/ga_v2_constraints.py) introduces frozen, tuple-backed term catalogs, confirmed heads, commitments and constraint snapshots. Clients submit an exact year/term and a reviewed constraint digest for optimistic concurrency. They cannot submit authority flags, resource mappings, trusted snapshots, checkpoint paths or a subset of revision IDs.

The server reads the **complete applicable D9 record set**, independent of D9's paginated display catalog. More than 1,000 records rejects the operation; nothing is silently truncated. D9 chain/content/evidence checks are reused and revision-base/record links checked again. Applicable records without a current confirmed head, including revoked records, block the operation. An unconfirmed successor proposal on an already-confirmed record does not replace the current head.

Fresh D8 evidence/issuer policy and fresh independent authority for the original confirmation decision are required. The immutable content is bound through an explicit `d10-durable.1` context; no expired preview receipt is reconstructed or accepted. Historical `VERIFIED` display fields do not grant current authority. Evidence identity/revision/issuer/policy must match the confirmed decision, while freshness/expiry/revocation is re-evaluated on every guarded boundary.

An independently supplied server catalog must bind current raw input bytes, exact templates, academic year/term, full effective window and explicit authoritative ID-to-runtime mappings. No stable identity is inferred from a name, alias or row order. File imports retain their original source-byte hash. Manual records have a labelled `canonical_manual_content` SHA-256; it is not misrepresented as a file-byte hash. Source row, record/revision/event, content/evidence digests, resource applicability and source-hash kind remain explicit.

Commitments use half-open `[start,end)` intervals. Days, positive durations, 30-minute grid, actual resource calendar containment, term coverage, duplicates and internal section/faculty/room overlaps are validated. Adjacent intervals are allowed. Missing applicable resources, ambiguous mappings, unsupported terms, calendar exceptions and contradictions with existing fixed section inputs fail closed. Optional resources are absent only when durable completion explicitly declares them not applicable. Unknown fields or normalized-away durable content are rejected.

**Production remains blocked:** `institutional_deployment`, the original D8 verifier/issuer registry and independent confirmation provider have no genuine deployment implementation. Fictional adapters are installed only in isolated tests, never production. No environment switch or administrator checkbox grants institutional authority.

## V2 execution, reset safety and admission

[ga_v2_engine.py](../backend/services/ga_v2_engine.py) identifies `ga-constrained-v2.1`, using constraint contract `gec-constraints-v2.1`. It calls the original tournament selection, 10% elitism/top-50%-nonelite selection, crossover, mutation and numerical fitness functions. External commitments are never Subject genes and do not add penalties or inferred teaching credits.

Faculty/room slots overlapping fixed commitments are removed from detached run-local calendars. Original reset helpers cannot recreate removed slots. Section commitments use the existing persistent fixed-calendar contract. Original data and resource objects remain unchanged. V2 construction uses the original reset, ranking, time-pattern, assignment and rollback helpers, passing the run-local subject set explicitly. This avoids the V1 convenience constructors' global section fallback without changing those protected functions or replacing module globals at runtime.

Every initial, seed, regenerated, crossover, mutation, survivor, elite and best-ever candidate must pass external conflict checks and the existing publication/reconstruction constraints before admission or best comparison. Authoritative faculty profiles are checked, not trusted from serialized caches. Rejected evaluated candidates are discarded without repair. Requested saved/uploaded V1 seeds are explicitly reconstructed and validated against the pinned V2 context; missing or incompatible seeds reject with no fresh fallback.

Default budgets: population 10, generations 5, fresh candidates 2, 20 candidate attempts per missing slot, 10 construction restarts per attempt, `max(1,int(population*0.9))*20` crossover calls with up to 20 original crossover attempts, and up to 20 original mutation attempts. Request bounds are explicit in [Parameters](../backend/schemas/ga_constrained.py). Admission/backfill guarantees the requested population size or raises `SEARCH_EXHAUSTED` with rejection counters and feasibility explicitly unknown. Original capacity rejection and unsupported original meeting patterns have separate input-error codes; exhaustion is not claimed as mathematical infeasibility.

V2 may change admitted populations and subsequent random-call paths, as approved. It does not promise V1/V2 RNG equivalence. API workers isolate V2's RNG state while holding the shared process-local GA execution lock, then restore V1's exact prior module RNG state. V1 and V2 API executions do not overlap in the supported single-backend-process configuration. Original RNG source and supported V1 continuation remain unchanged.

Tests cover a feasible original-operator run, controlled post-crossover/post-mutation rejection, reset persistence, backfill/exhaustion and original-crossover behavior. One test constructs valid fictional parents for which the **original crossover returns a lower-penalty child overlapping a fixed faculty commitment**; V2 rejects that real returned child before population/best-ever admission, then continues with valid candidates. The original fitness equation is unchanged throughout.

## Atomic checkpoint, saved-best and publication policy

[ga_v2_store.py](../backend/services/ga_v2_store.py) keeps V2 under ignored `backend/constrained_runs_v2/`. No original best/latest/stopped/history/checkpoint destination is used. Each V2 run has one atomic compressed envelope containing its engine/input identity, term/catalog/constraint set, parameters, original scoring context, complete population, run-scoped best, history, RNG continuation state, status and result. This is the V2 saved-best/history/checkpoint/result boundary, not an alteration of V1 global saved-best semantics. There is no independently writable metadata sidecar.

The V2 fingerprint binds the unchanged V1 fingerprint, new orchestration/storage/service/DTO/router source and D8/D9 durable trust contracts/models. Strict version, checksum, graph allowlist, size, input, engine, term, snapshot, population, original fitness and provenance checks precede continuation. Original evaluation inputs are freshly compared, not validated against their own deserialized overrides. A fresh Python subprocess continuation is tested. Missing, partial, corrupted, wrong-term or incompatible state fails closed with no V1 fallback.

At each generation/publication boundary, all candidates are re-admitted and the complete D9 set/trust rechecked while ledger locks are held. After validation/compression/file fsync, trust and input/engine identity are rechecked immediately before atomic replacement. Authority loss leaves the previous envelope intact; temporary files are removed. Current result reads and resume revalidate authority and heads again. Changed/revoked/unavailable authority blocks publication or retrieval; a prior stored result is not claimed current merely because it exists. A missing worker with only a RUNNING envelope is reported interrupted/failed rather than automatically resumed.

Owned SQLite tests use `BEGIN IMMEDIATE`; the PostgreSQL branch specifies bounded shared table locks to prevent head/membership changes through the atomic write. **That PostgreSQL branch has not been executed or accepted.** No PostgreSQL connection, provisioning, migration or institutional database operation occurred.

## Administrator API and dashboard

All new endpoints use the existing real administrator/session boundary; POST operations retain Origin/CSRF enforcement:

| Endpoint | Behavior |
|---|---|
| `GET /api/ga/v2/status` | Explicit legacy/V2 versions and production BLOCKED status |
| `GET /api/ga/v2/constraints` | Fresh complete term-bound confirmation snapshot/provenance |
| `POST /api/ga/v2/runs` | Revalidate reviewed digest, seed and authority; asynchronously start a separately identified V2 run |
| `GET /api/ga/v2/runs/{uuid}` | Scalar live status or freshly validated durable V2 proposal; no population graph exposed |
| `POST /api/ga/v2/runs/{uuid}/control` | Cooperative pause/stop and strict durable resume; no parameter/constraint replacement |

[Generate Schedule](../frontend/src/pages/admin/GenerateSchedule.tsx) adds a teal/gold V2 panel for sourced term review, population/generation bounds, explicit seed selection, diagnostics and versioned controls. Normal V1 controls and context remain unchanged. [Schedule View](../frontend/src/pages/admin/ScheduleView.tsx) and [Fitness Analysis](../frontend/src/pages/admin/FitnessAnalysis.tsx) select the V2 read-only view only for `?v2run=<uuid>`; default views retain their original component bodies. The existing weekly calendar is reused. Pages show provenance, original fitness, rejection counters and the label **GA-generated proposal — not Chair-approved or official**. Printed/reviewed/confirmed GEC input does not itself approve the generated CCS result.

## Exact implementation files

Modified existing files: `.gitignore` (ignore private V2 runtime output), `backend/main.py` (register protected router), and the three administrator pages above. The pre-existing protected preference modification remains byte-identical and is outside D10 implementation.

Created application files:

- `backend/routers/ga_constrained.py`
- `backend/schemas/ga_constrained.py`
- `backend/services/ga_v2_constraints.py`
- `backend/services/ga_v2_engine.py`
- `backend/services/ga_v2_store.py`
- `backend/services/ga_v2_service.py`
- `frontend/src/api/constrainedGA.ts`
- `frontend/src/components/ga/ConstrainedRunPanel.tsx`
- `frontend/src/components/ga/ConstrainedResultPanel.tsx`

Created tests/support: six files under `backend/tests/d10/` (`support.py`, `test_v1_baseline.py`, `test_v2_engine.py`, `test_v2_api.py`, `test_v2_live.py`, `resume_v2_child.py`) and four frontend files (`constrainedGA.test.mjs`, `.fixtures.mjs`, `.browser.test.mjs`, `.live.mjs`). D10 evidence utilities/archives, this report, command records, fixture identity records and actual PNGs are listed individually with raw-byte hashes in the [manifest](testing/dashboard-d10/manifest.json). Original D1-D9 implementation/tests/evidence were not rewritten.

## Validation results and evidence attribution

Latest results, excluding earlier failed attempts and container-test double counting:

| Check | Actual latest result | Evidence |
|---|---|---|
| Supported V1 fictional fixture pytest | 4 passed; original operators, real checkpoint I/O | [record](testing/dashboard-d10/20261023T234234124363+0800-v1-fixtures/command.json) |
| Actual pre-V2 supported V1 checkpoint copies | 3 standalone continuations passed, not pytest | [record](testing/dashboard-d10/20261024T001541404572+0800-supported-v1/command.json) |
| V2 kernel/constraints/checkpoints | 30 passed | [record](testing/dashboard-d10/20261024T004433134528+0800-v2-engine/command.json) |
| V2 real ASGI auth/D8/D9/SQLite API | 18 passed, 2 warnings | [record](testing/dashboard-d10/20261024T004434385182+0800-v2-api/command.json) |
| V2 real Edge -> FastAPI -> SQLite/original GA | 6 browser scenarios; 1 pytest wrapper passed, 2 warnings | [record](testing/dashboard-d10/20261024T004420813923+0800-v2-live/command.json) |
| V2 Edge/React with synthetic HTTP | 12 scenarios (13 Node checks including parent) | [record](testing/dashboard-d10/20261024T003238287843+0800-v2-browser/command.json) |
| Frontend contracts | 161 passed (11 new + 150 existing) | [record](testing/dashboard-d10/20261024T003034435458+0800-contracts/command.json) |
| D2-D9 backend regressions | 327 passed, 2 warnings | [record](testing/dashboard-d10/20261024T002647955206+0800-backend/command.json) |
| Existing auth/control regressions | 46 passed, 4 warnings; includes actual browser auth | [record](testing/dashboard-d10/20261024T003019348550+0800-backend-regressions/command.json) |
| Academic offline foundation | 85 passed, 2 warnings; no PostgreSQL cases selected | [record](testing/dashboard-d10/20261024T002647958810+0800-academic-offline/command.json) |
| Original resource/preassignment regressions | 3 passed | [record](testing/dashboard-d10/20261024T002651219905+0800-ga-resource-regressions/command.json) |
| D1-D8 Edge with synthetic HTTP | 125 scenarios (133 Node checks including 8 parents) | [record](testing/dashboard-d10/20261024T003608222141+0800-browser-regressions/command.json) |
| D9 real Edge/FastAPI/SQLite | 16 scenarios; 2 pytest wrappers passed, 2 warnings | [record](testing/dashboard-d10/20261024T004017442979+0800-live/command.json) |
| GA Edge with synthetic/intercepted HTTP | 51 scenarios (52 Node checks including parent) | [record](testing/dashboard-d10/20261024T003248844013+0800-ga-browser/command.json) |
| Production TypeScript/Vite build | Passed with bundling warnings | [record](testing/dashboard-d10/20261024T003037474121+0800-build/command.json) |
| Focused ESLint | 0 errors, 4 pre-existing warnings | [record](testing/dashboard-d10/20261024T003039410670+0800-lint/command.json) |
| Exact HEAD Schedule View lint comparison | Same 4 warnings before D10 | [record](testing/dashboard-d10/20261024T003747314373+0800-lint-baseline/command.json) |

Synthetic HTTP browser scenarios prove rendering/interaction contracts, not live authorization or actual GA generation. The separate real HTTP fixture uses real passwords/sessions, Origin/CSRF, D8/D9 ledger transactions and original GA functions, with entirely fictional institutional providers/resources and owned SQLite. Neither establishes PostgreSQL or genuine institutional approval. Screenshots are genuine Edge captures; no image generation, reconstructed success states, HARs, raw checkpoint graphs or database files are archived. Browser metadata records exact times/version/viewport and distinguishes the two scopes. Current browser version was Edge `155.0.4283.62`.

The earlier six boundary assertions remain historical characterizations, not new integration passes. The manifest retains every unsuccessful command. Initial fictional V1 fixtures lacked legacy analysis columns; fixture-only corrections resolved them. Initial V2 fixture assumptions and manual/file-hash handling were corrected without weakening protected algorithms. Two sandboxed D10 browser attempts and one existing-auth browser attempt failed at `Runtime.enable` before app navigation. The diagnostic socket closed abnormally (`1006`); the unchanged harness/timeouts passed outside the sandbox with an owned profile. This is supported as a sandbox-related browser transport problem; the exact underlying OS restriction was not independently identified. No test was disabled or timeout enlarged.

The early D10 runner reused a generic V1 scope label for some new command records. Only that attribution metadata is corrected, with the previous label/reason retained in each affected record. Commands, timestamps, sanitized output and outcomes remain unchanged. Failure evidence is not deleted.

## Warnings, performance and remaining limitations

Both V1 dependency warnings were investigated in installed source: Starlette 1.6.0 falls back to `httpx` 0.28.1 because `httpx2` is not installed; its annotation also uses AnyIO 4.15.1's deprecated `abc.BlockingPortal` alias for `from_thread.BlockingPortal`. These are test-client dependency maintenance warnings, not checkpoint integrity errors or evidence of a GA regression. Dependencies were not upgraded or warnings suppressed. The new original-operator V1 fixture, which does not import TestClient, emitted neither warning.

Academic/offline SQL rendering retains the existing Alembic `prepend_sys_path`/missing `path_separator` warning. It is SQL rendering, not migration execution. Four Schedule View hook-dependency warnings are verified against exact HEAD source and were not fixed by unrelated legacy-page edits. Build warnings concern an existing ineffective dynamic import and the >500 kB bundle.

The final fictional real-HTTP generation UI step completed in approximately 1.266 seconds, including HTTP/polling/rendering; kernel tests took 17.39 seconds. These are small bounded-fixture observations, not an institutional performance, memory, feasible-rate or V1/V2 speed comparison. Retry budgets/domains differ; the V1 fixture duration must not be used as a speedup baseline.

Remaining boundaries:

- Genuine issuer/evidence/independent-confirmer providers and authoritative term/resource catalogs are absent. Production V2 activation remains BLOCKED.
- The 17 Phase 4C PostgreSQL cases, D9 online PostgreSQL acceptance and new V2 PostgreSQL lock/concurrency acceptance remain NOT RUN. SQLite results are not substitutes.
- Only explicit whole-term weekly patterns without unresolved date exceptions are supported. Required unknown mappings, unsupported components and conflicting fixed inputs block rather than guess. External meeting hours do not invent course credits or change existing workload mathematics.
- GA admission is process-local, matching the existing single-backend-process deployment model. Multi-worker/distributed ownership and shared-file continuation have not been established or claimed.
- V2 best/history/result/checkpoint are run-scoped; existing V1 artifacts are not reinterpreted. Run lookup uses its retained URL/UUID; a separate V2 library/discovery UI and cross-run best reuse are not added here. Faculty My Schedule retains its existing V1 latest-result source; V2 does not silently publish into it.
- Six historical V1 artifacts remain incompatible as explicitly accepted. Supported checkpoints remain tied to exact inputs/source/dependency versions; subsequent changes correctly reject continuation.

## Preservation, privacy and next step

The [original baseline](testing/dashboard-d10/preservation-baseline.json) contains 873 files. **868 remain byte-identical; exactly the five intended existing paths listed above changed.** All 23 academic data paths, protected preference bytes, faculty UUID/code mappings, original operators, fitness/scoring, RNG, checkpoint services/formats, retained schedules/checkpoints/history, Phase 4C foundation, D1-D9 evidence, HEAD and Git index remain unchanged. The default V2 storage directory was not created; every executed V2 run used owned temporary storage.

The evidence audit checks raw hashes, Python syntax, Git/untracked whitespace, decoded complete/truncated receipt fragments, credential/key/header patterns, local private-name matches, PNG CRC/chunk metadata and visually reviewed original captures. Identical captures are identified by hash; an earlier mobile capture showing mostly navigation is retained, while the later main-content capture provides the mobile review view. Hashes identify artifacts; they do not authenticate institutional authority.

**Next step:** review the D10 diff and manifest before any Git checkpoint. Separately scope genuine institutional/catalog integration and disposable PostgreSQL acceptance when authorized, including concurrency and deployment topology. Do not activate production constraints, start D11/D12 or C++ work automatically. No staging, commit or push is part of this implementation.
