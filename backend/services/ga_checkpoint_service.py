"""Versioned JSON graph checkpoints; no pickle, imports from files, or scoring."""
import copy
import gzip
import hashlib
import json
import math
import os
import platform
import random
import tempfile
from pathlib import Path
from uuid import UUID, uuid4

import pandas as pd
import numpy as np

from genetic_algorithm.models.Subject import Subject
from genetic_algorithm.models.Faculty import Faculty
from genetic_algorithm.models.Room import Room
from genetic_algorithm.models.Section import Section
from genetic_algorithm.models.Student import Student
from genetic_algorithm.models.TimeBlock import TimeBlock
from genetic_algorithm.models.PreassignedAssignment import PreassignedAssignment, ExternalInstructor
from services.ga_progress_service import input_fingerprint
from services.ga_publication_service import validate_publication

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINTS_DIR = ROOT / "run_checkpoints"
SCHEMA_VERSION = 1
ENGINE_VERSION = "ga-continuation-v1"
MAX_JSON_BYTES = 512 * 1024 * 1024
MAX_NODES = 2_000_000
CLASSES = {cls.__name__: cls for cls in (
    Subject, Faculty, Room, Section, Student, TimeBlock, PreassignedAssignment, ExternalInstructor)}


class CheckpointError(ValueError):
    def __init__(self, message, code="GA_CHECKPOINT_INVALID"):
        super().__init__(message)
        self.code = code


class PausedRun:
    """Worker return value, never a published schedule."""
    pass


def canonical(value):
    return json.dumps(value, separators=(",", ":"), sort_keys=True, allow_nan=False).encode("utf-8")


def engine_fingerprint():
    digest = hashlib.sha256()
    paths = sorted((ROOT / "genetic_algorithm").rglob("*.py"))
    paths += [ROOT / "services" / name for name in (
        "ga_service.py", "ga_progress_service.py", "ga_publication_service.py",
        "ga_checkpoint_service.py", "ga_control_service.py", "chromosome_service.py",
        "faculty_analysis_service.py")]
    for path in paths:
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(path.read_bytes())
    digest.update(canonical([ENGINE_VERSION, platform.python_version(), pd.__version__, np.__version__]))
    return digest.hexdigest()


def run_directory(run_id):
    try:
        if str(UUID(run_id)) != run_id:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise CheckpointError("Invalid canonical run ID.")
    return CHECKPOINTS_DIR / run_id


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        # POSIX directory durability; Windows guarantees atomic file replacement
        # but does not expose a portable directory-fsync API.
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def encode_graph(root):
    """Preserve list/dict order, aliases and cyclic calendar/assignment references."""
    nodes, references = [], {}
    def encode(value):
        if value is None or type(value) in (str, int, bool):
            return value
        if type(value) is float:
            return value if math.isfinite(value) else {"scalar": repr(value)}
        if isinstance(value, np.generic):
            return encode(value.item())
        if value is pd.NA:
            return {"scalar": "NA"}
        marker = id(value)
        if marker in references:
            return {"ref": references[marker]}
        index = len(nodes)
        if index >= MAX_NODES:
            raise CheckpointError("Checkpoint exceeds the supported graph size.")
        references[marker] = index
        node = {}
        nodes.append(node)
        if type(value) in (list, tuple, set):
            node.update(kind=type(value).__name__, items=[encode(item) for item in value])
        elif type(value) is dict:
            node.update(kind="dict", items=[[encode(k), encode(v)] for k, v in value.items()])
        elif type(value).__name__ in CLASSES and type(value) is CLASSES[type(value).__name__]:
            node.update(kind=type(value).__name__,
                        items=[[k, encode(v)] for k, v in vars(value).items()])
        else:
            raise CheckpointError(f"Unsupported checkpoint value: {type(value).__name__}")
        return {"ref": index}
    reference = encode(root)
    return {"root": reference, "nodes": nodes}


