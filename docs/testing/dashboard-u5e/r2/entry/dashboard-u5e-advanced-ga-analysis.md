# U5E: advanced GA analysis and faculty satisfaction

Implemented and inspected 2026-11-05, Asia/Manila, on `main` at `d6db077793da52b7559351a5d0f8e6d54608cb77`. **Read-only administrator analysis is implemented and tested. Department Chair access, institutional academic-context activation and complete optimizer-consumption verification remain BLOCKED.** No Saved Best eligibility or GA behavior changed.

Open **GA Analysis → Advanced faculty analysis**, or `/admin/analysis?view=advanced`. Recorded penalty details remain the default. Existing V2 result links still open their existing constrained-result panel. U5E analyzes available V1 recorded history; it does not reinterpret transient loaded candidates or V2 stores as V1 history.

## Entry investigation and contract

U5C/U5C-R1 are in HEAD. U5D is still uncommitted: all 24 paths and its 23 manifested artifact hashes were checked at entry and preserved. Its four modified tracked files are separate from U5E. There were 15 pre-existing tracked modifications, protected preferences/settings, and extensive unrelated untracked U4/Live Center and research work. No fetch, staging, commit, push, reset or cleanup of that work occurred.

The [entry baseline](testing/dashboard-u5e/preservation-baseline.json) hashes 3,268 existing paths, including all 23 academic files, prior untracked evidence, retained ignored schedule/checkpoint stores and the Git index. Only `backend/main.py` and the U5E insertion into the already modified `FitnessAnalysis.tsx` differ. Reversing that insertion in memory reproduces the page's exact entry hash. The final [manifest](testing/dashboard-u5e/manifest.json) and [selective staging plan](testing/dashboard-u5e/staging-plan-final.json) enumerate every U5E path; unrelated changes are excluded.

Reviewed the U5A compatibility service, U5B provenance, U5C source qualification, U5D receipt contract, reporting/history services, GA lifecycle and authentication. The accessible `notebooks/main_loopv2.ipynb` contains 12 code cells with the GA loop, a fitness plot and diagnostics; it does **not** define the requested six faculty plots. Those definitions are in `backend/genetic_algorithm/analysis/FacultySelectedChromosomeDashboard.py`. Only notebook source was inspected; notebook outputs and institutional rows were not copied into evidence.

That legacy dashboard uses simple subject membership and sometimes treats absent preferences as satisfied. Its introductory description also omits terms present in the current eight-component reporter. U5E therefore preserves the seven visualization subjects while reusing the current captured-policy reporting predicates. It does not copy legacy percentages or equate descriptive satisfaction with fitness contributions.

## Architecture and access

Three administrator-only GET projections were added under `/api/ga/advanced-analysis`:

| Endpoint | Behavior |
|---|---|
| `/runs?offset=0` | Read recorded indexes without worker discovery, recovery, writes or status transitions; 20 runs per page. |
| `/runs/{run_id}?generation=0&candidate=generation_best&history_offset=0` | Candidate-bound faculty metrics, selected-source summary, provenance, recorded progress and available distinct snapshot choices. |
| `/runs/{run_id}/compare?left_generation=0&right_generation=1` | Same-run, distinct recorded chromosome comparison; candidate selectors also supported. |

Existing session authorization is reused through `require_admin`. Tests assert 401/403 for missing/faculty/unsupported Chair principals and 405 for writes. A Chair is a scoped institutional mandate in the existing system, not a general role that can be added to an administrator dependency. No trustworthy run-to-department binding or configured institutional Chair directory was found for these history files. The interface expressly explains that limitation; it grants no new authority.

The service calls the existing `fitness_reporting_service.generation_report` and validated history readers. It does **not** reconstruct chromosomes, evaluate fitness, read today's preferences as historical preferences, start optimization, write files, discover workers or use a database. Stored candidate IDs, input/engine/configuration identity and captured context bind the result. Raw assignments are matched by existing reporting interval checks. Generic `Faculty <code>` labels avoid introducing a display-name lookup.

U5B compatibility classification remains a separate projection. Observed context, matching source hashes and chart availability do not establish CURRENT eligibility. U5D is optional: absent installation produces `UNAVAILABLE / NOT_INSTALLED`; present receipts remain `UNVERIFIED`, with missing/incomplete/invalid/incompatible states distinguished. Forged VERIFIED/eligible flags are rejected, and receipt start/configuration/input binding is checked. No source or authority provider was activated.

## Graph definitions and sources

