"""Immutable *captured* input foundation, not an installed V1 consumption path.

No API, filesystem store, global rebinding, RNG operation or worker. The private
canonical bytes may contain academic records: never put them in logs/evidence.
Callers must own/quiesce the source graph during capture. This implementation
cannot prove that the legacy optimizer consumes it and cannot issue VERIFIED.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import re
from uuid import UUID

CONTRACT = "ga-captured-input-bundle-v1"
CODEC = "checkpoint-graph-v1-observed-order"
MAX_BYTES = 16 * 1024 * 1024
MAX_NODES = 100_000
PARAMETERS = {"population_size", "generations", "fresh_chromosomes", "baseline_mode", "mutation_attempts", "max_restarts"}
FIELDS = {"contract", "codec", "run_id", "captured_at", "academic_context_reference", "source_identities", "configuration", "configuration_fingerprint", "capture_implementation_fingerprint", "graph", "verification_status"}
ROOT_FIELDS = {"templates", "fallback_templates", "legacy_preferences", "scoring_context", "seed"}


class BundleError(ValueError):
    def __init__(self, code="GA_INPUT_BUNDLE_INVALID"):
        self.code = code
        super().__init__(code)  # Never interpolate source values or private records.


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def identifier(value):
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise BundleError("GA_INPUT_BUNDLE_RUN_MISMATCH")


def hash_value(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def unique_object(items):
    result = {}
    for key, value in items:
        if key in result:
            raise BundleError()
        result[key] = value
    return result


def validate_document(doc):
    from services import ga_checkpoint_service as codec
    if type(doc) is not dict or set(doc) != FIELDS or doc["contract"] != CONTRACT or doc["codec"] != CODEC or doc["verification_status"] != "UNVERIFIED":
        raise BundleError()
    identifier(doc["run_id"])
    stamp = datetime.fromisoformat(doc["captured_at"])
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise BundleError()
    if doc["academic_context_reference"] is not None and not hash_value(doc["academic_context_reference"]):
        raise BundleError()
    sources = doc["source_identities"]
    if type(sources) is not dict or not {"dataset", "engine", "loader", "transformation"} <= set(sources) or len(sources) > 32:
        raise BundleError()
    if any(not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", key) or not hash_value(value) for key, value in sources.items()):
        raise BundleError()
    config = doc["configuration"]
    if type(config) is not dict or set(config) != PARAMETERS or config["baseline_mode"] not in {"fresh", "saved", "uploaded"}:
        raise BundleError()
    if any(type(config[k]) is not int or config[k] < 0 for k in PARAMETERS - {"baseline_mode"}):
        raise BundleError()
    if doc["configuration_fingerprint"] != digest(canonical(config)) or not hash_value(doc["capture_implementation_fingerprint"]):
        raise BundleError()
    graph = doc["graph"]
    if type(graph) is not dict or set(graph) != {"root", "nodes"} or type(graph["nodes"]) is not list or not 0 < len(graph["nodes"]) <= MAX_NODES:
        raise BundleError()
    nodes = graph["nodes"]
    def value(item):
        if item is None or type(item) in (str, int, bool):
            return
        if type(item) is float:
            canonical(item)  # Reject non-finite bare JSON numbers.
            return
        if type(item) is not dict:
            raise BundleError()
        if set(item) == {"scalar"} and item["scalar"] in {"NA", "nan", "inf", "-inf"}:
            return
        if set(item) != {"ref"} or type(item["ref"]) is not int or not 0 <= item["ref"] < len(nodes):
            raise BundleError()
    value(graph["root"])
    for node in nodes:
        if type(node) is not dict or set(node) != {"kind", "items"} or type(node["items"]) is not list:
            raise BundleError()
        kind = node["kind"]
        if kind in {"list", "tuple", "set"}:
            for item in node["items"]:
                value(item)
        elif kind == "dict" or kind in codec.CLASSES:
            keys = set()
            for pair in node["items"]:
                if type(pair) is not list or len(pair) != 2:
                    raise BundleError()
                key, item = pair
                if kind == "dict":
                    value(key)
                elif type(key) is not str or not key.isidentifier() or key.startswith("_"):
                    raise BundleError()
                marker = canonical(key)
                if marker in keys:
                    raise BundleError()
                keys.add(marker)
                value(item)
        else:
            raise BundleError()
    restored = codec.decode_graph(graph)
    if type(restored) is not dict or set(restored) != ROOT_FIELDS:
        raise BundleError()
    for key in ("templates", "fallback_templates"):
        if type(restored[key]) is not tuple or len(restored[key]) != 3 or any(type(items) is not list for items in restored[key]):
            raise BundleError()
        for items, model in zip(restored[key], (codec.CLASSES["Subject"], codec.CLASSES["Faculty"], codec.CLASSES["Room"])):
            if any(type(item) is not model for item in items):
                raise BundleError()
    context = restored["scoring_context"]
    if type(context) is not dict or set(context) != {"preference_scoring_version", "settings", "preferences", "system_faculty", "input_fingerprint"}:
        raise BundleError()
    if type(context["preference_scoring_version"]) is not int or context["preference_scoring_version"] not in {1, 2} or context["input_fingerprint"] != sources["dataset"]:
        raise BundleError()
    if type(context["settings"]) is not dict or type(context["preferences"]) is not dict or type(context["system_faculty"]) is not list or any(type(f) is not codec.CLASSES["Faculty"] for f in context["system_faculty"]):
        raise BundleError()
    frame = codec.dataframe_from_state(restored["legacy_preferences"])
    seed = restored["seed"]
    if (config["baseline_mode"] == "fresh" and seed is not None) or (config["baseline_mode"] != "fresh" and (type(seed) is not dict or type(seed.get("schedule")) is not list)):
        raise BundleError()
    return restored, frame


@dataclass(frozen=True, slots=True)
class InputBundle:
    """Only immutable bytes/strings; no retained source graph or mutable view."""
    run_id: str
    fingerprint: str
    _raw: bytes = field(repr=False)

    @classmethod
    def from_bytes(cls, raw, expected_run_id, expected_fingerprint):
        try:
            identifier(expected_run_id)
            if type(raw) is not bytes or len(raw) > MAX_BYTES or not hash_value(expected_fingerprint) or digest(raw) != expected_fingerprint:
                raise BundleError()
            doc = json.loads(raw, object_pairs_hook=unique_object)
            if doc["run_id"] != expected_run_id:
                raise BundleError("GA_INPUT_BUNDLE_RUN_MISMATCH")
            if canonical(doc) != raw:
                raise BundleError()
            validate_document(doc)
            return cls(expected_run_id, expected_fingerprint, raw)
        except BundleError:
            raise
        except (ValueError, TypeError, KeyError, AttributeError, IndexError, RecursionError, OverflowError):
            raise BundleError() from None

    def materialize(self, expected_run_id):
        """A new private mutable working graph per call, not proof of GA reads."""
        if self.run_id != expected_run_id:
            raise BundleError("GA_INPUT_BUNDLE_RUN_MISMATCH")
        checked = self.from_bytes(self._raw, expected_run_id, self.fingerprint)
        doc = json.loads(checked._raw)
        restored, frame = validate_document(doc)
        return {**restored, "legacy_preferences": frame, "configuration": doc["configuration"]}

    def qualification(self, expected_run_id):
        if self.run_id != expected_run_id:
            raise BundleError("GA_INPUT_BUNDLE_RUN_MISMATCH")
        self.from_bytes(self._raw, expected_run_id, self.fingerprint)
        return {"contract": CONTRACT, "run_id": self.run_id, "bundle_fingerprint": self.fingerprint,
                "stage": "CAPTURED_INPUTS", "optimizer_consumption": "NOT_ESTABLISHED",
                "verification_status": "UNVERIFIED", "eligible_for_current": False,
                "institutional_authorization": "NOT_ESTABLISHED",
                "reasons": ["CONSUMPTION_BOUNDARY_NOT_INSTALLED", "SOURCE_CAPTURE_NOT_PROVEN_ATOMIC", "LEGACY_CHECKPOINT_HAS_NO_BUNDLE_BINDING"]}


def capture(*, run_id, templates, fallback_templates, legacy_preferences, scoring_context, configuration, source_identities, seed=None, academic_context_reference=None, captured_at=None):
    """Internal foundation API. Caller-supplied hashes are observations, not trust.

    No source-file loading occurs here. A caller must provide all transformed
    models and scoring values under exclusive ownership; production has no such
    installed loader boundary. Node/byte caps are checked after encoding and
    are not a proven peak-allocation bound. Order is preserved, not normalized.
    """
    from pathlib import Path
    from services import ga_checkpoint_service as codec
    try:
        graph = codec.encode_graph({"templates": templates, "fallback_templates": fallback_templates,
            "legacy_preferences": codec.dataframe_to_state(legacy_preferences), "scoring_context": scoring_context, "seed": seed})
        implementation = digest(Path(__file__).read_bytes() + Path(codec.__file__).read_bytes())
        doc = {"contract": CONTRACT, "codec": CODEC, "run_id": run_id,
            "captured_at": captured_at or datetime.now(timezone.utc).isoformat(),
            "academic_context_reference": academic_context_reference, "source_identities": source_identities,
            "configuration": configuration, "configuration_fingerprint": digest(canonical(configuration)),
            "capture_implementation_fingerprint": implementation, "graph": graph, "verification_status": "UNVERIFIED"}
        raw = canonical(doc)
        return InputBundle.from_bytes(raw, run_id, digest(raw))
    except BundleError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, IndexError, RecursionError, OverflowError):
        raise BundleError() from None


def require_consumption_boundary(bundle, expected_run_id):
    bundle.qualification(expected_run_id)
    raise BundleError("GA_BUNDLE_CONSUMPTION_NOT_INSTALLED")
