"""Observational, run-scoped history. Never scores, samples or restores a GA.

The context-local monitor adapter leaves checkpoint-fingerprinted engine source
unchanged. Candidates are copied to portable DTOs at the existing validated
boundary; a bounded writer performs validation, encoding and atomic disk I/O.
"""
import csv
import hashlib
import io
import json
import os
import queue
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from genetic_algorithm.utils.FitnessObservation import observed_scores
from services import ga_checkpoint_service as checkpoints
from services.chromosome_service import chromosome_to_payload, payload_to_chromosome
from services.ga_progress_service import GenerationMonitor, input_fingerprint
from services.ga_publication_service import validate_publication
from schemas.ga_history import GenerationSnapshot, HistoryIndex
from services.ga_validation_templates import validation_templates

SNAPSHOTS_DIR = Path(__file__).resolve().parents[1] / "saved_chromosomes" / "generation_snapshots"
SCHEMA_VERSION = 1
_capture = ContextVar("ga_generation_history", default=None)
_storage_lock = threading.RLock()


class HistoryError(ValueError):
    def __init__(self, message, code="GA_HISTORY_INVALID", status=422):
        super().__init__(message)
        self.code, self.status = code, status


def utc():
    return datetime.now(timezone.utc).isoformat()


def directory(run_id):
    try:
        if str(UUID(run_id)) != run_id:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise HistoryError("Invalid run ID.", status=404)
    return SNAPSHOTS_DIR / run_id


def write_document(path, data):
    encoded = checkpoints.canonical(data)
    envelope = {"sha256": hashlib.sha256(encoded).hexdigest(), "data": data}
    content = checkpoints.canonical(envelope)
    checkpoints.atomic_write(path, content)
    return len(content)


def read_document(path):
    try:
        envelope = json.loads(path.read_bytes())
        data = envelope["data"]
        if hashlib.sha256(checkpoints.canonical(data)).hexdigest() != envelope["sha256"]:
            raise ValueError()
        if data["schema_version"] != SCHEMA_VERSION:
            raise ValueError()
        return data
    except FileNotFoundError as error:
        raise HistoryError("History record not found.", "GA_HISTORY_NOT_FOUND", 404) from error
    except OSError as error:
        raise HistoryError("History storage is temporarily unavailable. Check backend storage and retry.",
                           "GA_HISTORY_UNAVAILABLE", 503) from error
    except (ValueError, KeyError, TypeError) as error:
        raise HistoryError("History record failed its schema/integrity check.", "GA_HISTORY_CORRUPT") from error


def manifest(run_id):
    data = read_document(directory(run_id) / "index.json")
    try:
        HistoryIndex.model_validate(data)
    except ValueError as error:
        raise HistoryError("History index failed its schema check.", "GA_HISTORY_CORRUPT") from error
    if data["run_id"] != run_id:
        raise HistoryError("History identity mismatch.")
    return data


def candidate_id(payload):
    # Timestamps and penalties are observations, not schedule identity.
    return hashlib.sha256(checkpoints.canonical({
        "schedule": payload["schedule"], "subject_keys": payload["subject_keys"]})).hexdigest()


def checked_payload(payload, templates, fingerprint):
    if input_fingerprint() != fingerprint:
        raise HistoryError("Original scheduling inputs are unavailable. Restore the run's inputs before validation/export.",
                           "GA_HISTORY_INPUT_CHANGED", 409)
    templates = validation_templates(templates)
    try:
        candidate = payload_to_chromosome(payload, *templates)
        validate_publication(candidate, *templates)
    except (ValueError, RuntimeError) as error:
        raise HistoryError(f"Historical schedule failed hard-constraint validation: {error}",
                           "GA_HISTORY_VALIDATION_FAILED") from error
    if input_fingerprint() != fingerprint:
        raise HistoryError("Inputs changed during validation; retry with the original inputs.", "GA_HISTORY_INPUT_CHANGED", 409)
    return candidate


def workloads(candidate, faculty):
    rows = []
    for member in faculty:
        if getattr(member, "is_external", False):
            continue
        assigned = [s for s in candidate if str(s.assigned_faculty.code) == str(member.code)]
        actual = sum(float(s.credit_units) for s in assigned)
        target = member.required_teaching_load
        rows.append({"faculty": f"Faculty {member.code}", "teaching_units": actual,
                     "required_teaching_load": target, "difference": actual - target,
                     "fulfillment_percent": actual / target * 100 if target else None,
                     "preparations": len({s.number for s in assigned}),
                     "assigned_subjects": sorted({s.number for s in assigned})})
    return rows


