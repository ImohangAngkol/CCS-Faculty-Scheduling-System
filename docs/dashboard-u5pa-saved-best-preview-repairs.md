# U5P-A: Saved Best context integrity and Schedule Applications repair

Completed 2026-11-09, Asia/Manila, on `main` at `ec21a67efed82f085d5e2134ef6002cf5ac69eed`. The two scoped correctness repairs are implemented and qualified in isolated fictional environments. Production admission remains **BLOCKED**, Continuous Optimization remains **DISABLED**, active checkpoint restoration remains blocked, and the seven-day experiment remains **NO-GO**.

Saved Best now declines unverified or incompatible replacement. This is a safety repair, not activation of trusted institutional Saved Best promotion. The fixed HTTP execution path still lacks an independent verifier of actual input consumption and academic scope. Its automatic Saved Best write therefore returns UNVERIFIED without reading or changing the archive. Per-run generation/results/history remain available. Schedule Applications now retains a valid preview when only published-history loading fails, with independent history retry.

## Investigation and original defects

U5O's frozen three-case characterization passes against an owned snapshot of the original committed U5O source. The runtime persistence/read/seed/analysis map is [saved-best-path-map.json](testing/dashboard-u5pa/saved-best-path-map.json). It also records notebook code-cell locations without reading/exporting notebook output or executing notebooks.

Original `save_best_if_better` replaced an archive outright when offering sets changed, otherwise compared raw fitness numbers without proving academic context or objective compatibility. The authoritative original GA minimizes penalty: lower is better, including exactly zero. Different preferences, faculty inputs, scoring settings or department/term cannot establish improvement merely through a lower scalar. Existing seed loading separately reconstructs, validates and evaluates against current inputs; it does not admit a historical stored scalar as the candidate's current score.

Original Schedule Applications `open` awaited preview and history in the same try/catch. A history-only error cleared both preview and history. The production backend still independently verifies application authority, Chair decisions, complete-schedule validity, version and transaction ownership; this repair does not alter those checks.

## Saved Best contract and implementation

New `backend/services/saved_best_policy.py` implements `saved-best-context-v1` with explicit decisions: ELIGIBLE, INCOMPATIBLE and UNVERIFIED. It has no GA scoring, database, API, RNG or institutional-data dependency.

| Required context | Purpose |
|---|---|
| Academic year, term, department, dataset identity | Scope and source identity; no inference from filenames or timestamps |
| Faculty, subject, preference fingerprints | Actual evaluation inputs |
| Scoring-configuration and constraint fingerprints | Applicable objective and hard/soft definitions |
| Engine, fitness-policy and chromosome versions | Evaluation/representation compatibility |
| Input-bundle and loaded-model fingerprints | Exact capture provenance |

All fields are required and strictly validated. Search seeds, number of generations and population size are not direct objective-comparison dimensions. However, different opaque loaded/bundle fingerprints are not silently ignored: even with all semantic fields matching, an independent verifier must prove complete evaluation-input equivalence under its validity guard. Without that proof, the decision is UNVERIFIED. A fictional test exercises actual U5H runs with different run/capture identities and generation counts, proves equality of the complete materialized evaluation graph excluding only search configuration, and compares only after both technical consumption receipts have been checked. This fixture is not an installed production equivalence provider.

The verifier must supply a coherent guard, current snapshot, authenticated record attestations and verification. Record content, context and storage-policy source are hash-bound and attested; a self-declared JSON hash does not grant trust. An institutional integration must establish consumption, scope, record authenticity and validity through commit, including revocation/fencing behavior. `configured_verifier()` returns None in deployment; no client role, environment flag or saved label installs one.

Compatible candidates minimize the original fitness value. Exact ties preserve incumbent bytes; zero is not treated as missing. Offering-set differences, preferences, policy, scope or other semantic differences decline replacement. Missing/corrupt historical provenance declines replacement and preserves the old file. No migration, alternate archive creation or institutional-record deletion occurs.

The isolated qualified storage path uses per-path thread and OS process locks, bounded lock acquisition, a same-directory temporary file, file flush/fsync and atomic replacement. Candidate and incumbent JSON are bounded to 64 MiB. Failed temporary writes remove only their own temporary file. Context and attestations are rechecked after locking. Tests exercise threads, three real processes, restart, corrupted records and failed atomic replacement. This does not qualify arbitrary deployment roots, hostile ancestor replacement or physical power-loss durability; no directory-fsync guarantee or production storage policy is claimed. Unconfigured execution performs no archive IO, serialization or comparison.

