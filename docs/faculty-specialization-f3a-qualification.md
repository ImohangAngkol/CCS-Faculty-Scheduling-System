# F3A: faculty specialization alignment policy and data qualification

2026-11-01, Asia/Manila. Local `main`, HEAD `7793da585c855572c72fe4baee9f04d50f1e8ac6`. **Qualification complete with explicit institutional blockers. No specialization scoring, production cohort cutover, new authority or institutional record is implemented.** IT is the user-reported available prototype scope; complete IT semester coverage and full CCS/IS coverage are not established. Formal adviser-approved thesis alignment remains **UNVERIFIED** because the manuscript is outside this repository.

**GO for a separately authorized F3B fictional rubric/metric qualification. NO-GO for institutional profile activation, new production fitness or a claim of improved real scheduling alignment.** The missing inputs are a verified semester IT roster, approved specialization/subject taxonomy and evidence, named qualification authority, and an approved treatment of unknowns and competing soft objectives. A production scoring weight has not been selected.

## Objectives, inspection and preservation boundary

F3A separates mandatory subject eligibility, verified specialization alignment, optional subject preferences and missing information. It proposes metrics and a semester profile contract, exercises fictional tradeoffs and preserves the existing GA and research releases. It does not repair institutional data, implement a provider, run an optimization-quality campaign or change academic policy.

Read the [functional audit](thesis-functional-correctness-audit.md), [42-row working-objective matrix](thesis-objective-traceability.md), [F1](faculty-cohort-f1-implementation.md), [F1.5](faculty-cohort-f1-5-it-qualification.md), [policy qualification](faculty-policy-qualification.md), [decision matrix](faculty-policy-decision-matrix.md), F2C/D/E contracts and relevant F2I results/source. These are working project requirements and prior evidence, not institutional approval. F1 roster activation remains blocked. The older policy matrix is historical; subsequent developer-approved workload decisions are not used to invent specialization approval.

F2I's 226 artifact hashes and its preservation audit passed before any F3A files were created. The new [baseline](testing/faculty-specialization-f3a/preservation-baseline.json) and [entry record](testing/faculty-specialization-f3a/entry-verification.json) protect **2,587 pre-existing paths**, all 23 academic paths, prior untracked owner studies, original sources, retained checkpoints/schedules and the Git index. No AGENTS.md was found. Both pre-existing protected data modifications remain private and byte-hashed; `faculty_preferences.json` and `ga_settings.json` are not parsed or printed.

The inspector uses bounded standard-library CSV parsing and private exact code/name joins. It exports schemas and aggregate counts, not faculty names/codes/UUIDs, per-person tags, rows, preference values, source notes or qualification documents. Unknown/private headers are withheld. It neither imports the GA nor reads/recalculates workbook cells. The two workbooks are covered by unchanged raw hashes and reviewed prior F1.5 aggregate evidence, clearly distinguished from fresh inspection. No database or network operation occurs.

## Current implementation and source flow

