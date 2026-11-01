# F3C: specialization policy decision and institutional data readiness

2026-11-01, Asia/Manila. **Qualification and decision package complete; NO-GO for institutional integration.** Scope: user-reported IT prototype, not the whole College of Computer Studies. No rubric, production weight, qualification authority or institutional profile is approved or activated by this document. Formal adviser-approved thesis alignment remains **UNVERIFIED**; the manuscript is outside the repository. This package is ready for adviser/department review, not deployment.

## Baseline and evidence status

Reviewed [F1](faculty-cohort-f1-implementation.md), [F1.5](faculty-cohort-f1-5-it-qualification.md), [F3A](faculty-specialization-f3a-qualification.md), [F3B](faculty-specialization-f3b-rubric-qualification.md), the three experimental rubrics and current eligibility/domain loaders. F1's roster-first principle is user-reported approved, but no verified complete semester IT roster/profile provider is configured. The operational roster still depends on legacy preference-derived keys. Missing preferences must not become an exclusion criterion in the proposed roster contract; this milestone does not cut over that source.

HEAD remains `1199838c7532c03635ec4fc09f2cadd94bed4f1b`, branch `main`, index unchanged. The entry check verified all 38 F3B artifact hashes and established a **2,661-path** preservation baseline including all earlier changes and F3B's 39 new files. The prior reports and evidence, including unsuccessful attempts, are preserved.

F3B's **354 Python tests, 42 frontend contracts, 53 hard-valid allocations, 636 rubric evaluations and 3,780 sensitivity rows** are reviewed historical evidence, not fresh F3C GA/browser results. Of those sensitivity rows, 1,350 were unranked because incomplete specialization data prevented comparing the complete hard-valid alternative set. The fresh F3C work is aggregate read-only taxonomy inspection, a passive review contract and focused fictional consistency tests. No real records become examples or approved profiles.

## Rubric comparison for a decision

For an explicitly eligible assignment, F is the faculty domain set and S the nonempty relevant subject-domain set. Point values require appropriately verified complete profiles, unless a separately approved partial-evidence convention applies. Aggregate alignment is the declared offering-weighted mean; penalty is 1 minus alignment. F3B uses exact reduced rational values, not rounded floats. Unrelated extra faculty tags do not increase scores.

| Dimension | ANY: indicator of nonempty intersection | COVERAGE: size(F intersect S)/size(S) | WEIGHTED_COVERAGE: relevant matched weight / total relevant weight |
|---|---|---|---|
| Interpretation | At least one recognized relevant domain | Breadth of declared subject-domain coverage | Breadth according to approved within-subject relevance |
| Required data | Verified domain sets and matching rules | Complete subject domain denominator, complete faculty facts and taxonomy | Coverage data plus exact positive domain weights; separate offering weights if used |
| Explanation | Simplest, but a small overlap can tie full coverage | Transparent fractions; assumes equal domain importance | More complex; requires explanation of every weight/version |
| Multiple specializations | One relevant match saturates; no raw tag-count reward | Only distinct relevant domains contribute | Only distinct relevant weighted domains contribute |
| Multiple subject domains | Treats one as sufficient for full binary alignment | Represents partial breadth | Can distinguish primary/secondary importance only after policy approval |
| Missing data | Unknown, not automatically false; current verified partial positive evidence may establish binary overlap under a distinct convention | Unknown denominator cannot be invented; partial positives can support bounds if subject mapping is complete | Same missing-data restrictions plus unavailable weights block weighted assessment |
| Sensitivity | No within-domain weights; aggregation/other objectives still matter | Sensitive to taxonomy granularity and offering aggregation | Also sensitive to arbitrary domain weights and priorities |
| Eligibility | Never creates/revokes course permission | Same | Same |
| Workload interaction | Can reward concentrating both subjects on one matching person | Same risk; balanced target fulfillment remains a separate objective | Weight changes can intensify concentration; never override hard ceilings |

