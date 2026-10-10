"""Cooperative lifecycle control. Process-local; never a population checkpoint."""
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
    "CREATED": {"INITIALIZING", "STOP_REQUESTED", "FAILED"},
    "INITIALIZING": {"RUNNING", "STOP_REQUESTED", "COMPLETED", "FAILED"},
    "RUNNING": {"STOP_REQUESTED", "COMPLETED", "FAILED"},
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
                    "execution_active": self.execution_active,
                    "stop_requested": self.stop_requested, "finalizing": self.finalizing,
                    "accepting_stop": self.state in {"CREATED", "INITIALIZING", "RUNNING"} and not self.finalizing,
                    "created_at": self.created_at, "started_at": self.started_at,
                    "stop_requested_at": self.stop_requested_at, "stopped_at": self.stopped_at,
                    "ended_at": self.ended_at, "stop_reason": self.stop_reason,
                    "latest_completed_generation": self.latest_completed_generation,
                    "latest_validated_best": None if self.latest_validated_best is None else dict(self.latest_validated_best),
                    "result_reference": self.result_reference, "terminal_error": self.terminal_error,
                    "elapsed_ms": round(((self.ended_clock or time.monotonic()) - self.started_clock) * 1000)}

    def _state(self, state, emit=True):
        if state not in TRANSITIONS[self.state]:
            raise ValueError(f"Invalid GA transition: {self.state} -> {state}")
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
            self.stop_requested_at = timestamp()
            self.stop_reason = "administrator_request"
            self._state("STOP_REQUESTED")
            return {**self.snapshot(), "accepted": True, "already_requested": False}

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
            self._state("FAILED")


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

    def release(self, control):
        with control.lock:
            control.execution_active = False
            control.on_state = None  # Terminal registry records retain no stream queue.
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
