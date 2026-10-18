# Phase 4B.1: browser acceptance readiness and proposed execution

## Current acceptance outcome (documentation update 2026-10-18)

**All six scenarios P4B-B01–P4B-B06: PASS — USER CONFIRMED.** The user reports completion in the recovered synthetic fixture. **Screenshots: NOT CAPTURED for every scenario; automated browser execution: NOT ESTABLISHED; original manual test timestamps: NOT RECORDED.** No screenshots were taken and no originals can be archived. The [final written-only report](manual-acceptance-results.md) and [manual manifest](manual-acceptance-manifest.json) are the current acceptance record.

B06 was an **injected fixture HTTP 503**, not a physical PostgreSQL outage. The user confirms removal of `ready.unavailable` and recovery of the same faculty session with Compact / Very High preserved. Earlier automated evidence and counts are unchanged; Codex did not execute or independently observe the manual browser tests.

**Historical plan boundary:** all subsequent readiness, authorization, NOT RUN and proposed-command sections retain their meaning at the time of Stage A/offline recovery preparation. They are preserved history, superseded for current acceptance status by the written report above. Do not treat them as instructions to repeat setup, rotate credentials, reseed accounts or run the pristine recovery gate against the now-populated database. No additional service, database or fixture operation is required for this written-only review.

## Historical readiness and offline authorization snapshot

Updated 2026-10-18, Asia/Manila. **STAGE A OFFLINE VERIFIED; INITIAL STAGE B SETUP USER CONFIRMED; SIX BROWSER SCENARIOS NOT RUN. RECOVERY IMPLEMENTED / OFFLINE VERIFIED, LIVE RECOVERY NOT AUTHORIZED.** The user reports initial database/fixture/frontend setup succeeded, followed by process exit and handoff removal; the retained database passed five user-performed read-only checks. Codex did not execute that setup or query its live database. See the [recovery report](stage-b-recovery-offline.md); the [Stage A report](stage-a-fixture-preparation.md) remains historical. Initialization commands below are reference-only for a new EMPTY target. Do not rerun them on the retained database. Use the separate recovery section after live approval.

## Verified evidence and warnings

The [user-executed PostgreSQL record](20261018T100533+0800-postgresql-e2beb33f.json) reports **14 passed, zero failed, zero skipped, three warnings**, pytest duration **12.23s**, runner elapsed **13.660s**, exit 0. It ran 2026-10-18 10:05:33.735990 to 10:05:47.395945 +08:00. Codex inspected the artifact; Codex did not execute this successful database run.

The command includes `--disable-warnings`, and the output contains only the warning count. **The three individual warning messages/categories cannot be recovered from this artifact.** They must remain unidentified rather than be invented. Static inspection finds a possible Alembic deprecation: `backend/alembic.ini` has `prepend_sys_path` without `path_separator`; installed Alembic's `config.py` contains the corresponding legacy-splitting warning. Attribution to this run remains UNCONFIRMED, and the other messages are unknown. No FastAPI/Pydantic warning attribution is supported by the record. Do not rerun the database suite against its now-nonempty database solely to recover warnings. If the original terminal has detailed warning text, archive a sanitized supplement; otherwise capture warnings during a later independently approved disposable execution without claiming they reconstruct this run.

The successful suite verifies the asserted identity tables/revision `4a_0001`, constraints, synthetic import, account binding, real authentication, sessions across fresh Python/ASGI processes, revocation, valid-CSRF ownership, concurrency, row-lock timeout and sanitized injected unavailability. It does not establish browser behavior, production readiness or the PostgreSQL server version (not recorded in this JSON). Earlier skips and the two setup errors remain historical artifacts.

## Historical fixture limitation and Stage A correction

Before Stage A the helper used the original test URL/gate and `pg_acceptance.__wrapped__()`. It could not reuse the now-nonempty successful database or select another target. Stage A removed this coupling: `tests.phase4b_browser_safety` has a separate exact gate; `phase4b_browser_support` constructs and seeds a synthetic app. The original acceptance helper and fourteen-case module remain unchanged. Initialization still requires an empty target; the new separate recovery gate accepts only the exact pristine seeded profile, without reset/reseed.

Leave `ccs_ga_phase4b_test` and its role/data unchanged. The prepared fixture accepts only database `ccs_ga_phase4b_browser_test`, restricted role `ccs_ga_phase4b_browser_tester`, variable `PHASE4B_BROWSER_DATABASE_URL`, and `127.0.0.1:5432`. Their actual existence/connectivity was not checked in Stage A. No reset/drop/reseed of the successful database is proposed.

