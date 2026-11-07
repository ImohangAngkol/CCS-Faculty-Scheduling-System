# U5G — immutable captured-input bundle and consumption qualification

2026-11-05, Asia/Manila. Entry: `main`, `d6db077793da52b7559351a5d0f8e6d54608cb77`.

**PARTIALLY IMPLEMENTED — immutable capture/materialization foundation is implemented and tested; actual V1 optimizer consumption is NOT implemented or verified.** U5G's full completion criterion is therefore **not met**. U5D receipts remain UNVERIFIED, Current Evaluation eligibility is unchanged and Continuous Mode remains disabled for institutional and fictional datasets. This uses the explicitly permitted foundation fallback; it does not claim that a frozen container fixes the optimizer's global reads.

## Entry review and implementation boundary

Read U5D, U5E/R2 and U5F reports, manifests and selective staging plans; traced the actual V1 execution, loading, scoring, checkpoint, history and result paths. Their uncommitted inventories remain separate: U5D 24 paths, U5E-R2 268 paths, U5F 80 paths. Shared working files include `backend/main.py`, the GA/evaluation routers, the common test fixture and Generate/Analysis pages. U5G edits **none** of them. The pre-edit baseline includes all 3,619 existing paths, all 23 academic files, protected preferences/settings, ignored runtime stores, prior evidence and Git index. The 79 U5F artifact hashes passed at entry.

Communicated plan: implement an isolated immutable capture contract with private working copies and strict run/integrity checks; establish original scoring/checkpoint parity separately; install no consumer or verification promotion unless complete dependency binding and compatible checkpoint semantics can be proven. No AGENTS.md was found. No dependencies were installed.

## Actual V1 input dependency graph

The [source map](testing/dashboard-u5g/source-map.json) records current source hashes and function line numbers. No academic row contents are retained.

```text
CSV/JSON + identity mappings + model defaults/availability constructors
  -> Functions module import / preprocessing / fixed-section & preassignment application
     -> cached subjects, sections/students, faculty/eligibility/loads, rooms/calendars
     -> transformed legacy preference DataFrame
        -> ga_service imported aliases -> locals -> population construction

Dashboard preferences/settings + Functions faculty alias + data-file fingerprint
  -> FrozenInputs.capture_inputs -> ContextVar -> existing scoring calls

/run or /stream admission -> U5B context / U5D observation / history templates
  -> decorated run_genetic_algorithm -> initialization -> finite generations
  -> validated progress/history boundaries -> optional checkpoint or best finalization
  -> Saved Best inside engine -> router latest/stopped result

resume -> strict current file + engine checks -> decoded checkpoint state
  -> restored scoring context, working/publication templates, preferences, RNG, monitor
  -> same finite loop; no U5G bundle reference
```

| Input / representation | Actual consumer / change window |
|---|---|
| Faculty identity, cohort, eligibility, qualifications/domains and fixed allowances | `Functions.py` imports legacy preference/load/qualification/eligibility/domain files, identity helpers and Faculty constructors. Cohort completeness remains an F1/F1.5 institutional question. Cached faculty models carry eligibility, workload limits, calendars and assignment state. A new account is not automatically an authoritative roster addition. |
| Subjects and sections | First-semester subject data and consolidated section schedule data become Subject/Section/Student models, component hours, schedules and preassignment declarations. Section-owned restrictions and room/faculty reset semantics differ. Filename does not establish an authorized current academic term. |
| Rooms, slots and patterns | Model constructors and `Functions.py` build resource calendars and meeting patterns. These are optimizer-ready object state, not merely a file hash. `get_available_rooms`, `section_schedule_is_available` and reset/construction helpers retain module-global fallbacks when explicit arguments are absent. |
| Legacy preferences | Imported and transformed `df_faculty_pref` is independently aliased by `ga_service`; passed to initialization/operators/scoring. It can diverge from later dashboard preference files. |
| Dashboard preferences / fitness weights | `FrozenInputs.capture_inputs` reads effective settings/preferences, deep-copies `Functions.list_faculty`, checks the data fingerprint before/after and sets a ContextVar. Fitness helpers reconstruct GASetting and copied preferences from that context when present; otherwise they read source files. This freezes selected scoring data, not the complete loader graph. |
| Engine inputs | `ga_service.run_genetic_algorithm` explicitly reads its `globals()` aliases into locals. Imported aliases can differ from Functions aliases or validation templates. It has no `input_bundle` parameter. |
| Seeds | Saved/uploaded payloads are read after initial engine binding and normalized/reconstructed against templates. A full contract must bind the actual seed content and preserve rejection behavior; a source path or stored fitness is insufficient. |
| Working state | Initialization and restarts reset/mutate resource calendars and assignments; operators copy/mutate candidates. These are legitimate mutable working objects and must not be made shared or globally frozen. |
| Configuration / observation | Six effective parameters, monitor configuration, original scoring version, cached input graph and selected seed all matter. Progress checks continue to compare live source-file fingerprints; changed files currently abort comparable publication. |
| Validation / history | Detached publication/history templates and active scoring context are separate inputs. History reconstruction reuses original validators; it is not proof of earlier optimizer reads. |
| Checkpoint continuation | Existing graph stores working/publication templates, population, best-ever, legacy preferences, scoring context, monitor, configuration and RNG. Loading requires current file and engine identities, matching run/version and hard validation. No bundle field/sidecar contract exists. |
| Result finalization | Original engine can write Saved Best before router latest/stopped output. A wrapper applied only after return cannot establish consumption or guard all persistence. |

