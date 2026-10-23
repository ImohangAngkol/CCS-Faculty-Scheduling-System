# Dashboard D9: durable GEC confirmation and revisions

Implemented and verified 2026-10-23, Asia/Manila, from D8 commit `eaba995e19c104a32d9cb2ea6c6acb4f2a1bf7ac` on `main`. **The safely testable D9 implementation is complete. Production confirmation remains BLOCKED: real institutional verification/confirmation providers and PostgreSQL acceptance are unavailable.** Confirmations shown in tests are explicitly fictional. No institutional approval or GA activation is established.

## Scope and inspected dependencies

The implementation reuses D3 intake, D4 identity reconciliation/projection, D5 fresh complete handoff, D6 original-source provenance, D7 session-bound readiness and D8 institutional trust. Inspection covered those services, authentication/ownership/Origin/CSRF dependencies, existing dashboard routing, SQLAlchemy identity/academic models, Alembic infrastructure and the [documentation standard](DEVELOPMENT_DOCUMENTATION_STANDARD.md). Historical [D7](dashboard-d7-implementation.md) and [D8](dashboard-d8-implementation.md) evidence remains unchanged.

The initial working tree contained only the protected preference modification. A 786-file raw-byte baseline, including all tracked files, protected datasets, saved chromosomes/checkpoints and the Git index, was recorded before edits in [preservation-baseline.json](testing/dashboard-d9/preservation-baseline.json). No PostgreSQL operation, provisioning, online migration, institutional write, GA execution or Git mutation was authorized or performed. D10 was not started.

## Exact implementation files

Six existing files changed (the sixth is the targeted screenshot stabilization test correction):

| File | Purpose |
|---|---|
| `backend/main.py` | Register the separate administrator-only confirmation router. |
| `backend/migrations/env.py` | Include separate D9 metadata alongside existing metadata; no startup migration. |
| `frontend/src/pages/admin/ExternalSchedules.tsx` | Mount durable history independently of temporary previews and forward current assessment. |
| `frontend/src/components/schedule/ExternalScheduleReview.tsx` | Export current assessed review to D9, clearing it on edits, expiry and unmount. |
| `backend/tests/academic/test_academic_foundation.py` | Update only migration-head and combined-metadata assertions for the additive D9 revision; retain seven-table constraints and frozen DDL checks. |
| `frontend/tests/gaMonitoring.browser.test.mjs` | Foreground/visibility/font/paint synchronization before the existing fitness screenshot; no changed functional assertion, capture method or timeout. |

Twelve application/test files created:

| File | Purpose |
|---|---|
| `backend/confirmation_models.py` | Three ledger relations, constraints and immutable/transactional trigger definitions. |
| `backend/migrations/versions/d9_0001_confirmation_ledger.py` | One additive, frozen PostgreSQL migration after `4c_0001`; offline rendering only. |
| `backend/schemas/external_confirmation.py` | Strict proposal/decision/revocation bodies; reject authority flags. |
| `backend/services/confirmation_authority_service.py` | Independent, default-unavailable institutional confirmer policy boundary. |
| `backend/services/external_confirmation_service.py` | Persistent proposals, fresh eligibility, confirmation, revocation, history and digest checks. |
| `backend/routers/external_confirmations.py` | Protected APIs with safe conflict/unavailability responses. |
| `backend/tests/dashboard/test_external_confirmations.py` | 26 policy/API/SQLite durability, history, concurrency, rollback and offline migration cases. |
| `backend/tests/dashboard/test_external_confirmations_live.py` | Two owned real-HTTP browser fixtures: default blocked and explicitly fictional authorized. |
| `frontend/src/api/externalConfirmations.ts` | Typed, validated DTOs and shared authenticated API transport. |
| `frontend/src/components/schedule/ExternalConfirmationLedger.tsx` | Teal/gold record, revision, comparison and authorized decision interface. |
| `frontend/tests/externalConfirmations.test.mjs` | Seven API contracts, error paths and fabricated-success rejection tests. |
| `frontend/tests/externalConfirmations.live.mjs` | Actual Edge/React to FastAPI browser scenarios; no simulated D9 HTTP responses. |