| Existing path | Observed behavior | Qualification |
|---|---|---|
| `backend/genetic_algorithm/utils/Functions.py:238-248` | Reads semicolon-separated `specializations` by faculty code; a later duplicate key overwrites an earlier value. | Descriptive tags. The `auto_qualify_by_specialization` column is not consumed. No credential verifier or lifecycle is installed. Duplicate/conflict rejection below is a future contract, not existing loader behavior. |
| `Functions.py:250-263` | Only rows whose normalized status is `eligible` enter the explicit faculty/course set. | Current operational hard-permission source. An additional conflicting non-eligible row would not remove the eligible set entry; the inspected data has no such duplicate/conflict. Do not implement a changed permission policy silently. |
| `Functions.py:266-278,493-510`; `models/Subject.py:34-47` | Loads primary/secondary domain strings into Subject metadata. | No approved taxonomy version, relevance weights, formal equivalence/hierarchy or verified subject-domain mapping contract. |
| `Functions.py:395-453`; `models/Faculty.py:107-125` | Constructs normal faculty from legacy preference-derived keys and attaches tag/eligibility lists. Empty eligibility denies all; missing tags become an empty list. | F1 roster limitation remains. The existing empty specialization list cannot distinguish unknown from an explicitly attested empty profile. |
| `Functions.py:1359-1378` | `faculty_is_explicitly_eligible_for_subject` checks explicit course membership only. Matching tags/preferences do not grant permission; mismatching tags do not revoke it. | Implemented and freshly verified; no strict-specialization hard constraint exists to relax. |
| `Functions.py:get_ranked_faculty_candidates` | Workload fulfillment, deficit, load, subject-preference and seniority rules rank eligible candidates. | No specialization optimization criterion. |
| `operators/FitnessFunction.py:984,1065` | Main scorer has eight existing components: subject/time/day preferences, schedule style, lecture/lab preference, preparation count, teaching-load balance and daily teaching load. | No specialization term. New actual tests and the preserved audit verify that changed descriptive tags alone do not change the original score. The separate similarly named utility in Functions is not a specialization dispatcher. |
| `services/metadata_service.py:37-53,132-157`; `schemas/faculty.py`; `schemas/subject.py`; `frontend/src/api/faculty.ts` | Read-only DTOs project specialization strings, domains and eligibility records. | Data display is not verification. These DTOs lack a complete term-qualified specialization/evidence/approval state. No frontend editing/verification flow was added or browser-tested. |
| `services/ga_v2_engine.py:29-44`; `services/ga_checkpoint_service.py:246` | Original hard profile comparisons cover eligibility/workload fields. Specialization is not an independent hard-profile comparison field. | Appropriate descriptive behavior today, not permission to add a new scored input without binding it. Raw data/input hashes, generic model graphs and the experimental bridge's full graph digests already protect other contexts; F3A does not claim tags are universally unfingerprinted. |

Production V1/V2 keep their original scorer/operator imports. Existing F2 exact-workload experiments are separately verified releases, not activated production policies. F3A's model lives only under `docs/testing/`, imports no GA/authentication/database implementation, returns reporting DTOs and has no registration, callback or fitness adapter.

## Existing data qualification: what is and is not established

The [final read-only inspection](testing/faculty-specialization-f3a/20261101T141403903239+0800-inspect/command.json) inventories all 17 CSVs with safe headers and counts. All 23 academic file bytes still match the earlier F1.5 baseline. Counts describe this snapshot; they do not establish institutional truth.

