# Dashboard D8: institutional verification policy and evidence trust

Implemented and verified **2026-10-23, Asia/Manila**, from main `015b026a0ed9d2a889193fafc4f4a0ce175c843d`, with the pre-existing protected preference modification retained. **D8 IMPLEMENTED; SCOPED CHECKS PASS. Production remains BLOCKED without an authorized institutional policy and trusted provider.** No actual MSU-IIT issuer, approval, document signature, permanent verification record or GA constraint is established by this work.

## Objective, inspection and implementation sequence

Reuse D3 intake and source provenance, D4 resource projection/calendar, D5 complete fresh handoff, D6 legacy originals and D7 completion/session receipts. Inspection covered those services/contracts, router guards, authentication/session ownership, reference fingerprints, D7 provider hooks/tests/evidence, README, roadmap, bug report and the [documentation standard](DEVELOPMENT_DOCUMENTATION_STANDARD.md). See historical [D3](dashboard-d3-implementation.md), [D4](dashboard-d4-implementation.md), [D5](dashboard-d5-implementation.md), [D6](dashboard-d6-implementation.md) and [D7](dashboard-d7-implementation.md); their evidence was not rewritten.

The minimum plan was: extend the existing provider hook with strict evidence and a separately trusted policy lookup; evaluate explicit scope/freshness/coverage inside D7; show public findings in the existing assessment and print document; introduce pre-write evidence sanitization; run fresh D8 and compatibility checks with isolated fictional data. No parallel scheduler, route, calendar, registry UI or PDF dependency was needed.

## Exact application and test inventory

| Path | Change |
|---|---|
| `backend/schemas/external_evidence.py` | New strict versioned policy/provider/public outcome contracts. |
| `backend/services/external_schedule_verification_service.py` | Extend D7 hook; add default-unavailable trusted policy lookup and conservative scope/lifecycle evaluation. |
| `backend/services/external_schedule_readiness_service.py` | Bind D8 to original/candidate/current preview; include findings and cap displayed validity; reject credential-like completion text. |
| `backend/schemas/external_readiness.py` | Add optional `evidence_trust` response field. |
| `backend/services/evidence_sanitization.py` | New whole-line/header, encoded-fragment, key and credential-URI evidence sanitizer. |
| `backend/tests/dashboard/evidence_support.py` | New explicitly fictional provider/policy injection for tests only. |
| `backend/tests/dashboard/test_external_evidence.py` | New 73 policy, API, preservation and privacy cases. |
| `backend/tests/dashboard/test_external_evidence_live.py` | New owned Edge/FastAPI/SQLite smoke, reusing D2 and D7 isolation. |
| `backend/tests/dashboard/test_external_readiness.py` | Adapt only the fictional trusted helper to the extended provider contract. |
| `frontend/src/api/externalEvidence.ts` | New typed public trust DTO, row coverage and conservative VERIFIED checks. |
| `frontend/src/api/externalReadiness.ts` | Accept optional D8 findings; include them in complete content verification. |
| `frontend/src/components/schedule/ExternalEvidencePanel.tsx` | New shared read-only evidence panel. |
| `frontend/src/components/schedule/ExternalScheduleReadiness.tsx` | Show unassessed evidence claims in existing completion workspace. |
| `frontend/src/components/schedule/ReadinessDocument.tsx` | Include the same panel in assessed screen/print output. |
| `frontend/tests/externalEvidence.fixtures.mjs` | New fictional HTTP provider simulation, never real authorization evidence. |
| `frontend/tests/externalEvidence.test.mjs` | New 11 frontend contracts including privacy tests. |
| `frontend/tests/externalEvidence.browser.test.mjs` | New 18 synthetic-HTTP rendered Edge scenarios. |
| `frontend/tests/externalEvidence.live.mjs` | New five live Edge-to-FastAPI scenarios; private login configuration travels through stdin only. |
| `frontend/tests/evidencePrivacy.mjs` | New browser-result sanitization before evidence writes. |

