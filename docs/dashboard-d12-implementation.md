# D12: Department Chair adjustment decisions

Implemented and validated on 2026-10-24, Asia/Manila, from D11 commit `cad837dde9bed38da6427ee3a4106566323dd53d`. D12 provides a complete isolated fictional workflow: faculty submission, scoped Chair review, approval or rejection, durable audit and faculty-visible decision. **Production Chair authority and faculty submission remain BLOCKED. Approval never applies an adjustment, publishes a schedule or runs the GA.** No PostgreSQL connection, migration execution, Git staging, commit or push occurred.

## Authorization and scope

The identity model permits administrator and faculty accounts; it contains no verified Chair appointment or authoritative faculty-department relationship. D12 preserves those account roles and adds an independent server-owned capability boundary. A logged-in administrator alone cannot decide requests.

`chair_authority_service.institutional_chair_directory()` defaults to `None`. A future verified directory must supply a coherent guarded context containing:

- A mandate bound to the exact authenticated account UUID, role `department_chair`, ACTIVE state, canonical department UUIDs, permitted labels, policy reference/digest and aware validity timestamps. Assertion lifetime is at most 300 seconds.
- An exact scope binding for faculty UUID, subject ID, section ID, academic year and term. Labels, aliases, row order, frontend role text and client department filters cannot establish authority.
- Rechecks before returning private data or committing a decision. Lost or changed mandate/scope fails closed. Acquisition failures return a sanitized unavailable response.

Independent authority is required for review, decisions, status and history. Cross-department request IDs return 404; an out-of-scope department filter returns 403. Neither an owner nor an account currently bound to the same faculty identity may approve or reject that request. There is no self-decision policy bypass. Existing session, active-account, Origin and CSRF checks protect decisions.

The real browser fixture explicitly injects fictional Chair, department, schedule and trusted-snapshot providers. It does not install a production provider. Separate backend integration tests execute the actual D8 evidence/issuer, D9 confirmation/history and D10 snapshot-validation code with fictional institutional providers.

## Lifecycle, persistence and audit

The new `faculty_adjustment_decisions` table stores one immutable final decision per request. It references the D11 request/version and authenticated actor, department, operation ID, command digest, explanation, timestamp, exact source revision/constraint digest, validation snapshot and authority/ledger provenance. Canonical payload digests bind the D11 history head and D10 confirmed heads.

Original D11 rows remain SUBMITTED/version 2, and CREATED/SUBMITTED events remain unchanged. Read projections expose `APPROVED_PENDING_APPLICATION` or `REJECTED`, the original base status and a separate decision record. Existing undecided D11 response shapes remain compatible. No APPLIED state, appeals, replacement decision or schedule write is implemented. Historical approval is not a claim of current institutional trust.

Every decision requires a 10-2000 character explanation. Commands bind the reviewed request version, content digest, schedule revision and constraint digest. An exact idempotent replay returns the retained decision when the operation's prerequisites are available; a changed command using the same key returns 409. A different operation cannot replace a final decision.

The additive `d12_0001` Alembic revision follows `d11_0001`. It adds only the decision table and its guards. Immutable update/delete triggers, uniqueness, eligible SUBMITTED/version checks and a D11 withdrawal guard supplement application checks. Downgrade refuses retained decisions. D11 migration bytes are unchanged. Only PostgreSQL SQL rendering was performed; these statements were not executed on PostgreSQL.

SQLite tests explicitly install fixture-owned equivalent guards. Application startup creates no schema. Deployment requires a separately approved D12 migration: request reads on an unmigrated D11 database fail closed rather than pretending no decisions exist. This rollout dependency remains outstanding.

## Transaction and validation boundaries

Approval rechecks the current owner account/binding and D11 immutable history, guarded original schedule identity/revision, academic year/term, owned assignment identity, duration/grid, recognized room/component, full faculty/room/section availability and overlaps, original reconstruction rules and confirmed GEC commitments. Missing coverage is a finding, not assumed availability. Adjacent intervals retain D11's half-open overlap semantics.