| Source and actual structure | Fresh finding | Classification and purpose |
|---|---|---|
| `faculty_identities.json` | 11 existing stable identity/code records; no verified term participation or department roster attestation. | Operational identity registry; not a complete approved IT semester cohort. Never infer additional IS participants. |
| `faculty_qualifications.csv`: `faculty_code,faculty_name,specializations,auto_qualify_by_specialization,source,notes` | 11 distinct registered codes; no missing/duplicate codes or conflicting duplicate tag sets. All 11 private exact name/code joins agree. No blank tag rows. All 11 auto-qualification flags are false. | Descriptive/incompletely qualified profile material. No structured degree/evidence/approval/term/department/taxonomy-version fields establish verified expertise. Missing credential fields do not mean faculty lack degrees. **Zero verified complete institutional specialization profiles are established by this evidence.** |
| Same qualification provenance | Three rows contain the narrow F1.5 review/unverified/provisional markers; 11 contain the broader F3A review/tentative/inference/auto markers. Ten reference teaching/load material; two match inference/derivation keywords. | These are overlapping textual indicators, not counts of verified deficiencies or proven derivation histories. The 3-versus-11 difference is a definition change, not changed data or an erased F1.5 finding. |
| `faculty_subject_eligibility.csv`: `faculty_code,faculty_name,course_no,eligibility_status,eligibility_basis,source,notes` | 39 `eligible` rows across 11 identities; all private name/code joins agree; no duplicate pairs or contradictory statuses. All source/basis fields are nonempty. 35 rows reference teaching/load material, four preferences. | Mandatory in current software, but current-semester institutional permission is unverified. A basis referring to a preference or past teaching is not independently sufficient qualification evidence. This review does not revoke or alter any current entry. |
| `subject_domains.csv`: `course_no,course_title,primary_domain,secondary_domains,offered_first_sem,offered_second_sem,domain_mapping_status,notes` | 56 unique course keys, no duplicate/conflicting domain rows or blank primary tags; 49 have multiple declared relevant domains. All 56 have review/inference markers. | Descriptive/derived mapping material; no approved controlled taxonomy/rubric/version is established. Seasonal booleans do not attest an academic year or current offering. |
| Cross-file tag vocabulary | 20 faculty tag strings versus 76 subject-domain strings; two faculty strings occur in no subject mapping; 58 subject strings occur in no faculty profile. 15 declared eligible faculty/course pairs have no exact string intersection. | Unresolved terminology/granularity/completeness, not 15 ineligible assignments or proof of missing expertise. No synonym, fuzzy match, hierarchy or credential is inferred. Explicit eligibility and descriptive alignment legitimately differ. |
| `first_sem_bsit_subjects.csv`, `second_sem_bsit_subjects.csv` | 19/55 distinct course keys; all have domain rows. 18/20 have normal explicit eligibility. | Curriculum descriptors, not complete term/section offerings or feasibility proof. The remaining first-list course has the previously documented preassignment path. The 35 second-list keys without normal eligibility require separate qualification; do not expand the evaluated term. |
| `Faculty Preferences V2.csv`: `Faculty,Subject,New Schedule,Schedule,Room Assignment,Day(s)` | Active legacy input, 131 rows, no explicit term/department columns. Older CSV variants remain reference material. | Wishes/form-derived content, not expertise. The repository alone does not attest authorship of each CSV submission. Current authenticated preference submission is an existing application workflow; the protected current JSON is deliberately not inspected. |
| `Faculty.csv`; active `Faculty Admin, Research and Extension.csv` | Prior F1.5 found 12 reference labels versus 11 registry identities, unresolved labels, incomplete release rows and a privately unresolved comparable allowance disagreement. | User-supplied/reference workload material, not a verified qualification source. Raw bytes are unchanged; previous aggregate findings are reviewed history, not newly reconciled facts. Option B remains unchanged. |
| `faculty_load.csv`: an export column plus `course_no,section,schedule,room,units,number_of_students` | 39 rows; no faculty identity field. | Scheduling/load export despite its filename; cannot supply a per-faculty roster, specialization or target. No student count is promoted to verified enrollment. |
| Consolidated schedule CSV, `BSIT_GEC.csv`, consolidated test CSV and saved/export CSVs | Existing section/course/schedule or derived scheduling material. | No automatic teaching qualification, current approval or authoritative specialization from a past assignment. GEC/testing/export files are not substituted into active inputs. |
| `preassigned_assignments.json` | Two preassignment declarations; no specialization evidence or fixed meeting-time authority arises from them. | Existing instructor/room declarations, not credential attestations. External instructor is not automatically IS affiliation or part of the IT optimization cohort. |
| Two tentative workbooks | Prior F1.5 structural evidence identifies tentative first-semester/year context and potential shared person/room/subject dependencies; no fresh cell/credential parsing here. | Tentative, not verified approvals. Shared-resource constraints need current exact identities/term/time/provenance. Do not fabricate IS profiles or claim complete CCS evaluation. |

**Authority summary:** current operational inputs exist; no reviewed source establishes the complete institutionally approved semester IT specialization dataset. Preference-like data is not credential evidence; tags, teaching-history references and inferred mappings are not approvals. Which external source is authoritative must be named and verified by IT administration. Adviser delivery of a dataset establishes user-reported provenance, not institutional authorization.

No currently inspected duplicate qualification/domain keys, contradictory eligibility statuses or known code/name conflicts were found. This does not resolve the taxonomy gaps, incomplete source scope or conflicting hypothetical qualification evidence. Fictional negative tests cover those cases without adding real records.

## Proposed alignment model: reporting only

The [pure model](testing/faculty-specialization-f3a/alignment_model.py) and [fictional examples](testing/faculty-specialization-f3a/20261101T140859482184+0800-examples/command.json) demonstrate a **recommended but unapproved** rubric, not a production metric or credential verifier. All input IDs require `FICT-` identifiers and the `FICTIONAL_TEST_ONLY` marker; neither marker nor `VERIFIED_COMPLETE` fixture status is institutional authority.

