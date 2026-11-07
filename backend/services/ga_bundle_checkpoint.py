"""New in-memory checkpoint envelope. Never reads/writes legacy artifacts.

The caller must retain the expected tip hash in trusted server metadata. A
checksum is not authentication against replacement of both bytes and that pin.
Durable stores/worker ownership are intentionally outside this synchronous SDK.
"""
import copy
import json
from services.ga_input_bundle import BundleError, canonical, digest, unique_object, hash_value

CONTRACT = "ga-bundle-checkpoint-v1"
MAX_BYTES = 64 * 1024 * 1024
FIELDS = {"contract", "run_id", "bundle_fingerprint", "optimizer_version", "optimizer_fingerprint",
    "configuration_fingerprint", "scoring_fingerprint", "generation", "sequence", "parent_fingerprint", "graph"}


def semantic_graph_fingerprint(value):
    from services.ga_checkpoint_service import encode_graph
    graph = encode_graph(value)
    # Identity comparison only. Working objects and their iteration order are
    # untouched. Captured bundle bytes retain their exact observed ordering.
    for node in graph["nodes"]:
        if node["kind"] == "set":
            if any(isinstance(v, dict) for v in node["items"]):
                raise BundleError("GA_BUNDLE_UNSUPPORTED_SET_IDENTITY")
            node["items"].sort(key=canonical)
    return digest(canonical(graph))


def encode(state, *, run_id, bundle_fingerprint, optimizer_version, optimizer_fingerprint,
           configuration_fingerprint, scoring_fingerprint, parent_fingerprint, sequence):
    from services.ga_checkpoint_service import encode_graph
    doc = dict(contract=CONTRACT, run_id=run_id, bundle_fingerprint=bundle_fingerprint,
        optimizer_version=optimizer_version, optimizer_fingerprint=optimizer_fingerprint,
        configuration_fingerprint=configuration_fingerprint, scoring_fingerprint=scoring_fingerprint,
        generation=state["generation_completed"], sequence=sequence,
        parent_fingerprint=parent_fingerprint, graph=encode_graph(state))
    raw = canonical(doc)
    if len(raw) > MAX_BYTES:raise BundleError("GA_BUNDLE_CHECKPOINT_LIMIT")
    return raw


def decode(raw, *, expected_fingerprint, run_id, bundle_fingerprint, optimizer_version,
           optimizer_fingerprint, configuration_fingerprint, scoring_fingerprint,
           expected_sequence, expected_parent):
    from services.ga_checkpoint_service import decode_graph
    try:
        if type(expected_sequence) is not int or expected_sequence < 1 or (expected_parent is not None and not hash_value(expected_parent)):
            raise BundleError("GA_BUNDLE_CHECKPOINT_BINDING")
        if type(raw) is not bytes or len(raw) > MAX_BYTES or digest(raw) != expected_fingerprint:
            raise BundleError("GA_BUNDLE_CHECKPOINT_INTEGRITY")
        doc = json.loads(raw, object_pairs_hook=unique_object)
        if type(doc) is not dict or set(doc) != FIELDS or canonical(doc) != raw:
            raise BundleError("GA_BUNDLE_CHECKPOINT_INVALID")
        expected = dict(contract=CONTRACT, run_id=run_id, bundle_fingerprint=bundle_fingerprint,
            optimizer_version=optimizer_version, optimizer_fingerprint=optimizer_fingerprint,
            configuration_fingerprint=configuration_fingerprint, scoring_fingerprint=scoring_fingerprint,
            sequence=expected_sequence, parent_fingerprint=expected_parent)
        if any(doc[k] != v or type(doc[k]) is not type(v) for k, v in expected.items()):
            raise BundleError("GA_BUNDLE_CHECKPOINT_BINDING")
        graph = doc["graph"]
        if type(graph) is not dict or set(graph) != {"root", "nodes"} or type(graph["nodes"]) is not list or len(graph["nodes"]) > 500_000:
            raise BundleError("GA_BUNDLE_CHECKPOINT_INVALID")
        state = decode_graph(graph)
        if type(doc["generation"]) is not int or doc["generation"] != state["generation_completed"]:
            raise BundleError("GA_BUNDLE_CHECKPOINT_BINDING")
        if semantic_graph_fingerprint(state["scoring_inputs"]) != scoring_fingerprint:
            raise BundleError("GA_BUNDLE_CHECKPOINT_BINDING")
        return state
    except BundleError:
        raise
    except (ValueError, KeyError, TypeError, AttributeError, IndexError, RecursionError, OverflowError):
        raise BundleError("GA_BUNDLE_CHECKPOINT_INVALID") from None
