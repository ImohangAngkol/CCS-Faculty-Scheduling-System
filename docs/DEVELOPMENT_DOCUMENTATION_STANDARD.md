# Development documentation and testing evidence standard

Applies to every future development phase of the CCS Faculty Scheduling Decision-Support System, including bug-fix subphases. Established 2026-10-16 (Asia/Manila).

## Required completion rule

A phase must include the sections and evidence below before it is presented for acceptance. Use PASS, FAIL, NOT RUN, BLOCKED or NOT APPLICABLE for individual verification items. Explain every omitted or unavailable check. A phase with missing evidence must be reported as incomplete or accepted with explicit limitations; an existing page, endpoint or screenshot alone does not establish correctness.

This is a development/review requirement. It does not introduce a CI gate or retroactively certify earlier phases. User instructions and the authorized scope of each task still govern implementation, data access and Git operations.

## Preserve and reference existing reports

Start by reading the README, [roadmap status](implementation-roadmap-status.md), [bug report](system-bug-report.md), relevant phase reports and tests. Reuse an existing phase report as the implementation account; append a dated verification section only when appropriate. Link to previous results and identify them as historical. Do not copy entire reports, rename them, move old screenshots or silently replace earlier failed results.

The Phase 1 metadata contract is in [api/phase-1-metadata.md](api/phase-1-metadata.md). Phase 2 through 4A implementation reports already live directly in `docs/`. The current Phase 4A evidence index is [thesis-evidence/phase-4a-evidence.md](thesis-evidence/phase-4a-evidence.md).

## Required phase report sections

| Section | Minimum required content |
|---|---|
| Objectives and requirements | Phase identifier, date/time zone, scope, requirement IDs where documented, acceptance criteria and explicit exclusions. Distinguish original requirements from new recommendations. |
| Files created or modified | Exact repository-relative paths, purpose of each change, migrations and test fixtures. Separate generated evidence from application changes. |
| Implementation details | Request/data flow, API contracts, configuration, compatibility, error handling and design decisions. State which services were unchanged. |
| Backend test results | Exact command and working directory, environment/runtime, test selection, start/end timestamps, exit status, passed/failed/skipped/deselected counts and sanitized evidence path. |
| Frontend test results | Same provenance as backend tests; separate model/contract tests, production build and focused/full lint. Record warnings and existing failures honestly. |
| Browser acceptance | Actual browser/tool and version, tested URL, production/development/isolated environment, fixture scope, step-by-step expected versus observed results, refresh/persistence and negative authorization checks where relevant. |
| Screenshots | Actual working UI captures, filenames, capture times, viewport/window dimensions, scenario IDs and descriptions. Visually inspect every image for correctness and privacy before inclusion. |
| API verification | Method, path, role, expected/actual status, validation/error behavior and storage-preservation checks. Never publish raw authenticated headers or responses. Mark NOT APPLICABLE with a reason when appropriate. |
| Database verification | Engine/version, isolated versus live environment, migration revision, schema/constraints/rollback/concurrency checks and results. Distinguish SQLite tests, PostgreSQL offline SQL and an online PostgreSQL migration. |
| Bugs found and resolved | Confirmed reproduction, impact, root cause if known, fix, regression and remaining risk. Link to the system bug report; mark unreproduced concerns UNCONFIRMED. Retain initial failures and identify reruns. |
| Known limitations | Missing evidence, untested platforms, deployment constraints, warnings, deferred work and any blocker. Do not claim deployment qualification from prototype tests. |
| Manual instructions | Prerequisites, safe account provisioning, isolation, reproducible steps, expected outcomes and cleanup limited to owned disposable resources. Never require a live institutional preference write to reproduce a test. |
| Thesis relevance | Map each supported prototype claim to requirement, test case, observed result and screenshot/report. Distinguish functional evidence from usability studies, performance benchmarks and GA-quality evaluation. |

## Evidence locations and naming

```text
docs/<existing-or-new-phase-report>.md        implementation account
docs/testing/README.md                      testing index and conventions
docs/testing/<phase>/<run-id>/               sanitized results and manifests
docs/testing/<phase>/                       reusable evidence-only fixtures
docs/screenshots/README.md                  image provenance and privacy policy
docs/screenshots/<phase>/<run-id>/           actual reviewed PNG screenshots
docs/thesis-evidence/README.md              thesis evidence index
docs/thesis-evidence/<phase>-evidence.md     requirement-to-evidence summary
```