Exactly **seven existing implementation/test files changed and twelve new files** were added above. Supporting files: this report; `docs/testing/dashboard-d8/run_checks.py`, `preservation-baseline.json`, `manifest.json` and timestamped command records; original PNGs and browser scenario JSON under `docs/screenshots/dashboard-d8/`. The [manifest](testing/dashboard-d8/manifest.json) gives every exact evidence path, hash and final command selection.

## Authority policy and role boundaries

`AuthorityPolicy` explicitly identifies issuer, issuing organizational identity, policy revision/provenance, active/suspended/revoked state, authorized evidence type/mechanism, organizations, academic years, terms, course identifiers, effective/expiration instants, bounded check age and authorized-revision permission. Scope lists are explicit, bounded, nonempty and cannot use wildcard inheritance. A higher-level organizational issuer gains no automatic authority over other colleges. Unknown issuers fail closed.

Supplying organization, authorized issuer, CCS receiving administrator and future confirming official remain different role categories. No Dean, Chair, registrar or named individual is hardcoded as an authority. `authority_policy_for` returns None in normal deployment. No user-entered name, environment switch, request flag, file or existing admin session populates this registry.

## Evidence trust model and provider contract

Document existence, claimed source, authenticated issuer, integrity, authority scope, exact schedule binding, freshness/revocation and later institutional confirmation are separate properties. A filename, title, email domain, handwritten name, ordinary PDF or matching byte hash cannot establish the latter properties by itself. D8 adds no evidence-document upload or signature-authentication feature.

D7's `verification_for(input_fingerprint)` boundary is extended with a keyword-only, detached `EvidenceContext`. `Verification` retains its original fields and adds strict `TrustedEvidence`. A legacy four-field response alone can no longer establish trust. The context contains content/preview digests and bounded academic scope, never the raw session receipt. Providers receive a deep copy so they cannot mutate the evaluator's expected row inventory.

The trusted result supplies public evidence/issuer/organization IDs, evidence/method type, explicit outcome, policy/evidence/source revisions, exact input/source/preview fingerprints, supplier/year/term, covered original row numbers, exact-source or authorized-revision coverage, issuance/check/expiry and independently established revocation status/time. The registry policy is obtained through a separate server-only hook. Strict validation is repeated even for constructed/copied provider objects; malformed objects and exceptions produce static safe findings, without logging exception details or returning raw payloads.

Supported outcomes: VERIFIED, UNVERIFIED, INVALID, EXPIRED, REVOKED, STALE, UNSUPPORTED and PROVIDER_UNAVAILABLE. Conflicting evidence, invalid signatures and unsupported signatures reported by a provider fail closed. The only supported mechanism is a trusted provider attestation. No proprietary cryptography, external network connector, public-key registry, signing private key, certificate or claim of locally verified digital signatures is introduced. Both production hooks remain unavailable. Fictional provider implementations live only in tests.

## Binding, corrections and bounded row coverage

The D7 input digest continues to cover the full original D4 projection, detached completed projection, mappings, reference inventory and completion metadata. D8 additionally checks the current preview receipt's hash, original projection fingerprint, source revision, supplier and exact academic year/term. The original projection includes source-byte hash when uploaded, or complete original manual content when no file exists. Evidence must explicitly name covered original source rows; duplicate, unknown or missing row coverage cannot grant whole-batch verification.

Material subject/title/section/day/time/room/instructor changes and changed resolved resource identities require `authorized_revision` evidence and explicit policy permission. Original values remain untouched. Exact-source evidence is acceptable only without material corrections. Provider evidence is bound to the completed candidate, so evidence for an original file cannot silently cover a later edit. Individual covered rows can remain VERIFIED in a partially covered batch, while uncovered rows stay UNVERIFIED and aggregate readiness stays BLOCKED. Rejected/partial decisions minimize provider detail in the public response; full public issuer/policy summaries are returned for a successful bounded decision.

