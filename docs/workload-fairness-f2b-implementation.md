# F2B: controlled fairness integration — compatibility and activation stop

2026-10-30, Asia/Manila. Inspected `main` at `1423812e13a5791a550c893ef6b17bfef4b4ebfb`. **NO-GO for application integration in the inspected architecture. F2B is not implemented or complete.** No application file, scorer, mode, setting, policy bridge, schema, API or checkpoint format was changed. The existing default and its current supported continuation baseline remain intact.

## Why integration stopped

F2B Phase3 explicitly says to stop if the architecture cannot safely support the opt-in mode without broader changes. The inspection and new isolated tests establish a need for a reviewed **versioned workload dispatch, continuation and reporting contract**, rather than a new setting alone. This is a stop at the current integration boundary, not proof that a safe extension is impossible or that protected operator math must change.

The developer-approved target-weighted formula, preservation of OptionB and overload/hard limits are accepted as the current user-reported policy direction. No additional adviser documentation is claimed. IT remains the prototype scope; F1/F1.5 institutional roster/providers and genuine activation remain BLOCKED. The [F2A prototype/report](workload-fairness-f2a-prototype.md) remains preserved historical evidence, not a newly integrated scorer.

### Verified blockers

| Boundary | Actual current behavior | Why a setting-only/post-hoc integration is unsafe |
|---|---|---|
| Mode configuration | `GASetting.from_dict` does not retain a workload-mode key; constrained `Parameters` forbids that extra field. A direct frozen-context experiment with an unrecognized mode key still returns500/475. | An apparent opt-in could silently leave old scoring active. Missing or arbitrary keys are not a supported new mode. No new selector was installed. |
| Shared scoring | Crossover and mutation import/call the same current `faculty_preference_fitness` used by orchestration. Their internal accept/reject comparisons use that objective. `ga_v2_engine.run` has no supported fitness callback. | Replacing only final totals or engine-level ranking leaves mixed objectives inside operators, best-ever or publication. Observation hooks record results; they do not dispatch scoring. |
| Existing V1 provenance | The engine fingerprint hashes GA source bytes, including the scorer. The preference-policy compatibility helper validates exact installed source hashes before reconstructing reviewed legacy source. | A hypothetical changed scorer byte string is rejected by the actual bridge in memory. Editing the scorer requires an explicit verified-source compatibility extension or versioned continuation path; simply keeping files on disk does not preserve resumability. |
| Existing V2 provenance | The V2 fingerprint includes the V1 engine identity plus V2 services; read/validation reject mismatches. Frozen-context fields and current profile/input identities are revalidated. | A source edit changes default checkpoint identity too. An experimental label alone does not distinguish weight, numeric policy, zero-target handling or stored fitness semantics. Old scores must not be silently reused. |
| Reporting/API | Current context records preference policy1/2, not workload policy. Reporting's workload definition is the rounded-band equation; it interprets recorded context/engine identities. | Reporting old bands for a new score would be false. New mode provenance and historical-reader semantics need review; preference version is not a workload version. |
| Numeric/storage | F2A's exact `Fraction` values are rejected by the real checkpoint graph encoder and report finite-number validator. | No implicit lossy float conversion or passive-type allowlist widening was attempted. A production numeric contract must pass oracle/ranking/serialization tests and be bound to provenance. |

Sources inspected: `genetic_algorithm/operators/FitnessFunction.py`, `operators/Swap.py`, `operators/mutation.py`, `utils/FrozenInputs.py`, `utils/FitnessObservation.py`, `models/Faculty.py`, `models/ga_setting.py`; services `ga_service`, `ga_v2_engine`, `ga_v2_service`, `ga_checkpoint_service`, `ga_v2_store`, `preference_scoring_policy`, `fitness_reporting_service`; constrained DTOs, current compatibility manifest, F2A/policy evidence and current V1/V2 tests. No AGENTS.md was found.

The compatibility proof changes **only an in-memory byte string**, never an installed source or checkpoint. It calls the actual `legacy_source` validator and observes its exact-release rejection. Fingerprint functions, signatures, validation and stored artifacts were not bypassed, spoofed, normalized or rewritten. Current-release V1 and V2 actual continuation are freshly tested below.

## Current baseline and mathematical specification

