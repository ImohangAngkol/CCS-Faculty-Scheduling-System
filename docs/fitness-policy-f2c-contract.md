# F2C: versioned fitness policy contract and readiness decision

2026-10-30, Asia/Manila. Inspected `main` at `1423812e13a5791a550c893ef6b17bfef4b4ebfb`. **Contract investigation completed; no experimental production scoring or authorization activated.** The design can preserve the existing integrity model by using explicit release identities, frozen scoring provenance and tagged comparisons. Those release/dispatch/codec changes have not been implemented or qualified as application integration.

**Recommendation: GO for review of the contract and narrowly scoped implementation planning; NO-GO for production F2 activation or claiming supported new-policy continuation.** Before controlled integration, settle workload weighting/overload composition and authorized-zero-target numeric treatment, and prove a versioned release/continuation implementation against the existing supported engines. Production roster and institutional authority remain BLOCKED. Formal adviser-approved thesis alignment remains UNVERIFIED; this report does not invent institutional approval from the developer's decisions.

## Scope and evidence

Read F2A/F2B, faculty policy/cohort qualification, D10 compatibility and implementation records, current fitness/frozen-input/observation code, V1/V2 orchestration, selection/swap/mutation, reconstruction, reporting, checkpoints and authority providers. The [call-path inventory](fitness-policy-f2c-call-paths.md) maps producers, comparisons, caches, reconstruction, storage, readers and standalone analysis utilities. Its [machine index](testing/fitness-policy-f2c/20261030T225816240468+0800-inventory/call-paths.json) records source locations/hashes in31 production Python files and154 scoring-related call expressions. This static index is not execution coverage.

Fresh validation: **80 contract cases plus30 unchanged D10 V2 cases =110 passed, zero failed/skipped**. The [initial73-case selection](testing/fitness-policy-f2c/20261030T225816239534+0800-contract/command.json) and [expanded80-case selection](testing/fitness-policy-f2c/20261030T230008542355+0800-contract/command.json) are both retained; they are not added together. The [V2 record](testing/fitness-policy-f2c/20261030T225823774914+0800-engine/command.json) contains30 passes and one `PytestAssertRewriteWarning` for already imported `anyio` during the schema-only test bootstrap. No warning was hidden or attributed to PostgreSQL.

The contract model imports no GA, authentication or database implementation. Its provider objects are explicitly fictional trusted test fixtures, with no signatures, credentials, session receipts or deployment hook. Two original selection files are loaded by path for score-order/copy tests; they load no academic files. The V2 regressions use the existing schema-only import bootstrap, synthetic scoring, guarded academic reads and owned temporary checkpoint stores. Fresh V2 checkpoint/resume tests are real Python engine/store tests with fictional authority, **not production institutional or PostgreSQL acceptance**. No new browser, frontend, API activation or V1 continuation execution was performed here.

The first new audit-tool invocation stopped on a `KeyError` from looking up an incorrectly named F2B evidence field. It found no protected-file/hash mismatch and wrote no manifest. Only the new F2C lookup was corrected to use the existing `current_V2_fingerprint` key; the [sanitized failed-audit record](testing/fitness-policy-f2c/audit-initial-error.json) is retained. This was an audit-harness error, not a failed application or pytest case. A pre-existing Git LF/CRLF warning named protected preferences; no normalization/write was performed, and raw bytes remain unchanged.

F2B's preserved historical evidence includes four V1 mirror tests: three actual checkpoint creation/continuation cases and strict validation, plus30 V2 default and42 frontend contracts. These are previous results, not additional fresh F2C passes. The six retained older checkpoints retain their already documented incompatibility; this report neither opens/reinterprets them as new-policy inputs nor repairs them.

## 1. Shared dispatch contract

The current code has a shared authoritative scorer, but no supported alternative workload dispatcher. Swap and mutation evaluate and compare internally; selection consumes score vectors; V1/V2 survivors and best-ever compare again. Reporting and saved-best storage also interpret scores. Replacing only a final total would mix objectives. Current observation hooks cannot select a policy. The older `Functions.py` preference-only function with the same name is a separate utility, not the main workload scorer.

