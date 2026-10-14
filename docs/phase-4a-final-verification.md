# Phase 4A final authentication, authorization and security verification

Date: 2026-10-15 (Asia/Manila). Repository: `ImohangAngkol/CCS-Faculty-Scheduling-System`, branch `main`.

## Assessment

**PASS WITH LIMITATIONS.** Backend ownership is enforced independently of CSRF: a valid faculty login, allowed Origin and correct session CSRF token cannot read/update another faculty's record. One confirmed frontend session-response race was reproduced and corrected. Final commands/results are recorded below; this is a prototype verification, not production security certification.

**Git readiness:** ready for a careful review and selective commit after approval, **not for committing the current index blindly**. The existing index contains partial Phase 4A versions, essential files remain untracked, and `backend/data/faculty_preferences.json` is a pre-existing user-data change to exclude from a code commit unless separately approved. Nothing was staged, committed, pushed, reset or reseeded by this verification.

## Implemented features inspected

- PostgreSQL identity models and migration `4a_0001`: stable faculty UUID mirror, unique normalized accounts, role/binding checks, unique faculty FK, active flags, database-backed sessions and timestamps.
- Explicit faculty import/first-admin bootstrap; no automatic migrations or predictable production accounts.
- Argon2id credential verification, HttpOnly/SameSite cookies, Secure by default with explicit loopback development exception, session expiration, logout and account-change revocation.
- Allowed-Origin checks and session-bound CSRF protection on unsafe authenticated operations; no client role/faculty header establishes identity.
- Backend ownership for faculty profile/eligibility/preferences; admin dependencies on account management, settings, GA controls, chromosome/history/fitness/report/export resources.
- Frontend role-aware login, protected portals, verified account binding, account administration and session-expiration handling. Faculty preferences do not guess a default identity.
- Atomic JSON preferences and original eligibility/component validation remain unchanged.

Source inspection included `backend/main.py`, `database.py`, `identity_models.py`, `identity_admin.py`, `migrations/env.py`, `migrations/versions/4a_0001_identity.py`, `schemas/auth.py`, authentication routes/service, preference authorization/routes, faculty routes, frontend AuthContext, ProtectedRoute/AppRoutes, auth/session clients, faculty preferences and existing authentication tests. Administrative router inclusion protects all legacy parallel GA/chromosome/history routes; the existing exhaustive test enumerates 39 administrative operations.

## Automated ownership verification

The new `backend/tests/test_phase4a_final_verification.py` contains **23 cases**. Its fixtures create a temporary SQLite database with foreign-key enforcement and temporary preference/settings files. The first isolated admin account is created directly in that disposable database; faculty accounts for registered codes 1 and 2 are then created through the real authenticated administrator API. Login produces genuine session cookies and CSRF values. Only database connections/file destinations/configuration are isolated; credential verification, session lookup, role/ownership dependencies, Origin and CSRF checks remain enabled. No principal or authorization dependency override is installed.

| Requirement | Verified behavior |
|---|---|
| Faculty 1 reads own preferences | HTTP 200; returned record has faculty_code 1. |
| Faculty 1 updates/reloads own preferences | HTTP 200; saved values reload; Faculty 2 record remains unchanged. |
| Faculty 1 reads Faculty 2 | HTTP 403 from backend ownership dependency. |
| Faculty 1 updates Faculty 2 with valid CSRF | HTTP 403 with `You may only update your own faculty preferences.` |
| Invalid CSRF versus ownership | Invalid nonce returns the security-check message; valid nonce reaches ownership and returns a different message. Both preserve stored bytes. |
| Rejected updates preserve data | Entire temporary preference-file SHA-256 is unchanged; Faculty 2 can still retrieve the original values. |
| Spoofed role/faculty headers/body/URL | Headers do not grant access; another faculty UUID is denied; identity fields in preference payload are rejected. |
| Administrator permitted actions | Can read/edit both faculty preferences and priority, list/reset preferences, read/write supported settings, and read GA status without starting a worker. |
| Faculty forbidden administration | List/create users, modify another account, change own/other roles or bindings, settings changes and GA start are all denied with valid CSRF. Accounts/storage remain unchanged. |
| Account changes revoke sessions | Password, role and faculty-binding updates revoke the affected account's existing session; unrelated sessions remain usable and account UUID is retained. |
| Duplicate/conflicting bindings | Duplicate username/binding returns 409; unregistered identity returns 422; existing accounts and registry identities are unchanged. |
| Anonymous/origin/CSRF rejection | Anonymous requests return 401; forbidden origins/missing nonce return 403; preferences are unchanged. |

