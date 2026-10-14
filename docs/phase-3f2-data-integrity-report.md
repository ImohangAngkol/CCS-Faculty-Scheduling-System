# Phase 3F.2: data integrity, authorization and preference correctness

## Pre-implementation investigation

The existing Phase 3F.1 roadmap and bug report were read first. Existing uncommitted Phase 3F/3F.1 changes, faculty preferences and saved artifacts are retained. PostgreSQL dependencies exist, but no authentication/database integration is present.

| Defect | Verified cause and reproduction | Expected vs actual | Data/compatibility risk | Minimal correction and required tests |
|---|---|---|---|---|
| BUG-004: anonymous writes | Preference PUT/DELETE and settings PUT have no authenticated principal dependency. An anonymous TestClient PUT succeeds against temporary storage. Client faculty code/adminMode is not identity. | Writes need trusted identity and role/ownership; currently any caller can change records. | Real faculty/account binding does not exist; inventing a client header or token would create fake authorization. | Deny unauthenticated writes by default; define server-principal/ownership/admin rules tested through isolated dependency overrides. Real identity integration remains blocked on Phase 4 authentication. |
| BUG-005: corrupt replacement | `_read_preferences` catches JSONDecodeError/OSError and returns an empty list; save rewrites it with direct non-atomic JSON output. Temporary malformed JSON is silently replaced. | Fail explicitly and preserve bytes; preserve unrelated records and serialize updates. | Whole-file writes can truncate or lose concurrent updates. Legacy records must remain readable without silent migration. | Strict structural read, explicit storage errors, a process lock around read/merge/validate/atomic replace, reject extras/invalid IDs, retain omitted fields and reload after save. Test corrupt/unreadable files, interrupted replacement, concurrent updates and round trips with temporary files. |
| BUG-006: disabled exact day/time | `_score_exact_subject_schedule_blocks` uses importance but ignores enable flags. A Monday lecture with mismatched Tuesday/time preference adds 20+30 even when both flags are false. | Disabled day/time contributes zero independently; other existing terms unchanged. | Corrected scores differ. Existing checkpoint scores/population must continue under original semantics; historical observations must not be rewritten. | Minimal helper gating for new evaluations, explicit versioned frozen scoring policy for new runs; preserve legacy policy for old checkpoints with strict source/runtime/input integrity checks. Tests independent flags, missing flags, actual breakdown, reporting policy, unchanged RNG/call counts and legacy continuation. |

The exception to protected source integrity is limited to the scorer helper/normalization, frozen scoring-policy provenance, and checkpoint policy compatibility. Operators, generation mathematics, weights, hard gates and RNG operations are not changed. New checkpoints need an optional frozen-policy marker to distinguish corrected from legacy scoring; existing files and schema version remain untouched.

## Implemented scope and final defect status

| Original defect/status | Root cause | Correction | Final status |
|---|---|---|---|
| BUG-004, HIGH, unresolved | No trustworthy server principal; client code/adminMode was treated as a UI selector, not authorization. | Anonymous preference/settings PUT and preference DELETE return 401. Trusted principal rules return 403 for other-faculty writes, faculty priority changes, settings and resets. | PARTIALLY FIXED; real authentication/account integration BLOCKED on Phase 4. No production user can save through the current provider. |
| BUG-005, HIGH, unresolved | Corrupt/unreadable JSON returned []; direct whole-file writes could truncate or lose unrelated updates. | Strict structural reads, explicit 503, duplicate/invalid record rejection, read/merge/validate/replace/reload under one process lock, fsynced temporary file and atomic replace. | FIXED within the supported one-process deployment. |
| BUG-006, MEDIUM, unresolved | Exact subject blocks checked importance but ignored enable flags. | New policy 2 independently gates exact day/time penalties; versioned legacy policy 1 preserves existing checkpoint scoring. Reports use original policy. | FIXED for corrected evaluations, with explicit legacy continuation exception. |

## Security design and blocker

`services/preference_authorization.py` defines a server principal with role and stable faculty identity. The production identity provider returns no principal because no verified credential/session subsystem exists. It does not read a client faculty ID, role header, bearer string or environment bypass as proof of identity. An unconfigured provider denies writes. A future Phase 4 provider must verify credentials, obtain role/faculty mapping from trusted account data and supply this principal.

Permission rules are server-side: an administrator can edit normal faculty preferences, reset records and manage supported settings; a faculty principal can update only its own stable identity and cannot change administrator priority. Unknown/external faculty IDs are rejected. An unchanged priority in a full faculty form can round-trip; omitted priority is retained. Client `adminMode` remains presentation, not proof of permission.

