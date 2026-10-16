# Phase 4A authentication and authorization: thesis evidence

Evidence date: 2026-10-16, Asia/Manila. Application source commit: `deba151d5963b083681ce88d60b95f858b61a149`.

**Assessment: the three outstanding acceptance scenarios remain PASS — USER CONFIRMED.** Four user-supplied screenshots are now archived and visually reviewed by Codex, with privacy redactions and explicit limits below. The user manually confirmed preference persistence, faculty denial on the administrator account page, and logout followed by protected-page redirection. These are USER-PERFORMED MANUAL TESTS, not Codex-executed browser tests. Earlier evidence remains seven Codex browser screenshots, 61 backend security cases, eight frontend authentication cases, eleven isolated API observations and one evidence-helper regression. These categories overlap and are not summed into a single security-case total. Both earlier Codex browser attempts remain blocked/not executed for the outstanding steps; no automated result or total has been increased.

## Existing implementation references

Keep these reports as the implementation and historical verification accounts:

- [Phase 4A authentication architecture, models, migration and permission matrix](../phase-4a-authentication-report.md).
- [Phase 4A final security verification and historical test ledger](../phase-4a-final-verification.md).
- [Local PostgreSQL identity setup and manual acceptance](../phase-4a-local-setup.md).
- [Phase 3F.2 data integrity safeguards](../phase-3f2-data-integrity-report.md).
- [Current implementation roadmap](../implementation-roadmap-status.md) and [system bug report](../system-bug-report.md).

This report adds provenance and current visual evidence; it does not duplicate those reports, retroactively change their results or claim a new development phase was implemented.

## Implemented features and supporting evidence

| Prototype claim | Current evidence | Limit |
|---|---|---|
| Verified administrator/faculty login and separate navigation | P4A-B02/B04; genuine credential/session backend tests; API A02/A03 | Temporary SQLite identities; not online PostgreSQL deployment acceptance. |
| Administrator dashboard is protected | Anonymous B01 redirect followed by authenticated B02 dashboard | No GA run was started. Faculty dashboard remains minimal placeholder content. |
| Faculty preferences use the server-confirmed account binding | B05; backend own-versus-other tests | Names/profiles are synthetic and academic metadata intentionally empty for privacy. Course eligibility filtering is not newly demonstrated. |
| Preferences save and survive browser refresh | Codex B06/B07 plus independent-client API A04; user-confirmed manual B08 retained Compact and Very High after refresh; archived before/after images show the selections | The images alone do not establish Save or refresh. Those steps remain user-confirmed, not independently reproduced by Codex. |
| Backend ownership and administrator-only access | Existing backend cases and API A05-A08, including valid-CSRF ownership denial; manual B09 and archived denial image | The image shows frontend denial at `/admin/accounts`; faculty identity and preceding actions are user-confirmed. Backend enforcement remains separately tested. |
| Logout invalidates access | Codex administrator B03 and API faculty logout 204 then 401; user-confirmed B10; archived sign-in image at the protected URL | `redirect.png` shows sign-in at `/faculty/preferences`, not `/login`. Logout and the later `/login` URL remain user-confirmed only. |
| Stable identities, account/session constraints and migrations exist | Current backend schema/FK/constraint tests and PostgreSQL offline SQL test; original architecture report | SQLite and offline SQL do not establish PostgreSQL online locking/restart behavior. |

## Environment, security and privacy

The usual local frontend/backend ports were unavailable (connection refused). Windows browser automation was available, so a separate Vite frontend on localhost:5189 and an ephemeral loopback FastAPI server were used. The evidence-only server reuses the existing real-auth fixture with temporary SQLite and preference/settings storage; no principal, password verification, ownership, Origin or CSRF dependency is bypassed.

The preceding paragraph describes the earlier Codex collection environment. The later user-performed manual tests used the disposable faculty test account `faculty_test01`; the administrator-route and protected-route requests were reported at `http://localhost:5173`. The user did not provide a browser/version, exact execution timestamps, a separately recorded Test 1 URL or a database configuration. Do not identify these manual tests as the localhost:5189 temporary SQLite run or infer online PostgreSQL verification from them.

