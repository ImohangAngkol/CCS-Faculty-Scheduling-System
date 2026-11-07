# U5J — scoped authority, trusted capture and deployment storage qualification

2026-11-05, Asia/Manila. `main` at `d6db077793da52b7559351a5d0f8e6d54608cb77`.

**Isolated contract qualification is implemented and tested. Genuine institutional authority, the institutional input transformation and deployment storage remain unqualified. Production admission remains BLOCKED.** No production provider, route, worker, source loader, storage path or database is activated.

## Preservation and prerequisite review

Reviewed U5G, U5H and U5I reports, manifests and selective staging plans, their implementation and tests, account/session models, academic scope models, Chair authority, source qualification/context services, loader/scoring code and development startup configuration. Required order remains **U5G → U5H → U5I → U5J**. U5G/U5H/U5I are uncommitted inventories of 34/77/67 paths respectively. Their 33/76/65 artifact hash references verify at entry and final audit.

The new baseline covers **3,796 paths**, all 23 academic data files, both protected local JSON modifications, original GA/operator/scoring/RNG and fingerprint sources, migrations, checkpoints, Saved Best, schedules, previous evidence, Git index and the mixed `main.py`. U5J changes **none of those bytes**. Existing sixteen tracked modifications and unrelated untracked research/U4/Live Center/U5D–U5I work are preserved. All U5J files are new; no partial staging of an existing file is needed for this milestone itself.

## Actual institutional findings

| Area | Verified source finding | Qualification |
|---|---|---|
| Authenticated identity | User/session infrastructure supplies server-verified account UUIDs, admin/faculty roles and an optional faculty binding. It does not supply an optimization mandate for a department. | Identity infrastructure reusable; scoped optimization authority missing. |
| Department | Phase 4C `AcademicScope` and term/section/offering relationships model academic scope. A scope record or department label does not authorize an account to optimize that scope. | Data schema exists; genuine account-to-action mandate source not connected. No live rows queried. |
| Chair | The existing independent Chair directory checks scoped review/decision mandates and resource/term bindings. Its institutional provider returns None. | A Chair-review capability cannot be reused as optimization or publication permission. Administrator role alone is insufficient. |
| Academic context | U5B/C verification provider is unconfigured; matching technical projections do not establish institutional context. | No academic year, term or department label is invented or activated. |
| Loader | `Functions.py` imports and transforms academic frames, builds cached resources, constructor calendars and fixed-section/preassignment state. `FrozenInputs` separately reads selected preference/settings data. | No coherent institutional source snapshot or complete raw-to-model attestation established. |
| U5G/H/I | Immutable prepared graphs and a verified technical consumer exist; U5I admits only with separately supplied issuer/capture/store dependencies. | Reusable internal boundary; genuine providers and deployment storage are still absent. |
| Deployment | Development launcher targets an existing private local development identity database; no approved persistent run volume, service account, backup/disposal policy or restoration supervisor was found. | Temporary SQLite acceptance does not establish deployment readiness. |

These are source/configuration findings, not a live database or institutional-record audit. IT remains the currently available prototype/evaluation scope; nothing expands the population to full CCS or invents IS records.

## Implemented authority contract

New internal bridge: `services.ga_qualification_authority.ScopedAuthority`, version `ga-scoped-optimization-qualification-v1`.

An independently trusted server directory supplies exactly one current `OptimizationMandate` for the authenticated actor and requested department. It includes record UUID/revision, actor/department, explicit `department_optimization_control` capability, permitted actions, source identity, state and effective interval. Missing, duplicate/ambiguous, revoked, future, expired or malformed mandates reject. Unsupported/duplicate actions and Chair-review-only capabilities reject.

A **separate trusted verifier** must attest the entire canonical mandate digest and source identity, with current validity and an evidence digest. Hashes and reference strings alone cannot create authority. No HTTP input or environment switch supplies these dependencies. The adapter is not connected to a genuine institutional directory or verifier.

The adapter yields the exact U5I Grant contract, bound to the current run context and action. Expiry is the earliest of 60 seconds, mandate expiry and attestation expiry. Its stable policy digest binds contract version, adapter source fingerprint, mandate and evidence. Revocation or changed policy/revision prevents a previously admitted run from continuing. Account role and client department labels are not evidence of a mandate.