Supporting files: this report; `docs/testing/dashboard-d9/run_checks.py`, `probe_ga_capture.py`, original and stabilization baselines, final audit, stabilization findings, [manifest](testing/dashboard-d9/manifest.json), timestamped command records; screenshots and scenario JSON under `docs/screenshots/dashboard-d9/`. The probe instruments disposable copies only, including a `git archive HEAD frontend` comparison; owned source copies are removed after execution. The manifest lists every individual file and raw SHA-256. No application dependencies were added.

## Durable data and immutable history

D9 uses the established SQLAlchemy sessions and Alembic chain. It creates no unrelated engine or implicit SQLite fallback. `ConfirmationBase` is separate so the existing seven-table academic foundation metadata remains intact. The existing identity database dependency is injected in routes; only isolated tests override it with owned file-backed SQLite.

| New relation | Stored content and safeguards |
|---|---|
| `gec_records` | Stable UUID, fixed sourced academic year/term/supplier labels, creation time, decision version and head event. Scope cannot be edited. |
| `gec_revisions` | Stable UUID, record and base-event links, proposing account UUID, reason/time, canonical original review, completed candidate/mappings/metadata, SHA-256 and public proposal evidence snapshot. Append-only. |
| `gec_events` | Operation UUID, record/revision/prior-event links, unique per-record sequence, CONFIRM/REVOKE, authenticated actor UUID, time/reason, policy reference/digest, evidence snapshot/digest and schedule-content digest. Append-only. |

Same-record composite foreign keys prevent cross-record head/revision/prior-event links. User references restrict deletion. UPDATE/DELETE triggers protect revisions/events; record deletion is rejected. A record starts at version zero with no head. Event insertion verifies the predecessor, expected sequence, revision base and revocation target; its AFTER trigger advances the head in the same transaction. PostgreSQL SQL explicitly locks the record with `FOR UPDATE`. SQLite trigger behavior is actually exercised; PostgreSQL behavior is not claimed verified.

`d9_0001` creates only these three tables, their indexes, constraints and D9 trigger functions. It contains frozen SQL rather than runtime model imports. Downgrade refuses any retained record/revision/event and uses no CASCADE; successful or refused online downgrade has NOT been executed. No original migration or academic table was changed. Offline rendering checks the generated SQL, index names and exact correspondence with runtime guard/transition SQL.

Fresh independent SQLAlchemy engines and a separate Python process reopen an owned SQLite file and verify committed content hashes and events. This establishes file-backed durability across process state, rather than in-memory history. It does not establish PostgreSQL restart, crash recovery, deployment, backup or disaster recovery behavior.

## Authority policy and D8 integration

A real administrator session is necessary for every route but never sufficient for confirmation. Each confirmation obtains a fresh D7 assessed handoff and recomputes D8 evidence/policy findings under the current session owner. Content, source, mappings, term, supplier, candidate, references and assessed evidence must still match. Readiness must be READY and D8 outcome VERIFIED.

The separate `authorization_for(ConfirmationContext)` hook returns None in deployment. A future trusted institutional adapter must independently authenticate the actor and institutional mandate; it must not accept a caller's institution name, document upload or admin role as proof. The grant binds actor, action, operation UUID, record/revision, expected version, exact year/term/supplier, content digest and evidence digest. Strict validation is repeated on provider objects; suspended/malformed/mismatched/expired grants and provider exceptions fail closed. Grants need aware timestamps, must be current and may last at most 300 seconds. Provider exceptions/raw payloads are never logged.

Only tests inject a fictional evidence registry/provider and a separate fictional confirmation policy. Neither is selected by request parameters, production settings or a frontend checkbox. There is no production bypass switch, real institutional connector or invented MSU-IIT authority assignment.

