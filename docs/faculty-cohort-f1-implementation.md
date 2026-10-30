# F1: faculty cohort correction — fictional adapter verified, production source blocked

2026-10-29, Asia/Manila. Source `main` at `1423812e13a5791a550c893ef6b17bfef4b4ebfb` with existing uncommitted performance/audit work and two protected local data modifications. **F1's fictional adapter is ready for review. Production cohort correction is BLOCKED by the unavailable trustworthy semester-specific roster/profile source.** No production source was replaced or activated.

## Objective and authorization

Implement roster-first cohort membership independently of optional preference submissions while preserving explicit eligibility, Option B workload accounting, existing scoring/operators, calendars, checkpoint checks and Chair/publication authority. The attached F1 request states that the roster-first principle has adviser/department approval. This is **USER-REPORTED approval**, not documentary evidence reviewed by this milestone. It does not establish that any local dataset is an approved term roster, resolve other pending workload/fairness/specialization policies, or prove formal thesis alignment.

The request explicitly instructs that if no trustworthy semester roster source is available, implement only independently testable fictional adapter behavior and report the blocker before changing the production cohort source. That branch applies. The preceding [functional audit](thesis-functional-correctness-audit.md), [42-row matrix](thesis-objective-traceability.md), [policy qualification](faculty-policy-qualification.md) and [decision matrix](faculty-policy-decision-matrix.md) remain unchanged historical findings. No policy document was rewritten to manufacture approval.

## Source inspection and root cause

Read the Faculty model, legacy roster dictionaries/loop, V1/V2 template construction and scoring freeze, preference model/schema/validation/storage/ownership, metadata/identity services, academic/authentication models and repository, and relevant engine/workflow/tests. No AGENTS.md was found. No live database inspection or institutional row parsing was performed.

| Existing source | Finding |
|---|---|
| `backend/genetic_algorithm/utils/Functions.py:219,318,395` | Builds code/subject/day/time/priority dictionaries from legacy preference rows; constructs normal Faculty objects only for `dct_fac_subj.keys()`. Absence of a key can omit a registered, eligible identity. This list is the faculty pool, not the population of candidate chromosomes. |
| `backend/services/ga_service.py` | V1 imports this runtime pool and deep-copies templates. A new account does not reconstruct this list. |
| `backend/services/metadata_service.py` | Faculty listing/normal lookup project the same runtime pool. This is not an independent complete roster. |
| `backend/services/identity_service.py`, `backend/identity_models.py`, `backend/routers/auth.py` | Static stable identity/code resolution and database account bindings exist. They establish identity/login, not participation in a particular semester. |
| `backend/academic_models.py:112`, `backend/repositories/academic_repository.py` | Faculty legacy-code mappings have no term participation contract. Term/course/section/offering foundation and read-only projections do not supply a complete approved faculty-term roster, profile/eligibility/load/availability snapshot. |
| `backend/services/ga_v2_service.py:25–49` | V2 accepts server-owned Deployment templates. Its institutional provider returns None; genuine deployment remains blocked. Test fixtures are not a roster provider. |
| `backend/routers/preferences.py`, `backend/services/preference_authorization.py` | Preferences depend on normal runtime faculty lookup and global storage, not an authoritative semester roster. Fixing the production source will also need coherent metadata/preference lookup and explicit applicability/rollover rules. |

No configured, trustworthy semester-specific roster source was found in the inspected repository. This is not a claim that the department lacks one outside the repository. Existing CSV names, all login accounts, the static identity registry, preference rows, qualification rows and identity projections must not be substituted as that source without the missing participation/profile contract. The sanitized [source review](testing/faculty-cohort-f1/source-inspection.json) records this boundary.

## Exact implementation

Created `backend/tests/f1/cohort_adapter.py`, a **test-only module with no production imports/references**. Its input contract is deliberately fictional, not a proposed institutional verification API:

- `Term` binds exact scope, academic year and term. `FictionalRoster` requires revision and the marker `FICTIONAL_TEST_ONLY`. That marker is a test boundary, not cryptographic authority or a production capability.
- Explicit roster entries carry canonical UUID, stable integer legacy code, term and participation/exclusion reason. Requested-term membership determines the result in explicit roster order. Other-term entries and explicit exclusions are diagnosed. No sorting by names, inferred IDs or authentication-account enumeration occurs.
- Duplicate identities, cross-record UUID/code conflicts, duplicate profiles/submissions, mismatched bindings, unknown term, absent revision, unknown submission identity, missing required profiles and dirty/preference-bearing run-state profiles fail the entire operation with neutral discrepancy codes. No partially returned cohort or store mutation occurs.
- Profiles supply explicit fictional Faculty objects and separately declared scoring priority. They must be pristine and neutral; the adapter does not silently import old preference hints or invent workload/priority metadata. Profiles are deep-copied; specialization, eligibility, existing calendars and Option B inputs are retained. Missing eligibility is explicit `MISSING_DENY_ALL`, never universal permission and never a reason to silently omit the participant. Known-empty eligibility stays distinct from unknown permission metadata.
- Submitted preferences are checked against the existing strict `FacultyPreferenceUpdate` schema and copied **only with explicitly supplied fields**, mapped by exact term/UUID/code. Missing submissions produce `MISSING_NEUTRAL` diagnostics and **no fabricated preference JSON row**. Existing priority-only legacy DataFrame rows feed the unchanged original scorer, whose no-submission semantics are neutral preference fields. Workload/preparation/daily-load rules still apply.
- Existing day/time/subject preference payloads reach the original scorer unchanged in the synthetic scoring context. The adapter does not transform soft preferences into closures, select calendar times, or change constructor/operator scoring. Pristine Faculty construction hints remain neutral; this is not a migration of legacy constructor preference hints.
- The result includes a deterministic diagnostic/digest binding to the fictional roster term/revision/order, profiles/calendars, eligibility, priorities and submissions. Set-node serialization is canonicalized. This digest is **not installed into production checkpoints**. Existing production source/input/template fingerprints and validation remain intact; a future provider must bind cohort provenance explicitly before cutover.

This adapter deliberately does not claim full preference business validation: the production write validator also checks offered subjects, eligibility and complete supported component/time patterns against trusted metadata. Those checks and existing authorization must be retained upstream when a real provider is designed. A strict schema, fictional marker or submitted priority field is not proof of write permission. No API, endpoint, roster loader, database table, settings change, authority provider or user-interface feature was added.

## Before/after fictional coverage

The new test executes the **original legacy roster AST loop** with fictional identity/load/eligibility dictionaries and one legacy preference-derived key. It then compares the detached roster-first adapter with the same declared three active members. Two are explicitly eligible for the two offerings; the third has no eligible offerings. An additional other-term member and an explicitly excluded fictional term-leave member are outside the requested cohort. No institutional records were used.

| Metric | Original legacy loop | Fictional roster-first adapter |
|---|---:|---:|
| Active term roster members in control | 3 | 3 |
| Members eligible for at least one offered subject | 2 | 2 |
| Runtime members included | 1 | 3 |
| Eligible members included | 1 | 2 |
| Active members omitted for missing legacy preference key | 2 | 0 |
| Runtime members missing submitted preferences | 0 | 2 |
| Other-term / explicit-leave exclusions | Not a term policy in legacy loop | 2, with distinct reasons |
| Runtime members with zero assignments | 0 | 1 |
| Unassigned offerings in successful controls | 0 | 0 |
| Faculty / room / section conflicts | 0 / 0 / 0 | 0 / 0 / 0 |

The after schedule is constructed with the actual original V2 constructor and admitted through original validation. The before schedule uses original assignment helpers and also passes original admission. [Coverage evidence](testing/faculty-cohort-f1/20261029T091141342982+0800-cohort/coverage-before-after.json) records exact counts and exclusion reasons. Differences are membership behavior, not evidence of improved fitness or unchanged assignment distribution: changing cohort changes the search/scoring universe intentionally. The unqualified included member has zero teaching assignments. Inclusion does not guarantee an assignment under scarcity, qualifications, hard limits or calendar restrictions.

With every member explicitly ineligible, the adapter still includes the cohort; original bounded construction returns `SEARCH_EXHAUSTED`. This is a truthful existing error classification, not a new mathematical infeasibility detector or permission relaxation.

## Validation and evidence

All fresh selections ran from the repository root through the new evidence runner; exact Python commands, backend/frontend cwd, environment versions, Asia/Manila timestamps, elapsed times, exit codes and sanitized stdout/stderr are archived. Latest successful results:

| Selection | Fresh result | Scope |
|---|---|---|
| Cohort and existing audit/D10 engine | **93 passed**, 0 failed/skipped; 1 warning | 30 new F1 cases, 33 previous audit cases, 30 D10 engine cases. Fictional in-memory inputs; owned temporary checkpoint files. |
| Adjustment, Chair trust, application trust and complete workflow | **48 passed**, 0 failed/skipped; 3 warnings | Real in-process FastAPI/password/session/Origin/CSRF/ownership and owned SQLite; explicit fictional authority. Includes fresh-process request persistence. |
| Frontend regression contracts | **99 passed**, 0 failed/skipped/cancelled | Node contracts for preferences, own schedule, requests, Chair, application, constrained GA, reports and authentication. No browser rendering/live browser evidence. |

**Final total: 141 backend cases and 99 frontend contracts**, reported separately. Do not add repeated intermediate passes. Warnings: AnyIO assertion rewrite after required schema bootstrap; existing Starlette/httpx TestClient deprecation; existing BlockingPortal alias deprecation. No dependencies were installed or warnings hidden.

The new F1 cases verify submitted and absent preferences, other-term/explicit exclusions, duplicate/conflicting IDs, absent profile and invalid binding failures, no account-only enrollment, missing eligibility deny-all, zero-eligible members and bounded failure, unchanged Option B fields/specialization/calendars, detached graph ownership, digest changes, exact old-loop coverage, separate original faculty/room/section conflict rejection, same-seed reproducibility and actual current V2 checkpoint creation/read/continuation. Existing audit/D10 tests also verify hard workload ceilings, eligibility, fixed commitments, descendant admission, strict checkpoint corruption/input mismatch rejection and best-ever isolation.

The adapter cohort's actual uninterrupted and paused/resumed V2 executions have identical results and final RNG state. Their best-ever histories are `[250,250,250]`; this is a flat, non-increasing history, **not convergence or a fairness improvement claim**. Original codec/store validation runs, and the best-ever graph is independent of population mutation. The [continuation record](testing/faculty-cohort-f1/20261029T091141342982+0800-cohort/adapter-engine-continuation.json) stores only numerical/boolean fictional results, not a checkpoint or trust token. Existing D10 tests additionally cover fresh-process continuation of their established fixture. V1 historical compatibility evidence is preserved, not freshly rerun by F1; none of the six retained historical checkpoints was loaded or migrated.

### Retained intermediate results

1. `20261029T090759402192+0800-cohort`: 90 passed before adding three explicit resource-conflict controls.
2. `20261029T091026603914+0800-cohort`: **91 passed, 2 failed**. The new Room/Section controls assumed room-list position was the selected room. `get_available_rooms` shuffles candidates (`Functions.py:853`), so one control could create no room conflict and another could create a room conflict before its intended section conflict. This was a test-fixture defect, not diagnosed by suppressing the failure or altering scheduling code.
3. The control now reads the actual first assignment room from its fictional payload, using that same room only for the room test and a distinct room for faculty/section tests. Final `20261029T091141342982+0800-cohort`: **93 passed**; all three individual resource checks reject through original reconstruction with the expected resource error. [Diagnosis](testing/faculty-cohort-f1/conflict-fixture-diagnosis.json) and all unsuccessful evidence remain.

Fresh browser scenarios, frontend build/lint and live PostgreSQL are **NOT RUN**: no production/UI change or new deployed source exists to test, and database access is outside this correction's safe boundary. D15 successful acceptance evidence and retained PostgreSQL data were not touched or queried. Passing these tests does not certify institutional input completeness, genuine approval or deployment readiness.

## Exact changes and preservation

Existing files modified: **none**. New implementation/test/tooling paths:

- `backend/tests/f1/cohort_adapter.py` — fictional-only detached roster adapter.
- `backend/tests/f1/test_cohort.py` — 30 regression/control cases.
- `docs/testing/faculty-cohort-f1/run_checks.py` — isolated bootstrap/owned-child/sanitized evidence runner.
- `docs/testing/faculty-cohort-f1/audit_evidence.py` — baseline, privacy, history, hashes, inventory and Git verification.
- `docs/faculty-cohort-f1-implementation.md` — this report.