Proposed new-release interface (specification, not installed):

```text
resolve(server_parameters, trusted_release_registry) -> FrozenEvaluationContext
evaluate(candidate, context, scope=complete_chromosome) -> TaggedScore + components
compare(left, right) -> exact ordering, or incompatible-context error
observe(candidate_revision, tagged_score) -> read-only run observation
```

Resolve a server-allowlisted descriptor before initialization. Freeze it, the existing settings/preferences, full explicit cohort, eligibility/profile/calendar versions, term, constraints and required exception pins once per run. Missing mode on a **new legacy request** continues to mean the established default; unknown/malformed/unsupported modes reject. Do not put a new key into the current settings model and hope it is retained. Do not add a global mode, environment switch, monkeypatch or untrusted callback.

Within a new release, keep a single facade at the authoritative scorer import boundary, used by initialization, original operator calls, survivor/best-ever logic, resume verification, analysis and result construction. The seven other component computations and hard gates remain unchanged. Implement a new workload component only behind the explicit descriptor. A context-local binding may transport the frozen descriptor; every evaluating worker/thread/child must explicitly inherit and verify it. An absent binding in a new-policy execution is an error, not legacy fallback. Separate runs cannot leak contexts into one another.

Each score binds:

| Identity | Meaning |
|---|---|
| `run_id`, evaluation scope | Whole-candidate ordering versus deliberately scoped faculty diagnostics. Never compare the two. |
| policy digest | Canonical complete descriptor: workload/preference versions, coefficients, aggregation, zero-target admission/math, overload composition and implementation identity. |
| engine fingerprint | Actual installed release/source/dependency identity, independently verified. A policy label is not a substitute. |
| input fingerprint and cohort digest | Frozen preferences/settings, exact participating faculty including zero assignments, targets/allowances, eligibility and academic metadata. No change to the unresolved F1 roster integration is made here. |
| constraint digest | Exact term/catalog/external-commitment snapshot and applicable calendars. |
| exception-set digest | Pinned approval IDs/revisions/context and issuer-policy identities. Empty set is explicit, not missing authority. |
| candidate content/revision digest | Assignment and relevant resource state excluding computed score to avoid circular hashing. Object identity alone is insufficient after mutation. |

Compare only scores with the same complete evaluation identity; different candidate digests are expected within a run. Cross-run numerical comparison for research is a separate explicit evaluation exercise under a common frozen context, not permission to merge optimization populations. Selection preflights entire vectors **before RNG draws**. Stable ties keep existing ordering/improvement rules. No epsilon tie rule, arbitrary tie-breaking, or additional random draw is authorized.

Cache keys include evaluation identity, candidate digest/revision and scope. A mutation, faculty profile, approval or input change invalidates them. A copied best-ever keeps an independent candidate graph and its matching tagged score; no mutable score alias may outlive candidate mutation. Numeric display conversions cannot enter selection, operator acceptance, survivor selection, best-ever or saved-best comparison. Histories store original exact observations; report readers do not silently recalculate them.

The executable [contract_model.py](testing/fitness-policy-f2c/contract_model.py) demonstrates comparison/serialization identities and an authority-admission specification only. It is **not an implemented application dispatcher**, cryptographic verifier, scheduling validator or checkpoint loader. Contract selector tests show compatible values can be ordered by the two original selection functions and mixed values reject. They do not establish that unchanged engines/operators accept a new policy end to end.

## 2. Versioning and checkpoint provenance

Keep preference policy1/2, workload policy, assignment authorization policy and numeric representation as independent version axes. Existing preference version2 must never be repurposed to mean a new workload formula. Bind the complete descriptor digest into a real new engine identity and format.

