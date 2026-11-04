# U5C: institutional academic-context source qualification

**U5C-R1 current verification:** browser initialization is working in the separately verified execution context. All 8 U5C, 17 U5B and 14 U5A browser scenarios passed. An independent source-snapshot rehearsal also passed, subject to the explicit fictional-data and unchanged-release-byte prerequisites below. The original U5C sections retain their historical attempt results; the U5C-R1 addendum and [R1 manifest](testing/dashboard-u5c-r1/manifest.json) provide the current review. Institutional activation remains BLOCKED.

Investigated and implemented 2026-11-04, Asia/Manila, on `main` at `4bf03c144d5a404889a83cc89befad0495b673e5`. U5A and U5B reports/manifests were reviewed before implementation. The entry state includes unfinished U4/Live Center/research work and both protected local JSON modifications. No authority source was supplied or activated.

**Outcome: partial read-only foundation; production qualification remains BLOCKED.** Five source tables can be compared with their current in-process cached tables. This cannot establish the identity of the complete input graph consumed by a particular optimization run. No institutional academic year, semester, department, dataset revision, stewardship or approval has been established.

## Written implementation plan

The plan was communicated before application edits: document the full source/consumer boundary; introduce strict source declarations and complete semantic projection comparison; observe only the caches whose transformations can be accounted for; expose an administrator-only read-only status; test fictional matching/drift/permission cases and U5A/U5B regressions. Preserve capture, classification, GA algorithms, fingerprints and persistence. Stop production activation at the missing authority and actual-consumption binding.

The declaration/comparison helper is an adapter-design precheck, not an institutional provider or a new GA input source. Neither it nor the endpoint can return CURRENT eligibility. No client can submit declarations or approve a source through this module.

## Source-to-consumer dependency map

All paths below are relative to the repository; no private faculty records are reproduced. A filename, a stable UUID, a data-table match, an administrator account and a checksum each establish different facts. None alone establishes institutional approval.

