# D15: disposable PostgreSQL acceptance — final evidence review

Inspected 2026-10-25, Asia/Manila. Branch `main`, HEAD and last-fetched `origin/main`: `c6baad2a0d59515555b33c84eca337a78a913a65`. No fetch, staging, commit or push in D15.

**Final review status:** **PASS within the authorized disposable PostgreSQL acceptance scope.** The operator executed 17 Phase4C cases and, after two preserved failed workflow attempts, all ten D9-D13 workflow cases passed. Codex inspected the saved artifacts; Codex did not execute PostgreSQL operations. The final run retained revision `d13_0001`, all twenty tables and fictional rows, with the Phase4C catalog unchanged and owned connection cleanup verified. **Production institutional authority remains BLOCKED; this is not production readiness.** Sections 1-17 are preserved stage history, including commands that must NOT be repeated against the now-populated retained database. Section 18 is the final review. No additional database operation is needed; a Git checkpoint requires separate authorization.

## 1. Objective and current decision

**D15 PostgreSQL acceptance is BLOCKED, not complete.** A PostgreSQL Windows service is running, but this process has no dedicated test connection, approval setting or verified disposable database. No PostgreSQL connection, online SQL statement, migration, provisioning, reset, truncate or deletion was attempted. A service name or localhost address cannot establish database identity, ownership, contents or disposability. The complementary regressions use only owned fictional SQLite stores and offline SQL rendering.

Work completed safely: preservation baseline, configuration/model/migration/test inspection, collection of the original 17 test IDs, fresh offline/SQLite regressions and a privacy-checked evidence manifest. These do not substitute for PostgreSQL acceptance. No application defect was reproduced or corrected.

Evidence: [manifest](testing/dashboard-d15/manifest.json), [environment inspection](testing/dashboard-d15/environment-inspection.json), [static model/migration inventory](testing/dashboard-d15/static-inspection.json), [preservation baseline](testing/dashboard-d15/preservation-baseline.json), [offline-only runner](testing/dashboard-d15/run_offline_checks.py), [audit utility](testing/dashboard-d15/audit_evidence.py). Exact commands, timestamps with `+08:00`, exit codes, warning summaries and sanitized outputs are in the per-run command records indexed by the manifest.

## 2. Environment and isolation status

Observed through Windows service metadata: `postgresql-x64-18`, Running, display label PostgreSQL Server 18. **Actual connected PostgreSQL version, cluster identity, listen address, database existence, role, ownership and schema inventory: NOT VERIFIED.** No attempt was made to reuse a pgAdmin session, recover passwords or inspect private credential files.

Presence-only inspection found none of `PHASE4C_TEST_DATABASE_URL`, `PHASE4C_POSTGRESQL_APPROVAL`, `D15_TEST_DATABASE_URL`, `DATABASE_URL`, the checked Phase 4B variables or common PG connection variables configured in this process. No project-root/backend/frontend `.env` file exists. These observations apply to this process/workspace, not other private terminals, pgAdmin registrations or machine-wide credential stores. No connection URL/password was printed or retained.

Installed Python/SQLAlchemy/Alembic/driver versions are recorded in the environment artifact. Having psycopg2 installed does not verify server connectivity. No software/service/firewall/credential configuration was changed.

Neither retained Phase 4B database, any institutional database nor an assumed existing Phase 4C database was contacted. The user was asked whether a fresh explicitly disposable D15 target already exists; no target identity or private process configuration is available to the runner at this report's stop point. Any later reply requires a new explicit identity/safety review before database use.

## 3. Configuration and migration inspection

Read actual models, six migration revisions, `backend/database.py`, `backend/migrations/env.py`, safety helpers, relevant D8-D14 reports/tests and the development documentation standard. The inspected chain is:

```text
4a_0001 -> 4c_0001 -> d9_0001 -> d11_0001 -> d12_0001 -> d13_0001
```

There is no D10 database migration: V2's checkpoints/results remain separately versioned file storage, with database-backed confirmation provenance and guarded reads. A PostgreSQL test must verify those links and boundaries rather than claim checkpoints became PostgreSQL rows.

| Revision | Added tables | Acceptance obligations |
|---|---:|---|
| 4a_0001 | 3 identity/session tables | Real authentication/session/binding FK and unique constraints; no institutional identities |
| 4c_0001 | 7 academic tables | Stable identities/revisions, scope/term FKs, timezone/calendar containment, advisory writer gate, read-only repository and empty-only downgrade |
| d9_0001 | 3 confirmation ledger tables | Deferrable head FK, revision/event links, immutable history, guarded head/event transitions and record indexes |
| d11_0001 | 2 adjustment tables | Owner/faculty FKs, active duplicate key, operation/event uniqueness, immutable content/history and allowed transitions |
| d12_0001 | 1 Chair decision table | Request/revision bindings, final decision uniqueness, independent actor/department authority and immutable decisions |
| d13_0001 | 3 publication/application tables | Version lineage, current head, request/decision/application uniqueness, FKs, transactional application/head transitions and immutable prior versions |

Expected fully upgraded inventory: **19 application tables plus `alembic_version` = 20**, from static models. This is not an observed live inventory. Phase 4C alone expects 11 including identity and `alembic_version`; its original inventory assertion would fail on a database already upgraded through D13.

Runtime identity access uses explicit `DATABASE_URL`; it is not invoked here. Bare Alembic CLI also reads `DATABASE_URL` when no caller-owned connection is provided. **Do not use bare `alembic upgrade head` for D15.** Future acceptance must create an engine only after an exact D15 gate and pass its verified connection through `Config.attributes['connection']`; the existing Alembic environment then has no URL fallback. No production environment variable/file needs to be edited.

## 4. Original Phase 4C tests

Fresh `--collect-only` located **17 exact cases** in `backend/tests/academic/test_academic_postgresql.py`. The command's output contains all case IDs, also copied into the manifest. Collection imports definitions but executes no fixtures/test bodies.

**PostgreSQL execution counts: 0 passed, 0 failed, 0 execution-skipped; 17 BLOCKED / NOT RUN.** These are not 17 newly observed pytest skips and not 17 acceptance passes.

Coverage prepared by those cases: revision/inventory; five parametrized direct identity/revision mutations; calendar containment/year shrink; timezone/archive/delete/truncate guards; cross-term/offering keys; populated downgrade refusal; failed DDL rollback; concurrent writer/rollback/retry; higher-isolation rejection; read-only snapshot/no default term; empty downgrade/upgrade identity preservation; calendar race; locked parent/inactive child rejection.

Their helper accepts only `ccs_ga_phase4c_test`, restricted `ccs_ga_phase4c_tester`, explicit `127.0.0.1:5432`, no query overrides, `PHASE4C_TEST_DATABASE_URL`, exact approval token and explicit allow-connect. Initial inspection is SELECT-only/read-only with statement/lock/connect timeouts. It validates connected database/user/server/schema/read-only state, owner, nonprivileged role, memberships, schemas, relations/functions/types/extensions/default ACLs and database/schema grants. There is no `DATABASE_URL` fallback.

**Compatibility prerequisite:** this original exact gate intentionally does not accept a newly named D15 target. No constants, helper or existing tests were modified. Do not disguise a D15 URL as approved Phase 4C access, monkeypatch the original safety gate or execute the 17 on retained/populated state. A separately reviewed D15 harness must retain the original case assertions with its own exact target gate and proper fixture isolation, or a separately approved fresh original Phase 4C target is required. Neither option has been implemented/executed in this blocked phase.

## 5. D9–D13 PostgreSQL matrix

All rows below are **BLOCKED / NOT RUN online**. Fresh SQLite/offline results in section 9 are complementary regression evidence only.

