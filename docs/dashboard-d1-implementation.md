# Dashboard-first milestone D1: subject catalog and faculty pages

Implemented and verified **2026-10-21, Asia/Manila**. Source baseline: `3167cda2bd2d86011b50ea582026a4c39accb529`, branch `main`, with pre-existing uncommitted Phase 4C.2 work and protected preference changes preserved. Status: **D1 IMPLEMENTED; FRONTEND CONTRACTS, BUILD, FOCUSED LINT AND SYNTHETIC BROWSER ACCEPTANCE PASS**. Live FastAPI/PostgreSQL deployment acceptance was not performed.

## Objectives and acceptance boundaries

The dashboard-first review supplied in the conversation prioritizes usable pages before further database infrastructure. D1 completes the existing subject catalog, faculty home and profile routes only. Requirement IDs used here: D1-SUB (read-only searchable catalog), D1-HOME (authenticated identity and truthful navigation), D1-PROFILE (own read-only metadata), D1-NAV (routes/responsive design), D1-SAFE (preservation).

The user selected the repository's current **teal/gold** theme after clarification; no global palette was replaced. No GEC intake, change requests, Chair authority, My Schedule implementation, new database tables or GA changes are included. The [confirmed scheduling workflow design](phase-4c-confirmed-scheduling-workflows.md) and [seven-table foundation](phase-4c2-academic-foundation.md) remain separate work. See the [documentation standard](DEVELOPMENT_DOCUMENTATION_STANDARD.md) and [existing metadata contract](api/phase-1-metadata.md).

## Files created or modified

### Application files

| Path | Change |
|---|---|
| `frontend/src/pages/admin/SubjectManagement.tsx` | Implements the previously empty page: search, catalog cards, expandable components, durations/day alternatives, unsupported patterns and loading/error/empty states. |
| `frontend/src/pages/faculty/Dashboard.tsx` | Implements welcome, linked identity, quick links and explicit unfinished-workflow status. |
| `frontend/src/pages/faculty/Profile.tsx` | Implements account, faculty identity and academic sections; own metadata loading, retry, missing binding/record and identity mismatch handling. |
| `frontend/src/routes/AppRoutes.tsx` | Wires the three real pages; preserves current role guards and the My Schedule placeholder. |
| `frontend/src/api/faculty.ts` | Adds a cancellable detail GET through existing cookie/session transport; faculty-list behavior remains intact. |
| `frontend/src/api/subjects.ts` | Adds optional cancellation to the existing catalog GET; explicit TS transport import supports Node tests. |
| `frontend/src/services/dashboardMetadata.ts` | Validates consumed metadata, rejects inconsistent identities, provides search/pattern labels and bounded actionable error messages. |
| `frontend/src/components/dashboard/MetadataState.tsx` | Shared loading/empty/error state presentation. |
| `frontend/src/layouts/FacultyLayout.tsx` | Correct route titles and responsive stacking/padding. |
| `frontend/src/layouts/AdminLayout.tsx` | Responsive stacking/padding; administrative and GA actions unchanged. |
| `frontend/src/components/common/Sidebar.tsx` | Full-width two-column navigation on small screens, existing desktop sidebar retained. |
| `frontend/src/components/common/Topbar.tsx` | Wraps account/title content on narrow screens. |
| `frontend/package.json` | Adds `test:dashboard` and `test:dashboard:browser`; no dependency or lockfile changes. |

### Tests and evidence tooling

- `frontend/tests/dashboardD1.fixtures.mjs`: explicitly synthetic identities, subjects and metadata; no institutional records or credentials.
- `frontend/tests/dashboardD1.test.mjs`: eight focused contract cases.
- `frontend/tests/dashboardD1.browser.test.mjs`: sixteen actual Edge scenarios with a synthetic HTTP API, temporary browser profile, ephemeral ports and optional genuine screenshots.
- `frontend/tests/gaMonitoring.browser.test.mjs`: updates obsolete placeholder assertions, isolates the debugger port, blocks unhandled real-backend requests, fixes Boolean serialization in the new assertion and bounds screenshot capture at 30 seconds.
- `docs/testing/dashboard-d1/run_checks.py`: records frontend commands in new run directories with a whitelisted OS environment; never imports application Python or reads credential files.
- This report, [evidence manifest](testing/dashboard-d1/manifest.json), [preservation baseline](testing/dashboard-d1/preservation-baseline.json), command JSON artifacts and four reviewed screenshots. The manifest enumerates every D1 artifact and SHA-256.

No backend application source, existing database model/migration, existing evidence or institutional data was edited.

## Implementation details and contracts

Subject Management calls existing `GET /api/subjects/available`. It includes unassigned/preassigned subjects without applying preference eligibility filtering. Search matches code/title, ignoring case and surrounding whitespace. Components, weekly hours, meeting counts, exact durations and day alternatives come from the server. Unsupported patterns remain labelled unavailable rather than inferred. The current dataset is explicitly identified as the first-semester prototype, without inventing an academic year. There is no CRUD form or mutation request.