Recommended release boundary: **fixed, reviewed, side-by-side immutable engine releases**, with a server-owned allowlist mapping release IDs to installed verified bundles. Preserve the existing supported V1/V2 bundle, its exact source and original strict verification. A new bundle contains the new facade/codec and every transitive implementation it depends on; it must not accidentally import mutable modules from the old bundle through absolute names. Separate processes/import roots are preferable to global alias replacement. Source/dependency verification remains inside each release; dispatch is not permission to override fingerprints. Paths, Python modules or executable code supplied by a checkpoint are never loaded.

New checkpoints atomically bind:

1. Format/engine version and actual source/dependency fingerprint.
2. Complete frozen descriptor and its recomputed policy digest; input/cohort/template/constraint identities.
3. Term/context and immutable exception pins; independently revalidated issuer/capability/lifecycle findings, without storing bearer credentials or raw provider payloads.
4. Complete population, best-ever independent graph, matching exact tagged scores/component records, generation histories/diagnostics and original RNG state.
5. Canonical passive DTO encoding, resource limits and checksum over the entire envelope, with the existing atomic commit/pinning guarantees.

Before continuation: validate envelope, graph, engine/source/dependency identity, original input fingerprint, policy descriptor, score/context agreement, constraints and fresh authority; recompute required scores under exactly the recorded policy before admitting state. Preserve `GA_CHECKPOINT_INPUT_CHANGED` and equivalent V2 mismatch rejection. Missing/unknown/inconsistent fields reject; do not drop fields, reinterpret old totals, replace archived scores, spoof hashes or migrate checkpoint files. A checksum proves byte identity, not institutional authority.

| Record and destination | Decision |
|---|---|
| Supported legacy artifact, exact original release/input, original trust checks and applicable current authorization satisfied | Continue through that verified legacy implementation only. Known old format can be mapped read-only to its documented legacy scoring identity after all original checks. Missing policy in an arbitrary artifact is not proof of legacy compatibility. |
| Legacy artifact requested as new scoring mode | Reject continuation. An explicitly requested reconstructed seed may start a **new run** after full hard/authority validation and fresh scoring; retain source provenance and never call it resumed evolution. |
| Same new release/policy/context, fresh matching authorization | Eligible for continuation after full original/new checks. This is a required future integration test, not currently supported. |
| Changed coefficient, numeric/zero/overload strategy, cohort/profile, input, constraint, approval revision, unknown release or damaged checksum | Reject explicitly; no silent downgrade, migration or best-score reuse. |
| Six historical already-incompatible artifacts | Remain byte-identical and historically readable only where existing readers support that; no new compatibility claim. |

**Option A adds a compatibility constraint, not a loophole.** Existing legacy engines lack the new exception gate. Legacy historical reading is not retrospective approval. Safe legacy continuation cannot be promised for a context capable of assigning positive teaching to target-zero faculty without enforcing Option A. Initially restrict supported continuation to contexts proven not to need that new gate (for example, all teaching targets positive, with profiles and inputs unchanged), or explicitly reject unsupported continuation. Do not remove target-zero faculty from the cohort to obtain this condition. A changed/authorized exception context needs a new guarded release/run until a reviewed continuation mechanism exists. Never grandfather unauthorized assignment through an old checkpoint. Any additional legacy guard/dispatcher must itself be reviewed and fingerprinted; merely documenting a condition is not implementation.

## 3. Proposed schema and reporting changes

The [proposal JSON Schema](testing/fitness-policy-f2c/policy-contract.schema.json) is a passive descriptor draft with `additionalProperties:false` and status `PROPOSAL_NOT_ACTIVATABLE`. Unsettled fields explicitly allow `UNRESOLVED`; no descriptor from this schema can activate the application. Runtime canonical reduction, cross-field rules, source trust and cryptographic/provider checks exceed JSON Schema shape validation. Tests check its JSON shape and required safety invariants; a complete deployed validator has not been built.