`audit(context)` provides an internal evidence projection: context/mandate/code digests, source/evidence identities, record UUID/revision, action and department. It declares no publication authority. It contains no bearer proof, private provider response or faculty name. This is an audit **projection**, not a newly deployed durable institutional approval ledger. U5I persists the resulting policy digest; full mandate/evidence custody and retention require an approved independent registry.

Directory/verifier guards must supply coherent lifecycle reads and serialize revocation. The adapter requires a guard even for direct authorize/audit calls. ContextVars isolate concurrent call scopes. Provider acquisition and validation failures are sanitized. Lock acquisition order in the provided adapters is directory → verifier → catalog; provider implementations and administrative update paths must honor that order. These trusted Python interfaces are not hostile-plugin sandboxes or cryptographic remote attestation.

**Authority result: server contract qualified with fictional providers; genuine institutional authorization NOT ESTABLISHED.**

## Implemented trusted prepared-input capture

New `services.ga_qualified_capture.CaptureAdapter`, version `ga-prepared-input-delivery-v1`, implements U5I's source interface without changing U5I.

The catalog owns a guarded immutable `PreparedSnapshot`: exact department/catalog reference, revision, source identity, effective interval and a valid U5G prepared bundle. The separate verifier must attest the complete snapshot identity. Admission accepts no trusted client fingerprint, bundle, runtime graph or transform function.

Capture does the following under the source/verifier guards:

1. Verify scope, validity, canonical bytes/hash and independent snapshot attestation.
2. Materialize the prepared bundle into a detached private graph. No fallback to `Functions` roster/subject/room/frame aliases is used.
3. Rebind the graph to the **new server-generated run ID** through the existing U5G encoder. Preserve graph ordering, aliases, sections/calendars, eligibility/load profiles, legacy preference frame, scoring context, exact configuration and optional captured seed/context reference.
4. Add source identities for the prepared bundle, catalog binding, attestation and actual delivery-adapter source. Preserve upstream declared source identities without promoting their institutional status.
5. Construct U5H Session for full engine/graph/configuration/alias preflight, with a separate local RNG and **zero optimization generations**.
6. Recheck before/after snapshot identity, canonical bytes, validity and independent evidence. Source drift or malformed content rejects the whole capture.

Tests verify unchanged source bytes/global RNG, exact graph equality, run rebinding, malformed bundles, engine mismatch, stale revisions, missing evidence, scope mismatch and poisoned cached globals. Actual admission → pause → durable checkpoint → coordinator restart → resume is exercised using this adapter and the scoped authority bridge, with fictional data only.

This is a **prepared-input delivery adapter**. It is not a newly implemented institutional CSV loader, roster merger or raw-data-to-model transformation. A real source steward must still establish authoritative term/department identities, cohort completeness, eligibility, qualifications, workloads, preferences, resources/calendars, external commitments and the upstream transformation/version. A valid prepared bundle proves technical shape/identity, not that institutional source data were complete or approved. Hashing a cached graph is not an acceptable substitute.

Capture receipts remain UNVERIFIED. U5H can subsequently issue VERIFIED **technical consumption** evidence only after its actual execution boundary. Runs remain ineligible for CURRENT and Saved Best promotion. U5D observations are unchanged and UNVERIFIED.

**Capture result: isolated prepared-input delivery verified; institutional source and raw-to-model transformation BLOCKED.**

## Storage qualification and policy

New read-only `services.ga_storage_qualification.inspect` accepts only the existing owned U5I Store contract. It rechecks private namespace identity, Windows DACL permissions, SQLite schema version, quick integrity/FKs and retained checkpoint lineage; observes free space without claiming a physical quota; and returns explicit deployment requirements. Expired retained checkpoints can be checked for integrity without making them accessible through run APIs.

On Windows, permission inspection reads only the owned temporary directory's actual ACL and requires protected access for the current user, SYSTEM and Administrators. It changes no ACL or owner. Its subprocess receives only whitelisted OS variables. The underlying new-store creation ACL behavior is unchanged. POSIX mode checks are present but were not executed on this Windows host.

Supplying a `DeploymentEvidence` reference for every requirement **never changes production_ready to true**. Independent evidence and an approved deployment implementation are required, not a caller-provided approval flag. This inspection is not a deployment activator.