New JSON paths under `docs/testing/faculty-cohort-f1/`: preservation baseline, source inspection, conflict-fixture diagnosis, all timestamped command/coverage/continuation/conflict records and the manifest. **Final inventory: 23 new files (four Python, one Markdown, eighteen JSON); 22 artifacts hashed, excluding the manifest itself.** The [manifest](testing/faculty-cohort-f1/manifest.json) provides the complete exact new-file inventory and raw artifact hashes, excluding itself. Privacy scan: zero findings; all 381 prior artifact entries independently reverified; Git and new-file whitespace checks passed.

Preservation audit compares **1,767 pre-existing paths**, including all23 academic files, previous audit/performance evidence, original GA/operators/scoring/RNG, V1/V2/checkpoint compatibility sources, migrations, six historical checkpoints, saved schedules/history and the Git index. Both existing local data modifications (`faculty_preferences.json`, `ga_settings.json`) remain byte-identical, unstaged and uncommitted. No existing file is rewritten, restored or discarded. Privacy checks scan new source/log/JSON/Markdown for credentials, signed complete/truncated receipts, tokens and sensitive log fields. No institutional names/records or raw authenticated responses are archived. Binary preservation hashes do not establish authority or source correctness.

Git whitespace checks are non-mutating. The existing LF-to-CRLF advisory for protected preferences may appear; raw bytes are verified after Git inspection, and no normalization/staging occurs. No PostgreSQL operation, dependency installation, staging, commit, push or next-milestone implementation was performed.

## Remaining work before F2 / production review

The **fictional adapter subset is ready for review; full production F1 is not complete**. Do not automatically proceed to F2.

1. Supply/design the actual server-owned term/scope roster source: owners, stable UUID/code mappings, effective revision, participation and explicit exclusions, freshness/revocation, integrity and approved ordering. Identity existence or login activity is insufficient. No request/client roster or environment bypass should confer authority.
2. Bind complete term-effective workload, priority, qualification/eligibility and availability profiles. Missing required profile data must remain visible/blocking; never silently substitute zero releases, fabricated credentials or universal eligibility. Define treatment of known-empty eligibility separately from missing information. Preserve current Option B math and the independent fairness/availability issues.
3. Define term applicability/carry-forward for the existing global preference store. Keep absent, empty and disabled states separate. Preserve existing business validation and administrator-only priority control; update metadata/preference lookups coherently with the approved cohort. Do not automatically carry a prior-term submission into a new term.
4. Implement the smallest provider-to-template cutover only when those sources exist. Explicitly version/bind roster revision, order, profiles and submissions to run provenance, seeds and checkpoints. A changed cohort legitimately changes input/template identity and results; never spoof fingerprints, silently reinterpret old artifacts or promise compatibility without evidence. Current V1 and V2 continuation remain the baseline.
5. Run real integration/API/UI journeys with the approved source contract plus fictional qualification fixtures before any institutional activation. Keep Chair approval/publication capabilities separate. Genuine providers remain BLOCKED and must not be installed as part of an F1 test adapter.

Recommended next authorized work is **F1 production source qualification and cutover planning**, followed by narrowly scoped integration once the authoritative roster/profile source is available. This does not authorize workload fairness changes, specialization scoring, availability reset corrections, new tables, production writes or F2 implementation.

## Reproduction

From the repository root using the existing Windows venv and Node installation:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/faculty-cohort-f1/run_checks.py cohort
.\.venv\Scripts\python.exe -B docs/testing/faculty-cohort-f1/run_checks.py workflow
.\.venv\Scripts\python.exe -B docs/testing/faculty-cohort-f1/run_checks.py frontend
.\.venv\Scripts\python.exe -B docs/testing/faculty-cohort-f1/audit_evidence.py
```

Each test command creates a new evidence directory; earlier results are retained. The runner strips database URLs/credentials from inherited environment and schema-bootstraps empty import data before collecting tests. Original institutional text parsing is blocked after bootstrap. Only exact reviewed checkpoint/restart child commands are allowed, with their own fictional bootstrap and owned temporary stores. Fresh-process private test sessions travel through existing private stdin handling and never into evidence. The audit refreshes only this new F1 manifest and stops on any baseline or unapproved-path mismatch, without repairing existing files.