class HistoryWriter:
    def __init__(self, control, templates, resume_state=None, warning=None):
        self.control, self.path = control, directory(control.run_id)
        self.warning = warning
        self.templates = validation_templates(templates)
        self.engine = checkpoints.engine_fingerprint()
        self.fingerprint = input_fingerprint()
        self.best = None
        if resume_state is not None:
            self.best = chromosome_to_payload(resume_state["best_ever"], resume_state["best_ever_fitness"])
        self.jobs = queue.Queue(maxsize=2)
        self.interval = max(1, int(os.environ.get("GA_HISTORY_INTERVAL", "1")))
        self.max_bytes = max(1, int(os.environ.get("GA_HISTORY_MAX_RUN_BYTES", str(256 * 1024 * 1024))))
        self.max_snapshot_bytes = 16 * 1024 * 1024
        self.last_error = None
        with _storage_lock:
            try:
                self.index = manifest(control.run_id)
            except HistoryError as error:
                if error.status != 404:
                    raise
                self.index = {"schema_version": 1, "run_id": control.run_id, "created_at": control.created_at, "started_at": control.started_at,
                              "configuration": control.configuration, "state": control.state,
                              "input_fingerprint": self.fingerprint, "engine_fingerprint": self.engine,
                              "retention": {"interval": self.interval, "max_run_bytes": self.max_bytes,
                                            "automatic_deletion": False},
                              "generations": [], "errors": [], "skipped_generations": [], "bytes_written": 0}
                write_document(self.path / "index.json", self.index)
            # Retention is a run policy, including after checkpoint continuation.
            self.interval = self.index["retention"]["interval"]
            self.max_bytes = self.index["retention"]["max_run_bytes"]
        # Do not share the foreground diagnostic writer's partial-line buffer
        # across threads. Complete history warnings have a run-scoped sink.
        self.thread = threading.Thread(target=self._write_jobs, name=f"history-{control.run_id}", daemon=True)
        self.thread.start()

    def error(self, generation, code):
        self.last_error = code
        with _storage_lock:
            self.index["errors"].append({"generation": generation, "code": code, "timestamp": utc()})
            try:
                write_document(self.path / "index.json", self.index)
            except OSError:
                pass  # The visible in-process warning still reports disk failure.
        self.control.history_error = code
        message = f"GENERATION HISTORY: generation {generation} not recorded ({code}). Optimization continues."
        from services.ga_log_service import console_print, diagnostic_print
        try:
            if self.warning:
                self.warning(message)
            else:
                diagnostic_print(message)
        except Exception:
            console_print(message)

    def capture(self, metrics, population, configuration=None):
        started = time.perf_counter()
        generation = metrics["generation"]
        try:
            scores = observed_scores.get()
            candidate = min(population, key=lambda item: scores[id(item)][1])
            penalty = scores[id(candidate)][1]
            if penalty != metrics["generation_best_fitness"] or metrics["validation_status"] != "passed":
                raise HistoryError("Boundary metrics/candidate mismatch.")
            payload = chromosome_to_payload(candidate, penalty)
            if self.best is None or metrics["best_ever_fitness"] < self.best["best_fitness"]:
                if penalty != metrics["best_ever_fitness"]:
                    raise HistoryError("Best-ever observation is unavailable.")
                self.best = payload
            if self.best["best_fitness"] != metrics["best_ever_fitness"]:
                raise HistoryError("Best-ever continuation mismatch.")
            if generation % self.interval:
                self.jobs.put_nowait(("skip", generation))
                return
            # Only pure DTOs cross the thread boundary; no mutable GA references.
            from genetic_algorithm.utils.FrozenInputs import scoring_inputs
            frozen = scoring_inputs.get()
            encoded = json.dumps({"schema_version": 1, "run_id": self.control.run_id,
                "generation": generation, "timestamp": utc(), "metrics": metrics,
                "engine_fingerprint": self.engine, "ga_configuration": configuration or self.control.configuration,
                "fitness_configuration": frozen["settings"] if frozen else None,
                "generation_best": {"chromosome_id": candidate_id(payload), "payload": payload},
                "best_ever": {"chromosome_id": candidate_id(self.best), "payload": self.best},
                "fitness_breakdown": None, "breakdown_unavailable_reason": "The boundary scorer returned only a total; no additional fitness evaluation was performed.",
                "capture_elapsed_ms": 0}, allow_nan=False)
            if len(encoded.encode("utf-8")) > self.max_snapshot_bytes:
                raise HistoryError("Snapshot exceeds payload budget.", "GA_HISTORY_CAPACITY")
            data = json.loads(encoded)
            data["capture_elapsed_ms"] = (time.perf_counter() - started) * 1000
            self.jobs.put_nowait(("snapshot", data))
        except queue.Full:
            self.error(generation, "GA_HISTORY_BACKPRESSURE")
        except Exception as error:
            self.error(generation, error.code if isinstance(error, HistoryError) else "GA_HISTORY_CAPTURE_FAILED")

    def _write_jobs(self):
        while True:
            job = self.jobs.get()
            try:
                if job is None:
                    return
                kind, data = job
                if kind == "analysis":
                    with _storage_lock:
                        if not any(data["chromosome_id"] in (row["generation_best_id"], row["best_ever_id"]) for row in self.index["generations"]):
                            continue
                        size = len(checkpoints.canonical(data)) + 128
                        if self.index["bytes_written"] + size > self.max_bytes:
                            raise HistoryError("History retention capacity reached.", "GA_HISTORY_CAPACITY")
                        self.index["bytes_written"] += write_document(self.path / f"analysis-{data['chromosome_id']}.json", data)
                        write_document(self.path / "index.json", self.index)
                    continue
                if kind == "skip":
                    with _storage_lock:
                        self.index["skipped_generations"].append(data)
                        write_document(self.path / "index.json", self.index)
                    continue
                self.commit(data)
            except Exception as error:
                self.error(data.get("generation") if isinstance(data, dict) else data,
                           error.code if isinstance(error, HistoryError) else "GA_HISTORY_STORAGE_FAILED")
            finally:
                self.jobs.task_done()

    def record_result(self, result):
        """Attach only the already computed final breakdown; never re-analyze."""
        if self.best is None or result is None:
            return
        if result["best_fitness"] != self.best["best_fitness"] or result["schedule"] != self.best["schedule"]:
            self.error(None, "GA_HISTORY_FINAL_ANALYSIS_MISMATCH")
            return
        self.jobs.put(("analysis", {"schema_version": 1, "chromosome_id": candidate_id(self.best),
            "timestamp": utc(), "fitness": result["best_fitness"],
            "fitness_breakdown": result["fitness_breakdown"], "source": "existing-final-evaluation",
            "input_fingerprint": self.fingerprint, "engine_fingerprint": self.engine}))

    def commit(self, data):
        started = time.perf_counter()
        if (data["run_id"] != self.control.run_id or data["engine_fingerprint"] != self.engine
                or data["metrics"]["input_fingerprint"] != self.fingerprint):
            raise HistoryError("Snapshot run/engine/input identity mismatch.")
        if data["generation"] < 0 or data["generation"] != data["metrics"]["generation"]:
            raise HistoryError("Snapshot generation mismatch.")
        for kind, metric in (("generation_best", "generation_best_fitness"), ("best_ever", "best_ever_fitness")):
            if (candidate_id(data[kind]["payload"]) != data[kind]["chromosome_id"]
                    or data[kind]["payload"]["best_fitness"] != data["metrics"][metric]):
                raise HistoryError("Snapshot candidate identity/penalty mismatch.")
        # Reuse the publication gate on reconstructed copies before indexing.
        checked = {}
        for kind in ("generation_best", "best_ever"):
            identity = data[kind]["chromosome_id"]
            if identity not in checked:
                checked[identity] = checked_payload(data[kind]["payload"], self.templates, data["metrics"]["input_fingerprint"])
            candidate = checked[identity]
            data[kind]["workload"] = workloads(candidate, self.templates[1])
        data["validation"] = {"status": "passed", "gate": "phase-3b-publication",
                              "validated_at": utc(), "conflicts": 0, "eligibility_violations": 0,
                              "overload_violations": 0, "fixed_schedule_violations": 0,
                              "preassignment_violations": 0, "component_duration_violations": 0}
        data["validation_elapsed_ms"] = (time.perf_counter() - started) * 1000
        GenerationSnapshot.model_validate(data)  # Check only; preserve original JSON numeric values.
        generation = data["generation"]
        with _storage_lock:
            # Immutable generation identity, including replay after a crash.
            existing = next((item for item in self.index["generations"] if item["generation"] == generation), None)
            if existing is not None:
                if (existing["generation_best_id"] != data["generation_best"]["chromosome_id"] or
                        existing["best_ever_id"] != data["best_ever"]["chromosome_id"] or existing["metrics"] != data["metrics"]):
                    raise HistoryError("Generation already recorded with different observations.", "GA_HISTORY_DUPLICATE_CONFLICT")
                return
            if self.index["generations"]:
                previous = self.index["generations"][-1]
                if (generation <= previous["generation"] or data["metrics"]["best_ever_fitness"] > previous["metrics"]["best_ever_fitness"]
                        or data["metrics"]["configuration_fingerprint"] != previous["metrics"]["configuration_fingerprint"]):
                    raise HistoryError("History ordering, best-ever or configuration mismatch.")
            size = len(checkpoints.canonical(data)) + 128
            if size > self.max_snapshot_bytes or self.index["bytes_written"] + size > self.max_bytes:
                raise HistoryError("History retention capacity reached.", "GA_HISTORY_CAPACITY")
            path = self.path / f"generation-{generation:06d}.json"
            # A committed but not indexed file may remain after an abrupt crash;
            # verify it, never overwrite it. Its observations must match a replay.
            if path.exists():
                orphan = read_document(path)
                for key in ("metrics", "generation_best", "best_ever"):
                    if orphan[key] != data[key]:
                        raise HistoryError("Unindexed generation conflicts with replay.", "GA_HISTORY_DUPLICATE_CONFLICT")
                data = orphan
                size = path.stat().st_size
            else:
                size = write_document(path, data)
            self.index["generations"].append({"generation": generation, "timestamp": data["timestamp"],
                "metrics": data["metrics"], "generation_best_id": data["generation_best"]["chromosome_id"],
                "best_ever_id": data["best_ever"]["chromosome_id"], "capture_elapsed_ms": data["capture_elapsed_ms"],
                "validation_elapsed_ms": data["validation_elapsed_ms"], "snapshot_bytes": size})
            self.index["bytes_written"] += size
            try:
                write_document(self.path / "index.json", self.index)
            except Exception:
                self.index["generations"].pop()
                self.index["bytes_written"] -= size
                raise

    def close(self):
        self.jobs.put(None)
        self.thread.join()
        with _storage_lock:
            self.index.update(state=self.control.state, updated_at=utc(), ended_at=self.control.ended_at)
            write_document(self.path / "index.json", self.index)


