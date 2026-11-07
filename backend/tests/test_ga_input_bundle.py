"""Fictional immutable-capture qualification. No V1 bundle consumer is installed."""
import copy
from dataclasses import FrozenInstanceError
from concurrent.futures import ThreadPoolExecutor
import json
import random
import pytest
from sqlalchemy.engine import Engine
from services import ga_input_bundle as bundle

RUN = "00000000-0000-4000-8000-000000000701"
OTHER = "00000000-0000-4000-8000-000000000702"
STAMP = "2026-11-05T00:00:00+00:00"


@pytest.fixture
def inputs(monkeypatch):
    from tests.d10.support import templates, preferences
    monkeypatch.setattr(Engine, "connect", lambda *_a, **_k: pytest.fail("No database access permitted"))
    models = templates(compact=True)
    return dict(run_id=RUN, templates=models, fallback_templates=models,
        legacy_preferences=preferences(), scoring_context={"preference_scoring_version": 2,
            "settings": {"underload_penalty": 25}, "preferences": {},
            "system_faculty": models[1], "input_fingerprint": "a" * 64},
        configuration=dict(population_size=2, generations=2, fresh_chromosomes=0,
            baseline_mode="fresh", mutation_attempts=1, max_restarts=5),
        source_identities=dict(dataset="a" * 64, engine="b" * 64, loader="c" * 64, transformation="d" * 64),
        captured_at=STAMP)


def forged(original, change):
    doc = json.loads(original._raw)
    change(doc)
    raw = bundle.canonical(doc)
    return raw, bundle.digest(raw)


def test_canonical_capture_is_repeatable_and_consumes_no_rng(inputs):
    before = random.getstate()
    a = bundle.capture(**inputs); b = bundle.capture(**inputs)
    assert a == b and a.fingerprint == b.fingerprint and random.getstate() == before
    assert bundle.InputBundle.from_bytes(a._raw, RUN, a.fingerprint) == a
    assert "Subject" not in repr(a) and "Fictional" not in repr(a)
    with pytest.raises(FrozenInstanceError):a.fingerprint = "e" * 64


def test_private_workspaces_preserve_internal_aliases_without_cross_run_sharing(inputs):
    a = bundle.capture(**inputs); first = a.materialize(RUN); second = a.materialize(RUN)
    assert first["templates"] is first["fallback_templates"]
    assert first["templates"][1] is first["scoring_context"]["system_faculty"]
    assert first["templates"][0][0] is not second["templates"][0][0]
    first["templates"][0][0].section = "Fictional changed section"
    first["configuration"]["generations"] = 9
    assert second["configuration"]["generations"] == 2 and a.materialize(RUN)["configuration"]["generations"] == 2


@pytest.mark.parametrize("change", ["preferences", "weights", "faculty", "subjects", "rooms", "configuration", "legacy_frame", "cached_fallback"])
def test_subsequent_source_changes_do_not_mutate_capture(inputs, change):
    captured = bundle.capture(**inputs); fingerprint = captured.fingerprint
    before = captured.materialize(RUN)
    if change == "preferences":inputs["scoring_context"]["preferences"]["990001"] = {"style": "fictional"}
    elif change == "weights":inputs["scoring_context"]["settings"]["underload_penalty"] = 77
    elif change == "faculty":inputs["templates"][1][0].admin_load = 0
    elif change == "subjects":inputs["templates"][0][0].section = "Fictional changed section"
    elif change == "rooms":inputs["templates"][2][0].name = "Fictional alternate room"
    elif change == "configuration":inputs["configuration"]["generations"] = 8
    elif change == "legacy_frame":inputs["legacy_preferences"].iloc[0, 0] = 990009
    else:inputs["fallback_templates"] = copy.deepcopy(inputs["templates"])
    assert captured.fingerprint == fingerprint
    again = captured.materialize(RUN)
    from services.ga_checkpoint_service import encode_graph, dataframe_to_state
    for state in (before, again):state["legacy_preferences"] = dataframe_to_state(state["legacy_preferences"])
    assert encode_graph(before) == encode_graph(again)
    assert bundle.capture(**inputs).fingerprint != fingerprint


def test_concurrent_materializations_are_separate_and_cross_run_reuse_fails(inputs):
    a = bundle.capture(**inputs)
    with ThreadPoolExecutor(max_workers=4) as pool:
        copies = list(pool.map(lambda _: a.materialize(RUN), range(8)))
    assert len({id(w["templates"][1][0]) for w in copies}) == 8
    for method in (a.materialize, a.qualification):
        with pytest.raises(bundle.BundleError, match="RUN_MISMATCH"):method(OTHER)
    raw, digest = forged(a, lambda doc: doc.update(run_id=OTHER))
    with pytest.raises(bundle.BundleError, match="RUN_MISMATCH"):bundle.InputBundle.from_bytes(raw, RUN, digest)
    fake = bundle.InputBundle(OTHER, a.fingerprint, a._raw)
    with pytest.raises(bundle.BundleError):fake.qualification(RUN)


