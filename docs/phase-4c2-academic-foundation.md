# Phase 4C.2: seven-table academic foundation

Implementation/review date: **2026-10-19, Asia/Manila**. Baseline: `3167cda2bd2d86011b50ea582026a4c39accb529`, branch `main`.

**IMPLEMENTED / OFFLINE VERIFIED; POSTGRESQL ACCEPTANCE PENDING.** Exactly seven additive academic tables are modelled. No PostgreSQL connection, live migration, institutional import, API/UI activation or GA execution was performed. The [offline execution record](testing/phase-4c/phase-4c2-offline-tests.json) records **85 passed, 17 skipped, zero failed, two warnings** in the final run. The [implementation manifest](testing/phase-4c/phase-4c2-implementation-manifest.json) identifies the files and preservation checks.

## Objective and approved boundary

Read with the historical [4C.1 academic contract](phase-4c1-academic-data-contract.md), [relational target proposal](architecture/phase-4c1-relational-schema.md) and [design manifest](testing/phase-4c/phase-4c1-design-manifest.json). Those drafts describe 41 possible new tables, not an approved migration. The user's subsequent seven-table scope review and implementation authorization in the conversation govern this implementation.

The implemented subset stores calendar and identity relationships only. It does not establish complete legacy metadata parity, schedulability, institutional ownership of source facts, or database-backed GA compatibility.

Approved reductions from the draft are retained: the faculty code bridge references existing `faculty_identities` directly, with no profile or import-batch dependency. No records are inserted by the migration. The existing identity models, historical `4a_0001` migration and account binding constraints are unchanged.

## Files created or modified

| Path | Purpose |
|---|---|
| [backend/academic_models.py](../backend/academic_models.py) | Seven academic tables using existing SQLAlchemy Base; no engine, data-file or GA imports |
| [backend/migrations/versions/4c_0001_academic_foundation.py](../backend/migrations/versions/4c_0001_academic_foundation.py) | Frozen additive DDL, PostgreSQL guards and empty-only downgrade |
| [backend/migrations/env.py](../backend/migrations/env.py) | **Only modified existing file**: explicit model discovery and caller-owned connection support |
| [backend/repositories/__init__.py](../backend/repositories/__init__.py) | New inert repository package |
| [backend/repositories/academic_repository.py](../backend/repositories/academic_repository.py) | SELECT-only repository using an explicitly supplied read-only transaction |
| [backend/schemas/academic.py](../backend/schemas/academic.py) | Frozen identity projections, discrepancy and dry-run report schemas |
| [backend/services/academic_metadata_adapter.py](../backend/services/academic_metadata_adapter.py) | Scoped UUID helpers and identity projection comparison; separate from live metadata |
| [backend/services/academic_import_service.py](../backend/services/academic_import_service.py) | Deterministic normalized-document dry-run planner; no apply operation |
| [backend/tests/academic/conftest.py](../backend/tests/academic/conftest.py) | Blocks institutional data reads; overrides legacy GA-importing fixture; blocks offline network/database connections |
| [backend/tests/academic/test_academic_foundation.py](../backend/tests/academic/test_academic_foundation.py) | Synthetic SQLite constraints/rollback, migration SQL rendering, repository and Alembic dispatch tests |
| [backend/tests/academic/test_academic_planner.py](../backend/tests/academic/test_academic_planner.py) | Stable mappings, discrepancy classifications, privacy and comparison tests |
| [backend/tests/academic/postgresql_safety.py](../backend/tests/academic/postgresql_safety.py) | Exact Phase 4C target and read-only pristine catalog/ownership/privilege preflight |
| [backend/tests/academic/test_academic_safety.py](../backend/tests/academic/test_academic_safety.py) | Negative URL/approval gates and fake catalog safety branches, without connections |
| [backend/tests/academic/test_academic_postgresql.py](../backend/tests/academic/test_academic_postgresql.py) | Seventeen prepared live PostgreSQL cases; default skip |
| `docs/phase-4c2-academic-foundation.md` | This implementation, limitation and next-acceptance report |
| `docs/testing/phase-4c/phase-4c2-offline-tests.json` | Actual offline run and earlier attempt history |
| `docs/testing/phase-4c/phase-4c2-implementation-manifest.json` | Artifact hashes, validation scope and preservation inventory; excludes itself |