class HistoryGenerationMonitor(GenerationMonitor):
    def report(self, generation, population, best_ever):
        recorder = _capture.get()
        if recorder is None:
            return super().report(generation, population, best_ever)
        original = self.callback
        def callback(kind, data):
            original(kind, data)
            recorder.capture(data, population, self.configuration)
        self.callback = callback if original is not None else None
        try:
            return super().report(generation, population, best_ever)
        finally:
            self.callback = original


@contextmanager
def capture_history(control, templates, resume_state=None, warning=None):
    recorder = None
    token = None
    try:
        recorder = HistoryWriter(control, templates, resume_state, warning)
        token = _capture.set(recorder)
    except Exception:
        control.history_error = "GA_HISTORY_UNAVAILABLE"
        from services.ga_log_service import diagnostic_print
        diagnostic_print("GENERATION HISTORY unavailable: storage initialization failed. Optimization continues.")
    try:
        yield recorder
    finally:
        if token is not None:
            _capture.reset(token)
        if recorder is not None:
            try:
                recorder.close()
            except Exception:
                recorder.error(None, "GA_HISTORY_FINALIZATION_FAILED")


def get_generation(run_id, generation):
    index = manifest(run_id)
    entry = next((item for item in index["generations"] if item["generation"] == generation), None)
    if entry is None:
        raise HistoryError("Generation not recorded.", "GA_HISTORY_NOT_FOUND", 404)
    data = read_document(directory(run_id) / f"generation-{generation:06d}.json")
    try:
        GenerationSnapshot.model_validate(data)
    except ValueError as error:
        raise HistoryError("Generation snapshot failed its schema check.", "GA_HISTORY_CORRUPT") from error
    if data["run_id"] != run_id or data["generation"] != generation or data["validation"]["status"] != "passed":
        raise HistoryError("Generation identity/validation mismatch.")
    if data["metrics"] != entry["metrics"] or data["engine_fingerprint"] != index["engine_fingerprint"]:
        raise HistoryError("Generation/index observations disagree.")
    for kind, metric, identity in (("generation_best", "generation_best_fitness", "generation_best_id"),
                                   ("best_ever", "best_ever_fitness", "best_ever_id")):
        if (candidate_id(data[kind]["payload"]) != data[kind]["chromosome_id"]
                or data[kind]["chromosome_id"] != entry[identity]
                or data[kind]["payload"]["best_fitness"] != data["metrics"][metric]):
            raise HistoryError("Candidate identity/penalty mismatch.")
    return data


