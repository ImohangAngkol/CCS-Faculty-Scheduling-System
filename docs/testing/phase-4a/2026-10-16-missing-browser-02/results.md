# Phase 4A missing-browser-evidence follow-up

Recorded: 2026-10-16T12:51:50.430156+08:00 (Asia/Manila). Application source remains `deba151d5963b083681ce88d60b95f858b61a149`.

**Latest manual acceptance: all three scenarios are PASS — USER CONFIRMED.** See the appended user-performed manual results below. The minimized-window preflight and incomplete statuses in the original Codex attempt remain historical facts; this update does not convert them into successful Codex browser tests.

## Scope and safety preflight

Only the three outstanding acceptance scenarios were requested. Previously verified administrator login/dashboard/logout, faculty login, preference edit/save and API security checks were not repeated.

The installed Computer Use skill and its guidance, confirmations and supported API reference were reviewed. The supported `@oai/sky` tooling was initialized through `node_repl`. Read-only application discovery identified a unique Microsoft Edge window titled `frontend - [InPrivate] - Microsoft Edge` (the actual title also contains a zero-width separator). That title establishes a candidate application window, not its URL or authenticated state.

Before any activation, navigation, refresh, typing or clicking, `sky.get_window_state` was requested with accessibility text enabled and screenshots disabled to independently read the address/document URL and application identity. It returned:

```text
window is minimized; call activate_window, refresh with get_window, then retry get_window_state
```

No URL or page content was returned. The user's instruction requires confident URL verification before browser interaction, so the suggested activation was not performed. No further browser calls or input were issued. No alternative protocol, helper, browser process, fixture server or API workaround was used to bypass this precondition.

The previous fixture URL was `http://localhost:5189`, but it is historical/intended context, **not an observed current browser URL**. No new application/browser identity or authenticated session is claimed verified. No fixture was started and no account or preference record was changed in this attempt.

## Historical Codex attempt results

| Scenario | Expected result | Actual observation in this attempt | Status | New screenshot |
|---|---|---|---|---|
| P4A-B08: preference persistence after refresh | The saved test preference remains unchanged after a full browser reload; the correct faculty's preferences reopen without unsaved changes. | Scenario not executed: current browser URL could not be verified during the minimized-window preflight. | INCOMPLETE / BLOCKED | None |
| P4A-B09: faculty navigation to administrator pages | A faculty session opening an admin-only route sees Access unavailable and no administrator content. | Scenario not executed for the same URL-verification precondition. | INCOMPLETE / BLOCKED | None |
| P4A-B10: faculty logout and protected-page authentication | Sign out completes; navigating/reloading a protected route afterward requires sign-in. | Scenario not executed for the same URL-verification precondition. | INCOMPLETE / BLOCKED | None |

**Completed by Codex in that attempt: zero. Screenshots captured in that attempt: zero.** No test passed or application failed merely because the evidence tooling could not inspect the minimized window. Existing seven screenshots and previous automated/API results remain historical evidence with their original scope. No backend/frontend regression suite was rerun for that follow-up or for this manual-result documentation update.

## Earlier isolated-fixture reproduction instructions

The user has since reported completion with disposable account `faculty_test01` on the normal localhost:5173 frontend. The localhost:5189 instructions below describe the earlier isolated fixture and are retained as a reproducible alternative; they are not the execution record for the user's later manual tests.

Use a fresh disposable fixture or a separately confirmed disposable development database. Do not use a live faculty account or institutional preferences. The previous evidence servers were stopped after collection and the previous password/session must not be reused.

### Safe prerequisites

1. Restore/open the intended browser window yourself. Independently check that it is Microsoft Edge showing **CCS Faculty Scheduling**, and verify the full local URL before entering test credentials or changing a record. Stop if the host, port or application is unexpected. Do not disable browser safety, cookie security or Origin/CSRF checks.
2. Start the existing [isolated evidence fixture](../serve_evidence_fixture.py) from the repository root, using a new handoff filename in the OS temporary directory:

   ```powershell
   $phase4aReady = Join-Path $env:TEMP ('phase4a-evidence-manual-' + [guid]::NewGuid().ToString() + '.json')
   .\.venv\Scripts\python.exe docs\testing\phase-4a\serve_evidence_fixture.py --ready-file $phase4aReady
   ```

   Keep the chosen path locally. The helper uses only temporary SQLite/JSON storage, synthetic names and empty academic metadata. It does not run a GA or migrate PostgreSQL. It has a 30-minute safety deadline. Its random per-run credential handoff is private: do not print it in shared terminals, add it to evidence, copy it into chat or capture it in a screenshot.
