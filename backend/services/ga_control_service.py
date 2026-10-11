"""Cooperative lifecycle control with durable boundary checkpoints."""
import json
import copy
import os
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


TERMINAL_STATES = {"STOPPED", "COMPLETED", "FAILED"}
TRANSITIONS = {
    "CREATED": {"INITIALIZING", "PAUSE_REQUESTED", "STOP_REQUESTED", "FAILED"},
    "INITIALIZING": {"RUNNING", "PAUSE_REQUESTED", "STOP_REQUESTED", "COMPLETED", "FAILED"},
    "RUNNING": {"PAUSE_REQUESTED", "STOP_REQUESTED", "COMPLETED", "FAILED"},
    "PAUSE_REQUESTED": {"PAUSING", "STOP_REQUESTED", "FAILED"},
    "PAUSING": {"PAUSED", "STOP_REQUESTED", "FAILED"},
    "PAUSED": {"RESUMING", "STOP_REQUESTED", "FAILED"},
    "RESUMING": {"RUNNING", "PAUSE_REQUESTED", "STOP_REQUESTED", "FAILED"},
    "STOP_REQUESTED": {"STOPPING", "FAILED"},
    "STOPPING": {"STOPPED", "FAILED"},
    "STOPPED": set(), "COMPLETED": set(), "FAILED": set(),
}
STOPPED_RUNS_DIR = Path(__file__).resolve().parents[1] / "saved_chromosomes" / "stopped_runs"


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class StopConflict(ValueError):
    pass