An unapproved experimental starting point is **COVERAGE as a reference measurement plus ANY, unknown rate and data coverage alongside it**. Keep weighted coverage for sensitivity analysis until importance is justified. This is not a final rubric choice. A subject's tags might represent necessary complementary expertise, alternative acceptable areas, or loose descriptive topics: coverage could be inappropriate if the department means alternatives. That semantic decision must precede institutional interpretation.

F3B illustrates why no coefficient is selected: equal coefficients tie opposite specialization/preference choices in one case, and higher specialization weights can favor concentrated workloads or unsatisfied time wishes. Across 810 comparable settings, ANY versus COVERAGE changed nine minimizer sets; COVERAGE versus weighted coverage changed six. Those tiny fixed-geometry fictional cases are not real faculty performance evidence or a measured GA benefit.

## Minimum official data contract

The machine-readable review package under this evidence directory is a **passive proposal**, not a database schema, upload format, authority service or populated roster. Required fields must exist with explicit states; unknown data can be represented without inventing a value. It does not follow that an unknown record is ready for scoring.

| Required input | Minimum semantics | If unavailable |
|---|---|---|
| Stable faculty identity | Existing UUID, legacy code and privately reconciled binding | Stop binding; never match by name similarity or row order |
| Academic year/semester | Official term ID, effective dates and calendar applicability | Stop term-sensitive use; filenames/season flags insufficient |
| Department membership and participation | IT membership, included/excluded reason, complete roster revision and attestation | F1 production integration blocked; do not construct cohort from preferences or invent IS faculty |
| Approved teaching eligibility | Explicit allow/deny/unknown/conflict by course or offering, term, issuer, reason, revision and effective interval | Missing/unknown/conflict never authorizes an assignment; specialization/preference cannot fill the gap |
| Specialization state | Complete, partial, unknown, unverified, contradictory, expired or revoked | Keep explicit unknown; retain faculty in roster |
| Specialization domains | Controlled IDs required for an assessable claim; attested empty differs from null/missing | Alignment unavailable or bounded under approved convention |
| Qualification provenance | Conditional on verified claims: restricted evidence reference/hash/type, issuer, validity and custody | No verified-specialization claim; no CV/credential document is published in evidence |
| Subject identity and applicable domains | Stable course/offering/curriculum scope, mapping completeness, taxonomy version and mapping revision | Unknown classification remains unknown, even if a tag exists |
| Record version | Immutable revision/hash, effective dates, supersession/revocation and correction reason | No reliable replay or lifecycle validation |
| Verification authority | Named actor plus independently established qualification capability and department/term mandate; verification time/decision | Authority remains unresolved; login role alone is insufficient |
| Approval status | Pending/approved/rejected/revoked plus scoped approval reference and genuine issuer verification | A self-declared flag, signature label or hash is not approval |

Optional: display name, restricted reviewer notes, biography/CV copy if policy permits, and authenticated applicable preferences. Missing preferences do not remove faculty or imply nonqualification. Degree title, experience thresholds and what documentary evidence is mandatory require D01; this report does not invent an accepted qualification standard. Domain/offering weights are required **only if** that weighted policy is approved.

Workload inputs, calendars and confirmed external commitments remain separately necessary for scheduling. They are not inferred from specialization records. Fixed recognized non-teaching allowances reduce teaching targets under Option B but are not scheduled activities. Shared external teaching-credit accounting remains unresolved as recorded in F1.5; a time reservation alone does not add teaching credits to workload totals.

## Fresh taxonomy qualification

The new bounded inspector reads only the qualification, eligibility, domain and two curriculum CSVs. It exports source hashes and aggregate counts, not faculty names/codes, subject rows, tag strings, notes or identity links. It imports no GA and reads neither protected JSON file. All five source hashes match the preserved academic baseline.