In the earlier Codex fixture only, privacy-related metadata is substituted: names are synthetic, profiles have synthetic/empty academic data and the offered-subject list is empty. The existing UUID/code adapter remains internally stable. Its screenshots and exported results contain no institutional faculty names, IDs, preferences, tokens, cookies, passwords, private keys or database credentials. Browser chrome/favorites were cropped out of those seven captures. The later user images are separate: their visible test preferences are attributed to the disposable account; populated username/password fields and unrelated bookmarks were obscured where present. No plaintext password, token, cookie, database credential or private faculty record was observed. No screenshot was generated or modified to manufacture an application outcome.

Saved chromosomes, latest results, stopped runs, generation history and checkpoints are redirected to owned temporary paths in this fixture, and no GA is started. Existing application data, notebooks, GA source and the already-modified live preference file are protected by before/after hashes. The Git index and HEAD are also checked. See the run manifest for the final preservation outcome.

## Actual screenshot inventory

The seven earlier Codex images were visually inspected. Original window: 954 x 1025; application crop: 905 x 904. Individual timestamps, crop bounds and SHA-256 values are in [screenshots.json](../testing/phase-4a/2026-10-16-acceptance-01/screenshots.json). The four later user images have different dimensions and provenance, recorded separately below.

| Scenario and screenshot | Observed result |
|---|---|
| [P4A-B01-anonymous-sign-in.png](../screenshots/phase-4a/2026-10-16-acceptance-01/P4A-B01-anonymous-sign-in.png) | Anonymous administrator navigation ends at the empty sign-in page. |
| [P4A-B02-admin-dashboard.png](../screenshots/phase-4a/2026-10-16-acceptance-01/P4A-B02-admin-dashboard.png) | Genuine synthetic admin is admitted to the dashboard. |
| [P4A-B03-admin-logout.png](../screenshots/phase-4a/2026-10-16-acceptance-01/P4A-B03-admin-logout.png) | Administrator logout returns to an empty login form. |
| [P4A-B04-faculty-dashboard.png](../screenshots/phase-4a/2026-10-16-acceptance-01/P4A-B04-faculty-dashboard.png) | Genuine synthetic faculty session sees the faculty portal/navigation. |
| [P4A-B05-faculty-preferences-before.png](../screenshots/phase-4a/2026-10-16-acceptance-01/P4A-B05-faculty-preferences-before.png) | Own default preference loads, enabled, with No changes. |
| [P4A-B06-preference-unsaved.png](../screenshots/phase-4a/2026-10-16-acceptance-01/P4A-B06-preference-unsaved.png) | Disabling the test preference produces Unsaved changes. |
| [P4A-B07-preference-saved.png](../screenshots/phase-4a/2026-10-16-acceptance-01/P4A-B07-preference-saved.png) | Real backend save finishes with Saved and the preference disabled. |

### User-supplied manual acceptance archive

Reviewed 2026-10-16, Asia/Manila; the exact review timestamp, original/archived SHA-256 hashes, dimensions and redaction rectangles are in [manual-acceptance-manifest.json](../testing/phase-4a/2026-10-16-missing-browser-02/manual-acceptance-manifest.json). Capture times and browser version were not supplied and remain unknown. Codex reviewed the actual files, without interacting with the application or rerunning the tests.

| Actual screenshot | Scenario | What the image independently shows | What remains user-confirmed |
|---|---|---|---|
| [before-change.png](../screenshots/phase-4a/manual-acceptance/before-change.png) | P4A-B08 baseline | Schedule Style **No Preference**, **No changes**; Lecture/Laboratory **Same Day**, informational-only importance. | Account, capture sequence and URL; the crop has no address bar. |
| [after-change.png](../screenshots/phase-4a/manual-acceptance/after-change.png) | P4A-B08 selections | Schedule Style **Compact**, importance **Very High**; Lecture/Laboratory **No Preference**. | Save and refresh, and persistence afterward. The crop does not show those actions, URL or save status. The other preference change is visible but was not an additional acceptance test. |
| [fcult-admin-denied.png](../screenshots/phase-4a/manual-acceptance/fcult-admin-denied.png) | P4A-B09 | `localhost:5173/admin/accounts`, **Access unavailable**, and **You do not have permission to open this portal.** | Signed-in faculty role and navigation procedure. A screen does not establish backend HTTP authorization. |
| [redirect.png](../screenshots/phase-4a/manual-acceptance/redirect.png) | P4A-B10 | CCS Faculty Scheduling sign-in screen at `http://localhost:5173/faculty/preferences`; protected preference content is absent. | Prior logout and subsequent `/login` URL. **This image does not show or prove `/login`.** |

