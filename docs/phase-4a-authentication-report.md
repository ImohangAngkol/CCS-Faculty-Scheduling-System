# Phase 4A identity, authentication and authorization

Scope: PostgreSQL identity foundation, verified administrator/faculty login and ownership-checked JSON preference saving. No Phase 4B/3G, voting, fitness weight experiments, term migration, C++, commit or push.

## Repository and safety findings

At the audit start, branch `main` and the working tree/index were clean. Commit `a91edb2` contained Phase 3F.2. SQLAlchemy/Alembic/psycopg2 were installed dependencies, with no runtime DB models, migrations or verified account provider. The eleven stable faculty UUIDs already existed in `faculty_identities.json`. Preference authorization was deliberately fail-closed; other administration APIs were public. Frontend role labels and portals had no authenticated routing.

The Windows PostgreSQL 18 service was running. The owner chose **isolated tests and documented setup**, so this implementation did not connect to it or run online PostgreSQL migrations. This is a production PostgreSQL code path with portable isolated relational tests, not a claim of verified online deployment. [Local setup](phase-4a-local-setup.md) supplies explicit reviewed migration/import/bootstrap commands.

## Database schema

| Table | Keys, constraints and purpose |
|---|---|
| `faculty_identities` | Existing faculty UUID PK; unique display code; name. Explicit registry mirror import, no automatic allocation/renumbering and no external instructor account. |
| `users` | UUID PK; unique normalized lowercase username/email; Argon2id hash; role check; unique nullable faculty FK with RESTRICT. Faculty requires a binding; administrator requires no binding. Active flag and UTC created/updated timestamps. |
| `login_sessions` | UUID PK; unique SHA-256 hash of opaque random cookie token; indexed user FK with CASCADE; random CSRF token; UTC created/expires timestamps. Database rows provide restart persistence and logout/revocation. |

Migration revision `4a_0001` explicitly creates these tables. UUID PKs are genuine relational identifiers, not the old numeric adapter. Model defaults assign account/session UUIDs and timestamps; explicit registry import preserves faculty PKs. No GA storage is migrated. Upgrade/downgrade were exercised against disposable SQLite and compiled to PostgreSQL SQL offline; live PostgreSQL constraints, transaction locks and deployment are not yet exercised.

The bootstrap command reads temporary environment-supplied credentials, hashes passwords, is idempotent for an existing active admin, refuses conflicting accounts/second bootstrap usernames, and uses a PostgreSQL advisory transaction lock. It does not run at startup. Identity import refuses conflicting registry records. No real credentials are saved in the repository.

## Authentication design

`POST /api/auth/login` verifies Argon2id credentials against the database, rejects disabled accounts, throttles attempts and rotates the browser's existing session. The opaque cookie is HttpOnly, SameSite=Lax, Path=/ and Secure by default; insecure cookies are explicitly limited to loopback HTTP development. Session duration is configurable from 60–86,400 seconds, default eight hours. Unknown users perform password verification against a random dummy hash and receive the same failure message as wrong credentials/disabled accounts.

`GET /api/auth/me` verifies the database session, expiration and current account activity, then returns trusted role, stable faculty binding/legacy adapter and a session-bound CSRF value. No password hash or session token is returned in JSON. Faculty binding lookup never invents a default when unavailable. `POST /api/auth/logout` deletes the session and expires the browser cookie. Account password/role/binding/active updates revoke all that user's sessions.

Every protected unsafe request requires an allowed exact Origin and matching CSRF token. Login itself requires an allowed Origin to prevent login CSRF. Cookie credential requests use explicit CORS credentials without wildcards. Private responses are no-store and nosniff; validation responses omit submitted values so passwords cannot be echoed. SQL errors expose a bounded 503 message rather than connection strings/parameters. Identity database connect/statement/lock timeouts are five seconds; authentication DB dependencies close before a streaming response begins so a long GA console does not pin a database connection. Authorization validates each new request; changing browser values never changes identity.

Frontend stores the CSRF value and account in memory only; the authentication token stays in the HttpOnly cookie. The existing GA sessionStorage entry remains only a run/process reference, not an authentication credential. Session initialization and authentication calls have a 15-second request bound and explicit service/DB errors. Authenticated 401 responses return to login; 403/422/503 saves retain their draft. An expired/revoked session unmounts private pages; unsaved drafts are not persisted into browser storage.