The existing identity suite independently covers administrator/faculty login, invalid credentials, disabled/expired sessions, logout/revoked-token rejection, cookie flags and rotation, constraints/migrations, imported UUID stability, concurrency/corrupt preference storage, exact-origin configuration and early authentication database release for streaming responses.

## User-reported manual checks

These are **reported by the user**, not relabelled as this audit's automated evidence:

1. Administrator login succeeded.
2. Faculty account creation succeeded.
3. Faculty login succeeded.
4. Faculty 1 GET own preferences returned 200.
5. Faculty 1 GET Faculty 2 preferences returned 403.
6. Faculty preference changes survived refresh.
7. Faculty opening `/admin/accounts` displayed Access unavailable.
8. Faculty GET `/api/auth/users` returned 403.
9. Logout followed by GET `/api/auth/me` returned 401.

The reported cross-faculty PUT returned 403 with `Session security check failed. Reload and try again.` That establishes CSRF rejection, not independent ownership rejection. This audit does not guess whether the supplied nonce was missing, stale, or from another session. The new properly authenticated test proves the separate ownership gate.

Read-only probes against the available local backend additionally returned `/api/health` 200 and anonymous `/api/auth/me` 401. Response bodies were omitted. No live preference write, login with existing credentials, account mutation or database migration was attempted.

## Confirmed defect and correction

**FINAL-AUTH-001 / BUG-010 ? delayed prior-session 401 invalidates a newer frontend login. Severity: MEDIUM (session UX/availability; no backend authorization bypass).**

Reproduction: start a request under session A, establish session B while it is pending, then deliver A's 401. Both fetch and Axios dispatched `ccs-session-expired` despite the newer valid session. AuthContext handles that signal by clearing the current account. Two transport regression cases failed before correction (`events.length` was 1 instead of 0); current-session expiration control cases already passed. The delayed-response signal was reproduced automatically; a simultaneous account-switch race was not manually exercised against real PostgreSQL.

Root cause: the shared API client checked only whether a CSRF value currently existed, without identifying which session issued the failed request.

Minimal correction: `setSessionSecurity` increments an in-memory revision only when the session CSRF value changes. Fetch captures that revision when issuing the request; Axios associates it with request configuration in a private WeakMap. A 401 signals expiration only if its request revision is still current. Axios bookkeeping is removed on completion and no tracking field/header/token is sent to the server. Current-session 401 behavior remains active. No authentication or permission check was disabled.

Regression: `frontend/tests/authSessionRace.test.mjs` tests old-session and current-session 401 behavior for both transports. All four cases pass after the correction. The existing real-server browser flow confirms genuine revocation still returns to login.

No backend ownership/session/role enforcement defect was reproduced. Missing MFA/SSO/audit/production qualification are limitations, not invented fixed security bugs.

## Exact verification commands and results

All commands run from repository root unless frontend cwd is specified. Repeated runs are not added to totals.

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_phase4a_final_verification.py backend/tests/test_phase4a_auth.py -q --disable-warnings -k 'not real_browser' --tb=short --maxfail=2
# 61 passed, 1 deselected, 4 warnings, 36.33 seconds (23 new + 38 existing).

# frontend cwd, before the fix:
node --test tests/authSessionRace.test.mjs
# 2 passed, 2 failed: both delayed previous-session 401 cases.