The two-argument `chromosome_service.save_best_if_better` interface is retained. Only this function changed in that existing module; the auditor compares every other source line. It pins the new helper's exact SHA-256 in its already engine-fingerprinted source, before import/admission. Missing or modified helper bytes fail closed. This covers the new dependency without changing the fingerprint algorithm or inventing an old engine identity. Legacy read/download/status/upload/seed helpers remain unchanged. Manual notebook/file operations are outside this runtime guard and have not been executed.

## Engine and checkpoint compatibility

The persistence caller's source edit genuinely changes current engine identity. Strict fingerprint rejection remains enabled, including `GA_CHECKPOINT_INPUT_CHANGED`; no compatibility hash was spoofed. Earlier release checkpoints are not promised resumable by this repair. All six retained historical checkpoints and all baseline schedules remain byte-identical.

Fresh current-release V1 fixtures really write, load and continue checkpoints in disposable storage. Three fixture records include source/input fingerprints, seeds, continuation points and schedule/RNG equality; raw checkpoint payloads are not archived. Final fixture engine fingerprint: `55f77a5008e842161f057e1f09ca3c33e7577111678808ae504b4359177fa3ad`. Earlier interim-release fixture records remain intact and must not be mistaken for the final release.

Original nonzero parity is **455.0**, with equal assignments, fitness breakdown, histories, faculty accounting and RNG state, including worker parity. U5H's existing prohibition on legacy automatic Saved Best writes is unchanged. No production optimizer, fitness equation, selection, crossover, mutation, termination or numerical workload rule was edited.

## Schedule Applications implementation

`PublishedHistory` owns its loading/data/error state, AbortController and retry. History-only failure cannot clear preview state or its authorized controls. History retry issues no preview request. Successful application refreshes preview and queue, then independently refreshes history.

Preview requests use cancellation and a monotonically changing operation epoch. Changing selection, refreshing the queue, filtering or unmounting invalidates pending detail/confirmation and ignores stale completions. Changing authenticated principal remounts the state owner. Backend-returned current authorization, command and validation remain necessary before submission. Idempotency keys and backend endpoints are retained. The API wrapper adds only optional AbortSignal forwarding.

No department selector or new authority is invented. A scope-change test simulates changed server-authorized queue contents after refresh and verifies old data cannot return. Backend application authority, Chair decision history, concurrency/rollback and immutable publication rules remain unchanged. The teal/gold presentation is preserved.

## Validation results and attribution

All tests below were newly executed during U5P-A. Command records retain exact selections, timestamps, exit codes and sanitized output. Repeated attempts are not added to coverage totals. The selected Python count is a sum of test outcomes across named selections, not proof of 1,033 unique test functions or an unrestricted full-repository run.

| Selection | Passed |
|---|---:|
| New Saved Best context/ownership/actual-U5H tests | 48 |
| Dashboard backend regression selection | 458 |
| Existing backend regressions | 99 |
| Receipt race / receipt / consumption | 19 / 36 / 39 |
| Bundle / admission / deployment qualification | 32 / 50 / 49 |
| Identity / preference scope / analysis / readiness | 16 / 3 / 20 / 20 |
| Supervision smoke / worker / original parity | 1 / 32 / 5 |
| Current V1 continuation / recovery / parent | 10 / 40 / 7 |
| V2 engine / V2 API | 30 / 18 |
| Final live HTTP wrapper | 1 (22 browser scenarios) |
| **Selected Python outcomes** | **1,033 passed** |

Broad regression selections ran against intermediate repair snapshots before the final helper-source pin and cross-capture equivalence refinement. The directly affected **48 Saved Best, 5 parity, 10 V1 continuation, 39 U5H consumption and final live wrapper** were rerun against exact final helper/caller bytes. Snapshot proofs bind those source hashes. Broad earlier results are preserved evidence, not falsely described as all executed against the final source.