Positive tests override the provider inside temporary test fixtures only. There is no configurable development token, shared password, client role selector or production bypass. Removing test overrides leaves anonymous calls denied. **This is security groundwork, not a working login system or production authorization rollout.** Preference reads, GA control/history/export and other resources still require Phase 4 read/ownership policies. Existing public metadata is not suddenly claimed private.

Faculty self-service no longer defaults to Faculty 0: without verified account binding it displays an explicit unavailable sign-in/identity message and mounts no editor. The administrator review page explains that saves are currently locked. It remains possible to inspect preferences. API save rejection preserves the draft and displays a failure, never Saved.

Phase 4 must provide verified credentials/identity provider integration, secure session/token lifecycle and revocation, stable account-to-faculty mapping, administrator/faculty permissions and all-resource ownership checks, credential recovery, account/deactivation policies, audit actor identity and protected private reads/exports/publishing. That dependency must be resolved before accepting Phase 3G.

## Persistence safeguards

- Missing files return unsaved defaults; GET does not create records/settings.
- Invalid UTF-8/JSON, duplicate JSON keys, deeply malformed JSON, invalid container/records, duplicate faculty records and unregistered faculty codes fail explicitly with 503. Original bytes remain unchanged.
- Existing records receive structural validation, not a new eligibility/duration migration on read. Older semantic preferences remain available for review. Unrelated dictionaries, including retained legacy fields, are preserved.
- New payloads forbid unknown fields and nested extra fields, require actual boolean flags, reject malformed fields and invalid faculty IDs, and run the existing eligibility/meeting-pattern validation.
- PUT merges only explicitly supplied fields into the current record. Omitted fields, disabled flags, optional null time fields and unrelated faculty records survive.
- A process-local reentrant lock covers the entire read/merge/authorization-field-check/validate/atomic-replace/reload transaction. Concurrent unrelated writes and concurrent independent partial updates to the same faculty cannot lose each other's changes in one process.
- A temporary file is created in the destination directory, written with UTF-8, flushed and fsynced, then replaced atomically. Pre-commit failures leave the previous valid file untouched. No partial file is published; cleanup is attempted without hiding the primary error.
- A read-back comparison verifies the committed JSON. If verification fails after commit, the response is a failure with guidance to reload, not a fabricated success or blind reset.
- Settings reads/writes get the same integrity/atomicity boundary and administrator authorization. No live settings file or penalty value was changed.
- No automatic corrupted-file repair, dataset reset, backup deletion or migration is performed.

Supported scope remains **one backend process**. The lock is not a distributed/file lease. Independent servers/external editors are unsupported. Use private directory ACLs and institutional backup/recovery; atomic replacement is not a substitute for backup or a multi-file database transaction.

## Fitness toggle correction and exact before/after behavior

The professor's scorer structure, all eight terms, penalty values, priority multipliers and formulas remain. Only the exact day/time helper's applicability changes.

For a mismatched exact subject block with day importance 4, time importance 3, weights 5/10 and priority multiplier 1:

| Day flag | Time flag | Original policy 1 (day/time) | Corrected policy 2 (day/time) |
|---|---|---|---|
| false | false | 20 / 30 | 0 / 0 |
| true | false | 20 / 30 | 20 / 0 |
| false | true | 20 / 30 | 0 / 30 |
| true | true | 20 / 30 | 20 / 30 |

Missing legacy flags preserve prior influence **for exact subject blocks only**. Normalization retains explicit exact applicability separately from general preference defaults. General preference behavior, subject/gap/lecture-lab flags, importance zero, independent day/start membership and matching internal raw starts are unchanged. There is no new joint meeting-match equation and no reward term.

The whole-fitness test confirms that only disabled day/time components change and total difference equals those removed contributions; all other components match. No new fitness calls or RNG draws are introduced in the optimization loop. Because corrected scores differ, policy-2 optimization can choose different candidates and its subsequent trajectory may differ from policy 1; claiming identical schedules across different scoring policies would be false.

Reports read the captured policy and recorded numbers. They do not recompute historical fitness with current preferences. Legacy reports retain original interpretation, corrected reports show Disabled for false flags, and unsupported future source versions retain observed totals/workloads while declining new derived interpretation.

## Checkpoint compatibility and protected-source exceptions

Three protected files necessarily changed:

1. `backend/genetic_algorithm/operators/FitnessFunction.py`: minimal helper guards and legacy-missing-flag normalization/provenance.
2. `backend/genetic_algorithm/utils/FrozenInputs.py`: new runs capture `preference_scoring_version: 2`.
3. `backend/services/ga_checkpoint_service.py`: validate the original/corrected policy and the matching exact engine fingerprint.

`fitness_policy_compatibility.json` stores **passive compressed original source bytes** for those three files and their original hashes, plus pinned compatible release hashes and the policy helper hash. It contains source code, not user preference/checkpoint data. The archive is never executed, imported as Python or loaded from a checkpoint.