@pytest.mark.parametrize("method", ["materialize", "qualification"])
def test_tampering_or_missing_bundle_is_rejected(inputs, method):
    a = bundle.capture(**inputs)
    damaged = bundle.InputBundle(RUN, a.fingerprint, a._raw[:-1])
    with pytest.raises(bundle.BundleError):getattr(damaged, method)(RUN)
    with pytest.raises(bundle.BundleError):bundle.InputBundle.from_bytes(None, RUN, a.fingerprint)


@pytest.mark.parametrize("change", [
    lambda d: d.update(contract="unsupported"), lambda d: d.update(verification_status="VERIFIED"),
    lambda d: d.update(unknown="ignored"), lambda d: d.pop("graph"),
    lambda d: d.update(captured_at="2026-11-05"), lambda d: d.update(academic_context_reference="fake-term"),
    lambda d: d["configuration"].update(generations=True),
    lambda d: d["configuration"].update(generations=3),
    lambda d: d["source_identities"].update(engine="not-a-hash"),
    lambda d: d["graph"].update(root={"ref": 9999999}),
    lambda d: d["graph"]["nodes"][0].update(kind="ExecutableObject"),
    lambda d: d["graph"]["nodes"][0].update(extra="ignored"),
    lambda d: d["graph"]["nodes"][0]["items"].append(d["graph"]["nodes"][0]["items"][0]),
])
def test_rehashed_malformed_or_forged_claims_fail_closed(inputs, change):
    a = bundle.capture(**inputs); raw, digest = forged(a, change)
    with pytest.raises(bundle.BundleError):bundle.InputBundle.from_bytes(raw, RUN, digest)


def test_duplicate_json_noncanonical_json_and_size_limits(inputs, monkeypatch):
    a = bundle.capture(**inputs)
    duplicate = a._raw[:-1] + b',"run_id":"' + RUN.encode() + b'"}'
    for raw in (duplicate, b' ' + a._raw):
        with pytest.raises(bundle.BundleError):bundle.InputBundle.from_bytes(raw, RUN, bundle.digest(raw))
    monkeypatch.setattr(bundle, "MAX_BYTES", len(a._raw) - 1)
    with pytest.raises(bundle.BundleError):bundle.InputBundle.from_bytes(a._raw, RUN, a.fingerprint)


def test_node_limit_and_unsupported_objects_fail_without_echoing_values(inputs, monkeypatch):
    monkeypatch.setattr(bundle, "MAX_NODES", 1)
    with pytest.raises(bundle.BundleError):bundle.capture(**inputs)
    monkeypatch.setattr(bundle, "MAX_NODES", 100_000)
    inputs["seed"] = object()
    with pytest.raises(bundle.BundleError) as error:bundle.capture(**inputs)
    assert str(error.value) == "GA_INPUT_BUNDLE_INVALID"


@pytest.mark.parametrize("mode", ["saved", "uploaded"])
def test_seed_is_required_and_captured_without_loading_any_store(inputs, mode):
    inputs["configuration"]["baseline_mode"] = mode
    with pytest.raises(bundle.BundleError):bundle.capture(**inputs)
    inputs["seed"] = {"schedule": [], "subject_keys": []}
    a = bundle.capture(**inputs)
    inputs["seed"]["schedule"].append({"subject": "Fictional later seed"})
    assert a.materialize(RUN)["seed"]["schedule"] == []


def test_capture_is_unverified_and_cannot_start_optimize_or_publish(inputs, monkeypatch):
    from services import chromosome_service, ga_checkpoint_service
    def forbidden(*_a, **_k):pytest.fail("Foundation attempted persistence or scoring")
    monkeypatch.setattr(chromosome_service, "save_best_if_better", forbidden)
    monkeypatch.setattr(ga_checkpoint_service, "save_checkpoint", forbidden)
    a = bundle.capture(**inputs); q = a.qualification(RUN)
    assert q["stage"] == "CAPTURED_INPUTS" and q["verification_status"] == "UNVERIFIED" and not q["eligible_for_current"]
    assert q["optimizer_consumption"] == "NOT_ESTABLISHED"
    with pytest.raises(bundle.BundleError, match="CONSUMPTION_NOT_INSTALLED"):bundle.require_consumption_boundary(a, RUN)


def test_existing_checkpoint_contract_has_no_bundle_consumer_or_version_bridge():
    import inspect
    from services import ga_service, ga_checkpoint_service
    assert "globals()[name]" in inspect.getsource(ga_service.run_genetic_algorithm)
    assert "input_bundle" not in inspect.signature(ga_service.run_genetic_algorithm).parameters
    source = inspect.getsource(ga_checkpoint_service.load_checkpoint)
    assert "GA_CHECKPOINT_INPUT_CHANGED" in source and "engine_fingerprint" in source
    assert ga_checkpoint_service.ENGINE_VERSION == "ga-continuation-v1"