| Frontend qualification | Result |
|---|---|
| Working UI including preserved unrelated work | 388 contracts passed |
| Proposed U5P-A-only UI snapshot over committed U5O | 342 contracts passed |
| TypeScript, production bundle, focused ESLint | Passed in both snapshots |
| New Edge/React intercepted-HTTP scenarios | 10 passed in each snapshot; runner reports 11 including parent |
| Existing Schedule Applications intercepted browser scenarios | 16 passed; runner reports 17 including parent |
| Final Edge → real FastAPI → disposable SQLite | 22/22 scenarios passed; no JavaScript runtime errors |
| Earlier successful working-UI extended live survey | 23/23, including an additional route survey |

The 10 focused browser scenarios cover history failure/retry, preserved controls, invalid/forbidden previews, selection/scope switching, stale completions, refresh, missing application authority and anonymous access. Their HTTP responses are intercepted fiction, not live FastAPI authorization proof.

The 22 final live scenarios use actual authentication/CSRF, fictional authority providers, SQLite transactions, real constrained V2 generation, faculty request, Chair review, controlled application, versioned timetable refresh, rollback, concurrency and trust/error recovery. The added U5PA-A01 injects only history failure, revalidates the preview, observes VALID/available action controls, removes the fault and retries history independently. No institutional database or real publication is involved. Initial published-source handoff is an explicit fixture step; it is not proof of a production initial-publication workflow.

Genuine PNGs, browser observations and exact scenario outcomes are retained with all attempts. The final visual/CRC/metadata inventory contains 89 PNGs, including duplicates. Some viewport captures omit below-fold content; DOM assertions, not screenshot filenames, establish the associated behavior. No screenshot was fabricated, edited or generated.

## Failed attempts, warnings and limits

All seven unsuccessful command records plus two initial harness/environment failure records are retained in [attempt-reconciliation.json](testing/dashboard-u5pa/attempt-reconciliation.json):

- Initial root pytest attempt encountered 37 setup errors from a sandbox temporary-directory permission issue before acceptance. Its retained terminal output was truncated; it is not presented as full diagnostic output. Subsequent owned snapshots isolate fictional input/temporary paths.
- A harness initialization attempt failed before browser launch because its route-survey fragment was missing. Reuse of the committed U5O fragment corrected the harness.
- Initial lint found synchronous state-setting in an effect and a ref-cleanup warning. The page was corrected and final lint passes.
- Three focused-browser attempts exposed harness issues: overbroad interception of Vite source imports, a fictional queue DTO mismatch and a premature click during queue loading. Exact API-origin interception, correct fixture DTOs and enabled-control synchronization corrected those failures without weakening assertions.
- Two late live-render failures stopped at a route heading or Approved requests heading. Their causes remain **UNRESOLVED**; unchanged application reruns passed. Vite cache under a shared dependency junction was an isolation risk, so new disposable snapshots place cache in their own root. This is not proof that cache sharing caused the historical failures. The final cache-isolated live run passed all 22 scenarios.
- Frozen U5O characterization `test_characterize_legacy_saved_best_comparison_without_provenance_gate` expects the old unsafe update. Original U5O snapshot: 3 passed. Current repaired snapshot: **2 passed, 1 failed**. This historical assertion was neither deleted nor weakened. The mismatch is expected for a characterization of a removed bug, but a whole-repository green pytest claim is unavailable. A separately reviewed historical-test collection/migration policy is required before that claim.

Existing backend dependency deprecations and Vite dynamic-import/chunk advisories remain. No dependency was installed and no arbitrary timeout increase, test deletion or algorithm adjustment was used to obtain passing evidence. PostgreSQL acceptance was not rerun; retained D15 evidence/state was not operated on.

## Preservation and privacy

The entry baseline records **4,658 raw paths**, including all 23 academic data files, both protected JSON files, original GA sources, migrations, Saved Best, checkpoints/history, historical evidence, unrelated work and Git index. Exactly three authorized existing paths changed; **4,655 baseline paths remain byte-identical**. Membership of protected runtime trees also remains unchanged.

The original 11 tracked modifications and 958 unrelated untracked files remain intact. Their values, including protected preference/settings content, were not printed or edited. No PostgreSQL connection, credential operation, staging, commit, push, deployment, restoration or continuous execution was performed. Prior U5G–U5O manifests contribute **1,029 artifact references**, independently rehashed without modifying those manifests.