The denial image's bookmarks and the sign-in image's bookmarks and populated credential fields were replaced with opaque rectangles. The original password was masked; its field was still fully obscured. Pixel comparison verified no changes outside the recorded rectangles. Original image hashes are retained, but unredacted copies are not added to the archive. The two preference images are byte-identical to the supplied files. Existing `docs/screenshots/admin-dashboard.png`, `generate-schedule.png` and all seven earlier Codex captures remain unchanged and are not relabelled.

## Existing Codex test results and user-confirmed manual acceptance

[Detailed commands, results and collection incidents](../testing/phase-4a/2026-10-16-acceptance-01/results.md) distinguish this run from the historical Phase 4A reports.

- Backend authentication/security: **61 passed, one browser integration case deselected**, four warnings, 45.34 seconds.
- Frontend authentication/transport: **8 passed**, zero failed.
- Codex browser acceptance: **seven observed scenarios passed**; the outstanding refresh/admin-denial/faculty-logout steps remain **BLOCKED / NOT RUN by Codex**.
- User-performed manual acceptance: **three PASS — USER CONFIRMED** (B08 Compact/Very High persistence, B09 administrator-page denial and B10 logout/protected-page login redirect). These are separately attributed user reports and add zero to automated test counts.
- Independent API verification: **11 assertions passed**; the browser-saved value reloaded in a separate HTTP client; rejected writes preserved the temporary preference contents.
- Evidence-helper lifecycle regression: **1 passed**, one warning, 7.91 seconds, after the documented initial cleanup failure.
- Frontend build/lint, broader GA/preference suites and online PostgreSQL: **NOT RUN in this task**. No application frontend source or dependency was changed; historical results remain separately referenced.

During refresh, Computer Use stopped because it could not determine the browser URL confidently enough to enforce policy. No further browser input was sent. Successful API persistence and historical browser tests are not used to claim that this blocked UI step passed.

The subsequent manual confirmation changes the manual acceptance status only. No application test, browser action, API request or database verification was run while making this documentation-only update.

## Bugs and evidence-collection corrections

No new authentication or scheduling defect was confirmed. The README's obsolete claim that preference events could be resized was corrected to match Phase 2's fixed-duration behavior; README now points to the current authentication setup and mandatory documentation standard.

Collection-only EVIDENCE-001: initial temporary-server cleanup exited with a Windows SQLite file-lock error. The new helper had closed a yield fixture instead of resuming its post-yield engine disposal. Its teardown was corrected, a regression was added and the corrected test passed. The initial failure remains documented; no production identity, GA or preference service changed. Other resolved capture-tool issues and the final browser-policy stop are recorded in the testing results.

## Earlier isolated reproduction procedure

This is the earlier Codex fixture procedure, retained for reproducibility. The user completed the three criteria manually with a different disposable test account; their four supplied images are now archived separately. Independent Codex browser completion remains outstanding.

1. Follow [local setup](../phase-4a-local-setup.md) only against an explicitly chosen disposable identity database, or use [serve_evidence_fixture.py](../testing/phase-4a/serve_evidence_fixture.py) to reuse the temporary real-auth fixture. Never run acceptance writes against the institutional preference file.
2. For the evidence fixture, pass a new `--ready-file` under the OS temporary directory with a `phase4a-evidence-` filename. It starts only a temporary backend. Keep its random credential handoff private; do not print, commit, screenshot or paste it. The fixture uses `admin@test.invalid` and `faculty@test.invalid`; their passwords are generated per run, not documented defaults.
3. Start a separate Vite server on localhost:5189 with `VITE_API_URL` set in that process from the private handoff's backend URL. Use a separate browser profile/InPrivate window. Keep the regular local services and cookies untouched.
4. Visit `/admin` while logged out: expect `/login`. Sign in as the synthetic admin, inspect the dashboard without starting a GA, then Sign out.
5. Sign in as the synthetic faculty and open My Preferences. Expect its own binding and No changes. Disable Consider my subject preferences, save, and expect Saved. In a permitted browser session, refresh and confirm the flag remains disabled; this last step is still missing from the current captures.
6. With the faculty session, visit `/admin/accounts`: expect Access unavailable. Also verify another-faculty GET/PUT returns 403, using valid Origin/CSRF for the PUT. Do not publish request credentials. This UI step needs a future permitted browser run; current API denial evidence already exists.
7. Sign out as faculty, reload a protected route and expect login. Preserve screenshots only after passwords are cleared and private fields are absent.
8. Stop only the servers/profile started for the fixture. Create the handoff's same-stem `.stop` marker for cooperative backend cleanup. The helper removes its handoff, stop marker and owned storage. It also has a 30-minute safety deadline. Do not delete or reset project data for cleanup.

