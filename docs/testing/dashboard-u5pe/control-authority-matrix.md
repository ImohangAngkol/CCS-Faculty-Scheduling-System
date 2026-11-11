# U5P-E pre-implementation control authority matrix

Resumed 2026-11-11, Asia/Manila. Only the original entry/baseline files existed at resume. All 5,410 captured paths match, including 302 ignored files, all 23 academic paths and the eight U5PD artifacts. The original baseline also includes seven pre-existing build files; these are preserved as additional coverage, not dropped. Dependencies/Git object storage are explicitly excluded; index/HEAD/config are separately hashed. No U5PD exception is applied.

| Operation | Trusted authority / existing mechanism | Exposure decision |
|---|---|---|
| Admit and Start | Actual session, Origin/CSRF, ResearchPermit actor/department/catalog/prepared bundle, J mandate/source, I idempotent admission, K exclusive lease/fence, L Windows process identity/job | New isolated opt-in factory only, server-owned bounded Limits, UUID-only request |
| Duplicate Start | Same request bound to original run; original SQLite idempotency and worker fence | Return current verified observation, never launch another supervisor for a completed request |
| Stop | Same principal/run ownership, current scoped stop grant, cooperative original worker command | Request accepted is not termination. STOPPED only via v2 durable terminal + exit verification |
| Observe | Existing four SELECT-only routes and U5PD freshness adapter | Reuse unchanged; control routes have a separate prefix |
| Shutdown | Original supervised worker shutdown, bounded grace and owned Job identity | Host responsibility; no unrelated PID termination |
| Pause / Resume / Restore / Promote | No new approved authority or active-recovery contract | Absent |
| Institutional execution | Genuine scoped providers unavailable, fictional-source guard rejects checkout | BLOCKED; no main.py registration |

Admission/command audit records must be bounded and authenticated in the newly owned private store. Write failures must not acknowledge a completed operation; partial dispatch requires inspection, not automatic replay. An auth/CSRF rejection occurs before any authorized control action and has HTTP denial evidence, not a fabricated successful lifecycle event.

Existing Stop is cooperative at a batch boundary; active computation can continue until the batch completes or the unchanged wall/physical limit expires. The new interface must say Stop requested until actual terminal cleanup is verified. CPU/user-time enforcement remains per-child, with prior quota-overrun uncertainty retained; no host-wide safety claim, increased 600-second limit or seven-day run is authorized.