def decode_graph(graph):
    """Allocate only allowlisted passive model objects; never invoke constructors."""
    nodes = graph["nodes"]
    if not isinstance(nodes, list) or len(nodes) > MAX_NODES:
        raise CheckpointError("Invalid checkpoint graph size.")
    objects = []
    for node in nodes:
        kind = node["kind"]
        if kind == "list":
            objects.append([])
        elif kind == "dict":
            objects.append({})
        elif kind == "set":
            objects.append(set())
        elif kind == "tuple":
            objects.append(None)
        elif kind in CLASSES:
            objects.append(object.__new__(CLASSES[kind]))
        else:
            raise CheckpointError("Checkpoint contains an unsupported model type.")
    resolving = set()
    def decode(value):
        if not isinstance(value, dict):
            if value is None or type(value) in (str, int, float, bool):
                return value
            raise CheckpointError("Invalid graph value.")
        if set(value) == {"scalar"}:
            if value["scalar"] == "NA":
                return pd.NA
            if value["scalar"] not in {"nan", "inf", "-inf"}:
                raise CheckpointError("Invalid scalar.")
            return float(value["scalar"])
        if set(value) != {"ref"} or type(value["ref"]) is not int or not 0 <= value["ref"] < len(nodes):
            raise CheckpointError("Invalid graph reference.")
        index = value["ref"]
        if nodes[index]["kind"] == "tuple" and objects[index] is None:
            if index in resolving:
                raise CheckpointError("Cyclic immutable graph value.")
            resolving.add(index)
            objects[index] = tuple(decode(item) for item in nodes[index]["items"])
            resolving.remove(index)
        return objects[index]
    for index, node in enumerate(nodes):
        kind = node["kind"]
        if kind == "tuple":
            decode({"ref": index})
        elif kind in {"list", "set"}:
            values = [decode(item) for item in node["items"]]
            objects[index].extend(values) if kind == "list" else objects[index].update(values)
        elif kind == "dict":
            objects[index].update((decode(k), decode(v)) for k, v in node["items"])
        else:
            for key, value in node["items"]:
                if not isinstance(key, str) or key.startswith("_"):
                    raise CheckpointError("Invalid model field.")
                object.__setattr__(objects[index], key, decode(value))
    return decode(graph["root"])


def rng_to_json(value):
    return [rng_to_json(item) for item in value] if isinstance(value, tuple) else value


def rng_from_json(value):
    return tuple(rng_from_json(item) for item in value) if isinstance(value, list) else value


def dataframe_to_state(frame):
    return {"split": frame.to_dict(orient="split"), "dtypes": [str(dtype) for dtype in frame.dtypes]}


def dataframe_from_state(state):
    split = state["split"]
    frame = pd.DataFrame(split["data"], columns=split["columns"], index=split["index"])
    for column, dtype in zip(frame.columns, state["dtypes"]):
        frame[column] = frame[column].astype(dtype)
    return frame


def validate_state(state, current_templates):
    parameters = state["parameters"]
    generation = state["generation_completed"]
    population = state["population"]
    if (type(generation) is not int or not 0 <= generation <= parameters["generations"]
            or state["next_generation"] != generation + 1
            or not population or len(population) > parameters["population_size"]):
        raise CheckpointError("Invalid generation/population counters.")
    if [item["generation"] for item in state["history"]] != list(range(generation + 1)):
        raise CheckpointError("Incomplete or duplicate generation history.")
    if state["scoring_inputs"]["input_fingerprint"] != state["monitor"]["fingerprint"]:
        raise CheckpointError("Frozen evaluation context differs from checkpoint input identity.")
    monitor_keys = {"fingerprint", "configuration_fingerprint", "accepted", "baseline_count",
                    "previous_best", "without_improvement", "comparable", "history"}
    if set(state["monitor"]) != monitor_keys or state["monitor"]["comparable"] is not True:
        raise CheckpointError("Invalid checkpoint monitoring state.")
    for candidate in [*population, state["best_ever"]]:
        validate_publication(candidate, *current_templates)
        validate_publication(candidate, *state["publication_templates"])
    # Validate model profiles as well as schedule rows: score and operator caches
    # must not quietly weaken eligibility/workload metadata.
    authoritative = {str(f.code): f for f in current_templates[1]}
    fields = ("eligible_subjects", "admin_load", "research_load", "extension_load",
              "required_teaching_load", "absolute_max_teaching_load", "seniority_level")
    for candidate in [*population, state["best_ever"]]:
        for subject in candidate:
            faculty = subject.assigned_faculty
            if getattr(faculty, "is_external", False):
                continue
            source = authoritative.get(str(faculty.code))
            if source is None or any(getattr(faculty, field) != getattr(source, field) for field in fields):
                raise CheckpointError("Checkpoint faculty profile differs from authoritative inputs.")
    if not math.isfinite(state["best_ever_fitness"]):
        raise CheckpointError("Non-finite checkpoint fitness.")
    random.Random(0).setstate(state["random_state"])  # Validate, do not change global RNG.


def read_marker(run_id):
    path = run_directory(run_id) / "status.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_bytes())
        if data["run_id"] != run_id or data["schema_version"] != SCHEMA_VERSION:
            raise ValueError("Lifecycle identity mismatch.")
        return data
    except (ValueError, KeyError, TypeError, OSError) as error:
        raise CheckpointError(f"Invalid durable run status: {error}") from error