All faculty graphs, heatmap cells and details use one selected run/generation/candidate/chromosome and corresponding captured context. Ten faculty are shown per page, with consistent numeric identifier ordering or the selected heatmap ordering. Three chart columns appear on wide screens, two on intermediate screens and one on mobile. Axes, units, legends, tooltips, reference lines and accessible value tables accompany plots. The final layout separates legends from axis labels and keeps zero visible.

| Graph | Exact basis and interpretation |
|---|---|
| Subject Preference Satisfaction | Existing reporter's ranked descriptive credit: `100 × (1 − mean(rank / max(1, preference_count)))`, zero-based rank; an absent subject contributes 1 to that mean. Only applicable enabled captured preferences produce a percentage. This is not a new fitness equation. |
| Day Preference Satisfaction | Reporter `100 × matched / applicable checks`. General preferences check each offering's actual days as a subset. Subject-specific requests check the requested day in the relevant component, using the captured preference-policy flags. |
| Time Preference Satisfaction | Reporter `100 × matched / applicable checks`. General preferences require component intervals within the requested window. Exact subject requests check raw component start membership independently of the day, as the existing reporter specifies. |
| Preparations per Faculty | Count of distinct assigned subject codes in the selected stored schedule. Multiple sections/components of the same subject are not extra preparations. Captured maximum-preparation reference shown when available. |
| Teaching Load Distribution | Existing recorded/reporting offering credit units, not a sum over duplicated meeting rows. Individual captured targets are separate bars. The existing 40-unit hard ceiling is displayed only with supported captured reporting context. No workload policy is changed. |
| Load Balance vs. Faculty Average | Assigned units minus the arithmetic mean for the full captured cohort; null when any required units are unknown. The reference is zero. This is a descriptive diagnostic, not the production workload penalty. |
| Scheduled Teaching Hours per Faculty | Per-day union of stored half-open meeting intervals, divided by 60. Duplicate, overlapping and adjacent spans merge; overlapping rows do not inflate hours. Monday–Saturday are stacked. Invalid days/times fail rather than being coerced. Contact hours differ from credit units. |

The heatmap displays each percentage and its enabled/applicable status, with a text-described scale. Missing/disabled/non-applicable values remain null, never zero. Sorting supports identifier, lowest/highest complete-case satisfaction, and each separate dimension; incomplete cases sort last. Native dialog drill-down displays captured preferences, assigned subjects/sections/components/day/time/room, targets, preparations, contact hours, deviations and unmet-status explanations. It has no editing controls.

Summary per-dimension percentages are arithmetic means over applicable faculty, with contributor IDs and `count / captured cohort` denominators. The optional overall mean includes only faculty with **all three** percentages. It is explicitly complete-case descriptive satisfaction, without importance-weighting or a claim of roster completeness.

## Progress and comparison boundaries

Progress reads at most 50 recorded generations per window. It shows recorded best-ever and average penalty, three applicable satisfaction means, recorded validation counts and cumulative elapsed time. Missing/corrupt observations and mismatched captured policy/context/configuration produce explicit gaps and issue counts. Contributor coverage is available per generation. Changes in coverage are not presented as a constant-cohort causal estimate. Fitness is never converted into satisfaction or a percentage.

Recorded hard-constraint counts cover validated snapshots, **not** every rejected child or search attempt. A zero series does not prove the search never proposed an invalid candidate. No missing historical measurements are manufactured. Fitness values and signed deltas retain the full serialized numeric precision, including zero and small nonzero differences; descriptive percentages may use two-place display formatting. The existing live monitor is linked; U5E adds no polling loop or continuous optimizer.

Comparison requires distinct real available snapshot IDs from the same run and matching engine/input/configuration fingerprints, comparable fitness flags and the complete captured reporting-policy/context digest. Different preferences, settings or captured term fields reject comparison. It displays signed right-minus-left deltas for raw fitness, mean absolute cohort load deviation, validation counts and per-faculty satisfaction/preparations/units/target deviation/hours. Unchanged is explicit; unknown remains incomparable. A lower fitness penalty is not described as an improvement for every faculty member. One distinct chromosome produces an unavailable message. Snapshot choices are bounded to the current progress window plus the selected generation.

Academic context in this view remains unverified observed metadata, or unavailable; no labels are inferred from filenames, dates or present-day datasets. Comparison does not assert institutional academic compatibility. Existing Saved Best files, history and checkpoint eligibility are untouched.

## Fresh validation