Revocation independently requires a fresh REVOKE grant for the current confirmed record, version and stored evidence digest. It deliberately does not require invalidated evidence to become READY again. Revocation appends an event, retains both historical content and evidence, clears the current confirmed revision and never restores an older revision automatically.

## Workflow and integrity

Temporary drafts remain editable through D3-D8. A current assessed preview may be stored as an immutable PROPOSED revision, including blocked findings; this is not approval. Proposals must have sourced, nonblank year/term/supplier labels. A new proposal cannot change those labels for an existing record. Original academic term UUIDs are not guessed or manufactured.

An existing confirmation remains current while a new proposal is reviewed. A fresh authorized CONFIRM appends a successor event and makes prior confirmed content SUPERSEDED. Old base versions cannot replace newer decisions. Historical GET responses explicitly say `current_evidence_status: NOT_RECHECKED`: a recorded confirmation is a historical decision, not a fresh assurance that its evidence is still valid. Later withdrawal can block further confirmation while history remains available, and an independently authorized revocation can still be recorded.

Content is canonical JSON with SHA-256, not a fabricated signature. Reads check revision digests; history verifies event sequence/predecessors/head and event content/evidence digests. Malformed stored evidence produces a safe 503. The DB triggers and hashes protect against ordinary application mutation; they do not defeat a database owner who can disable triggers or rewrite both content and hashes. Production role separation and independently retained audit/backup controls remain required.

Mutation responses are emitted only after transaction commit. Any error rolls back the event and trigger-updated head together. Unique operation UUIDs reject duplicate/replayed decisions; expected versions reject stale decisions. After a timeout or uncertain response, reload history and inspect the operation before attempting another decision. Requesting authority is an immediate read-only evaluation, not a durable approval queue or notification workflow.

No raw signed preview receipt, assessment receipt, cookie, password or provider secret is retained in revision snapshots. Proposal content is bounded to 512 KiB and passed through the existing sensitive-data detector before storage. Larger or unsafe proposals fail without partial storage. Ordinary administrative text is still institutional data in a future deployment and needs an approved retention/access policy.

## APIs and UI

All paths below start with `/api/external-confirmations` and require the existing administrator authorization. Writes retain actual session, Origin and CSRF checks. There is no authority input flag.

| Method/path | Behavior |
|---|---|
| GET `/` (empty suffix) | Bounded record/status list; current revision and NOT_RECHECKED evidence status. |
| GET `/records/{record_id}` | Decision chain, proposed/superseded/revoked/current revisions and version. |
| GET `/revisions/{revision_id}` | Digest-checked original/candidate content and historical public evidence. |
| POST `/revisions` | Atomically persist a new proposal; never confirms. |
| POST `/revisions/{id}/validate` | Fresh evidence and actor eligibility; no decision write. |
| POST `/revisions/{id}/request-confirmation` | Same fresh authority evaluation; BLOCKED when providers/mandate are absent. |
| POST `/revisions/{id}/confirm` | Repeat fresh server validation and atomically append authorized confirmation. |
| POST `/records/{id}/revoke` | Fresh independent revocation authority and current-version decision. |

Missing/invalid auth is 401/403; unknown UUID resources 404; stale/duplicate/substituted reviews 409; malformed input 422; missing schema/storage/integrity failures 503. Failed DB diagnostics do not expose SQL parameters. No successful persistence is claimed when tables are unavailable. All DTOs explicitly return `activated: false`; frontend schemas reject fabricated activated/success responses.

The existing administrator page now has a durable ledger separate from the temporary calendar. It lists records, loads immutable revision details/history, compares the selected candidate against the current confirmed row, accepts a decision reason and requests fresh server authority. Confirmation is exposed only after eligible server output for that exact review/selection/version/reason, and the server rechecks on execution. Controls reset after edits, revision selection or reload. The comparison uses original source-row references within a record, not inferred subject or faculty identity; changed row numbering or removed rows still require inspecting the complete snapshots.

