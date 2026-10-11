# Phase 3E.2: Windows-safe GA diagnostics

## Verified failure

The local backend (process 40840) recorded run
`b8d7cb7b-60d1-43f0-b85b-b2fbf0187949` as FAILED during initialization,
with no completed generation or committed checkpoint. Its run log ends with
54 checked class periods, SECTION CONFLICT CHECK, then the reported
`'charmap' codec can't encode character '\u2713'` exception.

An isolated strict cp1252 stream reproduces the exact traceback:

1. `Functions.print_conflicts()` prints `✓ NO CONFLICTS FOUND` (line 3134).
2. The module's existing `diagnostic_print` facade routes it to
   `DiagnosticWriter.write()`.
3. That writer previously called `self.stdout.write(text)` before appending
   the original text to the run buffer.
4. Windows' cp1252 encoder rejects U+2713. The exception escapes to the GA
   worker's failure handler. No logging handler or scheduling rule raised it.

This is a diagnostic-output failure. It does **not** establish that the
interrupted candidate passed every publication/hard-constraint gate. The
failed run stays FAILED; this correction does not certify or resume it.

## Correction

`ga_log_service._write_console()` keeps Unicode intact for UTF-8 and other
compatible streams. For a stream with a declared legacy encoding, it checks
encodability before writing and uses `backslashreplace` for unsupported
characters. A wrapper that omits or misreports its encoding gets an ASCII
escape fallback on `UnicodeEncodeError`. Other exceptions still propagate.

The run writer mirrors through this helper, then processes the **original**
Unicode text through the existing bounded buffer and SSE sink. Sequence
numbers, timestamps, cursors, run identities, partial-line buffering and
retention limits are unchanged. The browser still receives real checkmarks.
Nothing replaces `sys.stdout`, `sys.stderr`, or `builtins.print`, changes a
global stream's encoding, or captures another request's diagnostics.

`console_print()` provides the same encoding-safe path when no run capture is
active, including historical/checkpoint validation and explicit diagnostic
destinations. It formats each object once and retains print argument checking,
separators, line endings and requested flushes. History warning mirrors use it
without adding duplicate run entries.
The scoped facade also covers chromosome-save diagnostics, whose file paths
can contain characters outside the terminal's encoding.

No environment variable is required for this correction. Strict cp1252
regressions explicitly supply incompatible streams even in a UTF-8 test host;
the fresh-interpreter resume test also explicitly uses strict cp1252 stdout.

## Compatibility and acceptance

Engine source, fitness equations, operators, eligibility, fixed schedules,
external assignments, workload rules and checkpoint format are unchanged.
The adapter is outside the engine fingerprint, preserving compatibility of
existing checkpoints. Tests compare seeded output, RNG state and fitness-call
counts and exercise validated history/checkpoint access independently.

Manual acceptance after loading the corrected backend:

1. Start a small run on Windows using the normal launcher, without setting
   `PYTHONUTF8` or `PYTHONIOENCODING`.
2. Verify section/faculty/room diagnostics complete. Unsupported terminal
   glyphs may appear as `\u2713` or `\u2717`; browser logs show the glyphs.
3. Pause at a validated boundary, refresh, verify the same UUID and checkpoint,
   resume, and check that new diagnostics continue in sequence.
4. Inspect saved generation snapshots and exports. No new validation bypass
   or automatic retry of a failed GA is introduced.

Limitations: legacy consoles may display escaped glyphs instead of symbols;
their encoding is deliberately left alone. Closed/broken streams and genuine
validation/storage failures are not suppressed. Existing log buffers remain
memory-bounded and unavailable after backend restart; restart recovery retains
the existing truncation notice. A backend without autoreload needs a restart
to load Python changes; never interrupt an active generation to do that.

## Verification results

| Verification | Result |
| --- | --- |
| Strict legacy/UTF-8 diagnostics, real conflict validation, Unicode save path, concurrent capture | 11 passed |
| Existing and expanded run-log tests, seeded equivalence, pause/refresh/resume, fresh-process cp1252 resume | 12 passed |
| Monitoring, cooperative stop and conflicting lifecycle regressions | 48 passed |
| Checkpoint/history recovery, concurrent inspection, integrity/compatibility failures, all-fitness-call equivalence | 13 passed |
| Frontend monitoring/recovery/log/history contracts | 39 passed |

Total: 84 distinct backend tests and 39 frontend tests passed. Changed Python
modules parse successfully and `git diff --check` passes. All 84 protected
engine/input/checkpoint/saved-artifact files match their pre-task SHA-256
hashes. No production GA was started or resumed, and no files were committed
or pushed. A fresh Windows process also verified the corrected diagnostic on
its default cp1252/surrogateescape stream without a UTF-8 environment override.
