# Phase 4A local identity setup (Windows / PowerShell)

This release adds PostgreSQL **accounts and sessions only**. CSV/JSON faculty inputs, preferences, GA checkpoints, saved schedules and generation history remain in their original locations. Nothing runs migrations or creates accounts on application startup. The development tree was clean on `main`; Phase 3F.2 was already committed as `a91edb2` before this work.

The PostgreSQL 18 Windows service was running during development. At the owner's request, verification used isolated SQLite databases and temporary JSON files, plus PostgreSQL offline migration SQL. No connection, migration, account creation or data change was made to that PostgreSQL instance. Complete the steps below before using real local accounts.

## 1. Select an isolated local database

Use VS Code to open the repository and PowerShell in its root. Install PostgreSQL and pgAdmin if needed. In pgAdmin, connect to your **local development** PostgreSQL server. Do not select an institutional/production database.

In pgAdmin's Login/Group Roles dialog, create a dedicated role such as `ccs_identity_dev`: permit login, supply a unique private password, and leave superuser, replication, create-role and bypass-RLS privileges off. Create a new database such as `ccs_identity_dev` owned by that role. Keep this database separate from other projects. A production deployment should separate the schema migration owner from the runtime role with only the required DML permissions.

The SQL equivalents are shown only as placeholders; replace private values locally, never commit or paste real credentials into chat:

```sql
CREATE ROLE ccs_identity_dev LOGIN PASSWORD '<PRIVATE_DATABASE_PASSWORD>';
CREATE DATABASE ccs_identity_dev OWNER ccs_identity_dev;
```

## 2. Install packages and configure the process

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Set-Location frontend
npm.cmd ci
Set-Location ..
```

The existing frontend dependencies suffice. The added backend authentication dependency is `argon2-cffi>=25.1.0,<26`. SQLAlchemy, Alembic and psycopg2 are already listed.

Set the backend environment in a private terminal. The password prompt keeps the value out of command history:

```powershell
$identityDbSecret = Read-Host 'Local identity database password' -AsSecureString
$identityDbPassword = [Net.NetworkCredential]::new('', $identityDbSecret).Password
$identityEncodedPassword = [Uri]::EscapeDataString($identityDbPassword)
$env:DATABASE_URL = 'postgresql+psycopg2://ccs_identity_dev:' + $identityEncodedPassword + '@localhost:5432/ccs_identity_dev'
$env:AUTH_ALLOWED_ORIGINS = 'http://localhost:5173'
$env:AUTH_COOKIE_SECURE = 'false'
$env:AUTH_SESSION_SECONDS = '28800'
Remove-Variable identityDbPassword, identityEncodedPassword, identityDbSecret
```

Environment variables are process secrets, not a secrets manager. Do not print the database URL. Alternatively copy `.env.example` to a private ignored `.env`, replace placeholders, restrict its filesystem access, and explicitly use `uvicorn --env-file .env` for startup. Alembic and the CLI read process environment; they do not automatically load `.env`.

Allowed origins are exact comma-separated origins without a trailing slash. CORS is loaded at backend startup: restart the backend after changing it. Use **localhost for both frontend and backend**; mixing `localhost` and `127.0.0.1` breaks SameSite browser cookies. Cross-port localhost works. The frontend defaults to `http://localhost:8000`.

For a different backend port, create an ignored `frontend/.env.local` with `VITE_API_URL=http://localhost:<PORT>` and restart Vite. For deployment behind a same-origin reverse proxy, set `VITE_API_URL=` before building and forward `/api` and `/preferences` to FastAPI. Use HTTPS, `AUTH_COOKIE_SECURE=true`, an exact HTTPS `AUTH_ALLOWED_ORIGINS` and one backend worker. Third-party cross-site cookie deployments are not supported by the Lax-cookie design.

## 3. Inspect and apply the explicit migration

Verify the database selected above in pgAdmin before running commands. No command should use an existing production database.

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head --sql
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini current
```

Expected revision: `4a_0001`. It creates `faculty_identities`, `users`, `login_sessions` and Alembic's version table. It does not import GA data. The first command only renders SQL without a database connection.

The migration has a downgrade, but it **drops identity/account/session tables**. Back up first; use `downgrade base` only for a disposable identity database. PostgreSQL schema transactions support rollback when the upgrade fails. This phase did not exercise an online PostgreSQL migration against the local service.

## 4. Import stable identities and bootstrap the first administrator

```powershell
.\.venv\Scripts\python.exe backend\identity_admin.py import-faculty --confirm-local-identity-database
$env:BOOTSTRAP_ADMIN_USERNAME = Read-Host 'First administrator username or institutional email'
$identityAdminSecret = Read-Host 'Unique administrator password (at least 12 characters)' -AsSecureString
$env:BOOTSTRAP_ADMIN_PASSWORD = [Net.NetworkCredential]::new('', $identityAdminSecret).Password
try {
    .\.venv\Scripts\python.exe backend\identity_admin.py bootstrap-admin --confirm-local-identity-database
} finally {
    Remove-Item Env:BOOTSTRAP_ADMIN_USERNAME, Env:BOOTSTRAP_ADMIN_PASSWORD -ErrorAction SilentlyContinue
    Remove-Variable identityAdminSecret
}
```

Import is idempotent, adds missing registry UUIDs, and rejects conflicting names/display codes without overwriting them. All eleven normal optimization identities are mirrored; external Palad is excluded. Bootstrap is explicit and does not install predictable credentials. Repeating it for the existing active admin leaves the password unchanged. A different admin must subsequently be created through authenticated account administration; bootstrap cannot replace or promote an existing faculty account. A PostgreSQL transaction advisory lock serializes bootstrap commands.

## 5. Start the application

In the backend terminal with the environment above:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
Set-Location frontend
npm.cmd run dev -- --host localhost --port 5173 --strictPort
```