There are 16 created files and one modified existing file. The three pre-existing untracked 4C.1 documents and pre-existing modified faculty preferences are separate from this change.

## Tables and migration

Revision `4c_0001` follows `4a_0001`. The migration contains frozen PostgreSQL DDL rather than importing mutable runtime model definitions. It creates exactly these seven tables, their keys/indexes, three trigger functions and associated triggers. It does not create extensions, seed records, modify authentication tables or create a schema.

| Table | Identity and integrity boundary |
|---|---|
| `academic_scopes` | UUID PK; unique nonempty immutable scope key; institutional/department labels |
| `academic_years` | UUID PK; scope FK; unique scope/year key; nullable paired ordered dates; unresolved/confirmed calendar status |
| `academic_terms` | UUID PK; scope FK; same-scope optional year FK; unique scope/term key and global identity scope; unique known year/ordinal; positive optional ordinal; explicit timezone, kind, calendar status and lifecycle |
| `academic_faculty_legacy_codes` | Existing faculty UUID PK/FK; globally unique nonnegative integer code; immutable allocation timestamp; no account creation or code allocator |
| `academic_courses` | UUID PK; scope FK; unique normalized scope/course key; descriptor-only or verified catalog identity, neither sufficient for GA scheduling |
| `academic_sections` | UUID PK; composite term/scope FK; unique normalized term/section key |
| `academic_course_offerings` | UUID PK; composite same-scope course and same-term/scope section FKs; unique course/section/term and term/key; key must match course-code::section-code |

Except the append-only faculty-code reservation, administrative rows have created/updated timestamps, `row_version > 0`, `is_active` and optional archive timestamp. Insertions require revision one. Updates require unchanged creation time and exactly the next revision; a future writer must additionally use a revision predicate to detect stale edits. No write repository/API is supplied.

Identity keys and offering membership cannot be changed. Deletes and truncation are rejected. Archived rows cannot be edited or reactivated, and their unique keys remain reserved. Active insertions/updates require usable parents; even an inactive new child cannot be inserted under a locked/archived parent. Status-only closing updates may deactivate/archive an existing child after parent deactivation without deleting it. Academic deactivation does not change account activity or sessions.

### Calendar and concurrency mechanics

All academic INSERT/UPDATE/DELETE statements acquire the same **nonblocking transaction advisory lock**, `(41002,1)`. A competing writer fails with SQLSTATE `55P03`; no automatic retry is implemented. This deliberately serializes even different academic scopes during this small foundation milestone. Ordinary SELECTs do not acquire the gate.

Academic mutations require **READ COMMITTED**, otherwise SQLSTATE `0A000`. PostgreSQL `VOLATILE` AFTER STATEMENT guards validate term/year containment and timezone names after the complete command, including parent-year changes. Confirmed terms require a confirmed year, ordinal, non-legacy kind and contained dates. Dated terms attached to years also require contained dates. Unknown legacy calendar facts are not inferred or seeded. Term overlaps are not prohibited because institutional overlap policy remains unresolved.

These mechanisms follow PostgreSQL's documented [volatile-function snapshot rules](https://www.postgresql.org/docs/current/xfunc-volatility.html), [trigger visibility](https://www.postgresql.org/docs/current/trigger-datachanges.html) and [transaction advisory locks](https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS). They are **implemented but not executed or verified against PostgreSQL** in this milestone. Offline rendering does not compile or execute PL/pgSQL bodies. Superusers/DDL owners can bypass/drop guards; runtime privilege design remains deferred, and no new grants are made.

Downgrade locks all seven tables before checking emptiness, refuses any populated academic table, then removes only the seven empty tables and their functions. No CASCADE, truncate, institution-data cleanup or downgrade below `4a_0001` is part of the test plan. For retained populated data, application rollback means leaving the additive tables intact and retaining legacy readers.

## Identity-only repository and shadow comparison

`AcademicRepository` accepts an existing Connection and never creates an engine, opens a transaction, commits, flushes or reads an environment URL. PostgreSQL reads require a read-only REPEATABLE READ/SERIALIZABLE transaction; offline SQLite fixtures require query-only mode. Explicit scope/term lookup fails without fallback. Storage errors are sanitized.