| Area | Inspected implementation | Required independent PostgreSQL evidence |
|---|---|---|
| D9 confirmation | `confirmation_models.py`, `external_confirmation_service.py`, `confirmation_authority_service.py` | Fictional proposal/confirmation persistence, exact current-head event chain, concurrent confirms, duplicates, revoke/supersede, FK/index/immutability guards, rollback and fresh-process reads |
| D10 V2 | `ga_v2_constraints.py`, `ga_v2_service.py`, versioned store | Actual `LOCK TABLE public.gec_records, public.gec_revisions, public.gec_events IN SHARE MODE`; independent writer blocks/times out then proceeds after release; complete current-head snapshot; revoked/superseded set rejects publication/resume; file provenance preserved |
| D11 request | `adjustment_models.py`, adjustment services | Owner-before-request row locking, active-key/idempotency/event uniqueness, submit/withdraw transitions, stale revision rejection, competing updates, rollback and restart |
| D12 Chair | `chair_models.py`, Chair authority/review services | Independent department mandate, one final decision per request/revision, contradictory concurrent commands, stale schedule rejection, immutable decisions, revocation/rollback and restart |
| D13 application | `application_models.py`, application/published-source/version services | Valid approval plus independent publisher, current-head serialization, complete current constraints, competing publication/application, exact one-meeting delta, rollback of audit/version/head together, immutable prior version and restart |

Static source uses PostgreSQL `FOR UPDATE` row locks and D10/D12 GEC SHARE locks. D12 applies local 2-second lock and 10-second statement timeouts. Actual blocking/SQLSTATE/isolation/deadlock behavior has not been observed on PostgreSQL here. SQLAlchemy compilation or SQLite's BEGIN IMMEDIATE cannot prove those guarantees. Future concurrency tests must coordinate genuinely independent connections with bounded barriers/timeouts and inspect database-enforced invariants, not merely execute two sequential API calls.

## 6. Migration and downgrade execution plan

Only after target/role identity and explicit disposability are independently verified:

1. Establish a fresh exact-gated test target. Require expected database/role/server/owner/public schema, no memberships/privileged flags/foreign grants and pristine inventory before any write. Revalidate immediately before using the verified caller-owned connection.
2. Apply `4a_0001`, then `4c_0001` in the academic acceptance fixture. Inspect actual keys, indexes, nullability and compiled PostgreSQL triggers/functions; run the academic assertions with synthetic records only. Keep this fixture isolated from the D9-D13 full-chain inventory.
3. In the dedicated full-chain fixture, upgrade through `d9_0001`, `d11_0001`, `d12_0001`, `d13_0001` using the caller-owned connection. Inspect all 20 expected tables and relationships after each revision. No seed/import of academic CSVs or default real accounts.
4. Empty downgrade/upgrade and injected failed-upgrade cases require an independently provisioned and verified rollback fixture. Do not downgrade an existing database or shared populated full-chain fixture. Populated downgrade refusal must verify that all synthetic rows survive rejection. Do not weaken migration history or remove data to make a downgrade pass.
5. Close/dispose owned pools and restart only owned application/test processes, then authenticate/retrieve histories through a fresh process. Do not restart PostgreSQL or unrelated services. Record exact transaction isolation, outcomes, row counts/digests and sanitized SQLSTATEs.
6. Preserve failed diagnostics and leave disposable stores for review; no automatic drop/reset/truncate/reseed or migration downgrade as cleanup. Unexpected target/schema/data/lock behavior stops the relevant test operation.

No live D15 harness, migration runner or PostgreSQL fixture was created in this blocked environment. This sequence is a requirement for the next authorized execution, not a claim that existing SQLite tests already implement it.

## 7. Proposed disposable target and permissions

Proposed names only, **not created and not verified absent**:

- Main database `ccs_ga_d15_test`; restricted owner/login `ccs_ga_d15_tester`.
- Independently approved rollback fixture later: `ccs_ga_d15_rollback_test` and its separate restricted owner `ccs_ga_d15_rollback_tester`.
- IPv4 `127.0.0.1`, port `5432`, schema `public`; dedicated process-only `D15_TEST_DATABASE_URL`, with no fallback to `DATABASE_URL` or either Phase 4B variable.

An authorized maintenance administrator needs permission to create roles/databases and assign the new owner. The test role needs LOGIN and ownership/CREATE rights only within its new disposable database/public schema; no SUPERUSER, CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS or role memberships. Do not grant access to retained databases or modify their ACLs. Database ownership is necessary for migration testing and does not qualify this role for production runtime use. Admin/superuser bypass remains outside application invariants.

If existing authorized pgAdmin access is used, keep its current administrator registration and password/authentication configuration unchanged. Provisioning and a privately chosen **new test-role password** can use that authorized session later; the forgotten administrator password need not be reset for this task. Do not type passwords in SQL history, record them in screenshots, paste them into chat or save connection URLs in the repository. A private terminal's environment is not automatically inherited by this execution process.

The main and rollback names are distinct from all Phase 4B and the original Phase 4C targets. Existing objects with either proposed name must trigger ownership/data review, not automatic reuse or reset. Password authentication over the new role's actual IPv4 connection must eventually pass a read-only identity gate; a working administrator session over IPv6 alone does not establish the intended IPv4 target.

## 8. Next user action — read-only existence review

First establish whether the proposed main objects exist, using an already authorized administrator session on the **verified `postgres` maintenance database**, not an institutional database. This query is supplied for user review; **Codex did not execute it**:

```sql
BEGIN READ ONLY;
SELECT current_database() AS database,
       current_user AS connected_role,
       host(inet_server_addr()) AS server_address,
       inet_server_port() AS server_port,
       current_setting('transaction_read_only') AS read_only,
       version() AS server_version,
       EXISTS (SELECT 1 FROM pg_roles
               WHERE rolname = 'ccs_ga_d15_tester') AS d15_role_exists,
       EXISTS (SELECT 1 FROM pg_database
               WHERE datname = 'ccs_ga_d15_test') AS d15_database_exists;
ROLLBACK;
```

Return only sanitized identity/version/read-only/existence results, without passwords or connection URLs. If either object exists, stop for ownership/data review. If both are absent, review exact GUI provisioning and private credential steps before creation. This phase has no configured authorized administrator connection and therefore cannot itself establish absence or perform provisioning. Do not run migration commands, enable approval flags or connect using the new test role until the target exists and its new exact-gated D15 workflow has been reviewed.

## 9. Fresh regressions, separate from PostgreSQL

The runner strips all database connection variables and approval flags and selects only existing offline/owned SQLite suites. Original PostgreSQL tests are a collect-only selection. All commands use new owned basetemp paths and never overwrite prior evidence.

| Selection | Fresh D15 result | Scope |
|---|---:|---|
| Academic offline | 85 passed | Fake safety catalogs, in-memory SQLite constraints/planner/repository and offline PostgreSQL SQL |
| D2-D9 backend | 327 passed | Existing metadata/intake/review/verification/confirmation APIs with fictional providers and isolated storage |
| V2 engine | 30 passed | Original operators, admission/reset, file provenance/checkpoints, exact continuation; no PostgreSQL |
| V2 API | 18 passed | Fictional current-head/authority and isolated SQLite/API behavior |
| D11 backend/migration | 33 passed | Ownership, transitions, concurrency, fresh process, offline DDL |
| D12 backend/migration | 42 passed | Independent Chair, contradictory decisions, restart and offline DDL |
| D13 backend/migration | 47 passed | Independent publisher, versions/rollback/concurrency and offline DDL |
| D14 continuous backend | 6 passed | Actual fictional confirmation through GA/request/Chair/application using SQLite and an explicit test-only publication provider |
| Original PostgreSQL module | 17 collected only | No fixtures/test bodies executed; 17 BLOCKED / NOT RUN |

**588 freshly executed offline/SQLite cases passed; zero failed.** Counts exclude the 17 collected IDs. These do not add historical D14 passes or convert SQLite concurrency into PostgreSQL evidence. Exact final totals are verified by the manifest audit after the selected runs complete.

Warnings retained: existing Alembic missing `path_separator` configuration deprecations; Starlette/httpx TestClient and anyio BlockingPortal deprecations in HTTP-test selections. No warning suppression, dependency upgrade or broad cleanup. No new failure was erased. Earlier D14 failures remain in their original committed evidence, untouched.

Frontend contracts/build/lint and real/synthetic browser suites were **NOT RUN in D15**: no frontend/application implementation changed and no safe PostgreSQL-backed browser environment exists. Their D14 results remain historical. Existing D9 browser teardown flakiness remains documented and is not claimed fixed by these backend runs.