Changes can occur between module import, pre-call observation, independent scoring capture, engine-local binding, seed loading, generation callbacks, pause, resume and finalization. The API's process-local admission lock does not lock every source writer or eliminate ABA races. Existing source fingerprints also cover files that may not be semantically consumed.

## Implemented bundle foundation

`backend/services/ga_input_bundle.py` provides an internal, unused-by-V1 foundation API. It has no FastAPI endpoint, provider switch, database access, storage directory, worker, global rebinding, scorer replacement or optimizer invocation.

Contract `ga-captured-input-bundle-v1` contains:

- Canonical run UUID and aware capture timestamp.
- Optional academic-context hash reference; missing context remains None. No year, term, department or institutional dataset is invented.
- Dataset, engine, loader and transformation hash observations supplied by the trusted future caller; these are **not independently verified source authority or loaded-code attestation**.
- Exact six-parameter configuration and its canonical fingerprint.
- Capture implementation fingerprint over the new module and unchanged checkpoint codec source bytes.
- One captured graph containing optimizer templates, fallback templates, legacy DataFrame state/dtypes, scoring context and actual selected seed content, when applicable.
- Verification status limited to UNVERIFIED.

`InputBundle` retains only immutable strings/bytes. It retains no mutable reference to caller models, preferences, settings, DataFrame, seed or configuration. Canonical serialization is UTF-8 JSON with sorted object keys, no bare nonfinite JSON values and strict duplicate-key rejection. The graph reuses the **unchanged allowlisted passive checkpoint encoder/decoder**; no pickle or arbitrary object import/constructor execution is introduced. Graph/list/dictionary traversal, aliases and observed set order are preserved. Equivalent independently constructed unordered sets are **not promised** identical cross-process encodings; this is an observed-representation fingerprint, not a semantic equivalence key.

The SHA-256 bundle fingerprint covers run/time/provenance/configuration and graph, so it identifies the complete capture rather than making cross-run fitness comparable. Different run IDs correctly produce distinct identities. Original captured bytes remain stable after source mutation. `materialize(expected_run_id)` validates the pinned hash, run and schema and returns fresh, private mutable working models on every call, preserving internal aliases. Mutable working copies are necessary for the original scheduling semantics; sharing them across runs is prohibited.

Validation rejects wrong run IDs, changed pinned bytes, malformed/missing/duplicate/noncanonical JSON, unsupported versions/types, VERIFIED claims, unknown fields, broken references, duplicate graph entries, invalid source hashes/configuration/dtypes, seed/configuration mismatch and over-limit records. Errors use neutral codes and do not echo source records. Limits are 16 MiB encoded bytes / 100,000 graph nodes. **They are checked after encoding and do not establish a hard capture peak-RAM bound.** Multiple validation decodes and copied graphs have not been optimized or benchmarked.

Callers must own/quiesce the input graph during capture. This module does not supply atomic loader ownership, lock all source writers, prevent recapture under an already-used run ID, establish institutional authority, or validate full academic feasibility. A manually recaptured object cannot alter an existing bundle, but a future run registry must exclusively pin one approved fingerprint per run. Checksums assume a trusted caller/pinned reference; they are not signatures against an actor who can replace code, data and the reference together.

No raw bundle is persisted or archived. It may contain private academic records in legitimate future use; its private canonical bytes must not be logged or exposed through administrator/browser projections.

## Consumption and receipt contract: explicit failure boundary

`qualification(expected_run_id)` exposes bounded metadata only:

| Stage | Current evidence | Qualification |
|---|---|---|
| Captured inputs | Immutable bytes, run binding, hash and decoded-copy isolation tested | CAPTURED_INPUTS / UNVERIFIED |
| Inputs consumed | No V1 bundle parameter or validated routing through all global/frozen/seed/history consumers | NOT_ESTABLISHED |
| Verified consumption | No complete boundary proof or supported bundle checkpoint version | Unavailable |
| Interrupted / legacy run | Existing U5D observations/absence remain as before | Never backfilled or promoted |