History survives page reload while temporary preview receipts are discarded. Loading, unavailable, blocked and rejected operations have honest retry messages. React text interpolation is reused, with no raw HTML or new PDF dependency. D3-D8 remain temporary review/print workflows; their printing does not constitute D9 confirmation. No D9 printer/export feature or confirmation-as-GA-activation action is introduced.

Prototype limits: first 100 records with explicit `has_more`, at most 200 proposals per record, at most 1,000 decision events in a history response. Pagination/archive tooling is not implemented. No proposal deletion/editing, durable authority-request queue, automatic evidence polling, cross-record conflict aggregation, new term registry, resource master data or D10 GA constraint consumer is added.

## Fresh validation and actual browser evidence

Run checks from the repository root with `.\.venv\Scripts\python.exe -B docs/testing/dashboard-d9/run_checks.py <selection>`. The runner records exact subprocess commands, working directories, start/end times, elapsed time, exit code and sanitized output. Its OS environment allowlist excludes database URLs, credentials and approval switches. Test storage is newly owned OS-temp SQLite; no PostgreSQL URL is available to these children. No database URL or private login is placed on command lines or in evidence.

| Selection | Final result | Meaning |
|---|---|---|
| `backend` | 327 passed, 0 failed/skipped, 2 warnings | 26 new D9 cases + 301 D1-D8 API/validation cases; actual FastAPI ASGI auth, isolated SQLite, fictional providers. Includes offline PostgreSQL SQL rendering, not an online migration. |
| `backend-regressions` | 46 passed, 0 failed/skipped, 4 warnings | Existing authentication and GA control-conflict checks. |
| `ga-resource-regressions` | 3 passed, 0 failed/skipped | Existing reset/rollback, room/section conflicts and external/preassignment behavior. |
| `academic-offline` | 85 passed, 0 failed/skipped, 2 warnings | Existing seven-table foundation, deterministic planner and database safety tests; SQLite/offline SQL only. The 17 PostgreSQL cases were not selected. |
| `contracts` | 150 passed, 0 failed/skipped | Seven new D9 frontend contracts plus existing 143. These are not browser tests. |
| `live` | 2 pytest fixtures passed; 16 fixture-qualified browser scenarios passed | Six default-blocked + ten fictional-authorized scenarios against actual Uvicorn/FastAPI, real password/session/CSRF authentication and SQLite persistence. Parent wrappers are not additional cases. |
| `d1-browser` through `d8-browser` | 125 scenarios passed | Actual rendered Edge with synthetic HTTP responses; not backend authorization proof. Counts: 16, 13, 15, 15, 15, 15, 18, 18. |
| `ga-browser` | Final: 51 scenarios passed, 0 failed/skipped; Node parent also passed | Fresh targeted stabilization run below. Initial two attempts each had 50 passed and one screenshot timeout; retained as historical failures. No new GA generation or scoring. |
| `build` | PASS | TypeScript + Vite production build, 229 modules. |
| `lint` | PASS | Focused ESLint for 13 changed/reused frontend files; full-project lint not run. |

D9 policy/API cases cover unconfigured authority, D8 failure, actor/action/expiry/context mismatch, issuer/provider failure, incorrect term/evidence/metadata, stale/replayed requests, cross-session ownership, 401/403/Origin/CSRF/forged flags, immutable SQL UPDATE/DELETE rejection, proposal/supersession/revocation, evidence withdrawal after confirmation, independent process durability, two-connection DB concurrency, concurrent authenticated decisions, rollback after inserted event, corruption errors and frozen migration rendering. The broader D8 suite supplies expired/revoked/stale/wrong-issuer/scope/coverage evidence cases. API concurrency also uses a process-level preview lock; separate-connection trigger testing independently checks database enforcement. Cross-process PostgreSQL races remain unverified.