## 10. Defects, security, preservation and files

Confirmed PostgreSQL compatibility defects: **none reproduced**, because PostgreSQL was not accessed. No migration, runtime model, security policy or V1/V2 implementation was changed. The original target-gate mismatch and bare Alembic URL path are setup constraints, not newly proven defects.

Evidence is filtered before writing, then independently scanned for complete/truncated signed receipts, shorter fragments, session/bearer/header values, credentials, connection URIs and private keys. Decoded JSON/output/error fields and new documentation are inspected; private faculty names are compared locally without exporting them. No screenshots, browser trace, raw database, raw checkpoint, authenticated response or private provider payload is archived. Only variable presence, public service metadata and fictional test summaries are retained.

All **1295 pre-existing baselined files** must remain byte-identical, including all **23 academic data files**, protected `backend/data/faculty_preferences.json`, V1/V2/operator/scoring/RNG sources, checkpoint/saved-result/history trees, D8-D14 evidence and Git index. The protected preferences retain their pre-existing local modification without being touched, restored, staged or committed. The final audit checks the complete baseline and exact new-file scope; hashes establish artifact identity, not database correctness.

Created only:

- `docs/dashboard-d15-postgresql-acceptance.md` — this blocked acceptance report and safe next-step plan.
- `docs/testing/dashboard-d15/preservation-baseline.json` — before-test hashes, including current protected preference bytes and Git index.
- `docs/testing/dashboard-d15/environment-inspection.json` — presence-only settings and public service/runtime metadata.
- `docs/testing/dashboard-d15/static-inspection.json` — actual model table names and migration dependency inventory.
- `docs/testing/dashboard-d15/run_offline_checks.py` — credential-stripped, offline/SQLite-only selections plus collect-only PostgreSQL IDs.
- `docs/testing/dashboard-d15/audit_evidence.py` — preservation/privacy/test-count/artifact-hash verification and manifest generation.
- Unique timestamped command records and `docs/testing/dashboard-d15/manifest.json` — sanitized observations and raw-byte hashes; manifest excludes itself.

**Existing files modified: none.** No application/schema/GA/data/production configuration change. Genuine institutional evidence/confirmation/Chair/publication providers remain BLOCKED; fictional test providers remain confined to fixtures. No PostgreSQL, Phase 4B, production service, OS authentication/firewall or Git write operation occurred.

## 11. Remaining acceptance and stop

Online migrations, Phase 4C's 17 cases, D9-D13 PostgreSQL transactions/guards/concurrency/locking and real PostgreSQL restart/recovery are all **BLOCKED / NOT RUN**. Server version/configuration, isolation, row-lock/SHARE-lock outcomes, SQLSTATEs and production persistence cannot be certified from this report. SQLite/offline successes support regression preservation only.

Recommended next action is the sanitized maintenance existence check in section 8, followed by separately reviewed provisioning/private test-role setup and a dedicated exact-gated D15 harness. Do not reuse an unknown database, weaken the Phase 4C gate or launch the normal application against an unverified URL. D15 remains incomplete until actual PostgreSQL results are recorded.

**Stop:** database operations are blocked pending safe environment setup. No automatic commit/push, D16, cleanup, C++ work, institutional provider activation or scheduling-input change.

## 12. Continuation: user-confirmed provisioning; credential access still blocked

The user subsequently reports a disposable PostgreSQL 18.6 database `ccs_ga_d15_test`, owned by `ccs_ga_d15_tester`, with actual pgAdmin IPv4 host/port and both session/current users verified. The role is LOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, connection limit 20. This is **USER CONFIRMED**, not a Codex connection observation. Earlier absence-of-provisioning statements above retain their initial-inspection meaning; provisioning is no longer the reported blocker.

The same role can CONNECT to an existing non-D15 development database. The new acceptance guard must therefore validate actual database identity on every connection as well as session/current user, server address/port, owner, privileges and expected object inventory before admitting migrations, fixtures, recovery or any cleanup. Administrator sessions, unverified targets and unexpected objects must fail closed. Existing original Phase4C gating is not a D15 guard and has not been repurposed.

Readiness inspection found no `D15_TEST_DATABASE_URL`, D15 approval flag, Phase4C credential or configured password-file handoff in this execution process. No private credential stores were searched. A working pgAdmin login does not expose its password to this tool process. Per the user's explicit stop condition, PostgreSQL operations remain paused before connection: **zero new PostgreSQL tests or operations**. The earlier 588 offline/SQLite passes remain previously recorded results, not reruns in this continuation.

Next action is private local credential setup using the existing Get-Credential/process-local environment workflow. The password must be entered only into the user's credential prompt, never chat or a repository file. Keep a dedicated PowerShell terminal open: future gated commands must execute there because setting its environment does not configure the Codex tool process. This setup only prepares credentials; it must not launch bare Alembic, the application or the original Phase4C suite. No new test-target guard or PostgreSQL acceptance implementation has been executed. Detailed connection readiness is in `docs/testing/dashboard-d15/credential-readiness.json`.

No application, academic data, GA source, checkpoint or historical evidence changed. No database permissions, roles, cluster authentication or production configuration were changed. No staging, commit, push or next milestone occurred.

## 13. Dedicated read-only guard — offline verified, live execution pending

The user confirms the private PowerShell terminal is ready. Its environment is not inherited by Codex tools, and no attempt was made to inspect another process's credentials. The new entry point is intentionally limited to one SELECT-only pristine-target preflight. No migrations, acceptance fixtures, writes, object cleanup or normal application launch are exposed by it.

Created `docs/testing/dashboard-d15/d15_target_guard.py`, `preflight.py` and `test_d15_target_guard.py`; extended the offline-only runner and evidence audit. No existing backend, migration, Phase4C gate or GA source was modified.

The new guard accepts only the dedicated D15 variable and pins database `ccs_ga_d15_test`, role `ccs_ga_d15_tester`, host **and hostaddr** `127.0.0.1`, port `5432`. It rejects fallback variables, administrator usernames, alternative databases, missing passwords and URL query overrides before connecting. Driver options explicitly enforce transaction read-only, public/pg_catalog search path, connection/statement/lock/idle timeouts and a fixed application name.

Actual connected database, session user, current user, address, port, owner, public schema, read-only mode, role LOGIN/connection limit 20, nonprivileged flags, effective database/schema permissions and PostgreSQL major version 18 must pass. It rejects role memberships, nonstandard schemas/owners, relations, routines, standalone types, extra extensions, default ACLs, large objects, foreign servers/user mappings, event triggers, database-specific settings and unexpected database/schema grants. It does not revoke privileges or modify any object when rejected. The fact that the tester can CONNECT elsewhere does not authorize using those databases.

Fresh final result: **84 offline guard tests passed, zero failed**, including actual-identity mismatches despite apparently valid configuration, forbidden targets, role/grant/object branches, SELECT-only catalog access, rollback/connection close, driver-error redaction and safe CLI argument/result handling. Earlier intermediate guard selections of 79 and 83 also passed and are retained, not added to the final count. Fake DBAPI catalogs and blocked real connectors are explicitly test-only; they do not prove the live catalog SQL succeeds. The earlier 588 D15 offline/SQLite passes were not rerun in this continuation. No new frontend/browser/build run is applicable.