| Finding | Actual aggregate observation | Interpretation / required review |
|---|---|---|
| Current inventory | 11 qualification rows, 39 eligibility rows, 56 distinct subject keys | Operational records, not an approved term cohort or verified expertise |
| Exact vocabulary mismatch | 20 faculty versus 76 subject tag strings; two faculty strings absent from subject vocabulary and 58 subject strings absent from faculty vocabulary | Unmatched terminology/coverage needs private review; not proof of deficient faculty or wrong subject mapping |
| Simple spelling probe | Zero case/whitespace variant groups; both unmatched faculty strings remain unmatched after that diagnostic probe | Case/space normalization alone does not explain the mismatch; no synonym/semantic merge inferred |
| Multi-domain classifications | 49 of 56 rows have multiple relevant domains | Department must define necessary versus alternative domains and primary/secondary meaning |
| Duplicate/inconsistent source keys | Zero duplicate subject-key rows, conflicting duplicate-key groups, blank keys or blank primary domains | No detected structural conflict in this snapshot; no claim that classifications are academically correct |
| Repeated categories | Three identical domain-set groups across subject rows; 120 overlapping unordered pairs among distinct nonempty domain sets | Subjects may legitimately share categories. These counts do not prove duplicate concepts, synonyms, hierarchy or ambiguity resolution |
| Repeated tokens within a row | Zero repeated secondary tokens; zero primary tokens repeated in secondary | No automatic de-duplication needed for these observed structures |
| Missing seasonal classifications | Zero missing domain rows for the 19 first-list and 55 second-list course keys | Structural key coverage only; actual term offerings and curriculum completeness remain unverified |
| Eligibility and overlap differ | 15 eligible pairs have no exact tag intersection; zero eligible course keys lack a domain row | Never revoke eligibility or auto-grant a new permission from lexical alignment |
| Structured institutional lifecycle | No canonical year/term/department/taxonomy-version/verifier/approval/revision columns found in the three relevant CSVs | Notes and season flags do not establish those contracts; no approved complete specialization profiles are established by this repository evidence |

Ambiguous academic classification and potentially inconsistent **meaning** remain unresolved, even where keys are structurally unique. F3A recorded review/inference markers across all 56 mapping rows and partially qualified faculty provenance; those are preserved prior findings, not freshly reinterpreted institutional approval. No domain label is renamed, merged or selected as authoritative here.

Proposed verification workflow, all unapproved pending D01-D03/D10:

1. Obtain a restricted, versioned source copy and confirmed IT term/offering scope. Preserve original rows and source hashes; assign review issue IDs privately without deriving permanent identities from row positions.
2. Name authorized qualification, eligibility, curriculum and taxonomy owners. Verify each mandate and delegation independently. Adviser review, administrator accounts, GEC capabilities and Chair publication authority do not automatically provide these powers.
3. Review unmatched labels, broad/narrow categories, identical sets and overlaps with course owners. Produce explicit proposed mappings with rationale; do not use fuzzy matching as an authorization decision. Preserve unresolved/contradictory states.
4. Approve stable domain IDs, definitions, granularity and any explicit alias/hierarchy links, effective term and revision. Confirm primary/secondary meaning and whether domains are alternatives or complementary requirements.
5. Verify claim-specific specialization evidence and explicit eligibility separately. Resolve contradictions by a new authorized decision, not union, last-row precedence or preference inference.
6. Record scoped approval/rejection, evidence provenance and immutable revision history. Revalidate affected dependent measurements/runs when a source changes, expires or is revoked. Preserve old schedules, checkpoints and reports under their original identities.
7. Only after approved data and scoring decisions exist, separately authorize provider/release implementation and qualification. No implementation step is undertaken now.

## Missing-data decision alternatives

Let E be eligible assigned offerings, C the complete assessable subset, U=E-C, and A the complete assignments with any positive verified overlap.

| Alternative | Benefit | Risk and required disclosure |
|---|---|---|
| A: exclude unknown from alignment denominator, report A/C | Describes only what can be assessed | Can inflate apparent performance and favor scheduling faculty with more documented data. Null when C=0. Mandatory companion coverage C/E and unknown U/E; not a whole-schedule success rate |
| B: report unknown separately, with conservative [A/E,(A+U)/E] | Separates uncertainty from known nonalignment without invented data | Bounds may be wide; not a point fitness. Null for E=0. Approved partial evidence could tighten bounds only under a separately versioned rule |
| C: verify before specialization-sensitive comparisons | Prevents unknown data from silently deciding who wins | Verification may delay comparison. Require the **complete shared admissible alternative set** to be assessable; do not silently drop unknown candidates or faculty |

