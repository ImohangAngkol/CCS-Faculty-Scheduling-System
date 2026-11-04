# U5A: current GA compatibility and result provenance

2026-11-04, Asia/Manila. Entry branch `main`, HEAD `705cc44655ba775259ca21c38f4f10959d9fdf78`. **Status: PARTIAL.** The additive read-only projection and frontend states are implemented and verified. Strict qualification of ordinary deployed V1 records remains blocked by missing verified, captured academic context. Persistent best-selection/provenance changes require separate authorization. No production result was promoted and no historical metadata was backfilled.

The [manifest](testing/dashboard-u5a/manifest.json) records the exact inventory, raw hashes, preserved attempts, final checks and preservation audit. Earlier U4, GA Live Center and research work remains present. The later continuation request was incorporated into this same milestone; work was not restarted.

## Implemented and blocked boundaries

| Area | Status | Evidence and limit |
|---|---|---|
| `GET /api/ga/current-evaluation` | IMPLEMENTED / VERIFIED | Administrator-only read-only projection of existing V1 generation-history files, using existing authentication dependencies. ASGI tests use explicit fictional principals. No new authority model or worker admission. |
| Current/legacy/unknown classification | IMPLEMENTED / VERIFIED | Contract `ga-result-compatibility-v1`. Missing, inconsistent or unsupported provenance fails closed. Known explicit scoring/engine/input differences establish incompatibility for current comparison. |
| Ordinary V1 records as strict current results | BLOCKED | Installed `current_identity()` explicitly reports unresolved year/term. No verified academic context provider or captured term is invented. Actual fictional V1 generation is correctly classified unknown for this reason. |
| Complete-provenance examples | VERIFIED IN FICTIONAL TESTS ONLY | Tests explicitly supply `FICTIONAL-YEAR / FICTIONAL-TERM` and matching recorded context. This is a hypothetical contract qualification, not an installed institutional provider or an existing V1 writer capability. |
| Current Evaluation UI | IMPLEMENTED / VERIFIED | Server projection, loading/retry/error/unknown/empty states, exact scores, recorded provenance, archive links, mobile wrapping and a keyboard-focusable scroll area. |
| Historical Archive / analysis | PRESERVED / VERIFIED | Original values and history remain accessible. Analysis now explicitly separates original recorded evaluations from Current Evaluation. No result is rescored to create compatibility. |
| Automatic Saved Best admission | STILL BLOCKED IN CURRENT UI | Existing `isVerifiedCurrent` guard remains unchanged. The new projection always marks the unproven persistent Saved Best unknown and baseline-ineligible. This is not a new server baseline admission rule. |
| Persistent best replacement / producer metadata | REQUIRES AUTHORIZATION | No write-format change, migration, rewrite, sidecar, reset, deletion or backfill implemented. |
| V2 current-evaluation aggregation | PROPOSED / NOT IMPLEMENTED | V2 retains its separate constrained store, snapshot digest, authority checks and result view. U5A's coverage is explicitly V1 history, not a claim that every GA family was enumerated. |
| Institutional approval / publication | BLOCKED AS BEFORE | Technical fingerprints never confer academic approval. No real provider, Chair authorization or publication behavior changed. |

## Architecture findings

V1 execution in `ga_service.run_genetic_algorithm` freezes scoring inputs, creates or restores the population, evaluates existing fitness, preserves best-ever and calls `save_best_if_better` before returning. Router finalization subsequently writes latest/stopped results. The observational history adapter captures validated generation boundaries without adding fitness calls or consuming GA RNG. History stores checksum envelopes containing an index and immutable per-generation candidates, plus optional analysis observations.

`ga_checkpoint_service.engine_fingerprint` covers original GA Python sources and the existing orchestration/publication/progress/checkpoint/control/chromosome/faculty-analysis services, runtime/dependency versions, preference-policy bridge and its manifest. `evaluation_fingerprint` selects the actual legacy/current preference policy. Strict engine/input checks remain untouched. V2 additionally fingerprints its orchestration, constraints, store, routes and trust contracts. This milestone adds a separate service/router and registers it in `main.py`; no fingerprinted engine source or compatibility manifest changed. A Git revision/date alone is never the compatibility basis.