1. Freeze a declared IT/term cohort and offering scope. Exact identity/term/department/taxonomy mismatches, duplicates and unknown identities reject. Missing specialization is distinct from missing identity or permission. No names or row positions create stable IDs.
2. Evaluate mandatory eligibility independently. A missing allow decision or an eligibility conflict is reported as a hard eligibility violation, irrespective of expertise, preferences or workload. The model does not replace original time/room/section/duration/ceiling gates.
3. Keep specialization and subject-mapping states distinct: `VERIFIED_COMPLETE`, `VERIFIED_PARTIAL`, `UNKNOWN`, `UNVERIFIED`, `CONTRADICTORY`, `EXPIRED`, `REVOKED`. Verified fixture facts require explicit fictional evidence references. Actual verification/lifecycle providers are a future institutional contract.
4. For an eligible assignment with complete valid faculty and nonempty complete subject-domain data, define `coverage = |faculty_domains intersect subject_domains| / |subject_domains|`. No domain grants eligibility. Coverage one is full match; a positive fraction below one is partial; zero is **verified no overlap**, not professional disqualification.
5. Otherwise alignment is unknown, not zero/mismatch. Valid partial evidence can carry a separate positive-overlap flag, but complete-profile coverage is not fabricated. Even a full positive overlap in an incomplete profile remains explicitly partial-data evidence under this conservative rubric. Whether that evidence should count in a broader binary alignment numerator is F3A-P06, not silently decided for production.
6. An explicitly attested complete empty faculty specialization set can be assessed as no overlap; a missing legacy empty list cannot. Empty/unknown subject domains have no justified denominator and remain unknown. Expired/revoked/contradictory claims cannot supply verified overlap.
7. Subject preferences remain independent active, absent, disabled or known-empty wishes. The experimental match metric uses active nonempty wishes only. It is not the application's ranked preference indicator, importance weighting or survey satisfaction measure.

Binary overlap is a useful additional reporting candidate but can overstate broad multi-domain fit. Equal-domain fractional coverage makes partial overlap visible, but may penalize over-broad subject tagging and assumes equal relevance. Primary/secondary weighting, hierarchy and equivalence, a tie-breaker and weighted aggregation are **unapproved alternatives**. No production coefficients, fallback expertise or default penalty for missing data is chosen. Initially report metrics jointly; do not feed unknown-as-zero values back into the optimizer.

## Candidate metrics and exact denominators

Freeze `N` as the complete scoped proposed offering-assignment count, not number of faculty or class half-hours. Fixed external/GEC assignments and out-of-scope departments need a declared separate population; they are not silently added to an IT-only score. The caller must independently validate the complete required offering set and all original hard constraints. The pure model diagnoses eligibility only and is not schedule validation.

Let `E` be explicitly eligible assignments, `C` the eligible assignments with complete assessable specialization/domain data, `U=E-C`, `A` members of C with any overlap, `F` members with full overlap, and `r_i` their exact coverage fractions. Let `K` count unknown-data assignments whose valid partial evidence has an observed overlap; K remains separately visible and is not mislabeled mismatch.

| Candidate metric | Numerator / denominator | Unknown/empty behavior |
|---|---|---|
| Eligible assignment rate | E / N; additionally N-E hard eligibility violations | Unknown/conflicting permission does not authorize. Any violation invalidates scheduling acceptance; favorable soft metrics cannot hide it. |
| Complete-data specialization-aligned assignments | A / C; full F / C; partial (A-F) / C; verified non-overlap (C-A) / C | Report C/E beside it. A/C alone can misleadingly show 100% for a partly unknown schedule. K is a separate positive-partial-data observation. |
| Unknown specialization/alignment assignments | U / E with reason counts by faculty/subject state | Never label U as mismatch, ineligibility or zero expertise. Missing subject domains also produce U. |
| Specialization assessability coverage | C / E | Data availability, not teaching performance. Zero denominator is not applicable, never fabricated 100%. |
| Conservative observed alignment bounds | A/E through (A+U)/E | Bounds, not an estimated unknown score. They deliberately do not exploit all partial positive evidence and are not sharp probability intervals. |
| Mean multi-domain coverage | sum(r_i)/C | Exact reporting value; broader eligible-population conservative bounds are sum(r_i)/E through (sum(r_i)+U)/E. Unknowns are not assigned a production value. |
| Subject preference satisfaction | Matching assignments / eligible assignments whose faculty has an active, nonempty applicable subject-wish list | Missing, disabled and known-empty lists are separately non-applicable; do not invent satisfaction. No wishes become credentials. Importance/rank-sensitive alternatives require a separate rubric. |
| Assignment distribution by subject domain | Each eligible assignment with K_s known subject domains contributes 1/K_s offering and units/K_s credits to each domain | Avoids double counting multi-domain offerings/credits. Unknown subject-domain assignments/credits stay in a separate bucket. This is reporting attribution, not fractional changes to actual teaching units. |
| Domain-specific aligned/unknown exposure | Fractional domain contribution when matched under complete valid data; separate unknown-alignment contribution | Domain totals do not prove formal qualifications, demand adequacy or complete faculty coverage. |