## Stage A architecture (implemented); Stage B execution requires approval

1. Independent exact browser gate rejects wrong/missing targets, original acceptance database, query overrides, privileged roles, wrong owner, unexpected/nonempty schemas and objects. Connections start read-only with timeouts. No fallback or change to the original gate.
2. Dedicated setup/seed functions retain real password/session/Origin/CSRF/ownership checks. A second empty-target preflight precedes future Alembic. Initialization requires an explicit flag and Stage B approval; it was not executed in Stage A.
3. Synthetic dataclasses/UUIDs/labels replace all copied real faculty fields. The catalog and initial preferences are empty. Two identities and one administrator will be seeded; faculty accounts are created through the UI. This scope proves style/account workflows, not course/calendar behavior.
4. Fourteen reader/writer aliases are asserted under one private temporary root. Both generation and resume are blocked and the registry is fresh. No reload/workers/child backend. Future children would require their own explicit isolation.
5. Windows ACLs are applied and verified on the new private directory for current user/SYSTEM/Administrators; the actual owned-temp ACL regression passed. The ACL child receives no DB URL variables. Only owned handoff/control files are cleaned; synthetic storage/database remain for review. No service/process stop commands are used.
6. Offline verification passed 93 browser safety/fixture/evidence/original-safety cases, 61 auth cases and 78 frontend contracts. Initial ACL-script parser failure and reruns are preserved in the [report](stage-a-fixture-preparation.md). Fake engines and in-memory SQLite/ASGI are not real PostgreSQL/browser acceptance; Stage B remains unverified.

The [Stage A report](stage-a-fixture-preparation.md) lists implemented files. No production GA/model/checkpoint source or original successful PostgreSQL test/safety helper was changed.

## Required storage and process isolation

All destinations must resolve under one newly owned OS-temp root. Assert them before accepting HTTP requests; do not rely on a normal application launch command.

| Data/access path | Required target / current inspection |
|---|---|
| `routers.preferences.PREFERENCE_FILE` | Synthetic `preferences.json`; patched by dedicated browser support |
| `routers.preferences.GA_SETTINGS_FILE` | Temporary `settings.json`; already patched |
| `ga_service.FACULTY_PREFERENCES_FILE`, `FitnessFunction.PREFERENCE_FILE` | Same temporary preference file; already patched |
| Both `ga_service` / `FitnessFunction` settings paths | Same temporary settings file; already patched |
| `ga_checkpoint_service.CHECKPOINTS_DIR` | Temporary `checkpoints/`; already patched |
| `ga_history_service.SNAPSHOTS_DIR` | Temporary `history/`, including analysis sidecars/exports; already patched |
| `ga_control_service.STOPPED_RUNS_DIR` | Temporary `stopped/`; already patched |
| `routers.genetic_algorithm.LATEST_RESULT_FILE` | Temporary `latest.json`; already patched |
| `routers.chromosomes.LATEST_RESULT_FILE` | Redirected to the same temporary latest result; offline reader regression passed |
| `chromosome_service.SAVED_CHROMOSOME_DIR`, `BEST_CHROMOSOME_PATH`, `UPLOADED_CHROMOSOME_PATH` | Temporary saved/best/upload paths; already patched |
| Identity/session database dependencies and any direct engine access | Only verified browser database; no live/default URL fallback |
| Account credentials, ready/stop/fault markers | User-owned OS-temp, outside repository; no screenshot/log disclosure |
| Browser cookies/storage/downloads | Dedicated browser profile and owned temporary downloads; no existing development-session reuse |

Existing academic datasets may be loaded read-only internally; no writes or real profiles are permitted in responses/screenshots. All listed aliases now have redirects and offline assertions; actual PostgreSQL/browser startup remains unverified. Session writes use only the supplied engine (in-memory SQLite in offline tests). React/Vite does not write backend JSON. Use a single owned backend without reload/workers; never launch an unpatched backend with these credentials.

## Proposed commands: do not execute before approval

### A. Provision only the new, verified empty browser target

First use an authorized administrator connection on the verified maintenance database to inspect server address/port and the existence/ownership of the two proposed objects. Stop if either object already exists or belongs to unexpected data; do not use `IF NOT EXISTS`, reset or reuse automatically. Do not change `ccs_faculty_scheduling_dev` or `ccs_ga_phase4b_test`.

After explicit approval, on that verified administrator connection:

```sql
CREATE ROLE ccs_ga_phase4b_browser_tester
    LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS;
CREATE DATABASE ccs_ga_phase4b_browser_test
    OWNER ccs_ga_phase4b_browser_tester;
```