| Source | Loader / transformations | Consumer / unresolved boundary |
|---|---|---|
| `backend/data/first_sem_bsit_subjects.csv` | `genetic_algorithm/utils/Functions.py`: import-time `df_subjects`, `_create_subject_with_domain`, section expansion into `list_subjects`, track filtering | `services/ga_service.py` imports `list_subjects`; initialization, operators and publication templates consume models. Filename is not a verified term/year declaration; source rows are not identical to generated offerings. |
| `backend/data/BSIT_Consolidated_Subject_Schedules.csv` | `Functions.py`: import-time `df_section_schedules`; `apply_fixed_section_schedules` applies recognized section closures, reports skipped rows | Section availability helpers use section time blocks. A matching source frame does not prove every row became an applicable fixed commitment. |
| `backend/data/Faculty Preferences V2.csv` | `Functions.py`: cached legacy preferences, priority mapping, stable faculty-code mapping; `dct_fac_subj`, `df_faculty_pref` | Faculty cohort construction and legacy preference scoring. Missing legacy preference membership can omit faculty; authentication/account registration does not make a complete GA roster. F1/F1.5 institutional roster integration remains blocked. |
| `backend/data/Faculty Admin, Research and Extension.csv` | `Functions.py`: cached faculty loads; drop unnamed columns, normalize names, `dct_fac_loads`, constructor defaults for unmatched rows | `genetic_algorithm/models/Faculty.py` teaching targets and hard load ceiling; recognized non-teaching allowances are inputs, not scheduled activities. Actual semester-specific authorized allowances are unverified. |
| `backend/data/faculty_qualifications.csv` | `Functions.py`: `df_faculty_qualifications` and specialization dictionaries | Faculty specialization metadata; not a verified approved alignment rubric. |
| `backend/data/faculty_subject_eligibility.csv` | `Functions.py`: `df_faculty_subject_eligibility`, normalized eligible-only subject sets | Explicit eligibility on faculty models and operator/validation gates. A frame match is not proof of complete, current institutional qualifications. |
| `backend/data/subject_domains.csv` | `Functions.py`: `df_subject_domains`, subject-domain dictionaries and model construction | Subject metadata and domain relationships. No year/term ownership approval is present. |
| `backend/data/faculty_identities.json` | `services/identity_service.py`: cached `load_faculty_identities`, `resolve_faculty_identity`, `build_legacy_faculty_codes` | Stable UUID/code mapping for runtime models, authentication binding and metadata. Cached registry loading has no loader epoch bound to a run. Names must not be used to invent missing authoritative identities. |
| Section and student models | `Functions.py`: generated section groupings and synthetic student IDs | Section calendars and offerings; these are prototype construction rules, not verified institutional enrollment. `identity_service.py` uses `OFFERING_SCOPE="ccs:first-semester-prototype"`; catalog scope `msu-iit:ccs` does not prove complete CCS coverage. IT remains the available prototype/evaluation scope. |
| Room and timeslot models | `Functions.py` hardcoded room construction and lecture/laboratory patterns; `models/Room.py` calendars | Initial scheduling, conflict validation and reconstruction. No approved term-specific room inventory/closure source is bound to these constructors. Faculty/room reset semantics and authoritative closure persistence remain the F4B boundary. |
| `backend/data/preassigned_assignments.json` | `Functions.py`: `apply_preassigned_assignments` | Instructor/room declarations on subjects. `PreassignedAssignment` is not fixed day/start/end institutional scheduling. |
| Protected `faculty_preferences.json` | `FitnessFunction.py` loader, then `FrozenInputs.capture_inputs` freezes dashboard preferences; effective preferences merge cached legacy inputs | Scoring and reporting. U5C raw-hashes the protected file only via existing fingerprint/preservation readers; it does not edit or export its contents. New diagnostics do not normalize preferences. |
| Protected `ga_settings.json` | `FitnessFunction.py` settings loader, then frozen settings | Workload/scoring configuration, with existing defaults/fallbacks. Source bytes, parsed effective settings and actual run parameters are distinct identities. No setting is changed here. |
| All `backend/data/*.csv` and `*.json` | `services/ga_progress_service.input_fingerprint`: sorted paths, relative path bytes, then complete raw bytes | Monitor, frozen inputs, checkpoint input validation and U5A/B technical identity. It hashes the whole file set, including files not consumed by the active loader. It omits constructed model state, loader epoch, hardcoded calendars and run parameters as separate semantic components. |
| Effective run parameters | `GenerationMonitor`, `register_baseline`; U5B `ga_run_provenance.configuration` and `configuration_fingerprint` | Configuration fingerprints also distinguish baseline seed/configuration. U5C does not collapse these existing formats into a single new digest or compare different configurations. |
| Scoring and engine source | `ga_checkpoint_service.engine_fingerprint`, scoring-policy bridge/manifest, runtime Python/pandas/numpy versions | Strict V1 engine and checkpoint compatibility. Source and policy hashes do not certify academic source authority. No fingerprinted source is edited. |
| Frozen and resumed input graphs | `FrozenInputs.capture_inputs` / `with_frozen_inputs`; checkpoint graph reconstruction | Fresh capture deep-copies system faculty and reads current preference/settings context, but subjects/rooms/legacy frames were cached earlier. Resume uses its checkpoint-bound graph and policy, not new U5C cache observations. |
| Metadata APIs | `services/metadata_service.py` reads the same runtime faculty/subject model collections | Useful read-only projections, not an independent authoritative academic source. An API listing does not certify roster completeness or term binding. |
| Academic database foundation | `academic_models.py`, existing migrations, `academic_import_service.plan_import`, `academic_metadata_adapter.compare_projections` | Scoped years/terms/courses/sections/offerings and lifecycle constraints exist. Import planning is an identity dry run; it is not a production GA loader. No database was queried or migrated for U5C. |
| D8/D9 confirmation and D10 V2 | Independent trust/confirmation authority services and `ga_v2_service.institutional_deployment` | Production providers remain unconfigured. V2 confirmed-constraint authority is not a substitute for U5C dataset stewardship or the V1 loader contract. No V2 aggregation or authority integration is added. |

## Authority and qualification contract