The actual D10 deployment catalog/templates and complete D9 ledger are validated through `_read_snapshot` inside the decision transaction. This reuses D8 evidence/issuer and independent D9 confirmation-authority lifecycle checks, input/template fingerprints and current-head provenance. A mismatch between pinned and current constraints blocks approval. No historical VERIFIED label or expired preview receipt grants approval authority. Loss/revocation/change before commit rolls back the decision.

Rejection requires the same current Chair scope, eligible submitted request, immutable source references and explanation, but does not require a currently available scheduling source or approval trust. Its provenance explicitly says `NOT_REQUIRED_FOR_REJECTION`; it does not claim successful scheduling validation.

SQLite uses BEGIN IMMEDIATE for one decision-owned transaction. It does not acquire D10's separate SQLite writer transaction, which would deadlock a ledger read followed by a decision write. PostgreSQL code uses bounded transaction/statement timeouts, owner-before-request row locking consistent with D11, SHARE locks for the ledger read, uniqueness and database triggers. D11 withdraw refreshes the locked parent and checks for a retained final decision. Concurrent contradictory decisions or approval/withdrawal cannot both succeed in the isolated tests. Backend race tests use separate SQLAlchemy sessions, a simultaneous start barrier and independent directory contexts that deliberately do not serialize writers; database transaction/guard safety is not inferred solely from a fixture authority lock. **PostgreSQL locking, triggers, deadlocks and transaction isolation remain unverified.**

## API and dashboard

All Chair endpoints use the existing authenticated session:

| Endpoint | Behavior |
|---|---|
| `GET /api/chair-reviews/access` | Fresh capability and permitted department choices; no role escalation |
| `GET /api/chair-reviews` | Department-scoped pending queue; optional inclusion of final decisions |
| `GET /api/chair-reviews/{id}` | Original/proposed meetings, justification, revisions, current findings and eligibility |
| `GET /api/chair-reviews/{id}/history` | Retained immutable decision history within verified scope |
| `GET /api/chair-reviews/{id}/status` | Effective status and decision without schedule mutation |
| `POST /api/chair-reviews/{id}/approve` | Fresh validated authorization, pending application |
| `POST /api/chair-reviews/{id}/reject` | Explained final rejection |

The queue fails rather than returning a silently partial result above 1000 submitted records. It is not an unlimited production pagination implementation.

`/chair/requests` uses the current teal/gold styling, account/session UI and typed API client. A shared account-menu link appears only after a server capability check. Ordinary authenticated accounts see an authority error and no decision controls. The page includes department filtering, pending/final history, permitted faculty UUID, original/proposed details, source references, conflict findings, explanations, confirmation dialog, retry/loading/empty states and responsive layout. Imported text renders as React text; no raw HTML injection is used.

The existing faculty request page shows the decision, timestamp, explanation and pending-application warning. It hides withdrawal after a final decision. Original request history and normal draft/submission/withdrawal behavior remain intact. My Schedule is unchanged. One D11 browser button label and the D2 browser request allowlist were updated for the Chair-review label and read-only capability probe; no broader schedule API access was allowed.

## Exact implementation inventory

Created application and test files (19):

- `backend/chair_models.py`
- `backend/migrations/versions/d12_0001_chair_decisions.py`
- `backend/routers/chair_reviews.py`
- `backend/schemas/chair_reviews.py`
- `backend/services/chair_authority_service.py`
- `backend/services/chair_decision_projection.py`
- `backend/services/chair_review_service.py`
- `backend/tests/dashboard/chair_restart_child.py`
- `backend/tests/dashboard/chair_sqlite.py`
- `backend/tests/dashboard/test_chair_live.py`
- `backend/tests/dashboard/test_chair_migration.py`
- `backend/tests/dashboard/test_chair_reviews.py`
- `backend/tests/dashboard/test_chair_trust.py`
- `frontend/src/api/chairDecisions.ts`
- `frontend/src/api/chairReviews.ts`
- `frontend/src/components/common/ChairReviewLink.tsx`
- `frontend/src/pages/chair/Requests.tsx`
- `frontend/tests/chairReviews.live.mjs`
- `frontend/tests/chairReviews.test.mjs`

Modified existing files (12):