All exact fractions use integer numerator/denominator strings in JSON; no floating approximation enters ranking. There is **no specialization ranking implementation** here. Report context hashes bind term, cohort order, domain facts/status/revisions/evidence references, taxonomy, eligibility, preferences and assignments. A hash detects content identity, not authority. Partial-positive flags, bounds and coverage remain mandatory context, not hidden missing-data decisions.

Two additional source-qualification metrics should be considered for F3B, rather than overloading the word coverage: complete verified faculty profiles / the entire scoped roster (including zero-assignment faculty), and known subject-domain requirements with at least one explicitly eligible verified specialist / all known subject-domain requirements. Report missing-domain requirements separately. These are proposed cohort/opportunity metrics, not implemented output fields or measured institutional results here; the assignment-level prototype cannot prove roster completeness, staffing sufficiency or calendar feasibility.

## Worked fictional tradeoffs and original hard-gate evidence

The [examples](testing/faculty-specialization-f3a/20261101T140859482184+0800-examples/command.json) use three explicit fictional faculty and two fictional subject types. No IT person is simulated from an institutional profile. A subject with domains {A,B} can be taught by two explicitly eligible faculty: one has verified complete {A,B}, the other {B}. Their coverage is 1 versus 1/2. The first does not prefer that subject; the second does. Neither dominates all relevant soft objectives; no combined scalar ranking is chosen.

| Control | Measured/model result | Decision boundary |
|---|---|---|
| Equal teaching targets [6,6], four units assigned to one of two faculty | Exact target-weighted deviation D is 20/3 for either [4,0] or [0,4]. Alignment and subject wishes can disagree while workload ties. | Does not automatically prioritize alignment over wishes. |
| Unequal targets [6,12] under fixed hypothetical non-teaching allowances [18,12] | D([4,0])=38/3, D([0,4])=34/3. The lower-coverage, stronger-preference faculty can have the better workload outcome. | Individual targets matter. These are analytical values of the existing experimental formula, not newly activated fitness totals or scheduled non-teaching activities. |
| One complete aligned assignment and one unknown-profile assignment | A/C=1, C/E=1/2, U/E=1/2, conservative alignment bounds [1/2,1]. | Never report entire-schedule 100% alignment from the known subset alone. |
| Multiple faculty and subject domains | Fractional subject-domain distribution conserves two offerings and six teaching units in the example. | Primary/secondary weighting and taxonomic relationships remain undecided. |
| Partial positive evidence, missing domains, contradictory/revoked/expired claims | Unknown coverage with explicit reasons; positive current partial overlap separately flagged; no verified mismatch invented. | Contradictory specialization does not itself rewrite an independently established eligibility decision. An eligibility conflict is a separate fail-closed condition. |
| Subject wishes or matching tags without explicit eligibility | Original membership predicate rejects; pure model reports ineligible and does not assess a favorable alignment. | No tag/preference-based permission grant. |
| Perfect alignment with faculty/room/section overlap | All three independent original reconstruction controls reject with the intended resource-conflict type. | Hard validity always precedes soft optimization. |
| Invalid 30-minute boundary or reversed interval | Original admission rejects both fixtures. | No rounding or schedule repair to manufacture an aligned result. |
| Desired late time conflicts with fixed commitment | Original early schedule is hard-valid with a measured time-preference penalty of 30; the preferred late candidate rejects through the original fixed-constraint gate. | An imperfect preference outcome can be feasible; preference/alignment cannot override unavailability. |