`services/ga_source_qualification.py` defines frozen, strict declarations (unknown fields rejected) and revalidates constructed/copied objects before comparison:

| Fact | Contract / required evidence | Current qualification |
|---|---|---|
| Academic year/term/department | Existing `AcademicContext` canonical UUID identities and explicit labels; exact equality, including dataset ID/revision/input fingerprint | No genuine server source configured. Never inferred from filenames, timestamps or prototype namespace labels. |
| Dataset ownership | Explicit owner reference to a separately authenticated steward | Required; absent in deployment. A fictional fixture reference is not institutional ownership. |
| Source authority and approval | Separate authority reference, approval claim and approval reference, with independently verified issuer, scope, current lifecycle/revocation | Declaration fields alone never prove approval. No authority adapter or approval endpoint is installed. Administrator/Chair account roles do not grant dataset approval. |
| Effective period | Explicit timezone-aware start/end, evaluated as `[start,end)`; reversed, expired or future periods cannot technically match | Declaration validation/comparison implemented; authoritative institutional period absent. |
| Integrity | SHA-256 of complete canonical expected semantic projection; exact engine/configuration hashes and policy version | Implemented as a precheck for explicitly supplied projections, not signatures or run receipts. |
| Loaded input projection | Exact component keys: identities, faculty, eligibility, specialization, preferences, offerings, sections, rooms, availability, time patterns, workload, preassignments, settings, configuration | Complete fictional projection comparison implemented. No automatic extraction of a complete actual optimizer graph is claimed. |
| Run consumption | Atomic loader receipt binding source bytes, transformation/loader identity, complete constructed/frozen/resumed graph, run identity and configuration at the actual consumption boundary | **Unavailable.** New observation is not attached to a run, checkpoint or U5B capture. Cannot certify CURRENT. |

The origin classifications are `INSTITUTIONAL_DECLARATION`, `FICTIONAL_FIXTURE` and `UNVERIFIED_HISTORY`. Even `CLAIMED_APPROVED` institutional metadata with every hash matching remains ineligible: independently trusted authority and run consumption are still absent. `technical_projection=MATCH` means only equality of the explicitly supplied projections. It is intentionally independent of institutional approval.

## Implemented read-only observation and UI

`GET /api/ga/source-qualification` inherits the existing administrator dependency. Unauthenticated, faculty and Chair callers are denied; query parameters cannot override context; POST is unsupported. It exposes only fixed semantic source labels, technical digests/counts, bounded statuses and blockers. It returns no filesystem paths, faculty records, source rows, cookies or credentials.

The five safe-to-compare caches are `df_subjects`, `df_section_schedules`, `df_faculty_qualifications`, `df_faculty_subject_eligibility` and `df_subject_domains`. Current CSV bytes are parsed with the existing pandas defaults, compared with cached frame semantics, then reread for within-observation drift. Row order, scalar types and exact finite float representation are retained. Duplicate headings, ragged records, unsupported types/shapes, unreadable/oversized files and absent caches fail closed. Source table limits are 8 MiB, 20,000 records and 100 columns. The whole existing file fingerprint is checked before/after observation.

The fresh observation recorded **five MATCH results**, a stable file-set fingerprint and an unconfigured academic provider. It performed no GA generation or database connection. This checks the cached tables, not the transformed dictionaries/models/aliases or a live running worker. Changes between fingerprint samples and ABA changes are not ruled out; equality is not an atomic loader transaction. Transformed preferences/loads are deliberately excluded from this partial table comparison. Configuration, protected JSON semantics, availability calendars and all implicit/default state remain unmapped to authoritative source records.

The new teal/gold-compatible panel inside Current Evaluation displays BLOCKED, missing academic identity, institutional authority and run binding, partial table statuses, and independent loading/error/retry handling. There are no approval, term-selection, upload, activation or persistence controls. Invalid eligibility claims in a response are rejected by the frontend validator.