- `backend/main.py` - register the Chair router.
- `backend/migrations/env.py` - register additive model metadata.
- `backend/routers/adjustments.py` - expose optional faculty decision status.
- `backend/services/adjustment_service.py` - decision projection and transactional withdrawal guard.
- `backend/tests/academic/test_academic_foundation.py` - assert the new migration head and metadata; original seven-table checks remain.
- `backend/tests/dashboard/test_adjustments.py` - install D12 schema/guards in the owned D11 fixture.
- `frontend/src/api/adjustments.ts` - strictly validate optional final-decision projections.
- `frontend/src/components/common/AccountMenu.tsx` - conditional verified Chair link.
- `frontend/src/pages/faculty/AdjustmentRequests.tsx` - final decision display and correct controls/messages.
- `frontend/src/routes/AppRoutes.tsx` - Chair page route.
- `frontend/tests/adjustments.live.mjs` - renamed submit button only.
- `frontend/tests/mySchedule.browser.test.mjs` - allow the exact read-only Chair capability probe; GET-only and own-schedule restrictions remain.

Documentation/evidence additions are this report, the preservation baseline, `run_checks.py`, `audit_evidence.py`, command records, manifest and genuine D12 PNGs/browser result records. The [manifest](testing/dashboard-d12/manifest.json) lists every reviewed artifact and raw SHA-256, excluding itself.

## Fresh validation

Run from the repository root with `.\.venv\Scripts\python.exe -B docs/testing/dashboard-d12/run_checks.py <group>`. The runner records exact commands, cwd, timestamps, duration, status and sanitized output. Child environments contain whitelisted OS variables; database credentials/URLs and approval flags are not inherited. Backend tests use unique owned OS-temp roots. Browser credentials travel privately via stdin, never command arguments or evidence.

| Group | Fresh result | Evidence scope |
|---|---:|---|
| `focused` | 42 passed | Actual FastAPI auth/authorization and SQLite transactions, offline migration rendering, real D8-D10 validation with fictional issuers |
| `d11-backend` | 33 passed | Original D11 lifecycle, ownership, reconstruction, persistence and migration regression |
| `backend` | 327 passed | Existing D2-D9 APIs/validation |
| `backend-regressions` | 46 passed | Authentication and GA control, including the existing real browser wrapper |
| `academic-offline` | 85 passed | Foundation/planner/safety; no PostgreSQL execution |
| `ga-resource-regressions` | 3 passed | Existing reset, resource and preassignment behavior |
| `v1-fixtures` | 4 passed | Actual current-release V1 checkpoint continuation fixtures |
| `v2-engine` / `v2-api` | 30 / 18 passed | Existing constrained engine and real API regressions |
| `contracts` | 189 passed | 15 new D12 contracts plus 174 previous frontend contracts; no browser/auth proof |
| `d12-live` | 12 scenarios passed | Actual Edge/React to owned FastAPI/SQLite; fictional Chair/scope/schedule/trusted snapshot providers |
| `d11-live` | 12 scenarios passed | Actual Edge/FastAPI/SQLite regression |
| `browser-regressions` | 125 scenarios passed | D1-D8 synthetic HTTP browser regression |
| `ga-browser` / `v2-browser` | 51 / 12 scenarios passed | Existing synthetic HTTP GA/V2 browser regression |
| `live` / `v2-live` | 16 / 6 scenarios passed | Existing D9/D10 Edge/FastAPI/SQLite regression |
| `build` | PASS | TypeScript and production bundling |
| `lint` | PASS, zero errors/warnings | Focused changed application TypeScript/TSX |

Scenario counts exclude Node parent tests and pytest wrappers: D12 is 12 scenarios, 13 Node test records and one pytest wrapper, not 26 independent scenarios. Previous browser coverage totals 222 scenarios. D12 makes no claim of production or PostgreSQL acceptance.

The 12 D12 browser scenarios cover anonymous denial, real faculty submission/unauthorized API access, scoped Chair review/safe text, explained confirmed approval, faculty pending-application visibility/schedule preservation, explained rejection, no withdrawal/replacement, stale approval denial, concurrent contradictory HTTP decisions, mobile durable history, authenticated ordinary-account denial and safe retry without private cached rows. Screenshots use Edge 155 and fictional records only. Final screenshots are in the latest successful D12 browser directory identified by the manifest.

