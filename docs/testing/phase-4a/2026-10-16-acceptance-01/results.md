# Phase 4A evidence collection results

Date: 2026-10-16, Asia/Manila. Application source: `deba151d5963b083681ce88d60b95f858b61a149`. Documentation, evidence and an evidence-only fixture are pending changes. The pre-existing live preference change is outside this task.

## Environment and isolation

Windows; Python 3.14.2; FastAPI 0.141.1; SQLAlchemy 2.0.52; pytest 9.1.1; Node v24.11.1. The installed Microsoft Edge executable reports 155.0.4283.45. Screenshots were captured through the Computer Use `@oai/sky` API in a separate InPrivate window, 954 x 1025 pixels, cropped to the 905 x 904 application area. Browser chrome/favorites are excluded. Cropping and PNG conversion used Pillow; application pixels were not fabricated, relabelled or edited.

Read-only probes of `http://localhost:5173/`, `http://localhost:8000/api/health` and `/api/auth/me` returned connection refused (Windows errno 10061), including an unrestricted local-network retry. No existing service was restarted or configured. A separate Vite server on localhost:5189 pointed at a temporary Uvicorn backend on an ephemeral loopback port.

The [evidence server](../serve_evidence_fixture.py) reuses `backend/tests/test_phase4a_auth.py::identity_app`, with genuine password hashing, sessions, role/ownership, Origin and CSRF checks. Only database/file destinations and privacy-specific metadata are substituted. Faculty names are synthetic; the existing UUID/code compatibility map is retained internally. Academic profiles and offered-subject metadata are intentionally empty/synthetic so screenshots contain no private faculty records. These substitutions do not demonstrate course eligibility or GA scheduling correctness.

Preferences/settings, checkpoint/history/stopped-run paths, saved/uploaded chromosome paths and latest-result paths all point to disposable temporary storage. No production database was connected or migrated, no GA was started, and no stored institutional preference was changed.

## Commands executed and observed results

Commands below ran from repository root except the npm command, which ran in `frontend/`. Exit codes and counts come from the executed tools, not copied historical totals. Exact start/end wall-clock timestamps were not captured for the first two command invocations; their observed durations and execution date are retained rather than invented. API checks and screenshots have timestamps in their manifests.

```powershell
.venv/Scripts/python.exe -m pytest backend/tests/test_phase4a_final_verification.py backend/tests/test_phase4a_auth.py -q --disable-warnings -k 'not real_browser' --tb=short --maxfail=1 --basetemp=$env:TEMP/phase4a-documentation-tests-20261016-64d1a2f8
# Exit 0: 61 passed, 1 deselected, 4 warnings in 45.34s.

# frontend/ working directory:
npm.cmd run test:auth
# Exit 0: 8 passed, 0 failed; Node reported duration_ms 4409.4178.

# repository root, after the evidence-helper cleanup correction:
.venv/Scripts/python.exe -m pytest docs/testing/phase-4a/test_evidence_fixture_lifecycle.py -q --disable-warnings --tb=short --maxfail=1 --basetemp=$env:TEMP/phase4a-evidence-lifecycle-20261016-5ea1d9cf
# Exit 0: 1 passed, 1 warning in 7.91s.
```

The 61 cases are authentication/security regressions; the additional Python case tests evidence infrastructure, not another authentication feature. The existing browser integration pytest case was deliberately deselected because this collection used a separate real-browser acceptance session. It was not claimed to pass again. Frontend build/full lint, preference/GA contract suites and the full optimization regression suite were NOT RUN in this documentation-only task; their previous results remain in the linked Phase 4A reports. Dependency deprecation warnings remain.

## Browser observations