| Requirement | Actual isolated evidence | Required before deployment |
|---|---|---|
| Durable location | U5I deliberately accepts newly owned OS-temp roots only. | Explicit approved persistent local volume, separate from datasets/history; documented filesystem and service ownership. No path chosen or created here. |
| Directory permissions | Actual protected Windows DACL checks pass; permission setup/read failures fail closed. | Dedicated deployment service account, least privilege and audited operator/backup access; test under that identity. |
| Atomicity/recovery | Existing transaction couples checkpoint bytes/tip; interrupted process test and restart/RNG tests rerun. | Qualify intended filesystem/service supervisor and failure model; no arbitrary power-loss/network-storage guarantee. |
| Backup/restore | New fictional SQLite backup image is copied into a separate private fixture and independently checked for schema, counts, lineage and U5H restore decoding. Original stays paused and retained. | Backup schedule, restricted custody, encryption/access, restore drill and approved restoration epoch/fencing. |
| Restore ownership | Offline restored bytes are valid; no restored instance is installed or started as a second service. | Prevent the original and restored database from becoming competing active owners. Per-database leases alone do not prove cross-copy single ownership. |
| Retention/cleanup | Seven-day access expiry, bounded logical payload/run/checkpoint limits; retained expired bytes remain intact. | Approved disposal/archive/backup retention policy and audited cleanup. No deletion is authorized or implemented. |
| Physical disk | Current free space observed; deliberately impossible threshold reports false. | Enforce actual filesystem/database/journal/backup quotas and reserve; account for concurrent disk use. Logical payload limits are insufficient. |
| Concurrent access | U5I admission, leases, ownership fencing and concurrent runs rerun; new adapters test concurrent idempotent admission. | Qualify exact process topology, lock order, service identity, restore fences and failure handling. |
| Schema/version | Existing store version and release/bundle/config checks remain strict. No schema changes. | Approved migration/rollback/version policy for a future deployment backend. Never reinterpret historical checkpoints. |
| Restart | Real fresh-process restore and interrupted-write rollback rerun in U5I; new adapter coordinator reopen/resume tested. | Trusted providers must be freshly established after restart; no cached mandate or self-activation flag. |

The backup test is an **offline data-restoration experiment**, not a production backup service, automatic restore procedure or cross-store fencing proof. Fixture backup databases and raw checkpoint/bundle payloads are not archived in evidence. No source dataset, existing SQLite database, institutional PostgreSQL, retained D15 target or historical artifact is opened for writes.

**Storage result: isolated integrity/permission/backup-image qualification verified; deployment policy NOT READY.**

## Admission and HTTP status

The new adapters connect to U5I through constructor injection **only in isolated tests**. No existing file, route or deployment dependency is edited. `configured_service()` remains None, production authenticated execution remains 503/unavailable, and legacy endpoints remain separate. No institutional run is admitted. There is no new UI implying an unsupported capability, no continuous worker and no automatic CURRENT, approval, publication or Saved Best promotion.

## Fresh tests and evidence attribution

| Selection | Fresh result |
|---|---|
| U5J authority/capture/storage qualification | **49 passed** |
| U5I admission, owner access, SQLite persistence, recovery and HTTP | **50 passed** |
| U5H optimizer consumption | **39 passed** |
| U5H original fixed-engine and checkpoint RNG/fresh-process parity | **5 passed** |
| U5G fixed-engine checkpoint continuation qualification | **10 passed** |
| U5G immutable bundle tests | **32 passed** |
| U5D observations | **36 passed** |
| U5E analysis | **20 passed** |
| U5F readiness | **20 passed** |
| U5A–U5C compatibility/context/source regressions | **99 passed** |
| Unique Python cases above | **360 passed, zero failed/errors/skipped** |
| Frontend contracts | **210 passed** |
| Real Edge with fictional intercepted HTTP | **16 scenarios passed**; Node counts 17 including the wrapper |
| TypeScript, production build, focused ESLint | **PASS** |
| Git integrity/whitespace, artifact/privacy and preservation audit | **PASS**, manifest records exact evidence |

All backend runs use owned source snapshots excluding academic/runtime trees before archive creation, fictional import tables and D10 fictional models. The existing committed release-byte fixture reproduces unchanged source line endings; strict engine fingerprints are still evaluated. Dependencies were reused, not installed. No PostgreSQL connection or migration occurred.

