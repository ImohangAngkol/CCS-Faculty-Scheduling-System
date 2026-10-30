# F1.5: IT prototype cohort and cross-department dependency qualification

2026-10-29, Asia/Manila. Source `main` at `1423812e13a5791a550c893ef6b17bfef4b4ebfb`. **Read-only qualification. IT is the currently available prototype/evaluation scope, as reported by the user. Full CCS coverage and institutional authorization are not established. Production F1 cohort integration remains BLOCKED.**

## Scope and conclusion

The user identifies two relevant CCS departments, IS and IT, and states that the adviser supplied IT data only. This sets the available prototype boundary. It does not independently attest that every supplied identity is current IT faculty, that the files form a complete semester roster, or that any tentative meeting is institutionally approved. No IS faculty records, roster or evaluated population were created or inferred.

The inspected data contains useful IT-oriented course/load material and tentative first-semester 2026–2027 workbooks. **It does not yet establish a complete, verified IT semester roster with coherent qualifications, eligibility and workload profiles.** Identity coverage is not roster completeness; specialization tags are not verified degree credentials; source/basis text is not authorization; tentative scheduling rows are not immutable constraints.

The prior [F1 report](faculty-cohort-f1-implementation.md), [policy qualification](faculty-policy-qualification.md) and [functional audit](thesis-functional-correctness-audit.md) remain unchanged. This clarification narrows the intended real-data prototype population; it does not retrospectively relabel prior generic fictional tests as an institutional IT evaluation. The formal manuscript remains unavailable and adviser-approved thesis alignment is UNVERIFIED.

## Read-only method and evidence

Created a standalone standard-library CSV and ZIP/XML inspector. It reads source rows only in memory, exports schema labels and aggregate counts, and never imports/runs the GA, queries a database, executes workbook formulas/macros/links, recalculates or exports a workbook. Sheet names, faculty names/IDs, personal qualifications, workload values, source rows, formulas and source notes are not archived. Protected `faculty_preferences.json` and local `ga_settings.json` were not parsed; all academic files were raw-hashed for preservation.

The [final aggregate summary](testing/faculty-cohort-f1-5/20261029T094455234089+0800/summary.json) and [command record](testing/faculty-cohort-f1-5/20261029T094455234089+0800/command.json) record actual findings, source scope, timestamps and extraction boundaries. Source counts are observations from the present files, not provider verification. Normalization is restricted to existing identity names/declared aliases and exact stable-code joins; no fuzzy identity creation occurs. Unmatched labels are not assumed to be additional people or IS faculty.

## 1. IT prototype coverage

| Source | Observed structure/coverage | Qualification |
|---|---|---|
| `faculty_identities.json` | 11 identities with stable UUID/code/name/display labels; no department or semester fields. | Existing identity mapping, not an independently attested active IT roster. |
| `Faculty Preferences V2.csv` | 131 rows, 11 distinct faculty labels, all matched to the 11 registry identities. | Active legacy membership input, preference-derived and termless. Agreement with registry does not prove roster completeness. |
| `Faculty.csv` | 12 distinct labels; 10 match registry identities, two labels remain unresolved; one registry identity is not represented. Columns are Faculty/Admin/Research/Extension with an export index, not degree, department, term or participation fields. | Candidate reference source requiring private reconciliation. Do not create two new identities or declare them IS faculty from unmatched labels. |
| `Faculty Admin, Research and Extension.csv` | Active workload input: nine distinct labels all match registry; two registry members have no row. Includes source Teaching Load reference. | Incomplete relative to registry, no semester/dept binding. Current loader's zero-release fallback is not verified zero workload. |
| `faculty_qualifications.csv` | 11 distinct registered faculty codes, no missing/duplicate codes, nonblank specialization tags. Three rows have review/provisional markers. No degree/credential, term or department columns. | Tag coverage exists; credential completeness, current academic eligibility authority and departmental attestation remain unverified. Missing credentials does not imply faculty lack degrees. |
| `faculty_subject_eligibility.csv` | 39 explicit `eligible` rows across all 11 registered codes, no duplicate faculty/course pairs or unknown codes. No term/dept or degree fields. | Existing hard permissions usable only under current source assumptions. Nonempty source/basis fields do not prove current institutional approval. |
| `first_sem_bsit_subjects.csv` | 19 distinct course descriptors. 18 have normal-faculty eligibility; the remaining course has external preassignment declarations. | No course key lacking both forms in this snapshot. This is course-key coverage, not proof of all section offerings, global feasibility or complete qualifications. Filename supplies season, not a verified academic-year/calendar contract. |
| `second_sem_bsit_subjects.csv` | 55 distinct course descriptors, 18 also appear in the first list; 20 have existing normal eligibility and 35 do not. | Do not expand the evaluated term/population to this list. It requires separate term/curriculum/eligibility qualification; overlap does not prove either season label is wrong. |
| `subject_domains.csv` | 56 domain descriptor rows; seasonal flags and mapping notes. Review/inference markers appear across the mappings. | Descriptive domains/season flags, not exact-term authority or automatic teaching permission. No new specialization scoring or data was introduced. |
| `faculty_load.csv` | 39 course/section/schedule/room/unit/student-count rows; **no faculty identity column**. 35 rows contain IT-style section markers; four have unresolved other formats. | Despite its filename, not a per-faculty roster or teaching-target source. Other formats are not automatically IS. Student-count cells are not promoted to verified enrollment. |
| `BSIT_Consolidated_Subject_Schedules.csv` | 32 active fixed-section rows with Section/Course Number/Schedule; section labels have no department namespace. | Existing section constraints only; no room/faculty identity columns or actual academic-year binding. |
| `BSIT_GEC.csv` and consolidated `_test.csv` | Each has 34 section/course/schedule rows with unscoped year-section labels. | Not the active consolidated input; names/counts do not establish approval, identity equivalence or safe activation. No source was substituted. |
| `preassigned_assignments.json` | Two declarations, one external instructor resource; course/section/instructor/room fields. No fixed day/start/end or department field. | Existing locked instructor/room declarations, not confirmed timed IS meetings. External instructor does not mean IS affiliation. |
| Older preference CSVs and saved/export/test CSVs | Alternate preference sources contain additional unresolved labels; e.g. 159-row and 499-row variants cover 13 and23 distinct labels respectively. Saved/export/test files are not active roster sources. | Do not union these into an IT/CCS roster or fabricate departmental assignments. Their presence does not establish institutional provenance. |