The [12 original-behavior observations](testing/faculty-specialization-f3a/20261101T140846779889+0800-original/original-observations.jsonl) record actual original admission/scoring/reconstruction findings, including separate zero faculty/room/section conflicts for valid witnesses. The pure model itself does not render or validate timetables. No GA-quality improvement, convergence, performance gain or optimal real assignment is claimed.

## Proposed authoritative semester IT profile source

The [passive profile contract proposal](testing/faculty-specialization-f3a/proposed-profile-contract.json) is a design checklist, **not an installed JSON/API/database schema or authority provider**. It requires stable UUID/code binding, exact department/term membership and exclusions, complete explicit eligibility decisions, multi-domain specialization facts and completeness states, qualification evidence/digests, verifier/issuer capability, taxonomy and mapping revisions, effective/expiry/revocation state, source hashes/version, approval status and immutable corrections. Preferences remain a separately authenticated submission and revision.

Who may verify a degree, approved teaching experience or specialization must be established independently. Administrator login, a Chair publication/adjustment mandate, a prior GEC verification or adviser dataset delivery is not automatically specialization/eligibility authority. Do not turn a user-provided `verified:true`, a tag or a file hash into a grant. Validate genuine authority and evidence through a server-owned source before any institutional activation.

Missing identity, profile applicability or mandatory eligibility cannot be invented. Unknown specialization stays unknown without deleting a faculty member from the roster. Explicitly attested no-specialization is distinct from absent/blank data. Duplicate/conflicting authoritative records require quarantine/private reconciliation, not automatic union or last-row precedence. Confirmed eligibility changes need their own authorized decision. An approved correction creates a new immutable revision and invalidates affected dependent contexts; it does not rewrite prior checkpoint/history bytes.

Cross-department work is a dependency boundary: one shared person/room must retain one stable identity, and confirmed outside commitments affecting IT must be complete and current. No IS faculty roster, qualification or optimization population is inferred. Specialization measurement does not resolve F1.5's external teaching-credit accounting or general availability lifecycle gaps.

## Fitness and checkpoint compatibility plan: not implemented

F2C's single-policy-per-run, tagged comparison, cache isolation and frozen provenance contracts still apply. A future specialization objective needs an explicit allowlisted specialization policy/version, taxonomy/rubric/digests, independent eligibility and verified profile/evidence revisions, missing-data rule and approved composition/weights. Freeze them in the same complete evaluation identity through initialization, original operator-internal scoring, selection, replacement, best-ever, caches, reports, publication and continuation. A client reporting DTO is not a fitness value; tests reject it through the existing tagged-score preflight.

Raw CSV changes may already affect input hashes, and the experimental bridge binds full model/frozen graphs. That is not a substitute for a new auditable definition of verified expertise or for scored-claim lifecycle checks. Existing descriptive metadata comparisons cannot silently become new-policy acceptance rules. Revalidate source/evidence at appropriate boundaries; reject changed/revoked/incompatible inputs rather than mix old/new scores.

Keep current V1/V2/default and F2 experimental releases unchanged. New scoring integration requires separately qualified source/release/format identities; do not add a total after operators have optimized another policy, replace a global scorer, spoof fingerprints, reuse old best scores or reinterpret archived checkpoints. Legacy historical reads retain their actual old policy. No new table or migration is justified by this reporting qualification; durable implementation choices belong to a separately approved milestone.

## Adviser and IT administration decision packet

The [nine-question packet](testing/faculty-specialization-f3a/decision-packet.json) contains recommendations and null approval records. None is marked institutionally/adviser-approved by F3A.

