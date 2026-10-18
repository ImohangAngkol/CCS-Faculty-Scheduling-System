# Phase 4B.1 browser acceptance

## Current written-only acceptance summary (documentation update 2026-10-18)

**P4B-B01 through P4B-B06: PASS — USER CONFIRMED.** The user manually completed all six scenarios. **Screenshot evidence: NOT CAPTURED for every scenario; automated browser execution: NOT ESTABLISHED; original test timestamps: NOT RECORDED.** No original screenshots exist to recover. See the [final written acceptance matrix](manual-acceptance-results.md) and [attribution/hash manifest](manual-acceptance-manifest.json).

B06 used the isolated fixture's `ready.unavailable` marker to inject HTTP 503. The user confirms the expected error, successful marker removal and recovery of the same faculty session with Compact / Very High preserved. This was not a physical PostgreSQL outage. No browser actions, database operations or regression reruns were performed to prepare this written report.

The sections below are preserved **historical snapshots before the final user confirmation**, including obsolete startup guidance, NOT RUN states and blocked attempts. They are not current execution instructions. Do not rerun initialization or pristine recovery against the populated browser database to complete this written-only package. Existing automated counts remain separately attributed.

## Historical Stage A status and instructions

Status as of 2026-10-18: **STAGE A PREPARED / OFFLINE VERIFIED; STAGE B NOT RUN**. The user-executed PostgreSQL suite passed all 14 cases; Stage A added a separate browser gate, synthetic app and isolation tests. Browser target provisioning/online startup and execution approval remain outstanding. No Phase 4B screenshot was produced. Earlier missing-variable blocks remain historical, separate from Phase 4A evidence.

Use the [updated execution plan](browser-acceptance-plan.md) and [Stage A results](stage-a-fixture-preparation.md). The current helper accepts ONLY the browser variable/target, requires `--allow-browser-database-initialization` after Stage B approval and creates `ready.json` inside a NEW private OS-temp directory. Do not use the obsolete commands below or select/reset the successful acceptance database.

Before browser input, use supported Computer Use tooling to verify the actual application identity and local URL. Stop if uncertain. Do not reuse a live backend/account as an isolated fixture. First complete the [PostgreSQL safety gate](../../phase-4b-postgresql-verification.md), then explicitly configure a separately owned backend/frontend with synthetic identities and temporary preference/GA storage. The one-shot PostgreSQL test database must be reviewed before reuse; the automated suite refuses a nonempty schema rather than silently reseeding it.

## Existing owned fixture instructions (historical; current reuse blocked)

The following paragraphs describe the pre-Stage A helper only. They are retained as historical instructions, not the current startup procedure. Use the updated plan; the current helper no longer reads the old test variable or reuses its fixture.

Only after privately configuring PHASE4B_TEST_DATABASE_URL, start [serve_browser_fixture.py](serve_browser_fixture.py). It uses the same read-only empty-database gate, migration and synthetic bootstrap as the automated acceptance fixture. It redirects all writable preference/settings/checkpoint/history/saved-result paths to owned temporary storage and refuses GA generation. Authentication and role/ownership checks remain real.

```powershell
$phase4bReady = Join-Path $env:TEMP ('phase4b-browser-' + [guid]::NewGuid().ToString() + '.json')
.\.venv\Scripts\python.exe docs/testing/phase-4b/serve_browser_fixture.py --ready-file $phase4bReady
```

Keep the chosen ready path privately. Its handoff contains the generated synthetic administrator username/password and loopback backend URL: never print, commit, screenshot or paste the file. In a separate terminal, read only its `backend` field into process-local VITE_API_URL and start Vite from frontend on `localhost:5189` with `--strictPort`. Use a separate browser profile. Sign in using the privately held synthetic administrator credentials, then create/bind a synthetic faculty account through Account Administration; choose a private test password locally and do not record it in evidence. The normal account page lists the two synthetic identities.

The database suite and browser helper are alternative one-shot entry points for an empty schema. They must not be run concurrently or sequentially against retained data without owner review. The helper does not erase the database after testing. A subsequent combined/reuse run needs a separately reviewed procedure for the known synthetic records; no prefix-based automatic approval or reset is implemented.

For the unavailable-state scenario, create the ready file's same-stem `.unavailable` marker in OS temporary storage. Only the owned fixture then returns a clearly labelled injected 503; it does not stop PostgreSQL or affect another backend. Remove that owned marker to recover. The screenshot must say this is an injected fixture outage, not a demonstrated production outage.

To stop, create the handoff's same-stem `.stop` marker. The helper also has a 30-minute deadline. It stops its own server, disposes its engine and removes its temporary handoff/files; synthetic PostgreSQL records remain. If shutdown fails, preserve temporary files and report it rather than deleting an unknown directory. The executed missing-URL regression verifies that this helper does not start or write a handoff without the designated environment; real PostgreSQL startup and browser behavior remain unverified.

## Acceptance scenarios

| Scenario | Expected result | Actual result in this phase |
|---|---|---|
| P4B-B01: administrator account creation and binding | Synthetic faculty account created and bound to the intended UUID; duplicate binding explained | NOT RUN; separate fixture/approval pending |
| P4B-B02: faculty preference save and refresh | Compact / Very High remains saved after full refresh for that synthetic faculty | NOT RUN; separate fixture/approval pending |
| P4B-B03: administrator preference review | Administrator sees the same saved synthetic preference; another record is unchanged | NOT RUN; separate fixture/approval pending |
| P4B-B04: faculty administrator-route denial | `/admin/accounts` shows Access unavailable with no account list | NOT RUN; separate fixture/approval pending |
| P4B-B05: logout and protected navigation | Protected content disappears and authentication is required; record the actual URL rather than assuming `/login` | NOT RUN; separate fixture/approval pending |
| P4B-B06: safe database-unavailable presentation | Owned isolated backend with injected connection failure shows an actionable error, without changing/stopping the institutional database service | NOT RUN; separate fixture/approval pending |

For each future executed scenario record requested/observed URL, browser version, timestamp with offset, synthetic environment, steps, expected/actual result and genuine screenshot filename/hash. Inspect screenshots for credentials, cookies, tokens, private accounts and unrelated browser chrome. Clear credential fields or apply documented opaque redaction; never generate/reconstruct a success image. The user may perform these steps manually, but attribute that evidence as USER CONFIRMED rather than Codex-executed.

Do not start a GA to obtain these screenshots. A safe isolated fixture must redirect every writable destination in every process. Authentication/ownership/CSRF must remain real. Creating or changing accounts through Windows UI must follow the installed Computer Use action-confirmation policy; manual user operation is an available alternative.

## Resumption attempt: 2026-10-16 23:49 +08:00

All six scenarios above remain **BLOCKED / NOT RUN**. The private URL was still absent from the actual command execution environment, despite the user's configuration notice. No database connection, fixture startup, UI input, screenshot capture or dedicated-port service was attempted. Actual browser version and browser-observed URLs are unavailable because no browser test ran; this does not establish that browser automation itself is unavailable. See the [resumption record](2026-10-16-resume-01/acceptance-status.json).