Sanitized text is checked for private faculty-name matches locally without exporting names, credential URLs, private keys, complete/truncated encoded tokens and authentication markers. A single exact intercepted-fixture CSRF literal is explicitly treated as a noncredential fixture in scan-only logic; no general token exemption or evidence rewriting is used. Raw DBs, signed receipts, cookies, authentication headers and private Saved Best payloads are not archived. Hashes establish bytes, not institutional authority.

## Exact changes and proposed checkpoint

Existing files modified, all clean at entry:

1. `backend/services/chromosome_service.py` — guarded automatic Saved Best persistence only.
2. `frontend/src/api/scheduleApplications.ts` — preview AbortSignal forwarding.
3. `frontend/src/pages/admin/ScheduleApplications.tsx` — independent history lifecycle and stale-preview protection.

New application/test files:

- `backend/services/saved_best_policy.py`
- `backend/tests/test_saved_best_context.py`
- `frontend/tests/savedBestPreviewRepair.test.mjs`
- `frontend/tests/savedBestPreview.browser.test.mjs`

New documentation/tooling/evidence: this report and the exact recursively enumerated `docs/testing/dashboard-u5pa/` files. The sealed [manifest](testing/dashboard-u5pa/manifest.json) supplies every path and raw SHA-256; [staging-plan.json](testing/dashboard-u5pa/staging-plan.json) supplies the exact selective inventory and proposed raw Git blobs. Those inventories are canonical rather than directory-wide staging instructions.

No actual staging was performed. None of the three modified paths contained unrelated entry edits, so partial staging is unnecessary. Exclude all 11 original modifications and all 958 pre-existing untracked paths. Proposed logical commits: Saved Best service/tests, frontend preview/history repair/tests, then qualification tooling/report/evidence. Use explicit literal paths, preserve tested source bytes with `core.autocrlf=false`, and review CRLF-aware whitespace/blob identity. Changing line endings changes source-byte engine identity and requires fresh qualification. Calculate the plan/manifest blobs after sealing, avoiding self-referential hash claims.

The U5P-A-only frontend snapshot was tested independently of the 21 unrelated UI overlay paths. Backend snapshots use committed source plus the exact intended repair overlay, with isolated fictional loaders and stores. This is proposed checkpoint qualification, not a staged or committed snapshot.

## Reproduction

From the repository root in PowerShell, using installed dependencies only:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pa/backend_snapshot.py saved-best
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pa/backend_snapshot.py parity
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pa/backend_snapshot.py legacy
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pa/backend_snapshot.py consumption
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pa/frontend_snapshot.py contracts-all --checkpoint-ui
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pa/frontend_snapshot.py build --checkpoint-ui
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pa/frontend_snapshot.py bundle --checkpoint-ui
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pa/frontend_snapshot.py lint --checkpoint-ui
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pa/frontend_snapshot.py preview-browser --checkpoint-ui
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pa/backend_snapshot.py repair-live
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pa/audit_evidence.py
```

`build` is the installed TypeScript command; `bundle` is the Vite production build. Snapshot runners create new evidence and owned OS-temp roots, require local Windows browser/process permissions for native tests, and never copy institutional data into the snapshot. Their immutable audit assumes the sealed inventory; after any rerun, create a separately reviewed evidence addendum rather than silently rewriting this manifest. Do not run the new backend module directly against the working application's academic loaders.

## Remaining blockers and U5P-B recommendation

The scoped repairs meet the demonstrated safety and workflow criteria. Trusted production Saved Best promotion is **not implemented**: it needs independent actual-consumption/academic-scope verification, authenticated historical attestations, complete cross-capture equivalence and deployment-storage fencing qualification. Some unchanged legacy Generate Schedule guidance still assumes generation can update Saved Best; that page contains unrelated user edits and was preserved. Read-only capability messaging should be qualified before claiming a complete production Saved Best experience.

Recommend U5P-B qualify the trusted Saved Best provider/equivalence and persistence integration contract, truthful capability messaging, and the frozen historical-test collection policy. Preserve unresolved browser-render failure evidence and use owned caches in future acceptance. Separately qualify resource limits, power/recovery and deployment authority before any seven-day experiment. Do not activate production admission, restoration, continuous execution or C++ work as part of this milestone.
