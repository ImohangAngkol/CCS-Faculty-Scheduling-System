# U5P-C: read-only research console and operator handoff

Qualified 2026-11-09, Asia/Manila, on `main` at U5P-B
`1299d000a205287dbfc2d306decc427c98c2ee6e`. The isolated fictional console,
read-only API and bounded operator handoff are implemented and verified.
Production admission and institutional Saved Best promotion remain **BLOCKED**;
Continuous Optimization remains **DISABLED**; active checkpoint restoration is
unavailable; seven-day readiness remains **NO-GO**.

## Investigation and implementation boundary

U5P-B's `observe()` and `telemetry()` can append/backfill durable telemetry.
Its result method reconstructs an optimizer result through writable-capable
transactions. Reusing those methods in a GET would violate this milestone's
read-only contract. They remain unchanged. The new projection uses the existing
authorization, immutable bundle/context derivation, signed ledger, checkpoint
lineage and child-consumption proof validation through its own read-only handle.

Each observation opens the fixed, privately owned research database using SQLite
`mode=ro`, sets and verifies `PRAGMA query_only=ON`, then establishes a read
transaction before querying its metadata. A SQLite authorizer rejects DDL, DML,
ATTACH and writable PRAGMAs; a progress handler bounds SQL work. The transaction
rolls back and closes even on failure. No research migration, retention deletion,
telemetry append, optimizer execution, checkpoint restore or archive write occurs
in the observation path. Authentication session operations use a separate
disposable database in the demo and are not research-state changes.

The projection checks the private store identity, key/version binding, current
server-owned scoped mandate, fresh source guard, owner/department/catalog,
context MAC, full event chain and committed checkpoint/proof/result bindings.
It reconstructs context using private deterministic RNG state, without advancing
the caller RNG. Revocation, wrong owner, unknown run, corrupt state or unavailable
source fails closed. Administrator/Chair role labels and client headers do not
establish research authority. Institutional providers are not installed.

Four GET routes are registered in `main.py`. Their default provider returns None,
so ordinary application deployment reports unavailable rather than admitting
research execution. The optional isolated app factory exposes only these routes
and existing login/logout/me handlers, restricted to loopback. It does not include
U5P-B's operational HTTP routes. Existing fixed-generation endpoints are unchanged.

## API and data availability

All routes require the existing authenticated session and independently verified
research scope. Responses are private/no-store.

| Method/path | Projection and limits |
|---|---|
| GET `/api/research/observations/capabilities` | Fictional read-only availability and immutable safety flags |
| GET `/api/research/observations/runs` | Owner/department/catalog-filtered list; offset 0-1024, limit 1-10 |
| GET `/api/research/observations/runs/{run}` | Overview, verified provenance, original history projection, first telemetry page and checkpoint metadata |
| GET `/api/research/observations/runs/{run}/telemetry` | Ordered persisted events; after 0-256, limit 1-64 |

UUID parsing rejects malformed run IDs. The private ledger retains at most 256
events per run and the worker retains bounded checkpoints. No raw bundle, faculty
rows, schedule payload, checkpoint bytes, key, session cookie, signed receipt or
privileged command is exposed.

| Field | Meaning |
|---|---|
| Worker state and recorded reasons | Persisted observations |
| INTERRUPTED / RECOVERY_REQUIRED after an expired lease | Derived from the lease and original PID/creation-time liveness check; displayed alongside the stored worker state |
| Generation and best-so-far | Committed checkpoint/consumption proof, or explicit null if absent |
| Fitness chart | Original committed result history, checked for run binding, increasing generation and non-increasing best-ever penalty |
| Current chromosome fitness | Unavailable, not exposed by this projection |
| Satisfaction percentages | Unavailable, not emitted by the research worker |
| Academic labels | Server-owned FICTIONAL labels; technical verification confers no institutional authority |
| Checkpoint | Bound sequence and fingerprint only; restoration remains blocked |

GET never fills gaps in telemetry. A newer worker record can coexist with older
persisted events; the page explains this. A not-consumed run is explicitly
UNVERIFIED_NOT_CONSUMED. A verified child proof yields
TRUSTED_FICTIONAL_CONSUMPTION, not CURRENT institutional evaluation or approval.

## Frontend