Captured reporting context supplies preference scoring version, scorer SHA-256, original settings and engine/input identity. U5A uses these observations rather than inferring an approved fitness policy. The descriptive constraint identifier `v1-source-bound-publication-gate` refers to implementation bytes bound by the engine fingerprint; it is not a newly approved academic constraint policy.

`input_fingerprint` hashes the existing CSV/JSON input set. It establishes exact byte identity, not semester completeness, roster authority or academic approval. V1 history has no verified academic-year/term contract. U5A exposes that absence and refuses strict CURRENT classification even when technical fingerprints match. Production `current_identity()` has no mechanism that accepts a client-supplied term or fictional provider.

## Classification contract

`CURRENT_COMPATIBLE` is the contract's technical CURRENT state. It requires all of:

1. Canonical matching run UUID; supported existing index/snapshot schema 1.
2. Existing envelope integrity/schema validation via `history.manifest` and `history.get_generation`; recorded candidate schedule identity and penalty must agree with the index/metrics.
3. Valid ordered unique observations, finite best-ever penalties that do not increase, explicit validated/comparable metrics, consistent input/configuration fingerprints and matching snapshot observations.
4. Consistency between captured execution configuration and index request configuration. The index may contain the supplied request subset while the snapshot includes existing engine defaults; overlapping values must agree. No defaults are manufactured by U5A.
5. Captured reporting policy/context with a supported policy version, scorer fingerprint and matching original settings, engine and inputs.
6. Exact installed engine, preference policy 2, scorer and full input fingerprint match.
7. A server-established verified academic context with a matching captured record. This final requirement is **not currently available in production V1**. It is exercised only using explicitly fictional test input to the classifier.

`LEGACY_INCOMPATIBLE` requires sufficient consistent captured metadata and an explicit known difference: preference policy, engine/scorer fingerprint or input context. This name denotes incompatibility for current comparison; it does not prove chronological age, historical invalidity or institutional disapproval. An unknown schema/policy or corrupt/inconsistent record stays `UNKNOWN_COMPATIBILITY`, not an assumed mismatch.

Missing context, producer identity, unvalidated/noncomparable metrics, malformed IDs, nonfinite values and unrecognized provenance remain unknown. Valid zero and finite negative observations are preserved exactly. No score is rounded, clipped, replaced by zero or recomputed. Production's unresolved academic context produces `ACADEMIC_CONTEXT_NOT_ESTABLISHED`; no timestamp fallback exists.

The API scans at most 200 V1 run directories and validates at most the existing 10,001 indexed observations per run. It does not follow a run-directory symlink outside the configured history root. Unreadable canonical run records receive an unknown finding; invalid raw directory names are not exposed. An unreadable record or scan limit makes coverage incomplete, count null and global best null. Source/input drift during the projection returns 409. Existing server read wrappers provide sanitized 422/503 handling; GET query strings cannot override the classification.

Best selection considers only completed CURRENT records. It retains their exact observed best-ever score and deterministic UUID tie order. Failed/interrupted/paused runs may have compatible observations but cannot supply the current best. Different configuration fingerprints cannot supply one overall best: the response reports `INCOMPARABLE_CONFIGURATIONS` and best null. No cross-policy/configuration equivalence is asserted. The best is a **recorded candidate**, not a verified Saved Best file or an institutionally published schedule. The read does not re-prove mathematical feasibility under an external institutional calendar or reconstruct a seed.

Checksums are the existing local storage-integrity boundary, not signatures proving institutional authenticity. Neither a client `compatible:true` nor an arbitrary result field can promote an unproven file. The frontend validates the versioned projection's identities, count, candidate membership, completion state, exact best selection and configuration grouping; it does not determine scoring compatibility independently.

## Baseline findings

Fresh is the existing default. Explicit saved/uploaded baseline requests reconstruct the chromosome through existing hard gates and evaluate its starting score under the active scorer. The old stored penalty is not used as the initial population's freshly evaluated seed score. Those admission/scoring paths are unchanged.

However, `chromosome_service.save_best_if_better` compares the new fitness against the old persisted penalty when subject keys agree, or replaces when offering keys differ. The saved file does not carry sufficient captured engine/policy/term provenance to justify that cross-run comparison. U1's existing frontend guard continues to block automatic/unverified Saved Best use. U5A adds no backend admission bypass, no deletion and no persistent correction. Direct explicit backend baseline requests retain their existing behavior; a presentation guard must not be claimed as a new server security boundary.