Use a unique run ID, for example `2026-10-16-acceptance-01`, and scenario IDs such as `P4A-B01`. Store timestamps as ISO 8601 with an explicit offset (for example `+08:00` for Asia/Manila). Keep old artifacts intact. Screenshots should have descriptive names such as `P4A-B04-faculty-preferences-saved.png`.

Each run manifest must identify the source commit and dirty-tree scope; runtime/browser versions; commands and exit codes; fixture and storage isolation; scenario results; artifact paths; and limitations. Record SHA-256 hashes of approved evidence artifacts so later accidental edits are detectable. Hashes establish artifact identity, not independent proof that an application is correct.

## Safe testing and capture

1. Check Git status and the relevant existing documentation before edits. Record pre-existing user modifications separately.
2. Identify services already running without restarting or changing them. Use public health and anonymous session probes first; do not log in to an unknown production database.
3. Prefer existing isolated fixtures and synthetic accounts. Explicitly redirect every writable preference, settings, saved-result, history and checkpoint path used by a test. Child processes require their own isolation; parent monkeypatches do not cross process boundaries.
4. Do not change faculty preferences, institutional records, saved schedules or GA runs merely to produce evidence. For a safe persistence demonstration, save only a disposable test preference and verify it after reload against the same temporary store.
5. Run relevant backend/frontend regressions and applicable build/lint checks. Record exact failures, infrastructure limitations and skipped tests; do not silently turn a failed attempt into a clean first pass.
6. Use actual rendered browser captures, never generated artwork, mock screenshots or success messages fabricated through DOM editing. Label synthetic data and fixture substitutions explicitly. A screenshot of a dashboard with no run does not prove GA execution.
7. Capture only the target application. Clear password fields and close developer tools, credential prompts, unrelated tabs/overlays and private account lists before capture. Use synthetic identities, email domains reserved for testing and empty/synthetic course metadata where appropriate. Do not publish real names, IDs, preferences, passwords, tokens, cookies, database URLs, keys, connection files or raw HAR/session exports.
8. Sanitize logs before writing evidence. Prefer assertion summaries and HTTP status codes to full bodies. Keep temporary credentials outside the repository and remove owned credential handoffs after testing. Do not copy a database or a run checkpoint into the evidence directories.
9. Verify evidence links, image rendering, artifact inventory and content redaction. Compare protected-data hashes and Git index state with the pre-test baseline. Report unexpected modifications immediately; do not restore user data automatically.
10. Finish with created/modified files, new tests actually executed, failures/missing evidence, limitations and Git status. Staging, commit and push require authorization for that task.

## Interpreting test evidence

- A test using mocked HTTP responses demonstrates frontend behavior under that fixture; it does not prove backend authorization.
- Genuine authentication evidence must exercise real password verification, session lookup, role/ownership, Origin and CSRF checks. State any dependency overrides and distinguish storage isolation from a principal bypass.
- A 403 caused by a missing CSRF value does not independently prove ownership enforcement. Test cross-faculty access with valid credentials and CSRF separately.
- Count distinct cases once. Report browser parent wrappers separately and do not add a pytest wrapper and its underlying browser scenarios as independent security cases.
- Never infer a full-suite pass from focused tests. Preserve the distinction between a current run and results quoted from a historical report.
- SQLite FK tests and offline PostgreSQL SQL rendering do not verify PostgreSQL online locks, restart behavior, backups or deployment.
- For GA-related work, document lower-penalty-is-better semantics and evidence that authorized changes preserved hard constraints, evaluation counts and RNG behavior. Do not add optimization calls just to generate documentation evidence.

## Phase acceptance checklist

- [ ] Objectives, authorized scope and acceptance criteria are traceable.
- [ ] File inventory and implementation account are complete.
- [ ] Backend/frontend results include exact commands, dates, counts and failures.
- [ ] Browser scenarios and actual screenshots exist, or their absence is explicitly documented.
- [ ] API/database verification states its environment and any unverified behavior.
- [ ] Bugs, limitations and reproducible manual steps are recorded.
- [ ] Thesis claims link to specific evidence and do not overstate its scope.
- [ ] Sensitive information is absent; protected user data and GA state are preserved.
- [ ] Evidence links and artifact hashes have been checked.
- [ ] Final Git status and approval boundary are reported.
