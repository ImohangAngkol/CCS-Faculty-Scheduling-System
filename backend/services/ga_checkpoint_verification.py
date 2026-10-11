"""Bounded single-flight read-only verification; never caches a population.

Every request hashes the artifact bytes and current inputs/engine. Only an
unchanged artifact with unchanged authoritative metadata can reuse the scalar
answer from the original full checkpoint validator. Resume still loads and
validates the complete checkpoint independently.
"""
import copy
import hashlib
import threading
import zlib
from collections import OrderedDict
from concurrent.futures import Future

from services import ga_checkpoint_service as checkpoints

_lock = threading.Lock()
_answers = OrderedDict()
MAX_ANSWERS = 8


def load_checkpoint(run_id, templates):
    """Resume always uses the original full validator, never a status cache."""
    try:
        return checkpoints.load_checkpoint(run_id, templates)
    except zlib.error as error:
        raise checkpoints.CheckpointError("Checkpoint compression/integrity check failed.") from error


def identity(run_id, templates):
    marker = checkpoints.read_marker(run_id)
    if marker is None:
        raise checkpoints.CheckpointError("No durable run status exists.", "GA_UNKNOWN_RUN")
    filename = marker.get("checkpoint")
    if (not filename or checkpoints.Path(filename).name != filename
            or not filename.startswith("checkpoint-") or not filename.endswith(".json.gz")):
        raise checkpoints.CheckpointError("No safe checkpoint reference exists.")
    path = checkpoints.run_directory(run_id) / filename
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise checkpoints.CheckpointError("Checkpoint artifact is unavailable. Check backend storage and retry.",
                                          "GA_CHECKPOINT_UNAVAILABLE") from error
    metadata = hashlib.sha256(checkpoints.canonical(checkpoints.encode_graph(templates))).hexdigest()
    return (str(path.resolve()), digest.hexdigest(), marker["state"],
            checkpoints.engine_fingerprint(), checkpoints.input_fingerprint(), metadata)


def checkpoint_status(run_id, templates):
    marker = checkpoints.read_marker(run_id)
    if marker is None or marker["state"] != "PAUSED":
        return checkpoints.checkpoint_status(run_id, templates)
    try:
        key = identity(run_id, templates)
    except checkpoints.CheckpointError as error:
        return {"run_id": run_id, "state": marker["state"], "checkpoint": marker.get("checkpoint"),
                "generation_completed": marker.get("latest_completed_generation"), "resumable": False,
                "code": error.code, "error": str(error)}
    with _lock:
        answer = _answers.get(key)
        owner = answer is None
        if owner:
            while len(_answers) >= MAX_ANSWERS:
                completed = next((item for item, future in _answers.items() if future.done()), None)
                if completed is None:
                    raise checkpoints.CheckpointError("Checkpoint verification is busy; retry shortly.",
                                                      "GA_CHECKPOINT_VERIFICATION_BUSY")
                del _answers[completed]
            answer = Future()
            _answers[key] = answer
        _answers.move_to_end(key)
    if owner:
        try:
            try:
                result = checkpoints.checkpoint_status(run_id, templates)
            except zlib.error:
                result = {"run_id": run_id, "state": marker["state"], "checkpoint": marker["checkpoint"],
                          "generation_completed": marker.get("latest_completed_generation"), "resumable": False,
                          "code": "GA_CHECKPOINT_INVALID", "error": "Checkpoint compression/integrity check failed."}
            if identity(run_id, templates) != key:
                raise checkpoints.CheckpointError("Checkpoint or inputs changed during verification; retry.",
                                                  "GA_CHECKPOINT_VERIFICATION_CHANGED")
            answer.set_result(result)
        except BaseException as error:
            answer.set_exception(error)
            with _lock:
                _answers.pop(key, None)
            raise
    result = copy.deepcopy(answer.result())
    # Changes during another caller's validation/cache lookup also invalidate it.
    if identity(run_id, templates) != key:
        raise checkpoints.CheckpointError("Checkpoint or inputs changed during verification; retry.",
                                          "GA_CHECKPOINT_VERIFICATION_CHANGED")
    return result