V1/V2 checkpoint integrity/engine/input rejection and legacy policy dispatch remain unchanged. The three existing fictional V1 creation/load/continuation cases plus the strict-loader test passed in the D10 regression run. Historical checkpoint bytes remain preserved; passing current-release fixtures does not retroactively establish historical compatibility.

## Frontend integration

Saved Chromosomes and Generation History share `CurrentEvaluation`. Complete-provenance fictional examples show exact current penalties and links to their actual run. Empty verified scans show Current Runs 0, current fitness dash and Saved Chromosome None. Loading, denied/error or incomplete scans use unavailable count/fitness instead of zero-filling. Per-run classifications and reasons remain visible. Archive inspection never becomes baseline admission.

Current Evaluation has abort cleanup and stale-request protection, independent retry, semantic labels, ordinary keyboard controls and the established teal/gold design. Its bounded table scroll region is focusable and mobile content does not overflow the document. Full screen-reader/WCAG/device conformance was not established.

Fitness Analysis preserves original scoring/report data and U4 analytics. Its source note points to separate Current Evaluation and labels loaded candidates as original evaluations. Generate Schedule and the Live Center retain their existing context, transports, control flags and backend acknowledgement semantics. U5A makes no new claim that a fresh live run is strict CURRENT merely because it started recently or has a low penalty. The old `resultPresentation.isVerifiedCurrent` remains fail-closed specifically for metadata-poor saved baselines; it is not used to classify the new server projection.

## Fresh test results and limits

| Check | Final result | Scope |
|---|---|---|
| Focused U5A backend | 20 passed, 0 failed/errors/skipped | Pure classifier; fictional temporary history; read-only ASGI authorization; drift/corruption/bounds; real fictional V1 generation showing missing academic context stays unknown |
| Existing D10 regressions | 52 passed, 0 failed/errors/skipped | V1 checkpoint continuation, V2 engine and V2 API. Executed earlier in this milestone, before the later strict-context refinement; engine sources are unchanged. V2 API fixtures used temporary SQLite. |
| New frontend contracts | 16 passed, 0 failed/cancelled/skipped | Exact zero/negative/decimal values, missing metadata, policy/context mismatch, forged best/count, duplicate IDs, configuration separation, immutable data and UI cleanup |
| Existing frontend contracts | 182 passed, 0 failed/cancelled/skipped | U1-U4, Live Center, authentication/session races, metadata/preferences, history and fitness reporting |
| U5A browser | 14 scenarios passed (15 Node tests including parent) | Actual Edge/React; intercepted fictional HTTP, including fictional complete academic context |
| Existing browser regressions | 119 scenarios passed | U1 12, U3 15, U4 21, Live Center 20, existing GA 51. With U5A: 133 child scenarios / 139 Node tests including six parents. |
| TypeScript / Vite / focused ESLint | Exit 0 / 0 / 0 | Existing mixed-import and large-chunk build warnings retained; final main JS approximately 1017.21 kB. |
| Git integrity / whitespace / privacy / preservation | See manifest | Read-only Git check; no reset, normalization, staging or history rewrite. |

Browser tests are actual rendering/interactions against mocked HTTP. They are not live FastAPI/worker/checkpoint/PostgreSQL or institutional acceptance. Backend API tests are real in-process FastAPI requests with dependency overrides, not browser evidence. Fictional V1 tests use actual GA functions/operators with compact D10 resources and preserve/restore RNG state. No production GA run occurred.

Two installed dependency warnings remain: Starlette's httpx TestClient deprecation and anyio's BlockingPortal alias deprecation. No installation or upgrade was performed.

### Temporary-directory and database scope qualification

The user reported a separate manual pytest attempt with **11 setup errors, 7 deselections** at the inaccessible `pytest-of-User` root. That is user-attributed environment evidence, not a reproduced U5A assertion failure or a newly executed pass. No such directory was deleted, taken over, chmodded or tested with administrator privileges.