## API permission matrix

| Resource | Public | Faculty | Administrator |
|---|---|---|---|
| Root, health, API schema/docs | Yes, no private records | Yes | Yes |
| Login | Allowed Origin, credentials, throttle | Same | Same |
| Current account; logout | 401 | Own session | Own session |
| Account list/create/update | 401 | 403 | Yes; explicit binding/last-active-admin checks |
| All faculty records/list | 401 | 403 | Yes |
| Faculty profile and eligible subjects | 401 | Own stable UUID or matching numeric adapter only | Any registered normal faculty |
| Offered subject metadata | 401 | Yes, browsing metadata does not grant eligibility | Yes |
| All preferences; GA settings GET/PUT | 401 | 403 | Yes |
| Individual preferences GET/PUT | 401 | Own only; cannot change priority | Any normal faculty; administrative priority permitted |
| Preference DELETE/reset | 401 | 403 | Yes |
| GA status, logs, result, start/stream/pause/resume/stop | 401 | 403 | Yes |
| Saved/uploaded chromosomes and analysis/downloads | 401 | 403 | Yes |
| Generation history, schedule/fitness inspection, comparison, exports | 401 | 403 | Yes |

Whole-router dependencies protect all GA/chromosome/history/report endpoints including legacy parallel start/upload routes. Faculty/preferences routes have operation-specific ownership/admin dependencies. The exhaustive route test checks all administrative operations from the live OpenAPI inventory, rather than testing only the newest endpoint. Existing scheduling services do not know about authentication.

## Faculty preferences and frontend experience

Login routes administrators and faculty to their verified portal. Protected layouts show current-account identity and a logout action. Faculty preferences take the binding exclusively from `/me`; no identity prop, URL code or local storage value selects another faculty. The existing ranking/calendar UI and backend eligibility/component validators are retained. Administrator review remains explicitly privileged; the old unconfigured-auth banner is replaced with an administrative-permission explanation.

Account Administration provides create, bind/rebind, enable/disable, role change and password reset operations. Database uniqueness/FKs prevent a faculty identity from being shared by unrelated accounts. The last active admin cannot be disabled/demoted; locking active admins serializes concurrent admin changes in PostgreSQL. Full faculty CRUD, schedule publishing, published personal schedules, student/class-list access and audit-event history are outside Phase 4A.

All clients now use one configured API base, cookie credentials and session-bound CSRF headers, including POST SSE, recovery controls, uploads/analysis and exports. Native fetch Headers preserve existing GA process headers. The admin-only GAProvider is mounted only inside an authenticated admin portal; anonymous/faculty users do not begin GA recovery polling. Logout revokes access but does not cancel a server GA or delete its checkpoints.

## Changed files

- Backend identity: `database.py`, `identity_models.py`, `identity_admin.py`, `alembic.ini`, `migrations/env.py`, `migrations/versions/4a_0001_identity.py`, `schemas/auth.py`, `services/auth_service.py`, `routers/auth.py`.
- Backend integration: `main.py`, `services/preference_authorization.py`, `routers/faculty.py`, `routers/preferences.py`, `requirements.txt`, root `.env.example`.
- Frontend: `App.tsx`, `context/AuthContext.tsx`, `routes/AppRoutes.tsx`, `routes/ProtectedRoute.tsx`, `pages/Login.tsx`, `pages/admin/Accounts.tsx`, admin/faculty layouts, `components/common/AccountMenu.tsx`, administrator preference review, faculty preferences, API/session/auth transports and existing faculty/preferences/subjects/GA/recovery/history/fitness clients.
- Tests: `backend/tests/test_phase4a_auth.py`, legacy regression principal fixture in `tests/conftest.py`, updated protected-read audit and fresh-process log fixture; frontend auth contracts/browser integration, existing preference API/browser and GA monitoring/continuation browser fixtures; frontend package script.
- Documentation: this report, local setup, roadmap status and bug report.

No operator, scorer, GA generation service, preference storage/validation implementation or checkpoint format was edited. The existing durable-marker fault-injection test also receives a boundary Event so a cold checkpoint operation does not cause premature fixture teardown (BUG-008).

## Complete changed-file inventory

