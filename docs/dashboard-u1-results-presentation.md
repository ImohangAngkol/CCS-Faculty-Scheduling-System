# U1: results reset, display ordering and optimization progress

Implemented 2026-11-02 on `main`, starting HEAD `f5262637acfb2d4d063cad1b0de80779a10bcba3`. This is a frontend presentation milestone. No backend, stored schedule, historical record, database, fitness policy or engine source changed. Evidence and exact inventory are in [the manifest](testing/dashboard-u1/manifest.json).

## Compatibility findings and the safe boundary

`backend/services/chromosome_service.py` stores the best payload through `save_best_if_better`. Its comparison uses the previous saved penalty. `get_saved_best_metadata` and `/api/chromosomes/best` return existence, fitness and creation time, with no authoritative current-engine/fitness-policy compatibility finding. A new date or a numerical penalty cannot establish compatibility. The existing save/comparison logic was preserved, including its limitation when historical scoring differs.

`backend/services/ga_history_service.py` records engine/input/configuration fingerprints internally and validates captured observations. However, `backend/routers/ga_history.py:lifecycle` does not expose an engine/policy compatibility decision against the running release. The list API supplies lifecycle, timestamps and metrics, which are insufficient to classify a run as current. This investigation inspected source contracts; it did not open or export institutional saved-result payloads.

Accordingly, `resultPresentation.isVerifiedCurrent` deliberately returns false for every record. It is an explicit fail-closed boundary, not a completed version-classification feature or an assumed mismatch. No client version string, date, completion state or fabricated `compatible` flag can promote a record. Both current views explain that even newly generated records remain unclassified until a server-owned compatibility contract exists.

- Saved Chromosomes has **No Current Best Chromosome**, the requested explanation and a dash for unknown current fitness. The preserved record appears as **Historical Archive · Saved Best Chromosome**, with its actual archived penalty. Missing/nonfinite values render as a dash; a measured zero remains zero.
- Saved-baseline use is disabled both in the saved page action and Generate Schedule's radio/submit guard. A remembered `gaPreferredBaseline=saved` is consumed without selecting it. Fresh generation remains available. Explicit upload, upload inspection, historical inspection and download implementations remain in place.
- Generation History defaults to **Current Evaluation**, showing **No Current GA Runs Yet**. **Historical Archive** retains the original run list, lifecycle states, pagination, inspection, comparisons and downloads. Existing `?run=…` links explicitly enter the archive so navigation remains useful.
- This is a presentation guard, not an authorization boundary against direct backend requests. No API baseline admission policy changed. The server's historical best-write comparison is also unchanged. Current-result population and safe persistent cross-version best comparison require separately reviewed provenance/API/storage work; U1 does not claim those are implemented.

## Display ordering

`displaySchedule` returns a new array containing the original row objects. It orders faculty numerically using existing faculty-code normalization, followed by natural subject code, natural section, Lecture, Laboratory, other component types, day, start time and room. End time/title and deterministic lexical comparisons resolve remaining display ties. Nonnumeric faculty labels follow numeric identifiers without losing their identities. Identical display keys retain stable input order. No rows are merged, including separate lecture/laboratory rows.

The adapter is applied at the Generated Schedule table and at historical candidate/before-after tables. Existing search, faculty/day/section filters, weekly calendars, canonical arrays and exports remain unchanged. Calendars retain chronological placement. The shared `components/schedule/ScheduleTable.tsx` is empty and was not repurposed; this change uses the actual implemented tables. Immutable publication/application tables were not reordered.

## Chart semantics

The shared convergence chart used by live monitoring, Generation History and Fitness Analysis defaults to **Optimization Improvement**. **Raw Fitness Penalty** remains selectable. For each series independently:

`absolute improvement = first valid penalty in the same run − observed penalty`