**Compatibility boundary:** U5A/U5B capture and classification remain unchanged. The new endpoint is observational and does not gate a new configured provider, backfill provenance, rewrite history or promote Saved Best. The default U5B provider still returns None, so deployment cannot qualify an unverified run as CURRENT. U5B tests with explicitly trusted fictional providers still exercise the conditional earlier contract; they do not establish that a genuine U5C source has been qualified. Configuring a real provider before run-bound source verification is enforced would bypass an unresolved deployment requirement and is not authorized by U5C. That integration is a remaining blocker, not implemented functionality.

## Validation and evidence

Fresh results and attempt reconciliation are recorded in the [manifest](testing/dashboard-u5c/manifest.json). Backend tests use fictional projections, temporary CSV/history/provenance stores and ASGI dependency overrides. Focused tests forbid `Engine.connect`. Existing U5A/B and V1/V2 engine regressions use their established fictional fixtures and temporary storage. No database suite is selected.

| Fresh check | Actual result |
|---|---|
| U5C backend/ASGI tests | 45 passed, zero failed |
| U5A/U5B and current V1/V2 backend regressions | 88 passed, zero failed |
| U5C frontend contracts | 13 passed, zero failed |
| Existing frontend contracts including U5A/U5B | 212 passed, zero failed |
| TypeScript, production Vite build, focused ESLint | Passed |
| Read-only actual cache inspection | Five MATCH observations; stable file-set sample; qualification BLOCKED |
| Git fsck | Passed; existing dangling objects retained |
| New browser acceptance | **0 of 8 scenarios executed; two initialization failures** |
| Existing U5A/U5B browser reruns | NOT RUN after reproduced renderer blocker; earlier browser results remain historical |

The 133 backend and 225 frontend contract passes are freshly executed. They are not browser or institutional acceptance. Existing TestClient/httpx and anyio deprecation warnings, Vite mixed-import and large-chunk warnings remain; no dependency was installed or changed.

Both Edge attempts timed out in `Runtime.enable` before scenario execution. Their unsuccessful command/results remain archived. A separate owned blank-page probe tested Edge with extensions disabled and installed Chrome with normal settings: `Browser.getVersion` succeeded, while `Page.enable`, `Runtime.evaluate` and `Runtime.enable` each timed out without any application/API loaded. This establishes a reproducible renderer-command automation blocker independent of application startup; the underlying environment cause is unconfirmed. The extension-disable flag did not eliminate all observed background targets, so it does not rule out managed/injected extension effects. No timeout was increased or test removed. Probe exit zero means diagnostics completed, not browser tests passed. The initial unarchived exploratory blank-page probe is not counted as formal test evidence.

The browser suite is prepared for actual headless Edge/React with intercepted fictional HTTP responses, not live FastAPI/database acceptance. **No application browser scenario ran and no screenshot was captured.** One defined scenario supplies U5B's trusted-provider zero-fitness fixture independently of the blocked source diagnostic; this intended regression check is unexecuted. Backend and frontend contracts freshly verify exact zero preservation. No visual/layout, loading/retry DOM, device or browser authorization acceptance is claimed for U5C.