- `.env.example`
- `backend/alembic.ini`
- `backend/database.py`
- `backend/identity_admin.py`
- `backend/identity_models.py`
- `backend/main.py`
- `backend/migrations/env.py`
- `backend/migrations/versions/4a_0001_identity.py`
- `backend/requirements.txt`
- `backend/routers/auth.py`
- `backend/routers/faculty.py`
- `backend/routers/preferences.py`
- `backend/schemas/auth.py`
- `backend/services/auth_service.py`
- `backend/services/preference_authorization.py`
- `backend/tests/conftest.py`
- `backend/tests/test_ga_logs.py`
- `backend/tests/test_ga_pause_resume.py`
- `backend/tests/test_phase4a_auth.py`
- `backend/tests/test_system_audit.py`
- `docs/implementation-roadmap-status.md`
- `docs/phase-4a-authentication-report.md`
- `docs/phase-4a-local-setup.md`
- `docs/system-bug-report.md`
- `frontend/package.json`
- `frontend/src/App.tsx`
- `frontend/src/api/faculty.ts`
- `frontend/src/api/preferences.ts`
- `frontend/src/api/subjects.ts`
- `frontend/src/components/common/AccountMenu.tsx`
- `frontend/src/context/AuthContext.tsx`
- `frontend/src/layouts/AdminLayout.tsx`
- `frontend/src/layouts/FacultyLayout.tsx`
- `frontend/src/pages/Login.tsx`
- `frontend/src/pages/admin/Accounts.tsx`
- `frontend/src/pages/admin/PreferencesReview.tsx`
- `frontend/src/pages/faculty/Preferences.tsx`
- `frontend/src/routes/AppRoutes.tsx`
- `frontend/src/routes/ProtectedRoute.tsx`
- `frontend/src/services/apiSession.ts`
- `frontend/src/services/auth.ts`
- `frontend/src/services/fitnessReporting.ts`
- `frontend/src/services/gaHistory.ts`
- `frontend/src/services/gaRecovery.ts`
- `frontend/src/services/gaService.ts`
- `frontend/tests/auth.browser.integration.mjs`
- `frontend/tests/auth.test.mjs`
- `frontend/tests/gaMonitoring.browser.test.mjs`
- `frontend/tests/gaPausedRecovery.integration.mjs`
- `frontend/tests/preferenceApi.test.mjs`
- `frontend/tests/preferences.browser.test.mjs`

## Verification ledger

Verification uses **409 distinct backend cases** across the following suites; repeats are not added to totals. The combined Phase 3B?3E invocation initially had one test-harness deadline failure (BUG-008); its corrected focused rerun passed. This is not presented as an uninterrupted all-green combined invocation.

| Check | Executed result |
|---|---|
| Phase 4A identity/session/role/schema/migration/configuration/stream-DB scope tests | 38 passed; browser case excluded from this invocation |
| Genuine FastAPI + Edge administrator account creation, login/refresh/logout and faculty save/ownership/revocation | 1 backend integration case passed; 13 Node browser results including the parent wrapper |
| Preference integrity/validation, system audit, metadata and fitness reporting | 118 passed |
| Selection, preassignments, hard gates, API crossover and toggle policy | 109 passed |
| Existing Phase 3B?3E backend combined invocation | 141 passed, 1 failed, 1 browser deselected, 2,125.62 seconds; failure is the reproduced test-only BUG-008 |
| Corrected BUG-008 marker-boundary regression | 1 passed in final focused rerun (49.11 seconds; earlier corrected run 66.83 seconds); completes the 142 distinct non-browser lifecycle/history cases |
| Existing genuine server/Edge pause ? refresh ? same-population resume | 1 passed, 92.15 seconds |
| Fresh-interpreter checkpoint/log continuation with explicit temporary history | 1 passed, 41.29 seconds; repeat of an existing lifecycle case, not an extra case in totals |
| Frontend preference/model/API contracts | 22 passed |
| Frontend GA/history/log/fitness/display contracts | 48 passed |
| New frontend auth/transport contracts | 4 passed |
| Existing preference browser fixtures | 23 results passed (22 scenarios + parent) |
| Existing GA monitoring/history/report browser fixtures | 52 results passed (51 scenarios + parent) |
| Frontend production build | Passed, 129 modules; existing >500 kB bundle warning (751.40 kB JS) |
| Focused lint on changed production frontend modules | Passed, zero findings |
| Full repository lint | 3 existing errors + 8 warnings in untouched GAContext/FacultyManagement/RoomAssignments/ScheduleView; not claimed passing |
| PostgreSQL migration SQL | Offline upgrade/downgrade passed; no online database connection |
| Integrity | 141/141 protected baseline files byte-identical; no new protected-area files; remaining fingerprinted modules have no Git diff |
| Diff whitespace checks | Working/index checks passed; normal LF/CRLF Git notices |

