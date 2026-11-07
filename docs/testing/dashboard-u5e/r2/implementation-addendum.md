# U5E interaction completion and renewed checkpoint review

2026-11-05, Asia/Manila. Continuation of the existing U5E implementation at `d6db077793da52b7559351a5d0f8e6d54608cb77`; not a new GA or authority milestone. This addendum and `r2/manifest.json` supersede the previous checkpoint inventory for the current source revision. Original U5E evidence and unsuccessful attempts remain preserved.

## Completed request gaps

The existing three tabs, seven graphs, heatmap, captured-preference details, same-run snapshot comparison and read-only backend contract were retained. The updated request's remaining supported interactions are now implemented:

| Requirement | Current behavior |
|---|---|
| Select faculty through charts | Nonempty bars across all seven faculty charts open the same candidate-bound read-only dialog. Enter/Space and accessible table buttons also support selection. Pointer and Enter actions were exercised in Edge. Missing or zero-height bars remain inspectable through the heatmap/table. |
| Percentage labels | Subject/day/time bars show descriptive percentages. An explicit baseline marker displays actual 0%; absent preferences still have no percentage. Full numeric fitness remains separate and unchanged. |
| Low-satisfaction highlighting | Values below 40% use the heatmap's existing descriptive low band. The chart states that this is a display threshold, not an optimizer/scoring rule. Text statuses accompany color. Boundary tests cover 0, 39, 39.99, 40, 70 and 100. |
| Preparation-limit highlighting | Highlight only when the actual captured reference exists and preparations exceed it. Equality does not exceed the reference. Missing/invalid references never introduce a default limit. Isolated display-rule tests cover excess/equality/missing cases; no institutional policy limit was invented. |
| Diverging workload bars | Positive deviation is orange, negative deviation blue, zero neutral, with the existing zero reference and actual unit values. The arithmetic cohort mean definition is unchanged. |
| Teaching-hour totals | Visible per-faculty weekly totals and accessible table totals accompany the day-stacked chart. Values come directly from the existing backend's merged-interval `weekly_hours`, without re-counting meeting rows or changing calendars. |
| Best-so-far identity | Summary distinguishes the selected candidate's fitness from the recorded best-ever penalty at that generation, where the compatible progress observation exists. It explains generation-best versus best-ever selection; missing observations stay unavailable. |

`analysisChartPresentation.ts` contains only descriptive display rules. No backend, GA, workload, preference policy, source qualification, provenance capture, receipt service or persistence implementation changed in R2. The original report continues to document the exact seven metric formulas and source mapping. Browser fixture fitness numbers remain explicitly fictional stored DTO examples, not measured optimization results.

## Current evidence

| Fresh check | Outcome |
|---|---|
| U5E/U5D backend | **56 passed**, 2 existing dependency warnings; U5E projection/auth tests plus U5D observation/receipt tests, including actual fictional engine parity/continuation and an owned loopback receipt-read test. No real sessions or institutional database. |
| Frontend focused | **30 passed**: 17 existing U5E contracts and 13 new display/interaction contracts. |
| Existing frontend regressions | **166 passed**. |
| Current U5E browser | **20 scenarios passed**; Node reports 21 tests including the parent harness. Actual Edge/React DOM with fictional CDP-intercepted HTTP. No browser-to-FastAPI/PostgreSQL acceptance claim. |
| TypeScript/build/lint | **PASS** in the worktree and independently tested selective source snapshot. |
| Git integrity | `git fsck --no-reflogs` exit 0; pre-existing dangling objects retained. |
| Independent snapshot | All seven groups passed: **20 backend**, **30 focused**, **166 frontend regressions**, TypeScript, production build, focused ESLint and **20 browser scenarios**. HEAD plus current U5E source only; no uncommitted U5D or U4/Live dependency. |

The 145 reporting/history/provenance tests, 34 V1/V2 tests and 39 U5A–U5C browser scenarios from the preceding U5E signoff were **reviewed, not rerun** in this UI-only continuation. Do not add repeated tests or parent harnesses to fresh scenario totals. The final independent proof is [20261105T164801574539+0800-snapshot](20261105T164801574539+0800-snapshot/snapshot-proof.json).

Final original screenshots include [seven charts](20261105T164801574539+0800-snapshot/U5E-B01-charts.png), [bar-selected faculty](20261105T164801574539+0800-snapshot/U5E-B17-bar-details.png), [zero percentage](20261105T164801574539+0800-snapshot/U5E-B19-percentage-labels.png) and [hour totals](20261105T164801574539+0800-snapshot/U5E-B20-hours-and-best.png). All R2 PNGs were visually reviewed by distinct raw hashes and matched by exact hash for identical duplicates. No screenshots were fabricated, edited or regenerated from descriptions.