Reasons remain explicit: `CONSUMPTION_BOUNDARY_NOT_INSTALLED`, `SOURCE_CAPTURE_NOT_PROVEN_ATOMIC`, `LEGACY_CHECKPOINT_HAS_NO_BUNDLE_BINDING`. CURRENT eligibility is false and institutional authorization NOT_ESTABLISHED. `require_consumption_boundary` validates the capture and then **always rejects** with `GA_BUNDLE_CONSUMPTION_NOT_INSTALLED`.

This is an additive capture-qualification foundation, **not an installed extension of the U5D serialized receipts/API**. Their strict historical schema, bytes, observation callbacks and UNVERIFIED-only behavior remain unchanged. No path can issue VERIFIED or activate continuous execution. No capture is passed into a real optimizer by application code.

## Why production integration stopped

Passing a graph to an outer wrapper would leave `ga_service` global reads, independently captured FrozenInputs, Functions fallback calendars/sections/rooms, seed loading and validation/history reconstruction outside the proven boundary. Rebinding module globals or temporarily replacing the scorer would introduce shared-state/concurrency hazards and unversioned effective behavior, so neither was used.

Editing the actual consumer/frozen-input/monitor/checkpoint services changes the existing strict engine identity. Supported V1 continuation and its original source-drift rejection must not be silently reinterpreted. A bundle-based continuation that tolerates changed external files differs from the current mandatory file-fingerprint check; removing it for V1 would weaken the existing contract. A stored graph alone does not authorize that change. A separately versioned consumption and continuation design must specify both modes and bind the complete bundle before installation.

This is a stop at the inspected boundary, not a claim that every injection architecture is impossible. No new V1/V2 branch or compatibility bridge was implemented, and no source fingerprints were spoofed or disabled. Existing algorithms, scoring, RNG operations, termination, hard constraints and Saved Best behavior remain unchanged.

## Tests and checkpoint qualification

Fresh final distinct selections: **217 Python cases passed**, **210 frontend contracts passed**, **16 actual Edge scenarios passed**, zero failures/errors/skips. The browser uses intercepted fictional HTTP, not live browser-to-optimizer or database evidence. TypeScript, production build, focused ESLint, Git whitespace and integrity checks passed. Existing TestClient/httpx and AnyIO alias deprecations, Vite mixed-import/chunk warnings and Git dangling objects are recorded without dependency changes or cleanup.

| Selection | Passed | Evidence / limit |
|---|---:|---|
| Bundle foundation | 32 | Repeatable canonical capture, no RNG change, source preferences/weights/models/configuration/frame/cache changes, eight concurrent private materializations, aliases, cross-run rejection, corrupt/missing/forged/oversized data, seed capture and no persistence/activation. |
| Isolated original V1 / copy oracle | 10 | Real checkpoint creation/load/resume, RNG/best/history/schedule parity at pause generations 0/1/2; registry replacement; duplicate/concurrent controls; actual fictional source/weight drift rejection; cancellation/failure; copied-template original scoring/publication parity. |
| U5A/U5B/U5C backend | 99 | Inspected fictional source/context/compatibility cases; excludes legacy roster-backed fitness/history fixtures identified during U5F. |
| U5D receipts | 36 | Original fictional receipt/API/real-engine tests; UNVERIFIED behavior retained. |
| U5E analysis | 20 | Fictional temporary histories and read-only analysis tests. |
| U5F readiness | 20 | Fictional principals, forbidden DB connections and blocked execution. |
| Existing frontend contracts | 210 | U5A–U5F/current dashboard/auth/GA monitoring/history and U5E chart contracts. |
| Existing U5F browser | 16 | Actual Edge/React; synthetic HTTP acknowledgments. Still blocked; no fabricated continuous run. Node reports 17 including the parent suite. |

The 32 bundle tests pass both in the working tree and independently in HEAD plus **only the three new U5G source/test files**, without uncommitted U5D/U5E/U5F application source. They count once above. The 10-case source-snapshot qualification uses empty fictional import tables and explicit D10 models (two fictional faculty/offerings, one room) in a newly owned OS-temp repository copy. Existing dependencies are linked, not installed. The original finite engine and all operators run unchanged; test-only mutation/restart bounds are 1 and 5. Original crossover effort remains unchanged. A copied U5F test harness is new U5G evidence; the original U5F file is not modified.

The extra copy oracle first captures templates/scoring data, runs the **original global-input engine**, reconstructs its payload using the materialized templates, then compares the original fitness/breakdown, checks publication constraints and confirms no RNG change during reconstruction/scoring. **It does not run the GA from the bundle and is not a consumption proof.**

Checkpoint results are deliberately separated:

- Legacy compatible pause/resume and exact RNG/best-ever behavior: passed unchanged.
- Changed external preference/settings files: original `GA_CHECKPOINT_INPUT_CHANGED` rejection passed; no bundle override.
- Missing/corrupt/cross-run bundle bytes: foundation restore rejects them.
- Missing legacy bundle metadata: no metadata inferred or old artifact rewritten; original V1 behavior remains.
- Bundle-bound checkpoint creation/resume and continuation after external-source drift: **NOT IMPLEMENTED / NOT TESTED**, rejected by the new consumption gate. Old checkpoints have no binding to validate.
- Two simultaneous actual optimizer runs: not enabled or claimed. Concurrent materialization tests prove copy isolation only; existing single-process admission remains.

All U5G executions passed. The first development command used selection label `bundle` for the 32 Python tests; the runner subsequently names that selection `bundle-tests`, leaving `bundle` for Vite. Both exact commands remain in separate records and are attributed by command, not just label. Earlier U5F failed/time-limited attempts remain historical; they are not rewritten or counted as new U5G successes. No new PostgreSQL or institutional acceptance was performed; D15 evidence/database were not touched.

## Preservation and exact file scope

**Existing files modified: none.** All 3,619 entry paths must remain byte-identical, including protected local JSON modifications, all 23 academic files, engine/scoring/RNG/migrations, six historical checkpoints and other retained runtime stores, schedules, Saved Best and U5D–U5F evidence. Existing unstaged/untracked work remains present. No Git index/HEAD change, staging, commit, push, reset, clean, overwrite, database operation or runtime store activation was performed.

New implementation/test files:

1. `backend/services/ga_input_bundle.py`
2. `backend/tests/test_ga_input_bundle.py`
3. `backend/tests/test_ga_input_bundle_checkpoint_qualification.py`

New report: this file. New tooling/evidence: `docs/testing/dashboard-u5g/` containing entry/preservation baselines, source map, runner, fictional source-snapshot verifier, audit, exact staging plan, manifest, command results, snapshot proof and original screenshots. The manifest's `exact_checkpoint_inventory` enumerates every literal path. No raw model graph, preference payload, checkpoint, database, session cookie or signed receipt is archived. Privacy inspection includes complete/partial encoded tokens, credential URLs/headers, local private-name comparison, PNG metadata/CRC and visual review. Artifact hashes exclude the manifest itself to avoid self-reference.

## Reproduction and selective checkpoint

From the repository root, with existing dependencies:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5g/run_checks.py bundle-tests
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5g/checkpoint_snapshot.py
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5g/run_checks.py backend-regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5g/run_checks.py receipts
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5g/run_checks.py analysis
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5g/run_checks.py backend
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5g/run_checks.py frontend
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5g/run_checks.py build
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5g/run_checks.py bundle
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5g/run_checks.py lint
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5g/run_checks.py browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5g/audit_evidence.py
```

Runners whitelist OS variables, exclude credentials/database URLs and use new owned temporary paths. The real checkpoint qualification skips outside the verified fictional source snapshot; use the snapshot tool instead of running it directly against academic inputs. Commands never overwrite sealed evidence. Later reruns add artifacts and require a separate manifest addendum; do not rewrite the sealed history.

The [staging plan](testing/dashboard-u5g/staging-plan.json) contains only new whole-file U5G paths; **no partial or existing-file staging is needed**. U5D/U5E/U5F and unrelated work stay outside it. After separate authorization and a fresh branch/upstream/inventory review, suggested commits are `feat(ga): add immutable captured-input bundle foundation` and `docs(testing): archive U5G capture and legacy parity evidence`. Proposed blob OIDs bind the independent three-file source snapshot to those contents. No staging or checkpoint action is authorized/performed here. Readiness is for the labelled foundation, not a verified-input optimization release.

## Required next boundary before a continuous worker

First approve and implement an explicitly versioned V1-successor input-consumption contract: exclusive run-to-bundle pinning; complete source/derived-model capture ownership; private working graphs; explicit routing of every initialization/scoring/operator fallback/seed/history/publication consumer; truthful consumed/verified receipts; and a new bundle-bound checkpoint version with strict integrity/RNG/best-ever restoration. Specify when current source/authority drift rejects publication versus when immutable continuation may proceed; keep original V1 validation intact. Define durable bundle storage, access controls, quotas and missing-sidecar failure before any persistent format is introduced.

Only after that boundary is actually qualified should the next worker milestone introduce bounded managed continuous execution with pause/resume/stop, cooperative safe points, run ownership, CPU/private-memory/wall-time/disk/history budgets, shutdown/recovery and run-local best-so-far persistence. Institutional Chair scope and genuine academic sources remain separate prerequisites. Do not start that worker or activate institutional capabilities as part of U5G.