The projection includes the requested scope, term and referenced year; catalog identities in that scope; sections/offerings in that term; and the **global legacy faculty-code bridge**, explicitly labelled global rather than fabricated scope membership. No `users`, password or session fields are selected. There is no new HTTP route or authorization bypass; this is an internal explicitly invoked repository, not a multi-tenant API.

Comparison detects missing, unexpected, changed and duplicate primary identities. UUID sorting is only canonical comparison order, never GA construction order. Existing UUID helpers and namespace are preserved; new helpers accept explicit scope strings and do not consume Python GA RNG. The existing metadata adapter and frontend consumers remain active and unchanged.

## Dry-run import planner

The planner accepts caller-supplied bytes under logical source keys, an optional existing identity projection, and explicit authoritative UUID/integer-code pairs. It opens **no files**, loads no registry or `.env`, connects to no database and writes no records or reports. The caller may inspect the returned immutable plan and its counts.

Supported source format is a normalized JSON document: `schema_version=1`, `records=[typed identity records]`. This is **not a direct institutional CSV/registry importer**. Projection identity records intentionally omit calendar facts, lifecycle, workload and other descriptive fields. Matching means identity-field agreement only, never complete database-row agreement or permission to apply a plan.

Every source has a SHA-256 and each discrepancy has a logical source key, one-based row ordinal (zero for a malformed whole document), classification and code. Results are deterministic for identical source bytes regardless of source-map traversal order. Source row reordering retains identity meaning but changes source hashes and row references as expected.

- **New:** valid candidate identity without a conflicting existing UUID/natural key.
- **Matching:** identical supported identity fields already supplied in the existing projection.
- **Conflicting:** duplicate candidate identities/natural keys or disagreement with an existing identity. Source order cannot pick a winner.
- **Unresolved:** malformed/unknown fields, UUID/code mismatch, unknown faculty UUID, invalid UUID formula, missing parents, or scope/term disagreement. Invalid ancestors cannot validate descendants.
- **Deferred:** explicit kinds outside the identity foundation, such as eligibility, domain, workload, enrollment, room or preferences. Their payloads do not appear in reports and grant nothing.

Reports contain no raw rows, faculty names, credentials or exception messages. Full original bytes remain the caller's responsibility; sanitized reports are not a substitute for retained source provenance. No apply method, auto-upsert, registry rewrite, term inference or default-term fallback exists.

Valid keys outside the offered catalog can be supplied as descriptor-only catalog identities. Orphan eligibility/domain records remain deferred with source/hash/ordinal references; no offering, qualification or permission is manufactured. The historical 4C.1 aggregate observations are not re-imported or recounted here.

## Unsupported and deferred functionality

No profiles, degrees/rank, specialization/domain permissions, eligibility decisions, workloads/releases, capacities, actual enrollment, course titles/units, lecture/lab components/templates, rooms, availability/fixed blocks, external assignments, preferences, datasets, audit/import persistence or run snapshots are implemented. Unknown values are not represented as zero, false, synthetic enrollment 40, invented dates or guessed permissions.

Also deferred: new faculty/code allocation, institutional source parsers/apply, CRUD APIs, authorization/CSRF changes, management UI, active-term selection, term rollover, preference migration/carry-forward, full metadata parity and database-backed GA inputs. No data-directory export, chromosome change, scoring/operator/RNG change, fingerprint change, checkpoint conversion or historical rescore occurs. No frontend/browser execution or screenshot is applicable to this backend-only inactive foundation.

## Actual verification and attempt history

Final command from `backend`, with database URL/approval environment variables removed and bytecode/cache writes disabled:

```powershell
..\.venv\Scripts\python.exe -B -m pytest tests/academic -q -p no:cacheprovider
```

Python **3.14.2**; **85 passed, 17 skipped, zero failed, two warnings; 1.34s pytest duration; exit 0**. Exact measured start/end and runner elapsed time are in the execution record. Skips are all seventeen separately gated PostgreSQL cases. The two warnings are the same pre-existing Alembic `prepend_sys_path`/missing `path_separator` deprecation emitted by two tests; `alembic.ini` was not changed.

An earlier run had 61 passes and one failure: a quoted boolean server default was interpreted as text by SQLite, weakening its archive CHECK. The model now uses SQLAlchemy `true()` and the unexecuted migration DDL was updated accordingly. Subsequent successful runs and additions are preserved in the execution record; they are not added together as distinct acceptance passes. Earlier attempt timestamps were not recorded unless present in that record.