Run only this command in the already configured **same private terminal**, from the repository root:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-d15/preflight.py --read-only
```

The command first verifies the pre-existing repository preservation baseline, then opens only the explicit D15 connection. It rolls back/closes, checks preservation again, writes a unique sanitized `*-read-only-preflight/result.json` and prints only public identity/status/error fields and the evidence path. It never prints the password or connection URL. Do not pass credentials as arguments, run bare Alembic, use an administrator connection or retry a rejection automatically. Return its public JSON result; any rejection must be reviewed before proceeding.

Expected status is `READ_ONLY_PREFLIGHT_PASSED`, with matching database/session/current user/owner/address/port and `read_only=true`, `empty=true`, `writes_performed=false`. As of this report **no PostgreSQL connection or live preflight has been executed by Codex**, and the original 17 PostgreSQL cases plus D9-D13 acceptance remain NOT RUN. A subsequent writing harness must use the same actual-identity verification on **every** migration, fixture, recovery and any cleanup connection, with explicit expected schema-state profiles and no ungated factory or fallback. That write-path enforcement is still required before any write and is not claimed implemented by this read-only module.

## 14. Read-only preflight passed; controlled write phase prepared

The user executed the read-only command in the private terminal. Codex inspected the actual [saved result](testing/dashboard-d15/20261025T153542972324+0800-read-only-preflight/result.json): PostgreSQL **18.6**, database `ccs_ga_d15_test`, session/current user and owner `ccs_ga_d15_tester`, host `127.0.0.1`, port `5432`, public schema, read-only transaction, empty inventory and verified role restrictions; no writes. Attribution is **LOCAL_OPERATOR_EXECUTION**, not a Codex database connection or an acceptance-test pass. The original result bytes remain unchanged.

### Write-path enforcement

New `d15_write_guard.py` owns a dedicated engine and checks the actual connected identity, role flags, required privileges and expected academic object profile at physical connection admission, pool checkout, transaction start, every non-control statement and commit. Fresh physical connections start read-only; write mode is enabled only after verification and rechecked afterward. The target remains hard-pinned by both host and hostaddr, database and role; the engine carries no credential URL. NULL pooling means every new physical connection is verified, including independent connections used by concurrency assertions.

The initial control connection must pass a fresh pristine inventory check and acquire a cooperative session advisory run lock before the run becomes active. It verifies pristine state again after acquiring the lock. A populated target is not automatically reused. This lock coordinates owned test runners; it does not prevent a privileged administrator or another uncooperative database owner from changing the database.

While the owned runner is active, an in-process psycopg2 barrier rejects connection attempts outside the controlled creator and rejects mismatched driver parameters before contacting a server. Migrations receive only the guarded caller-owned SQLAlchemy connection. Test fixtures receive the same guarded engine. No acceptance connection uses `DATABASE_URL`, a Phase4B/Phase4C variable or libpq address/password defaults. The runner excludes those environment values from the child. The original 17-test module's `pg_engine` factory and safety gate are not invoked or modified.

Statement checks reject database/role/authentication/extension/foreign-server/schema operations, unsupported settings, role/search-path switching, unapproved objects and unrelated cleanup targets. Normal savepoints, rollback-to-savepoint and exact read-only transaction controls remain available without a guard SELECT preceding a transaction-mode change. These controls cannot change database/role/host and operate only on an already admitted connection. Rollback/close release only owned resources; all tracked connections must close before a successful final status. No cleanup DDL, reset, drop database or reseed is implemented.

The mid-run profile permits only the identity/academic/Alembic tables and their automatic indexes/composite types, plus the three frozen academic functions and expected triggers. It rejects unrelated relations, owners, routines, types, triggers, grants, extensions and external resources. It deliberately **does not admit D9-D13 schema objects** in this first phase. The guard is an enforcement boundary for this trusted fixture harness, not a sandbox for malicious Python code or an administrator with DDL privileges.

### Exact controlled scope and original-case reuse

`test_phase4c_d15.py` imports the **unchanged original test callables and parametrization** from `backend/tests/academic/test_academic_postgresql.py` in original definition order and supplies only a new D15 `pg_engine` fixture. The original `pg_rows` rollback fixture is reused. No approval token is set for the original Phase4C suite, and its exact safety constants are untouched. Fresh collection produced the same 17 case suffixes in the same order, and a unit test verifies callable identity rather than a reimplementation of the assertions.

The new fixture starts only through `run_phase4c.py --execute`. On its freshly verified empty D15 target, it upgrades only through **`4c_0001`**, then executes those 17 assertions. The original empty-table downgrade/upgrade tests operate on tables created by this run, inside rollback-only test transactions. They are not cleanup, do not affect retained institutional data and do not downgrade identity tables. This first phase uses only the already authorized D15 database; it does not create or connect to the earlier proposed separate rollback target. After completion or failure the schema remains for review; no automatic retry/reset/recovery provisioning is exposed.

`d15_phase4c_plugin.py` records exact case IDs/outcomes, phase, exception class and public safety code/SQLSTATE without serializing exceptions, SQL parameters, credentials or locals. The parent captures and sanitizes stdout/stderr before writing, verifies repository preservation before and after execution, and requires exactly 17 passes, no skips/errors and successful owned-connection cleanup for `ACCEPTANCE_PHASE_PASSED`. It uses a finite 300-second child-process deadline, `-x`, no traceback/local dump and unique evidence/temp directories. Failure, deadline or preservation discrepancy yields `STOP_REVIEW_REQUIRED`; state is retained and no retry occurs automatically.

### Fresh offline verification and next command

Latest combined selection: **243 passed, zero failed**. It includes the original 84 read-only guard cases, so they are not added again. Earlier development selections (195, 229, 232 and 234) passed and remain archived; only the latest count is authoritative. Tests cover wrong database/role/host/port at physical, checkout, begin, statement, migration, fixture, cleanup and commit boundaries; wrong factory configuration before driver contact; forbidden session/cluster/foreign-schema operations; changed catalog/owners/grants; final connection cleanup; driver barrier; engine callback wiring; the actual frozen upgrade/downgrade SQL compiled offline; original assertion reuse; child environment isolation; and sanitized CLI/evidence failure handling. No actual PostgreSQL writes were executed by these fake-DBAPI tests.

Created: `docs/testing/dashboard-d15/d15_write_guard.py`, `test_d15_write_guard.py`, `test_phase4c_d15.py`, `d15_phase4c_plugin.py`, `run_phase4c.py`. Extended only D15 tooling: the target verifier accepts an explicit read-only-mode expectation for guarded write transactions while preserving its strict default; the offline runner, audit, report and manifest include this handoff. Existing application, migration, academic test, GA source, data and D14 evidence files remain unchanged.

In the **same existing private PowerShell terminal**, from the repository root, execute:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-d15/run_phase4c.py --execute
```

**This is write-enabled acceptance**, not another read-only probe. It will freshly gate D15, migrate through the seven-table academic foundation and run the original 17 cases. Return only the printed public JSON summary/evidence path. On `STOP_REVIEW_REQUIRED`, do not retry, reset, remove tables, change privileges or run another migration; review the retained result first. D9-D13 PostgreSQL migration/workflow/concurrency acceptance remains pending and will require an explicitly expanded guarded schema profile and fixtures after the first-phase results are known. No D16, institutional authority activation, staging, commit or push is authorized.

## 15. Phase4C evidence reviewed; retained-schema D9-D13 handoff

### Actual PostgreSQL evidence, executed by the operator

Inspected the unchanged [command record](testing/dashboard-d15/20261025T160918219600+0800-phase4c-postgresql/command.json), [case outcomes](testing/dashboard-d15/20261025T160918219600+0800-phase4c-postgresql/pytest-results.json) and [guard summary](testing/dashboard-d15/20261025T160918219600+0800-phase4c-postgresql/connection-guard-summary.json). The command ran 2026-10-25 16:09:18.219600 to 16:09:33.491277 +08:00: **17 passed, zero failed/errors/skipped/not-run**, exit 0, pytest 13.10 seconds, runner 15.268 seconds. All 17 case suffixes/order match the collected original academic test cases. This is inspected **LOCAL_OPERATOR_EXECUTION**, not a fresh Codex execution or browser result.

The original assertions cover exact inventory/revision; immutable identity/revision fields; calendar containment/year shrink, timezone/archive/delete guards; cross-term foreign keys; populated downgrade refusal; failed-upgrade transactional rollback; concurrent writers/retry; isolation restrictions; read-only snapshots/no default term; rollback-only empty downgrade/upgrade; calendar races and locked-parent protection. The fixture reuses original callables and rolls back fictional per-case rows. It retains revision `4c_0001` and all eleven tables including Alembic/identity tables.

The guard recorded **22 physical connections, 370 identity checks, 314 guarded statements**, owned connections closed, schema retained and no cleanup DDL. There are **three emissions of one Alembic deprecation**: absent `path_separator` uses legacy splitting of `prepend_sys_path`. The messages are present in this artifact; no warnings were suppressed or attributed to another dependency. This does not establish production readiness or the later workflow migrations.