| Check | Actual final outcome and scope |
|---|---|
| New backend tests | **20 passed**, fictional recorded DTOs, temporary stores and FastAPI ASGI TestClient; `Engine.connect` forbidden. Real sessions/database authorization were not exercised. |
| Reporting/history/U5A–U5C regressions | **145 passed**, 2 dependency warnings, 280.39 seconds. Existing real-model/history tests use their temporary fictional fixtures. |
| V1/V2 engine regressions | **34 passed**, 87.94 seconds, existing fictional creation/continuation/admission tests; no production inputs or authority activation. |
| New frontend contracts | **17 passed**. |
| Existing frontend regressions | **166 passed**. |
| U5E browser | **16 scenarios passed** in Edge 156.0.4314.50; Node reports 17 passing tests including the parent harness. Final selective snapshot reran all 16 after layout and DTO fixes. |
| U5A/U5B/U5C browser regressions | **14 + 17 + 8 = 39 scenarios passed**; 15 + 18 + 9 Node tests including parent harnesses. |
| TypeScript, production build, focused ESLint | **PASS** in the worktree and selective snapshot. Final TypeScript/lint/frontend contract reruns also pass. |
| Git integrity | `git fsck --no-reflogs` exit 0; retained dangling objects reported, no destructive cleanup. |
| Preservation/privacy/whitespace/hashes | Audited by the new replayable tool and manifest. Screenshots: 52 originals, 29 distinct raw hashes, visually inspected; no credential/private record exposure found. |

Backend totals are **199 unique selected tests** (20 + 145 + 34). Frontend contracts total **183** (17 + 166). Browser coverage totals **55 scenarios**, not including repeated acceptance runs or parent wrappers. Do not add repeat runs to those unique totals.

The browser executes actual React DOM and Recharts through headless Edge, with **CDP-intercepted fictional HTTP responses**. It is not Edge-to-FastAPI/database acceptance. The API fixtures are exported by actual projection code from explicitly fictional stored DTOs. Their fitness/history numbers are schema examples, not measured optimizer results or evidence of convergence. No new institutional dataset, credential, private preference payload or approval record was archived.

The final independently tested source snapshot is [20261105T073957495590+0800-snapshot](testing/dashboard-u5e/20261105T073957495590+0800-snapshot/snapshot-proof.json): HEAD plus exact U5E files and a minimal FitnessAnalysis patch, excluding unfinished U4/Live and U5D source. It passed 20 backend, 17 focused and 166 regression contracts, TypeScript, build, lint and all 16 browser scenarios. It reuses installed dependencies and the committed fictional import bootstrap and verified release-newline recipe in a temporary copy; strict engine fingerprint checks are unchanged. No real index was created or staged. Temporary source snapshots are retained outside the repository.

Final screenshots include [seven charts](testing/dashboard-u5e/20261105T073957495590+0800-snapshot/U5E-B01-charts.png), [summary](testing/dashboard-u5e/20261105T073957495590+0800-snapshot/U5E-B01-summary.png), [faculty details](testing/dashboard-u5e/20261105T073957495590+0800-snapshot/U5E-B03-details.png), [progress](testing/dashboard-u5e/20261105T073957495590+0800-snapshot/U5E-B06-progress.png) and [comparison](testing/dashboard-u5e/20261105T073957495590+0800-snapshot/U5E-B07-comparison.png). Screenshot hashes establish artifact identity, not institutional authority.

## Unsuccessful attempts retained

The first TypeScript build failed on a missing JSX brace; the original record remains. First lint identified three unused conditional expressions; these were rewritten as statements. The first browser run passed nine scenarios then rejected a generation-0 request supplied with a generation-1 legacy fixture; the harness request was corrected, without weakening identity validation. The first backend regression selection named a nonexistent test file and collected no tests; the actual history module was selected afterward.

The combined 179-test backend selection exceeded its fixed 300-second runner bound after partial progress. It is **incomplete**, not a passing run. The same coverage was split into 145 reporting/history/provenance and 34 engine cases, which both passed within the unchanged bound. A read-only owned-process check found no surviving process bearing the expired run's exact temporary base; no service or unrelated process was stopped.

Two temporary snapshot setup attempts failed strict release-byte validation: overlay ordering and inherited archive newline conversion. Both were corrected in the verifier only, preserving expected hashes. A third snapshot ran 19 tests successfully and failed one new assertion that incorrectly demanded UNVERIFIED when optional U5D was absent; the assertion now accepts the designed UNAVAILABLE state. The successful later snapshot demonstrates no U5D source dependency. These failure records, tooling descriptions and earlier screenshots remain in the evidence tree. Initial legend/axis overlap screenshots are also preserved beside the corrected final layout.

