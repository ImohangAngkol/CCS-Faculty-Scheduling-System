# Phase 4C.2: existing implementation revalidation

Review date: **2026-10-20, Asia/Manila**. Branch `main`; HEAD `3167cda2bd2d86011b50ea582026a4c39accb529`.

**EXISTING IMPLEMENTATION REUSED / OFFLINE REVALIDATION PASS / POSTGRESQL ACCEPTANCE PENDING.** No duplicate models, migration, repository, adapter or planner were created. No application or existing documentation file was modified in this request. This is a new verification note for the existing [implementation account](../../phase-4c2-academic-foundation.md), not a replacement of its original results.

## Inputs reviewed and repository findings

Reviewed the updated [academic contract](../../phase-4c1-academic-data-contract.md), [relational proposal](../../architecture/phase-4c1-relational-schema.md), [confirmed scheduling workflows](../../phase-4c-confirmed-scheduling-workflows.md), seven-table scope-review findings in the conversation, and the existing implementation account. Inspected the academic model/migration, Alembic discovery, schemas, repository, adapter, planner, test isolation and target safety interlocks. All existing implementation artifact hashes still match their earlier manifest.

The working tree already contained the full uncommitted 4C.2 implementation, the updated designs, and pre-existing modifications to `backend/data/faculty_preferences.json` and `backend/migrations/env.py`. These are retained, including the existing protected preference bytes. They are not new changes made by this revalidation. No staging or remote operation was performed.

## Exact implementation coverage

| Existing implementation | Coverage / limit |
|---|---|
| `backend/academic_models.py` | Exactly seven academic tables using the existing Base: `academic_scopes`, `academic_years`, `academic_terms`, `academic_faculty_legacy_codes`, `academic_courses`, `academic_sections`, `academic_course_offerings` |
| `backend/migrations/versions/4c_0001_academic_foundation.py` | One additive revision after `4a_0001`; frozen DDL for the seven tables, PK/FK/UQ/CHECK/indexes, immutable identity/version/archive guards, same-scope/term relationships, calendar containment and concurrency guards; no seed/backfill |
| `backend/migrations/env.py` | Existing explicit academic metadata registration and caller-owned migration connection support; unchanged by this request |
| `backend/repositories/academic_repository.py` and package initializer | Explicitly injected, SELECT-only, read-only consistent-snapshot repository; explicit scope/term with no fallback; global legacy faculty bridge labelled as such |
| `backend/services/academic_metadata_adapter.py` | Legacy-compatible scoped UUID formulas and identity-only projection comparison; no active metadata/GA cutover |
| `backend/services/academic_import_service.py` | Deterministic caller-supplied normalized identity JSON planner; new/matching/conflicting/unresolved/deferred classifications, discrepancy codes, source keys/row ordinals/hashes; no file loading, DB access or apply operation |
| `backend/schemas/academic.py` | Frozen, allowlisted identity/report schemas; unsupported descriptive and scheduling fields remain explicit |
| `backend/tests/academic/` | Focused synthetic offline tests and separately gated PostgreSQL suite; overrides the parent GA-loading fixture and blocks institutional input reads and offline network/driver connections |

The earlier [implementation manifest](phase-4c2-implementation-manifest.json) provides the exact existing source/test inventory. Its 16 artifact hashes are checked rather than rewritten. The existing identity models, account-binding FK/checks, old migration, legacy UUID helper, application routes, frontend, GA sources and stored artifacts are unchanged.

PostgreSQL guards remain implemented but **not executed or compiled by a PostgreSQL server**. The existing conservative mutation protocol uses one nonblocking transaction advisory gate and READ COMMITTED, next-revision updates, terminal archive protection and an empty-only downgrade. Offline SQL rendering and SQLite checks do not certify that protocol online.

## Compatibility with the professor-confirmed workflows

| Updated requirement / design issue | Foundation review finding |
|---|---|
| Confirmed GEC/external schedules and tentative/review states | Future dedicated external commitments, resource links and constraint sets are explicitly deferred. They are not forced into CCS course offerings or the current identity-only planner. No requirement to add those tables to 4C.2. |
| Every faculty adjustment needs scoped Chair approval | Existing account roles/bindings remain unchanged. Future scoped capabilities, requests, decisions and immutable schedule revisions are absent by design; no admin-as-Chair shortcut or direct schedule write is introduced. |
| External meetings may cover multiple sections or shared resources | Future external meeting/link entities can reference existing term/section identities without changing the approved one-course/section/term CCS offering cardinality. Canonical shared-room/instructor policy remains a later prerequisite. |
| Broad draft code bridge references profiles/import batches | The approved seven-table narrowing intentionally references existing `faculty_identities` directly and omits those dependencies. The implementation account already records this; the broad draft is not authority to expand the migration. |
| Immutable GA proposal and complete hard validation | Identity comparison is not full metadata/schedule equivalence or approval validation. No GA input activation, schedule revision store, new fitness call, checkpoint conversion or database-backed scheduling claim is made. |