### Retained-schema safety and compatibility

`d15_workflow_guard.py` introduces a separate `WorkflowRun` profile. The pristine first-phase guard remains the default. Entry uses a read-only connection, exact actual D15 identity/role/owner/address/port/restrictions, a strict public object inventory and revision **exactly `4c_0001`**. It checks the complete column name/type/length/nullability contract, complete constraint/index name inventory and validated constraints, exact frozen academic function bodies/configuration and enabled trigger inventory. All ten non-Alembic fixture tables must still be empty; unexpected rows, objects, owners, grants or revision cause rejection. It does not reinterpret populated targets as disposable.

It captures a canonical catalog fingerprint of the retained tables' columns/defaults, constraint definitions, indexes, trigger definitions/enabled state and function bodies/settings. This metadata must be identical after obtaining the owned lifetime session advisory lock, at every later non-control statement/commit/physical connection boundary, and after the test suite. The seven academic tables must remain empty. The metadata artifact contains no row payloads. Initial checks compare named contracts and frozen functions; they are compatibility checks, not a forensic proof of a database's entire creation history.

Every subsequent connection inherits the existing exact driver barrier, read-only-first physical admission, checkout/begin/statement/commit identity checks, owned connection tracking and whitelisted environment. No `DATABASE_URL`, Phase4B/Phase4C URL or libpq default is inherited. Alembic receives only a guarded caller-owned connection. The same guard covers real authentication/API sessions, fresh ledger reads, worker-thread V2 authority reads, race participants, migrations, recovery and teardown verification.

The expanded phase admits only frozen, reviewed additive D9/D11/D12/D13 upgrade DDL. It rejects other CREATE/ALTER, all DROP/TRUNCATE, academic DML and unreviewed DO programs. Existing cluster/role/authentication/schema/foreign-target restrictions remain. The known populated-downgrade refusal DO checks are admitted, but destructive downgrade statements remain forbidden. No automatic reset, drop, truncate, reseed or cleanup is implemented. The cooperative run lock cannot prevent an uncooperative privileged administrator from changing the target; this remains a trusted acceptance harness rather than a hostile-code sandbox.

### Prepared PostgreSQL cases: ten, NOT RUN

`test_workflows_d15.py` is deliberately ordered, uses `-x`, and cannot start without the controlled private-terminal runner. Collection verifies all ten exact case IDs/order. One retained workflow fixture uses fictional resources/accounts/providers and real application services. It does not run SQLite metadata creation/trigger substitution on PostgreSQL.

| Case | Required actual PostgreSQL assertions |
|---|---|
| 01 | Read-only retained-schema gate; real `4c_0001 -> d9_0001 -> d11_0001 -> d12_0001 -> d13_0001` upgrade in a rolled-back transaction; repeat with a real divide-by-zero SQL failure and verify rollback; then commit additive upgrades. Verify all twenty tables, functions/triggers, retained catalog and validated constraints. No downgrade/drop/reset. |
| 02 | Real authenticated GEC proposal, confirmation and replacement revision; competing API confirmations produce one winner and one stale rejection; independent ledger session reconstructs the current head. |
| 03 | Real PostgreSQL immutability triggers; independent `FOR UPDATE` connections cause actual SQLSTATE `55P03` under a bounded local lock timeout, then succeed after lock release; populated D9 downgrade refuses before any DROP. |
| 04 | Real V2 generation with fresh PostgreSQL-backed ledger authority and fictional mappings; generated proposal binds the current confirmed revision. V2 artifacts use a new owned temporary store. |
| 05 | Authenticated owned adjustment creation, idempotent replay and submission; different faculty and anonymous reads denied. |
| 06 | Competing Chair approvals produce one immutable decision; generated schedule bytes remain unchanged. Fictional independent mandate only; actual trust check restored. |
| 07 | Application failure after audit insert rolls back versions/head/audit; synthetic storage exception returns sanitized 503 with no partial publication. These injected exceptions are not a physical PostgreSQL outage. |
| 08 | Competing application transactions publish exactly once; replay of the successful operation is idempotent; two versions/one head/one application retained. |
| 09 | PostgreSQL publication/decision/event immutability; request-chain verification in a new session; faculty sees only its own versioned assignments; original generated bytes unchanged. |
| 10 | Authorized fictional GEC revocation invalidates the previously pinned V2 scope, while immutable publication history and generated bytes remain intact. |

The migration rehearsals roll back newly added D9-D13 DDL only; retained Phase4C is never downgraded. After a successful run, revision `d13_0001`, all twenty tables and all new fictional accounts/sessions/ledger/request/decision/publication rows are retained. A second automatic execution is not supported: the entry gate will reject the changed revision/populated fixture tables. After a failure, preserve state and review the failing phase before any new command.

### Fresh preparation verification and retained failures

Latest combined guard selection: **343 passed, zero failed**. This includes the prior 243 cases; counts are not added twice. New cases prove wrong actual database/role/host/port rejection across all execution boundaries, retained revision/object/column/nullability/constraint/index/function/security/search-path/trigger/row checks, changed-catalog rejection, unchanged pristine defaults, academic-write/destructive-DDL rejection and admission of the real frozen upgrades. Real connectors are blocked in these unit tests. Earlier 342-pass preparation output remains historical.

New workflow-fixture rehearsal: **7 passed, two warnings**, using a new owned fictional SQLite database and in-process FastAPI TestClient, with psycopg2 blocked. It executes actual V2 generation and service workflows but **does not validate PostgreSQL migrations, PostgreSQL trigger bodies, row locking or browser behavior**. Two dependency warnings identify deprecated Starlette HTTPX TestClient support and AnyIO's `BlockingPortal` alias. No dependency or application change was made.

Two failed rehearsal records are preserved: the initial socket-connect prohibition blocked Windows asyncio's internal socket pair during fixture setup; the next run had six passes and an assertion expecting HTTPException where the real V2 authority raises `ConstraintError`. The test now asserts the exact `CONFIRMATION_NOT_CURRENT` code. Corrections were limited to the new D15 rehearsal/assertion code; no production defect was reproduced. The final rehearsal passed. Collection separately found the exact **ten PostgreSQL cases**, without running their fixtures.

Created D15 tooling: `d15_workflow_guard.py`, `workflow_fixture.py`, `test_workflows_d15.py`, `d15_workflow_plugin.py`, `run_workflows.py`, `test_d15_workflow_guard.py`, `test_workflow_rehearsal.py`. Extended existing D15-only `d15_write_guard.py` with explicit profile parameters while preserving default behavior, `run_offline_checks.py`, `audit_evidence.py`, this report and the manifest. Unique per-command evidence directories preserve all original records. No application or original test/migration file changed.

### Next private-terminal command