3. In another terminal, use the same locally chosen handoff path to set `VITE_API_URL` from its `backend` field in process memory; start Vite from `frontend/` on `localhost:5189` with `--strictPort`. Do not alter an existing server or resolve a port conflict by stopping an unknown process. Follow the existing [local setup](../../../phase-4a-local-setup.md) for environment conventions.
4. Use a separate browser profile/InPrivate window. Open `http://localhost:5189/login`, confirm the application and URL, then sign in only as the fixture's `faculty@test.invalid` using the new private test password. This login is a prerequisite, not a request to repeat the completed administrator scenarios. Do not save the password in the browser.

### P4A-B08: refresh persistence

1. Confirm the URL is `http://localhost:5189/faculty/preferences`, the Faculty Preferences heading is present and the synthetic faculty identity is correct.
2. In the disposable record only, disable Consider my subject preferences and save. Confirm Saved before refreshing. If that value is already saved, do not repeat the edit unnecessarily.
3. Refresh using the browser's Reload control. Wait for the authenticated preference page and its backend data to finish loading.
4. Confirm the flag is still disabled, the faculty identity is unchanged, the status is No changes and there is no fabricated/default replacement record or unexpected login redirect.
5. Capture the actual post-refresh application state as `P4A-B08-preference-after-refresh.png`. Record the requested and observed URL, Edge version, ISO timestamp with `+08:00`, expected/actual result and screenshot hash. If any expected condition is absent, record FAIL or INCOMPLETE instead of PASS.

### P4A-B09: administrator-route denial

1. While still signed in as the synthetic faculty, navigate to `http://localhost:5189/admin/accounts`.
2. Confirm Access unavailable, the permission explanation and a way back to the faculty dashboard. No account list, role editor or administrator form should be displayed. The SPA page itself need not return HTTP 403; backend API denial is separate evidence.
3. Capture `P4A-B09-faculty-admin-denied.png` with the same timestamp, application/URL and expected/actual metadata. Do not substitute the earlier API 403 result for this UI observation.

### P4A-B10: logout and subsequent protected access

1. Return to the faculty dashboard/preferences through the provided navigation and confirm the expected local URL. Click Sign out and wait for the empty sign-in form.
2. Navigate to `http://localhost:5189/faculty/preferences` while logged out, or reload that protected URL. Confirm the browser returns to `/login` and no preferences or faculty-private content are accessible.
3. Capture `P4A-B10-logout-protected-redirect.png`. Record both the requested protected URL and the observed login URL, timestamp and actual result. A sign-in screenshot without the preceding protected-route check does not alone prove logout enforcement.

### Evidence and cleanup

Place successful new images in a new run subdirectory under `docs/screenshots/phase-4a/`, and observations/manifests under `docs/testing/phase-4a/`. Link them from the [Phase 4A evidence report](../../../thesis-evidence/phase-4a-evidence.md). Capture only cleared password forms or authenticated nonprivate application content; exclude browser profiles/favorites, private names, tokens, cookies, developer-tool network panels and unrelated windows. Do not fabricate an image for a missing result.

Stop only the temporary servers/profile you started. For the helper, create a `.stop` marker with the same stem as its private handoff file; cooperative shutdown disposes the database and removes owned handoff/storage. Do not delete or restore project preferences, settings, saved schedules, checkpoints or history for cleanup.

## Final review scope

Existing Phase 4A screenshots, manifests, reports and evidence-helper files were reviewed for sensitive information, screenshot references and relative documentation links. Automated scans report file/finding types only, never matched secret values. The current evidence report is a living document; its manifest digest is refreshed with an explicit revision record preserving the previous digest. Historical capture times, screenshots, results and original test counts are not rewritten or relabelled as a new successful run.

Protected GA/data source and stored-run hashes, HEAD and index are compared with the pre-edit baseline. No staging, commit or push is authorized or performed. See [attempt-manifest.json](attempt-manifest.json) for final verification metadata.

## User-performed manual acceptance: final confirmation

Confirmation source: the user's explicit report in this conversation, documented 2026-10-16 (Asia/Manila). Execution timestamps and browser/version were not supplied and are not inferred from the documentation timestamp. The account `faculty_test01` is described by the user as a disposable faculty test account. No password, cookie, token or private account details are recorded. Codex did not perform new browser actions or connect to a database while documenting this confirmation.

### P4A-B08 — Faculty preference persistence