The initial evidence audit stopped on inherited capture metadata: five reused U5A/U5B/U5C mobile captures report a fixed 1280x960 viewport while their original PNG dimensions are 390x844. The [metadata addendum](testing/dashboard-u5e/capture-metadata-addendum.json) binds the exact five original record/image hashes and records their actual pixel dimensions. Original records and PNGs are unchanged; U5E captures use dynamic viewport metadata. The initial `staging-plan.json` is retained as a superseded draft; `staging-plan-final.json` is the selective checkpoint plan. No manifest was issued by that failed audit.

The two known backend warnings concern Starlette's httpx TestClient deprecation and AnyIO BlockingPortal alias. No dependency was installed. Builds retain the existing mixed static/dynamic import and large-chunk warnings. These are not silently counted as test failures or removed by unrelated refactoring.

## Exact implementation inventory and checkpoint separation

Two existing paths have U5E changes:

- `backend/main.py` — new read-only router registration, two added lines; entire file is U5E-safe relative to entry.
- `frontend/src/pages/admin/FitnessAnalysis.tsx` — new import and opt-in wrapper only; **mixed prior U4/Live work must not be staged wholesale**.

Eight new application/test paths:

- `backend/routers/advanced_ga_analysis.py`
- `backend/services/advanced_ga_analysis.py`
- `backend/tests/test_advanced_ga_analysis.py`
- `frontend/src/components/ga/AdvancedAnalysis.tsx`
- `frontend/src/services/advancedAnalysis.ts`
- `frontend/tests/advancedAnalysis.fixtures.mjs`
- `frontend/tests/advancedAnalysis.test.mjs`
- `frontend/tests/advancedAnalysis.browser.test.mjs`

New tooling: `build_fictional_fixtures.py`, `run_checks.py`, `checkpoint_snapshot.py` and `audit_evidence.py` under `docs/testing/dashboard-u5e/`. This report and that directory's baseline, fictional DTO export, original command records, snapshot proofs, failure summaries, screenshots, screenshot review, integration patch, staging plan and manifest complete the inventory. The manifest's `exact_checkpoint_inventory` gives every individual path without a directory-wide staging assumption.

Recommended separately authorized commits: `feat(ga): add candidate-bound advanced faculty analysis`, then `docs(testing): archive U5E analysis validation`. Stage only explicit `whole_file_paths`; apply the supplied `fitness-analysis-integration.patch` to the index for the mixed page. Its `git apply --check --cached` check already passed without staging. Verify the partial page against its proposed blob hash, not the mixed worktree hash. U5D's 24 paths and all unrelated modifications are excluded; decide their checkpoints separately. A fresh upstream comparison is required before any future checkpoint. No commit/push is authorized by U5E.

## Reproduction and limits

From the repository root in PowerShell, with existing dependencies:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/run_checks.py backend
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/run_checks.py backend-regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/run_checks.py backend-engine
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/run_checks.py focused
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/run_checks.py regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/run_checks.py build
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/run_checks.py bundle
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/run_checks.py lint
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/run_checks.py startup
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/run_checks.py browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/checkpoint_snapshot.py
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/audit_evidence.py
```

Browser execution requires the renderer-capable context qualified in U5C-R1; the fresh owned blank-page probe succeeded here. Do not run the fixture exporter over its existing output: it intentionally refuses overwrite. Audit replay checks the recorded inventory; new rerun evidence requires a separately reviewed manifest addendum, not rewriting history.

Analysis is deliberately bounded: at most 200 archive directories, 500 faculty per snapshot, 50 progress observations per window and 10 chart faculty per page. More than 200 directories yields an explicit unavailable response. No large-archive performance, screen-reader certification, full keyboard-tab conformance audit, real-session end-to-end workflow or new PostgreSQL acceptance was performed. Live V2 analytics and complete roster inclusion are separate work. Old records lacking captured preferences cannot supply equivalent modern satisfaction graphs and show unavailable values/recorded indicators instead.

All original GA/scoring/selection/crossover/mutation/RNG sources, workload policy, fingerprint rules, migrations, protected preferences/settings, academic mappings, six historical checkpoints, saved schedules, Saved Best and prior evidence remain byte-identical to entry. D15 retained PostgreSQL was not connected to or inspected. Institutional approval, trusted academic source activation and full optimizer-consumption verification remain unestablished.

Recommended next milestone: qualify a server-owned run-to-department authorization contract for scoped Chair review, and the missing atomic loader-consumption contract identified by U5D. Add V2 analysis only through its separate versioned store contract. None of those authority or execution changes is implemented here.