From the repository root in the **same privately configured PowerShell terminal**:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-d15/run_workflows.py --execute
```

The command checks repository preservation before/after, privately reads only `D15_TEST_DATABASE_URL`, runs the retained-schema read-only gate before enabling writes, then performs the above controlled migration/workflow acceptance. It creates unique sanitized command, exact case-outcome, retained/upgraded catalog and owned-connection records, with a finite 600-second child deadline. It emits only a public summary/evidence path. Do not send credentials or raw sessions. **On any rejection or `STOP_REVIEW_REQUIRED`, stop; do not retry, reset, clean tables, change privileges or run bare Alembic.** Return the public summary for review.

Remaining limitations: D9-D13 PostgreSQL acceptance is NOT RUN; actual retained-schema compatibility must pass on the live target. Recovery here covers transactional rollback, lock release and a synthetic storage failure, not service crash/restart, physical outage or cross-process recovery. No new browser/build run is needed for D15-only tooling. Genuine institutional providers remain blocked. The seventeen academic cases are now verified through operator evidence; they are no longer described as unexecuted. Protected data/GA/checkpoints/schedules and all 1,295 baselined files remain byte-identical as verified by the manifest audit. No PostgreSQL connection was attempted by Codex, no Git mutation occurred, and no D16 or C++ work began.

## 16. PostgreSQL18 NOT NULL inventory correction; guarded resumption prepared

### Preserved failure and read-only diagnosis

The operator's [20261025T163206495077+0800 workflow run](testing/dashboard-d15/20261025T163206495077+0800-workflows-postgresql/command.json) exited 1. Its [outcomes](testing/dashboard-d15/20261025T163206495077+0800-workflows-postgresql/pytest-results.json) record `test_01_additive_upgrade_atomic_rollback_then_commit` as a **setup ERROR**, SafetyError code `RETAINED_CONSTRAINT_CONTRACT_MISMATCH`, with nine NOT_RUN cases. The [guard summary](testing/dashboard-d15/20261025T163206495077+0800-workflows-postgresql/connection-guard-summary.json) records one physical control connection, one identity check, zero guarded statements, successful owned connection closure and no cleanup DDL. The read-only entry check failed before engine construction, advisory run lock, write-mode activation, migrations or fictional seeding. No workflow test body executed. The original traceback was not captured (`--tb=no`); the call path was established from source, not reconstructed as original terminal evidence. All three failure artifacts remain byte-identical and are now indexed in the manifest.

The user then executed the explicitly READ ONLY diagnostic in the private terminal and reported PostgreSQL18.6, exact D15 database/session/current user/host/port, revision `4c_0001`, ten empty fixture tables, and verified rollback/connection cleanup. Actual constraint categories: **76 NOT NULL, 11 primary key, 37 CHECK, 11 foreign key, 18 unique**. All reported missing/unexpected NOT NULL and other-constraint differences were empty; none were unvalidated or unenforced. These results are archived as an explicitly [USER_REPORTED supplement](testing/dashboard-d15/operator-pg18-diagnosis.json), not a raw independently captured terminal result. Original diagnostic timestamps were not supplied and are not invented. Codex did not connect to PostgreSQL.

The D15 expected inventory covered declared SQLAlchemy constraints but omitted PostgreSQL18's table NOT NULL catalog entries. The old fake fixture built its inventory from the same expectation and therefore missed the server-version difference. The user-reported actual differences and the earlier memory-only PostgreSQL18-shaped reproduction establish a D15 guard defect, not a defective application migration. PostgreSQL18 introduced table NOT NULL rows in `pg_constraint` and the `conenforced` field. References: [official PostgreSQL18 catalog](https://www.postgresql.org/docs/18/catalog-pg-constraint.html), [official release notes](https://www.postgresql.org/docs/18/release-18.html), [PostgreSQL18 constraint deparser source](https://github.com/postgres/postgres/blob/REL_18_STABLE/src/backend/utils/adt/ruleutils.c). No database repair or migration reset is required by this diagnosis.

### Narrow correction

Only the D15 workflow guard's metadata reader/validator and supporting tests/evidence changed:

- `catalog()` reads the connected server version and retains each constraint's complete existing metadata plus enforcement flag and ordered column bindings from `conkey`/`pg_attribute`. A LEFT JOIN preserves unresolved bindings as invalid metadata instead of silently dropping them. NOT NULL rows, names, definitions, flags and bindings stay in the full catalog/preservation hash.
- The retained-schema validator requires exactly one PostgreSQL18 NOT NULL constraint for each expected non-null table/column pair. It checks that each binding contains exactly one recognized required column and that its deparsed `NOT NULL` definition agrees. It rejects missing/extra bindings, nullable/unknown columns, wrong tables, duplicate names or bindings, malformed rows, unresolved/repeated columns, inconsistent definitions, and non-boolean/false validation or enforcement flags.
- Other constraints must still match the exact expected name/type inventory; unexpected types or duplicate records fail closed. All constraint categories must be validated and enforced. No type-n records are simply ignored, no constraint/database operation is performed, and no scope/permission restriction is weakened.
- For pre18 catalog readers, the SQL uses literal TRUE for enforcement because those servers lack `conenforced`; required nullability remains checked through the complete column contract. Pre18 tables do not require PostgreSQL18-only NOT NULL catalog rows. Tests cover this helper compatibility, while the **actual D15 allowlist remains PostgreSQL18 only**, with the same exact database, role, owner, host and port.

The independent [fixture](testing/dashboard-d15/fixtures/pg18-constraint-inventory.json) has all 153 catalog-shaped constraint records. It was derived offline from the frozen 4a/4c migration DDL, not the guard's expected-inventory helper, and records the migration source hashes. NOT NULL constraint names are explicitly fictional; this is not a live catalog dump or institutional data. The validator uses actual table/column bindings rather than guessing PostgreSQL-generated names. The older compatible fake fixture now uses these independent constraint rows.

### Fresh verification

| Selection | Actual fresh result | Scope |
|---|---|---|
| `d15-workflow-guard` | **381 passed, zero failed**, 2.03s | All D15 target/write/workflow guard tests; includes prior 243 and 343 selections, not added twice. Connectors/network are blocked in unit tests. |
| `d15-workflow-rehearsal` | **7 passed, zero failed**, 8.61s; two warnings | New owned fictional SQLite/FastAPI/V2 rehearsal; psycopg2 blocked. Not PostgreSQL migration/trigger/locking or browser evidence. |
| `d15-workflow-collection` | **10 collected**, 0.93s | No fixture/test execution; the ordered PostgreSQL selection is unchanged. |

New regression cases cover the independent 153-record fixture/source hashes; missing/unexpected/nullable/wrong-table/wrong-column/multiple/duplicate/unresolved NOT NULL bindings; duplicate ordinary constraints; malformed metadata; incorrect definitions; unvalidated/unenforced flags across constraint types; unknown/mistyped/missing ordinary constraints; quoted valid definitions; every NOT NULL metadata field's contribution to hashing; no mutation/removal during validation; and pre18 catalog SQL compatibility. The two rehearsal warnings remain the existing Starlette HTTPX TestClient and AnyIO BlockingPortal alias deprecations. No dependency change was made. Earlier failures/passes and the 17-case Phase4C evidence remain historical and intact.

Exact existing D15 files updated for this correction: `d15_workflow_guard.py`, `test_d15_workflow_guard.py`, `audit_evidence.py`, this report, and `manifest.json`. New files: `fixtures/pg18-constraint-inventory.json`, `operator-pg18-diagnosis.json`, plus the three uniquely named guard/rehearsal/collection command records. No runner, application, original test, migration, target allowlist or credential-handling source changed. The audit recognizes the historical setup failure explicitly; passing privacy/hash inspection must not relabel that failed execution as acceptance success.

### Next command; not executed by Codex

In the **same existing private PowerShell terminal**, from the repository root:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-d15/run_workflows.py --execute
```

The command rechecks the retained `4c_0001` profile, now including PostgreSQL18 NOT NULL bindings, before any write. Only if all live checks pass does it run the previously prepared additive D9-D13 migrations and ten acceptance cases. The database is unchanged by this correction; no records were inserted. This is the next authorized operator handoff, not a claim that the corrected PostgreSQL run has passed. On rejection or `STOP_REVIEW_REQUIRED`, stop and return the public JSON; no automatic retry/reset/cleanup, permission change or bare Alembic command.

Preservation: all 1,295 baselined files, all 23 academic files including the protected preference modification, original GA/V1/V2/operator/fitness/RNG sources, migration files, checkpoint/history/schedule artifacts and Git index/HEAD remain unchanged. Prior evidence files remain intact; the manifest records current hashes for intentionally updated D15 tooling. Privacy scans include full/truncated receipts, credentials, tokens, decoded JSON and private faculty names without exporting those names. No PostgreSQL operation, browser run, staging, commit, push, D16 or C++ work was performed by Codex. Genuine institutional authority remains blocked, and D9-D13 PostgreSQL acceptance remains pending the corrected live run.

## 17. Exact driver transport, abort recovery and phase reporting

### Retest failure and user-confirmed recovery