def write_marker(control, state=None, checkpoint=None):
    marker = {**control.snapshot(), "schema_version": SCHEMA_VERSION}
    if state:
        marker.update(state=state, status=state)
    if checkpoint is not None:
        marker["checkpoint"] = checkpoint
    else:
        marker["checkpoint"] = control.checkpoint
    atomic_write(run_directory(control.run_id) / "status.json", canonical(marker))
    return marker


def save_checkpoint(control, state, current_templates):
    validate_state(state, current_templates)
    payload = {"schema_version": SCHEMA_VERSION, "engine_version": ENGINE_VERSION,
               "run_id": control.run_id, "engine_fingerprint": engine_fingerprint(),
               "input_fingerprint": input_fingerprint(), "graph": encode_graph(state),
               "validation": {"population": "passed", "best_ever": "passed"},
               "requested_population": state["parameters"]["population_size"],
               "actual_population": len(state["population"]),
               "generation_completed": state["generation_completed"],
               "next_generation": state["next_generation"],
               "lifecycle": control.snapshot(),
               "source_inputs": {str(path.relative_to(ROOT)): path.read_text(encoding="utf-8-sig")
                                 for path in sorted((ROOT / "data").iterdir())
                                 if path.suffix in {".json", ".csv"}}}
    body = canonical(payload)
    if len(body) > MAX_JSON_BYTES:
        raise CheckpointError("Checkpoint exceeds supported JSON size.")
    envelope = {"sha256": hashlib.sha256(body).hexdigest(), "payload": payload}
    filename = f"checkpoint-{state['generation_completed']}-{uuid4()}.json.gz"
    path = run_directory(control.run_id) / filename
    atomic_write(path, gzip.compress(canonical(envelope), mtime=0))
    # Read and hard-validate the artifact before acknowledging its commit.
    load_checkpoint(control.run_id, current_templates, filename)
    return filename


def load_checkpoint(run_id, current_templates, filename=None):
    try:
        marker = read_marker(run_id) if filename is None else None
        filename = filename or (marker and marker["checkpoint"])
        if (not filename or Path(filename).name != filename or not filename.startswith("checkpoint-")
                or not filename.endswith(".json.gz")):
            raise CheckpointError("No safe checkpoint reference exists.")
        with gzip.open(run_directory(run_id) / filename, "rb") as stream:
            content = stream.read(MAX_JSON_BYTES + 1)
        if len(content) > MAX_JSON_BYTES:
            raise CheckpointError("Checkpoint exceeds supported JSON size.")
        envelope = json.loads(content)
        payload = envelope["payload"]
        if hashlib.sha256(canonical(payload)).hexdigest() != envelope["sha256"]:
            raise CheckpointError("Checkpoint checksum failed.")
        if (payload["schema_version"] != SCHEMA_VERSION or payload["engine_version"] != ENGINE_VERSION
                or payload["run_id"] != run_id or payload["engine_fingerprint"] != engine_fingerprint()):
            raise CheckpointError("Checkpoint engine/schema is incompatible.", "GA_CHECKPOINT_INCOMPATIBLE")
        if payload["input_fingerprint"] != input_fingerprint():
            raise CheckpointError("Scheduling inputs changed; resume is rejected.", "GA_CHECKPOINT_INPUT_CHANGED")
        state = decode_graph(payload["graph"])
        validate_state(state, current_templates)
        if (payload["generation_completed"] != state["generation_completed"]
                or payload["actual_population"] != len(state["population"])
                or state["monitor"]["fingerprint"] != payload["input_fingerprint"]):
            raise CheckpointError("Checkpoint counters or input identity are inconsistent.")
        return state
    except CheckpointError:
        raise
    except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, EOFError, RecursionError) as error:
        raise CheckpointError(f"Checkpoint cannot be restored: {error}") from error


def checkpoint_status(run_id, current_templates):
    marker = read_marker(run_id)
    if marker is None:
        raise CheckpointError("No durable run status exists.", "GA_UNKNOWN_RUN")
    result = {"run_id": run_id, "state": marker["state"], "checkpoint": marker.get("checkpoint"),
              "resumable": False, "generation_completed": marker.get("latest_completed_generation")}
    if marker["state"] == "PAUSED":
        try:
            state = load_checkpoint(run_id, current_templates)
            result.update(resumable=True, next_generation=state["next_generation"])
        except CheckpointError as error:
            result.update(code=error.code, error=str(error))
    return result