The inspected source defaults, used explicitly in fictional fixtures, are underload25, overload10, heavy-overload25, three-unit overload bands; subject70, time10, day5, preparation10, gap10, lecture/lab5 and daily-load10; preparation threshold3, daily teaching threshold360 minutes and step60. The normal Faculty model gives target `max(0,24-admin-research-extension)`, warning30 and hard teaching ceiling40. These are **source/default fixture values**, not a dump or assertion about the user's modified protected settings. No protected settings or preferences were parsed or changed.

The current workload equation remains:

```
A < T: 25 * ceil(10*(T-A)/T)
A >= T: 10 * ceil(max(0,min(A,max(T,30))-T)/3)
      + 25 * ceil(max(0,A-max(T,30))/3)
```

The new default-mode characterization reproduces500 for `[2,2]` and475 for `[4,0]`, targets24 each. Adding an unrecognized workload key in the isolated context does not change the result. This demonstrates a missing activation seam, not a successful experimental mode. All temporary context state is restored. Current unrelated fitness terms and operators remain unchanged.

**Proposed mathematical policy, not installed:** for positive targets, `D=sum((A_i-T_i)^2/T_i)`. Target0/actual0 contributes0. Positive actual at target0 has no denominator in this formula; no arbitrary1-unit replacement is approved here. A mode must explicitly define that case or reject unsupported activation before candidate evaluation; legacy runs must retain their existing behavior.

Preserving original overload rules while using full D raises the explicit question `W=lambda*D+O_legacy`: above-target assignments then contribute both continuous deviation and the original overload bands. This is observable double contribution, not automatically an implementation defect or an approved new penalty. Removing O would change existing overload scoring; using only underload D would differ from the approved full-deviation proposal and lose excess-distribution pressure. A reviewed specification must say which contribution/ordering is intended. No new default coefficient was selected.

### Calibration analysis boundary

Fresh [exact algebra](testing/workload-fairness-f2b/calibration-algebra.json) evaluates42 coefficient/component combinations. It is **not** a new GA or nonzero-preference schedule calibration campaign. At the equal-target counterexample, balanced D=`121/3`, concentrated D=`122/3`, and both legacy overload contributions are0. If the balanced candidate hypothetically incurs an additional existing component penalty p, its total advantage is governed by `p-lambda/3`: it wins only when `lambda>3p`.

| Existing component difference, one unit/step | Hypothetical p under source defaults, importance/priority1 where applicable | Coefficient threshold for balanced to win |
|---|---:|---:|
| Subject mismatch | 70 | `lambda>210` |
| Time mismatch | 10 | `lambda>30` |
| Day mismatch | 5 | `lambda>15` |
| Preparation beyond threshold | 10 | `lambda>30` |
| Daily-load step | 10 | `lambda>30` |
| Gap/style step | 10 | `lambda>30` |
| Lecture/lab mismatch | 5 | `lambda>15` |

This is counterfactual arithmetic: it does not claim that the lecture-only control can incur a lecture/lab mismatch or that all components have these values in every schedule. Importance, rank fractions, priority, counts and pattern differences change p. The illustrative F2A scaling250/24 gives only3.472222 balanced advantage here; even a5-point contrary preference difference outweighs it. It is not selected as a default. Real calibration must include valid nonzero-preference schedules for each component, eligibility-limited scarcity and surplus, lab patterns, warnings, complete GA evolution and pinned modes. Those trials are **BLOCKED/NOT RUN for F2B** because coherent opt-in dispatch is not implemented. F2A's prior numerical/ranking and timing results remain historical.

## Zero-target findings

Fresh original-scorer checks verify target0/actual0 workload0 and targets`[0,0]`/actual`[2,2]` workload20: each positive assignment is an original overload band, not ordinary fulfillment. Current hard teaching ceiling remains40; target0 is not currently an automatic hard exclusion. Source/report inspection shows target0 fulfillment is undefined and positive deviation is classed as overload. No new assignment permission or prohibition was invented.

For the proposed D mode, confirm whether positive teaching at target0 should use only the existing overload treatment, another explicitly approved deviation convention, or an explicit unsupported-mode block. Preserving overload permission does not define an undefined division. The unapproved F2A denominator1 must not silently become production policy. Since no new mode is installed, there is no route by which it can activate for this unsupported case; default legacy behavior remains as before.

## Fresh validation and checkpoint compatibility

The [initial backend record](testing/workload-fairness-f2b/20261030T134723083374+0800-backend/command.json) passed39 tests (nine new boundary cases and30 current D10 engine cases). A final additional numeric-storage boundary case was added and rerun: the [final backend record](testing/workload-fairness-f2b/20261030T135345404946+0800-backend/command.json) passed40. Counts are not added across repeated selections.