The faculty home uses `AuthContext`'s current account and linked faculty identity. Preferences and Profile are linked; My Schedule remains linked with an explicit unavailable status. It creates no workload/schedule statistics and does not mount an administrator GA provider.

Profile separates verified session account fields from linked identity and fetched academic metadata. Only `GET /api/faculty/{authenticated-faculty-UUID}` is requested. UUID, legacy numeric code and normal-faculty type are checked before displaying the returned academic data. Code/level zero remain valid. A 404 means missing metadata, not a replacement identity; a mismatched response is rejected. Specializations, explicit eligible subject codes and source seniority are read-only. Formal qualifications, appointments and current-term workload are not fabricated. There are no editable fields or save actions.

Both metadata requests use existing authenticated transport and its 401 handling. Abort signals and request keys prevent navigation/retry responses from displaying stale data. Existing `ProtectedRoute` gates loading, unauthenticated and wrong-role access. These client checks complement the unchanged FastAPI authorization; synthetic client tests do not independently prove server authorization.

## Frontend validation

Runtime: Node **v24.11.1**, Vite **8.2.2**, Windows; local timestamps include `+08:00`. Each linked command record contains its exact argv, working directory, start/end timestamps, duration, output and exit code. Latest recorded commands run through `.\.venv\Scripts\python.exe -B docs/testing/dashboard-d1/run_checks.py <check>` at repository root; frontend working directory is `frontend`.

| Check | Current result | Exact command record |
|---|---|---|
| Contracts and relevant auth/preferences/GA regressions | **PASS: 86 passed, 0 failed/skipped**; eight D1 plus 78 existing cases | [contracts](testing/dashboard-d1/20261021T164454161844+0800-contracts/command.json) |
| Production TypeScript/Vite build | **PASS**, exit 0; 213 modules | [build](testing/dashboard-d1/20261021T164454105993+0800-build/command.json) |
| Focused ESLint, all twelve changed/new TS/TSX modules | **PASS**, no findings | [lint](testing/dashboard-d1/20261021T164454105430+0800-lint/command.json) |
| D1 browser acceptance | **PASS: 16 scenarios plus one parent wrapper** | [command](testing/dashboard-d1/20261021T164423889032+0800-browser/command.json) |
| Existing GA dashboard browser regressions | **PASS: 51 scenarios plus one parent wrapper** | [final command](testing/dashboard-d1/20261021T164819634561+0800-ga-browser/command.json) |

Do not count parent wrappers as extra functional cases or combine API simulations with real backend acceptance. Full-project lint was not run; focused lint does not resolve previously documented unrelated findings. The build retains a chunk-size warning: main JS **833.03 kB**, gzip **235.57 kB**, above the default 500 kB threshold. No performance benchmark or optimization claim is made.

## Actual browser verification and screenshots

Actual headless **Microsoft Edge 155.0.4283.62**, controlled through the repository's Node/CDP test approach. React/Vite rendered real DOM and handled actual input/navigation. The D1 fixture served synthetic HTTP responses only: no FastAPI process, database, credential login or persisted workflow. Vite used `envDir=false`; only the owned fixture and browser processes were closed. Exact local application URLs, viewport sizes and timestamps are in [browser results](screenshots/dashboard-d1/20261021T164423889032+0800-browser/browser-results.json).

| Scenario group | Expected and observed result |
|---|---|
| D1-B01–B05 | Delayed catalog shows loading, then supplied components; code/title search and clearing work; empty data, unavailable service, retry and 403 remain distinct. PASS. |
| D1-B06–B08 | Home shows the synthetic account and truthful links; profile has separate read-only sections, loads metadata and survives refresh; missing fields remain unknown. PASS. |
| D1-B09–B12 | Missing record, wrong identity, service failure/retry and missing binding never select an alternative faculty or disclose its academic details. PASS. |
| D1-B13–B14, B16 | Wrong-role routes do not mount protected pages; anonymous routes redirect; synthetic 401 expires the client session; 403 reveals no academic details. PASS for client behavior only. |
| D1-B15 | Catalog, home and profile fit a 390-pixel viewport without horizontal overflow. PASS. |

All four PNGs were visually inspected for layout and privacy. They contain only synthetic data; original captures were not edited. Desktop viewport: **1366 × 1000**; mobile viewport: **390 × 844**. The mobile image records the visible viewport, not the entire scrollable profile.

- [D1-B01 subject catalog](screenshots/dashboard-d1/20261021T164423889032+0800-browser/D1-B01-subject-catalog.png)
- [D1-B06 faculty dashboard](screenshots/dashboard-d1/20261021T164423889032+0800-browser/D1-B06-faculty-dashboard.png)
- [D1-B07 faculty profile](screenshots/dashboard-d1/20261021T164423889032+0800-browser/D1-B07-faculty-profile.png)
- [D1-B15 mobile profile](screenshots/dashboard-d1/20261021T164423889032+0800-browser/D1-B15-mobile-profile.png)