| Boundary | Proposed versioned change |
|---|---|
| Request/parameters | Explicit optional allowlisted policy ID for a new release; server resolves the full descriptor. Reject unknown IDs/extra fields. Preserve current defaults. |
| Frozen input DTO | Add policy descriptor/digest, numeric/assignment versions, complete cohort/profile and exception-set bindings beside existing settings/preferences/input identity. Exact key/version validation must change in the new release only. |
| Checkpoint/graph | New format version with bounded passive exact-score DTO, not serialized `Fraction` instances or arbitrary object imports. No unbound optional sidecar. |
| Best-ever/saved-best | Candidate identity + evaluation identity + exact score/components + copied graph. New stores separated by release/policy/context; never run today's float-only saved-best comparison across policies. |
| Histories/metrics | Each point retains policy/context and exact score; average is explicitly defined over compatible scores. Immutable old points use old definitions. |
| API/TypeScript/report/export | Expose version, policy ID/digest, component definitions, exact numerator/denominator strings, separate display value and rounding metadata, comparison eligibility and authority state. Do not put large integers in JavaScript Number. Unknown historical policy returns a truthful unsupported interpretation. |
| Future durable exception authorization | Likely requires immutable grant/revision/event records, faculty/department/term/context scope, issuer mandate/policy provenance, units/offering limits, lifecycle/revocation and audit references. Reuse existing immutable-ledger **patterns**, not their unrelated capabilities. No current D9-D13 schema should be silently repurposed. Review a separately scoped persistence/API design and migration before implementation. |

No database schema, table, migration, API, DTO or production source was changed in F2C. Proposed shape changes are not already supported fields.

## 4. Numeric representation

For positive targets, the proposed workload quantity is `D = sum((A_i - T_i)^2 / T_i)`. Option B retains `T_i=max(0,24-admin_i-research_i-extension_i)` with recognized fixed hypothetical allowances; non-teaching work is not scheduled. Individual teaching limits/warnings remain40/30. Include every member of the frozen cohort, including unassigned faculty. Eligibility, complete assignment, calendars and external constraints remain mandatory gates, not terms that a favorable D can offset.

The original counterexample has targets24/24: D(`[2,2]`)=`121/3`; D(`[4,0]`)=`122/3`. The original500/475 result is preserved and documented by F2A/F2B; F2C's new arithmetic tests verify the exact proposed values, not a changed production ranking. The balanced advantage is only `lambda/3` in a weighted scalar aggregate. Coefficient calibration, existing overload-band composition and tradeoffs with the other seven components remain decisions before activation. No hidden zero-assignment bonus, hard target minimum, coefficient or eligibility relaxation was added.

| Representation | Reproducibility/serialization/ranking | Recommendation |
|---|---|---|
| Exact rational | Reduced signed numerator and positive denominator as canonical decimal **integer strings**. Bounded JSON size/4096-bit integers, duplicate/extra keys and malformed/unreduced ratios reject. | Reference and authoritative new-mode ordering. Exact comparisons preserve mathematical ties; display decimals are separate. |
| Exact integer numerator on common denominator | For validated integer T1..24, `L=lcm(1..24)=5354228880`; workload numerator is `sum((A-T)^2*(L//T))`. Zero/zero contributes0 separately. | Optional exact fast path under this explicit domain. Convert to reduced rational at DTO boundaries. Never truncate fractional credits/allowances into this domain or assume Python constructor annotations enforce it. Other numeric domains require a reviewed version/algorithm. |
| Finite canonical decimal | Finite decimals cannot exactly represent1/3. A canonical representation is reproducible but finite precision can collapse distinct totals. Decimal context, rounding and quantization would be policy. | Display only, unless a future approved domain has a proof of exact finite representation. Do not rank rounded values. |
| Binary64 with exact oracle | Convenient in current APIs but errors/ties depend on aggregation. Arbitrary tolerance changes ranking. | Display/diagnostics; or a later certified error-bound comparison with exact fallback when bounds overlap. Never use `abs(diff)<epsilon` to turn an uncertain difference into a tie. No such fast comparator was implemented. |