The machine-readable summary inventories all17 CSV schemas/counts and distinguishes the seven active legacy CSV imports from reference/export variants. It leaves all rows and mappings intact.

### Workload source reconciliation

Eight identities match across the active workload source and `Faculty.csv`. Six raw text vectors differ, but **only three pairs are fully comparable finite numeric vectors**: one differs numerically and two agree; five have unknown/nonnumeric values in the alternate source. There are no formatting-only differences in this particular comparison. Missing/NaN fields are not replaced by zero.

The initial aggregate extraction reported raw-text disagreement before numeric qualification. It is retained with its original hash; [analysis refinement](testing/faculty-cohort-f1-5/analysis-refinement.json) identifies the corrected interpretation and final source summary. **Six text differences must not be reported as six confirmed workload conflicts.** No source wins automatically because it has more rows, a newer-looking filename or adviser-supplied provenance. An authorized owner must privately reconcile the one comparable disagreement, five unknown pairs, missing identities and intended effective term. No values or affected identities are disclosed here.

Option B remains unchanged: verified fixed allowances reduce teaching target; those activities are not scheduled. This review neither approves a replacement workload policy nor resolves the separate fairness counterexample. Original settings/scoring/RNG are unchanged.

### Tentative workbook coverage

Both supplied tentative-load workbooks have29 worksheets. Their text contains first-semester and 2026–2027 labels and IT department phrasing. Those are meaningful provisional context; they do not bind every listed person/meeting to an official active roster or confirmed term dates. No degree-header marker was found by the bounded structural search; this is not proof that complete qualification evidence could not exist elsewhere.

The two files differ (including328 versus314 formula cells). Formula definitions were not executed and cached values were not treated as fresh approved calculations. Only five registry identities have exact alias matches in inspected cell values; this conservative matching is **not** a count of faculty represented, because name formats, templates, repeated sheets and embedded labels can differ. No private sheet-name-to-person mapping was exported. Signature/Chair/approval-role labels are form text, not verified signatures or authority.

Neither workbook is automatically selected as the current version. Confirm the official file/revision, roster table/form interpretation, effective dates, and whether entries are tentative, excluded or final. The current evidence does not establish a complete semester-specific faculty cohort even though a plausible first-semester planning document exists.

## 2. Cross-department dependencies

**Dependency indicators are present; the actual confirmed shared-resource constraint set remains unresolved.** Inspection found IT-style and IS-style student-section references, not an authoritative IS faculty roster:

