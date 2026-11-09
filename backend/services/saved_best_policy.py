"""Fail-closed Saved Best admission, separate from GA scoring and RNG.

No trusted consumption/academic-context verifier is configured in deployment.
Neither serialized context metadata nor a source-file digest grants trust.
An integration must supply an independent server verifier, including record
attestation, before this contract can write. It is not institutional approval.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import threading
import time

VERSION = "saved-best-context-v1"
HASHES = {"bundle_fingerprint", "loaded_model_fingerprint", "faculty_fingerprint",
          "subject_fingerprint", "preferences_fingerprint", "scoring_configuration_fingerprint",
          "engine_fingerprint", "constraints_fingerprint"}
LABELS = {"academic_year", "term", "department_id", "dataset_identity",
          "fitness_version", "chromosome_version"}
PROVENANCE_ONLY = {"bundle_fingerprint", "loaded_model_fingerprint"}
_locks = {}
_registry = threading.Lock()


def configured_verifier():
    """Fixed HTTP consumption and institutional context remain unverified."""
    return None


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def context(value):
    if type(value) is not dict or set(value) != HASHES | LABELS | {"version"} or value["version"] != VERSION:
        raise ValueError("SAVED_BEST_CONTEXT_INVALID")
    if any(type(value[k]) is not str or not re.fullmatch("[0-9a-f]{64}", value[k]) for k in HASHES):
        raise ValueError("SAVED_BEST_CONTEXT_INVALID")
    if any(type(value[k]) is not str or not value[k].strip() or len(value[k]) > 256 for k in LABELS):
        raise ValueError("SAVED_BEST_CONTEXT_INVALID")
    return json.loads(canonical(value))


def content(payload):
    if type(payload) is not dict or payload.get("format") != "ccs-ga-chromosome" or type(payload.get("version")) is not int or payload["version"] != 1:
        raise ValueError("SAVED_BEST_PAYLOAD_INVALID")
    score = payload.get("best_fitness")
    if type(score) not in (int, float) or not math.isfinite(score):
        raise ValueError("SAVED_BEST_FITNESS_INVALID")
    keys = payload.get("subject_keys")
    if not isinstance(keys, list) or not keys or any(type(k) is not str or not k for k in keys) or len(keys) != len(set(keys)):
        raise ValueError("SAVED_BEST_PAYLOAD_INVALID")
    if not isinstance(payload.get("schedule"), list) or not payload["schedule"]:
        raise ValueError("SAVED_BEST_PAYLOAD_INVALID")
    return {k: payload[k] for k in ("format", "version", "best_fitness", "subject_keys", "schedule")}


@dataclass(frozen=True)
class Decision:
    classification: str
    reason: str
    updated: bool = False
    payload: dict | None = None


def verify_record(payload, verifier):
    proof = payload.get("saved_best_context")
    if type(proof) is not dict or set(proof) != {"context", "context_fingerprint", "content_fingerprint", "attestation", "storage_policy_fingerprint"}:
        raise ValueError("SAVED_BEST_PROVENANCE_MISSING")
    ctx = context(proof["context"])
    if proof["storage_policy_fingerprint"] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
        raise ValueError("SAVED_BEST_STORAGE_POLICY_CHANGED")
    if proof["context_fingerprint"] != digest(ctx) or proof["content_fingerprint"] != digest(content(payload)):
        raise ValueError("SAVED_BEST_PROVENANCE_INVALID")
    # Hashes alone are not evidence that an optimizer consumed those inputs.
    binding = digest({k: proof[k] for k in ("context_fingerprint", "content_fingerprint", "storage_policy_fingerprint")})
    if verifier.verify(ctx, binding, proof["attestation"]) is not True:
        raise ValueError("SAVED_BEST_ATTESTATION_UNVERIFIED")
    return ctx


@contextmanager
def locked(path):
    with _registry:
        lock = _locks.setdefault(str(path.resolve()), threading.RLock())
    if not lock.acquire(timeout=2):
        raise ValueError("SAVED_BEST_STORAGE_BUSY")
    stream = None
    acquired = False
    try:
        # Target directories must be explicitly prepared by the server owner.
        if not path.parent.is_dir() or path.parent.is_symlink() or path.parent.is_junction() or path.is_symlink():
            raise ValueError("SAVED_BEST_STORAGE_UNVERIFIED")
        lockfile = path.with_name(path.name + ".lock")
        if lockfile.is_symlink() or lockfile.is_junction():
            raise ValueError("SAVED_BEST_STORAGE_UNVERIFIED")
        stream = lockfile.open("a+b")
        if stream.seek(0, 2) == 0:
            stream.write(b"0");stream.flush()
        until = time.monotonic() + 2
        while True:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except OSError:
                if time.monotonic() >= until:
                    raise ValueError("SAVED_BEST_STORAGE_BUSY") from None
                time.sleep(.01)
        yield
    finally:
        if stream is not None:
            if acquired:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            stream.close()
        lock.release()


def consider(path, candidate, verifier=None):
    """Independent server verifier supplies current context and attestations.

    Its guard/snapshot/attest/verify methods must establish actual consumption, scope
    and freshness, including historical record provenance. No HTTP input is a
    verifier. Cross-capture equivalence needs its separate guarded proof.
    The unconfigured path performs no file IO or numeric comparison.
    """
    if verifier is None:
        return Decision("UNVERIFIED", "SAVED_BEST_CONSUMPTION_CONTEXT_UNAVAILABLE")
    try:
        # An institutional integration must establish a coherent validity lease
        # through commit, not just an earlier Boolean authority snapshot.
        with verifier.guard():
            return _consider(path, candidate, verifier)
    except Exception:
        return Decision("UNVERIFIED", "SAVED_BEST_VERIFICATION_OR_STORAGE_FAILED")


def _consider(path, candidate, verifier):
    try:
        current = context(verifier.snapshot())
        candidate = json.loads(canonical(candidate))
        fingerprint = digest(content(candidate))
        proof = dict(context=current, context_fingerprint=digest(current), content_fingerprint=fingerprint,
            storage_policy_fingerprint=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        binding = digest({k: proof[k] for k in ("context_fingerprint", "content_fingerprint", "storage_policy_fingerprint")})
        proof["attestation"] = verifier.attest(current, binding)
        candidate["saved_best_context"] = proof
        verify_record(candidate, verifier)
        raw = canonical(candidate)
        if len(raw) > 64 * 1024 * 1024:
            raise ValueError("SAVED_BEST_RECORD_TOO_LARGE")
        path = Path(path)
        with locked(path):
            # Recheck after locking; a context change cannot race admission.
            if context(verifier.snapshot()) != current:
                return Decision("UNVERIFIED", "SAVED_BEST_CONTEXT_CHANGED")
            verify_record(candidate, verifier)
            if path.exists():
                if path.stat().st_size > 64 * 1024 * 1024:
                    raise ValueError("SAVED_BEST_RECORD_TOO_LARGE")
                previous = json.loads(path.read_bytes())
                old_context = verify_record(previous, verifier)
                comparable = lambda ctx: {k: v for k, v in ctx.items() if k not in PROVENANCE_ONLY}
                if comparable(current) != comparable(old_context) or set(candidate["subject_keys"]) != set(previous["subject_keys"]):
                    return Decision("INCOMPATIBLE", "SAVED_BEST_CONTEXT_MISMATCH")
                if current != old_context:
                    # Bundle/run/time/search metadata can differ without changing
                    # an objective. Only an independent, guarded server proof of
                    # complete input equivalence may establish that distinction.
                    equivalent = getattr(verifier, "equivalent_inputs", None)
                    if equivalent is None or equivalent(current, old_context) is not True:
                        return Decision("UNVERIFIED", "SAVED_BEST_INPUT_EQUIVALENCE_UNESTABLISHED")
                # Original objective is minimization; equal penalties retain the incumbent.
                if candidate["best_fitness"] >= previous["best_fitness"]:
                    return Decision("ELIGIBLE", "SAVED_BEST_NOT_IMPROVED", payload=previous)
            if context(verifier.snapshot()) != current:
                return Decision("UNVERIFIED", "SAVED_BEST_CONTEXT_CHANGED")
            verify_record(candidate, verifier)
            fd, temporary = tempfile.mkstemp(prefix=".saved-best-", suffix=".tmp", dir=path.parent)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(raw);stream.flush();os.fsync(stream.fileno())
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            return Decision("ELIGIBLE", "SAVED_BEST_IMPROVED", True, candidate)
    except (ValueError, TypeError, KeyError, OSError, AttributeError):
        # No payload/exception echo: records may contain private schedule data.
        return Decision("UNVERIFIED", "SAVED_BEST_VERIFICATION_OR_STORAGE_FAILED")
