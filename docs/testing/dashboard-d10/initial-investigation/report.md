# D10: confirmed GEC constraint integration — compatibility stop

Inspected 2026-10-23, Asia/Manila, on `main` at D9 commit `d6446d0757b91e1b3b17d650fcb49e896f51203b`. **D10 is BLOCKED BEFORE APPLICATION IMPLEMENTATION.** Six read-only synthetic boundary probes passed. They characterize integration gaps; they do not establish constrained GA generation, institutional confirmation, feasibility or PostgreSQL acceptance.

The request explicitly requires stopping when safe integration cannot preserve the protected algorithm behavior. No existing input-only adapter supplies all required fixed faculty/room/section enforcement through generation, swaps, mutation, best-ever selection, checkpoint continuation and persistence. Addressing the gaps requires a decision about candidate admission and engine-version compatibility. This is a constraint on the inspected integration boundary, not a claim that every possible adapter architecture is impossible.

## Inspection and preservation baseline

Initial status contained only the pre-existing protected `backend/data/faculty_preferences.json` modification. Local `main` and the last-fetched `origin/main` identify the D9 commit above. No fetch, staging, commit, push, restore, reset or database operation was performed. No AGENTS.md was found.

Read D8/D9 trust and confirmation services/reports, current route admission/execution/finalization, `run_genetic_algorithm`, scheduling helpers/models, population construction, selection, crossover and mutation checks, publication/reconstruction, checkpoints/fingerprints, history observation, saved-best flow, frontend Generate Schedule/GA context, schedule and analysis pages, existing preassignment/resource tests, README, roadmap, bug report and documentation standard.

The [preservation baseline](testing/dashboard-d10/preservation-baseline.json) records 873 files, including tracked application/tests/historical evidence, all 23 academic data paths, retained checkpoint/saved-result trees and the Git index. It was recorded before the diagnostic imports or new probe source. Only the new D10 documentation/evidence paths were created. Final verification in the [manifest](testing/dashboard-d10/manifest.json) compares the complete baseline without restoring or rewriting anything.

## Observed integration boundary

| Boundary | Existing behavior | D10 consequence |
|---|---|---|
| D8 evidence trust | `verification_for` and `authority_policy_for` return None in deployment; evaluator checks exact schedule/term/scope/freshness/revocation. | Keep production blocked; a past public VERIFIED snapshot cannot replace a fresh provider check. |
| D9 confirmation ledger | Stores immutable proposal/content/evidence and decision chain. Historical reads explicitly return NOT_RECHECKED evidence status. Independent confirmation provider defaults to None. | D10 needs a fresh, trusted current-head read and ongoing authority/evidence checks; submitting a revision UUID alone is insufficient. No new retrieval/activation API was implemented. |
| Scheduling input construction | `Functions.py` loads runtime subjects, faculty, rooms and consolidated fixed section blocks. Generation has no D9 year/term/revision input contract. | A run-scoped immutable constraint snapshot and verified mapping/term binding must be designed explicitly. |
| Initial/fresh population | `CreatePopulation.generate_population` calls `create_schedule_with_minimum_load`; its restart loop calls `reset_complete_schedule`. | Faculty/room reservations applied once to input objects are reopened at every restart. |
| Section availability | `section_schedule_is_available` checks section-owned unavailable blocks. Section calendars survive the faculty/room reset. | Reusable for the section part, but section-only enforcement cannot satisfy faculty/room requirements. |
| Crossover/mutation | Swap faculty assignments, enforce normal eligibility/preassignments, conflicts among chromosome entries and hard teaching-load ceiling, then compare existing fitness. | They do not consult a separate fixed faculty/room commitment snapshot. Valid initial seeds alone cannot establish valid descendants. |
| Generation admission/best-ever | `ga_service.py` admits returned children/mutations; sorts and compares fitness; carries elites and best-ever forward. Existing publication validation occurs at generation boundaries. | A new hard-constraint admission filter must act before invalid descendants influence selection/best-ever. Raising at the later boundary aborts the run; it is not successful constrained generation. |
| Publication/persistence | `run_genetic_algorithm` validates and calls `save_best_if_better` before returning. Router `_finish_result` later writes latest/stopped output. | A router-only result check is too late to protect saved-best storage. Fresh head/evidence checks must guard every relevant publication path before writes. |
| Checkpoint continuation | Source-byte engine fingerprint includes GA modules and orchestration/publication/progress/checkpoint/chromosome services; loader rejects mismatches. | Editing those services changes the accepted engine identity. Retained artifacts can remain byte-identical yet become non-resumable. An explicit versioned compatibility policy is required. |