The other seven components currently produce existing finite numeric values. A proposed exact aggregation can preserve each **computed binary64 component value** using `as_integer_ratio`, then add exact weighted D/explicit overload contribution. It must not claim to reconstruct an ideal mathematical preference score or to reproduce legacy float summation near ties. Changing total aggregation is itself a new numeric policy and needs differential tests/approval. Legacy calculations remain untouched. Reject nonfinite inputs/results and oversized exact aggregates; never silently clamp, round, omit a faculty row or fall back to old scoring.

### Measured arithmetic study

[numeric.json](testing/fitness-policy-f2c/20261030T225816239413+0800-numeric/numeric.json): Python3.14.2, fictional vectors only, local seed4827. Three cohort sizes, seven batches of1000 calls each after100 warm-up calls per method. Independent samples are batching repetitions in one process, not seven fresh GA runs. Medians below are microseconds/call; parentheses show sample SD, and ranges retain observed min/max.

| Faculty count | Fraction oracle including domain checks | Exact integer, prevalidated | Binary64 fsum, prevalidated | Decimal28 local context, prevalidated |
|---|---|---|---|---|
| 2 | 3.093 (0.079), 3.016-3.252 | 0.820 (0.020), 0.784-0.845 | 0.628 (0.016), 0.612-0.656 | 4.332 (0.240), 3.912-4.580 |
| 12 | 16.519 (1.253), 16.088-19.697 | 2.650 (0.204), 2.415-2.931 | 1.722 (0.080), 1.609-1.867 | 14.769 (1.080), 14.292-17.400 |
| 24 | 35.151 (3.193), 32.774-41.669 | 4.345 (0.209), 4.210-4.691 | 2.993 (0.699), 2.767-4.764 | 28.841 (1.803), 26.649-32.094 |

All3000 sampled pair orderings agreed between exact and binary64; maximum sampled absolute float error was approximately`4.363e-13`. All sampled integer-fast-path values equaled the Fraction oracle exactly. These samples do **not** prove universal float ordering. Constructed aggregate totals `2^53+1/3` versus `2^53+2/3` become an equal binary64 value; Decimal28 around`10^30` also collapses distinct additions. Those constructed aggregates are not claimed to be observed production workload totals. Production configuration does not establish a full aggregate error bound that would make arbitrary epsilon comparisons safe.

Timings include different validation/conversion work as labeled; they do not establish an end-to-end GA speedup, new-mode runtime, calibration quality or memory benefit. No profiling cumulative totals, native compiler, dependency installation, allocator change or performance integration was involved.

## 5. Developer-approved zero-target Option A

The update settles **admission policy**, not authority provenance or the undefined division in D. T0/A0 is allowed and contributes0. T0/Apositive without a valid explicit exception is rejected. A grant cannot change T0, fabricate eligibility, override calendars/conflicts/room requirements or exceed the applicable hard maximum40. No general target-zero exclusion or omission from workload coverage is proposed.

Inspection found **no appropriate existing dedicated authorization workflow**. Administrator login is insufficient. Chair request-decision authority, controlled schedule-application authority, GEC confirmation and publication are distinct capabilities; none automatically conveys workload-exception authority. Their production providers remain unconfigured. The developer decision is not an institutional mandate or real approval record.

Required future contract:

- Independently authenticated server-owned provider, with a separately established capability such as `zero_target_workload_exception.authorize`; institution must identify who may exercise it and in which departments/terms. Do not accept client `approved:true`, a session preview receipt, role name or a hash alone.
- Immutable grant ID, revision/event chain, authenticated issuer and issuer-policy version; exact faculty/department/year/term, run/scheduling context, original target/profile/allowances, eligibility/input/constraint bindings, approved offering scope and bounded teaching-unit ceiling. No identifying names required in public benchmark/audit examples.
- Timezone-aware issuance/expiry; current approval state and mandate, revocation and context checks. Freshness limits/provider error behavior must be reviewed; fail closed on unavailable/unverifiable authority. Approval cannot be inferred from an earlier public VERIFIED snapshot.
- Pin the grant revision/context in frozen inputs and cache identity. Revalidate at admission/evaluation batches, selection boundaries, checkpoint/continuation and every saved-best/result/history/application publication boundary. A changed/revoked/expired grant or changed inputs invalidates old scores/context; do not silently refresh to a different revision or retain mixed-authority scores. Attestation refresh of the **same** pinned immutable grant is separate from changing the scoring identity.
- Audit each exceptional assignment with original target0, actual units, scoped grant/revision and validation result, while protecting private issuer/provider material. Publication remains subject to its separate existing authority and complete hard validation.