## Unsuccessful evidence and diagnosis

- The first combined backend run recorded **56 setup errors**, zero passing assertions: pytest could not create numbered fixture directories inside the Windows sandbox temporary root. No application assertion or database operation ran. The same selection passed outside that sandbox using new owned temporary paths; no permissions, dependency, application or database changes were used to obtain a pass.
- Initial B19 attempts did not establish the zero-label assertion. An explicit zero marker was added for zero-height percentage bars. A subsequent fictional SVG diagnostic showed `0%` in the rendered labels while the assertion inspected the empty legend SVG. The test now targets actual chart labels. The temporary source rehearsal additionally exposed an immediate lookup before labels mounted; the test now waits for those labels using the existing bounded synchronization helper. No timeout was increased and no scenario was removed or disabled.
- Two failed selective snapshot runs and all earlier browser records remain. The final source snapshot passed all seven groups. Failure diagnostics remain identifiable independently of later success.
- Existing Starlette/httpx and AnyIO deprecation warnings, Vite static/dynamic import and chunk-size warnings remain. No dependency installation or broad cleanup occurred.

## Preservation and entry reconciliation

At continuation entry, all **140 prior U5E artifact hashes** still matched. The old audit stopped because seven additional runtime files existed since its earlier signoff: one checkpoint, four saved-history files and two input-receipt files. Read-only metadata dates established these were later additions; no payload was inspected or archived. They were included in the **3,414-path R2 entry baseline**, preserved and excluded from the checkpoint. Their existence is not evidence of consumption verification or institutional approval.

Only two paths already present at R2 entry changed: `frontend/src/components/ga/AdvancedAnalysis.tsx` and the parent implementation report. Their exact previous bytes are archived in `r2/entry/`, so the earlier manifest remains independently verifiable through explicit artifact aliases. All other **3,412 baseline paths** must match exactly. All 23 academic files, protected local preferences/settings, original GA/scoring/RNG and engine-fingerprint modules, migrations, retained checkpoints, schedules, Saved Best, U5D's 24 paths and unrelated U4/Live/research work remain unchanged. Runtime file inventories are checked for unreviewed additions. Git index/HEAD remain unchanged; no staging, commit, push, deployment or database operation occurred.

The new application/test paths are exactly:

- `frontend/src/services/analysisChartPresentation.ts`
- `frontend/tests/advancedAnalysisInteraction.test.mjs`
- `frontend/tests/advancedAnalysisInteraction.browser.test.mjs`

New R2 tooling/evidence includes this addendum, entry baseline and review, two archived entry files, runner, snapshot verifier, audit, command records, original PNGs, SVG diagnostics, snapshot proofs, screenshot review, manifest and selective staging plan. `r2/manifest.json` enumerates every individual path for the **combined U5E checkpoint**, not just the continuation. The original root manifest and staging plans remain historical; they have not been silently rewritten to match new source.

## Remaining boundaries and checkpoint plan

All seven requested charts are functional for defensible recorded data. Historical satisfaction/progress without sufficient captured context remains partially supported and explicitly unavailable. Comparisons remain same-run, distinct-snapshot and matching-policy/input/configuration only. V2/transient loaded candidates retain their original views. Department Chair analytics requires an authorized run-to-department binding; it remains blocked. U5D consumption receipts remain UNVERIFIED, production context providers unconfigured, institutional activation blocked, and Saved Best promotion unchanged. There is no uncontrolled continuous optimizer.

The selective source snapshot demonstrates that current U5E can be tested without unrelated work. The **R2 selective staging plan** lists whole-file paths and the existing minimal cached patch for `FitnessAnalysis.tsx`. Never stage that mixed page wholesale. Exclude all U5D paths, protected data/settings, seven runtime additions and unrelated changes. A fresh upstream comparison and separate authorization are required before a Git checkpoint; none is performed here.

Recommended next work remains scoped Chair analysis authorization and the independently approved loader-consumption boundary contract. No production authority, persistence, GA integration, optimization or next milestone is automatically started.

From the repository root, using installed dependencies:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/r2/run_checks.py focused
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/r2/run_checks.py regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/r2/run_checks.py backend
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/r2/run_checks.py build
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/r2/run_checks.py bundle
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/r2/run_checks.py lint
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/r2/run_checks.py browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/r2/checkpoint_snapshot.py
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5e/r2/audit_evidence.py
```

Browser and temporary backend tests need the qualified renderer/temp-capable execution context. Runners append uniquely named evidence; after sealing, new records require an explicit reviewed manifest addendum. Audit replay is non-mutating and deliberately rejects later unexplained content or runtime changes.