Policy content digest, policy/evidence revisions, outcome and row findings are included in D7's assessment content fingerprint. Policy, source, metadata, references, evidence, revocation or mapping changes cannot reuse an old assessed handoff.

## Freshness and revocation

Timezone-aware instants are required. Issuance/current review outside authority validity is rejected; expiry, suspension, revoked evidence, future/stale checks and mismatched policy revision block trust. A good revocation status must come from the trusted provider, be recent and not predate issuance. Unknown status is explicitly unverified, never presumed good. Policy check age is bounded to 30–900 seconds. The public validity window is the minimum of evidence expiry, policy expiry, verification freshness and revocation freshness; the readiness display also expires no later than its existing session/preview lifetime.

Every assessed handoff recomputes policy/provider findings and compares the current content fingerprint to the session-bound receipt. This is a point-in-time review, not a durable authority assertion. A future real provider must supply stable, consistently versioned snapshots and trustworthy revocation information; asynchronous external changes cannot be converted into permanent approval by this prototype.

## Backend security and API compatibility

No new public endpoint was necessary. Existing administrator-only POST `/api/external-schedules/readiness` returns optional versioned `evidence_trust`; assessed POST `/handoff` carries the same findings after fresh server verification. Existing preview/review/invalidation paths retain their role/session ownership and exact Origin/CSRF checks. Payload limits, strict rejection of client authority flags, safe 401/403/409/413/415/422 behavior, reference unavailability and session/revision locks are reused. No client path, arbitrary filesystem read, provider-credential response or policy-write API is added.

D3 canonical CSV/XLSX, D4 calendar/reconciliation, D5 source-only review and printing, D6 four-column originals and D7 completion remain available. Old source-only handoffs remain explicitly **not assessed**; they cannot claim evidence verification or readiness. D7 metadata/handoff request bodies are unchanged. The optional response extension keeps older synthetic DTO fixtures readable. D7's old fictional READY helper was upgraded to independently injected fictional evidence and policy; a legacy incomplete provider result intentionally fails closed.

## Frontend and printing workflow

The existing teal/gold `/admin/external-schedules` page now displays claims before assessment and a server-derived evidence panel after **Check readiness**. Trust evaluation and readiness occur together rather than allowing independently cached client trust. The panel distinguishes administrator claims, verified issuer, evidence identity/type/method, explicit scope, fingerprint/term match, coverage mode, check/validity times, revocation uncertainty, per-row outcomes and actionable blockers.

The mandatory label is **EVIDENCE VERIFICATION REVIEW — NOT INSTITUTIONALLY CONFIRMED OR ACTIVE IN GA**. There is no self-certification checkbox. Edits remove old assessment/output using D7 invalidation; the existing candidate calendar and D5 fresh handoff/print component are reused. React renders imported text as text, and the DTO rejects arbitrary provider fields, missing row coverage and inconsistent VERIFIED data. Raw receipts and credentials are not rendered. Native printing, physical printers, PDF pagination, maximum-row printing and non-Edge browsers remain NOT RUN.

## Fresh validation and evidence

Run selections from repository root with `.\.venv\Scripts\python.exe -B docs/testing/dashboard-d8/run_checks.py <selection>`. Every command record contains its exact child command, cwd, start/end timestamps with +08:00, elapsed time, exit status and sanitized output. The runner whitelists OS variables, omits all database URLs/approval/credential variables, disables pytest cache/bytecode, uses fresh owned temporary roots and unique evidence paths. Build/lint and every regression below ran during D8; historical D7 results were not substituted.

