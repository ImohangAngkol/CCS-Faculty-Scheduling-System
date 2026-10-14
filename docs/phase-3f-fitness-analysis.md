# Phase 3F: Explainable fitness analysis

## Inspected scoring behavior

The current scorer is `backend/genetic_algorithm/operators/FitnessFunction.py`.
Its result is the sum of eight components; lower is better. It has no separate
reward branch. The reporter reads actual recorded contributions rather than
assuming that every preference indicator is a penalty.

| Component | Actual rule | Inspected resolved weight |
| --- | --- | --- |
| Ranked subjects | Per offering: rank index / preferred-list length, or 1 for an unlisted subject, multiplied by weight, importance, and priority multiplier. First rank costs zero. | 70 |
| Preferred times | With subject blocks: each requested start absent from raw component blocks. Otherwise: each component extending outside the general preferred window. | 10 |
| Preferred days | With subject blocks: each requested day absent from the component. Otherwise: one penalty per offering with days outside the preferred set. | 5 |
| Schedule style | Compact: daily ceil(total idle minutes / 30). Spread Out: one step per component gap below 30 minutes. Both use component daily bounds, importance and priority. | 10 |
| Lecture/laboratory days | Same Day requires any shared day; Different Days requires no shared day. One weighted mismatch per offering with both components. | 5 |
| Preparations | Unique subject codes above the preparation limit, multiplied by preparation weight and priority. Multiple sections of the same code are one preparation. | 10; limit 3 |
| Teaching workload | Underload: ceil(shortfall / faculty target × 10). Overload up to the warning threshold and heavy overload above it use separate ceil(excess / step units) bands. No priority multiplier. | Underload 25; overload 10; heavy overload 25; step 3 units |
| Daily teaching time | Merge actual teaching intervals; ceil(minutes above the daily limit / daily step) × weight. No preference importance or priority multiplier. | 10; limit 360 minutes; step 60 minutes |

These numbers document the inspected configuration, not new defaults or an
override. Reports display original captured settings where available. The
legacy `target_teaching_load=12`, `load_tolerance`, and the raw JSON
`regular_teaching_load=18` are not used as the faculty target. The settings
loader resolves its regular-load alias from the 24-unit total workload model.
`load_balance_penalty` is a compatibility fallback, not the active underload
weight when the dedicated settings exist. Legacy scorer keyword arguments
are ignored by the existing scorer; this phase does not change that behavior.

Importance is clamped to 0..5. The actual priority multiplier is
`max(effective priorities) - faculty priority + 1`. Preference/preparation
penalties use it; workload and daily teaching penalties do not.

Subject-specific calendar blocks have two notable existing semantics:

* Day and start-time membership are checked independently, not as a joint
  day/start match. Both can match different meetings.
* Start membership includes internal raw blocks of a longer meeting. A request
  for 09:30 can match the internal 09:30 block of a 09:00–11:00 lecture.
* Under original policy 1 these blocks bypassed day/time enable toggles.
  Phase 3F.2 adds policy 2 for new evaluations: explicit false flags disable
  the corresponding exact-block contribution. Legacy checkpoints/reports keep
  policy 1; historical scores are never rewritten.

General day matching uses the scorer's existing normalizer. Calendar day codes
are normalized separately when checking captured raw intervals against the
portable schedule, so reporting does not alter preference matching semantics.

Hard eligibility, resource conflicts, 40 teaching units, fixed institutional
schedules, external ITE184 Palad/ICT3A locks and continuous laboratories remain
mandatory publication gates outside fitness. No gate is bypassed by reporting.

## Architecture and provenance

`fitness_reporting_service.py` produces observation-only DTOs. It never calls
fitness, population generation, operators, or random sampling. Global and
per-faculty penalties come exclusively from already evaluated, recorded data.
Components must be finite, match the supported eight-component contract and
reconcile with the recorded overall total. Recorded faculty sums are reported
separately; absent contributions are never allocated to force equality.

Future generation snapshots receive additive fields:

* `reporting_context`: original effective preferences, resolved settings,
  normal-faculty release profiles, input fingerprint and scorer source hash.
* Each candidate's `reporting_assignments`: offering credit units, instructor
  role/display label and original raw lecture/laboratory intervals.
