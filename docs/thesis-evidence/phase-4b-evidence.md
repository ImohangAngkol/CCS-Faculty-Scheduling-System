# Phase 4B.1 thesis evidence

Date: 2026-10-16, Asia/Manila. Source baseline: `c770c841259b968132f8ce6b48ae5cb36df35171`.

## Current thesis evidence assessment (documentation update 2026-10-18)

**P4B-B01 through P4B-B06: PASS — USER CONFIRMED.** See the [final written acceptance matrix](../testing/phase-4b/manual-acceptance-results.md) and [manual acceptance manifest](../testing/phase-4b/manual-acceptance-manifest.json). All six were manually executed by the user; Codex did not independently execute or observe them. **Screenshot evidence: NOT CAPTURED for every scenario. Automated browser execution: NOT ESTABLISHED. Original manual test timestamps: NOT RECORDED.** No screenshots were taken and no originals exist to archive.

The written outcomes support synthetic account/binding, preference persistence, administrator review, role restriction, logout and error/recovery prototype workflows. B06 was an **injected fixture HTTP 503** via `ready.unavailable`; the user confirms marker removal restored the same faculty session with Compact / Very High preserved. It was not a physical PostgreSQL outage. These are attributed functional results, not a usability study, independent visual demonstration or production/GA-quality qualification.

Existing automated evidence remains separate and unchanged: real PostgreSQL 14 passes (user executed, artifact inspected); latest offline browser/recovery 187 passes; authentication 61 passes with 1 deselected; frontend contracts 8 + 22 + 48 = 78 passes. No counts are increased by adding manual scenarios or overlapping historical reruns. The missing images/browser metadata are explicit limitations under the [documentation standard](../DEVELOPMENT_DOCUMENTATION_STANDARD.md); the package is ready for written-only review with those limitations.

## Historical assessment and verification chronology

The assessments below retain their original pre-confirmation scope, including NOT RUN/BLOCKED statements. They are not the current browser acceptance status. Stage A/recovery source manifests and all earlier test artifacts retain their historical hashes.

**Assessment: PostgreSQL acceptance PASSED; Stage A fixture preparation OFFLINE VERIFIED; actual browser evidence outstanding.** The user-executed [2026-10-18 record](../testing/phase-4b/20261018T100533+0800-postgresql-e2beb33f.json) reports 14 passed, zero failed/skipped, three warnings in 12.23s, exit 0. Codex reviewed that artifact, then implemented/tested only the authorized Stage A fixture. Earlier blocked/failed attempts remain historical. No browser success is inferred from database/offline tests.

| Thesis/prototype requirement | Evidence | Limitation |
|---|---|---|
| Invalid scheduling inputs do not silently become empty preferences through the web API | New start-route admission regressions, missing/empty/default cases, no-worker/no-write checks | Direct Python/notebook loader calls are unchanged; this is an API-boundary fix |
| Instrumentation/validation preserves valid GA optimization | Seeded equivalence of schedule, penalty, breakdown, RNG and fitness-call count; existing domain/control/checkpoint tests | Bounded fixtures are not a production performance/optimality study |
| Identity storage is safely targeted | Exact-URL gate and read-only catalog-gate unit tests | Unit fakes do not establish PostgreSQL acceptance |
| Real PostgreSQL identity/authentication acceptance | User-executed suite: 14 passed; migration revision, constraints, bootstrap, sessions, authorization, concurrency and lock assertions passed | Browser/production qualification remains outstanding; exact warning messages and server version absent from artifact |
| Administrator/faculty ownership and session controls | Executed existing real-auth SQLite/temporary-storage regression group | Not online PostgreSQL proof; previous Phase 4A evidence remains separately attributed |
| User-friendly verified workflows | Existing frontend contracts/build/focused lint; planned browser scenarios | Six genuine PostgreSQL browser scenarios BLOCKED; no screenshots |
| Data and GA preservation | Baseline/final SHA-256 comparison and unchanged checkpoint-fingerprinted sources | Does not certify the contents or resumability of every user checkpoint |

See the [implementation/verification report](../phase-4b-postgresql-verification.md), [executed testing ledger](../testing/phase-4b/README.md), [browser status/instructions](../testing/phase-4b/browser-acceptance.md) and [screenshot status](../screenshots/phase-4b/README.md).

All test counts/timestamps come from actual execution artifacts. Repeated successful runs are not added to totals. Initial reproduction and evidence-helper incidents remain disclosed in the ledger. No claim is made of improved fitness, changed weights, institutional data migration, production deployment qualification, usability-study results or production readiness. No new Phase 4B screenshot filename is claimed.

## Historical first-execution evidence summary (2026-10-16)

503 distinct backend cases and 78 frontend contracts passed; frontend build and scoped lint passed. Fourteen PostgreSQL cases skipped and six browser scenarios remain blocked; these are not passed evidence. Exact command/timing/failure artifacts and the [final manifest](../testing/phase-4b/manifest.json) support this assessment. The API correction is reviewable; full database/browser phase acceptance remains outstanding.

