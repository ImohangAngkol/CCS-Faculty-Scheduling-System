# U5P-D: observation continuity and telemetry freshness

Completed 2026-11-10, Asia/Manila, against U5P-C `3719af0734e395bf2b905a13ab6ccc1ca7dda5f9` on `main`.

**Isolated fictional v2 functional checks are complete; full preservation signoff and Git checkpoint readiness are BLOCKED by an entry-baseline coverage gap.** Production admission and institutional Saved Best promotion remain BLOCKED; Continuous Optimization remains DISABLED; active restoration remains unavailable; seven-day readiness remains NO-GO. No worker limits, original optimizer, scoring, RNG, publication authority, production provider or existing backend source were changed.

Final distinct selections produced **297 Python passes and one unchanged historical assertion failure, 391 frontend contracts, nine real Edge/FastAPI/SQLite scenarios, 16 new intercepted-HTTP browser scenarios and 12 existing intercepted-HTTP browser scenarios**. TypeScript, production build and focused lint passed. These are selected regressions, not a completely green repository-wide suite. Reruns are retained and are not added to the final counts.

## Architecture and scope

The original U5P-C `Observer`, four authenticated GET routes, production `main.py` registration and provider defaults are unchanged. `ContinuityObserver` is an explicit new `research-observation-v2` adapter over that reader, installed only in the disposable fictional test/handoff environment. It inherits principal/scope authorization, context and checkpoint verification, authenticated ledger validation, SELECT-only SQLite snapshots and bounded reads. No POST, worker control, ledger repair, checkpoint restoration or institutional connection was added.

The same route contract remains:

- `GET /api/research/observations/capabilities`
- `GET /api/research/observations/runs`
- `GET /api/research/observations/runs/{run}`
- `GET /api/research/observations/runs/{run}/telemetry`

The frontend accepts strict v1/v2 DTOs. A v1 response retains its recorded observations but has **UNKNOWN freshness** because it lacks the new evidence. The ordinary production source is still unavailable. A successful isolated test does not activate the adapter in production or establish institutional authority.

## Freshness contract

`research-freshness-v1` distinguishes source time, server verification time and browser retrieval time. The source is the timestamp in the verified durable fictional research ledger; HTTP success is retrieval evidence only.

| Classification | Required evidence and meaning |
|---|---|
| FRESH | Valid, ordered source timestamps with latest age at most 30 seconds. This is observation recency, not a worker-health probe. |
| STALE | Age exceeds 30 seconds. The worker is not declared terminated or completed. |
| UNKNOWN | Missing timestamps, unsupported legacy source, excessive future skew, backwards source time, interrupted ownership or insufficient terminal confirmation. |
| TERMINAL | Durable terminal state, matching lifecycle event/tip/fence and released owner, with recorded native-process exit verification. Silence is never terminal evidence. |

The 30-second threshold is a deliberately conservative **research-console display threshold**, covering three nominal ten-second refresh intervals. It is not a guaranteed worker heartbeat, scheduling SLA or institutional policy. Future skew up to two seconds is tolerated explicitly without changing the source value; larger future times become UNKNOWN. Finite numeric timestamps are required; booleans, malformed values and unsupported state values are rejected. Missing optional timestamps are represented explicitly, not fabricated from retrieval time.

Event order follows verified sequence order. Equal timestamps and duplicate observations do not renew freshness; backwards or delayed timestamps do not become a newer observation by arrival order. Malformed records fail closed rather than being omitted or rewritten. TERMINAL has a separate telemetry-age classification as of the server snapshot. Its reason describes terminal confirmation; the underlying age remains visible. The browser ages FRESH to STALE between reads using elapsed monotonic time; it cannot make a stale record fresh.

Terminal confirmation checks the matching run, worker and lifecycle records, including the existing one-fence increment for a recorded user stop. All recorded child processes must be EXIT_VERIFIED. Completed-result proof validation still comes from the original reader. Interrupted or abandoned ownership is UNKNOWN, with the recorded/derived state and reason separately displayed.

