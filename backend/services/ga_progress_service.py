"""Read-only generation telemetry; scores are captured, never recalculated."""
import hashlib
import json
import math
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from genetic_algorithm.utils.FitnessObservation import observed_scores
from schemas.ga_events import GAEvent


def input_fingerprint():
    backend = Path(__file__).resolve().parents[1]
    paths = sorted({*backend.joinpath("data").glob("*.json"),
                    *backend.joinpath("data").glob("*.csv")})
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(backend)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class EventEmitter:
    def __init__(self, sink, run_id=None):
        self.run_id = run_id or str(uuid4())  # OS entropy; does not consume GA random state.
        self.sequence = 0
        self.sink = sink
        self.lock = threading.Lock()

    def emit(self, event_type, data):
        with self.lock:
            self.sequence += 1
            event = GAEvent(run_id=self.run_id, sequence=self.sequence, type=event_type,
                            timestamp=datetime.now(timezone.utc).isoformat(), data=data).model_dump()
            if event_type in {"log", "error"}:
                event["message"] = data["message"]  # Existing stream clients.
            self.sink(event)


class GenerationMonitor:
    def __init__(self, callback, population_size, generations, configuration):
        self.callback = callback
        self.population_size = population_size
        self.generations = generations
        self.configuration = configuration
        self.started = self.previous_time = time.monotonic()
        self.fingerprint = input_fingerprint()
        self.configuration_fingerprint = hashlib.sha256(json.dumps(
            {"inputs": self.fingerprint, "ga": configuration}, sort_keys=True
        ).encode()).hexdigest()
        self.accepted = 0
        self.baseline_count = 0
        self.previous_best = None
        self.without_improvement = 0
        self.comparable = True

    def check_inputs(self):
        self.comparable = self.comparable and input_fingerprint() == self.fingerprint
        if not self.comparable:
            raise ValueError("GA inputs/configuration changed during execution; metrics are no longer comparable. No result will be published.")

    def register_baseline(self, payload):
        # Include the actual seed; stored fitness and file timestamps are not inputs.
        seed = None if payload is None else {"schedule": payload["schedule"], "subject_keys": payload.get("subject_keys")}
        self.configuration_fingerprint = hashlib.sha256(json.dumps({
            "inputs": self.fingerprint, "ga": self.configuration, "baseline": seed,
        }, sort_keys=True, default=str).encode()).hexdigest()

    def report(self, generation, population, best_ever):
        self.check_inputs()
        if self.callback is None:
            return
        scores = observed_scores.get()
        if scores is None or any(id(candidate) not in scores for candidate in population):
            raise ValueError("Monitoring failed: survivor fitness values were not captured by the scorer.")
        values = [scores[id(candidate)][1] for candidate in population]
        if not values or not all(math.isfinite(value) for value in values):
            raise ValueError("Monitoring failed: survivor fitness values are unavailable or non-finite.")
        improvement = 0 if self.previous_best is None else max(0, self.previous_best - best_ever)
        self.without_improvement = 0 if generation == 0 or improvement > 0 else self.without_improvement + 1
        now = time.monotonic()
        data = {
            "status": "RUNNING", "generation": generation, "generation_limit": self.generations,
            "population_requested": self.population_size, "population_actual": len(population),
            "generation_best_fitness": min(values), "best_ever_fitness": best_ever,
            "average_fitness": sum(values) / len(values), "worst_fitness": max(values),
            "best_ever_improvement": improvement,
            "generations_without_improvement": self.without_improvement,
            "elapsed_ms": round((now - self.started) * 1000),
            "generation_elapsed_ms": round((now - self.previous_time) * 1000),
            "accepted_new_chromosomes_total": self.accepted,
            "baseline_chromosomes": self.baseline_count, "fitness_evaluations_total": None,
            "input_fingerprint": self.fingerprint,
            "configuration_fingerprint": self.configuration_fingerprint,
            "metrics_comparable": self.comparable, "validation_status": "passed",
        }
        # JSON copy prevents consumers from receiving mutable GA state.
        self.callback("initial_population_ready" if generation == 0 else "generation_completed",
                      json.loads(json.dumps(data, allow_nan=False)))
        self.previous_best, self.previous_time = best_ever, now
        scores.clear()