There are 74 frontend model/contract tests. Browser-result counts include their parent wrappers and are reported separately from backend test counts to avoid double-counting the real-server cases. The new real-browser case uses actual FastAPI credential/session endpoints with temporary SQLite/JSON storage; it overrides only DB connections. Existing GA behavior suites explicitly supply a trusted principal within test fixtures, while the identity suite separately exercises anonymous/faculty denial for all administrative operations.

Two test-only integration issues were diagnosed: changing `AUTH_ALLOWED_ORIGINS` after importing the app did not rebuild startup CORS, and older GA mocks indexed headers as plain objects after the transport adopted native Headers. Both fixtures were corrected, along with an asynchronous recovery-notice assertion and an obsolete faculty-profile placeholder expectation. The in-app browser could not connect (sandbox metadata unavailable); the existing isolated Edge harness was used. The first browser launch also needed a dedicated temporary pytest directory because the shared directory had incompatible Windows ACLs.

## Integrity and limitations

The protected-source/data hash check covers GA code, all existing data files, notebook files, checkpoints and saved histories/schedules. The final check found all 141 baseline files byte-identical, no new files remaining in protected data/checkpoint/saved/notebook areas, and no Git diff in the remaining fingerprinted publication/faculty-analysis modules. BUG-009 initially created one new test-only history bundle through the original preloaded subprocess script; after verifying its test provenance, that bundle was preserved intact in temporary storage. The corrected fixture sets child history storage explicitly, and its focused regression passed. No original schedule, checkpoint, preference or historical record was deleted, moved or rewritten. Authentication tests use temporary database/preference storage. The legacy subprocess isolation defect and its correction are documented above; it was caught by the final protected-area audit. PostgreSQL online verification remains a local acceptance step explicitly deferred by the owner; there are no hidden automatic migrations or credentials.

Deployment still requires one API worker because GA admission, diagnostic buffers, login throttling and atomic JSON preference locks are process-local. Sessions themselves are durable database records. The limiter is bounded to 4,096 keys and ten attempts per username/client pair per five minutes; distributed throttling and institutional abuse monitoring remain deployment work. Expired sessions are removed on login; a dedicated retention/maintenance job is future work.

No MFA/SSO, invitation/email verification, self-service password recovery, comprehensive audit-event table, published faculty schedule access, account deletion or term-aware scheduling database exists yet. Established long-running streams authenticate at admission; revocation affects subsequent requests and does not kill an ongoing valid GA. CSRF does not protect against application XSS. Database backups, HTTPS/reverse-proxy configuration, credential rotation and production deployment qualification are still required.

Recommended next work: perform the documented local PostgreSQL acceptance, then scope term-aware relational management and identity audit/recovery. Phase 3G voting requires that accepted identity deployment and a separately approved voting/aggregation design. Phase 4B/3G was not started.

## Current roadmap and defects

The original 56 R groups now contain 41 COMPLETE AND VERIFIED, 5 IMPLEMENTED BUT NOT FULLY TESTED, 6 PARTIALLY IMPLEMENTED, 3 UI PLACEHOLDER ONLY, 1 NOT IMPLEMENTED and 0 BLOCKED. R47 is a partial identity-only PostgreSQL foundation; R48 is implemented with online PostgreSQL acceptance pending; R54 is a partial verified-account view without academic profile editing. The 12 N groups and 12 overlapping future F groups remain separate. No percentage is used.

Nine confirmed defects are documented: six application defects and three test-harness defects. All nine are fixed within their stated scope; zero confirmed defects remain unresolved. BUG-004 closes real account/role/ownership integration; BUG-008 synchronizes the durable-marker fault-injection test without changing checkpoint behavior; BUG-009 explicitly isolates child-process history writes. Existing lint findings, deployment limitations and unconfirmed issues are not concealed by these totals.