The operator's [second workflow command](testing/dashboard-d15/20261025T170223852944+0800-workflows-postgresql/command.json) ran 17:02:23.852944 to 17:02:27.900833 +08:00, exit 1. Its original stdout records **one FAILED call plus one teardown ERROR**, nine other cases not run, and one existing Alembic configuration warning. The legacy [outcome JSON](testing/dashboard-d15/20261025T170223852944+0800-workflows-postgresql/pytest-results.json) incorrectly shows only one ERROR: it overwrote the call's exception type/status with teardown's AssertionError while retaining the call's `UNREVIEWED_WORKFLOW_DDL_REJECTED` safety code. This discrepancy is documented, not corrected by rewriting historical evidence.

The [entry catalog](testing/dashboard-d15/20261025T170223852944+0800-workflows-postgresql/retained-schema.json) proves that the PostgreSQL18 constraint correction passed the full read-only gate. Its 153 constraints include all 76 NOT NULL bindings with validation/enforcement. The [guard summary](testing/dashboard-d15/20261025T170223852944+0800-workflows-postgresql/connection-guard-summary.json) records three physical connections, 26 identity checks and 16 admitted statements, with owned connections closed and no cleanup DDL. No workflow fixture ran. The legacy unconditional `fictional_rows_retained=true` was not evidence of seeded rows.