These alternatives can be combined for reporting. Experimental recommendation, **unapproved**: A only with B's coverage/unknown disclosures, and C for scalar comparison readiness. Do not convert unknown to zero, assume a missing profile is explicitly empty, grant eligibility, exclude roster members or label a scheduling problem infeasible because specialization measurement is blocked.

Fictional example: E=2, C=1, A=1 gives A/C=100%, coverage 50%, unknown 50%, and overall binary alignment bounds [50%,100%]. With two verified nonaligned assignments, A/C=0 and unknown=0; these cases are different. E=0 produces null rates, not a fabricated perfect score. Tests exercise those distinctions and invalid count rejection.

## Adviser/department decision package

Every decision below is **PENDING; formal approval required**. Suggested owners are categories to confirm, not already established mandates. The passive JSON package links each question, field and metric to these IDs and prior F3A decisions; approval records are null.

| ID | Question / alternatives | Unapproved starting recommendation and implications |
|---|---|---|
| D01 | Accepted specialization evidence: credentials, verified experience, professional/research evidence, combinations | Department defines acceptable evidence, relevance and validity; no preference-only or assignment-only inference. Qualification policy owner and adviser must confirm |
| D02 | Who verifies: designated department reviewer or formally delegated institutional office? | Name the verifier and explicit mandate/scope; publication permission alone is insufficient. Institutional authority owner must establish the role |
| D03 | Who approves subject taxonomy: curriculum panel or delegated course owners? | Common controlled version, explicit definitions/equivalence, review of all mappings. Curriculum/taxonomy authority and adviser decide |
| D04 | Rubric and role: ANY, COVERAGE, weighted; reporting, tie-break, lexicographic or weighted optimization? | Coverage plus binary diagnostic as a reference only; neither production choice nor coefficients are selected. Adviser and scheduling-policy owner decide |
| D05 | Multiple specializations/domains: sufficiency, breadth or approved relevance weights? | No raw tag-count reward; decide alternative versus complementary meaning before computing an institutional score. Qualification/taxonomy owners and adviser decide |
| D06 | Unknowns: complete-only reporting, separate bounds, verification-first comparisons? | Disclose unknown and coverage; do not rank incomplete alternative sets or exclude people. Qualification owner and adviser approve convention/thresholds |
| D07 | Specialization versus subject/time preferences: report, hierarchy, weighted or Pareto treatment? | Keep separate metrics and hard constraints absolute; sensitivity does not authorize a priority. Adviser and scheduling-policy owner decide |
| D08 | Specialization versus workload: hierarchy, independent reporting or explicit scales? | Include every roster member and unavoidable underload; keep ceilings and eligibility hard. Workload-policy owner and adviser decide |
| D09 | Fixed or configurable weights? | Fictional weights only until approved; future changes require authorized versioned configuration frozen per run. Policy-change owner and adviser decide |
| D10 | Who approves changes, corrections and revocations? | Explicit scoped authority and immutable effective revisions; revalidate, never rewrite history or reuse old scores as a new policy. Institutional governance owner establishes mandate |
| D11 | Which term IT population, external scope and historical comparator? | Complete approved IT roster/offering set, confirmed dependencies, genuine historical schedule and manuscript/evaluation protocol. Roster/curriculum owners and adviser approve |

No production change may proceed by treating this developer-generated packet, a fictional `VERIFIED` marker, adviser data delivery or a SHA-256 as institutional approval. Actual decisions can be recorded later through a separately authorized and verified process; no approval workflow is implemented here.

## Proposed research evaluation methodology

This is a proposed DSRM evaluation plan for review, not a substitute for the actual manuscript. Separate artifact demonstration/constraint qualification from empirical effectiveness evaluation. Preregister the approved IT term/cohort, complete required components, external commitments, data states, hypotheses, success thresholds, weights/rubric, seeds, run limits, hardware/software and statistical comparisons before collecting confirmatory results.