Reproduce from a dedicated PowerShell terminal at the repository root:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5c/run_checks.py backend
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5c/run_checks.py backend-regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5c/run_checks.py focused
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5c/run_checks.py regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5c/run_checks.py source-inspection
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5c/run_checks.py browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5c/run_checks.py u5b-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5c/run_checks.py u5a-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5c/run_checks.py build
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5c/run_checks.py bundle
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5c/run_checks.py lint
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5c/audit_evidence.py
```

Each check writes a new uniquely named command record; existing evidence is never overwritten. Re-running checks after the sealed manifest requires a new explicitly reviewed audit/manifest supplement rather than treating new evidence as part of the original signoff. Do not run browser suites concurrently with frontend edits or each other.

## Changed/new implementation inventory

Existing files modified only:

- `backend/routers/ga_evaluation.py` — additive protected read-only route.
- `frontend/src/components/ga/CurrentEvaluation.tsx` — embeds independent qualification observation.

New implementation/tests:

- `backend/services/ga_source_qualification.py`
- `backend/tests/test_ga_source_qualification.py`
- `frontend/src/services/sourceQualification.ts`
- `frontend/src/components/ga/SourceQualification.tsx`
- `frontend/tests/sourceQualification.fixtures.mjs`
- `frontend/tests/sourceQualification.test.mjs`
- `frontend/tests/sourceQualification.browser.test.mjs`

New report/evidence: this report and `docs/testing/dashboard-u5c/` (preservation baseline, check runner, read-only source inspector, blank-page browser diagnostic, audit utility, uniquely dated command/browser records and manifest). There are no screenshots. The manifest lists every exact path and raw artifact hash; it excludes its own hash.

## Production activation blockers and next milestone

1. Obtain an authenticated institutional source with steward/owner, approved year/term/scope, dataset identity/revision, effective period and independently checkable approval/revocation. IT prototype data does not establish complete CCS authority.
2. Define a complete, approved semester roster/eligibility/offerings/sections/enrollment/room inventory and availability source. Resolve F1/F1.5/F3/F4B policy/data gaps; do not infer missing records or turn preassignments into fixed meetings.
3. Design a loader receipt at actual V1 construction/freeze/consumption boundaries covering all transformed/default/implicit inputs and aliases, plus configuration, policy, loader/engine version and cache lifecycle. Bind it coherently to run-start provenance. Double-reading file bytes is insufficient.
4. Review engine/checkpoint compatibility before touching fingerprinted loader/service code. Preserve current-release V1 and versioned V2 contracts and all six retained historical artifacts. Define resume and old-result handling explicitly; do not reconstruct missing proof from current files.
5. Enforce source qualification at capture/evaluation using that reviewed run-bound receipt before configuring a genuine provider. Version any required provenance extension; leave historical records immutable. Separately approve any Saved Best persistence contract.

Recommended next milestone: a fictional loader-receipt contract/compatibility qualification, followed by institutional source adapter review when authoritative evidence is available. No production activation, authority redesign, migration, institutional provider, GA input change or further milestone is automatically started.

## Preservation and limits

The raw entry baseline contains **3,168 paths**, including the Git index, all 23 academic data files, previous untracked research/U4/Live work and retained checkpoint/result trees. Only the two listed existing source files may differ. Protected preferences/settings are raw-hashed, not edited, restored, staged or normalized. Existing GA/scoring/RNG/fingerprint code, original migrations, authentication/authority services, historical results and prior evidence remain byte-identical; final replay is recorded in the manifest.

No PostgreSQL or existing SQLite connection, credential change, migration, dependency installation, checkpoint write, institutional publication, provider activation, staging, commit or push is performed. D15 records are preservation-checked; the retained D15 database is not inspected or altered. Disposable historical acceptance does not authorize institutional activation. Technical hashes and fictional tests do not establish production readiness.

## U5C-R1: browser verification and checkpoint review

R1 continued at the same `main` commit, without application changes. Its entry baseline covers 3,197 existing paths. The only R1 updates to pre-existing files are this report and the standalone U5C check runner. The original report and original runner are retained as `entry-report.md` and `entry-run_checks.py`, with raw hashes exactly matching the sealed original U5C manifest. Earlier unsuccessful evidence, the original manifest and its audit utility remain unchanged. Use `dashboard-u5c-r1/audit_r1.py` for the current review; the earlier audit describes the earlier sealed inventory and test selection.

### Browser investigation

| Identical blank-page operation | Restricted execution, Edge | Verified execution context, Edge | Verified execution context, Chrome |
|---|---|---|---|
| `Browser.getVersion` | 13 ms | 30 ms | 17 ms |
| `Page.enable` | 5,008 ms timeout | 22 ms | 29 ms |
| `Runtime.evaluate` (`1+1`) | 5,007 ms timeout | 24 ms | 10 ms |
| `Runtime.enable` | 5,005 ms timeout | 3 ms | 5 ms |

The working probe uses the same installed executable, unchanged arguments, owned temporary profile, blank page and existing 5-second limits. No application, API or credentials are involved. The repeated failure is therefore an execution-context/renderer automation limitation, not a reproduced U5C application defect. Running the probe outside the restrictive execution sandbox restores renderer responses. The precise denied OS capability is not observed; installation corruption, a particular extension and historical resource pressure are not claimed as proven root causes. Installed Edge and Chrome both work in the verified context. No browser, dependency or compiler was installed, no global browser configuration was changed, and no timeout was increased.

The first successful R1 probe was written as a new timestamped record under the original U5C evidence directory. It is explicitly included in the R1 checkpoint inventory; it does not overwrite an old record. All subsequent R1 evidence is in `docs/testing/dashboard-u5c-r1/`.

### Fresh R1 results

| Check | Result and scope |
|---|---|
| U5C browser suite in working tree | **8/8 passed**, actual headless Edge/React, fictional intercepted HTTP |
| U5B browser regressions | **17/17 passed**, same isolated scope |
| U5A browser regressions | **14/14 passed**, same isolated scope |
| U5C browser suite in independent source snapshot | **8/8 passed again**, not eight additional unique requirements |
| Independent U5C/U5A/U5B backend tests | **99 passed**, fictional fixtures, ASGI dependency overrides and temporary stores |
| Independent U5C frontend contracts | **13 passed** |
| Independent committed-baseline frontend regressions | **166 passed** |
| Independent TypeScript / Vite production bundle / focused ESLint | **Passed** |
| Browser request and runtime checks | Only GET API requests; no unexpected runtime errors |
| Screenshots | **16 genuine PNGs**, all contents visually reviewed; CRC/metadata/privacy inspected; no editing |

All final selected tests have zero failures, errors, skips or cancellations. There are **39 unique browser scenarios**, plus the repeated eight U5C snapshot cases. Parent Node tests are recorded separately (9, 18 and 15 for the three working-tree suites, and 9 for the snapshot browser suite). Browser results are synthetic-HTTP UI evidence, **not** live browser-to-FastAPI/database or institutional acceptance. The backend results are actual Python/ASGI tests, not browser authorization proof. U5A/B browser fixtures do not implement the new diagnostic endpoint and deliberately show its harmless unavailable/404 panel while exercising the earlier evaluation contract; U5C's own suite tests matching, stale, loading, error/retry and invalid-source cases.

Earlier U5C results (133 backend and 225 frontend passes) remain recorded history, not additional fresh R1 executions. The new 166-test regression selection omits 46 tests belonging to unfinished U4/Live work; those tests are not disabled or deleted, and their files remain untouched. Full historical D10/V2 engine suites are not freshly rerun by R1; their original bytes and previous evidence remain preservation-checked. Source-inspection and production authority activation are not repeated or enabled.

The retained R1 failed attempts are explicit:

- A new snapshot-tool syntax error stopped before snapshot creation; corrected in standalone tooling.
- An initial in-memory historical-runner candidate used LF instead of its original CRLF and was rejected; only the subsequently exact sealed-hash match was archived.
- An export assertion found only inherited Git CRLF expansion; the failed temporary snapshot was retained and later exports explicitly used canonical Git bytes.
- Missing private CSVs caused three collection errors and zero executed tests. A guarded fictional import bootstrap was added for temporary snapshots only.
- The first fictional preassignment bootstrap omitted the required empty `external_instructors` object, causing three further collection errors; its schema was completed from the unchanged loader.
- A canonical export then produced **98 passed, 1 failed**: `test_actual_engine_fingerprint_scope_is_unchanged`, with `ValueError: Installed source is not the verified legacy-compatible release.` Its evidence remains intact.
- A release-layout preparation syntax error and a snapshot started before that recipe existed stopped before tests. These preparation failures are retained in `tooling-failures.json`.

The initial snapshot wrapper printed `passed:false` in its JSON but returned process exit zero after a failed test batch. R1 corrected that wrapper to return nonzero for unsuccessful final checks. Per-case command exit codes and outcomes, rather than those earlier wrapper exits, determine the failure attribution above. No application test failure was erased or relabeled as a pass.

### Independent checkpoint-source rehearsal

`checkpoint_snapshot.py` exports committed U5B into a newly owned OS-temp directory and overlays the exact original 31 U5C paths. It does not use the real Git index. It checks canonical HEAD content and excludes unfinished U4/Live services, tests and page edits. No repository academic data is extracted: seven empty fictional CSV headers, an empty fictional identity registry, empty preferences/settings and empty preassignments allow module imports. Existing tests then install their own fictional model fixtures. These empty import tables are not claimed to be a schedulable institutional dataset.

Installed `.venv` and `frontend/node_modules` dependencies are reused through explicit temporary junctions; no dependency installation occurs. This establishes source isolation, not a clean dependency-installation or OS containment test. Temporary repositories and unsuccessful attempts are retained outside the working repository. Application outputs and fixture stores stay in temporary locations.

**Pre-existing release-byte prerequisite:** the supported source tree contains mixed LF/CRLF bytes pinned by the original strict legacy bridge. Git's canonical export does not preserve that byte layout, even though the source text is identical. R1 does not weaken the bridge, edit its manifest, spoof a fingerprint or reinterpret a checkpoint. A metadata-only recipe (`release-byte-layout.json`) records newline positions plus canonical and raw SHA-256 identities for 55 unchanged backend source files. Every raw hash is verified against the R1 entry baseline and every canonical source against committed U5B. The helper reconstructs those exact bytes **only in a guarded temporary snapshot** and verifies the hashes before the unchanged engine performs its own strict checks. No code bodies, private faculty names or approval records are stored in the recipe.

The final 99-test rehearsal includes the originally failing fingerprint test, which now passes without changing any assertion or production function. All nine proposed U5C application/test source hashes and the revised U5C runner match the tested overlay. This proves independence from unrelated unfinished work under the documented runtime baseline. **A plain canonical checkout without the release-byte fixture is still not claimed legacy-compatible.** General production packaging and cross-platform source-byte compatibility remain outside U5C-R1 and require separate review.

Reproduce the source rehearsal in a process capable of starting the verified browser renderer:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5c-r1/checkpoint_snapshot.py
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5c-r1/audit_r1.py
```