Offline PASS covers model/migration DDL agreement, Alembic revision ordering and full offline SQL rendering, injected-connection dispatch, synthetic SQLite scalar/FK/uniqueness/rollback checks, archive-key reservation, query-only repository behavior, sanitized injected failures, deterministic planner classifications, exact legacy formulas, no RNG consumption by identity helpers, no GA/application import, and fake/negative target safety branches.

**NOT RUN:** PostgreSQL PL/pgSQL compilation/execution, online schema reflection, actual PostgreSQL constraints/calendar/locking/concurrency/DDL rollback, live safety catalog inspection, backup/restore, institutional reconciliation/import, existing full application/auth/GA regressions, frontend build/contracts, browser acceptance or new screenshots. Existing automated/manual Phase 4B evidence remains historical and unchanged. No full-suite pass or production readiness is claimed.

## Next acceptance step: isolated PostgreSQL approval

Do not execute the live tests under this milestone's offline authorization.

1. Review this implementation, especially the global nonblocking write gate, READ COMMITTED mutation restriction, terminal archive rule and empty-only downgrade. These are conservative implementation choices, not new runtime features.
2. Separately approve provisioning/verification of a new disposable synthetic target: database `ccs_ga_phase4c_test`, restricted owner/login `ccs_ga_phase4c_tester`, host `127.0.0.1`, port `5432`, schema `public`. These objects have not been checked or provisioned. Never reuse the development or either Phase 4B database.
3. Configure only `PHASE4C_TEST_DATABASE_URL` privately in the operator process. No URL/password in shell arguments, source files, reports or logs; no default URL fallback. Leave the live approval variable unset until execution is explicitly approved.
4. After separate read-only authorization, review/run `inspect_empty_test_database` with its explicit `allow_connect` switch and approval sentinel. The SELECT-only gate checks server identity, database/schema ownership, restricted role flags, role memberships, unexpected schemas/relations/routines/types/extensions/default ACLs and grants. Rejection stops the operation. It never resets or cleans a nonempty target.
5. Only after approval for synthetic migrations/tests, enable `PHASE4C_POSTGRESQL_APPROVAL=I_APPROVE_ISOLATED_PHASE4C_POSTGRESQL_TESTS` and run the prepared PostgreSQL module. The sentinel is an execution interlock, not a replacement for human authorization. The fixture runs the pristine preflight before migrating the explicitly injected target connection to `4c_0001`.
6. The seventeen prepared cases cover inventory/revision/account FK, immutable/revision guards, date containment/year shrink, timezone/archive/delete/truncate protection, offering relationships, populated downgrade refusal, transactional DDL failure, concurrent writer/calendar exclusion, higher-isolation write refusal, read-only lookup and empty downgrade/upgrade roundtrip. Additional committed interleaving/load/privilege tests may be needed before any institutional activation; no performance or production concurrency claim is established by these cases.
7. Per-test synthetic rows roll back; the isolated migrated schema remains for inspection. Empty downgrade tests operate within rollback-only transactions on this explicitly disposable target. There is no automatic drop/reset/reseed or database disposal. A repeat whole-suite run against its now-nonempty schema will be rejected by the pristine gate; stop for review rather than bypassing it.
8. Archive sanitized real PostgreSQL results, server version, actual counts, discrepancies and hashes. Institutional import, APIs/UI and GA cutover remain separate approvals after that acceptance.

## Preservation and review readiness

The implementation manifest records comparisons against the pre-edit working tree, including the pre-existing local faculty-preferences change. Only `backend/migrations/env.py` is expected to differ among the 402 baselined existing files. The Git index, baseline HEAD, protected preference bytes, existing GA sources/inputs/schedules/checkpoints and historical 4C.1/4B evidence must remain unchanged.

Historical preservation/source entries for `backend/migrations/env.py` in earlier manifests remain their original as-of-phase observations, not assertions about this newly approved version. They are not rewritten. The new implementation manifest records both the pre-edit and current environment-file hashes.

No staging, commits, push, database provisioning/connection, service restart, credential rotation or fixture operation occurred. The foundation is ready for code/offline-evidence review **with PostgreSQL acceptance outstanding**. It is not ready for institutional import, deployment or Phase 4C.3 activation.