# frontend cwd, after the fix:
npm.cmd run test:auth
# 8 passed (four existing contracts + four race regressions).
npm.cmd run test:preferences
# 22 passed.
npm.cmd run test:ga
# 48 passed.
npm.cmd run build
# Passed; 129 modules, existing >500 kB bundle warning (751.57 kB JS after fix).

# frontend cwd:
.\node_modules\.bin\eslint.cmd src/context/AuthContext.tsx src/services/auth.ts src/services/apiSession.ts src/routes/ProtectedRoute.tsx src/routes/AppRoutes.tsx src/pages/Login.tsx src/pages/admin/Accounts.tsx src/pages/admin/PreferencesReview.tsx src/pages/faculty/Preferences.tsx src/api/preferences.ts src/api/faculty.ts src/api/subjects.ts
# Passed, zero findings; apiSession.ts also linted after its correction.
```

The existing genuine FastAPI/Edge browser test and preference/GA browser regressions were rerun after the transport fix:

```powershell
# repository root; fresh dedicated temporary pytest directory:
.\.venv\Scripts\python.exe -m pytest backend/tests/test_phase4a_auth.py::test_real_browser_identity_and_preferences -q -s --disable-warnings --tb=short --basetemp=C:/Users/User/AppData/Local/Temp/phase4a-final-security-browser-96a3df18-b37a-4c38-a60e-75f5e55ffbe3
# 1 backend integration case passed, 3 warnings, 19.12 seconds.
# Its real FastAPI/Edge flow: 13 Node results passed (12 scenarios + parent).