* Final analysis sidecars retain the existing `faculty_analysis`, together
  with the reporting context and best-ever raw assignments.

These fields are captured from the existing frozen run at a validated boundary.
Only small JSON DTOs are added. No extra fitness evaluation or RNG draw occurs.
The existing bounded queue, atomic/checksummed writes and capacity policies
continue to apply. Resume reporting uses checkpoint-preserved legacy priorities;
the checkpoint format and engine fingerprinted source files are unchanged.

Raw intervals matter because the portable calendar merges consecutive blocks.
Reporting validates raw interval coverage against that immutable calendar
before using it for descriptive preference comparisons. It does not construct
a new historical schedule or accept current faculty eligibility as a substitute
for the original publication validation.

Existing snapshots and checkpoints are not migrated or rewritten. Older
snapshots retain known totals/workloads and explicit missing values. A matching
candidate may have a later final-evaluation sidecar; its evaluation timestamp
and source are identified, not presented as an evaluation performed at the
earlier boundary. Latest-result reporting also reuses its original stored
faculty analysis when an older sidecar retained only the global breakdown.
Neither path re-evaluates against current preferences.

Pandas sometimes serializes faculty codes as integral floats. The report joins
`7.0` and `7` as the same existing code; it does not assign new faculty identities.

## Workload and preferences

Teaching target is `max(0, 24 - admin - research - extension)`. Actual units are
course credits counted once per faculty/offering, not summed calendar hours.
Difference is actual minus target; fulfillment is actual / target × 100.
Zero targets yield no percentage, and overload percentages are not clipped.
Unassigned normal faculty remain visible. Underload bands are descriptive;
their penalty is displayed only when an original contribution was recorded.
External instructors are named separately and excluded from normal scoring.

For new captured contexts, preference indicators use the inspected scorer's
predicates and original raw intervals. Ranked subject percentages are
descriptive rank credit; day/time counters follow per-offering scoring units;
gap results describe component gaps; lecture/lab results describe shared days.
Satisfied, partially satisfied, unmet, disabled and no-applicable-comparison
states are separate. Importance zero can leave a descriptive match visible
while its fitness influence is explicitly off. Missing component penalties
remain null even when a descriptive match can be calculated.

When only older final percentages were recorded, those values are labeled as
recorded descriptive indicators. Original enable flags, release components or
raw intervals are not guessed. When no preference observation exists, the
page says it was not captured. If the captured scorer hash differs, new
predicate-based interpretation is unavailable instead of using changed rules.
The complete recorded engine fingerprint is checked as well, protecting
interpretation when a normalizer/model dependency or runtime changes.

## Pages, comparison and exports

The existing `/admin/analysis` page retains the MSU-IIT theme and live monitor.
It adds source/run/generation/candidate selection, faculty and workload filters,
component explanations, release/workload tables, preference results and CSV/
JSON downloads. It reuses `ConvergenceChart` and paginated Generation History.
Generation History links directly to an explanation of the selected candidate.
Source, generation and candidate are represented in the URL for refresh.

The existing saved/uploaded "View Results Only" workflow remains supported.
Its previously evaluated result in GAContext is displayed as a loaded-candidate
evaluation, with no new API scoring call. Original unavailable targets and
release details remain unavailable. Local exports identify this source and
leave generation blank; this ephemeral evaluation is not claimed to be a
historical GA generation. Reload the candidate after browser refresh if needed.

Generation comparison first enforces matching run inputs, configuration and
engine. It compares original workload distribution, descriptive preference
outcomes, assignment changes and component reductions where both were
recorded. Positive reduction means improvement. Missing observations cannot
numerically explain an improvement, and measured associations are not claimed
as proof of causation.

Read-only routes:

* `GET /api/ga/fitness-analysis/latest`
* `GET /api/ga/fitness-analysis/latest/export?section=fitness|workload&format=json|csv`
* `GET /api/ga/runs/{id}/generations/{g}/fitness-analysis?candidate=generation_best|best_ever`
* The same generation route with `/export`, `section` and `format`.
* `GET /api/ga/runs/{id}/fitness-comparison?left={g}&right={g}&candidate=...`

