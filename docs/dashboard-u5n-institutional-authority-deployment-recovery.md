# U5N: authority, deployment storage and recovery qualification

2026-11-09, Asia/Manila. Baseline: `main`, `ed35d620111490d3021567ba7dcc6b26ec93d212` (U5M). **Isolated recovery authorization and writable checkpoint quarantine are implemented. Native parent/worker containment is qualified for the tested launcher. Institutional authority and deployment remain UNQUALIFIED/BLOCKED; continuous execution UI remains DISABLED.** Quarantine is deliberately not activation of a restored worker or replacement of an existing scheduling store.

## Preservation and prerequisite investigation

Reviewed U5G-M reports, manifests and checkpoint ordering, M's receipt repair, G immutable bundles, H consumption/checkpoint codec, I durable ownership, J independent mandate/capture/storage adapters, K/L bounded workers and Windows containment. Also reviewed real authentication/preference ownership, D12 Chair mandates, D13 application authority, immutable decisions/versioning, and existing storage/backup interfaces. [Prerequisite report identities](testing/dashboard-u5n/prerequisite-review.json) identify the unchanged documents. No AGENTS.md was found.

The [entry inventory](testing/dashboard-u5n/entry-review.json) verifies **11 unrelated tracked modifications and 958 unrelated untracked files**. The pre-edit [baseline](testing/dashboard-u5n/preservation-baseline.json) records **4,271 existing paths**, including the Git index, all 23 academic files, both protected local JSON modifications, all original GA/fitness/RNG/version bridges, migrations, notebooks, Saved Best, historical schedules/checkpoints, prior evidence and unfinished research/UI work. All remain byte-identical. **No existing tracked or untracked application file is modified by U5N.** New functionality is in separate unregistered qualification modules, guarded by the existing fictional-source snapshot contract.

No PostgreSQL or institutional database was accessed, and no schema migration was executed. Disposable SQLite schemas are created only inside newly owned private fixture stores. D15's retained PostgreSQL state and acceptance evidence are unaffected. No deployment account, credential, service, existing ACL, storage root, historical backup or original run was modified. No dependency installation, Git staging, commit or push occurred.

## Identity and authority boundaries

Existing session authentication hashes opaque cookies and resolves active users through server-side database state. The account roles administrator/faculty and verified faculty bindings are distinct from department appointments. Client headers, query parameters, displayed labels and ownership claims never establish scoped optimization authority. Account role changes, credential changes, expiry, disablement and logout invalidate sessions as tested in the unchanged M qualification.

| Capability | Required authority and U5N finding |
|---|---|
| Faculty preference writes | Authenticated own faculty binding; priority changes retain administrator-only checks. Three new actual handler tests verify own persistence and cross-faculty/forged-role denial using fictional metadata and SQLite. |
| Administrative operations | Existing server account role grants only the operation's existing administrative permission, not Chair/recovery/optimization scope. |
| Chair final decision | Independently current D12 Chair mandate, department/term binding and recheck. An administrator is not implicitly Chair. |
| Schedule application/publication | Independent D13 application mandate and immutable source/revision binding. Not granted by optimization or quarantine. |
| Optimization ownership/control | J scoped actor/department/action evidence plus I/K/L run owner, configuration, bundle and fence. |
| Recovery quarantine | New independent recovery mandate tied to actor, department, run, action, request, package identity, target store and epoch. Existing optimization or Chair grants cannot substitute. |

Genuine MSU-IIT identity feeds, current IT/IS appointments, department membership, recovery operators and institutional grant issuers were not supplied or verified. `ga_trusted_runs.configured_service()`, `institutional_chair_directory()` and `institutional_application_directory()` remain unavailable. J's existing synthetic directory/verifier is reused only in tests. No institutional identity or approval is fabricated; IT prototype scope does not imply full CCS coverage.

### New recovery contract

`backend/services/ga_recovery_qualification.py` defines frozen `RecoveryContext` and `RecoveryMandate` values and an internal `RecoveryAuthority`. These are server dependency contracts, not client DTOs. The distinct capability is `checkpoint_quarantine_recovery`; actions are restore/inspect quarantine. A current, uniquely scoped record and independently verified source attestation are mandatory. Directory/verifier guards stay held through the operation; expiry is checked again before vault commit. A provider outage, expired/revoked/unverified grant, changed department/run, or wrong capability fails closed.

Successful audit provenance includes actor, explicit recovery role, requested action, department/run, time, mandate record/revision, source/evidence/context digests. Denials with a validated context record requested actor/scope/action, decision and time without pretending authority was established. Malformed packages/identities reject before they have enough trusted context for a scoped durable event. Bounded audit capacity fails closed; failure to write a secondary audit does not replace the primary error and is identified by a separate safe note. No passwords, cookies or token values belong in these records.