## Backend continuity evidence

All new execution data is fictional and stored in newly owned private temporary SQLite/file namespaces. Authentication uses a separate disposable identity database. No repository database, PostgreSQL server or retained D15 state was accessed.

| Condition | Actual verification and limitation |
|---|---|
| API unavailable while worker executes | Real TCP listener stopped before a test-only dispatch barrier releases the original native optimizer. Worker completes while the listener is down; reconstructed API returns equal durable observations. Same-host reconstruction, not institutional failover. |
| Browser refresh | Actual Edge reload restores the validated run UUID from the URL and rereads authorized observations. No cookies or payloads are copied into browser storage. |
| Storage unavailable | Real SQLite EXCLUSIVE lock makes the read unavailable; release and retry recover. Separate browser HTTP 503 uses an explicitly injected private fixture marker. |
| Concurrent readers | Real bounded read-only SQLite snapshots return consistent results without research-store mutation. |
| Partial/missing/malformed records | Explicit missing timestamps yield UNKNOWN; invalid signed payload/state/time is rejected. No backfill or silent repair. |
| Duplicate/delayed/out-of-order data | Deterministic tests retain sequence provenance and reject/regard uncertainty correctly. Duplicate source time is not a heartbeat. |
| Terminal persistence | Actual bounded worker completion, persisted proofs/checkpoints and verified cleanup survive API reconstruction. Zero penalty is preserved exactly. |
| Orphaned owner/supervisor interruption | Existing real Windows parent-crash scenario is observed through v2: parent exit 23, reconstructed state INTERRUPTED, freshness UNKNOWN; no active restore. |
| Read-only behavior | Research bytes, RNG and checkpoint identity checked before/after GETs; auth activity is isolated from research persistence. |
| Authorization | Actual sessions and server-scoped permits, cross-owner denial and unscoped administrator denial. Administrator status is not department authority. |

The API-offline barrier and browser fault marker are test infrastructure, not production scheduling changes. Expired-owner browser metadata is an identified fixture injection; real parent interruption is separately tested. No physical machine crash, separate-machine failover or institutional storage acceptance is claimed.

## Frontend resilience

Only the research API DTO module and research-console page are modified existing files. A new pure helper handles freshness, history advance and bounded merging.

- Transient request/storage failures retain already authorized details, chart values and the last successful retrieval time, with an error and independent retry. Run-list failure does not erase a valid selected run.
- Definite authentication, authorization, integrity and disappearance responses (401/403/404/409/410/422) invalidate cached observations. Selection/account changes cancel in-flight reads. Late responses cannot overwrite a newer selection.
- Run/context, checkpoint sequence and event-prefix regression are rejected. History is bounded to 256 events, 21 fitness points, pages of 64 events and ten listed runs.
- Per selection or explicit retry there is one initial detail read and at most six automatic refreshes, scheduled ten seconds after each response, with an eight-second request timeout. Error, terminal state, navigation or unmount stops automatic refresh. The approximately 70-second browser test exercises the complete refresh bound; a separate cancellation case waits beyond one interval.
- The URL retains only a validated run UUID. Refresh performs authorization again. No payload, password or source permit is persisted in local/session storage.
- Existing convergence rendering is reused. Best penalty zero stays zero. Unavailable current-fitness and satisfaction metrics are labelled unavailable. No generation values, improvement or operational controls are invented.

## Final validation and unsuccessful attempts

Each timestamped `command.json` records the isolated snapshot, exact command, current-source hashes, elapsed time, exit code and sanitized output. The manifest identifies the final selection and retains all earlier attempts.