Offline compilation identifies the primary rejection at D9 statement14, `CREATE FUNCTION d9_guard_event()`. The actual psycopg2 transport representation doubles the two `%ROWTYPE` markers to `%%ROWTYPE`; the former allowlist compared against uncompiled source SQL. The first thirteen D9 DDL statements preceded the rejection inside the first rollback rehearsal transaction. No complete D9 revision or migration commit was reached. Teardown then incorrectly demanded `d13_0001`, producing the secondary assertion. The original traceback/statement payload was not archived (`--tb=no`); this attribution combines the saved public code/counts with source inspection and actual dialect compilation. [SQLAlchemy documents this percent escaping](https://docs.sqlalchemy.org/en/20/faq/sqlexpressions.html#why-are-percent-signs-being-doubled-up-when-stringifying-sql-statements).

The user subsequently supplied the successful server-enforced READ ONLY diagnostic result: exact D15 target/role/address/port, revision `4c_0001`, retained guard passed, all ten fixture tables empty, catalog equal to the saved retest entry, no writes and successful connection cleanup. This confirms rollback of the failed transaction. The [recovery supplement](testing/dashboard-d15/operator-post-abort-diagnosis.json) is explicitly **USER_REPORTED**, not an independently captured terminal transcript; original execution timestamps are unknown. It hashes all four unchanged retest artifacts. No live diagnostic was repeated during this correction.

### Minimal D15-only correction

`d15_workflow_guard.py` now builds allowed transport strings by compiling only the trusted frozen migration statements with the **actual SQLAlchemy connection dialect**, requiring PostgreSQL/psycopg2/pyformat. The compiled sets are cached per dialect. Incoming CREATE/ALTER/DO statements must match the exact expected transport string; neither percent signs nor whitespace/literals are rewritten. DDL parameters, executemany, unexpected placeholders, altered bodies/identifiers/literal spacing, added comments/DDL and extra terminators are rejected. Source-mode offline validation still matches exact frozen source strings. All existing target, statement-policy and PostgreSQL18 constraint checks remain.

`test_workflows_d15.py` marks an upgrade committed only after the owned `engine.begin()` exits successfully. Its SELECT-only end inspection distinguishes:

- **Abort:** require the exact retained `4c_0001` schema, original catalog and all ten empty fixture tables. A changed/unknown state is an error, never reset or repaired. No successful-final-revision assertion runs on this path.
- **Committed upgrade:** require `d13_0001`, unchanged retained catalog, zero academic rows and actual per-table row counts. Rows before fixture preparation are rejected. Fictional-row retention is derived from verified counts; unverified state reports null rather than success.

Owned connection cleanup is recorded separately and must complete without errors. Preservation/recovery failures still fail teardown and remain visible; an expected fail-closed primary rejection is never relabeled a passed acceptance run.

`d15_workflow_plugin.py` now retains separate setup/call/teardown outcomes, exception classes and safe public codes. It never serializes exception arguments, locals, SQL parameters or driver payloads. Safety messages are rebuilt from restricted public codes. `counts` follows pytest phase-report semantics, so one call failure plus one teardown error remains **FAILED=1, ERROR=1**; exclusive `case_counts` is also supplied. `run_workflows.py` exposes both phases and verified retention/end-state facts, and requires all ten passes, verified completed upgrade and successful cleanup before reporting acceptance success. The original two failed run directories remain untouched.

### Fresh validation

| Selection | Fresh result | Boundary |
|---|---|---|
| Combined D15 offline guard/tooling tests | **469 passed, zero failed**, 6.24s | Includes the prior 381 cases, exact dialect-compiled frozen statements at the before-cursor boundary, mutation/binding negatives, abort/success end verification, cleanup, phase evidence and parent CLI summaries. Counts are not added to prior selections. |
| Synthetic pytest/SQLite recorder executions | **Three scenarios passed within the 469 tests** | Actual child pytest hooks exercise success, call failure with successful SQLite rollback, and call failure plus independent teardown error. All use new owned fictional SQLite files; no PostgreSQL connection. |
| Fictional SQLite workflow rehearsal | **7 passed, zero failed**, 10.96s; two existing warnings | Real in-process FastAPI/V2/workflow services with fictional providers. Not PostgreSQL migration/trigger/locking or browser evidence. |
| PostgreSQL workflow collection | **10 collected**, 0.97s | Ordered selection unchanged; no live fixtures executed. |

The latest 469-case selection was rerun after the safe-message correction. Earlier 461/468-pass development records remain intact. New tests reject single/triple/quadrupled percent changes at the wire boundary, extra percent characters, positional/named placeholders, extra DDL, altered literals, unexpected bindings/executemany and wrong driver styles. Separate cases retain the PostgreSQL18 independent fixture and rejection/fingerprint coverage. The two SQLite workflow warnings remain Starlette HTTPX TestClient and AnyIO BlockingPortal deprecations; no dependency change.

Exact existing files changed this correction:

- `docs/testing/dashboard-d15/d15_workflow_guard.py`
- `docs/testing/dashboard-d15/test_workflows_d15.py`
- `docs/testing/dashboard-d15/d15_workflow_plugin.py`
- `docs/testing/dashboard-d15/run_workflows.py`
- `docs/testing/dashboard-d15/run_offline_checks.py`
- `docs/testing/dashboard-d15/audit_evidence.py`
- `docs/dashboard-d15-postgresql-acceptance.md`
- `docs/testing/dashboard-d15/manifest.json`

Created `test_d15_workflow_tooling.py`, `operator-post-abort-diagnosis.json` and five unique command records (three offline guard selections, one SQLite rehearsal and one collection). No existing failure, dataset, application, original migration, GA or historical artifact was edited. The audit checks all original baseline bytes and all previously manifested artifacts outside the explicitly updated D15 tooling/report paths before replacing the manifest. Privacy inspection includes decoded evidence, complete/truncated receipt patterns, secrets/credential URIs and local private-faculty-name comparison without exporting values.

### Separately supervised PostgreSQL handoff

The corrected runner is ready for a **separately supervised live attempt**, not established as passing PostgreSQL acceptance. From the repository root in the existing private PowerShell terminal:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-d15/run_workflows.py --execute
```

This freshly verifies the exact retained target and schema before the controlled writing phase. It retains schema/data/evidence, never automatically retries and never resets/cleans the target. Return only its public JSON. Stop on any rejection or `STOP_REVIEW_REQUIRED`; do not change privileges or run bare Alembic. The user-confirmed recovery diagnostic was not repeated, and this write-enabled command was **not executed by Codex**.

Remaining limits: D9-D13 PostgreSQL acceptance has not passed. The exact-transport and recovery/reporting corrections have offline and SQLite evidence only; PostgreSQL-trigger, concurrency and workflow behavior still requires the live attempt. The 17 Phase4C cases remain passed historical operator evidence. Production institutional authority stays BLOCKED. No production readiness, physical outage/crash recovery or new browser acceptance is claimed. All 1,295 original baseline files, 23 academic files/protected preferences, GA operators/math/RNG/V1/V2, migrations, checkpoints, historical schedules and Git index/HEAD remain unchanged. No PostgreSQL connection, Git mutation, D16 or C++ work occurred during this correction.

## 18. Final evidence review and checkpoint boundary

### Successful operator execution inspected

The [successful command record](testing/dashboard-d15/20261025T173552806839+0800-workflows-postgresql/command.json) ran **2026-10-25 17:35:52.806839 to 17:36:44.641150 +08:00**, runner elapsed **51.831s**, exit 0, pytest **49.38s**. The [outcome record](testing/dashboard-d15/20261025T173552806839+0800-workflows-postgresql/pytest-results.json) records **10 PASSED, zero FAILED/ERROR/SKIPPED/NOT_RUN**, matching stdout and the ten collected IDs in the same order. All thirty setup/call/teardown reports passed. Attribution: **LOCAL_OPERATOR_EXECUTION, saved artifacts inspected by Codex**. No tests or database diagnostics were rerun during final review.

The [connection/end-state record](testing/dashboard-d15/20261025T173552806839+0800-workflows-postgresql/connection-guard-summary.json) records **168 physical connections, 1,551 identity checks and 884 admitted statements**. All owned connections closed; cleanup verified; no cleanup DDL executed. The exact stored end-state status is **`COMPLETED_UPGRADE_VERIFIED`** (the user's abbreviated public transcription used `COMPLETE_UPGRADE_VERIFIED`). It records committed revision **`d13_0001`**, retained schema, successful fixture preparation, actual retained fictional rows and `retained_schema_matches_entry=true`. This spelling difference is a transcription difference, not an artifact-integrity mismatch.

The [entry catalog](testing/dashboard-d15/20261025T173552806839+0800-workflows-postgresql/retained-schema.json) has revision `4c_0001`, no unexpected rows and a verified canonical SHA-256. It is byte-identical to the preceding retest's entry artifact. The [upgraded catalog](testing/dashboard-d15/20261025T173552806839+0800-workflows-postgresql/upgraded-schema.json) has revision `d13_0001`, twenty tables and a separately verified canonical SHA-256; its retained-4c digest matches the entry. Final review independently projected the upgraded columns/defaults, constraints/flags/bindings, indexes, triggers and functions onto the original eleven-table academic/identity/Alembic catalog and found exact equality. All upgraded constraint validation/enforcement flags are true and all non-internal triggers are enabled. The upgraded catalog contains 157 NOT NULL, 20 primary key, 51 CHECK, 32 foreign key and 34 unique constraints.

The recorded final row counts total **25 fictional rows**, including six users, three faculty identities, two sessions, one GEC record/two revisions/three events, one adjustment request/two events, one Chair decision, two published versions/one head and one controlled application. All seven academic tables remain empty. No actual row payloads, account credentials or session values are archived. The final GEC revocation case intentionally retains its fictional immutable history; retained test publications do not establish institutional authority or an active production constraint set. These are recorded end-of-run observations, not a new query of the current server.

Five warnings are retained in stdout: three emissions of the existing Alembic `path_separator` deprecation, one Starlette HTTPX TestClient deprecation and one AnyIO BlockingPortal alias deprecation. No warning was suppressed or repaired during this review.

### Reconciled attempt history

| Record | Actual result | Final interpretation |
|---|---|---|
| Phase4C `160918219600` | 17 passed, exit 0 | Original assertions verified against D15; retained `4c_0001`. |
| Workflow `163206495077` | One setup ERROR, nine NOT_RUN | PostgreSQL18 NOT NULL inventory mismatch; no migration reached. Original artifacts preserved. |
| Workflow `170223852944` | Raw pytest: one FAILED call plus one teardown ERROR; nine NOT_RUN | D9 transport rejection and misleading teardown. Legacy JSON overwrote the primary status; discrepancy remains explicitly documented. User-reported READ ONLY recovery confirmed unchanged `4c_0001` and empty tables. |
| Workflow `173552806839` | 10 passed, exit 0 | Corrected guard, migration rollback/commit, real PostgreSQL triggers/locking and fictional-provider workflows passed; retained `d13_0001`. |

The two earlier failed SQLite fixture rehearsals, all intermediate successful guard selections and both failed live workflow attempts remain present and hashed. The successful final attempt supersedes their blockers without deleting or rewriting them. The latest **469 offline tests** (including three synthetic pytest/SQLite recorder scenarios) and **seven SQLite workflow rehearsal cases** remain previously executed evidence, not fresh final-review executions. Distinct successful PostgreSQL acceptance cases total **27** (17 academic plus ten workflows); historical failed attempts are not counted as additional passes.

The ten successful cases cover additive migrations and actual statement-failure rollback; durable confirmation/revision races; immutable database guards and actual `55P03` locking/retry; actual V2 generation bound to PostgreSQL heads; owned faculty requests and denial; concurrent Chair decisions; injected application failure rollback/recovery; competing controlled applications/idempotency; immutable publication history/own views; and fresh-authority revocation. In-process FastAPI against PostgreSQL is real backend evidence, **not browser acceptance**. Injected storage exceptions are not physical PostgreSQL outages. No crash/restart, cross-process recovery or production deployment claim is made.

### Privacy, preservation and exact Git inventory

At review entry, all **1,295 original baseline files** and all **70 previously manifested artifacts** matched their raw SHA-256 hashes. Canonical catalog hashes and the retained projection were verified independently from the saved JSON. Final privacy inspection covers every D15 artifact and decoded JSON string, full/truncated receipt/token patterns, private keys and credential-bearing URIs, command outputs and locally compared private faculty names without exporting those names. No sensitive values or unwanted generated files were found. There are no D15 screenshots, HARs, database files, environment files or credential handoffs in the checkpoint inventory.

The exact proposed checkpoint contains **76 new D15 files: 18 Python tooling/test files, 57 JSON evidence/manifest files and this one Markdown report**. The [manifest](testing/dashboard-d15/manifest.json) lists all **76 exact paths** in `checkpoint_file_inventory`, with byte lengths and raw SHA-256 for the other 75 artifacts; the manifest excludes its own hash. This is the authoritative full inventory, including every retained failed attempt. All paths are confined to this report and `docs/testing/dashboard-d15/`.

Tracked application, original test and migration changes: **none**. The sole tracked working-tree modification remains the pre-existing protected `backend/data/faculty_preferences.json`; its local bytes still match the protected baseline. It is explicitly excluded from the proposed checkpoint and must not be restored, staged or committed. All 23 academic data files, faculty identities/mappings in files, GA operators/fitness/math/RNG/V1/V2 sources, checkpoints, saved schedules/history, prior D1-D14 evidence and Git index remain byte-identical. Branch `main`, HEAD and last-fetched `origin/main` still identify `c6baad2a0d59515555b33c84eca337a78a913a65`; no fetch or remote-state claim beyond that tracking reference is made. Git whitespace checks pass; Git's existing LF/CRLF advisory for protected preferences does not alter the file.

Only this report and the manifest were updated during final review. No tooling/application correction, test execution, database connection, migration, reset, row cleanup, permission change or Git mutation occurred. The retained disposable database and its fictional rows were not touched.

The existing `audit_evidence.py` manifest-writer retains its pre-final preparation-stage logic and was not rerun. Final review independently checked the successful evidence and finalized manifest below; do not use the historical writer to replace this final acceptance record. The original baseline-pinned execution/audit scripts remain historical tooling, not instructions for another database run or general cleanup.

### Decision and remaining limits

**D15 is safe to propose for a separately authorized Git checkpoint**, limited to the exact 76-file inventory and excluding protected preferences. This review does not authorize staging, committing or pushing. Do not rerun the acceptance runner against the populated `d13_0001` database; no additional database action is needed for this checkpoint.

Disposable PostgreSQL acceptance does not supply real institutional issuers, confirmation mandates, Chair mandates, publication authority or production configuration. All workflow providers used by the tests were explicitly fictional and scoped to the owned test process; deployment institutional providers remain BLOCKED. PostgreSQL crash recovery, physical outage behavior, production readiness, new browser acceptance and broader performance conclusions remain outside this evidence. No D16, general cleanup or C++ work has begun.