For a legacy checkpoint lacking the optional policy marker, policy 1 applies. Its fingerprint is reconstructed using the exact original bytes for the three authorized source exceptions, **current bytes for every other previously fingerprinted file**, and the same original engine/runtime/package canonical identity. The installed exception files and policy helper must match the pinned verified release; the archived bytes must match their original hashes. Other code changes, unknown profiles, runtime/input differences or integrity failures still reject continuation. A manifest is not automatically regenerated during execution.

Policy-2 runs fingerprint the corrected source plus compatibility provenance/helper. A checkpoint cannot select another scoring policy while retaining an incompatible fingerprint. Integrity, bounded JSON graph reconstruction, counters, population/best hard validation and RNG validation remain mandatory; actual resume revalidates. No saved-best schedule substitutes for the full population.

The checkpoint envelope/schema version remains 1. **The sole additive serialized change is the optional scoring-policy field inside new frozen input contexts**, necessary to distinguish semantics. Existing checkpoint files are not rewritten. Legacy continuations keep their original marker absence/profile and best scores. History capture uses the restored engine profile so resumed legacy records append consistently; original history/candidate IDs/scores are not rewritten.

Safe deployment: do not upgrade/reload code underneath an executing worker. First finish or durably pause under the old process, then restart one worker with the compatible runtime. The bridge supports the exact pre-Phase-3F.2 source baseline, not arbitrary older/mixed releases. Changing line endings/source/package versions can legitimately make a checkpoint incompatible; do not bypass checks or edit fingerprints.

Protected-file SHA-256 verification: **133/136 unchanged**, with exactly the three explained source exceptions. All source data, faculty preferences, GA configuration, notebooks, saved schedules, uploaded baseline, checkpoints and generation history in the original baseline remain byte-for-byte unchanged. The generation loop, selection/crossover/mutation/elitism, hard validators, RNG restoration and best tracking services are unchanged.

## Files changed during Phase 3F.2

Backend:

- `routers/preferences.py`, `schemas/faculty_preference.py`.
- New `services/preference_authorization.py`, `preference_storage_service.py`, `preference_scoring_policy.py`, `fitness_policy_compatibility.json`.
- The three protected source exceptions listed above.
- `services/ga_history_service.py` and `fitness_reporting_service.py`: original policy/engine provenance and truthful reporting.
- New `tests/test_preference_integrity.py`, `test_preference_toggles.py`; updated `test_preference_validation.py`, `test_system_audit.py`, `test_fitness_reporting.py`.

Frontend:

- `src/api/preferences.ts`, `components/faculty/FacultyPreferenceEditor.tsx`, `pages/admin/PreferencesReview.tsx`, `pages/faculty/Preferences.tsx`.
- New `tests/preferenceApi.test.mjs`; updated `preferences.browser.test.mjs`, `gaMonitoring.browser.test.mjs` (failure diagnostics only for this phase), `package.json` test script.

Documentation: this report, `system-bug-report.md`, `implementation-roadmap-status.md`, and policy note in `phase-3f-fitness-analysis.md`.

Pre-existing Phase 3F/3F.1 edits remain separate. In particular, the already-dirty institutional preference file was neither reverted nor rewritten.

## Verification results

Final backend control/checkpoint suite result: **142 passed, 1 genuine browser case run separately**.

Executed current checks:

| Suite | Result |
|---|---|
| Metadata, preference validation, audit, integrity/toggle and reporting combined | 128 passed before the two added reporting cases and one added deep-JSON case |
| Final reporting suite | 27 passed; includes original-policy reporting and unsupported-future-source observations |
| Final integrity suite | 26 passed; includes deep malformed JSON |
| Stronger exact legacy uninterrupted vs pause/resume comparison | 1 passed; schedules/history/scores/analysis/RNG and counted service fitness calls match |
| Existing tournament, crossover, eligibility, fixed/preassigned/lab/workload constraints | 96 passed |
| Existing Phase 3B–3E backend monitoring/stop/recovery/pause/history/logging/Unicode suite | 142 passed, 1 genuine browser case run separately |
| Genuine isolated FastAPI + Edge start/pause/refresh/concurrent inspection/resume | 1 passed in 82.10 seconds; same run/population continued |
| Frontend preference model/API contracts | 22 passed |
| Frontend GA/report/history/log/display contracts | 48 passed |
| Real Edge preference DOM/pointer suite with isolated API responses | 23 passed; unauthorized/invalid save retained draft, sign-in boundary, rankings and fixed-duration calendar |
| Real Edge GA/control/history/report suite with isolated API responses | 52 passed on rerun |
| Production build and focused changed-file lint | Passed; existing large-chunk warning remains |