| ID | Question requiring confirmation | Recommended starting point and classification |
|---|---|---|
| F3A-P01 | What evidence qualifies as verified specialization? | Department defines accepted credential/experience evidence and current relevance. **Requires institutional confirmation.** |
| F3A-P02 | Who verifies, approves and may delegate? | Establish explicit qualification/eligibility capability and term/department scope; do not borrow publication authority. **Requires institutional confirmation.** |
| F3A-P03 | How do domains match subjects? | Approve taxonomy IDs, granularity, multi-domain relevance, aliases/hierarchy and primary/secondary rules. **Requires institutional and adviser confirmation.** |
| F3A-P04 | Should alignment be descriptive, a tie-breaker or weighted objective? | Report first; qualify a new version only after selecting the objective. **Recommended but unapproved; requires adviser/institutional confirmation and implementation.** |
| F3A-P05 | How should alignment compete with preferences and fairness? | Review Pareto/lexicographic/weighted alternatives on the supplied tradeoffs; no hard constraint can be softened. **Requires adviser/institutional confirmation and additional testing.** |
| F3A-P06 | How should incomplete, missing or partial positive evidence be handled? | Unknown is not mismatch; require coverage/bounds, and decide readiness thresholds and whether verified partial positives count. Do not exclude faculty or silently award a free optimization score. **Recommended but unapproved; requires adviser/institutional confirmation.** |
| F3A-P07 | Can past teaching contribute? | Only reviewed identity/term/source-bound evidence under approved criteria; never automatic qualification from a stored assignment/preference. **Requires institutional confirmation.** |
| F3A-P08 | Who corrects inaccurate records and how are affected schedules handled? | Authorized supersession/revocation, immutable reason/history and revalidation; preserve old artifacts. **Requires institutional confirmation, implementation and tests.** |
| F3A-P09 | Which cohort, offering/external scope and metric denominators are approved? | Confirm a complete semester IT population and evaluation protocol before research claims. **Requires institutional and adviser confirmation.** |

Already verified: current explicit eligibility is separate, original specialization scoring is absent, the detached fictional measurement works within its stated rubric, and the original hard gates remain enforced. This is not approval of that rubric for production. Planned DSRM evaluation must distinguish data qualification, artifact demonstration and measured scheduling effectiveness. Formal thesis-method/objective alignment remains unverified; do not relabel these working requirements as approved manuscript objectives.

## Fresh tests, retained attempts and non-applicable checks

| Fresh final selection | Result | Evidence |
|---|---|---|
| Pure model/inspection plus unchanged F2C/F2D contracts | **226 passed**, zero failed/errors/skipped: 48 new cases plus 178 preserved contract cases | [command and outcomes](testing/faculty-specialization-f3a/20261101T141402109720+0800-pure/command.json) |
| Original-GA/reporting-admission plus unchanged audit/D10 engine | **75 passed**, zero failed/errors/skipped: 12 new cases plus 33 audit and 30 V2 cases | [command](testing/faculty-specialization-f3a/20261101T140846779889+0800-original/command.json) |
| Actual current V1 source-identical mirror | **4 passed**, three owned fictional checkpoint archives, 202 byte-identical source paths | [command](testing/faculty-specialization-f3a/20261101T140915812918+0800-v1-mirror/command.json) |
| **Unique final Python cases** | **305 passed, 0 failed, 0 errors, 0 skipped** | Do not add intermediate 224/225-case passes again. |

Pure tests include exact fractions, explicit eligibility, multiple domains, missing/partial/expired/revoked/contradictory facts, unknown denominators, known-empty versus absent preferences, context/identity mismatches, synthetic source duplication/code-name conflicts, privacy, immutability/RNG, reporting-versus-fitness incompatibility and the non-activating policy proposal. Original regressions include real V2 construction/operators/checkpoint continuation, hard workload/eligibility constraints, independent best-ever and RNG behavior. The V1 mirror creates/loads/continues actual original checkpoints; no fingerprint function or old archive is replaced.

The first inspection failed closed during preservation hashing: CPython's Windows open audit event represented both `Path.read_bytes` and text reads as mode `r` with identical flags. An owned fictional calibration demonstrated the distinction could not be made there. The new inspector now gets an explicit digest-only callback; GA tests retain the existing mode-aware data guard. No protected JSON/settings text was parsed and no data was written. The [failed record](testing/faculty-specialization-f3a/20261101T135652302236+0800-inspect/command.json) and [guard diagnosis](testing/faculty-specialization-f3a/guard-diagnosis.json) remain intact. No application defect was corrected or test disabled. Earlier successful inspections remain, with later aggregate refinements clearly superseding them.

Runtime/command/cwd/source hashes, offset timestamps, elapsed times, exit codes and warnings are retained per record. The 75-case worker recorded one `PytestAssertRewriteWarning` for already-imported anyio; no additional warning attribution is inferred. No dependency upgrade is performed. No timing value here is a benchmark or optimization result.