def analysis(run_id, generation, kind="generation_best"):
    data = get_generation(run_id, generation)
    selected = data[kind]
    breakdown = None
    breakdown_timestamp = None
    path = directory(run_id) / f"analysis-{selected['chromosome_id']}.json"
    if path.exists():
        extra = read_document(path)
        if (extra["chromosome_id"] != selected["chromosome_id"] or extra["fitness"] != selected["payload"]["best_fitness"]
                or extra["input_fingerprint"] != data["metrics"]["input_fingerprint"] or extra["engine_fingerprint"] != data["engine_fingerprint"]):
            raise HistoryError("Historical analysis identity mismatch.")
        breakdown = extra["fitness_breakdown"]
        breakdown_timestamp = extra["timestamp"]
    return {"schema_version": 1, "run_id": run_id, "generation": generation, "candidate": kind,
            "chromosome_id": selected["chromosome_id"], "timestamp": data["timestamp"],
            "fitness": selected["payload"]["best_fitness"], "fitness_breakdown": breakdown,
            "breakdown_source": "existing-final-evaluation" if breakdown is not None else None,
            "breakdown_timestamp": breakdown_timestamp,
            "breakdown_unavailable_reason": None if breakdown is not None else data["breakdown_unavailable_reason"],
            "workload": selected["workload"], "preference_satisfaction": None,
            "preference_unavailable_reason": "Per-faculty preference results were not captured at this boundary.",
            "validation": data["validation"]}