Set the new role's password privately with psql's interactive `\password ccs_ga_phase4b_browser_tester` on the administrator connection, or pgAdmin role properties. No password-bearing SQL, URL on command line, transcript or repository secret file. Do not grant membership in the acceptance role or privileges on the successful database.

In the dedicated browser-backend PowerShell terminal, configure the new environment privately (do not enable transcription or print variables):

```powershell
Set-Location -LiteralPath 'C:\Users\User\Desktop\Genetic-Algorithm Dashboard'
$phase4bBrowserCredential = Get-Credential -UserName 'ccs_ga_phase4b_browser_tester' -Message 'Disposable browser database password'
$phase4bBrowserPassword = $phase4bBrowserCredential.GetNetworkCredential().Password
$env:PHASE4B_BROWSER_DATABASE_URL = 'postgresql+psycopg2://' + 'ccs_ga_phase4b_browser_tester:' + [Uri]::EscapeDataString($phase4bBrowserPassword) + '@127.0.0.1:5432/ccs_ga_phase4b_browser_test'
Remove-Variable phase4bBrowserPassword, phase4bBrowserCredential
$env:PYTHONDONTWRITEBYTECODE = '1'
```

The URL remains only in this process's environment and its owned children. Keep the original acceptance variable unchanged; the updated helper must not read it. Credentials must be available privately to the actual execution process; a variable in another terminal is not automatically inherited.

### B. Read-only preflight, then approved owned backend startup

These helper functions are implemented. Run this read-only check from the privately configured terminal before the separately approved Stage B writing run. It invokes no migration.

```powershell
@'
import json, sys
sys.path.insert(0, 'backend')
from tests.phase4b_browser_safety import (
    SafetyError, designated_browser_url, inspect_empty_browser_database,
)
try:
    print(json.dumps(inspect_empty_browser_database(designated_browser_url())))
except SafetyError as error:
    print(str(error))
    sys.exit(1)
'@ | .\.venv\Scripts\python.exe -
```

Only after this passes and Stage B approval is in place, start the prepared helper. Do not create its parent directory beforehand: the helper must create and secure a NEW directory itself.

```powershell
$phase4bPrivate = Join-Path $env:TEMP ('phase4b-browser-' + [guid]::NewGuid().ToString())
$phase4bReady = Join-Path $phase4bPrivate 'ready.json'
.\.venv\Scripts\python.exe docs/testing/phase-4b/serve_browser_fixture.py --ready-file $phase4bReady --allow-browser-database-initialization
```

The backend reserves its own IPv4 ephemeral socket before DB changes and hands that same socket to Uvicorn. The private ready file contains actual `http://localhost:<port>`, synthetic administrator credential, browser database name and instance ID. Verify `/__phase4b_fixture` matches the handoff before browser input. No database password is in the handoff; never dump the whole file. Bind/setup failure stops only this fixture. Isolation assertions precede migration/seed/readiness. Without the initialization flag the helper stops before connecting/binding.

### C. Dedicated React frontend

In a second dedicated terminal, privately provide the ready-file path chosen above:

```powershell
Set-Location -LiteralPath 'C:\Users\User\Desktop\Genetic-Algorithm Dashboard'
$phase4bReady = Read-Host 'Owned browser-fixture ready-file path'
$env:VITE_API_URL = (Get-Content -LiteralPath $phase4bReady -Raw | ConvertFrom-Json).backend
Push-Location frontend
npm.cmd run dev -- --host localhost --port 5189 --strictPort
```

Use `http://localhost:5189`, not a different hostname, so frontend/backend cookies share the intended site. Backend CORS/Origin checks must allow only this origin; `AUTH_COOKIE_SECURE=false` applies only to the owned loopback fixture. `--strictPort` must fail on a collision, not switch to another app's port. Do not change an existing frontend's environment or stop its service. The backend and frontend URLs/ownership must be independently verified before browser input.

## Six scenarios and genuine screenshot procedure

Use the installed Computer Use skill and its current supported tooling after approval; automation availability and actual browser version are not verified by this planning task. Use an isolated browser profile so localhost cookies do not interfere with development sessions. Obtain the generated administrator credential privately without logging it; create the synthetic faculty account through the real Accounts UI using an independently chosen private test password.