The first GA browser run had a stopping-refresh timeout followed by recovery-scenario failures; the same implementation passed all 52 checks on rerun with added diagnostic capture. No application root cause was established. This is a documented unconfirmed test/timing risk, not a claimed product fix or justification to weaken controls/timeouts. An initial new legacy test used a nonexistent test-only transition method; it was corrected to the existing admission API before successful verification. Successful repeated cases are not double-counted.

The in-app browser connection was attempted and failed with unavailable sandbox metadata. Browser automation nevertheless ran through the repository's isolated Edge harness. Mocked UI tests are not claimed as production authenticated acceptance. The separate genuine FastAPI/browser continuation integration did execute. No full institutional GA or destructive artifact test was run.

Final distinct backend count: **370 passed (131 metadata/preference/report/integrity/toggle/audit + 96 domain/operator + 142 Phase 3B–3E + 1 genuine browser integration)**. Frontend contracts/models: **70 passed**; browser results: **75 passed** (including their parent results). The genuine backend/browser integration is counted once in the backend total. Existing TestClient deprecation warnings and unrelated repository lint findings remain; no new changed-file lint error was introduced.

## Updated progress and remaining work

Original inventory remains 56 groups: **41 COMPLETE AND VERIFIED; 4 IMPLEMENTED BUT NOT FULLY TESTED; 4 PARTIALLY IMPLEMENTED; 4 UI PLACEHOLDER ONLY; 2 NOT IMPLEMENTED; 1 BLOCKED**. Twelve earlier N groups retain their missing-original-milestone classification. The newly explicit future twelve requirements are recorded separately with overlap references, not double-counted.

Original confirmed defects remain seven: **six fixed; one partially fixed/blocked (BUG-004)**. Production login/full RBAC, protected reads/control/history/export/publishing, database integration, distributed writes/run ownership, production-sized profiling, retention and standalone publishing remain outside this phase. The original empirical history failure is not retroactively assigned an invented root cause.

Recommended next authorized phase: **Phase 4 real faculty/administrator identity and authorization integration**, resolving BUG-004 before Phase 3G acceptance. Future trials/voting/aggregation/administrator oversight, PostgreSQL/terms, publishing/ratings, profiling/selective C++, formal evaluation, cleanup and deployment are plans only.

## Exact manual acceptance procedure

Use the tests and a separate temporary development storage directory for mutable positive cases. Do not treat the institutional JSON/checkpoints as disposable fixtures.

1. Ensure there is no executing production worker. If necessary, finish or commit a durable pause under its original process/runtime. Restart the updated backend with one worker and compatible packages; avoid autoreload during execution.
2. Open administrator Preferences. Confirm the account/save-lock notice, normal faculty privacy selector and eligibility-filtered subject list. Load existing data without writing.
3. Without authentication, edit a harmless draft and click Save. Inspect PUT /preferences/{code}: expect 401, Save failed with the authentication message, draft retained and no Saved status. No source preference bytes change. A forged X-Role/X-Faculty-ID/bearer string must not authorize a write.
4. Open /faculty/preferences. Expect the explicit unconfigured sign-in/identity message, no Faculty 0 default and no editor mounted.
5. Run `pytest backend/tests/test_preference_integrity.py` using the project Python and a unique temporary basetemp. Positive trusted-principal cases must save/reload; other-faculty/priority/settings/reset attempts return 403. Corrupt reads/saves return 503 and preserve bytes. Concurrent partial updates and interrupted replacements pass. These overrides are test-only; do not add a production development bypass.
6. Run the preference browser suite. Confirm ranked search/categories, exact card drops, move/remove, no resizing, lab 180 minutes, disabled controls, invalid/unauthorized save states and fixture save/reload.
7. Run `pytest backend/tests/test_preference_toggles.py`. Verify false/false=0/0, true/false=20/0, false/true=0/30, true/true=20/30 for the documented mismatch fixture. Missing flags retain prior exact-block influence; other components/weights remain unchanged.
8. In isolated scoring-policy checkpoint fixtures, pause/refresh/resume under policy 2 and legacy policy 1. Verify same run ID, full population, RNG/counters/history and original policy scores; reject changed inputs/source/runtime/integrity. Never edit an old fingerprint or restart generation 0 as a substitute.
9. Inspect old saved reports. Recorded totals/component contributions remain original; legacy policy is identified, current flags are not applied retroactively, and unavailable observations remain unavailable.
10. Confirm all institutional artifact hashes still match the pre-task baseline. No commit/push, database migration, C++ work, notebook edit or Phase 3G work should be present.

STOP after Phase 3F.2. Authentication integration remains an explicit blocker; no automatic next phase is started.