Approved admission alone does not define `A^2/0`. Compare these remaining choices explicitly:

| Authorized positive assignment numeric treatment | Consequence | Status |
|---|---|---|
| Legacy overload bands only; D contribution0 for this case | Avoids division, keeps an auditable overload cost; may favor approved zero-target recipients relative to others under some weights. | Candidate; requires explicit scoring-policy decision and calibration. |
| Separate approved positive reference scale q, e.g. `A^2/q`, plus explicitly chosen overload composition | Preserves original target0 but adds a new exceptional deviation scale; q changes rankings. | Candidate; q and composition require approval. **No automatic denominator1.** |
| Hard block all positive assignment even with a valid grant | Easy numerically but fails the selected exceptional-assignment policy as a general solution. | Not recommended as policy. Temporary unsupported-mode rejection is truthful until math is defined. |

The executable model permits a fictional valid grant at the **admission** boundary, retains target0, and then explicitly rejects experimental scoring for positive target-zero workload as `AUTHORIZED_ZERO_TARGET_NUMERIC_POLICY_UNRESOLVED`. This distinguishes a valid exception from a ready scoring implementation. Approved, unapproved, absent-provider, expired/future/revoked/wrong-capability, jurisdiction, changed faculty/term/profile/input/constraints, grant revision and hard-constraint failure cases are tested. Hard findings are supplied to the model by a fictional fixture; it does not replace the real scheduler's validators or prove authentic provider signatures.

## 6. Acceptance and implementation gates

| Required area | Fresh F2C evidence | Required before integration |
|---|---|---|
| Legacy backward compatibility |30 original V2 engine cases; actual source bridge accepts reviewed bytes and rejects hypothetical in-memory edits. V1 mirror evidence reviewed, not rerun. | Re-run all supported V1/V2 continuation cases against packaged old/new releases and matching runtime/dependencies. Preserve six historical artifacts unchanged. |
| Experimental isolation | Test-only module, no application imports/hooks; baseline source hashes preserved. | Explicit opt-in only; absent/unknown policy tests at every route/worker; concurrent context isolation and default byte/behavior parity. |
| Mixed-policy rejection | Tagged comparisons reject changes in8 evaluation identity fields; selectors reject incompatible values. | Validate entire vectors/caches/stores **before** RNG or writes; all operator, survivor and saved-best paths. |
| Compatible continuation | Exact-score DTO round trips;30 default engine cases cover real current V2 checkpoint/resume. | New-format actual checkpoints, fresh processes, RNG-equivalent split/uninterrupted runs under each policy and live authority. |
| Incompatible continuation | Contract rejects changed contexts; original V2 corruption/source/input tests passed. | Tampered descriptor/score/history/approval, unsupported versions, legacy-to-new mode, missing provenance/sidecar and size-bound tests with original error semantics. |
| Deterministic serialization | Canonical round trips, malformed/duplicate/oversized rejection, descriptor hash sensitivity;3000 numeric samples. | Full passive graph codec/API/TypeScript/export round trips, exact totals/components, cross-platform supported runtime and fractional-domain decisions. |
| Best-ever preservation | Contract strict improvement/stable ties/RNG-free comparisons; default V2 best-ever/continuation tests. | Actual new-mode best-ever graph isolation, persisted identity/history and all publication paths. |
| Operator consistency | Static original swap/mutation import/call counts, original selector experiments, default V2 operators. | Run all internal swap/mutation evaluations with the same new context; parent/child malformed, infeasible, rejections and failure recovery. No post-hoc score replacement. |
| Zero target | Fictional grants, invalidation, authority separation, unchanged target, unresolved math fail-closed. | Authentic institution-defined provider, durable audit/pinning, transaction/revocation races, approved exceptional math and complete hard validation. |
| Existing publication protection | Four production authority factories statically asserted to returnNone; default V2 trust/rejection regressions. | New policy must never enable D8/D9/Chair/application/publication authority or bypass unavailable providers. Test revalidation failures before every persistent write. |