| Final selection | Result |
|---|---:|
| New continuity/oracle/native tests | 32 passed |
| Existing U5P-C observations | 24 passed |
| Optimizer parity | 5 passed |
| Fixed/legacy GA, including three real current-V1 checkpoint write/load/continuation fixtures | 10 passed |
| New real API/browser integration | 2 pytest tests passed; nine browser scenarios |
| Relevant U5A-G/monitoring regressions | 99 passed |
| Receipt regressions | 36 passed |
| Verified consumption regressions | 39 passed |
| Existing research bridge/supervision/storage | 50 passed, one unchanged historical expectation failed |
| Frontend contracts | 391 passed, including 30 new contracts |
| New intercepted-HTTP Edge scenarios | 16 passed |
| Existing intercepted-HTTP Edge scenarios | 12 passed |
| TypeScript / production build / focused ESLint | PASS / PASS / PASS |

The retained failure is `tests/test_research_bridge.py::test_original_http_and_production_providers_unmodified`, which asserts that there are no `/api/research/` routes. U5P-C already introduced four read-only routes. Its source was not weakened or changed. This historical expectation mismatch remains a real failing assertion in the recorded selection; it does not establish a new U5P-D authorization failure.

Original nonzero worker parity records **455.0** for original and worker output, with identical schedule, fitness history, breakdown, faculty results and RNG, no Saved Best promotion and unchanged caller RNG. Three current V1 fixtures exercise actual checkpoint creation/load/resume with matching engine identity and schedule/RNG. This does not make the six incompatible historical checkpoints resumable; they remain untouched.

Two dependency warnings are retained: Starlette's deprecated httpx TestClient integration and the deprecated anyio BlockingPortal alias. No dependency was installed or changed.

The first combined lint attempt timed out (configured 300 seconds, observed elapsed 1,636.94 seconds) during severe host memory pressure. Near that attempt the host reported 98% physical RAM use, about 258 MiB available and 1.15 GiB commit headroom. The user offered to free RAM. Later sampling showed about 3.65 GiB available. This supports resource pressure as a concern but does **not conclusively establish the timeout's cause**. Per-file lint passed against the unchanged failed-attempt source, and the final combined lint passed without increasing its timeout. The timeout record remains intact.

Initial screenshots exposed incorrectly decoded separator characters. Only those page literals were replaced with ASCII separators; original screenshots and source identities are preserved in `separator-encoding-diagnosis.json`. The final contracts, TypeScript, build, lint, new/legacy browser suites and live integration were rerun against the corrected page. Fourteen genuine PNGs, including intermediate captures, were visually reviewed for fictional scope and privacy; no image was edited or fabricated.

## Resource and retention findings

No limits were raised and no host power/process settings were changed.

| Boundary | Existing limit/finding |
|---|---|
| Worker wall time | Default 120 seconds; hard maximum 600 seconds. Not suitable for a seven-day optimization session. |
| Generation / concurrency bounds | At most 20 generations; one active worker by default, configurable maximum two. |
| Windows child resources | 768 MiB private-commit cap and 60 seconds user CPU per child by default; five-second grace. Per-child CPU is not a whole-run CPU budget or rate quota. |
| Recorded child observations | Private-commit peaks 623,165,440 and 739,225,600 bytes; user CPU 2.375 and 6.125 seconds; zero active processes after exit verification. These samples do not prove host-wide headroom under concurrency. |
| Research persistence | Supervised main database bound 64 MiB, minimum free space 64 MiB, one backup. No qualified filesystem quota covering journals, backup, checkpoint and host totals. |
| Telemetry / checkpoints | 256 events/run and 8 KiB/event; at most 21 proofs of 8 KiB each; fixture store four runs; default eight checkpoints, 8 MiB each / 64 MiB per run. No automatic deletion was introduced. |
| Reads | Existing SQL progress budget, bounded pages/history and seven detail reads per explicit selection/retry cycle. Multiple operators remain an aggregate-load concern. |
| Disk | Instantaneous repository-volume free space 23,668,891,648 bytes. Free space is not a reserved quota or retention guarantee. |
| Sleep / hibernate | Read-only current AC/DC sleep and hibernation timeout queries both returned zero. Earlier U5O's 12-hour AC result is historical. Manual sleep, lid, battery exhaustion and power-loss behavior remain untested. |