Actual D9 browser: **Edge 155.0.4283.62**, Node v24.11.1, 1600 x 1200, owned ephemeral `http://localhost:<port>/admin/external-schedules`, no persistent development profile or real institutional credentials. Exact ephemeral URLs, timestamps and individual outcomes are in each `browser-results.json`. Private fixture login configuration travels via stdin only. Default deployment hooks remain absent; authorized fixtures inject two independent fictional providers only inside the test process.

Final run `20261023T102433771189+0800-live`:

| Cases | Expected and observed |
|---|---|
| L01-L03, both fixtures | Real login, canonical import/calendar and fresh D8 assessment; default BLOCKED versus fictional trusted evidence. |
| L04-L05, both fixtures | Store actual SQLite proposal and evaluate independent confirmation authority; default cannot confirm. |
| L06, authorized fixture | Fictional authorized confirmation persisted, no GA activation. |
| L07-L08, authorized fixture | Propose 10:00-11:00 while 09:00-10:00 remains current; fresh successor decision supersedes it. |
| L09, authorized fixture | Authorized revocation preserves three events and restores no older revision. |
| L10, both fixtures | Reload retrieves stored proposal/history without restoring temporary assessment receipts. |

Final D9 workflow captures are [blocked proposal after reload](screenshots/dashboard-d9/20261023T102433771189+0800-live/default-blocked/D9-L10-blocked-proposal-retained.png), [fictional revision comparison](screenshots/dashboard-d9/20261023T102433771189+0800-live/fictional-authorized/D9-L07-fictional-revision-comparison.png) and [fictional revocation/history after reload](screenshots/dashboard-d9/20261023T102433771189+0800-live/fictional-authorized/D9-L10-fictional-history-retained.png). All original 11 PNGs were visually reviewed, followed by the new GA stabilization capture linked below. Early captures with punctuation encoding defects or incomplete fictional workflows are historical evidence only; originals were not edited or represented as final acceptance. Native printing and a new D9-specific mobile layout scenario were not executed; earlier dashboard responsive/print regression cases passed.

## Failures found and retained

Initial lint reported four synchronous effect-state resets in the new component. State resets were moved to selection/refresh handlers and eligibility is bound to current context; lint reruns pass. The first live run failed on a child-environment variable typo before browser execution; it was corrected. The second live run passed the blocked path but hit an asynchronous record/revision-selector race in its fictional-authorized test; the harness now waits for completed history/options before selecting. An encoding mistake in the new component's punctuation was corrected using explicit UTF-8; early screenshots remain unchanged and labelled historical.

D3-D6 initially each rejected the read-only label "Reload confirmation history" as an action matching their no-confirmation-controls check. It now says "Reload ledger history", accurately describing a read; those tests passed unchanged. No authorization behavior was weakened. The initial GA browser run passed 50 of 51 scenarios but timed out capturing a screenshot while other owned browsers were active; the suite was rerun alone and the same screenshot command timed out. Inspection placed this failure after the fitness-analysis assertions and before the cache PNG write. Subsequent scenarios still passed. The targeted stabilization below resolves capture synchronization; both original failed records remain unchanged. Final outcomes and all failed attempts are indexed in the manifest; only final selected runs support acceptance counts.

The academic offline compatibility review identified two assertions that assumed `4c_0001` was still the migration head and that Alembic had only one metadata collection. They now check the additive `d9_0001 -> 4c_0001` chain and both separate metadata collections, retaining the original exact-seven-table and frozen foundation DDL assertions. The first recorded offline run passed 84 and failed the old metadata assertion; the corrected run passed all 85. No foundation model, planner, safety gate or original migration was changed. Historical Phase 4B helpers that target the moving `head` must not be rerun against retained databases; their original revision-specific evidence remains historical.

Warnings retained: Starlette/httpx and AnyIO deprecations; existing Alembic path-separator warnings in authentication regressions; Vite shared static/dynamic readiness import and >500 kB chunk warnings. No unrelated dependency or bundling change was made. No full backend suite, performance benchmark, real-user usability study, native printer, live institutional provider or PostgreSQL acceptance was executed.