**No blocking design conflict was identified within the approved foundation scope.** Calendar institutional facts, shared resources, Chair appointments/delegation and later publication policies remain unresolved for their respective future workflows; they do not require guessing identities or altering this inactive foundation. Any later requirement that changes identity/cardinality must stop for a separately reviewed migration, not reinterpret existing IDs.

## Fresh offline execution

From `backend`:

```powershell
..\.venv\Scripts\python.exe -B -m pytest tests/academic -q -p no:cacheprovider
```

The child process removed `DATABASE_URL`, both Phase 4B URL variables, `PHASE4C_TEST_DATABASE_URL` and `PHASE4C_POSTGRESQL_APPROVAL`; their values were never printed. Bytecode/cache writes were disabled. The existing test fixture rejects institutional input reads and offline network/driver connections. The default-skipped PostgreSQL module never executes its connection/migration fixture.

**85 passed, 17 skipped, zero failed, two warnings; 2.99s pytest duration; exit 0.** Python 3.14.2. Actual measured timestamps/runner duration and sanitized stdout are preserved in the [fresh execution record](20261020-foundation-revalidation-tests.json). This run is separate from the original 2026-10-19 test evidence; counts are not added together.

Both warnings are the existing Alembic missing-`path_separator` deprecation emitted by two tests. The configuration is unchanged. Offline coverage includes synthetic SQLite scalar/FK/uniqueness/rollback checks, frozen model/migration DDL agreement, migration ordering/full SQL rendering, Alembic connection dispatch, identity/code preservation, deterministic classifications, shadow comparisons, sanitized failures, and negative/fake catalog target gates. No new defect or implementation fix was required by this revalidation.

**NOT RUN:** real PostgreSQL schema/trigger/calendar/concurrency/downgrade execution, physical server/version/privilege inspection, institutional imports, GA execution/resume, full application/auth regressions, frontend builds/browser tests or screenshots. No new API or UI was implemented, so frontend/browser verification is not applicable to this narrow revalidation. No production, cross-department conflict, full metadata parity or confirmed-workflow acceptance claim follows from these unit results.

## Remaining PostgreSQL acceptance and next step

Separately approve a fresh isolated target and its read-only preflight: `ccs_ga_phase4c_test`, restricted role/owner `ccs_ga_phase4c_tester`, `127.0.0.1:5432`, public schema, configured only through private `PHASE4C_TEST_DATABASE_URL`. Existence/connectivity has not been checked. Do not reuse either Phase 4B database or the development database.

The prepared gate requires explicit connection authorization plus an execution interlock, validates exact target/owner/role/host/port and pristine schema/objects/privileges, and stops without reset/cleanup on rejection. Passing a read-only check does not authorize migration execution. After separate synthetic migration/test approval, the 17 prepared PostgreSQL cases must establish actual revision/inventory, direct constraints, identity/version/archive/lock guards, calendar containment/year shrink, rollback, populated downgrade refusal, concurrency and read-only snapshot behavior. Retain the resulting isolated schema for review; no automatic disposal or rerun against a now-nonempty target.

Record actual server version and real pass/fail/skip evidence before accepting PostgreSQL behavior. The recommended next action is that narrowly scoped approval/review, not GEC/Chair implementation, institutional import or GA cutover. The eighteen proposed future relations remain unimplemented.

## Files and preservation for this request

Only three new verification artifacts were created:

1. `docs/testing/phase-4c/20261020-foundation-revalidation.md` — this note.
2. `docs/testing/phase-4c/20261020-foundation-revalidation-tests.json` — fresh offline execution.
3. [20261020-foundation-revalidation-manifest.json](20261020-foundation-revalidation-manifest.json) — artifact hashes, reviewed dependencies and preservation/static checks.

No existing file was changed. The manifest records comparisons against all 422 pre-request baselined files, including the Git index. Protected preferences, faculty identity sources, account schema, both migrations, application routes/frontend, GA operators/scoring/RNG/checkpoint sources, saved schedules/histories and existing Phase 4B/4C evidence remain byte-identical to their pre-request versions. Hash comparisons establish byte preservation, not execution of a live database query or GA run.

The foundation remains **ready for code/offline-evidence review, with PostgreSQL acceptance outstanding**. No database connection, schema application, protected data change, staging, commit or push occurred.