| Scenario | Actual result | Status |
|---|---|---|
| P4A-B01 | Anonymous navigation to `/admin` redirected to `/login`; empty sign-in form. | PASS |
| P4A-B02 | Genuine synthetic administrator credentials opened Admin Dashboard and admin navigation; no GA started. | PASS |
| P4A-B03 | Administrator clicked Sign out and returned to an empty login form. | PASS |
| P4A-B04 | Genuine synthetic faculty credentials opened the faculty portal and faculty navigation. The dashboard content is a minimal placeholder, not a newly implemented academic dashboard. | PASS |
| P4A-B05 | Own preferences loaded with the default subject-preference flag enabled and no pending changes. | PASS |
| P4A-B06 | Disabling that flag produced Unsaved changes and enabled Save Preferences. Only a disposable test record was edited. | PASS |
| P4A-B07 | Save completed through the actual backend and displayed Saved; the flag remained disabled. | PASS |
| P4A-B08 | Browser refresh was attempted, but Computer Use stopped before completion could be verified. | BLOCKED |
| P4A-B09 | Faculty navigation to an administrator URL was not performed after the browser-policy stop. Backend role/ownership denial was verified separately. | NOT RUN |
| P4A-B10 | Faculty browser Sign out was not performed after the stop. API logout and post-logout rejection passed separately. | NOT RUN |

The exact stopping reason was: `Computer Use has been stopped for this turn because it could not determine the current browser URL on Windows with enough confidence to enforce policy.` No further browser input was issued. The InPrivate window was left untouched after that stop. No refreshed-state or access-denial screenshot was fabricated.

Earlier collection-only issues were resolved without changing the app: input geometry required a fresh screenshot; a missing supported Sharp import was replaced by Pillow for privacy cropping; a partial Windows `document_text` required checking the fresh accessibility tree together with the actual image. These are tooling observations, not product failures.

## API observations

[api-results.json](api-results.json) contains eleven timestamped status-code assertions against only the disposable server. All passed:

- Anonymous session GET: 401.
- Administrator and faculty login: 200 with genuine test credentials.
- A new HTTP faculty client read the preference saved by the browser: 200 and `use_subject_preference` false. This proves server-side persistence across independent requests; it does not substitute for the blocked browser-refresh check.
- Other-faculty GET: 403.
- Other-faculty PUT with valid Origin and session CSRF: 403 from ownership enforcement.
- Faculty account-list GET and own-priority PUT: 403.
- Preference contents were unchanged by the rejected operations.
- Faculty logout: 204, then session GET: 401. Administrator API logout: 204.

Credentials, cookies, tokens and response bodies were not written to the API artifact. These are additional observations of overlapping requirements, not counts to add to the backend suite as independent security coverage.

## Collection incident EVIDENCE-001 and correction

The first disposable evidence server shut down, but its cleanup exited 1 with Windows `PermissionError [WinError 32]` for its temporary `identity.sqlite`. Cause: calling `close()` on a pytest yield-fixture generator raised GeneratorExit and skipped the existing fixture's post-yield `engine.dispose()` statement. This did not invalidate the completed UI/API assertions and did not affect the institutional database.

The evidence-only helper now resumes the fixture normally to run disposal before temporary-directory cleanup. [test_evidence_fixture_lifecycle.py](../test_evidence_fixture_lifecycle.py) verifies readiness, genuine faculty login, synthetic identity, owned preference access, cooperative shutdown, absence of credential output and removal of owned storage/handoff files. The corrected fresh-process test passed. The initial failure is retained here; no backend application or existing test was edited to conceal it. The orphaned owned temporary directory was subsequently removed after the first process exited.

## Artifacts and remaining evidence

- [screenshots.json](screenshots.json): seven actual screenshots with scenario IDs, capture times, original/cropped dimensions and SHA-256 hashes.
- [api-results.json](api-results.json): eleven real isolated API observations.
- [run-manifest.json](run-manifest.json): source/environment, commands, current outcomes, artifact hashes and preservation checks.
- [Phase 4A thesis evidence](../../../thesis-evidence/phase-4a-evidence.md): readable requirement mapping, screenshot links and acceptance instructions.

Remaining: browser refresh completion, faculty-to-admin UI denial and faculty browser logout screenshots; online PostgreSQL migration/locking/restart verification; production deployment qualification; fresh calendar/eligibility/GA screenshots; and controlled thesis usability/performance/quality evaluation. Historical screenshots elsewhere are preserved and not relabelled as current.