| ID | Procedure / required observed outcome | Proposed screenshot name (not yet created) |
|---|---|---|
| P4B-B01 | Administrator creates synthetic faculty account and binds the intended synthetic identity; observe successful list/binding after save | `P4B-B01-account-bound.png` |
| P4B-B02 | Faculty selects Compact / Very High, saves, fully refreshes, and sees both persisted | `P4B-B02-preferences-refreshed.png` |
| P4B-B03 | Administrator signs in and reviews the same faculty's saved preference; unrelated synthetic record remains unchanged | `P4B-B03-admin-preference-review.png` |
| P4B-B04 | Faculty navigates to `/admin/accounts`; observe denial with no account list | `P4B-B04-faculty-admin-denied.png` |
| P4B-B05 | Faculty logs out and navigates to protected preferences; observe authentication requirement and record actual URL | `P4B-B05-protected-sign-in.png` |
| P4B-B06 | In a valid isolated session, inject the owned fixture's unavailable marker; observe actionable database-unavailable UI; remove marker and verify recovery | `P4B-B06-injected-unavailable.png` |

For P4B-B06, write only the validated handoff's same-stem `.unavailable` marker under owned OS-temp. Do not stop PostgreSQL, revoke credentials, lock institutional tables or touch another service. Label evidence **injected fixture 503**, not physical PostgreSQL outage. The dependency/fault/recovery path passed offline ASGI regression; actual React presentation remains unverified.

Clear password fields and close credential dialogs, developer tools and unrelated/private chrome before captures. Use genuine tool screenshots, never generated images or edited success states. Archive under a new run directory in `docs/screenshots/phase-4b/`; filenames above are planned, not existing evidence. Record actual browser/tool/version, viewport, application URL, ISO timestamp with `+08:00`, scenario steps, expected/observed results, fixture scope and SHA-256. Privacy-review every image; retain original/redacted hashes with provenance if redaction is needed. Store no credentials, cookie/header dumps or private faculty records. When automation is unavailable, record BLOCKED and use the same steps for explicitly attributed USER CONFIRMED evidence.

Stop only the owned Vite terminal and backend via its same-stem `.stop` marker (30-minute backend deadline also applies). The helper removes only its own private temporary handoff/markers after clean server shutdown; retain the new synthetic database for review. No database drop, reset, migration downgrade or disposal is authorized by the browser run. Preserve the successful original acceptance database throughout.

## Approval and readiness decision

Stage B administrator preflight (read-only, on a verified authorized maintenance connection; do not run creation yet):

```sql
BEGIN READ ONLY;
SELECT current_database(), current_user, host(inet_server_addr()), inet_server_port();
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls
FROM pg_roles WHERE rolname = 'ccs_ga_phase4b_browser_tester';
SELECT datname, pg_get_userbyid(datdba) AS owner
FROM pg_database WHERE datname = 'ccs_ga_phase4b_browser_test';
ROLLBACK;
```

If either object exists, stop for explicit ownership/data review; no automatic reset, grant, ALTER or reuse. If both are absent and Stage B provisioning is approved, use the creation/password commands above, then privately set the browser variable and run its read-only gate. Never put a password in SQL history or echo a database URL.

For owned fault/stop controls in the operator terminal, first confirm `$phase4bReady` is the exact private ready file created for this run, with matching fixture instance ID. These commands are **Stage B only**, never service-wide operations:

```powershell
$phase4bFault = [IO.Path]::ChangeExtension($phase4bReady, '.unavailable')
Set-Content -LiteralPath $phase4bFault -Value ''
# Observe/capture the injected 503, then recover this fixture only:
Remove-Item -LiteralPath $phase4bFault
# After acceptance/captures, stop only the owned backend:
Set-Content -LiteralPath ([IO.Path]::ChangeExtension($phase4bReady, '.stop')) -Value ''
```

Capture real PNGs through supported Computer Use after URL/identity verification and approval. No capture script runs in Stage A. After visually reviewing an actual PNG, the prepared `record_browser_evidence.record_capture` function can record its hash/metadata. It requires the image and new JSON sidecar in the same directory, a supported scenario/observer, actual timestamp with offset, browser/version, actual local URL, expected/observed text and explicit privacy review. It refuses overwrite and returns **CAPTURE RECORDED - ACCEPTANCE REVIEW PENDING**, never an automatic PASS. Update the run's acceptance matrix only after observing/reviewing the actual result. Example structure (fill actual observations, not placeholders; do not execute before Stage B):

```python
import sys
from pathlib import Path
sys.path.insert(0, 'docs/testing/phase-4b')
from record_browser_evidence import record_capture
record_capture(
    Path('docs/screenshots/phase-4b/<actual-run>/P4B-B02-preferences-refreshed.png'),
    Path('docs/screenshots/phase-4b/<actual-run>/P4B-B02-preferences-refreshed.json'),
    scenario='P4B-B02', observer='CODEX_BROWSER',
    observed_at='<actual ISO timestamp with +08:00>',
    browser='<actual browser and version>',
    url='http://localhost:5189/faculty/preferences',
    expected='Compact and Very High remain saved after full refresh',
    observed='<actual observed result>', privacy_reviewed=True,
)
```