## Storage and writable quarantine

`backend/services/ga_recovery_vault.py` adds a separate, fictional-only `PrivateRoot`, `RootApproval`, `Anchor`, `Package` and `Vault`. No normal application import configures or registers them.

Only I's newly created ACL-private OS-temp stores can be provisioned. The developer checkout is not an approved deployment root. Approval is a trusted provisioning registry value binding the exact store identity and root/marker/database device/inode identities; it is not inferred afresh from whatever files happen to exist at restart. Reopening requires the previously retained approval. J's actual private-DACL inspection and I's owner-marker checks remain active. Root, marker, database, junction/symlink or identity mismatches reject. Tests include real junction detection and simulated identity/permission substitution. These are trusted-local-process protections, not a claim to resist a malicious administrator racing SQLite pathname opens. No approved institutional service-account ownership policy was established.

Vault and anchor must have different store identities. Package contents include the exact immutable bundle and the complete supplied checkpoint chain, bound to run, owner and department. Validation calls the unchanged H `InputBundle.from_bytes` and `Session.restore` for every sequence with its exact parent/tip. This preserves source engine, optimizer, configuration, scoring context, graph, resource validation and RNG codec checks. Metadata labels or checksums alone never establish approval. No payload is added to chromosome genes, rescored, rounded or repaired.

The independently supplied anchor pins validated package facts and a monotonically increasing epoch. Advancing a pin requires unchanged run/owner/department/bundle/configuration/optimizer and a strictly advancing checkpoint sequence extending the old tip. A backup manifest cannot self-authorize freshness. The fixture anchor is a **separate logical SQLite store on the same host**, not an independent failure domain, external institutional ledger or hardware anti-rollback device. Production freshness remains unqualified.

### Atomicity, replay and interruption

The authority guard and an immediate anchor transaction cover reservation and vault insertion. The vault stores bounded package bytes and its prepared audit in one FULL-synchronous SQLite transaction. It rejects duplicate request IDs, existing-run collisions and per-package/global payload quota exhaustion. Checkpoint bytes are retained in the new quarantine only; no original store or run is overwritten, relocated, deleted, migrated or activated.

After vault commit, the independent anchor consumes the exact request/target/epoch. These are two databases: **there is no claimed distributed atomic commit**. An interruption before vault commit rolls back the new payload. An interruption after vault commit but before anchor completion leaves an inert retained quarantine and an INDETERMINATE audit; inspection rejects it and subsequent collision/replay attempts fail. Automatic reconciliation, deletion or retry is intentionally absent. This preserves evidence rather than inventing a successful recovery acknowledgment.

A successful inspection revalidates current recovery authority, consumed anchor, package hash and the original H checkpoint contract. It returns `VALIDATED_QUARANTINE`, `worker_resume_enabled=false` and `institutional_restore_enabled=false`. It never returns an executable worker or a publication permission. Tests independently read the private fixture package and compare original/restored continuation assignments, fitness/breakdown, history, faculty analysis and RNG. A fresh Python process reopens the retained vault with externally retained root approvals and a freshly constructed fictional recovery provider.

**Writable backup restoration into an active I-L worker remains BLOCKED.** Existing workers do not consult this new anchor, so merely cloning their database would permit old-owner/rollback hazards. A separately versioned activation contract must fence all original and restored owners and anchor every subsequent publication/checkpoint boundary before that portion can be implemented safely. The already qualified same-store L recovery is a different operation.

### Quotas and limits

New quarantine/anchor transactions apply a 32 MiB main SQLite page bound and minimum 64 MiB observed free space. Default payload limits are 8 MiB per package and 16 MiB total; package chain length and audit count are bounded. A real oversized SQLite zeroblob transaction rolls back without retaining its table or corrupting the existing quarantine. Quota negatives, disk-headroom injection, permission/identity changes, corrupted inputs and failed audits are separately testable. Payload/page bounds do not cover journal files, backup volumes, Python allocations or all filesystem overhead. Free-space checks do not reserve disk space. No NTFS quota, whole-volume policy, automatic retention deletion or approved institutional backup destination is claimed.

## Windows parent and worker qualification

The new `test_parent_containment_qualification.py` uses the unchanged L `Process` implementation to create an outer Job for a fictional supervisor and nested worker Jobs. The final seven native/diagnostic cases verify explicit snapshot imports, observed launcher topology, membership of the actual interpreter and nested worker, denied breakaway, parent allocation denial, parent CPU termination, owned-tree cleanup with an unrelated sentinel surviving, and real durable checkpoint recovery after forced parent-tree termination. A stale executor/fence cannot reclaim the recovered run. No process is killed using an unverified saved PID.