Four browser CDP samples reported approximately 21.55-24.33 MiB used JS heap during different views; final sample approximately 23.35 MiB. They are JS heap/DOM observations only, **not browser-process RSS, private commit, a continuous peak, or a long-duration leak assessment**. No forced GC or allocator setting change was used. Different DOM sizes and short runs prevent a sustained-retention conclusion.

Seven-day readiness remains NO-GO: wall-time limits, aggregate physical resources, durable storage/retention, authorized recovery and institutional providers are not qualified for that experiment. A changed power timeout alone does not resolve those blockers.

## Reproduction and operator handoff

From the repository root in PowerShell, use the existing dependencies. Each test runner builds an isolated snapshot of committed prerequisites plus the exact U5P-D overlays, fictional import tables and fresh private storage. It does not overlay unrelated working-tree UI changes or institutional datasets. New evidence directories are exclusive and existing artifacts are not overwritten.

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pd/run_checks.py continuity observations parity legacy live regressions receipts consumption
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pd/run_checks.py bridge
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pd/frontend_checks.py contracts-all build bundle lint preview-browser legacy-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pd/audit_evidence.py
```

The bridge command deliberately preserves the documented one-failure outcome. Additional test executions create new artifacts and require an explicit additive evidence reconciliation before a checkpoint; the sealed inventory must not silently absorb them.

An optional, bounded operator procedure is prepared:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pd/run_checks.py handoff
```

This standalone handoff wrapper was **not separately executed in U5P-D**. Its original U5P-C base procedure was qualified previously; the new v2 adapter, real host, authentication, worker and browser behavior are verified by the tests above. Treat the manual wrapper procedure as prepared, not an additional completed acceptance scenario.

The procedure creates a fresh fictional environment, runs one bounded existing worker before observation, and serves the console for at most five minutes. It prints the console address, a private login-file path and its own stop-marker path; it does not print the login secret. Open the private file locally, sign in through the actual login page using an isolated browser profile, and do not copy credentials, cookies, permits or HAR files into evidence. Stop only through its printed owned marker or finite expiry; do not terminate unrelated services.

For an evaluator:

1. View the recorded completed run, exact zero penalty and generation history. A zero-start history does not demonstrate improvement or convergence from a worse solution.
2. Compare last source observation, snapshot verification and last successful retrieval. An old CREATED observation may be STALE while its recorded state remains CREATED; that is not confirmed failure.
3. Explain UNKNOWN for absent legacy timestamp/expired ownership and TERMINAL only for bound lifecycle/cleanup evidence. HTTP errors retain history but do not certify health.
4. Reload the selected run and use retry for a failed read. The URL preserves only the run ID; authorization and source verification run again.
5. Explain that same-store API reconstruction was tested, but this command creates a new fixture on every invocation. It is not an active restore or a general service failover tool.
6. Export only scoped public observation JSON if separately needed, without headers/private stores/keys/checkpoint payloads. No institutionally approved schedule or genuine authority is represented.

## Preservation, privacy and checkpoint proposal

The entry baseline covers 5,121 paths, including selected ignored protected/runtime artifacts and the Git index. Exactly two baseline files were intentionally changed; **5,119 remain byte-identical**. This includes all 23 academic files, both protected JSON local states, original GA/scoring/RNG sources, migrations, baselined Saved Best/schedules/checkpoints, prior evidence and index. HEAD is unchanged. The original 11 unrelated tracked modifications and 958 unrelated untracked files are preserved and excluded.

**Coverage blocker:** the final full-directory membership check correctly stopped on eight additional ignored artifacts belonging to one pre-existing run: four saved-result/snapshot files, two checkpoint/status files and two input receipts. Their filesystem creation/modification timestamps are from the previous evening, before the 07:51 entry baseline. The entry inventory reused prior protected runtime paths and omitted this later pre-existing run. No entry hashes exist for those eight, so their before/after byte identity cannot be proved. Their current hashes and timestamps are recorded in `preservation-coverage-gap.json`; they were not edited, removed or repaired. Timestamp evidence is not retrospective preservation proof. The original baseline is retained unchanged. Full preservation must not be claimed until this scope gap is separately reviewed; the proposed Git checkpoint remains BLOCKED.