| Indicator | Tentative workbook `(2)` | Other tentative workbook | Interpretation |
|---|---:|---:|---|
| Worksheets containing both section styles | 10 | 10 | May include summaries, duplicates and templates; not ten shared faculty. |
| Faculty-labeled worksheets containing both styles | 7 | 7 | Potential shared teaching/records; no unique-person or employer-department inference. |
| Rows with IT-style section markers | 575 | 567 | Cooccurrence observations, not unique meetings. |
| Rows with IS-style section markers | 188 | 176 | IS dependencies may be represented within IT-oriented planning data; not expanded evaluation population. |
| Current runtime room labels appearing on rows for both styles | 5 | 5 | Potential physical-room sharing requiring exact identity/time/term reconciliation. |
| Recognized course-code values appearing with both styles | 5 | 5 | Potential shared courses/cross-listing; code equality does not establish the same offering or department ownership. |

These counts are not deduplicated validated assignments, proven temporal conflicts, enrollment totals or confirmed external constraints. The bounded regexes recognize section-like labels and known course prefixes; they do not establish the meaning of every cell. A course title mentioning Information Systems or an `ISY` course prefix alone is **not** an IS faculty/department assignment. IT curriculum data itself contains such course labels.

For an IT-only scheduling evaluation, **confirmed IS commitments that occupy an IT participant's time, a shared physical room or an affected IT student section must be treated as external dependencies**, without optimizing an IS faculty population. To do that safely requires:

- Stable shared resource identities: one person/room across departments, exact affected section/offering mappings, not two departmental copies that can evade conflict checks.
- Applicable term/effective dates, complete day/start/end/timezone/recurrence and exceptions; validated half-open intervals and current authoritative revisions.
- A resource/meeting owner and genuine confirmation/provenance/revocation checks. Tentative workbooks and adviser data delivery alone do not satisfy D8/D9 trust.
- Reviewed duplicate/cross-listing semantics. Repeated summary/form rows cannot become duplicate constraints or extra Subject genes.
- Explicit completeness for shared-resource dependencies. An unknown room/instructor that is required for conflict prevention must not be silently discarded.

Current V2 snapshots already support section/faculty/room reservations and original admission checks for properly supplied trusted commitments. However, `Commitment` has no teaching-credit units: its external time reservations are not automatically accumulated as external teaching units in the workload scorer, which sums chromosome subject credits. The separate `ExternalInstructor` class is excluded from normal workload scoring. **Time blocking alone does not demonstrate correct all-department workload accounting for a shared IT faculty member.** Confirm how external teaching is counted toward targets and hard ceilings without misclassifying it as a non-teaching allowance or inventing IS genes. No policy/formula change is authorized or made here.

No actual IS meetings were generated, confirmed, loaded as constraints or activated. This qualification does not establish current conflicts or a complete conflict-free CCS timetable.

## 3. Full CCS deployment versus IT prototype

| Boundary | IT prototype/evaluation | Cross-department dependencies | Full CCS deployment |
|---|---|---|---|
| Population | Only the approved active IT cohort, once qualified. Available data is user-reported IT data; current11 identities are not a proven complete roster. | Shared IT participants/resources remain one identity. Confirm outside commitments without inventing IS staff. | Requires a separately supplied and verified IS roster/profile source and college-wide scope policy. |
| Inputs | Qualified IT offerings, optional applicable preferences, explicit eligibility, loads and calendars. | Verified IS/other-owner reservations affecting IT and explicit shared teaching-credit accounting. | Coherent department, term, course, section, person, room and authority contracts for every deployed unit. |
| Claims | IT internal hard validity and compatibility with the complete supplied confirmed external set, with explicit missing-source limitations. | Report unresolved dependency coverage; cannot claim campus/CCS conflict freedom from IT-only data. | Independent complete deployment/data/permission/operational acceptance, not extrapolation from IT tests. |
| Evaluation metrics | IT roster denominator; declared term, engine/input/constraint identities, all attempted runs, shortages and unknowns. | External facts excluded from optimized population but included where required for resources/workload accounting; avoid double counting. | New approved protocol/population. Do not silently merge departmental cohorts into earlier IT results. |

Extensibility does not require changing current code now. F1's fictional `Term.scope` and explicit UUID/code/profile bindings provide a testable seam, and the academic foundation has scope/term identities. They do not constitute a deployed multi-department provider. Future providers should distinguish IT and IS section identities while sharing physical room/person identities, bind revisions explicitly and enforce genuine department-scoped Chair/application capabilities.

Do not simply strip `IT`/`IS` from labels and map both to legacy `1A`. Legacy section and offering identifiers use prototype namespaces; blanket renaming or namespace changes would affect mappings, authority and checkpoints. Department/catalog ownership and cross-listed courses require an approved identity policy and versioned compatibility plan. No mapping, namespace, authority, checkpoint or production file was changed.