`/research/runs` is an authenticated standalone dashboard route, linked from the
administrator sidebar. Server-side scope still governs reads for every account.
The teal/gold page provides run selection, independent list/detail retry, empty
and unavailable states, provenance, timeline, checkpoint metadata and exact
recorded fitness values including zero. It reuses the existing ConvergenceChart
without modifying that component or including its unrelated working-tree edits.

Responses pass strict typed API schemas and cross-run/context/cursor/order
checks. React text rendering escapes imported strings. AbortControllers, keyed
account/run/refresh state and response guards reject stale completions. Active
selected runs receive at most six automatic refreshes, ten seconds apart, with
an eight-second request timeout. Errors, terminal states, switching selections
and unmounting stop polling. Run-list refresh and pagination are manual.

There are no execution, restore, approval, application or Saved Best controls.
Refreshing a chart or list is a GET. The existing disabled institutional
Continuous Optimization interface is unchanged.

Final genuine live screenshots:

- [Completed original worker and exact history](testing/dashboard-u5pc/20261109T171137596488+0800-live/L03-real-worker-history.png).
- [Derived interruption, explicitly injected fixture metadata](testing/dashboard-u5pc/20261109T171137596488+0800-live/L06-injected-expired-owner.png).

All captures were visually reviewed. Earlier viewport-only PNGs are retained;
they establish the header/list view and do not show the off-screen chart. Later
captures are genuine full-page CDP PNGs. No screenshot was generated or edited.

## Fresh verification and retained failures

| Selection | Final result | Evidence scope |
|---|---:|---|
| Observation projection | 24 passed | Scoped reads, enforced read-only handle, denied writes, corruption, concurrent readers, ordering/pagination, unavailable metrics, expiry, restart, zero and RNG preservation |
| Live console/handoff | 2 passed | One pytest case contains 9 actual Edge scenarios; the other starts/stops the separate documented operator host |
| Bundle parity | 5 passed | Original engine versus verified bundle consumer |
| Current-release V1 checkpoints | 10 passed | Actual creation, load, continuation and RNG/schedule equivalence |
| U5A-U5C regressions | 99 passed | Compatibility, academic-context and source qualification |
| U5D receipts | 36 passed | Existing receipt behavior; not a new institutional verification claim |
| U5H consumption | 39 passed | Optimizer/consumption/checkpoint behavior |
| Unmodified U5P-B suite | 50 passed, 1 failed | Historical no-research-routes assertion conflicts with intentionally added GET-only routes |
| Selective frontend contracts | 361 passed | Committed U5P-B UI plus only U5P-C overlay; 342 existing + 19 new |
| Intercepted HTTP browser | 12 scenarios passed | Actual Edge/React with fictional intercepted responses; Node reports 13 tests including its parent test |
| TypeScript, production build, focused ESLint | PASS | Independently selectable frontend snapshot |

The selected final Python outcomes comprise **265 passes and one explicitly
retained historical assertion failure**, not a fully green repository-wide suite.
Rerun passes are not summed. The original 455.0 parity check again verified exact
assignments, fitness history/breakdown, faculty accounting and global RNG equality.
The current V1 engine identity matches the prior qualified release; strict
fingerprint checks were not modified. Historical checkpoint limitations remain.

The nine live scenarios used real React login, real FastAPI sessions, TCP HTTP,
a genuine bounded Windows worker and new disposable SQLite. All research network
requests were GET. Research files were byte-identical before/after browser reads;
reconstructing the API/observer returned equal observations. The interruption
scenario deliberately injects expired-owner metadata; it is not a fresh physical
supervisor crash. The unmodified U5P-B suite separately reran its real parent-crash
and orphan cases. No live PostgreSQL operation was performed.

All intermediate records remain:

1. First contracts run: 342 passes and one module-load failure because the new
   fixture was omitted from the snapshot overlay. Corrected overlay; final 361
   contracts pass.
2. Initial TypeScript run: optional detail-error text passed to a required string
   prop. Added the fixed fallback. Final TypeScript/build/lint pass.
3. Initial live browser: login succeeded; the exact-zero assertion selected the
   shared chart legend's table instead of the exact-values table. Narrowed the
   selector to its caption. Final nine scenarios pass.