The U5I regression includes real session lookup/CSRF/Origin against a fresh fictional identity SQLite database and owned loopback HTTP; other tests inject explicit fictional principals/providers. U5J's new adapter tests invoke actual U5H execution and real private SQLite persistence. The browser regression is a separate intercepted-HTTP React test, not a browser-to-live-U5J authority demonstration. Six genuine screenshots were visually reviewed and hashed; no private faculty/account data or tokens are visible.

The initial U5J suite passed 43 cases. After adding missing-dependency, permission and RNG tests, the expanded suite passed 49; the final 49-case rerun qualifies the final authority implementation fingerprint. These superseded successful runs are retained and not counted again. There are no new U5J failed test assertions or timeouts. Prior U5I setup failures remain unchanged in their own sealed evidence.

An inherited command-recorder scope string in early qualification/admission records incorrectly said "No database access". Those original records and test outcomes are preserved. `attribution-addendum.json` identifies each affected record and clarifies that they used **fictional owned SQLite**, with no PostgreSQL/institutional database. Later command records use the corrected scope. The final qualification record's scope is correct. Do not interpret the copied wording as a claim that SQLite acceptance was mocked.

Warnings are the existing Starlette/httpx and anyio TestClient deprecations in applicable suites, plus existing Vite dynamic-import/chunk-size warnings. No dependency change or cleanup was made. Git fsck exited zero with existing dangling objects. The historical intermittent U5D concurrency issue remains root-cause-unconfirmed; the fresh full U5D suite passed, which is not a new fix claim.

## Exact changes and checkpoint plan

New application modules:

- `backend/services/ga_qualification_authority.py`
- `backend/services/ga_qualified_capture.py`
- `backend/services/ga_storage_qualification.py`

New focused tests: `backend/tests/test_qualified_execution.py`.

New documentation/evidence: this report and `docs/testing/dashboard-u5j/` with preservation baseline, entry review, qualification findings, source-snapshot/check runners, original command records/proofs/parity artifacts, screenshots/review, attribution addendum, audit, manifest and staging plan. The manifest's `exact_changed_and_new_file_inventory` is exhaustive. **Existing files modified by U5J: none.**

**Ready for selective checkpoint review of the isolated qualification foundation, not institutional activation.** Review prerequisites U5G → U5H → U5I first; they remain uncommitted and contain mixed overlaps. Explicitly select only the four new U5J application/test paths, then the exact new documentation/evidence inventory. U5J requires no existing main/router hunk. Never stage protected JSON or unrelated work. Reproduce the proposed source snapshot before a separately authorized checkpoint. No staging, commit, push or deployment was performed.

## Reproduction in PowerShell

From the repository root, using the existing environment:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5j/checkpoint_snapshot.py qualification
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5j/checkpoint_snapshot.py admission
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5j/checkpoint_snapshot.py consumption
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5j/checkpoint_snapshot.py parity
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5j/checkpoint_snapshot.py legacy
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5j/checkpoint_snapshot.py bundle-tests
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5j/checkpoint_snapshot.py receipts
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5j/checkpoint_snapshot.py analysis
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5j/checkpoint_snapshot.py readiness
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5j/checkpoint_snapshot.py backend-regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5j/run_checks.py frontend
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5j/run_checks.py build
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5j/run_checks.py bundle
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5j/run_checks.py lint
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5j/run_checks.py browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5j/audit_evidence.py
```

Every execution writes new evidence paths, never earlier records. OS-temp/Windows ACL/owned child-process permissions are required for the isolated fixtures, not database privileges. Audit replay is non-writing; first manifest creation uses explicit `--record` and refuses overwrite. Do not copy fixture databases, raw bundles/checkpoints, sessions or provider payloads into evidence.

## Remaining blockers and next milestone

1. Establish genuine department/action mandates and separate evidence verification, lifecycle/revocation, audit custody and permitted optimization actors. Chair review or Administrator account status cannot substitute.
2. Qualify a complete IT term-specific institutional catalog and upstream transformation into prepared inputs, with source ownership, verified mappings, availability/external commitments and policy/config provenance. Do not infer these from filenames or imported globals.
3. Approve deployment storage location/service identity, physical quotas, backup protection, globally safe restore ownership and retention/disposal/version policy; then implement and independently test that approved deployment backend. No production path is selected here.

Recommended next milestone: **institutional provider and deployment policy acceptance**, with explicit evidence and operator decisions for these three blockers. Keep worker implementation/activation, genuine scheduling admission, CURRENT classification and publication outside that milestone until their required proofs exist. No continuous worker is authorized by this report.