def compare(run_id, left, right, kind="generation_best"):
    a, b = get_generation(run_id, left), get_generation(run_id, right)
    for key in ("input_fingerprint", "configuration_fingerprint"):
        if a["metrics"][key] != b["metrics"][key]:
            raise HistoryError("Generations use incompatible inputs/configuration.", "GA_HISTORY_INCOMPATIBLE", 409)
    if a["engine_fingerprint"] != b["engine_fingerprint"]:
        raise HistoryError("Generations use incompatible engines.", "GA_HISTORY_INCOMPATIBLE", 409)
    def grouped(data):
        result = {}
        for row in data[kind]["payload"]["schedule"]:
            result.setdefault((row["subject"], row["section"], row["type"]), []).append(row)
        return {key: sorted(rows, key=lambda row: (row["day"], row["start"], row["end"])) for key, rows in result.items()}
    before, after = grouped(a), grouped(b)
    changes = []
    for key in sorted(before.keys() | after.keys()):
        old, new = before.get(key, []), after.get(key, [])
        if old != new:
            fields = [field for field in ("faculty", "room", "day", "start", "end")
                      if [row[field] for row in old] != [row[field] for row in new]]
            changes.append({"subject": key[0], "section": key[1], "component": key[2],
                            "fields": fields, "offering_change": "added" if not old else "removed" if not new else "changed",
                            "before": old, "after": new})
    before_breakdown = analysis(run_id, left, kind)["fitness_breakdown"]
    after_breakdown = analysis(run_id, right, kind)["fitness_breakdown"]
    return {"schema_version": 1, "run_id": run_id, "left": left, "right": right, "candidate": kind,
            "identical_chromosomes": a[kind]["chromosome_id"] == b[kind]["chromosome_id"],
            "left_metrics": a["metrics"], "right_metrics": b["metrics"],
            "improvement": {key: a["metrics"][key] - b["metrics"][key] for key in
                            ("generation_best_fitness", "best_ever_fitness", "average_fitness")},
            "changes": changes, "left_workload": a[kind]["workload"], "right_workload": b[kind]["workload"],
            "left_fitness_breakdown": before_breakdown, "right_fitness_breakdown": after_breakdown,
            "preference_comparison": None, "preference_unavailable_reason": "Per-faculty preference satisfaction was not captured at these generation boundaries."}


def update_lifecycle(control):
    """Persist final/paused lifecycle independently of continuation checkpoints."""
    with _storage_lock:
        try:
            index = manifest(control.run_id)
        except HistoryError as error:
            if error.status == 404:
                return
            raise
        index.update(state=control.state, started_at=control.started_at, ended_at=control.ended_at, updated_at=utc())
        write_document(directory(control.run_id) / "index.json", index)


def csv_content(rows, fields):
    def safe(value):
        text = str(value) if value is not None else ""
        if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
            return "'" + text
        return text
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows({key: safe(row.get(key)) for key in fields} for row in rows)
    return output.getvalue()