All 1,495 prior artifact references are reconciled. Old U5P-C hashes for the two intentionally edited frontend source files and the already different working-tree AppRoutes bytes are verified against the committed U5P-C blobs. Historical evidence bytes themselves remain unchanged. The pre-existing AppRoutes working file is not edited or included.

The new audit scans complete/truncated encoded-token patterns, credential URLs, authentication assignments and private faculty names locally without exporting their values; structurally and visually reviews PNGs; compiles new Python source without import; checks raw SHA-256/Git blob identities, CRLF-aware whitespace and Git object integrity. It never connects to a database or stages files. Hashes establish byte identity, not institutional correctness.

The first seal attempt stopped at its tracked-name assertion: forcing `core.autocrlf=false` exposed the already-baselined mixed-CRLF AppRoutes working representation as a diff. Its raw SHA-256 still exactly matched entry and its index blob matched HEAD. `audit-line-ending-reconciliation.json` retains this audit-tool failure and byte counts. The new auditor now compares tracked names using the same repository conversion as entry, while preserving raw hashes independently. Whitespace checks cover the two authorized diffs and all new text artifacts; unrelated working files are not normalized or staged. No seal was created by the failed attempt.

Modified existing files:

- `frontend/src/api/researchObservations.ts`
- `frontend/src/pages/ResearchConsole.tsx`

New implementation/test files:

- `backend/services/ga_observation_freshness.py`
- `backend/services/ga_research_continuity.py`
- `backend/tests/test_observation_continuity.py`
- `backend/tests/test_observation_continuity_live.py`
- `frontend/src/services/researchFreshness.ts`
- `frontend/tests/observationContinuity.test.mjs`
- `frontend/tests/observationContinuity.fixtures.mjs`
- `frontend/tests/observationContinuity.browser.test.mjs`
- `frontend/tests/observationContinuity.live.mjs`

This report and every new tooling/diagnostic/command/proof/screenshot path under `docs/testing/dashboard-u5pd/` are enumerated individually in `staging-plan.json` and `manifest.json`. The plan is the exact selective checkpoint proposal, including raw-byte blob identities and exclusions, explicitly marked BLOCKED and not authorized for staging. No mixed-file partial staging is required for the two clean-at-entry research frontend files. Do not stage AppRoutes, the eight ignored run artifacts or any of the original 11 modified files. The two seal files' blob identities are computed after sealing to avoid self-hash recursion. Nothing has been staged, committed or pushed.

Suggested logical messages, subject to separate review/authorization:

- `feat(ga): qualify read-only observation freshness and continuity (U5P-D)`
- `docs(testing): archive U5P-D continuity and resource findings`

## Remaining blockers and U5P-E recommendation

The isolated v2 functional path passed its selected checks, but **Git checkpoint readiness remains BLOCKED** on the eight-path preservation-coverage gap. The historical test mismatch, lint timeout and manual-wrapper qualification limitation are also retained. The audit returns exit code 2 for the documented coverage blocker even when all other checks pass. Its manifest seals current evidence without certifying missing before-hashes. Production backend installation is intentionally absent. No claim is made that ordinary production observations now have v2 freshness.

Recommended U5P-E: qualify a bounded operator session and deployment-storage/reconstruction contract, including explicit same-store ownership across API process restarts, aggregate CPU/private-commit/disk enforcement and retention accounting, before adding any execution controls or lengthening runs. First separately exercise the prepared manual handoff. Preserve the original optimizer and keep institutional authority, promotion and active restoration blocked. Institutionally scoped source/authority providers and approved recovery policy remain separate prerequisites. Do not begin the seven-day experiment or silently revise the historical no-routes assertion during checkpoint preparation.