## Thesis relevance and limits

This evidence supports a prototype claim that role-aware web access can protect scheduling administration and faculty-owned preference entry through server-verified identities. The before/edit/save sequence, independent API read and valid-CSRF negative tests connect visible behavior to backend enforcement, rather than relying only on screenshots.

It does not establish scheduling optimality, better fitness, faculty satisfaction, usability-study outcomes, benchmark performance or production security. No new GA evaluation, population, chromosome or fitness analysis was created. Online PostgreSQL migration/locks/restart, HTTPS deployment, multiworker/distributed operation, MFA/SSO, account audit/recovery and institutional acceptance remain outside the evidence established here. The current single-worker limitation still applies.

## Historical Codex missing-browser-evidence follow-up: 2026-10-16

The focused continuation is documented in [the follow-up results and manual instructions](../testing/phase-4a/2026-10-16-missing-browser-02/results.md). No already verified scenario was repeated. Read-only supported Computer Use discovery identified the isolated Microsoft Edge application window, but its state request returned `window is minimized; call activate_window, refresh with get_window, then retry get_window_state`. No current URL or page content could be verified. Because URL verification was required before interaction, the window was not activated and no browser input, fixture startup or authentication action followed.

| Outstanding scenario | Status of that Codex attempt | Observation in that attempt | New screenshot in that attempt |
|---|---|---|---|
| P4A-B08: preference persistence after browser refresh | INCOMPLETE / BLOCKED | Not executed; URL verification unavailable before input. | None |
| P4A-B09: faculty denial on an administrator-only page | INCOMPLETE / BLOCKED | Not executed for the same safety precondition. | None |
| P4A-B10: faculty logout and subsequent protected-page authentication | INCOMPLETE / BLOCKED | Not executed for the same safety precondition. | None |

The historical fixture origin `http://localhost:5189` is an intended/manual-test URL, not an observed current URL in this attempt. The earlier seven screenshots, security results and independent API persistence check remain valid within their recorded scope; they do not complete these three missing browser scenarios. The follow-up provides focused manual steps, expected results and capture filenames without asking for real credentials or live preference changes. No new screenshot or passing browser result is claimed.

The living report's updated digest is recorded as a documentation revision in the original run manifest; its previous digest and historical capture/test results are retained. Follow-up review and data/Git preservation metadata are in [attempt-manifest.json](../testing/phase-4a/2026-10-16-missing-browser-02/attempt-manifest.json).

## Final user-performed manual acceptance confirmation

Provenance: the user's explicit confirmation in this conversation, documented 2026-10-16 (Asia/Manila). The exact test execution times were not supplied. Test account: disposable `faculty_test01`. Codex did not execute or independently observe the browser procedures. Codex subsequently inspected the four supplied image files, whose narrower visual evidence is described above. Detailed procedures and expected/actual results are appended to the [existing manual follow-up results](../testing/phase-4a/2026-10-16-missing-browser-02/results.md).

| Manual scenario | Expected result | User-confirmed actual result | Current manual status |
|---|---|---|---|
| P4A-B08: preference persistence | Schedule Style Compact and Schedule Style Importance Very High remain saved after Save and browser refresh. | Both selections remained saved after refresh. | **PASS — USER CONFIRMED** |
| P4A-B09: administrator account-page denial | A faculty account cannot access `http://localhost:5173/admin/accounts`. | Application displayed **Access unavailable** and **You do not have permission to open this portal.** | **PASS — USER CONFIRMED** |
| P4A-B10: logout and protected-page access | After Sign out, `http://localhost:5173/faculty/preferences` requires authentication. | Login page displayed; the browser subsequently showed `/login`. | **PASS — USER CONFIRMED** |

Manual B09 demonstrates the frontend restriction. Existing automated backend tests separately verify API authorization; the manual screen does not replace them. The confirmation does not establish the database engine, restart durability, production deployment security, scheduling quality or new GA behavior. All existing automated totals and blocked Codex attempt records remain unchanged. Screenshot archival is complete for the four supplied files. A screenshot of the final `/login` URL is not present; that URL remains user-confirmed only. Exact capture times, browser version and independent Codex repetition remain unavailable.