Relevant code: [reset helpers](../backend/genetic_algorithm/utils/Functions.py#L1254), [schedule restart loop](../backend/genetic_algorithm/utils/Functions.py#L1924), [section availability](../backend/genetic_algorithm/utils/Functions.py#L895), [mutation gates](../backend/genetic_algorithm/operators/mutation.py#L143), [crossover gates](../backend/genetic_algorithm/operators/Swap.py#L600), [population/orchestration](../backend/services/ga_service.py#L487), [publication validation](../backend/services/ga_publication_service.py#L7), [saved-best write](../backend/services/ga_service.py#L943), [engine fingerprint](../backend/services/ga_checkpoint_service.py#L53), [checkpoint rejection](../backend/services/ga_checkpoint_service.py#L312), [router execution](../backend/routers/genetic_algorithm.py#L50).

`PreassignedAssignment` contains only instructor identity/name and room name. Its validator checks declared resources and required meeting hours, not fixed day/start/end. Reusing it as fixed institutional meeting times would misrepresent its contract. Adding external commitments as extra Subject genes would also violate the request and alter the chromosome/scoring domain; that approach was not attempted.

## Synthetic characterization evidence

Executed `.\.venv\Scripts\python.exe -B docs/testing/dashboard-d10/inspect_integration_boundary.py` in a child with whitelisted OS variables; database URLs, credentials and approval flags were excluded. Existing scheduling modules read academic files at import, so import stdout/stderr was suppressed rather than exported. All model objects used by the checks are freshly constructed fictional resources. No database module, GA generation, fitness evaluation, publication or checkpoint-writing function was invoked.

Record: [20261023T215141091867+0800-boundary/command.json](testing/dashboard-d10/20261023T215141091867+0800-boundary/command.json). It contains exact command, cwd, start/end timestamps, elapsed time, exit code and sanitized output.

| ID | Expected and observed characterization |
|---|---|
| D10-I01 | Faculty and room blocks marked unavailable, even with `fixed_schedule=True`, become available after the real reset helper; section block remains unavailable. PASS. |
| D10-I02 | Existing section availability rejects overlap with that retained section block. PASS. |
| D10-I03 | Actual mutation and crossover conflict/eligibility/load gates do not reject a synthetic post-swap-shaped entry overlapping a separate faculty/room commitment. PASS as characterization of a gap. This deliberately partial fixture does not claim complete meeting duration, a successful operator return or a valid full chromosome. |
| D10-I04 | Actual preassignment dataclass has no fixed day/time fields. PASS. |
| D10-I05 | Source inspection verifies fingerprint coverage and loader rejection; a hypothetical source-byte change produces a different digest in memory only. PASS. No existing checkpoint was opened or modified, and no online resume was attempted. |
| D10-I06 | AST inspection verifies best saving precedes final return; no RNG draws were consumed by probes after imports. PASS. |

**Fresh results: six diagnostic checks passed, zero failed; zero GA generations, zero fitness evaluations, zero database connections.** These are standalone assertions, not six pytest integration/acceptance cases. The probe is small enough to review in full and emits no faculty rows, receipt values, cookies or provider payloads.

## Proposed integration design requiring a scope decision

Recommended direction is a **versioned orchestration extension using unchanged professor operator implementations**, with the following explicitly reviewed boundaries before implementation:

1. Read current D9 heads under a coherent database transaction and verify record/revision/event links and all relevant digests. Reconstruct trusted D8 scope from durable canonical content through a dedicated server-owned contract, not an expired session preview receipt. Obtain independently trusted evidence/issuer/confirmation-authority lifecycle findings. Production stays blocked when any required provider is absent.
2. Bind an academic year/term and the complete applicable record set. D9 stores sourced labels; active GA inputs have no authoritative term-selection contract. Require an institutional mapping/catalog boundary, using fictional mappings only in isolated tests. Do not infer identities from faculty names, section aliases or row order. Missing required mappings reject the whole scheduling operation; missing optional resources retain explicit applicability state.
3. Build immutable, hashed half-open `[start,end)` commitments with source-row/revision/evidence provenance and authoritative resource IDs. Reject duplicates/internal conflicts rather than silently dropping rows. Validate each day, grid/window, required duration and applicable calendar coverage. Keep these commitments outside genes and fitness.
4. Give initial/restart construction durable reservation semantics. Options include a fixed-resource availability contract that reset/reconstruction honors, or a carefully specified run-local reduced time domain. A one-time boolean flag is insufficient. A reduced domain alone still does not validate swapped faculty.
5. Add explicit orchestration admission checks before returned descendants enter populations or update best-ever. The original operator functions and original fitness calculations stay unchanged, but rejection of a returned child changes the admitted population and may change subsequent random-call paths. Approve that as the intended constrained mode, with bounded attempts and truthful exhaustion diagnostics. Do not promise byte-identical constrained/unconstrained RNG trajectories.
6. Distinguish a proven-invalid input/constraint conflict from search exhaustion. Failure to find a candidate within a bounded search is **not proof of mathematical infeasibility**. Never repair evaluated chromosomes, soften commitments, modify preferences or fabricate assignments to obtain a result.
7. Revalidate the pinned revision set and trust before saved-best, latest/stopped result, history publication and resume boundaries. Changed/revoked/unavailable authority rejects constrained publication. Validate saved/uploaded seeds against the same snapshot before admission; never silently discard a requested seed or reinterpret old stored results under new commitments.
8. Approve explicit engine-version dispatch/compatibility for legacy checkpoint continuation. Keep old engine verification intact; use reviewed legacy source/version handling or a separately versioned continuation path. Add versioned constrained provenance beside the existing checkpoint representation if approved, with atomic binding and missing-sidecar failure handling. Never disable fingerprint checks or spoof the old engine hash for new behavior.
9. Add backend DTOs and existing-page status/provenance panels only after these execution semantics are agreed. Reuse Generate Schedule, Schedule View, Fitness Analysis and the existing teal/gold layout. The request's reference to an existing purple/orange theme does not match the inspected D1-D9 theme; no theme changes were made.

The request already permits adapter/orchestration work in principle. The unresolved decision is specifically whether new pre-selection admission/retry behavior and a versioned checkpoint-continuation bridge are acceptable under its strict preservation clauses. This report supplies a concrete design for that review rather than silently deciding those semantics.

## Options and tradeoffs

| Option | Effect | Recommendation |
|---|---|---|
| Versioned D10 orchestration with immutable constraints, persistent availability semantics and pre-admission checks | Keeps operator source/math unchanged; explicitly changes constrained-mode admitted population and requires checkpoint compatibility design. | Recommended direction for separate approval; scope legacy continuation and constrained provenance before coding. |
| Make operator validation directly aware of external commitments | Could check swaps at source, but changes protected crossover/mutation validation semantics. | Requires explicit relaxation of the operator-preservation rule. Not implemented. |
| Reject only final outputs in a new route | Does not guide feasible generation and may run after saved-best writes. | Insufficient for D10; not implemented or described as hard-constraint integration. |
| Integrate only section constraints | Existing section support is useful but omits required faculty/room commitments. | Does not satisfy D10; not presented as completion. |
| Runtime replacement of unmodified module symbols to evade source fingerprint changes | Alters effective engine behavior while its original source identity remains unchanged, and adds global/concurrency/provenance risk. | Not used as a fingerprint workaround. Any adapter must be explicitly versioned and bound to checkpoints. |

## Exact changes and validation boundaries

Created only:

- `docs/dashboard-d10-implementation.md` — this blocked implementation/design report.
- `docs/testing/dashboard-d10/preservation-baseline.json` — pre-probe raw-file baseline.
- `docs/testing/dashboard-d10/inspect_integration_boundary.py` — read-only characterization utility.
- `docs/testing/dashboard-d10/20261023T215141091867+0800-boundary/command.json` — sanitized probe evidence.
- `docs/testing/dashboard-d10/manifest.json` — results, preservation/privacy findings and raw artifact hashes; excludes itself.

**Existing files modified: none.** No backend route, model, service, schema, operator, UI, dependency, migration, settings file, academic dataset, saved schedule or historical D1-D9 evidence was changed. No D10 confirmation retrieval, constrained execution, frontend feature, migration, database table, faculty/Chair workflow or GA activation was implemented.

Status by requested validation category:

| Category | Status |
|---|---|
| D8/D9/API/UI integration tests for D10 | NOT RUN — application integration stopped before implementation. |
| Feasible/infeasible constrained GA cases and successful conflict-free output | NOT RUN — no constrained GA implementation; probe results are not substitutes. |
| D10 backend/frontend/browser acceptance, screenshots, production build, focused lint | NOT RUN — no application changes or new UI to validate; no screenshots fabricated. |
| D1-D9 regressions | Not rerun. Application/test bytes match the D9 baseline; prior D9 results remain historical, not fresh D10 passes. |
| Performance/memory/feasible-rate comparison | NOT RUN — no integration or GA execution. Recorded probe elapsed time is diagnostic runtime only, not scheduling overhead. |
| PostgreSQL acceptance | NOT RUN. Existing 17 Phase 4C cases and D9 online acceptance remain unverified. No PostgreSQL operation or migration. |
| Genuine institutional providers | BLOCKED/unconfigured. No fictional provider was installed in production or activated in the probe. |
| Preservation/privacy/hash/whitespace inspection | PASS as recorded in the manifest; all 873 baselined files and protected preference bytes unchanged. |

## Security, privacy and final stop

Evidence stores static findings and fictional identifiers only. Academic rows read internally at import are not printed or retained. The run uses no session or signed receipt; the final scan still checks complete/truncated encoded fragments, credential URIs, key/header/token patterns and locally compares private faculty names without exporting them. No database fixture, HAR or screenshot is archived. Hashes establish artifact identity, not institutional authority or correctness.

Protected preferences, all data/identity/qualification mappings, professor operators, numerical fitness penalties, selection/crossover/mutation/RNG/elitism source, chromosomes, checkpoint files/formats, saved schedules, historical results, original migrations, Git index and HEAD remain unchanged. No generation or provider activation occurred. Existing unconstrained generation behavior remains exactly as before; no new D10 compatibility fallback was introduced.

**Stop point:** approve or revise the versioned orchestration/admission and legacy-checkpoint policy above before D10 application work. Do not claim D10 complete, do not commit/push, and do not begin D11/D12 or C++ work. The fresh evidence supports the architectural stop only.