Focused backend coverage additionally includes cross-department IDOR/filter denial, self-decision, wrong/expired/revoked mandates, drafts/withdrawals, optimistic reference mismatch, invalid terms, faculty/room/section/GEC conflicts, missing availability, component rules, CSRF/extra fields, fresh-process authenticated decision reads, database immutability, concurrency with withdrawal, authority-loss rollback and idempotency mismatch. Fresh trust loss tests exercise actual D8 issuer/evidence, D9 confirmer/revocation and D10 digest checks.

### Retained failures and warnings

No failed record or intermediate screenshot was deleted:

- Initial D12 and existing auth browser runs timed out at DevTools `Runtime.enable` in the sandbox. Equivalent owned local browser execution outside it passed without timeout increases or disabled tests.
- Two academic assertions expected the D11 migration head/metadata. They were updated only for the additive D12 schema and all 85 cases passed afterward.
- The D2 browser wrapper initially rejected the new capability-probe path even though its 13 scenarios passed. Its exact GET-only allowlist now includes that path and the full 125-scenario D1-D8 rerun passed.
- A concurrent broad D9 browser run passed all 16 scenarios but one wrapper failed during owned Uvicorn shutdown, with Windows connection-reset diagnostics. The unchanged suite was rerun separately: both pytest wrappers and all 16 scenarios passed with clean shutdown; the final result is retained in the manifest. This teardown instability remains a test-infrastructure risk, not evidence of a failed D9 application scenario.
- Visual review caught an intermediate D11 message incorrectly saying no approval had occurred after a decision, and a clipped mobile status. Final code corrects both. Intermediate PNGs remain historical, superseded by final screenshots.

Existing warnings remain visible: Starlette TestClient/httpx compatibility, AnyIO BlockingPortal alias, Alembic `path_separator` deprecation during offline SQL rendering, and existing Vite dynamic/static import and large-bundle warnings. No dependency or unrelated code cleanup was performed.

## Preservation, privacy and deployment limits

The [pre-edit baseline](testing/dashboard-d12/preservation-baseline.json) contains 1043 files. Exactly the 12 approved D12 integration paths differ; the other 1031 baseline files remain byte-identical, including all 23 academic data paths, protected preferences, professor GA modules, numerical fitness/scoring/RNG/elitism, V1/V2 execution/fingerprint sources, six historical checkpoints, saved schedules, history, original migrations and D1-D11 historical evidence. The Git index, HEAD and last-fetched origin/main remain unchanged. The pre-existing protected preference modification remains local and untouched.

D12 service code contains no GA generation or schedule-write calls. Existing GA regression suites do execute fictional runs/checkpoints inside owned temporary fixtures; they do not activate institutional constraints or change retained artifacts. SQLite decision tests write only their owned fixture databases. No PostgreSQL operation, production database operation or real credential use occurred.

Evidence is sanitized before writing, then independently checked for complete/truncated receipt fragments, encoded tokens, credentials, private keys, bearer/header assignments, decoded JSON strings and private faculty names compared locally without exporting them. PNG checks verify CRCs and absence of text/EXIF metadata; original screenshots receive visual privacy review. No raw SQLite databases, session payloads, HARs or production faculty rows are archived. The final audit passed: zero privacy findings, 92 artifact hashes verified, 19 original screenshots visually reviewed with clean CRC/metadata checks, and all five nonzero command records retained. The manifest excludes its own hash.

Remaining acceptance: the 17 Phase 4C PostgreSQL tests, D9-D12 PostgreSQL migrations/triggers/concurrency, and D10 PostgreSQL locking remain unverified. Genuine Chair appointment, department ownership and schedule/term/resource providers require independently verified institutional integration. SQLite success does not establish PostgreSQL behavior. No ordinary account or client metadata can enable production approval.

Recommended next action: review the D12 implementation/evidence before any separately requested Git checkpoint, then define the verified provider and isolated PostgreSQL acceptance rollout. Any later schedule application needs its own versioned, atomic revalidation/publication workflow with current trust and audit. It is not implemented or started here; neither is C++ work.