Frontend contracts/build/lint, browser screenshots, live HTTP/API acceptance and PostgreSQL: **NOT RUN / not applicable to a documentation-only detached model with no deployed UI/API/schema change**. No screenshot is fabricated. F1/F1.5 and F2I prior results are reviewed historical evidence, not added as new F3A tests. D15 evidence and the retained database are untouched and not re-queried.

## Files and reproducibility

All **35 new files** are this report and `docs/testing/faculty-specialization-f3a/`: **nine Python, 20 JSON, five JSONL and one Markdown**. No existing file is modified. The [manifest](testing/faculty-specialization-f3a/manifest.json) lists every exact path and **34 raw artifact hashes**, excluding its own hash. New reusable files:

- `alignment_model.py`: pure fictional reporting oracle; no scorer or authority hook.
- `examples.py`: worked fictional multi-domain/preference/workload tradeoffs.
- `inspect_data.py`: bounded aggregate-only private source inspection.
- `test_alignment.py`, `test_inspection.py`, `test_original.py`: new fictional tests and actual original hard-gate controls.
- `run_checks.py`: bounded guarded workers and sanitized evidence records.
- `verify_v1.py`: owned source-identical V1 mirror entry, copied without modifying the old helper.
- `audit_evidence.py`: preservation/privacy/source/history/hash/inventory replay.
- `proposed-profile-contract.json`, `decision-packet.json`: passive non-activating contract and nine pending decisions.
- Baseline/entry/diagnosis, timestamped command/outcome/progress/observation files and the manifest: evidence, not institutional records.

From the repository root in Windows PowerShell, use the existing environment and install nothing. Integrity-only replay runs no GA or database operations:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/faculty-specialization-f3a/audit_evidence.py --verify
```

For a separately reviewed fresh evidence run (creates new timestamped records; do not overwrite the existing manifest):

```powershell
foreach ($F3aSelection in @('inspect', 'examples', 'pure', 'original')) {
    .\.venv\Scripts\python.exe -B docs/testing/faculty-specialization-f3a/run_checks.py $F3aSelection
    if ($LASTEXITCODE -ne 0) { throw 'Stop: review the saved F3A record.' }
}
.\.venv\Scripts\python.exe -B docs/testing/faculty-specialization-f3a/verify_v1.py
```

No raw pytest/import against institutional inputs is necessary. Every new worker strips credential/database variables, denies database/network operations, and confines repository writes to the new evidence scope. Original academic binary fingerprint reads remain genuine; protected content is never parsed for tests. New evidence needs its own reviewed manifest/addendum, not an automatic rewrite of this completed record.

## Preservation and F3B gate

The replayable audit verifies all **2,587 baseline paths**, all **23 academic files**, **1,189 historical artifact entries**, original V1/V2 fingerprints, and all existing experimental release source bindings. Raw hashes preserve existing owner changes, not merely committed versions. Original GA/operators/scoring/RNG/workload settings, source fingerprints, migrations, 17 retained run-checkpoint files, saved schedules/history and old research artifacts are unchanged. Both protected local data modifications remain byte-identical, unstaged and uncommitted. The historical checkpoint incompatibility/rejection policy is unchanged; no archive is rewritten or reinterpreted.

Privacy verification scans new source/log/JSON/Markdown for private registry labels, complete/truncated encoded receipts, credential URLs, keys, bearer/session artifacts and sensitive log patterns. No real faculty profile, preference, qualification note, cookie, credential or signed receipt is copied. Schemas/counts and fictional observations are the only data exports. Hashes prove artifact identity, not institutional authority. Git whitespace checks are non-mutating; any existing protected-preference LF/CRLF advisory is not a normalization operation. HEAD/index/staged state remain at entry.

F3B may investigate only separately authorized fictional rubric alternatives, unknown-data bias, primary/secondary semantics and preference/workload Pareto comparisons, with the same original hard gates and exact reporting. **Do not activate the F1 provider, install qualification authority, assign production weights or integrate a specialization score until the nine policy/data decisions and explicit new-release compatibility are settled.** No database operation, schema change, dependency installation, staging, commit, push or automatic next milestone occurred.