## Initial failures and corrections

1. Two initial sandboxed browser attempts failed before any UI scenario: [Runtime.enable timeout](testing/dashboard-d1/20261021T163848+0800-d1/browser-command.json) and [Page.enable timeout](testing/dashboard-d1/20261021T164022+0800-d1/browser-command.json). Edge's browser-level connection responded; renderer commands timed out. The same isolated test could render after approved execution outside the sandbox. The recorded final D1 run passes with Runtime/Page domains enabled. No security flag, database access or production bypass was added.
2. The [first broader browser run](testing/dashboard-d1/20261021T164519205668+0800-ga-browser/command.json) had **49/51 scenarios pass**, two failures and a failed parent wrapper. A new assertion returned a DOM node instead of a Boolean to CDP; it now returns an explicit Boolean. An existing fitness screenshot exceeded its 10-second command limit; the screenshot-only timeout is now 30 seconds. The final full rerun passed 51 scenarios, including that screenshot. These were harness corrections, not GA behavior changes. Earlier failed evidence is retained.

## API, backend and database verification

- **Frontend API use PASS:** existing GET paths, cancellation, errors, identity matching and zero mutation requests exercised with synthetic responses. D1 browser results explicitly record zero mutation requests.
- **Live FastAPI authorization NOT RUN:** no backend service or real login was started. Existing server authorization source was inspected and unchanged; prior Phase 4A/4B evidence remains historical.
- **Backend tests NOT APPLICABLE to this frontend-only change:** no backend application code changed and no backend module was imported by the D1 runner.
- **PostgreSQL/migrations NOT RUN:** paused by user instruction. No database provisioning, connection, schema change, acceptance suite or Phase 4B fixture operation occurred.

## Preservation and remaining limitations

The pre-edit baseline contains **373 existing files/index entries**: tracked/untracked nonignored files, all existing files under `backend/data`, and the Git index. Exactly twelve existing frontend/package/test files changed for D1; all other **361** baseline hashes remained identical. No unexpected baseline modification is allowed. The preservation manifest records the protected preference SHA-256, original index hash, allowed paths and final verification. This is a file-scope check, not a claim to have inspected live database contents or reconstructed old saved-artifact provenance.

The first preservation-verifier attempt read the UTF-8 baseline using Windows' default text encoding and misdecoded one existing non-ASCII filename. Explicit UTF-8 reading resolves the false missing-path assertion; the original filename and content hash match. No user file was renamed or restored.

Pre-existing changes to `backend/data/faculty_preferences.json`, `backend/migrations/env.py`, the seven-table implementation and Phase 4C design/evidence were not authored or restored by D1. GA operators, fitness mathematics, RNG, checkpoint code, identities/account bindings, backend routes and existing schedules/history were not edited. No GA worker was started. No staging, commit, push, reset or cleanup of unrelated work occurred. Build/cache outputs are ignored generated frontend artifacts; owned browser profiles were removed after exit.

My Schedule remains a placeholder. External/GEC management, faculty change requests, Chair approval and institutional schedule revisions remain unimplemented. Institutional profile editing/academic CRUD, formal qualifications and reliable current-term workload are outside D1. Production data/browser acceptance and real service permission checks remain unverified by these synthetic tests.

## Safe reproduction and next milestone

Use Node and the installed frontend dependencies. From `frontend`, run `npm.cmd run test:dashboard`, the existing auth/preferences/GA contract scripts, and `npm.cmd run build`. Focused lint paths are in the recorded command. For isolated rendered acceptance, run the D1 evidence runner's `browser` check from repository root; Edge must be able to start its renderer. The runner supplies synthetic HTTP data and reads no `.env` credentials; it does not require PostgreSQL or a backend. A fresh evidence/screenshot directory is created for every run. Do not launch an institutional backend, rerun Phase 4B setup or provide production accounts merely to reproduce D1.

Manual synthetic checks: open the catalog, expand components, search code/title and clear; open the faculty home and follow Profile/My Schedule; check separate profile sections and refresh; inspect the mobile viewport. The automated scenarios additionally exercise missing/denied/unavailable responses. Close only owned fixture/browser processes. Never save institutional preferences to demonstrate this read-only milestone.

Thesis claim supported: functional metadata-backed React pages, client access/error handling and responsive rendering under an isolated synthetic API. This is not a usability study, scheduling-quality experiment, performance benchmark or PostgreSQL integration result.

Recommended **D2**: implement the server-filtered own-assignment endpoint and real My Schedule page, accurately labelled as a GA proposal until an approved publication lifecycle exists. D2, GEC workflows and Chair approval were not implemented here.