- **Performed by:** User, with disposable faculty account `faculty_test01`.
- **Procedure:** Open Faculty Preferences; select Schedule Style **Compact**; set Schedule Style Importance **Very High**; save; refresh the browser; inspect the saved selections.
- **Expected:** Schedule Style remains Compact and importance remains Very High.
- **Actual, user-confirmed:** Both selections remained saved after refresh.
- **Status:** **PASS — USER CONFIRMED**.
- **URL:** The preference page was reported; a separate full URL for this test was not supplied and neither preference crop shows an address bar. Do not substitute the old localhost:5189 fixture URL.
- **Screenshots:** [before-change.png](../../../screenshots/phase-4a/manual-acceptance/before-change.png) shows No Preference/No changes; [after-change.png](../../../screenshots/phase-4a/manual-acceptance/after-change.png) shows Compact/Very High. Codex inspected the files. The images do not independently show Save or refresh; those remain user-confirmed. The visible Lecture/Laboratory selection also differs and is not claimed as an extra acceptance test.

### P4A-B09 — Faculty administrator access restriction

- **Performed by:** User, signed in with the disposable faculty test account.
- **Procedure:** Navigate to `http://localhost:5173/admin/accounts`.
- **Expected:** Faculty cannot access administrator account management.
- **Actual, user-observed:** The application displayed **Access unavailable** and **You do not have permission to open this portal.**
- **Status:** **PASS — USER CONFIRMED**.
- **Evidence scope:** Frontend authorization only. Existing automated backend tests independently verify API authorization. No HTTP status, server-side response or PostgreSQL verification is inferred from this screen.
- **Screenshot:** [fcult-admin-denied.png](../../../screenshots/phase-4a/manual-acceptance/fcult-admin-denied.png) visibly shows `localhost:5173/admin/accounts` and the reported denial. Faculty identity and prior navigation are user-confirmed; unrelated bookmarks were obscured.

### P4A-B10 — Faculty logout and protected-page access

- **Performed by:** User, with the same disposable faculty test account.
- **Procedure:** Sign out; navigate to `http://localhost:5173/faculty/preferences`.
- **Expected:** Protected faculty content is inaccessible and the application redirects to the login screen.
- **Actual, user-observed:** The login page was displayed and the browser subsequently showed `/login`.
- **Status:** **PASS — USER CONFIRMED**.
- **Screenshot:** [redirect.png](../../../screenshots/phase-4a/manual-acceptance/redirect.png) shows the CCS Faculty Scheduling sign-in form at `http://localhost:5173/faculty/preferences`, with no protected content. It **does not show `/login`**, prior logout or the redirect sequence. The later `/login` path remains user-confirmed only. Populated username/password fields and bookmarks were obscured; the image is not evidence of an empty form.

### Attribution, screenshot availability and remaining limits

Manual results now contain **three PASS — USER CONFIRMED** entries. This does not add three to Codex's seven earlier observed browser scenarios or to any automated test total. The earlier 61 backend cases, eight frontend authentication cases, eleven API observations and one evidence-helper regression remain unchanged; no regression suite was rerun for this documentation update. Codex's minimized-window attempt still completed zero scenarios and captured zero screenshots.

At the earlier manual-confirmation documentation update, the user-supplied files were unavailable and were recorded as not yet archived. On 2026-10-16 the four actual files were found under `docs/screenshots/phase-4a/manual-acceptance/` and inspected. They are now **USER-PROVIDED EVIDENCE — ARCHIVED AND VISUALLY REVIEWED**, with the limits above. See [manual-acceptance-manifest.json](manual-acceptance-manifest.json) for exact review time, filenames, dimensions, original/archived SHA-256 hashes and deterministic redaction rectangles. Capture times and browser version remain unknown. Existing dashboard/schedule images and the seven historical Codex captures were not relabelled or changed.

Only the denial and sign-in images needed opaque privacy rectangles: bookmarks in both, plus the populated username and masked-password fields in the sign-in image. Pixel comparison verified that all remaining pixels were unchanged. The preference images remain byte-identical. No actual password, token, cookie, private faculty record or database credential was observed; unredacted copies are not added to the archive. This is file inspection, not a newly executed browser test, API check or database verification.

The manual report does not identify the database engine or prove online PostgreSQL migrations/locks/restart recovery. Production security, deployment qualification and independent Codex browser completion remain separate limitations. The three functional acceptance criteria remain **PASS — USER CONFIRMED**. The four supplied images are archived; there is no screenshot of the final `/login` URL or direct visual proof of the Save/refresh sequence. The blocked automation records remain unchanged.