| Selection | Final result |
|---|---|
| backend | **301 passed**, zero failed/skipped, 2 warnings: 73 D8 + 228 D2–D7 cases. |
| backend-regressions | **46 passed**, zero failed/skipped, 4 warnings; actual auth/GA-control regressions, including isolated auth browser fixture. |
| ga-resource-regressions | **3 passed**, zero failed/skipped: existing synthetic reset/rollback/resource cases; no production generations. |
| contracts | **143 passed**, zero failed/skipped: 11 D8 + 132 existing. |
| browser | **18 D8 synthetic-HTTP Edge scenarios passed**, plus one Node parent. |
| d1/d2/d3/d4/d5/d6/d7/ga-browser | **16 / 13 / 15 / 15 / 15 / 15 / 18 / 51 scenarios passed**: 158 distinct scenarios plus eight Node parents. |
| live | **5 live browser-to-FastAPI scenarios passed**, one Node parent and one pytest wrapper, 2 warnings. |
| build | **PASS**, 227 modules; JS 904.50 kB / gzip 252.89 kB. |
| lint | **PASS**, eleven focused TypeScript/TSX files. |

Backend API tests use real FastAPI password/session/role/Origin/CSRF with fictional metadata and isolated SQLite. They cover trust scope/lifecycle, malformed provider output, correction and partial coverage, invalid client fields, fresh handoff denial after policy change, original rows/storage/RNG preservation and realistic pre-write privacy redaction. Existing D7 tests retain cross-session/wrong-admin, faculty/anonymous, request size, receipt replay, reference changes and invalidation-race checks. SQLite fixture session writes are synthetic authentication setup, never permanent academic confirmation writes.

Synthetic browser tests render actual React/Edge but mock HTTP policy responses. Their fictional VERIFIED/READY examples do not test backend authority. The separate live smoke uses React → Uvicorn/FastAPI → isolated SQLite with real login, cookies, Origin and CSRF, a test-only exact ephemeral-origin CORS wrapper and default unavailable authority. It verifies intake, BLOCKED evidence, handoff and edit invalidation. Credentials travel only through private child stdin; no network header/body traces are archived. Owned browsers/servers/profiles are stopped after each run.

Edge 155.0.4283.62; Node v24.11.1; Python 3.14.2. Actual per-run URL, browser/user-agent, viewport, capture timestamps and expected/observed scenario results are in each browser-results JSON and the manifest. Desktop 1600×1200; mobile viewport 390×844. Final [unavailable provider](screenshots/dashboard-d8/20261023T003852681542+0800-browser/D8-B02-provider-unavailable.png), [fictional provider only](screenshots/dashboard-d8/20261023T003852681542+0800-browser/D8-B11-fictional-provider-only.png), [mobile literal text](screenshots/dashboard-d8/20261023T003852681542+0800-browser/D8-B17-mobile-evidence.png) and [live BLOCKED](screenshots/dashboard-d8/20261023T003852253448+0800-live/D8-L03-live-fastapi-blocked.png) are genuine unedited captures. Synthetic 2099 expiries, fixed timestamps and repeated-letter hashes are fixture values, not actual provider lifetimes or observation times.

Existing Starlette/httpx and AnyIO deprecations remain; auth regressions also report two Alembic `path_separator` deprecations during **offline SQL rendering**, not a PostgreSQL connection/migration. Vite warns about the existing large bundle and static/dynamic readiness imports. Full-project lint, full backend/GA suite, production GA evolution, performance and usability studies were NOT RUN. **All 17 PostgreSQL acceptance tests remain paused/unverified.**

## Retained failures and corrections

Initial sandbox runs timed out during Edge protocol initialization before D8 scenarios ran: D8 browser parent failed, live pytest/Node parent failed; auth regressions had 45 passes and one browser-initialization failure. Authorized execution outside the sandbox used only owned loopback services and fresh profiles; final auth, D8 browser and live runs passed. No production auth setting was weakened.

The first executable D8 browser run passed 15 scenarios and failed three, plus failed parent. The legacy selector incorrectly expected an aria-label instead of the existing wrapping label; that failure left the next mobile step without loaded fields. The faculty test incorrectly expected a redirect rather than the existing Access unavailable screen. Only new D8 test expectations/selectors changed; final 18 pass. The earlier command, two original screenshots and scenario JSON remain archived.