The D10 cases exercise actual default multi-generation GA operators, eligibility, complete hard-valid coverage, fixed section/faculty/room constraints, same seed/RNG continuation, best-ever graph preservation, current V2 checkpoint creation/read/resume, fresh-process continuation and strict corruption/source/input rejection. These are **default-mode regressions, not experimental-mode tests**. They use fictional unit authority, schema-only import bootstrap and owned temporary stores; no institutional provider or database is involved.

Fresh [V1 mirror record](testing/workload-fairness-f2b/20261030T134900506824+0800-v1-mirror/command.json): four original tests passed, including three actual checkpoint creation/continuation cases paused at generations0/1/2 and strict loader checks. The existing Phase6 worker ran unchanged against a byte-identical owned source mirror with generated empty schemas/default fictional JSON. Its actual engine fingerprint equals the original current-release engine; real fictional input fingerprints/archives are verified. No fingerprint replacement or existing checkpoint input was used. All retained historical checkpoints remain byte-identical with their documented historical limitations.

Fresh [frontend record](testing/workload-fairness-f2b/20261030T134901860331+0800-frontend/command.json):42 Node reporting/preferences/faculty-display/constrained-GA contracts passed. This is not browser or new-mode API evidence. No new API field or UI was added.

Final counts are **44 backend cases** (10 boundary,30 D10 default,4 V1 mirror) and **42 frontend contracts**, zero failed/skipped. One AnyIO assertion-rewrite warning appears in backend bootstrap; V1 mirror reports its exact output separately. No failure was hidden or dependency installed. Earlier39-pass evidence is retained as a superseded narrower selection. No failed F2B test attempt is claimed or deleted; F2A's earlier failed evidence remains preserved.

| Requested F2B area | Status |
|---|---|
| Formula direction and OptionB | Developer-approved direction, per user. Exact-arithmetic oracle remains F2A historical implementation; no new application dispatcher. |
| Default legacy behavior | IMPLEMENTED BEFORE F2B / freshly verified unchanged. |
| Experimental shared opt-in | **BLOCKED / NOT IMPLEMENTED**. No missing-config activation or runtime replacement introduced. |
| Fraction/ranking/zero handling in integrated mode | **BLOCKED / NOT RUN**. Boundary rejection and original zero-target behavior characterized only. |
| Current supported V1/V2 continuation | Fresh PASS on fictional/owned fixtures; no claim for new-policy checkpoints. |
| New-policy continuation/persistence | **BLOCKED / NOT IMPLEMENTED**. No old fitness reused under another policy. |
| Actual nonzero-component calibration and before/after schedule quality | **NOT RUN** for integrated F2B. Only explicit algebra is new; F2A data is historical. |
| Original versus experimental full-GA timing, allocations and memory | **NOT RUN**: no legitimate integrated experimental engine to compare. Regression elapsed times are not GA benchmarks. |
| Browser, build/lint, PostgreSQL | NOT RUN: no application/UI integration; no database connection or operations. |
| Institutional use, full CCS coverage, production F1 roster | BLOCKED and unchanged. |

## Concrete extension requiring review before application work

The following is a proposed minimum contract, **not implemented files or accepted policy values**:

1. Introduce a server/test-owned workload-policy DTO with distinct policy identifier, math/precision version, explicit positive finite coefficient, overload strategy and zero-target strategy. Missing policy means legacy; missing coefficient or unknown experimental fields must reject an experimental request, not silently default. Do not reuse preference-policy1/2 to imply workload policy. No institutional role/trust grant comes from selecting a score.
2. Centralize one version-aware workload dispatch inside the existing scorer's workload block so original engine, crossover and mutation aliases all use the same pinned objective. Keep the other seven terms, hard constraints and operator implementations unchanged. A new `services/workload_scoring_policy.py` is a possible pure-policy module, but adding it alone cannot hook current callers.
3. Capture that exact configuration in `FrozenInputs`, freeze it once per run, reject changes at continuation/publication and report every component under the captured policy. Do not use mutable globals, a runtime monkeypatch, environment fallback, final-score replacement or untrusted client metadata as authority.
4. Approve a versioned continuation strategy across `ga_checkpoint_service`, `preference_scoring_policy`/compatibility manifest, V2 engine/store/service and historical readers. Either a reviewed exact-source bridge extension or a separate immutable legacy continuation bundle must preserve supported existing policy behavior. Do not merely update expected hashes, spoof old engine identity, disable checks or migrate old artifacts. Preserve current V1/V2 proof cases before and after the change.
5. Define exact versus float/fixed representation for policy component, total ordering and persisted/display values. Prove oracle equivalence and tie/ranking behavior at all supported targets/weights and near ties; current `Fraction` objects cannot be directly serialized/reported by existing guards. No silent type allowlist widening or lossy cast is proposed.
6. Extend captured report/context and API interpretation through `fitness_reporting_service` and relevant frontend DTOs only as needed. Keep old definitions for old recorded policies; reject unknown versions rather than relabeling old results or recomputing them under new weights.
7. Then run the requested full F2B calibration and equal-seed/budget multi-generation comparison with candidate acceptance, checkpoints, best-ever, hard constraints, preference tradeoffs, zero/no-eligible faculty, scarcity/surplus, quality/runtime and separate allocation-memory measurements. New policy can legitimately change accepted candidates and subsequent RNG paths; within-policy reproducibility/continuation must hold. Institutional activation remains separately blocked.

