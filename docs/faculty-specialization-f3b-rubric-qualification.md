# F3B: experimental specialization rubrics and qualification

Completed 2026-11-01, Asia/Manila. **Isolated rubric qualification complete; no production specialization scoring activated or selected.** Scope is fictional IT prototype measurement. Formal adviser-approved thesis alignment remains **UNVERIFIED**; production institutional authority remains **BLOCKED**. These results establish properties of three mathematical rubrics on a small fictional allocation domain, not faculty competence, institutional scheduling quality, GA convergence or full CCS coverage.

## Inspection and integration boundary

Read the [F3A qualification](faculty-specialization-f3a-qualification.md), its reporting oracle, fictional cases and preserved evidence; the F2D policy/identity/cache contracts; existing eligibility, specialization/domain loaders, fitness, V2 admission and relevant checkpoint tests. Existing semicolon tags are descriptive. The original [eligibility predicate](../backend/genetic_algorithm/utils/Functions.py#L1359) requires an explicit course permission. Preferences, domain matches and missing qualification records cannot grant it. Existing [fitness](../backend/genetic_algorithm/operators/FitnessFunction.py#L984) does not include this new rubric. No changes were made to those paths, the roster, operators, workload policy, fingerprints or dispatch.

F3A found 11 qualification records, 39 eligibility records, 56 domain mappings and 15 eligible pairs without exact domain overlap. Those are **previously recorded F3A dataset findings**, not fresh institutional observations or grounds for revoking eligibility. F3B does not load those records into experiments or manufacture verified specialization profiles. The semester-specific authoritative IT roster and approved specialization standards remain unresolved. No IS faculty are invented.

At entry, `main` was `1199838c7532c03635ec4fc09f2cadd94bed4f1b`, parent `7793da585c855572c72fe4baee9f04d50f1e8ac6`. The intervening owner commit adds exactly `docs/faculty-specialization-f3a-qualification.md`. The [entry record](testing/faculty-specialization-f3b/entry-verification.json) verifies the parent, exact path, report/blob hashes and index transition before establishing the new 2,622-path baseline. Prior manifests are preserved, including their historical Git expectations; none was rewritten to conceal that transition.

## Rubrics and mathematical definitions

For an otherwise eligible offering i, let F be its faculty's verified specialization-domain set, S its subject's nonempty verified relevant-domain set, and I = F intersect S. All main point comparisons require complete current fictional profiles. Faculty unrelated tags neither help nor hurt. Duplicate domains are sets, not extra votes. These are alignment measurements, not a ranking of academic competence.

| Identifier | Alignment a(i), higher is better | Main limitation |
|---|---|---|
| ANY | 1 if I is nonempty, otherwise 0 | One relevant domain can tie complete coverage. |
| COVERAGE | size(I) / size(S) | Equal-domain importance is an explicit hypothesis, not an approved standard. |
| WEIGHTED_COVERAGE | sum(q(d) for d in I) / sum(q(d) for d in S), q(d) > 0 | Requires an approved importance mapping before any institutional use. |

An offering-importance weight w(i) > 0 is separate from within-subject domain importance. Aggregate alignment A = sum(w(i) a(i)) / sum(w(i)); experimental penalty P = 1 - A, lower is better. Main domain importance ratios are 1:1, 3:1 and 9:1, with explicitly named fictional priority domains. Offering-1 importance is 1, 2 or 4 relative to offering-2 importance 1. No order-derived priority or production weights are inferred.

All arithmetic uses `Fraction`, serialized as reduced numerator/denominator **strings** through the existing exact contract. No floating rounding changes rankings. Empty subject domains produce unavailable data, not a denominator of one. Positive teaching assignments to zero-target faculty are not given invented arithmetic or authority; the standalone workload helper rejects that unresolved case. Zero assignment at zero target contributes zero. Main targets are positive.

Worked case: subject-1 domains {X,Y}, subject-2 {Z}; faculty A {X}, B {Y,Z}. Allocation AB has alignment 1 under ANY, 3/4 under COVERAGE, and 7/8 under WEIGHTED_COVERAGE with X:Y = 3:1. Its penalties are 0, 1/4 and 1/8. Allocation BB has the same binary and equal-domain coverage but weighted alignment 5/8 and penalty 3/8. Adding an unrelated faculty tag changes none of these results. If A instead covers both X and Y, COVERAGE distinguishes AB (alignment 1) from BB (3/4), while ANY still ties them.

## Unknown information is a separate dimension

| Convention | Treatment | Scalar comparison |
|---|---|---|
| COMPLETE_BLOCK | Any incomplete assigned profile blocks the whole candidate's point measurement. | Only when every hard-valid candidate in the comparison domain has a point. |
| COMPLETE_BOUNDS | Complete contributions exact; incomplete contributions conservatively span [0,1]. | Only strict interval dominance or exact ties; overlapping bounds are incomparable. |
| POSITIVE_BOUNDS | Current verified partial positive overlap can tighten bounds. ANY can be certain after a verified positive match; coverage lower bounds require a complete subject-domain denominator. | Same interval rule; unverified, contradictory, expired or revoked assertions never supply positive verified evidence. |
| OBSERVED_ONLY | Report mean among complete profiles alongside complete-data coverage. | Diagnostic only; never cached or ordered as a point fitness. |

Missing faculty data, missing subject domains, partial verified profiles, conflicting tags and unverified profiles are separate cases. Tests also cover expired/revoked states. Verified complete nonalignment is a real zero alignment; unknown is not. In the missing-faculty AB case, the observed complete subset appears 100% aligned but covers only 1/2 of assignments. That is not evidence of 100% overall alignment. Conservative total alignment remains [1/2,1].

Importantly, some alternatives in the same allocation domain can have complete data while others do not. Ranking only the complete alternatives would favor data availability and could silently exclude faculty. Therefore the sensitivity analysis blocks the **entire common comparison domain** whenever any otherwise hard-valid alternative lacks a point value. This is a measurement stop, not ineligibility or proof that scheduling is infeasible. No pessimistic/optimistic unknown imputation is adopted as academic policy.

## Fictional experiment and denominators

The [frozen protocol](testing/faculty-specialization-f3b/protocol.json) pins the five-source scoring/fixture/oracle contract to digest `2abbfd83e0f395de32391c23e0675153ae405d3f04e805a54eca7723703de459`, before the main experiment. The [results](testing/faculty-specialization-f3b/20261101T145119885878+0800-experiment/results.json) retain every rejected allocation, hard proof, row metric, rubric configuration and sensitivity outcome. [Independent passive replay](testing/faculty-specialization-f3b/analysis.json) recomputes exact rubric values and every sensitivity minimizer set without a new GA/database run.

Fourteen cases cover one/both/neither eligible faculty matching; missing faculty/subject information; specialization versus subject preference, time preference and workload; multiple domains/specializations; partial, contradictory and unverified facts; and limited eligibility. Every case has two fictional faculty, two 2-unit offerings, two sections and two rooms. AA, AB, BA, BB mean the faculty assignments of offerings 1 and 2. Meetings are Monday/Tuesday 07:30-09:30 on a 30-minute grid. A fixed fictional section commitment starts Monday 09:30; adjacency passes, moving into it fails.

All 56 combinations are enumerated. Three limited-eligibility combinations fail explicit permission checks and remain recorded. All **53 admitted allocations** pass the actual unchanged original V2 full admission/reconstruction gate and an independent faculty/room/section conflict check: 106/106 assignments explicitly eligible, zero hard conflicts, zero unassigned offerings. This is fixed-geometry allocation enumeration; there is no new specialization-aware GA search, convergence experiment or claim of global timetable optimality.

| Metric | Explicit denominator / rule |
|---|---|
| Eligible assignment percentage | Explicitly eligible assignments / all assignments; 106/106 in admitted evidence. Rejected candidates are reported separately. |
| Verified any-domain alignment | Known positive matches / complete assessable eligible assignments; null when none are assessable. |
| Unknown assignment percentage | Incomplete faculty or subject profile assignments / eligible assignments. |
| Data coverage | Complete assessable eligible assignments / eligible assignments; independently reported from alignment. |
| Subject-domain coverage | Mean of size(I)/size(S) among complete assessable assignments; total eligible lower/upper bounds also retained. |
| Subject preference satisfaction | Preferred subject assignments / assignments with active nonempty subject preferences. Both faculty have such preferences in main cases, so denominator 2. |
| Time satisfaction | Assigned half-hour meeting blocks wholly inside the assigned faculty's preferred window / all assigned meeting blocks. Main denominator 8, with both preferences active. |
| Teaching distribution | Full two-faculty cohort, including zero-assignment faculty; loads, target, underload, overload and zero counts. Four offered teaching units remain fixed. |
| Domain distribution | Each multi-domain subject contributes 1/size(S) per domain, including proportional credit units. Unknown subject domains stay in an explicit bucket. |

The complete numerical case table is in `analysis.json`. Both-match and neither-match cases retain eligibility and allow preferences/workload to distinguish schedules; they do not fabricate a specialization distinction. Limited eligibility leaves AB only, regardless of a more favorable alternative rubric score.

## Tradeoffs and sensitivity findings

The standalone sensitivity objective is `cS*P + cP*(1-subject_satisfaction) + cT*(1-time_satisfaction) + cW*D/sum(targets)`. Here D = sum((assigned-target)^2/target) for positive targets, with the explicit zero-target exception rule above. This **fictional analysis namespace** is not original production fitness or an activated F2 workload release. The components remain separately available; normalized D is not guaranteed to be bounded by one for arbitrary workloads.

Option B targets are fixed hypothetical inputs: max(0,24-admin-research-extension). Most cases use [6,6]; the workload-conflict case uses [6,12], implemented with fixed hypothetical administrative allowances [18,12]. No administrative/research/extension activity is scheduled. The existing 30-unit warning/40-unit hard-ceiling policy is untouched, not tested at scale by these 4-unit examples.

Ten explicit coefficient tuples are preregistered in the protocol, ordered (cS,cP,cT,cW): (0,1,1,1), (1,0,0,0), (1,1,1,1), (2,1,1,1), (4,1,1,1), (1,4,1,1), (1,1,4,1), (1,1,1,4), (1,1,1,0), (1,1,1,2). Combined with 14 cases, 3 rubrics, 3 domain ratios and 3 offering-importance values, this gives **3,780 rows: 2,430 ranked, 1,350 blocked**. All ties are retained deterministically; no random tie breaker or policy priority is introduced.

| Comparison | Changed exact minimizer sets / comparable settings |
|---|---|
| ANY versus COVERAGE | 9 / 810 |
| COVERAGE versus WEIGHTED_COVERAGE | 6 / 810 |
| ANY versus WEIGHTED_COVERAGE | 15 / 810 |
| Vary cross-objective coefficients, holding case/rubric/domain/offering importance | 165 / 243 groups |
| Vary within-subject domain ratio, holding other settings | 3 / 810 groups |
| Vary offering importance, holding other settings | 63 / 810 groups |

These are changes in minimizer sets, including creation/removal of ties. They are not statistical population effects, GA improvement rates or institutional benefit estimates. Restricted fixtures explain the small number of rubric disagreements.

Concrete examples at equal domain/offering importance:

| Case | Direct measurements | Sensitivity consequence |
|---|---|---|
| Subject preference conflict | AB: alignment 1, subject satisfaction 0; BA: alignment 0, subject satisfaction 1. Both loads [2,2], D=16/3. | Equal coefficients tie AB/BA. cS=2 selects AB; cP=4 selects BA. Removing workload weight can also admit concentrated ties. |
| Workload conflict | AA: alignment 1, loads [4,0], targets [6,12], D=38/3. AB: alignment 1/2, loads [2,2], D=11. | Equal coefficients select AB; cS=2 selects AA. A specialization objective can worsen target-relative distribution. |
| Time conflict | AA: alignment 1, time satisfaction 0; AB: 1/2 and 1/2; BB: 0 and 1. | Equal coefficients select AB; cS=4 selects AA; cT=4 selects BB. Moving a meeting into the fixed commitment still fails original admission. |
| Multiple subject domains | A covers X, B covers Y,Z; ANY and equal coverage tie specialization-only AB/BB. | X:Y=3:1 or 9:1 makes weighted coverage prefer AB. That requires an explicit importance decision. |

No single coefficient tuple is endorsed. Eligibility, mandatory assignments and hard commitments remain outside these soft tradeoffs. Unavoidable underload remains visible; a specialization score cannot manufacture eligible teaching units or justify excluding faculty.

## Identity, cache and checkpoint boundaries

The new `f3b-fictional-rubric/1` namespace binds actual source digest, rubric, unknown convention, exact domain/offering weights, profile evidence states/revisions, term/taxonomy, required offerings, eligibility, preferences, targets and geometry. The same raw assignments under a different rubric/config/input are incompatible evaluations. Every result/cache lookup validates source/input context. Tagged comparisons and cross-context cache insertions fail closed; altered result fields are recomputed before ordering. No F2 point value is compared with this specialization value.

The bounded passive `F3B_MEASUREMENT_ARCHIVE/1` supports deterministic measurement roundtrips with mandatory external byte-hash pin, identity binding, duplicate-key rejection, envelope/body validation and recomputation. It is **not a GA checkpoint or a continuation-capable specialization engine**. Tests reject changed rubric, missing pin, changed profile revision, changed importance/convention, tampered body even with recomputed checksums, extra fields and a legacy-labelled format. A hash proves bytes, not academic authority.

Separately, the unchanged current-release V1 source mirror passes four real creation/load/continuation cases with 202 byte-identical backend files and three owned fictional archives. Original V2 and F2 checkpoint/operator regressions run through existing isolated workers and owned temporary stores. No historical checkpoint is rewritten or reinterpreted. Previously documented six historical checkpoint incompatibilities remain accepted historical limitations; this milestone does not claim to repair or freshly resume those artifacts. F2H/F2I source/release anchors are verified, while their entire old research campaigns are **not freshly rerun**.

## Fresh validation and retained intermediate evidence

| Selection | Passed | Scope |
|---|---:|---|
| Pure rubric + F2C/F2D contracts | 222 | 44 new rubric/identity/archive cases plus 178 preserved contracts |
| Original admission + thesis audit + V2 engine | 72 | 9 new hard-gate tests plus 63 preserved cases |
| F2 operator/section regressions | 33 | Existing isolated operator-aware engine and reservation behavior |
| F2 checkpoints | 23 | Existing actual continuation, integrity and incompatible-context cases |
| Current V1 mirror | 4 | Actual source-identical creation/load/continuation |
| **Unique final Python total** | **354** | Zero final failed/errors/skipped; repeat passes counted once |
| Frontend Node contracts | **42** | Fitness reporting, identity display, preferences and constrained-GA DTOs; not browser acceptance |

There are 636 repeated-result determinism checks, 636 independently replayed rubric rows and 3,780 independently replayed sensitivity rows, **separate from pytest counts**. No new UI, real browser, HTTP, database, production build, performance, scheduling throughput or institutional acceptance was claimed or needed for this isolated measurement module. Existing D15 acceptance remains historical and untouched.

The [retained intermediate diagnosis](testing/faculty-specialization-f3b/intermediate-diagnosis.json) documents one failed test run: 69 passed, three failed at a new test assertion comparing string rational DTO fields with integer literals, before those three conflict calls ran. The test now uses the preserved exact ratio parser; the rerun passes 72/72 including those conflicts. No production or rubric formula was changed. All failed command/progress/outcome evidence is retained. Preloaded-GA pytest runs report the existing `anyio` assertion-rewrite warning; it concerns test instrumentation, not a passing assertion or hidden skip. Pure tests disable plugin autoload and pass without that warning.

Earlier command records retain a field called `tooling_sha256_at_launch` that the first runner actually sampled at completion. The diagnosis explicitly discloses that limitation. All five frozen computational source hashes agree with the frozen protocol and passive replay; the runner was corrected to record accurately named before/after hashes. The final pure run verifies that instrumentation correction. Historical records were not edited or represented as stronger launch-time attestations.

## Preservation, privacy and exact file inventory

The [manifest](testing/faculty-specialization-f3b/manifest.json) contains the exact **39 new files** and **38 artifact hashes**, excluding its own hash: nine Python files, 23 JSON files, six JSONL files and this Markdown report. All new paths are this report plus `docs/testing/faculty-specialization-f3b/` only. Python modules are rubrics, fixtures, experiment, runner, two test files, V1 mirror verifier, passive analysis and audit. JSON/JSONL records contain the protocol, analysis, entry/preservation/diagnosis and timestamped command/outcome/progress evidence. Existing application, experiment and historical report files modified by F3B: **zero**.

Final audit checks all **2,622** preexisting paths, **23** academic paths and **1,223** historical artifact entries; original V1/V2 fingerprints; F2 release anchors; unchanged HEAD/index; no staged paths or unexpected new files; Git whitespace; every new artifact's syntax/JSON/whitespace; credentials/URI/private-key, complete/partial encoded receipt, bearer/OS security identifiers; and private faculty-name matches against the identity registry in memory only. No real faculty row or protected preference/setting value enters the new evidence. Neither protected file is parsed for experiments or privacy checks.

The two preexisting owner modifications remain byte-identical and unstaged: `backend/data/faculty_preferences.json` and `backend/data/ga_settings.json`. Their contents are not displayed, restored or edited. GA operators, scoring, workload settings, RNG source, input datasets, migrations, checkpoints, schedules, authority gates, previous research evidence and Git index remain unchanged. No database operation, installation, staging, commit or push occurred.

## Reproduction and evidence rules

From the repository root in PowerShell, verify the sealed record without rerunning GA work:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/faculty-specialization-f3b/audit_evidence.py --verify
.\.venv\Scripts\python.exe -B docs/testing/faculty-specialization-f3b/analyze.py --verify
```

To generate fresh timestamped validation records after a separately reviewed evidence extension:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/faculty-specialization-f3b/run_checks.py pure
.\.venv\Scripts\python.exe -B docs/testing/faculty-specialization-f3b/run_checks.py original
.\.venv\Scripts\python.exe -B docs/testing/faculty-specialization-f3b/run_checks.py F2-operators
.\.venv\Scripts\python.exe -B docs/testing/faculty-specialization-f3b/run_checks.py F2-checkpoints
.\.venv\Scripts\python.exe -B docs/testing/faculty-specialization-f3b/verify_v1.py
.\.venv\Scripts\python.exe -B docs/testing/faculty-specialization-f3b/run_checks.py frontend
.\.venv\Scripts\python.exe -B docs/testing/faculty-specialization-f3b/run_checks.py experiment
```

The protocol is already frozen: do not run its creation again or overwrite the manifest, analysis, baseline or results. Each worker uses a new timestamp directory, whitelisted child environment and bounded runtime. Fresh evidence changes the inventory and therefore requires a new reviewed addendum/manifest rather than claiming it matches the sealed record. The passive analyzer intentionally requires one main experiment artifact for this release; compare a fresh run independently in a new qualification addendum. Existing evidence must be preserved. No credentials or database setup are needed.

## Policy questions and F3C recommendation

| Decision / dependency | Classification | Required next step |
|---|---|---|
| Explicit eligibility overrides soft wishes/matches | Already verified | Preserve every hard gate and audit violations separately. |
| Coverage rubrics resist unrelated-tag inflation | Already verified on fictional cases | Validate taxonomy granularity and completeness before interpreting institutional scores. |
| Equal-domain coverage as a transparent reference measurement | Recommended but unapproved | Adviser/department review; not a production default. |
| Binary sufficiency versus breadth; primary/secondary importance | Requires adviser and institutional confirmation | Decide whether domains are necessary coverage, alternatives, levels or merely descriptive. |
| Completeness, contradictions, expiration and partial evidence | Requires institutional confirmation | Identify authorized verifier, term-specific trusted records, revisions/revocation and independent evidence lifecycle. |
| Specialization/preference/time/workload priority | Requires adviser and institutional confirmation | Agree objective hierarchy or explicit normalized weights and acceptable tradeoffs. |
| Versioned specialization-aware engine/dispatch/checkpoint | Requires implementation and additional testing | Separately reviewed release with consistent operator scoring and rejection of mixed-policy history/cache/checkpoints; preserve existing release validation. |
| IT evaluation cohort and cross-department resources | Requires institutional data and confirmation | Complete approved semester-specific IT roster/eligibility/qualifications; document shared IS resources without inventing IS staff. |
| Positive assignments at zero teaching target | Existing developer rule; arithmetic/authority integration unresolved | Require valid scoped exceptional authorization; do not repurpose publication authority or choose denominator-one arithmetic. |
| Formal research objectives and real scheduling benefit | Requires adviser manuscript and additional testing | Compare approved metrics and real evaluation design; these 14 tiny cases cannot establish empirical efficacy. |

**Conditional GO for a separately authorized F3C isolated data-governance/dispatch qualification, with COVERAGE retained only as an unapproved reference and all three alternatives available. NO-GO for production specialization scoring, final weights or institutional scheduling activation.** Before integration, qualify trusted complete IT specialization data, decide unknown and taxonomy policy, and extend the versioned operator/selection/best-ever/checkpoint contract with exact parity tests. No next milestone was started.