| Metric ID | Definition, denominator and data requirements |
|---|---|
| ALIGNMENT_ANY | A/C among eligible complete-profile assignments; report C/E and U/E, where C=0 gives null. Requires independently verified term-specific faculty/domain profiles and permission data |
| DOMAIN_COVERAGE | Sum of exact relevant-domain overlap fractions / C; separate equal-domain versus approved weighted result. No absent subject denominator invented; report total-eligible bounds/data coverage |
| UNKNOWN_RATE | U/E, null for E=0. Faculty and subject missing-data causes reported separately; never collapsed into verified nonalignment |
| ALIGNMENT_BOUNDS | Conservative [A/E,(A+U)/E], null for E=0. This is binary uncertainty, not the coverage objective or an approved penalty |
| PREFERENCE_SATISFACTION | Separate subject/day/time match rates over assignments with applicable active nonempty submissions for each preference. Disclose applicability counts, rank/importance indicators separately and unsubmitted/disabled/known-empty states. Not a faculty satisfaction survey |
| WORKLOAD_FAIRNESS | Full active roster including zero assignments: actual teaching units, fixed individual targets, under/over distribution and zero count; proposed D=sum((a-t)^2/t) for positive t, with zero-at-zero allowed. Positive-at-zero needs valid separate exceptional authority and an approved scoring contract; no denominator-one fallback. Include verified external teaching credits only under a reconciled nonduplicative policy |
| CONFLICTS | Primary counts of unique unordered overlapping same-resource meeting pairs, separately faculty/room/section. If rates used, denominator is applicable same-resource pair opportunities under declared recurrence; zero opportunities yields null. Report invalid slots, unavailable rooms and other hard violations separately. Half-open adjacency permitted; every accepted schedule must have zero hard violations |
| UNASSIGNED | Missing required offering-components / frozen required component count; also incomplete-offering count / required offering count. Track duplicates/partial duration independently; no drop from denominator. Null for an empty required set; distinguish invalid inputs and bounded search exhaustion from mathematical infeasibility |
| GENERATION_TIME | Uninstrumented wall time per attempted seed, separate preprocessing/search/validation/persistence phases and cold/warm states. Report all attempts, success/failure counts, bounded exhaustion/timeouts, median, sample SD, min/max and sample size. Profiling/tracemalloc runs separate; do not substitute time caps for successful completion times |

Baseline comparisons, only after policy/data approval:

1. Use identical immutable inputs/constraints and a complete common comparison domain. Compare the existing supported engine/policy with a separately versioned specialization-aware release, using paired seeds and equal search budgets. Changing scoring legitimately changes search; do not claim identical RNG trajectories, reinterpret checkpoints or mix best scores from policies.
2. Cross-evaluate assignments under common reporting metrics independently of optimizer fitness. Eligibility and all original calendar/availability/workload gates are prerequisites, not tradeable metrics. Report Pareto tradeoffs, failure rates and unknown-data sensitivity, not just a selected winning fitness or seed. Choose repeat count and meaningful difference criteria before evaluation; no significance claims from these fictional tiny cases.
3. Obtain a genuinely approved historical IT schedule **privately**, with source owner, version, permission to use, exact term, roster, offerings, teaching credits, room/person/section identities, approved exception/constraint snapshots and revision history. Such an approved comparator is not established in this repository. A file called consolidated, tentative or saved is not approval.
4. Reconcile historical scope without modifying the original. Compare only the approved common term/cohort/offering scope; disclose changes in staffing, demand, eligibility, preferences and unavailable historical preference submissions. If comparability cannot be established, block that comparison rather than impute missing wishes, infer expertise from past teaching or present a biased improvement claim. Historical computation time may be unavailable and must remain so.
5. Independent authorized reviewers adjudicate discrepancies and historical exceptions; blind/same-rubric review where feasible. Use deidentified aggregates in thesis artifacts, protect restricted evidence and predefine retention/access. Keep real institutional authorization separate from fictional demonstration and developer approval.