4. Standalone handoff startup: backend module path was absent. A separate
   read-only module-resolution probe confirmed the defect. The first test did not
   capture startup stderr, so no historical traceback is invented. Added the
   exact snapshot-relative backend path and future sanitized stderr capture;
   final real separate-process startup/owned-stop passes.
5. `test_original_http_and_production_providers_unmodified` still asserts that
   no `/api/research/` path exists. It was not edited, skipped or relabeled PASS.
   The new boundary test verifies exactly four GET-only routes and no configured
   provider. This intentional contract expansion is the reason for the remaining
   failure, not a new authority or execution route.

The first evidence-seal attempt stopped when the privacy scanner matched its own
quoted fictional noncredential marker. The failure is retained. Expressing that
exact literal by concatenation removed the self-match; scan patterns and the
file-specific fixture exception were not broadened. No sensitive value was found.

A second seal attempt caught pre-existing whitespace in AppRoutes. No file was
reformatted. The auditor now proves all original integration-file bytes by
inverting only the five approved insertions in memory, checks added lines with
Git, and continues whole-file whitespace checks for every new artifact. Both
audit stops and their reconciliations remain in evidence. A third stop recorded
the default Git check treating new CRLF registration lines as whitespace. The
explicit CRLF-aware check retains blank-at-eol, blank-at-eof and space-before-tab
checks and passes without normalizing working-tree bytes.

Recorded dependency warnings concern Starlette's deprecated httpx TestClient
integration and anyio BlockingPortal alias. No dependency was installed or changed.

## Reproducible Windows commands