class RunControl:
    def __init__(self, process_instance_id=None, configuration=None):
        self.run_id = str(uuid4())
        self.process_instance_id = process_instance_id
        self.configuration = dict(configuration or {})
        self.latest_progress = None
        self.execution_active = True
        self.lock = threading.RLock()
        self.state = "CREATED"
        self.stop_requested = False
        self.pause_requested = False
        self.pause_requested_at = self.paused_at = self.resumed_at = None
        self.checkpoint = None
        self.progress_history = []
        self.durable = False
        self.elapsed_offset = 0
        self.finalizing = False
        self.created_at = timestamp()
        self.started_at = self.stopped_at = self.ended_at = None
        self.stop_requested_at = None
        self.stop_reason = None
        self.latest_completed_generation = None
        self.latest_validated_best = None
        self.result_reference = None
        self.terminal_error = None
        self.started_clock = time.monotonic()
        self.ended_clock = None
        self.on_state = None

    def snapshot(self):
        with self.lock:
            return {"run_id": self.run_id, "state": self.state, "status": self.state,
                    "process_instance_id": self.process_instance_id,
                    "configuration": dict(self.configuration),
                    "latest_progress": copy.deepcopy(self.latest_progress),
                    "progress_history": copy.deepcopy(self.progress_history),
                    "execution_active": self.execution_active,
                    "pause_requested": self.pause_requested, "checkpoint": self.checkpoint,
                    "pause_requested_at": self.pause_requested_at, "paused_at": self.paused_at,
                    "resumed_at": self.resumed_at,
                    "accepting_pause": self.state in {"CREATED", "INITIALIZING", "RUNNING"} and not self.finalizing,
                    "accepting_resume": self.state == "PAUSED" and not self.execution_active,
                    "stop_requested": self.stop_requested, "finalizing": self.finalizing,
                    "accepting_stop": self.state in {"CREATED", "INITIALIZING", "RUNNING", "PAUSE_REQUESTED", "PAUSING", "PAUSED", "RESUMING"} and not self.finalizing,
                    "created_at": self.created_at, "started_at": self.started_at,
                    "stop_requested_at": self.stop_requested_at, "stopped_at": self.stopped_at,
                    "ended_at": self.ended_at, "stop_reason": self.stop_reason,
                    "latest_completed_generation": self.latest_completed_generation,
                    "latest_validated_best": None if self.latest_validated_best is None else dict(self.latest_validated_best),
                    "result_reference": self.result_reference, "terminal_error": self.terminal_error,
                    "elapsed_ms": self.elapsed_offset + round(((self.ended_clock or time.monotonic()) - self.started_clock) * 1000)}

    def _state(self, state, emit=True, persist=True):
        if state not in TRANSITIONS[self.state]:
            raise ValueError(f"Invalid GA transition: {self.state} -> {state}")
        if self.durable and persist:
            from services.ga_checkpoint_service import write_marker
            write_marker(self, state=state)
        self.state = state
        if emit and self.on_state:
            self.on_state("run_state_changed", self.snapshot())

    def start(self):
        with self.lock:
            self.started_at = timestamp()
            if self.state == "CREATED":
                self._state("INITIALIZING", emit=False)

    def request_stop(self):
        with self.lock:
            if self.state in TERMINAL_STATES:
                return {**self.snapshot(), "accepted": False, "already_requested": self.stop_requested}
            if self.stop_requested:
                return {**self.snapshot(), "accepted": True, "already_requested": True}
            if self.finalizing:
                raise StopConflict("The final generation has been committed; this run is already finalizing.")
            self.stop_requested = True
            self.pause_requested = False
            self.stop_requested_at = timestamp()
            self.stop_reason = "administrator_request"
            self._state("STOP_REQUESTED")
            return {**self.snapshot(), "accepted": True, "already_requested": False}

    def request_pause(self):
        with self.lock:
            if self.state in TERMINAL_STATES:
                return {**self.snapshot(), "accepted": False, "already_requested": False}
            if self.state in {"PAUSE_REQUESTED", "PAUSING", "PAUSED"}:
                return {**self.snapshot(), "accepted": True, "already_requested": True}
            if self.stop_requested or self.finalizing or self.state == "RESUMING":
                raise StopConflict("Pause is unavailable while stopping, resuming or finalizing.")
            self.pause_requested = True
            self.pause_requested_at = timestamp()
            self._state("PAUSE_REQUESTED")
            return {**self.snapshot(), "accepted": True, "already_requested": False}

    def begin_pause(self, final=False):
        with self.lock:
            if self.stop_requested:
                return False
            if self.pause_requested:
                self._state("PAUSING")
                return True
            if final:
                self.finalizing = True  # Linearize pause/completion at the last boundary.
            return False

    def finish_pause(self, checkpoint):
        with self.lock:
            self.checkpoint = checkpoint
            if self.stop_requested:
                return False  # Stop won while the checkpoint was being written.
            from services.ga_checkpoint_service import write_marker
            self.paused_at = timestamp()
            self.ended_clock = time.monotonic()
            # Durable PAUSED marker precedes the in-memory state/event acknowledgement.
            write_marker(self, state="PAUSED", checkpoint=checkpoint)
            self._state("PAUSED", persist=False)
            return True

    def begin_resume(self):
        with self.lock:
            if self.execution_active or self.state != "PAUSED":
                raise StopConflict("Only an idle, durably paused run can resume.")
            self.execution_active = True
            self.pause_requested = False
            self.finalizing = False
            self.elapsed_offset = self.snapshot()["elapsed_ms"]
            self.started_clock = time.monotonic()
            self.ended_clock = None
            self.resumed_at = timestamp()
            self._state("RESUMING")

    def resumed(self):
        with self.lock:
            if self.state == "RESUMING":
                self._state("RUNNING")

    def boundary(self, generation, fitness):
        """Only called after the whole survivor population passes publication validation."""
        with self.lock:
            self.latest_completed_generation = generation
            self.latest_validated_best = {"generation": generation, "best_fitness": fitness}
            if self.state == "INITIALIZING":
                self._state("RUNNING", emit=False)

    def capture_progress(self, event_type, data):
        if event_type in {"initial_population_ready", "generation_completed"}:
            with self.lock:
                self.latest_progress = copy.deepcopy(data)
                if not self.progress_history or self.progress_history[-1]["generation"] != data["generation"]:
                    self.progress_history.append(copy.deepcopy(data))

    def acknowledge_stop(self):
        with self.lock:
            if not self.stop_requested:
                return False
            if self.state != "STOPPING":
                self.finalizing = True
                self._state("STOPPING")
            return True

    def seal(self):
        """Linearize the last stop/completion race before result finalization."""
        with self.lock:
            self.finalizing = True
            return self.acknowledge_stop()

    def finish(self, state, reference=None, stopped_at=None):
        with self.lock:
            if state not in {"STOPPED", "COMPLETED"}:
                raise ValueError("Invalid successful terminal state")
            if (state == "STOPPED") != (self.state == "STOPPING"):
                raise ValueError("Terminal state disagrees with acknowledged stop")
            self.result_reference = reference
            self.ended_at = stopped_at or timestamp()
            self.ended_clock = time.monotonic()
            if state == "STOPPED":
                self.stopped_at = self.ended_at
            self._state(state)

    def fail(self, error):
        with self.lock:
            if self.state in TERMINAL_STATES:
                return  # Transport errors cannot rewrite an acknowledged terminal result.
            self.terminal_error = str(error)
            self.ended_at = timestamp()
            self.ended_clock = time.monotonic()
            try:
                self._state("FAILED")
            except OSError:
                self.state = "FAILED"
                if self.on_state:
                    self.on_state("run_state_changed", self.snapshot())