## Privacy and preservation

Before evidence writes, existing D8 sanitizers remove complete/truncated receipt fragments, sensitive assignment/header lines and credential URIs from child outputs and JSON trees. The final independent audit also parses decoded JSON, scans complete/partial encoded tokens, signatures, credentials, keys, cookie/header artifacts and password hashes; compares actual faculty names locally without outputting them; inspects PNG ancillary metadata; and visually reviews every capture. Record/revision/event UUIDs and the fictional actor UUID are audit identifiers, not session identifiers. No database file, raw authenticated request dump, HAR, signing key or credential handoff is archived. The final audit/manifest record findings and hashes; hashes prove file identity, not institutional authenticity.

All 23 baselined academic data paths, the protected raw preference hash, identity/qualification/eligibility sources, professor GA code, fitness/RNG/checkpoint code, saved schedules/history, Phase 4C foundation models, original migrations and historical D1-D8 evidence remain byte-identical. Of 786 baselined files, only the six intended integration/test files changed; the other 780 match. The existing protected Git modification remains uncommitted and untouched. Git HEAD/index remain at the starting state, with no staging, commits, push, reset or restore.

## Targeted screenshot stabilization, 2026-10-23 afternoon

The exact failure was `fitness analysis shows original workload, decomposition and preference explanations`, previously at line 761 of `frontend/tests/gaMonitoring.browser.test.mjs`. Its existing assertions passed; `Page.captureScreenshot({format:'png', captureBeyondViewport:false})` then exceeded the existing 30-second CDP deadline. The standalone repeat ruled out an explanation limited to parallel test load. No prior trace/HAR or failed capture PNG existed for these two timeouts; sanitized command records preserve their stacks and all outcomes.

Classification: **browser automation capture lifecycle / test synchronization**, not an observed application or GA regression. The first current-tree instrumented probe found `document.visibilityState=hidden`, `readyState=complete`, loaded fonts, no active animations, a valid 1366 x 900 viewport and stable 2865-pixel document height. The surface command timed out at 30,005 ms; the DOM and layout APIs still responded afterward. A diagnostic `fromSurface:false` alternative returned in 240 ms but visual review found a blank image. That alternative was rejected and is not used in the real test or counted as successful visual acceptance.

A second current-tree probe activated the same target with `Page.bringToFront`, required visible state and waited two animation frames. The original surface capture then completed in **88 ms**, producing a real readable page. Owned-browser target inspection also found welcome/extension pages. They are a plausible source of focus changes; the exact page responsible for the original transition is not established. No claim is made about an Edge internal compositor defect or a measured memory/CPU bottleneck.

Historical D8 command `20261023T003151903542+0800-ga-browser` passed all 51 scenarios with the unchanged script. A fresh disposable copy of the exact pre-D9 HEAD frontend also passed all 51 scenarios when its target was visible, capturing in **104 ms**. Thus the failure was not recorded in the earlier D8 acceptance run; the missing visibility precondition was already present in the old test. The comparison changes no checkout, application source or institutional data. Initial diagnostic setup failed because its disposable tree lacked a local Vite executable; the harness was corrected to use the existing dependency installation. Two controlled-tab experiments, first creating a target and then explicitly bringing that new target forward, could not force the original target into hidden state in this headless environment. Both unmet-precondition failures are retained, not counted as GA acceptance, and do not establish a forced pre-D9 reproduction. The diagnosis relies on the directly observed hidden current-tree failure and foreground recovery; the upstream reason for that original hidden state remains unconfirmed.

