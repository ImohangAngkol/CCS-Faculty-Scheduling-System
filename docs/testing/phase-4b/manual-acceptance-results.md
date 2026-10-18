# Phase 4B.1 final browser acceptance: written-only user confirmation

Documentation update: 2026-10-18, Asia/Manila. This is the report preparation date, **not an original browser-test timestamp**. Source baseline: `c770c841259b968132f8ce6b48ae5cb36df35171`, with pre-existing uncommitted Phase 4B work.

**All six functional scenarios: PASS — USER CONFIRMED. Screenshot evidence: NOT CAPTURED for every scenario. Automated browser execution: NOT ESTABLISHED. Original test timestamps: NOT RECORDED.** The user explicitly confirmed that no screenshots were taken; there are no original images to recover or archive. Codex prepared this written record from that confirmation and repository inspection; it did not independently execute or observe these browser scenarios.

## Environment and attribution

The user reports Microsoft Edge, the actual React frontend at `http://localhost:5189`, the isolated FastAPI browser fixture, and database `ccs_ga_phase4b_browser_test` with restricted role `ccs_ga_phase4b_browser_tester`. These are user-reported execution context, not fresh connectivity or database checks in this documentation task. The exact Edge version, viewport, per-scenario observed URLs, original execution times and duration were not recorded in the supplied evidence. The expected routes below come from the existing plan; no final `/login` URL is inferred for B05.

The fixture design uses synthetic identities/accounts and disposable preference/GA storage, with generation/resume blocked. See the [historical execution plan](browser-acceptance-plan.md), [Stage A report](stage-a-fixture-preparation.md) and [offline recovery report](stage-b-recovery-offline.md) for implementation and isolation assertions. Those reports document their original verification scope. The user reports later recovered-fixture use and manual completion; this does not turn earlier offline or blocked attempts into successful automated browser runs.

## Manual acceptance matrix

| Scenario | Expected result | User-confirmed actual result | Functional status | Screenshot evidence | Original test timestamp |
|---|---|---|---|---|---|
| P4B-B01: account creation and faculty binding | Administrator creates a synthetic faculty account and binds the intended synthetic identity | Account creation and intended faculty binding succeeded | PASS — USER CONFIRMED | NOT CAPTURED | NOT RECORDED |
| P4B-B02: preference save and refresh | Compact / Very High remains saved after browser refresh | Faculty preference save and refresh persistence passed | PASS — USER CONFIRMED | NOT CAPTURED | NOT RECORDED |
| P4B-B03: administrator preference review | Administrator can review the synthetic faculty's saved preferences | Administrator preference review succeeded | PASS — USER CONFIRMED | NOT CAPTURED | NOT RECORDED |
| P4B-B04: administrator-route restriction | Faculty navigation to the planned `/admin/accounts` route denies administrator content | Faculty denial from administrator routes passed | PASS — USER CONFIRMED | NOT CAPTURED | NOT RECORDED |
| P4B-B05: logout and authentication requirement | After logout, protected navigation requires authentication | Logout and subsequent authentication enforcement passed | PASS — USER CONFIRMED | NOT CAPTURED | NOT RECORDED |
| P4B-B06: injected unavailability and recovery | Owned fixture fault shows an unavailable error; removing it restores the original session and saved preferences | User created `ready.unavailable`, observed the expected unavailable error, removed the marker successfully, and recovered the same faculty session with Compact / Very High preserved | PASS — USER CONFIRMED | NOT CAPTURED | NOT RECORDED |

Automated browser execution is **NOT ESTABLISHED for each of these six rows**. The matrix records the user's functional confirmation, not independent screenshots, HTTP traces, cookie/session inspection or database queries. More detailed subchecks in the historical plan (such as a duplicate-binding attempt or separate unchanged-record comparison) have no separately recorded observations here and must not be presented as additional independently verified cases.

## B06 scope and security interpretation