Run from the repository root. Existing Python/Node/Edge dependencies are reused.
No environment credentials or database connection URLs are required.

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pc/run_checks.py observations live parity legacy regressions receipts consumption
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pc/run_checks.py bridge
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pc/frontend_checks.py contracts-all build bundle lint preview-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pc/audit_evidence.py
```

The bridge command is expected to retain the single historical route assertion
failure described above. Commands create fresh timestamped evidence and refuse
overwrite; after new executions, an already sealed manifest intentionally fails
inventory replay until a separately reviewed addendum accounts for new artifacts.
Do not rewrite the sealed historical manifest automatically.

Snapshot tooling archives the committed U5P-B tree, excludes real data/runtime
stores, creates the previously qualified tiny empty import tables and overlays
only U5P-C files. The original release byte recipe is applied only to matching
unchanged source; the U5P-A caller uses its actual committed bytes. Existing
dependencies are junctioned without installation; Vite caches and pytest temp
files remain in the owned snapshot. The original eleven UI/data edits are not
silently included in checkpoint-only tests. Whitelisted child environments omit
database URLs, credentials and institutional authority switches.

## Operator handoff

1. From the root run the bounded fictional handoff:

   ```powershell
   .\.venv\Scripts\python.exe -B docs/testing/dashboard-u5pc/run_checks.py handoff
   ```

2. The tool prepares a new owned snapshot, invokes the existing U5P-B admission
   and bounded runner internally, waits for one genuine fictional generation,
   and starts a loopback GET-only API and Vite host. It also prepares a CREATED
   example and an explicitly injected expired-owner example. There is no browser
   execution command, privileged token or institutional source.
3. Read the printed console URL and private login-file path locally. The login
   file is under the worker's private OS-temp root, outside Git, using its
   existing verified private-directory ACL. Never print, archive or paste its
   contents. Use a fresh isolated Edge profile to avoid existing localhost
   cookies; enter these fictional credentials privately in the actual login page.
4. Open the printed URL ending `/research/runs`, select COMPLETED, inspect the
   FICTIONAL context, committed batch events, exact zero history and checkpoint
   sequence. Zero starting penalty establishes parity, not convergence or useful
   optimization improvement. CREATED has unavailable generation history; the
   expired-owner example displays a derived interruption alongside RUNNING in
   the worker record. Neither is silently reported successful.
5. Reload and select again. Only durable observations return. Backend tests also
   reconstruct the complete API/observer and verify equality; a separate host
   restart requires the same permit, source, owner/store identity and intact
   private key. The convenience handoff command always creates a new store; it
   does not attach, restore or reinterpret old runs.
6. To inspect/export evidence, inspect only authenticated research GET response
   JSON (runs/detail/paginated telemetry) in the browser, with at most ten runs
   or 64 events per page. Review the sanitized DTO and save an optional copy in
   owned private storage. Do not export HAR, auth headers/bodies, cookies, raw
   database files, bundles, checkpoint payloads or keys. No export implies approval.
7. The host expires after 300 seconds. To end it sooner, create only the printed
   owned `CONSOLE.stop` marker. It closes its API/frontend and verifies worker
   quiescence; it does not reset/delete the private research database or stop
   unrelated services. No active checkpoint restore is offered.
8. Replay the evidence auditor to check that protected application stores and
   the original working-tree changes remain untouched. Do not archive the private
   handoff or login file. No seven-day experiment is launched by this procedure.

Actual automated evidence confirms separate-process host readiness, owned-marker
shutdown, exit zero and private credentials excluded from artifacts. A person
performing this handoff manually was not observed; that is not claimed.

## Inventory, preservation and checkpoint plan

Only three pre-existing files changed, by five added registration/navigation
lines: `backend/main.py`, `frontend/src/routes/AppRoutes.tsx` and
`frontend/src/layouts/AdminLayout.tsx`. They were clean at entry. New production
files are `backend/services/ga_research_observation.py`,
`backend/routers/research_observations.py`,
`frontend/src/api/researchObservations.ts` and
`frontend/src/pages/ResearchConsole.tsx`.

New test files are `backend/tests/test_research_observations.py`,
`backend/tests/test_research_console_live.py`,
`backend/tests/research_console_support.py` and the six
`frontend/tests/researchObservations.*` / `researchConsole.*` helpers/tests listed
in the exact inventory. Tooling and all successful/failed evidence are under
`docs/testing/dashboard-u5pc/`. The machine-readable
[manifest](testing/dashboard-u5pc/manifest.json) and
[selective staging plan](testing/dashboard-u5pc/staging-plan.json) enumerate every
exact path, artifact SHA-256 and proposed raw Git blob identity. No broad directory
staging is appropriate. The staging plan is a proposal; nothing was staged.

The pre-edit baseline records 5,005 paths. Exactly the three authorized routing
files differ; the other **5,002** remain byte-identical. All 23 academic files,
protected local preferences/settings, original GA/operator/scoring/RNG modules,
migrations, checkpoint/schedule/archive stores, prior research and historical
evidence are unchanged. The original **11 tracked modifications and 958 unrelated
untracked files** remain intact. All **1,377** prior manifest artifact references
are rehashed. Git HEAD and index remain unchanged. Text/privacy/PNG integrity and
CRLF-aware Git whitespace/integrity checks are recorded by the auditor.

For a separately authorized checkpoint, use two reviewed groups:

- `feat(ga): add read-only isolated research console (U5P-C)` for the exact
  application/tests group in the plan, including only the three clean-at-entry
  integration files.
- `docs(testing): archive U5P-C console and operator qualification` for the exact
  remaining report/tooling/evidence paths, retaining every failed attempt.

Use literal explicit paths, `core.autocrlf=false` and raw blob verification. The
plan/manifest cannot contain their own final blob identity without circularity;
calculate those separately after sealing. No partial staging is needed for these
three integration files. Exclude all eleven original tracked edits and all 958
unrelated untracked paths. Git network/ref/staging operations were not performed.

## Remaining limits and recommended U5P-D

This qualifies a tiny, bounded fictional workflow and independent selective
snapshot, not full institutional deployment, hostile-OS security, every browser,
high-volume polling, long-duration stability or real academic approval. SQLite
read transactions are coherent; filesystem/authority checks do not establish a
distributed institutional transaction. Private HMAC/ACL guarantees inherit U5P-B's
limitations against a malicious OS/store owner or whole-store rollback. No new
telemetry producer was added, so gaps remain visibly unavailable. Independent
source/mandate/catalog providers remain absent in production. Fixed-generation
U5D receipts and current-evaluation policy remain unchanged.

Recommend U5P-D qualify operator-owned observation continuity and telemetry
freshness under bounded running/interruption/restart conditions, plus resource
and deployment-storage limitations, before considering operational controls or
longer experiments. Define any new control authority and recovery policy
separately. Do not activate production, continuous execution, checkpoint restore
or seven-day research on the basis of this console. U5P-D was not implemented.
