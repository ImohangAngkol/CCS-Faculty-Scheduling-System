"""Immutable run-start side records, separate from Saved Best/results/checkpoints."""
from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import tempfile
from uuid import UUID

from services import ga_academic_context as academic
from services.ga_history_service import HistoryError
from services.ga_result_compatibility import current_identity

PROVENANCE_DIR = Path(__file__).resolve().parents[1] / "run_provenance_v1"
CONTRACT = "ga-run-start-provenance-v1"
PARAMETERS = ("population_size", "generations", "fresh_chromosomes", "baseline_mode", "mutation_attempts", "max_restarts")
MAX_BYTES = 32768


def fail(code, message):
    raise HistoryError(message, code, 409)


def path_for(run_id):
    try:
        if str(UUID(run_id)) != run_id:
            raise ValueError()
    except (TypeError, ValueError, AttributeError):
        fail("GA_RUN_PROVENANCE_INVALID", "Invalid canonical run identity.")
    return PROVENANCE_DIR / (run_id + ".json")


def configuration(parameters):
    from services.ga_service import run_genetic_algorithm
    signature = inspect.signature(run_genetic_algorithm)
    result = {key: parameters.get(key, signature.parameters[key].default) for key in PARAMETERS}
    if result["baseline_mode"] != "fresh":
        fail("GA_RUN_PROVENANCE_SEED_UNSUPPORTED", "Verified run-start capture supports fresh runs only; saved/uploaded seed provenance needs separate approval.")
    for key in set(PARAMETERS) - {"baseline_mode"}:
        if type(result[key]) is not int or result[key] < (1 if key in {"population_size", "generations", "max_restarts"} else 0):
            fail("GA_RUN_PROVENANCE_INVALID", "Scheduling configuration is invalid.")
    return result


def configuration_fingerprint(inputs, config):
    # Exact existing GenerationMonitor.register_baseline(None) representation.
    return hashlib.sha256(json.dumps({"inputs": inputs, "ga": config, "baseline": None},
                                    sort_keys=True, default=str).encode()).hexdigest()


def begin(control, parameters):
    """Called before GA search, only on a new execution, never on resume/backfill.

    No provider means legacy execution is unchanged, without current eligibility.
    A configured but invalid provider rejects provenance/search, never falls back.
    """
    if parameters.get("resume_state") is not None:
        return None
    identity = current_identity()
    verified = academic.verified_context(identity)
    if verified is None:
        return None
    from services import ga_history_service as history
    if control.latest_completed_generation is not None or (history.directory(control.run_id)/"index.json").exists():
        fail("GA_RUN_PROVENANCE_RETROACTIVE", "Run-start provenance cannot be added to an existing run.")
    config = configuration(parameters)
    if not control.started_at:
        fail("GA_RUN_PROVENANCE_INVALID", "The server must establish run start before provenance capture.")
    payload = {"schema_version": 1, "contract": CONTRACT, "run_id": control.run_id,
        "started_at": control.started_at, "captured_at": datetime.now(timezone.utc).isoformat(),
        "technical_identity": identity, "academic_context": verified.context.model_dump(),
        "context_sha256": verified.context.digest, "verification_reference": verified.verification_reference,
        "verification_issued_at": verified.issued_at, "verification_expires_at": verified.expires_at,
        "configuration": config, "configuration_fingerprint": configuration_fingerprint(identity["input_fingerprint"], config)}
    if current_identity() != identity:
        fail("GA_RUN_PROVENANCE_CHANGED", "Implementation or inputs changed before run-start capture.")
    # Recheck provider lifecycle immediately before commit, without consuming GA RNG.
    fresh = academic.verified_context(identity)
    if fresh is None or fresh.context.digest != verified.context.digest:
        fail("GA_RUN_PROVENANCE_CHANGED", "Academic context changed before run-start capture.")
    body = academic.canonical(payload)
    envelope = academic.canonical({"sha256": hashlib.sha256(body).hexdigest(), "data": payload})
    if len(envelope) > MAX_BYTES:
        fail("GA_RUN_PROVENANCE_INVALID", "Run-start provenance exceeds its bounded record size.")
    target = path_for(control.run_id)
    if PROVENANCE_DIR.is_symlink():
        fail("GA_RUN_PROVENANCE_INVALID", "Provenance storage must not be a directory alias.")
    PROVENANCE_DIR.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".run-start-", suffix=".tmp", dir=PROVENANCE_DIR)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(envelope)
            stream.flush()
            os.fsync(stream.fileno())
        # Publish a complete file atomically with NO replacement of an existing name.
        try:
            os.link(temporary, target)
        except FileExistsError as error:
            fail("GA_RUN_PROVENANCE_EXISTS", "Immutable run-start provenance already exists; no overwrite was attempted.")
        except OSError as error:
            raise HistoryError("Atomic immutable provenance storage is unavailable; no GA search was started.",
                               "GA_RUN_PROVENANCE_UNAVAILABLE", 503) from error
        if os.name != "nt":
            directory = os.open(PROVENANCE_DIR, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)  # Only this newly owned temporary file.
    return payload


def read(run_id):
    target = path_for(run_id)
    try:
        if PROVENANCE_DIR.is_symlink() or target.is_symlink() or target.resolve().parent != PROVENANCE_DIR.resolve():
            raise ValueError()
        with target.open("rb") as stream:
            raw = stream.read(MAX_BYTES+1)
        if len(raw) > MAX_BYTES:
            raise ValueError()
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError()
                result[key] = value
            return result
        document = json.loads(raw, object_pairs_hook=pairs)
        data = document["data"]
        if hashlib.sha256(academic.canonical(data)).hexdigest() != document["sha256"]:
            raise ValueError()
        if type(data["schema_version"]) is not int or data["schema_version"] != 1 or data["contract"] != CONTRACT or data["run_id"] != run_id:
            raise ValueError()
        context = academic.AcademicContext.model_validate(data["academic_context"])
        if context.digest != data["context_sha256"]:
            raise ValueError()
        if data["configuration"] != configuration(data["configuration"]):
            raise ValueError()
        if configuration_fingerprint(context.input_fingerprint, data["configuration"]) != data["configuration_fingerprint"]:
            raise ValueError()
        for field in ("started_at", "captured_at", "verification_issued_at", "verification_expires_at"):
            if datetime.fromisoformat(data[field]).tzinfo is None:
                raise ValueError()
        technical = data["technical_identity"]
        if not isinstance(technical, dict) or technical.get("input_fingerprint") != context.input_fingerprint:
            raise ValueError()
        if datetime.fromisoformat(data["captured_at"]) < datetime.fromisoformat(data["started_at"]):
            raise ValueError()
        if not datetime.fromisoformat(data["verification_issued_at"]) <= datetime.fromisoformat(data["captured_at"]) < datetime.fromisoformat(data["verification_expires_at"]):
            raise ValueError()
        return data
    except FileNotFoundError:
        return None
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise HistoryError("Run-start provenance is unreadable or inconsistent; current compatibility is unknown.",
                           "GA_RUN_PROVENANCE_INVALID", 422) from error