B06 exercised an **injected fixture HTTP 503**, controlled by the isolated fixture's same-stem `ready.unavailable` marker. It was **not a physical PostgreSQL outage**. The user confirms error presentation, marker removal, recovery of the same faculty session and preservation of Compact / Very High preferences. There is no archived screenshot or network trace independently proving that response or session continuity. This supports the reported synthetic-fixture error/recovery workflow, not service-stop recovery, production availability, failover or durability benchmarking.

B04/B05 provide user-confirmed frontend authorization and logout behavior. Backend authorization, ownership, CSRF, session persistence and relational constraints are supported separately by automated records; the manual passes are not additional automated security tests.

## Existing automated evidence, unchanged

No tests were rerun to prepare this report. Repeated scoped executions must not be added together or mixed with the six manual scenarios.

| Evidence scope | Existing result | Artifact |
|---|---|---|
| Real PostgreSQL acceptance, user executed; artifact inspected by Codex | 14 passed, 0 failed, 0 skipped, 3 warnings; pytest 12.23s | [PostgreSQL run](20261018T100533+0800-postgresql-e2beb33f.json) |
| Latest recovery/browser-fixture offline regression | 187 passed, 0 failed, 0 skipped, 2 warnings; 7.39s | [Offline run](20261018T124936+0800-browser-offline-517a1187.json) |
| Latest authentication regression | 61 passed, 1 deselected, 4 warnings; 37.06s | [Authentication run](20261018T124832+0800-auth-bcf8ebc9.json) |
| Frontend contracts, separately from real browser execution | 8 auth + 22 preferences + 48 GA/report = 78 passed | [Auth](20261018T124833+0800-frontend-auth-5addb12f.json), [preferences](20261018T124834+0800-frontend-preferences-d0aa5fd2.json), [GA/report](20261018T124836+0800-frontend-ga-88a9fe6a.json) |

The PostgreSQL artifact suppressed individual warning messages; their three categories remain unidentified. Build/lint and older 503-backend/78-frontend results retain their original scope in the [ledger](README.md). Fake-engine and SQLite offline tests remain distinct from real PostgreSQL and manual browser observations. Original automated execution timestamps belong to those artifacts only.

## Evidence checklist and thesis relevance

- [x] Six functional outcomes are attributed to USER CONFIRMED manual testing.
- [x] Screenshot absence, unavailable test times and lack of established automated browser execution are explicit.
- [x] Injected 503 and same-session recovery claim are attributed and scoped accurately.
- [x] Existing automated evidence and previous blocked/failed attempts remain separate.
- [ ] Screenshots, capture metadata and screenshot hashes: NOT CAPTURED; no originals exist.
- [ ] Original manual timestamps, exact browser version, viewport and per-test observed URLs: NOT RECORDED.
- [ ] Independent automated browser execution: NOT ESTABLISHED.

The written account supports a thesis prototype demonstration of synthetic administrator/faculty workflows, preference persistence, role restriction, logout and fixture error recovery. It is not a usability study, GA-quality evaluation, production qualification or independently observed browser demonstration. Under the [documentation standard](../../DEVELOPMENT_DOCUMENTATION_STANDARD.md), this package is ready for **written-only review with explicit evidence limitations**, not an unqualified declaration that all screenshot requirements were satisfied.

## Reproduction and review boundary

Use the historical plan as the description of the manual procedures already performed. Do not recreate accounts, resave preferences, toggle fault markers, log out, restart services, rotate credentials, rerun initialization/recovery or reset either retained database merely to fill evidence gaps. The pristine recovery gate is not a reuse procedure for the now-populated browser database. No new application interaction is needed to review this written-only report. Any later supplemental capture would need its own actual capture time and scope; it cannot reconstruct these original tests or acquire their missing timestamps.

The [manual acceptance manifest](manual-acceptance-manifest.json) records the six attributed results and current documentation hashes. The [main manifest](manifest.json) records revised current artifact references with superseded hashes retained as provenance. Stage A/recovery manifests, old execution JSON, historical blocked attempts and original test counts remain unchanged. No screenshot filenames, image hashes, raw credentials, cookies, password hashes or private handoff contents are included in this report.