The first D7 regression requested a D8 screenshot destination; its unchanged path guard rejected four captures and the final sidecar write failed (14 scenario passes, four scenario failures and failed parent). The D8 runner now runs unchanged D7 assertions without requesting D7 captures; all 18 pass. D8 captures are separate. Intermediate backend passes 287/293/296 preceded additional defense tests; final 301 pass. No earlier attempt was deleted or relabeled PASS, and the historical bug report was not rewritten.

## Privacy and evidence integrity

Python and browser evidence sanitizers act **before** command/scenario writes. Entire sensitive assignment/header lines are replaced, including escaped pytest reprs, so truncated receipt prefixes/signatures cannot survive a complete-token-only regex. Additional filters cover unlabelled encoded/signed fragments, bearer values, private-key blocks, credential-bearing URIs, cookies, CSRF/session/password/client-secret/API-key fields and nested objects. Tests use only deliberately fictional secret-like strings. Runner summaries are sanitized too, and raw provider exceptions/responses are never logged.

All D8 command/browser JSON, report text and PNG metadata were checked for remaining credential/receipt patterns and private faculty names. Every original capture was reviewed visually, with byte-identical duplicates verified against reviewed representatives; PNGs have no text/EXIF metadata. Only fictional data/reserved email domains appear. Failed diagnostics retain outcomes/timestamps without secret values. Hashes refer to the sanitized working-file bytes; originals containing confidential values are never copied into the evidence archive. Hashes identify artifacts, not independent proof of correctness. Pattern matching cannot prove the absence of every imaginable unknown secret, so bounded public DTOs, synthetic-only testing and visual review remain necessary defenses.

## Preservation and institutional dependencies

Baseline covers **728 files: 721 unchanged, exactly seven intended existing changes** listed above. Protected `backend/data/faculty_preferences.json` retains its pre-existing byte contents; every other academic dataset, faculty UUID/code binding, section/room identity, GA operator/fitness/penalty/RNG, checkpoint/chromosome format, fixed-section input, saved schedule/history, Phase 4C foundation and historical evidence remains unchanged. HEAD and Git index are unchanged. Nothing staged, committed or pushed. No PostgreSQL connection, migration or permanent table was introduced.

Real institutional inputs are still required: approved issuer roles and organizational identities, documentary policy provenance, exact organizational/course/term authority, supported verification mechanism and credential management, independently authenticated evidence delivery, consistent revision binding and trusted current revocation checks. No actual official, office, key or document was supplied. Therefore the production registry/provider remain absent and assessments remain BLOCKED. Rejected/partial results deliberately reveal minimal provider detail; richer rejected-evidence diagnostics would need a separate public-data contract. Multiple external evidence documents are not aggregated locally; the provider must resolve conflicts into one explicitly bounded finding.

## Safe reproduction, thesis claims and D9 boundary

Use the D8 runner with its fresh owned fixtures, without setting database URLs. The live/browser selections may require permission to launch owned loopback listeners and Edge outside the sandbox. In an independently isolated administrator fixture, import a fictional canonical or legacy source, reconcile, complete metadata, press Check readiness, inspect actionable evidence blockers, open the unchanged candidate calendar, prepare a complete handoff and revalidate before print. Editing metadata removes old trust. Anonymous access redirects to login; faculty access shows denial. Refresh discards temporary completion. VERIFIED/READY requires explicit test injection; no production enablement procedure is supplied.

Thesis evidence supports conservative server-side verification policy evaluation, source/candidate/row binding, explainable trust findings, safe preview/handoff, negative authorization and bounded privacy protection under synthetic storage. It does not support real MSU-IIT authority validation, institutional confirmation, production readiness, GA-quality improvement, performance improvement or a usability conclusion.

Recommended **D9 planning boundary**: obtain and review actual institutional issuer/evidence/revocation policy and authoritative calendar/resource contracts, then design a separately approved provider integration and durable provenance/confirmation acceptance gate. Database provisioning/acceptance requires separate authorization. Immutable external GA constraint compilation, activation, Chair approval and faculty change requests remain later work. No D9 work, permanent confirmation, publishing or GA activation occurred.