# frontend cwd:
npm.cmd run test:preferences:browser
# 23 results passed (22 scenarios + parent), 22.12 seconds.
npm.cmd run test:ga:browser
# Initial run: 50 passed, 2 failed, 76.11 seconds.
# One screenshot command timed out in the fitness-analysis scenario;
# the parent wrapper also counted as failed. Application assertions had passed.
# Unchanged-code rerun: 52 passed (51 scenarios + parent), 69.09 seconds.
```

Final distinct totals: **62 backend cases** (61 focused + one real-browser integration), **78 frontend contracts/models** (8 auth + 22 preference + 48 GA), and **88 browser results including parent wrappers** (13 + 23 + 52). The real-browser flow is reported in both layers for clarity, not added twice to a grand total. The four new race regressions initially had two expected reproduction failures and now all pass. No unresolved assertion failure remains.

The screenshot timeout is a browser capture/tool incident, not a demonstrated fitness or scheduling defect. Its exact renderer/OS cause was not verified; it remains a test-reliability limitation. No arbitrary timeout increase or GA/fitness/report modification was made to hide it. Their isolated credentials/data are disposable, not existing PostgreSQL records. The in-app browser connection was attempted through the browser skill and failed because sandbox metadata was unavailable; the existing Edge harness was used. This audit does not claim in-app browser verification.

## Git readiness and private-data inspection

At start, `main` was at `a91edb2`. Numerous prior Phase 4A changes were staged, unstaged or untracked. They were preserved. Important examples: staged `main.py`/`apiSession.ts` differ from their latest working versions; `backend/services/auth_service.py` and identity tests/setup reports were still untracked. Committing only the existing index would omit necessary files and recent corrections.

| Pending group | Classification / review action |
|---|---|
| Backend identity/auth/migrations, .env.example, requirements | Phase 4A source/configuration template. Example URL/password fields are placeholders. Include reviewed final source versions, not only old staged blobs. |
| Frontend login/context/routes/account/preferences/shared clients | Phase 4A application changes; this verification adds session-response revision tracking. |
| Existing GA/browser/audit test fixture edits | Prior Phase 4A security adaptation and storage/synchronization fixes; review as tests, not GA equation changes. |
| Existing roadmap/bug report and Phase 4A reports/setup docs | Phase status and verification documentation; keep claims scoped to evidence. |
| backend/data/faculty_preferences.json | Pre-existing live/user preference change, not created by this verification. Preserve locally and exclude from a source commit unless explicitly approved. |
| New final verification tests/report | This verification's scope; include after review. |

A bounded credential-pattern scan of pending tracked/untracked text found no private-key blocks, GitHub/AWS token patterns, literal Argon2 hashes or non-placeholder database URL candidates. Matched values were never printed. This heuristic scan is not proof that no possible secret exists; human review is still required. No pending `.env`/local DB/checkpoint/history artifact path was detected. Ignore rules were checked for `.env`, backend `.env`, frontend `.env.local`, SQLite files, run checkpoints and generation snapshot files. No private environment file contents or credentials were inspected/printed.

`git status --short`, working-tree/index `git diff --check`, protected-file hashes and an index fingerprint were checked. Final integrity results below distinguish pre-existing work from this turn's changes.

## Files modified by this verification

1. `backend/tests/test_phase4a_final_verification.py` ? new 23-case real-session ownership/admin verification.
2. `frontend/src/services/apiSession.ts` ? minimal confirmed stale-401 session fix.
3. `frontend/tests/authSessionRace.test.mjs` ? four regression cases.
4. `frontend/package.json` ? include race tests in `test:auth`.
5. `docs/phase-4a-final-verification.md` ? this report.
6. `docs/system-bug-report.md` ? record BUG-010 and current closure totals.
7. `docs/implementation-roadmap-status.md` ? synchronize current defect count and link this verification; no requirement status/phase advancement.

All other pending files belong to earlier development work or the user's manual changes. No backend production implementation, GA mathematics/operators/weights/RNG, checkpoints/history, notebook, UUID registry or preference data was changed here. Existing PostgreSQL accounts were neither connected to for mutations nor reset/reseeded. Temporary fixtures do not migrate the real database.

## Remaining limitations

- Automated relational tests use SQLite plus existing offline PostgreSQL migration SQL. User-reported PostgreSQL login/account tests are useful evidence, but online PostgreSQL migration/locking/last-admin concurrency, privilege provisioning, restart recovery and production load are not independently verified in this pass.
- One backend process remains necessary for GA admission, JSON preference locking and local login throttling. No multi-worker guarantee is inferred.
- Established streams authenticate at admission; logout/revocation governs subsequent requests and does not cancel a valid server GA. Cross-tab account changes can require reload to refresh CSRF/account context.
- HTTPS/Secure cookies, deployment origin/proxy settings, backups, institutional credential policy and edge throttling remain deployment acceptance work. MFA/SSO/self-service password recovery and comprehensive audit history are absent.
- Focused lint/build passed; the prior full-repository lint's three errors/eight warnings in untouched files are historical findings, not a newly executed full-lint pass. The existing large frontend bundle warning remains.
- This pass does not rerun the entire long GA optimization regression suite or start a production GA. Earlier Phase 4A results are documented separately; current preservation evidence is source/data hashes and relevant frontend monitoring regressions.
- Approval is still required before any staging/commit/push. No such operation was performed.

## Final preservation and Git checks

`git status --short` identifies the prior staged/unstaged/untracked Phase 4A work plus this report/tests/fix. Working/index `git diff --check` both passed, with ordinary LF/CRLF notices only. A SHA-256 fingerprint of `git ls-files --stage` is identical to the start-of-verification fingerprint: no staged blob or index entry changed. HEAD remains `a91edb2`; no commit/push occurred.

All **143 protected baseline files are byte-identical**, with no new files in application data/checkpoint/saved-history/notebook directories. This includes the user's already-modified faculty_preferences.json and unchanged faculty UUID registry. Tests only mutated temporary SQL/JSON data. Existing PostgreSQL records were not modified or reset; no online mutation connection was made.

Current phase counts are unchanged. The latest bug inventory is ten confirmed defects, ten fixed within documented scope, zero unresolved confirmed defects. This final verification discovered/fixed only BUG-010; prior defect closures are historical evidence. Production qualification and the explicitly unconfirmed browser-capture cause remain limitations.
