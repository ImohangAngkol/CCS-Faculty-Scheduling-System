"""Bounded diagnostic transport, independent of GA and checkpoint state.

Legacy GA modules resolve `print` through a scoped facade. Neither sys.stdout
nor builtins.print is replaced; other modules/threads keep their normal output.
This adapter leaves fingerprinted engine source and existing checkpoints intact.
"""
import builtins
import io
import json
import sys
import threading
from collections import OrderedDict, deque
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from uuid import uuid4

MAX_RUNS = 16
MAX_LINES = 1000
MAX_BYTES = 512 * 1024
MAX_LINE_BYTES = 4096
MAX_RESPONSE_BYTES = 64 * 1024
MAX_RESPONSE_LINES = 200
_writer = ContextVar("ga_diagnostic_writer", default=None)
_binding_lock = threading.Lock()


class RunLogBuffer:
    def __init__(self, history_unavailable=False):
        self.lock = threading.Lock()
        self.epoch = str(uuid4())  # OS entropy, never GA random.
        self.entries = deque()
        self.sequence = self.byte_count = 0
        self.history_unavailable = history_unavailable

    def append(self, message, shortened=False):
        encoded = message.encode("utf-8", errors="replace")
        oversized = len(encoded) > MAX_LINE_BYTES
        shortened = shortened or oversized
        if oversized:
            message = encoded[:MAX_LINE_BYTES - 32].decode("utf-8", errors="ignore") + " [line truncated]"
        size = len(message.encode("utf-8", errors="replace"))
        with self.lock:
            self.sequence += 1
            entry = {"sequence": self.sequence, "timestamp": datetime.now(timezone.utc).isoformat(),
                     "message": message, "line_truncated": shortened}
            self.entries.append((entry, size))
            self.byte_count += size
            while len(self.entries) > MAX_LINES or self.byte_count > MAX_BYTES:
                _, removed = self.entries.popleft()
                self.byte_count -= removed
            return dict(entry)

    def read(self, after_sequence):
        with self.lock:
            oldest = self.entries[0][0]["sequence"] if self.entries else self.sequence + 1
            reset = after_sequence > self.sequence
            cursor = 0 if reset else after_sequence
            entries, size = [], 0
            for entry, _ in self.entries:
                if entry["sequence"] <= cursor:
                    continue
                # Include JSON escaping/metadata in the response budget.
                encoded_size = len(json.dumps(entry, ensure_ascii=True).encode())
                if len(entries) >= MAX_RESPONSE_LINES or size + encoded_size > MAX_RESPONSE_BYTES:
                    break
                entries.append(dict(entry))
                size += encoded_size
            next_sequence = entries[-1]["sequence"] if entries else cursor
            return {"log_epoch": self.epoch, "entries": entries, "latest_sequence": self.sequence,
                    "next_sequence": next_sequence, "has_more": next_sequence < self.sequence,
                    "earlier_logs_truncated": self.history_unavailable or cursor < oldest - 1 or reset,
                    "cursor_reset": reset}


class RunLogStore:
    """Global retention is bounded too; executing runs cannot be evicted."""
    def __init__(self):
        self.lock = threading.Lock()
        self.buffers = OrderedDict()
        self.pinned = set()

    def buffer(self, run_id, history_unavailable=False, pin=False):
        with self.lock:
            if run_id not in self.buffers:
                while len(self.buffers) >= MAX_RUNS:
                    evict = next((key for key in self.buffers if key not in self.pinned), None)
                    if evict is None:
                        raise RuntimeError("Log retention capacity exceeded by simultaneous workers.")
                    del self.buffers[evict]
                self.buffers[run_id] = RunLogBuffer(history_unavailable)
            self.buffers.move_to_end(run_id)
            if pin:
                self.pinned.add(run_id)
            return self.buffers[run_id]

    def unpin(self, run_id):
        with self.lock:
            self.pinned.discard(run_id)


def store_for(registry):
    with registry.lock:
        if not hasattr(registry, "log_store"):
            registry.log_store = RunLogStore()
        return registry.log_store


def _write_console(stream, text):
    """Keep UTF-8/Unicode destinations intact; escape legacy console glyphs.

    Never reconfigure or replace process-wide streams. Preflight a declared
    encoding so a legacy write does not emit a partial prefix before failing.
    Only encoding errors get a fallback; real I/O and validation errors escape.
    """
    encoding = getattr(stream, "encoding", None)
    if encoding and not text.isascii():
        try:
            text.encode(encoding)
        except UnicodeEncodeError:
            text = text.encode(encoding, errors="backslashreplace").decode(encoding)
    try:
        stream.write(text)
    except UnicodeEncodeError:
        # Some wrappers omit/misreport encoding. ASCII escapes work even there.
        stream.write(text.encode("ascii", errors="backslashreplace").decode("ascii"))


def console_print(*args, **kwargs):
    """Encoding-safe diagnostic output, without adding a run log entry."""
    destination = kwargs.get("file")
    if destination is None:
        destination = sys.stdout
    rendered = io.StringIO()
    # Let print validate sep/end/keywords and format each object exactly once.
    builtins.print(*args, **{**kwargs, "file": rendered})
    if destination is not None:
        _write_console(destination, rendered.getvalue())
        if kwargs.get("flush"):
            destination.flush()


def diagnostic_print(*args, **kwargs):
    writer = _writer.get()
    destination = kwargs.get("file")
    if writer is None or (destination is not None and destination is not sys.stdout):
        return console_print(*args, **kwargs)
    # Formatting occurs once, preserving print semantics and object side effects.
    return builtins.print(*args, **{**kwargs, "file": writer})


def bind_diagnostics():
    with _binding_lock:
        for name, module in list(sys.modules.items()):
            if module is not None and (name in {"services.ga_service", "services.chromosome_service"}
                                       or name.startswith("genetic_algorithm.")):
                module.__dict__.setdefault("print", diagnostic_print)


class DiagnosticWriter(io.TextIOBase):
    def __init__(self, buffer, sink=None):
        self.buffer = buffer
        self.sink = sink
        self.stdout = sys.stdout
        self.pending = ""
        self.shortened = False

    def write(self, text):
        _write_console(self.stdout, text)
        # Partial lines are bounded as well; keep parsing newline boundaries.
        parts = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        for index, part in enumerate(parts):
            available = MAX_LINE_BYTES - len(self.pending)
            self.pending += part[:max(0, available)]
            self.shortened = self.shortened or len(part) > available
            if index < len(parts) - 1:
                self.emit()
        return len(text)

    def emit(self):
        message = self.pending + (" [line truncated]" if self.shortened else "")
        entry = self.buffer.append(message, self.shortened)
        self.pending, self.shortened = "", False
        if self.sink:
            self.sink({**entry, "log_sequence": entry["sequence"], "log_epoch": self.buffer.epoch})

    def flush(self):
        self.stdout.flush()

    def finish(self):
        if self.pending or self.shortened:
            self.emit()
        self.flush()


@contextmanager
def capture_run_logs(registry, control, sink=None):
    bind_diagnostics()
    store = store_for(registry)
    buffer = store.buffer(control.run_id, history_unavailable=control.state != "CREATED", pin=True)
    writer = DiagnosticWriter(buffer, sink)
    token = _writer.set(writer)
    try:
        yield diagnostic_print
    finally:
        try:
            writer.finish()
        finally:
            _writer.reset(token)
            store.unpin(control.run_id)