Open `http://localhost:5173/login`. Avoid reload mode while qualifying GA continuation, and do not use multiple backend workers: existing JSON preference locks and GA worker admission are process-local. Preserve the pinned Python/package/runtime environment needed by older checkpoints.

## 6. Create and bind faculty accounts

Sign in as the first administrator. Open **Accounts**. Choose **Create a new account**, enter a unique username/email and private password, select **Faculty**, and select the matching faculty identity by display code/name. Save. The API rejects duplicate faculty bindings, duplicate normalized usernames, unknown/external IDs and inconsistent role/binding combinations.

Edit an account through the same page to change its binding, disable it, change its role or set a new password. Every update revokes that account's existing sessions. An admin cannot disable/demote the last active administrator. Administrator accounts have no faculty binding. Account deletion, email invitation, institutional SSO, self-service password reset, MFA and account-event audit history are future work.

## 7. Manual acceptance

1. Visit an admin URL while logged out: it redirects to login. An anonymous direct API PUT remains HTTP 401.
2. Log in as admin. Check Accounts, Preferences, Generate Schedule and Generation History. Inspect pages without starting a production GA.
3. Sign out; reload an admin page and confirm login is required.
4. Log in with a bound faculty account. Confirm faculty navigation and the correct display code/profile. Preferences load from `/api/auth/me`'s verified binding, never a client-supplied Faculty 0 default.
5. Change a subject preference or disable a preference flag. Save; reload. Confirm the saved value and eligible-subject filter. Do not stretch events; component durations remain locked.
6. As faculty, navigate to `/admin/preferences`: access is unavailable and no admin editor mounts. Direct requests for another faculty's preferences/eligibility return 403; writes leave the file unchanged. Changing URL/local storage/body IDs cannot change the server principal.
7. From a separate administrator session, disable the faculty account. Its next protected request must return 401 and the browser must return to login. Re-enable it and sign in again with a new session.
8. Use a deliberately short allowed session lifetime (minimum 60 seconds) in a disposable environment to check expiration. Restore the intended lifetime and restart.

## Troubleshooting

| Symptom | Check / correction |
|---|---|
| Identity database 503 | Verify private `DATABASE_URL`, PostgreSQL service, role/database permissions, installed driver and explicit Alembic revision. No fallback database is silently created. |
| Login says invalid credentials/account unavailable | Username is trimmed/lowercased; check private password and active status. Disabled/nonexistent/wrong-password failures deliberately share a message. |
| Login succeeds but refresh is anonymous | Use localhost consistently; check cookie Secure versus HTTP and browser cookie settings. Restart after configuration changes. |
| Browser reports authentication service unavailable | Inspect failed request and exact CORS origin, frontend API URL and backend port; backend CORS configuration is fixed at startup. |
| Security check failed on save | Reload to obtain the current session CSRF value; confirm browser origin is allowed. Never bypass verification or add a client role header. |
| Faculty binding unavailable | Import registry identities, correct binding through Accounts, and sign in again. Do not guess faculty index/code. |
| Preference storage 503 | Preserve corrupt/unreadable bytes; investigate ACLs and backups. Authentication does not reset JSON or bypass validation. |
| 429 login throttled | Wait five minutes. The limiter is bounded and process-local; institutional deployments need edge-level throttling as well. |
| Old script receives 401/403 | It now needs a real session cookie, authorized role, allowed Origin and CSRF token for writes. There are no anonymous parallel write routes. |
| Cannot recover the only admin credential | Restore access using an approved database/backup procedure. Bootstrap will not overwrite an existing admin password; no insecure recovery backdoor is provided. |

## Isolated verification commands

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_phase4a_auth.py -q
Set-Location frontend
npm.cmd run test:auth
npm.cmd run test:preferences
npm.cmd run test:ga
npm.cmd run test:preferences:browser
npm.cmd run test:ga:browser
npm.cmd run build
```

The identity pytest module uses temporary SQLite tables with FK enforcement, actual Argon2 password/session requests, and temporary preference JSON. Its browser case launches a real isolated FastAPI server and Edge/Vite; no principal override or PostgreSQL connection is used in that case. Other GA behavior suites explicitly override a verified admin principal to continue testing scheduling behavior, with authorization separately tested against every administrative route. On Windows, use a new dedicated `--basetemp=<TEMP>\phase4a-<UNIQUE_ID>` if the shared pytest temporary directory has incompatible ACLs. Browser tests require an installed Edge/Chromium binary and permission to start it.