Expected production touchpoints to review are `genetic_algorithm/operators/FitnessFunction.py`, `genetic_algorithm/utils/FrozenInputs.py`, checkpoint/preference-policy compatibility services/manifest, `ga_v2_engine.py`, `ga_v2_store.py`, `ga_v2_service.py` and report/context schemas. This is a source/provenance/continuation extension, not an already-supported setting. Original operator math, Faculty target rules, roster/data and Chair/publication authority need not change. This report supplies the review boundary rather than deciding a legacy-compatibility release contract implicitly.

## Exact changes, preservation and reproduction

Existing files modified: **none**. New files:

- `docs/workload-fairness-f2b-implementation.md` — this stopped-integration report/specification.
- `docs/testing/workload-fairness-f2b/test_integration_boundary.py` —10 fictional read-only characterization cases.
- `docs/testing/workload-fairness-f2b/run_checks.py` — isolated default/V2/contract evidence runner.
- `docs/testing/workload-fairness-f2b/verify_v1.py` — new output wrapper around the unchanged source-mirror worker; copies no institutional data.
- `docs/testing/workload-fairness-f2b/audit_evidence.py` — hash/privacy/preservation and final inventory verification.
- JSON baseline, boundary observations, all command records, calibration algebra and manifest under the same evidence root. [Manifest](testing/workload-fairness-f2b/manifest.json) records every exact new path/hash.

Final inventory: **25 new files (four Python, one Markdown, twenty JSON)**;24 artifact hashes verified, excluding the manifest itself. All456 prior artifact entries independently verify. Privacy findings: zero. New-file syntax/whitespace and Git whitespace checks pass. Git's existing LF-to-CRLF advisory for protected preferences did not change its raw bytes or stage a file.

The baseline includes **1,845 pre-existing paths and all23 academic files**, previous F1/F1.5/F2A and performance work, original GA/scoring/RNG/roster/migrations, six historical checkpoints, saved schedules/history, existing compatibility sources, Git index and the two original local data modifications. Protected preferences/settings remain byte-identical, unstaged and uncommitted. No source, academic row, role, trust gate, checkpoint or history is restored/overwritten. Evidence has only fictional structural/numeric observations, hashes and sanitized test output; no credentials, session artifacts or private faculty records are archived.

Run from the repository root with the existing venv/Node; no installation:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/workload-fairness-f2b/run_checks.py backend
.\.venv\Scripts\python.exe -B docs/testing/workload-fairness-f2b/run_checks.py frontend
.\.venv\Scripts\python.exe -B docs/testing/workload-fairness-f2b/verify_v1.py
.\.venv\Scripts\python.exe -B docs/testing/workload-fairness-f2b/audit_evidence.py
```

Each run creates fresh evidence and uses whitelisted child environments. The V1 mirror's archival inputs are newly generated fictional files with real matching hashes, not copied institutional data; it does not weaken fingerprint checks. The verifier stops on mismatches without repairing existing files. No database operation, dependency installation, staging, commit, push, F2 activation, F3, cleanup or C++ work occurred.

**Review result: NO-GO for F2B integration/activation; architecture qualification is ready for review.** The versioned shared-dispatch/legacy-continuation/reporting contract and zero-target/coefficient/overload decisions above must be reviewed before implementing beyond the current stop. F2A remains a prototype, not a completed F2B scoring option.