Exports include definitions, source run/generation/candidate identity and
capture timestamps where recorded. JSON preserves nulls; CSV leaves unknown
cells blank. CSV uses existing formula-injection protection on every field.
Loaded-candidate exports apply equivalent quoting/formula protection locally.
Report exports contain observations, not a schedule newly validated against
changed institutional inputs. Existing candidate schedule exports retain their
separate hard-validation requirements.

## Files changed

| Area | Files |
| --- | --- |
| API | `backend/main.py`; new `backend/routers/fitness_analysis.py` |
| Reporting/storage | new `backend/services/fitness_reporting_service.py`; `backend/services/ga_history_service.py` |
| UI | `frontend/src/pages/admin/FitnessAnalysis.tsx`; `GenerationHistory.tsx` |
| Client contracts | new `frontend/src/services/fitnessReporting.ts`; `gaHistory.ts` |
| Backend tests | new `backend/tests/test_fitness_reporting.py` |
| Frontend tests | new `frontend/tests/fitnessReporting.test.mjs`; `gaMonitoring.browser.test.mjs`; `frontend/package.json` |
| Documentation | this file |

The pre-existing modification to `backend/data/faculty_preferences.json` was
preserved byte-for-byte and is not a change made by Phase 3F.

## Limitations and acceptance

No exact per-generation component decomposition is available when the scorer
returned only a total. This phase does not instrument scorer internals or add
evaluations to recover it. Original missing releases, enable flags and raw
intervals cannot be reconstructed from current inputs. Loaded evaluations lack
durable historical provenance. Existing snapshot retention/backpressure can
still omit generations; reporting does not create replacements. Backend
authentication and role enforcement are not implemented. Administrator/faculty
portal labels and hidden controls do not provide access control.

Manual acceptance:

1. Reload the backend to load the new routes. Inspect a completed run in
   Fitness Analysis and verify component sum equals overall penalty.
2. Inspect an older boundary without decomposition. Missing values must stay
   explicit, with no zero-filled bars or current-preference substitution.
3. Verify each captured target/release/actual/difference/fulfillment against
   the original workload model; inspect unassigned faculty and external locks.
4. Compare two saved generations. Check source/candidate identity and missing
   contribution states. Change current preferences and confirm old reports
   retain their original observations.
5. Download analysis/workload CSV and JSON; check source fields, definitions,
   null/blank values and safe spreadsheet cells.
6. Use existing saved-candidate View Results Only and navigate to Analysis.
   It must retain that original evaluation without generating or re-scoring.
7. Refresh a historical view; verify the same source, generation and candidate.

No commits, pushes, database migration or Phase 3G implementation are included.

## Verification

| Checks | Result |
| --- | --- |
| Phase 3F reporting accuracy, workload/pref indicators, concurrent historical reads, legacy results and CSV/JSON exports | 25 passed |
| Existing Phase 3B–3E backend suites, including RNG/all-fitness-call equivalence | 142 passed |
| Existing real-browser backend pause/refresh/resume integration, isolated test server/storage | 1 passed |
| Frontend monitoring/recovery/log/history/report contracts | 46 passed |
| Isolated browser suite, including latest convergence, fitness filtering, comparison, exports, refresh and loaded-candidate compatibility | 47 passed |
| TypeScript/Vite production build and focused ESLint | Passed; existing bundle-size warning remains |
| Whitespace check and protected-file SHA-256 verification | Passed; 125 files unchanged |

The 142-case backend run excluded the real-browser test, which then passed
separately. Additional focused continuation checks were run after the final
reporting adapter adjustment. The protected set includes the scorer, models,
operators, engine/checkpoint services, notebooks, all current input data,
checkpoints and saved schedules/snapshots. No production GA was executed.

A read-only check of the existing stored run
`ba440200-b932-454e-a814-b6633723ffe1`, generation 20, returned overall penalty
20,770 and recorded component sum 20,770. It recovered 11 faculty rows, all 11
original teaching targets and all 11 recorded preference rows without scoring
or changing any artifact. Legacy release components remain unavailable.

The in-app browser connection failed during setup; UI verification used the
repository's isolated headless Edge harness with mocked API responses. The
separate real-browser regression used its existing temporary live test backend.