No real-world improvement, adviser approval, actual user satisfaction, optimality or institution-wide conflict freedom is claimed. An IT-only study must include confirmed outside commitments affecting its resources; it does not require inventing an IS optimization population or generalizing IT results to all CCS.

## Validation, files and preservation

Fresh validation: **79 Python tests passed, zero failed/errors/skipped**, comprising **35 new F3C consistency cases and 44 preserved F3B pure rubric cases**. Tests cover all decision links/required fields, prohibited unapproved activation, exact unknown/empty denominators, unchanged eligibility separation, lexical versus semantic taxonomy differences, missing classifications, duplicates/conflicts and nonmutating aggregate privacy. The preserved F3B pure rubric suite is rerun separately from its historical full GA campaign. No new test attempt failed and no warning was reported. Exact command timestamps, source hashes and outcomes are retained in the manifest; they are not added to the old 354/42 counts.

All **16 new files** are this report and `docs/testing/faculty-specialization-f3c/`: **five Python, nine JSON, one JSONL and one Markdown**. The [manifest](testing/faculty-specialization-f3c/manifest.json) lists the exact inventory and **15 raw artifact hashes**, excluding itself. Supporting source is `readiness_contract.py`, `inspect_taxonomy.py`, `test_readiness.py`, `run_checks.py` and `audit_evidence.py`; remaining artifacts are passive packet, sanitized aggregate findings, command/outcome/progress and entry/preservation records. No production/previous source file is changed.

The final audit rechecks all **2,661** baseline paths, **23** academic paths, original V1/V2 fingerprints, previous release sources, checkpoints/schedules/migrations, all **1,261** historical artifact entries and Git HEAD/index/staged state. Both preexisting protected local modifications remain byte-identical, unparsed, unstaged and uncommitted. New evidence is inspected for private faculty labels, credential URLs, keys and complete/truncated tokens/receipts; no source rows or domain strings are exported. Git/new-file whitespace and all new artifact hashes are checked. Database connections/writes, dependency installation and Git mutations: zero.

No fresh GA engine performance/correctness campaign, browser/API acceptance, frontend build/lint or PostgreSQL test is applicable to this passive qualification. Existing F3B and D15 evidence remain preserved historical evidence; the retained D15 database is not accessed. No protected file is reset, normalized, overwritten or repaired.

Integrity-only replay from the repository root in PowerShell, using the existing environment:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/faculty-specialization-f3c/audit_evidence.py --verify
```

Fresh evidence commands, only when preparing a reviewed addendum; each creates a new timestamp directory and does not overwrite the sealed manifest:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/faculty-specialization-f3c/run_checks.py inspect
.\.venv\Scripts\python.exe -B docs/testing/faculty-specialization-f3c/run_checks.py packet
.\.venv\Scripts\python.exe -B docs/testing/faculty-specialization-f3c/run_checks.py tests
```

New observations require their own reviewed inventory/addendum; do not rewrite historical results or the preservation baseline. No credentials or database access are needed.

## Readiness decision and ordered blockers

1. **Institutional data and authority:** name IT roster/qualification/eligibility/curriculum owners and establish actual scoped mandates, the complete semester cohort and verified claims/mappings. Intended owner categories in D01-D03/D10-D11 are not appointments. Production F1 remains blocked.
2. **Academic and research decisions:** obtain D04-D09 decisions on taxonomy semantics, rubric, unknown handling and preference/workload priorities, then examine the adviser-approved manuscript and agree the evaluation protocol. All recommendations here remain unapproved.
3. **Shared-resource/workload scope:** resolve actual external/IS dependencies and external teaching-credit treatment without adding an unverified IS population. Reconcile workload and historical schedule inputs privately.
4. **Separately authorized implementation:** only then consider a trusted provider and explicitly versioned whole-run fitness dispatch, cache/best-ever/report/checkpoint provenance, lifecycle revalidation and original-hard-gate regression qualification. No existing authority/fingerprint checks may be bypassed.

**GO for formal review of this decision package. NO-GO for institutional profile/cohort activation, production specialization scoring, final weights or an institutional evaluation claim.** Stop at this qualification; no next implementation milestone has begun.