Later backend commands use `--basetemp` with a fresh UUID-named child under the resolved OS temporary root, checked not to exist before pytest starts. The shared autouse fixture redirects checkpoints/history under `tmp_path`. The fictional V1 baseline fixture additionally redirects Saved Best; V2 fixtures redirect their own store and use owned SQLite. No cache provider is used by final commands. Temporary paths and exact commands are recorded. No cleanup targets an existing user directory. Environment-variable absence was not treated as isolation proof; fixture sources and actual redirections were reviewed.

**Scope exception:** the earlier 52-case D10 regression command included temporary fictional SQLite schema/row writes. This exceeded the blanket no-database-writes instruction. It did not connect to PostgreSQL or mutate an existing application, retained D15, production or institutional database. No further SQLite workflow tests were run after recognizing the exception. This report cannot certify zero database writes across every test process. Owner review of this disclosed exception is required before an unqualified checkpoint signoff. The new U5A endpoint and focused API tests themselves do not write a database.

### Preserved unsuccessful attempts

- `20261104T072245641383+0800-backend`: 15 passed, 2 failed. New test mistakes: reloading the projection reset its fictional identity stub, and a fictional principal used a nonexistent constructor field. Corrected test setup without weakening assertions. Initial pytest cache warnings were additional environment diagnostics; final commands disable the cache provider.
- `20261104T072452708699+0800-build`: exit 2, unused compatibility-notice import after replacing the old static panel. Removed that unused import; later builds passed.
- `20261104T155822987037+0800-browser`: 2 passed, 12 failed, 1 cancelled including parent/descendant outcomes. An aborted old-document intercepted request raised `Invalid InterceptionId`; the parent ended and later tests could not start. These are not twelve independently reproduced application defects.
- `20261104T160022783888+0800-browser`: all 14 child scenarios passed, parent failed on one remaining aborted-request diagnostic. The harness now accepts only exact old-document cancellations or matching network IDs with browser-reported `Network.loadingFailed.canceled`; other fulfillment errors still fail. Final repeated runs passed all scenarios.
- `20261104T160904884620+0800-integrity`: exit 128, Git ownership check in the sanitized child environment. The rerun uses process-local `-c safe.directory=<exact repository>` for read-only fsck. No global Git configuration/ownership change. Final fsck exit 0 reports dangling objects, not corruption; nothing was removed.

The first new privacy-audit pass stopped on a scanner false positive: the suffix of the DTO field `institutional_authorization` matched the Authorization-header pattern. A word-boundary correction retains positive Authorization/Set-Cookie detection while excluding that noncredential status field; a separate audit-notes artifact records the diagnosis. No source/evidence value was redacted.

All successful and unsuccessful records remain. Earlier passing 17/18-test and 13-contract runs predate added cases and the stricter continuation rules; final counts above supersede them, without rewriting their outcomes.

## Screenshots

Final unedited fictional captures: `testing/dashboard-u5a/20261104T160715186919+0800-browser/`.

- [Current candidate example](testing/dashboard-u5a/20261104T160715186919+0800-browser/U5A-B01-current-best.png)
- [Fictional provenance](testing/dashboard-u5a/20261104T160715186919+0800-browser/U5A-B02-provenance.png)
- [Unknown compatibility](testing/dashboard-u5a/20261104T160715186919+0800-browser/U5A-B05-unknown.png)
- [Mobile presentation](testing/dashboard-u5a/20261104T160715186919+0800-browser/U5A-B13-mobile.png)

Every unique PNG was visually reviewed; the manifest hashes duplicates and verifies PNG structure/metadata. The CURRENT example explicitly says FICTIONAL-YEAR / FICTIONAL-TERM and does not demonstrate production current classification. No screenshot was generated or edited.

## Exact implementation scope

Existing files extended from U5A entry state:

1. `backend/main.py` - register the additive protected GET router.
2. `frontend/src/pages/admin/ChromosomeViewer.tsx` - replace the static Current Evaluation panel with the read-only projection.
3. `frontend/src/pages/admin/GenerationHistory.tsx` - shared current panel and explicit archive context.
4. `frontend/src/pages/admin/FitnessAnalysis.tsx` - original-evaluation label and compatibility explanation only; earlier U4/Live work retained.
5. `frontend/tests/resultPresentation.test.mjs` - locate assertions in the shared component after extraction.
6. `frontend/tests/evaluationCoverage.test.mjs` - retain baseline/empty-state assertions against the shared component.
7. `frontend/tests/resultPresentation.browser.test.mjs` - explicit empty projection fixture for existing U1 scenarios.
8. `frontend/tests/evaluationCoverage.browser.test.mjs` - explicit empty projection fixture and wait for its asynchronous state.