`percentage improvement = absolute improvement / starting penalty × 100`, only for a finite positive baseline. A zero baseline still yields accurate absolute reduction/deterioration, with percentage unavailable. Invalid observations remain missing; missing values break lines rather than being coerced into zero. Negative improvements remain visible. No best-ever/average values are substituted for another series, and no curve is forced to increase.

Labels are **Optimization Progress**, **Penalty Reduction** and **Generation**, with the requested higher-improvement explanation. Keyboard-focusable SVG points have original-penalty/absolute/percentage tooltips and accessible labels. An exact-values table is available separately. Responsive SVG sizing and overflow containers are preserved.

Paginated charts fetch preceding observations from the same run before computing a baseline. Missing/incomplete prefix pages fail visibly; no page-local baseline is substituted. Prefix loads are cancelled on scope changes. Conflicting or partially supplied run/input/configuration/engine/policy identities, explicitly noncomparable metrics and out-of-order generation observations reject the chart. The existing historical backend validates a run's captured engine identity internally; the UI does not infer the current release from that historical fact. Remounting on run identity resets chart mode and prevents cross-run UI state reuse. V2's separate result/provenance view and immutable published-history UI remain unchanged.

## Fresh verification and retained unsuccessful attempts

| Check | Final result | Evidence scope |
|---|---|---|
| New U1 frontend models/contracts | 21 passed, zero failed/skipped | Node tests: currency fail-closed, archive preservation, numeric/natural ordering, immutable rows, improvement/zero/deterioration, series/run identity, pagination and component wiring |
| Existing frontend regressions | 91 passed, zero failed/skipped | Auth/session races, D1, own-schedule, preferences, GA monitoring/recovery/logs/history/reporting/faculty display |
| New rendered U1 scenarios | 12 passed | Actual headless Edge `156.0.4314.50`, React DOM, CDP-intercepted fictional API responses; Node reports 13 including the parent test |
| Existing GA browser regression scenarios | 51 passed | Actual Edge/React with original synthetic response harness; Node reports 52 including the parent test |
| TypeScript | Passed | `tsc -b` |
| Production frontend bundle | Passed | Vite build |
| Focused ESLint | Exit 0, zero errors, four warnings | Existing `ScheduleView` fallback-array/useMemo dependency warnings remain |
| Whitespace, privacy, preservation and artifact hashes | See manifest audit | No institutional database or GA execution |

Build warnings remain for the existing externalReadiness mixed static/dynamic import and the approximately 980 kB application chunk. No unrelated bundle refactoring was performed. Browser access-control checks verify frontend presentation only; backend authorization was not re-proven. No upload/inspection backend action, persistent download write, production scheduling run, real session, PostgreSQL connection or institutional approval was exercised. This is not full-system end-to-end acceptance.

All command records are retained, including unsuccessful attempts:

1. Initial restricted-environment U1 and unchanged GA browser launches timed out at `Page.enable` / `Runtime.enable`, before application scenarios. The same fixtures rendered outside that environment; the observation supports a browser-launch environment limitation, not an application pass.
2. An early U1 fixture used a broad `/api/` interception pattern. It intercepted `/src/api/faculty.ts`, preventing React module loading. Its selected port also used a browser-restricted low port. The fixture now intercepts only its explicit unprivileged fictional API origin. The preserved attempt has no successful scenarios and does not qualify application behavior.
3. Windows default text decoding corrupted a new fixture's expected dash and a new chart file's punctuation. Both new files were corrected to UTF-8. A later attempt reached 11 passing scenarios but its permission assertion expected “denied”; the unchanged portal says “Access unavailable”. The assertion was corrected to the existing protected-route contract. No authentication code changed.
4. Two final U1 runs passed all 12 scenarios. The latest captures scroll the graph/table into view; earlier clipped captures remain historical evidence. All ten retained U1 PNGs were visually inspected for privacy. Their fictional account, resource values and run identity are not institutional approval records. No screenshot was synthesized or edited.

## Exact implementation inventory

Existing frontend files modified:

- `frontend/src/components/ga/LiveGAMonitor.tsx` — consume/re-export the shared chart; bind live chart to run identity.
- `frontend/src/pages/admin/ChromosomeViewer.tsx` — current empty state, archived penalty, status failure explanation, saved-baseline guard.
- `frontend/src/pages/admin/GenerateSchedule.tsx` — reject remembered/unverified saved baseline and label historical fitness honestly.
- `frontend/src/pages/admin/GenerationHistory.tsx` — current/archive navigation, same-run historical chart and display sorting.
- `frontend/src/pages/admin/FitnessAnalysis.tsx` — use the recorded same-run chart with pagination baseline support.
- `frontend/src/pages/admin/ScheduleView.tsx` — sort display rows after filtering.

New frontend files:

- `frontend/src/services/resultPresentation.ts` — honest compatibility boundary, penalty formatter and series transformation.
- `frontend/src/components/schedule/scheduleOrder.ts` — immutable display ordering.
- `frontend/src/components/ga/ConvergenceChart.tsx` — modes, SVG, exact values and accessibility.
- `frontend/src/components/ga/RecordedProgress.tsx` — historical baseline loading/error handling.
- `frontend/tests/resultPresentation.test.mjs` — 21 focused frontend tests.
- `frontend/tests/resultPresentation.browser.test.mjs` — 12 fictional rendered-browser scenarios and genuine captures.

New documentation/tooling: this report, `docs/testing/dashboard-u1/run_checks.py`, `audit_evidence.py`, `preservation-baseline.json`, `manifest.json` and unique timestamped command/browser/PNG evidence. The manifest enumerates every U1 path and hashes all artifacts other than itself. Failed evidence remains intact. Pre-existing unrelated untracked research and development-terminal files are excluded from U1's inventory and preserved.

## Reproduction and manual review

From the repository root in PowerShell, with the existing environment and dependencies:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u1/run_checks.py focused
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u1/run_checks.py regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u1/run_checks.py build
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u1/run_checks.py bundle
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u1/run_checks.py lint
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u1/run_checks.py browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u1/run_checks.py ga-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u1/audit_evidence.py
```

Checks create new timestamped evidence directories and never overwrite prior records. On a restricted execution host Edge may require permission to launch outside that environment. The browser harness uses a new temporary profile, intercepts API responses and closes only its owned Vite/browser instances. It does not require a backend or credentials. New evidence requires a separately reviewed manifest update; the audit will reject an inventory/hash mismatch rather than silently updating approval.

For manual presentation review, use an already authorized isolated fictional application environment: open Saved Chromosomes and verify the dash/current empty state plus historical actions; open Generation History without a run, switch to archive, choose a run and paginate; toggle both chart modes and inspect exact values; open Schedules and compare numeric faculty order, lecture/lab separation and search. Inspect a deterioration and zero-baseline fixture in the browser test rather than manufacturing a production result. Do not click Generate, upload-baseline or publication actions against an institutional environment for a presentation check.

## Preservation and remaining blocker

The baseline covers 2,727 pre-existing paths including 23 academic files, protected preference/settings bytes, original GA/operator/scoring/RNG source, migrations, six historical checkpoint artifacts, saved schedules, prior evidence, Git index and local development configuration. Only the six listed frontend paths may differ. The remaining 2,721 baseline paths must match exactly. Both pre-existing protected local modifications remain untouched and unstaged. HEAD remains the entry commit. No staging, commit, push, migration, database operation, artifact deletion, production optimization or new institutional authority occurred.

The remaining U1 blocker is authoritative current-evaluation identification and version-aware persistent best selection. Address it in a separately scoped backend provenance contract that preserves existing engine/checkpoint fingerprints and explicitly defines comparison compatibility. No date-based guessing, historical migration, fitness change or automatic overwrite is authorized by this UI milestone. Production institutional activation remains blocked by the existing trust requirements.