Early probes failed before qualified execution: the base interpreter in isolated mode could not import the snapshot tests. Explicit owned-snapshot/package paths resolve that import boundary. Using the Windows venv redirector then reproduced `CreateProcessW` failure at L source line 111, error **1816**; the actual GA parent also encountered denied ACL-helper execution. Launching the real interpreter with the same existing venv dependencies and owned snapshot succeeded without raising resource quotas or changing L code. Python documents Windows venv [redirector executables](https://docs.python.org/3/library/venv.html). The measured creation PID differs from the interpreter PID with the redirector and matches in the direct profile. Sampled Job accounting reported three versus two active entries despite the configured two-process outer limit; it must not be treated as an exact, quiescent live-tree count. The precise internal accounting transition/limit responsible is not independently established.

Two attempted diagnostics incorrectly assumed exact wrapper counts and failed. They remain recorded. A later repetition also caught premature test acknowledgment: an empty Job-accounting observation preceded the nested worker's signaled termination. The final probe explicitly polls the exact PID plus creation-time identity within the existing five-second cleanup bound. This is supported by [Windows nested-job termination semantics](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs) and [TerminateJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-terminatejobobject), which terminates the associated hierarchy. No timeout was increased and no enforcement assertion was suppressed; immediate accounting was replaced by actual descendant-exit verification.

Per-process private commitment and user-CPU thresholds cover the tested parent and child, not aggregate host RAM or total run CPU. The 64 MiB parent allocation probe rejects 256 MiB. User-CPU termination is periodic and may overshoot; exact observations are retained in the final `U5N-parent-cpu.json`, alongside the separate unchanged L native results. No RSS, CPU-rate or aggregate Job-memory limit is added. Native Win32 tests coexist with injected faults; no compiler or native dependency was installed.

**No parent-wide production service mode is installed or enabled.** The web server, multiple concurrent department runs, extra helper processes, source providers, new vault plus optimizer together, cross-session owners and arbitrary deployment topologies are not covered by these bounded probes. A production supervisor must own the launcher and descendant-exit acknowledgments, explicitly budget helper processes and fence recovery. Automatic reattachment and deployment-wide resource guarantees remain unavailable.

## Failed attempts and privacy remediation

Eight unsuccessful invocations are preserved: seven parent diagnostic/qualification attempts and one preference-scope attempt. Parent records retain import failures, Win32 failure codes, incorrect wrapper-count assumptions and the asynchronous-exit assertion failure. They are not counted as final passing cases.

The preference test initially used `/api/preferences` instead of the existing `/preferences` route. Its three failures were a harness routing error, not an ownership bypass. Pytest call introspection exposed fictional CSRF values in that new failure record. **Entire token values were removed**, without retaining prefixes, suffixes or replayable fragments; the original and sanitized SHA-256 values and reason are recorded in [privacy-redaction.json](testing/dashboard-u5n/privacy-redaction.json). Failure outcomes, timestamps and traceback meaning remain intact, and no raw original token-bearing copy was retained. No pre-existing historical evidence was rewritten. The new runner sanitizes credential/header fields before recording, and the corrected tests use response variables to avoid secret-bearing bound-call introspection. The final three preference handler cases pass.

## Fresh verification

| Selected Python suites | Passed |
|---|---:|
| New recovery authority/storage/quarantine | 40 |
| New parent topology/native recovery | 7 |
| New actual preference ownership handlers | 3 |
| U5M receipt race / identity; original U5D receipts | 19 / 16 / 36 |
| U5L supervised / native plus configuration | 41 / 12 |
| U5K bounded worker | 32 |
| U5H consumption / original nonzero parity / legacy continuation | 39 / 5 / 10 |
| U5G bundles | 32 |
| U5I admission / U5J qualification | 50 / 49 |
| U5A-C compatibility/source/context | 99 |
| U5E analysis / U5F readiness | 20 / 20 |
| D12 review / Chair trust / D13 application trust | 34 / 6 / 5 |
| **Final selected Python cases** | **575** |

Earlier successful 35- and 37-case recovery runs are retained but not double-counted. These are selected cases across isolated executions, not 575 institutional end-to-end journeys. Existing TestClient/httpx and AnyIO deprecation warnings remain; no dependency was installed to remove them.

**210 frontend contracts, TypeScript, production build and focused ESLint pass.** Vite's existing bundle-size/dynamic-import advisories remain. **16 actual Edge/React scenarios pass**, with 17 Node runner entries including the parent suite. Six screenshots were visually/privacy reviewed. These are intercepted fictional HTTP responses, not browser-to-live-U5N worker acceptance. Committed frontend source is tested; unrelated working-tree UI modifications are excluded. Existing U5D regression additionally exercises a limited real loopback Uvicorn read with a fictional overridden principal. New identity/preference cases use actual FastAPI handlers with TestClient and disposable SQLite; they are not network browser tests.

The unchanged original/worker **455.0 nonzero fitness** assertions pass, including schedule assignments, breakdown, history and RNG continuation. No original operator, scoring equation, workload target, configuration file, RNG operation, checkpoint policy or scheduling semantics changed. H continues enforcing strict source/input fingerprints. U5D receipts remain UNVERIFIED and ineligible for CURRENT. No Saved Best promotion occurs.

## Prototype and production readiness

The [separate readiness assessment](testing/dashboard-u5n/readiness-assessment.json) distinguishes a fictional research demonstration from institutional deployment:

- **Research prototype:** existing fixed UI, read-only analysis, fictional conflict/ownership checks, internal bounded worker best-so-far tracking and controlled authority/recovery exercises are demonstrable. Production deployment is not a prerequisite for this fictional component demonstration. Prior D16 end-to-end acceptance is historical; a new complete D16 browser journey was not rerun here.
- **Continuous dashboard demonstration:** incomplete. Internal worker functionality is not wired into executable continuous HTTP/UI controls, and U5N does not activate it. Best, satisfaction and workload analysis are existing read-only capabilities, not institutional schedule approval.
- **Thesis validation:** formal adviser-approved manuscript alignment, approved evaluation cohort/policies, authentic comparison IT schedule and sanctioned institutional resource data remain to be supplied/qualified. Test timing is qualification runtime, not a fresh performance/convergence benchmark or a thesis-quality result.
- **Production:** blocked by genuine actor/department/Chair/recovery authority, authoritative academic capture, approved service identity/root, cross-session ownership, parent/host resource and storage budgets, independently durable freshness/fencing, restore reconciliation and separately approved retention disposal. No institutional restoration or optimization may be enabled from these fictional results.

## Reproduction and checkpoint preparation

Use existing dependencies from the repository root in Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5n/checkpoint_snapshot.py recovery
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5n/checkpoint_snapshot.py parent
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5n/checkpoint_snapshot.py preference-scope
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5n/checkpoint_snapshot.py race
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5n/checkpoint_snapshot.py supervised
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5n/checkpoint_snapshot.py parity
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5n/checkpoint_snapshot.py legacy
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5n/frontend_snapshot.py
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u5n/audit_evidence.py
```

Other recorded backend selections are named in the manifest. Each invocation creates a new evidence directory; it never overwrites the earlier run. Re-running after sealing requires a separate manifest review. Backend snapshots exclude academic/runtime inputs, use the established fictional bootstrap/release-byte recipe, restore committed current main before tests and copy only the five new implementation/test files. No original engine hash is spoofed. Historical generic snapshot consumption fields denote prerequisite capability, not proof that every selection invokes an optimizer; suite-specific evidence above controls the claim.

The [manifest](testing/dashboard-u5n/manifest.json) contains the exact new-file inventory and artifact hashes, excluding its own hash. The [audit](testing/dashboard-u5n/audit_evidence.py) verifies all 4,271 preserved baseline paths, 644 prior G-M artifact hash references, final tested source identities, unsuccessful records, redaction metadata, privacy/whitespace patterns, six PNG CRC/metadata/visual checks and Git integrity. No raw checkpoint, input package, SQLite database, backup image, institutional record, session token or worker wire payload is archived.

The [selective staging plan](testing/dashboard-u5n/staging-plan.json) proposes the two new qualification modules and three new test files, then documentation/tooling/evidence. All U5N files are new; no mixed tracked file needs partial staging. Explicitly exclude the eleven existing modifications and 958 unrelated untracked files. A later authorized checkpoint must reverify HEAD/live remote/index, exact NUL-delimited literal paths, raw Git blob identities, hashes and CRLF-aware whitespace with `core.autocrlf=false`. Nothing has been staged, committed, pushed or deployed.

## U5O recommendation

First qualify an approved service identity/root and an independently managed freshness/authority provider. Specify a versioned activation/reconciliation protocol that fences both original and restored workers, including crash-after-vault-commit recovery, durable root approvals and all checkpoint/publication boundaries. Then qualify a real supervised service topology with helper budgets, cross-session ownership and host/volume/journal/backup quotas. Separately consider an explicitly fictional-only HTTP/UI demonstration bridge without changing genuine institutional defaults. Do not enable active backup restoration, retention deletion or continuous execution merely because quarantine tests pass. No U5O implementation is included.