The first command creates new evidence and retained temporary copies. After sealed signoff, additional executions require a separately reviewed evidence supplement. The audit is read-only. No production provider or database credential should be configured in this terminal; child environments allowlist ordinary OS variables and a fictional intercepted API origin.

### Exact selective checkpoint plan

The original 31 paths remain in scope. R1 adds only its review tooling, metadata-only release fixture, exact historical report/runner archives, diagnostic/test records and fictional screenshots. The [staging plan](testing/dashboard-u5c-r1/staging-plan.json) contains **every literal checkpoint path** and the excluded tracked paths. The [R1 manifest](testing/dashboard-u5c-r1/manifest.json) records their raw SHA-256 hashes, proposed Git blob IDs, preservation results and test attribution.

No mixed application hunks require partial staging. The two tracked changes are still exactly the additive route and the two-line component integration reviewed for U5C. All eleven pre-existing tracked modifications, including both protected JSON files, and all unrelated untracked research/U4/Live work are excluded.

After separate authorization and a fresh upstream comparison, stage only the literal plan entries with per-command `git -c core.autocrlf=false add -- <path>`. This preserves evidence raw bytes; default normalization can invalidate their raw hashes. No Git configuration is changed globally. Verify exact staged names/counts and index blob contents against the plan/manifest before committing. Neither staging nor an alternate Git index was used in this review.

Recommended single atomic checkpoint message: `feat(ga): add read-only academic source qualification`.

**Readiness: READY for a selective U5C checkpoint with the documented fictional-data/release-byte test prerequisites.** This is not a claim of ordinary clean-checkout production deployment readiness. A fresh remote comparison and separately authorized staging/blob verification remain required. Production institutional context, genuine source approval, run-consumption binding, Saved Best persistence eligibility and any U5D work remain BLOCKED or outside scope.

R1 preservation checks cover all 23 academic files, protected local preferences/settings, all GA/operator/scoring/RNG/fingerprint sources, migrations, checkpoints, Saved Best, historical schedules, previous evidence and the actual Git index. Of 3,197 entry paths, 3,195 remain byte-identical; only this report and the standalone U5C runner changed, with exact original copies archived. No database operation, staging, commit, push, destructive cleanup or production source correction occurred.