## Qualification decision and required next inputs

**F1.5 qualification is complete with documented blockers; production roster activation remains BLOCKED.** Adviser supply establishes user-reported data provenance and a prototype boundary, not institutional authority. The previously reported roster-first policy approval is not evidence that a particular file is the complete official term roster.

Before production F1 cutover or any expanded evaluation, obtain privately from the appropriate owners:

1. The exact IT roster/version and effective semester/year, stable ID/code reconciliation, completeness attestation, participating/excluded members and reasons. Resolve the reference-file label mismatches without inventing identities.
2. A single authoritative workload revision with missing/unknown allowances reconciled, current approved qualifications/eligibility provenance and term applicability. Confirm which of the tentative workbooks is current; retain alternative versions as history.
3. Verified room identity/type/availability, affected section mappings and any shared faculty/course facts. Resolve the potential IS dependencies into a confirmed, complete time/resource snapshot before claiming conflict prevention across that boundary.
4. An explicit policy for shared teaching credits, cohort targets and ceilings, plus preference term applicability/carry-forward. Preserve original Option B and fairness scoring unless separately authorized.
5. Trusted server-owned roster/profile and institutional confirmation providers, run/checkpoint provenance binding, and a separately approved IT evaluation protocol. An IS dataset is needed only for expansion to an IS/CCS scheduling population, not as permission to fabricate it now.

This is qualification and planning only. No F2, source cutover, production data cleanup, GA run, external activation or institutional publication has begun.

## Tests, files and preservation

Fresh **18 fictional aggregation/parser tests passed**, zero failed/skipped, covering exact alias joins without identity invention; section indicators versus course prefixes; unknown qualifications; numeric disagreement versus missing/format-only values; CSV/XLSX byte preservation; workbook cooccurrence without a roster claim; and archive-size fail-closed behavior. Test data has only generic fictional IT data/room labels and section-pattern controls, **no fabricated IS faculty**. Earlier15-case extraction tests and both read-only extraction attempts are retained; do not add repeated passes. The numeric refinement is documented rather than erasing the earlier text comparison.

Previous F1's141 backend and99 frontend results are historical and their bytes/hashes are preserved, not freshly rerun. Browser, frontend build/lint, GA/integration and PostgreSQL tests are **NOT RUN** because this task changes no production functionality. No PostgreSQL or other database connection occurred.

New files only:

- `docs/faculty-cohort-f1-5-it-qualification.md` — this report.
- `docs/testing/faculty-cohort-f1-5/inspect_sources.py` — aggregate-only read-only source analysis.
- `docs/testing/faculty-cohort-f1-5/test_source_qualification.py` — fictional controls.
- `docs/testing/faculty-cohort-f1-5/run_tests.py` — isolated test evidence runner.
- `docs/testing/faculty-cohort-f1-5/audit_evidence.py` — preservation/privacy/hash verification.
- JSON baseline, refinement note, all timestamped source summaries/commands, test commands and manifest under the same evidence root. The [manifest](testing/faculty-cohort-f1-5/manifest.json) lists every exact new path/hash.

Final inventory: **16 new files (four Python, one Markdown, eleven JSON); 15 artifact hashes verified**, excluding the manifest itself. Three read-only extraction records are retained: the initial text comparison, finite-numeric qualification, and final domain-provenance summary. Both test attempts remain, with the latest18-case selection superseding the earlier15-case selection. All403 prior artifact entries independently reverify; privacy findings: zero. The existing Git LF-to-CRLF advisory for protected preferences did not change raw bytes or stage any file.

All **1,790 pre-existing paths and all23 academic files** are checked byte-for-byte, including existing untracked studies, F1 tests/report/evidence, original GA/scoring/RNG/migrations, protected preferences/settings, saved schedules/checkpoints/history and Git index. No existing file was modified. New artifacts are scanned for encoded complete/truncated credentials/receipts, sensitive logs and private faculty labels; no source names/rows/sheet names or sensitive records are archived. Git whitespace and artifact hashes are checked without staging. No installation, database operation, commit or push occurred.

Reproduce from the repository root using the existing venv, without installing anything:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/faculty-cohort-f1-5/inspect_sources.py
.\.venv\Scripts\python.exe -B docs/testing/faculty-cohort-f1-5/run_tests.py
.\.venv\Scripts\python.exe -B docs/testing/faculty-cohort-f1-5/audit_evidence.py
```

Extraction/test reruns create new timestamped evidence directories and never alter source workbooks or data. The audit refreshes only this new milestone's manifest, stops on any preservation mismatch, and never resets or repairs existing files.