New implementation/tests:

- `backend/services/ga_result_compatibility.py`
- `backend/routers/ga_evaluation.py`
- `backend/tests/test_ga_result_compatibility.py`
- `frontend/src/services/currentEvaluation.ts`
- `frontend/src/components/ga/CurrentEvaluation.tsx`
- `frontend/tests/currentEvaluation.fixtures.mjs`
- `frontend/tests/currentEvaluation.test.mjs`
- `frontend/tests/currentEvaluation.browser.test.mjs`

New documentation/tooling: this report; `docs/testing/dashboard-u5a/run_checks.py`, `audit_evidence.py`, `preservation-baseline.json`, `manifest.json`; and the exact timestamped JSON/PNG evidence enumerated by the manifest. Existing GA services, schemas, fingerprints, operators, preference/workload mathematics, settings, eligibility, original migrations, baseline admission, authority and database code were not changed.

## Preservation and Git

The entry baseline covers **3,039 paths**, including all **23 academic data files**, protected local preference/settings raw bytes, existing saved schedules/checkpoints/results, historical research/evidence and Git index. Eight source/test extensions are intentional; the other **3,031 baseline paths must match byte-for-byte** in the final audit. Existing local modifications to the protected files remain unstaged and unchanged. No original institutional record or historical evidence was rewritten. Generated ignored build output is not checkpoint inventory.

Branch remains `main`, HEAD `705cc44655ba775259ca21c38f4f10959d9fdf78`; nothing is staged. No commit, push, branch switch, reset, restore or clean occurred. Existing unrelated U4, Live Center and research changes remain in the working tree. The manifest records tracked changes and the exact U5A inventory, rather than claiming every dirty path belongs to U5A. Git LF/CRLF notices are distinct from whitespace errors; protected data was not normalized.

## Reproduce safely

From the repository root in PowerShell, with the already installed environment:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5a/run_checks.py backend
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5a/run_checks.py focused
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5a/run_checks.py regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5a/run_checks.py browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5a/run_checks.py u1-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5a/run_checks.py u3-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5a/run_checks.py u4-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5a/run_checks.py live-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5a/run_checks.py ga-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5a/run_checks.py build
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5a/run_checks.py bundle
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5a/run_checks.py lint
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5a/audit_evidence.py
```

Each test command creates a new attempt directory; existing evidence is not replaced. The audit replays the frozen manifest and will reject unreviewed additions. `backend-regressions` is retained as the exact earlier command definition but **must not be rerun under the no-database-writes scope**: its D10 API fixtures use SQLite. Additional evidence needs a reviewed addendum, not overwriting this manifest.

## Required next decision

**PROPOSED:** approve a server-owned run-context contract binding verified year/term, roster/offering scope and immutable inputs to producer engine/policy/configuration and result identity. Determine the authorized academic-context source independently of generic administrator or Chair publication roles. Reuse existing academic/confirmation metadata only through a separately reviewed provider; no missing scope should be guessed from filenames, names, dates or timestamps.

**REQUIRES AUTHORIZATION:** versioned durable producer/context capture and version-aware Saved Best comparison, with strict checkpoint compatibility and failure/recovery design before editing fingerprinted persistence services. Decide whether separately stored immutable provenance can be bound atomically to existing artifacts or whether an explicitly versioned result format is required. Either entails new writes and cannot be implemented in U5A. Database migration requirements depend on that approved design; U5A adds none. No historical backfill should fabricate provenance.

**Checkpoint recommendation:** the read-only foundation is available for manual code/evidence review. Do not mark U5A fully complete or give an unqualified checkpoint signoff until the owner reviews the SQLite scope exception and accepts the documented academic-context/persistence blockers. Do not start U5B or persistent integration automatically. Genuine institutional activation remains BLOCKED.