The minimum real-test correction adds five lines before the original capture: activate the target, require visible state, await font readiness and two animation frames. It changes no deadline, screenshot options, UI assertion, request fixture, production component, GA implementation or authority path. The successful actual-suite run is [20261023T152412404110+0800-ga-browser](testing/dashboard-d9/20261023T152412404110+0800-ga-browser/command.json): **51 scenarios passed, 0 failed/skipped, plus one passed parent wrapper (Node reports 52)**. The formerly failing scenario passed in approximately 1.065 seconds including its original assertions and screenshot. Its [actual 1366 x 900 screenshot](screenshots/dashboard-d9/20261023T152412404110+0800-ga-browser/GA-fitness-analysis-foreground.png) was visually reviewed and contains only the synthetic account and report values. Capture metadata gives file capture time and explicit synthetic-HTTP attribution; this is not live FastAPI or real GA execution evidence.

Fresh adjacent validation: [150 frontend contracts passed](testing/dashboard-d9/20261023T152354462890+0800-contracts/command.json); Node syntax checking passed for the edited browser test. The backend, academic, build, lint, live D9 and D1-D8 results above are the earlier recorded runs, not newly rerun during this test-only stabilization. Byte comparison against the stabilization baseline verifies the D9 application/security implementation is unchanged. Updated audit, findings and manifest include new diagnostics and hashes without deleting historical failures.

D9 is ready for a separately authorized, reviewed Git checkpoint of its safely testable scope once the final manifest audit passes. PostgreSQL/institutional-authority deployment limitations remain unchanged; no checkpoint approval, commit, push or D10 work is implied.

## Deployment blockers, safe reproduction and next action

Production ledger persistence requires separate approval to provision and migrate a fresh isolated PostgreSQL target, followed by actual acceptance of all D9 constraints/triggers, FK cycles, concurrent transaction/lock-timeout behavior, rollback, restart durability and data-retaining downgrade refusal. The existing **17 Phase 4C PostgreSQL tests remain unverified and were not run**. D9 SQLite tests do not replace them. No online migration command was executed or proposed for a retained Phase 4B/institutional database.

Before institutional use, CCS must approve the real issuer/provider and independent confirmation/revocation actor policy, canonical term/resource ownership, retention/privacy policy, stable evidence revision/revocation semantics and least-privilege database roles. A database owner can defeat trigger guards; deployment must separate migration ownership from runtime access and validate grants/audit/backup procedures. Real provider changes between observation and commit require an institutional consistency/versioning contract; current tests establish bounded point-in-time checks, not distributed atomicity with an external authority.

For safe reproduction, run the evidence runner's `backend`, `contracts`, `build`, `lint` or `live` selection with the local development dependencies available. The live fixture owns its loopback sockets, synthetic accounts, SQLite file and browser profile; do not start the production app with real credentials to reproduce fictional confirmation. Test cleanup stops only its own server/profile; no database cleanup or academic-data write is needed. Without the schema/provider setup, the ordinary page should report ledger unavailable or confirmation BLOCKED, never claim success.

Recommended next action is a separate D9 review and narrowly approved disposable PostgreSQL/authority acceptance plan. **Do not activate constraints or begin D10 until those gaps and the exact confirmed-revision consumer contract are approved.** The supported thesis claim is a tested prototype for durable, independently authorized revision history under synthetic institutional fixtures; it is not verified institutional approval, scheduling-quality improvement, production qualification or GA constraint enforcement.

## Git checkpoint evidence representation

The authorized checkpoint review rechecked the existing test evidence without rerunning tests, reviewed all 93 proposed paths and 12 screenshots, and verified the original 92 artifact hashes before staging. Historical failures and diagnostics remain retained. The protected preference modification is excluded.

This Windows repository uses Git text line-ending normalization. The manifest retains each artifact's raw working-file `sha256` and additionally records `git_blob_sha256` and `git_blob_bytes` for the normalized committed representation. Binary PNG bytes are unchanged. Checkpoint verification compares staged and committed blobs against these additional hashes, preserving the original evidence files and the normal repository whitespace rules. Manifest hashes exclude the manifest itself. Earlier preservation/audit statements describe the pre-checkpoint implementation state; authorized staging and commits subsequently change the Git index and HEAD.