Use `USER_CONFIRMED` for user-performed observations. Image dimensions are recorded from the PNG; record viewport/tool version separately when the capture surface differs. Hashing does not prove that a screenshot is genuine or privacy-safe. Clear credential fields before capture; never generate/reconstruct a screenshot or archive the private handoff. The backend retains synthetic storage/database after stop; no database cleanup/drop/downgrade is part of Stage B.

**PostgreSQL acceptance: PASS, user-executed evidence inspected. Stage A: OFFLINE VERIFIED. Initial Stage B setup: USER CONFIRMED. All six browser scenarios: NOT RUN. Recovery: OFFLINE VERIFIED, live execution pending approval.** Do not reset either retained database, weaken initialization emptiness or manually rerun migrations. The following recovery workflow supersedes new-target setup for the retained browser database only.

## Recovery of the retained browser database (offline prepared)

Current authorization covers implementation/offline tests only. The user confirmed exact read-only target, revision `4a_0001`, two declared synthetic identities, one active unbound synthetic administrator and zero sessions. Actual catalog reflection/ownership/privileges must still pass the implemented live preflight. No administrator login or scenario has completed. Earlier process exit has a plausible 30-minute deadline mechanism but no independently verified exit reason.

Use three named terminals: **Browser Backend**, **Browser Frontend**, **Private Login Helper**. Keep credentials private and record the new ready path locally before starting a blocking backend command. Do not search for passwords, open/dump the handoff, change ACLs or use the original acceptance variable/database as fallback. Leave the original acceptance database intact.

First, after approval for the live read-only check, use the privately configured backend terminal at the repository root:

```powershell
@'
import json, sys
sys.path.insert(0, 'backend')
from tests.phase4b_browser_safety import designated_browser_url, SafetyError
from tests.phase4b_browser_recovery import inspect_browser_recovery_database
try:
    print(json.dumps(inspect_browser_recovery_database(designated_browser_url())))
except SafetyError as error:
    print(str(error))
    sys.exit(1)
'@ | .\.venv\Scripts\python.exe -B -
```

This is SELECT-only: no ownership lock, rotation, migration, seeding or reset. Stop on rejection. After separate approval for credential rotation and fixture startup, the exact proposed command is:

```powershell
$phase4bPrivate = Join-Path $env:TEMP ('phase4b-browser-' + [guid]::NewGuid().ToString())
$phase4bReady = Join-Path $phase4bPrivate 'ready.json'
.\.venv\Scripts\python.exe -B docs/testing/phase-4b/serve_browser_fixture.py --ready-file $phase4bReady --allow-browser-database-recovery --lifetime-seconds 14400
```

Do not create the new parent beforehand, reuse old storage, add the initialization flag, or retry automatically. Recovery acquires the same lifetime advisory ownership lock used by initialization, validates the complete profile and revalidates under table locks immediately before updating only the existing synthetic administrator credential/timestamp. Any session, extra faculty account, schema drift or wrong target blocks it. No migration/seed/session deletion occurs. Unexpected failure after rotation may need another reviewed rotation. Legacy fixture processes must already be stopped because they do not hold the new ownership lock.

The default remains 1800 seconds; explicit 14400 provides four hours with a finite expiry, warnings and stop reason. Normal authentication expiration remains unchanged. New private handoff/instance/storage replace no old artifacts; do not infer readiness from an old URL. Cleanup removes the new owned handoff/control markers; retained database/storage are not reset. An unresponsive owned worker terminates only its own CLI process before ownership is relinquished, retaining private artifacts for review.

After approval to reconfigure only the dedicated frontend, set its process-local `VITE_API_URL` from the NEW handoff's `.backend` field and restart only that owned Vite process on `localhost:5189 --strictPort`. The old Vite environment may target an expired ephemeral port. Verify the Vite-served API configuration, fixture marker/instance match and CORS before input. Do not stop unrelated services. Use a fresh isolated browser profile to exclude old cookies and remembered GA state.

User performs private credential entry through the actual React login page. Use an authorized local clipboard transfer excluding Windows history/roaming; clear afterward, never print passwords or disable ACLs. Prepare the six scenario steps and capture destination before starting the window. Record real screenshots only after actual results, label user-performed tests USER CONFIRMED, and label unavailable-marker evidence injected fixture 503. Follow existing capture/privacy/hash rules above. No scenarios or captures were executed during offline recovery preparation.