## User-requested acceptance resumption, 2026-10-16 23:49 +08:00

The private test URL was still absent in the actual execution environment after the user reported configuration. The PostgreSQL suite again reported **14 skipped / BLOCKED**, without connecting, migrating or writing. No database identity, privilege, schema or data check could be completed; no fallback was used.

The safe isolated reruns passed **142 backend cases and 30 frontend contracts**; one existing backend browser case was deselected. They repeat existing cases and do not increase the original 503/78 distinct totals. All six PostgreSQL browser scenarios remain BLOCKED / NOT RUN. No browser version, observed application URL, screenshot or successful PostgreSQL outcome is claimed. The earlier blocked attempts and evidence artifacts remain archived unchanged.

See the [resumption evidence record](../testing/phase-4b/2026-10-16-resume-01/acceptance-status.json) and [updated ledger](../testing/phase-4b/README.md). Full Phase 4B.1 acceptance remains outstanding.

## PostgreSQL acceptance and next evidence gate (2026-10-18)

**PASS: USER EXECUTED, ARTIFACT INSPECTED BY CODEX.** Fourteen PostgreSQL cases passed with zero failures/skips and three warnings. Pytest duration 12.23s; runner elapsed 13.660s; timestamps 10:05:33.735990 to 10:05:47.395945 +08:00. This provides real PostgreSQL evidence for the asserted identity migration, relational constraints, genuine credentials/authorization, transactions, persistent sessions, concurrency and locking. It is not a production rollout or browser study.

The three warning messages were suppressed by `--disable-warnings` and cannot be individually identified from the successful JSON. They remain explicitly unidentified; a static Alembic deprecation candidate is unconfirmed. Neither omitted warnings nor historical skips are rewritten as additional passed tests.

Six browser scenarios remain **NOT RUN**, with no screenshots. The [separate-database browser plan](../testing/phase-4b/browser-acceptance-plan.md) preserves the successful database and specifies pending fixture/target/privacy improvements, exact proposed commands and genuine screenshot provenance. All browser filenames in that plan are proposed names, not archived evidence. Full phase acceptance still needs those real browser observations. Documentation review started no services or database operations and changed no application data.

## Stage A: controlled fixture and offline evidence (2026-10-18)

The [prepared fixture report](../testing/phase-4b/stage-a-fixture-preparation.md) and [stage manifest](../testing/phase-4b/stage-a-manifest.json) support these additional prototype claims: the original acceptance database cannot be selected by browser configuration; exposed profiles and preferences are synthetic; all fourteen storage aliases and direct session engine access are isolated; genuine credentials/Origin/CSRF/ownership remain enforced; optimization/resume and unintended startup are denied. These were tested with fake PostgreSQL engines and real in-memory SQLite/ASGI authentication, **not** live PostgreSQL or React browser interaction.

Executed: 93 browser safety/fixture/evidence/original-safety cases and 61 auth cases passed; one existing browser case deselected. Frontend contracts: 8 auth + 22 preferences + 48 GA/report passed. Original overlapping scoped totals are not added. The initial ACL-script parser failure and subsequent 91/92/93-case passes remain distinct artifacts; no production bug/pass is fabricated from that development incident. The actual owned-temp Windows ACL regression passed.

No new PostgreSQL objects/records, live preference changes, GA calls, services or browser captures occurred in Stage A. The evidence helper only hashes existing privacy-reviewed PNGs and records pending-review metadata. Its temporary IO sample is not Phase 4B screenshot evidence. Actual browser version/URLs/results, six captures, second-target migration/startup and usability/deployment conclusions remain outstanding. [Stage B instructions](../testing/phase-4b/browser-acceptance-plan.md) require separate approval and actual observed evidence.


## Stage B recovery tooling: offline evidence (2026-10-18)

The user reports earlier successful isolated database/fixture/frontend setup and five read-only retained-state checks. These remain USER CONFIRMED; no supplied screenshots/raw output or exact observation times were available to archive. No administrator login or six acceptance scenarios have completed.

The [recovery report](../testing/phase-4b/stage-b-recovery-offline.md) supports fail-closed retained-fixture validation, shared ownership, explicit credential-update transaction shape, finite lifecycle and private handoff/isolation claims through offline tests. Latest results: 187 browser/recovery tests, 61 auth tests (1 browser case deselected) and 78 frontend contracts passed. SQLite/fake PostgreSQL catalogs are identified explicitly; they do not prove live PostgreSQL recovery/locking or actual React acceptance. Intermediate/historical executions remain preserved and are not counted twice.

Live recovery, credential rotation, services, migrations and screenshots were NOT RUN in this task. Catalog compatibility and real six-scenario observations remain pending separate approval under the [updated plan](../testing/phase-4b/browser-acceptance-plan.md#recovery-of-the-retained-browser-database-offline-prepared). The [recovery manifest](../testing/phase-4b/stage-b-recovery-manifest.json) records current hashes and protected-data/source comparisons. The historical Stage A manifest remains unchanged, including its earlier source hashes. No usability, GA-quality or production-readiness conclusion is inferred.