Additional calibration gates: equal/unequal targets, scarcity/surplus, no/limited eligible offerings, zero-assignment faculty, nonzero competing preferences, authorized exceptions, full-course coverage and unchanged hard rules. Freeze full population/cohort; F1 roster incompleteness cannot be hidden by excluding non-submitters. Specify coefficient/overload strategy and quantify workload/preference tradeoffs before recommending production fitness. Within-policy deterministic continuation is required; different policies legitimately change accepted candidates and subsequent RNG paths. Do not promise identical cross-policy schedules.

Required implementation sequence, **not performed here**:

1. Approve numeric total aggregation, weight/calibration plan, overload composition, authorized-zero-target math and institutional exception mandate/provider requirements.
2. Package and verify immutable existing/new engine release boundaries and registry; prove supported legacy continuation before changing any source covered by its fingerprints. Reject unsupported contexts explicitly.
3. Implement the new pure policy facade and frozen descriptor in the new release, shared by existing internal operator calls and all ordering paths. Keep original operator mechanics/math outside the specifically approved workload component unchanged.
4. Implement new passive score/checkpoint/history/API codecs, context-aware stores/cache and truthful old/new reporting; hard/authority gates must run before writes. Existing stored artifacts remain untouched.
5. Complete isolated fictional whole-run differential, calibration, recovery, security and regression evidence. Only then consider a separately approved production integration. No database provider or genuine institutional deployment is implied.

## Preservation, exact files and reproduction

Existing files modified by F2C: **none**. The initial protected local modifications to `backend/data/faculty_preferences.json` and `backend/data/ga_settings.json` remain byte-identical and unstaged; neither was parsed or printed for this milestone. All23 academic files, original GA/scoring/operator/RNG code, existing migrations, retained checkpoints/schedules and earlier evidence are included in the1870-path pre-F2C binary baseline. The [manifest](testing/fitness-policy-f2c/manifest.json) records the complete new-file inventory, raw hashes, historical manifest checks, privacy and whitespace findings; it excludes its own hash.

New authored files:

- This report and `docs/fitness-policy-f2c-call-paths.md`.
- `docs/testing/fitness-policy-f2c/contract_model.py`, `test_contract.py`, `policy-contract.schema.json`.
- `numeric_study.py`, `inventory_calls.py`, `run_checks.py`, `audit_evidence.py` in that same directory.
- `preservation-baseline.json`, timestamped command/outcome/numeric/index/engine-identity JSON and `manifest.json`; exact paths are in the manifest.

From the repository root, Windows11 PowerShell:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2c/run_checks.py contract
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2c/run_checks.py engine
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2c/run_checks.py numeric
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2c/run_checks.py inventory
.\.venv\Scripts\python.exe -B docs/testing/fitness-policy-f2c/audit_evidence.py --verify
```

Runners create new timestamped directories and retain earlier evidence. `--verify` checks the archived manifest without rewriting it; new rerun artifacts require a separate reviewed manifest update and are not silently added. Test environments exclude database URLs/credentials/approval variables; pure contract and numeric work uses no application/DB connection. Git checks are non-mutating and use optional index locks disabled. No production authority, GA run under new scoring, PostgreSQL operation, dependency installation, checkpoint rewrite, staging, commit or push occurred. No next milestone or performance integration was begun.