class RunRegistry:
    def __init__(self):
        self.lock = threading.Lock()
        self.runs = {}
        self.active_id = None
        self.process_instance_id = str(uuid4())

    def register(self, configuration=None):
        control = RunControl(self.process_instance_id, configuration)
        with self.lock:
            self.runs[control.run_id] = control
            self.active_id = control.run_id
        return control

    def get(self, run_id):
        with self.lock:
            return self.runs.get(run_id)

    def active(self):
        with self.lock:
            return self.runs.get(self.active_id)

    def claim(self, control):
        with self.lock:
            if self.active_id is not None:
                raise StopConflict("Another GA worker already owns admission.")
            self.active_id = control.run_id

    def discover(self):
        """Read durable records once per ID; never start workers during discovery."""
        from services.ga_checkpoint_service import CHECKPOINTS_DIR, read_marker
        if not CHECKPOINTS_DIR.exists():
            return
        for directory in CHECKPOINTS_DIR.iterdir():
            if not directory.is_dir():
                continue
            try:
                with self.lock:
                    if directory.name in self.runs:
                        continue
                marker = read_marker(directory.name)
                if marker is None:
                    continue
                control = RunControl(self.process_instance_id, marker.get("configuration"))
                control.run_id = directory.name
                control.state = marker["state"] if marker["state"] in TERMINAL_STATES | {"PAUSED"} else "INTERRUPTED"
                for field in ("created_at", "started_at", "pause_requested_at", "paused_at", "resumed_at",
                              "stop_requested", "pause_requested", "finalizing",
                              "stop_requested_at", "stopped_at", "ended_at", "stop_reason",
                              "latest_completed_generation", "latest_validated_best", "latest_progress",
                              "progress_history", "result_reference", "terminal_error", "checkpoint"):
                    if field in marker:
                        setattr(control, field, marker[field])
                control.execution_active = False
                control.elapsed_offset = marker.get("elapsed_ms", 0)
                control.ended_clock = control.started_clock
                control.durable = True
                with self.lock:
                    self.runs.setdefault(control.run_id, control)
            except (ValueError, OSError, KeyError, TypeError):
                # Corrupt durable metadata is never adopted as a resumable run.
                continue

    def paused(self):
        with self.lock:
            return [control for control in self.runs.values() if control.state == "PAUSED"]

    def release(self, control):
        with control.lock:
            control.execution_active = False
            control.on_state = None  # Terminal registry records retain no stream queue.
            if control.durable:
                from services.ga_checkpoint_service import write_marker
                try:
                    write_marker(control)
                except OSError:
                    # Core lifecycle commits already happened before their events.
                    # Cleanup must release admission even on an unavailable disk.
                    pass
        with self.lock:
            if self.active_id == control.run_id:
                self.active_id = None


def save_stopped_result(control, result):
    """Write only finalized validated results, replacing atomically on the same volume."""
    STOPPED_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = STOPPED_RUNS_DIR / f"{control.run_id}.json"
    descriptor, temporary = tempfile.mkstemp(prefix=f".{control.run_id}-", suffix=".tmp", dir=STOPPED_RUNS_DIR)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(result, file, indent=2, ensure_ascii=False, allow_nan=False)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return f"stopped_runs/{control.run_id}.json"
