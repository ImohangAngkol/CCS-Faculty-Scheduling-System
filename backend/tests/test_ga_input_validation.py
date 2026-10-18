"""Admission tests use temporary inputs and never start a production GA."""
import copy
import importlib
import json
import random

import pytest
from fastapi.testclient import TestClient

from main import app
from services import ga_service, chromosome_service
from services.ga_control_service import RunRegistry, RunControl
from tests.test_ga_api_crossover import small_population
from tests.test_ga_monitoring import bounded_run

router = importlib.import_module("routers.genetic_algorithm")
fitness = importlib.import_module("genetic_algorithm.operators.FitnessFunction")


@pytest.fixture
def admission(monkeypatch, tmp_path):
    preferences = tmp_path / "preferences.json"
    settings = tmp_path / "settings.json"
    preferences.write_text("[]", encoding="utf-8")
    settings.write_text("{}", encoding="utf-8")
    for module, name, path in (
        (ga_service, "FACULTY_PREFERENCES_FILE", preferences),
        (fitness, "PREFERENCE_FILE", preferences),
        (ga_service, "GA_SETTINGS_FILE", settings),
        (fitness, "GA_SETTINGS_FILE", settings),
    ):
        monkeypatch.setattr(module, name, path)
    monkeypatch.setattr(router, "_run_registry", RunRegistry())
    preserved = tmp_path / "preserved"
    preserved.mkdir()
    for owner, name, filename in (
        (router, "LATEST_RESULT_FILE", "latest.json"),
        (chromosome_service, "BEST_CHROMOSOME_PATH", "best.json"),
        (chromosome_service, "UPLOADED_CHROMOSOME_PATH", "uploaded.json"),
    ):
        path = preserved / filename
        path.write_bytes(b"existing-artifact-sentinel")
        monkeypatch.setattr(owner, name, path)
    return preferences, settings, tmp_path


@pytest.mark.parametrize("endpoint", ["generate", "run", "stream"])
@pytest.mark.parametrize("which,content", [
    ("preferences", "{broken"),
    ("preferences", "{}"),
    ("preferences", "null"),
    ("preferences", "\ufeff[]"),
    ("preferences", '[{"faculty_code":true}]'),
    ("preferences", '[{"faculty_code":0,"subject_importance":-1}]'),
    ("preferences", '[{"faculty_code":0},{"faculty_code":0}]'),
    ("preferences", '[{"faculty_code":0,"use_day_preference":"false"}]'),
    ("preferences", '[{"faculty_code":0,"subject_importance":NaN}]'),
    ("preferences", '[{"faculty_code":0,"faculty_code":1}]'),
    ("settings", "{broken"),
    ("settings", "[]"),
    ("settings", "null"),
    ("settings", '{"subject_penalty":-1}'),
    ("settings", '{"gap_penalty":"10"}'),
    ("settings", '{"workload_step_units":0}'),
    ("settings", '{"unsupported_parameter":10}'),
])
def test_bad_inputs_fail_before_admission_without_writes(admission, monkeypatch, endpoint, which, content):
    preferences, settings, folder = admission
    (preferences if which == "preferences" else settings).write_text(content, encoding="utf-8")
    calls = []
    monkeypatch.setattr(router, "generate_schedule", lambda **kw: calls.append("generate"))
    monkeypatch.setattr(router, "run_genetic_algorithm", lambda **kw: calls.append("run"))
    before = {p: p.read_bytes() for p in folder.rglob("*") if p.is_file()}
    rng = random.getstate()
    with TestClient(app) as client:
        response = client.post(f"/api/ga/{endpoint}", params={"population_size": 2, "generations": 1})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "GA_INPUT_INVALID"
    assert calls == [] and router._run_registry.active() is None
    assert not router._ga_execution_lock.locked()
    assert before == {p: p.read_bytes() for p in folder.rglob("*") if p.is_file()}
    assert random.getstate() == rng


@pytest.mark.parametrize("missing", ["preferences", "settings", "both"])
def test_missing_inputs_keep_existing_defaults(admission, missing):
    from services.ga_input_validation_service import validate_ga_inputs
    preferences, settings, _ = admission
    for name, path in (("preferences", preferences), ("settings", settings)):
        if missing in (name, "both"):
            path.unlink()
    before = random.getstate()
    validate_ga_inputs()
    assert random.getstate() == before
    if missing in ("preferences", "both"): assert not preferences.exists()
    if missing in ("settings", "both"): assert not settings.exists()


def test_valid_inputs_are_observational_and_do_not_fill_defaults(admission):
    from services.ga_input_validation_service import validate_ga_inputs
    preferences, settings, _ = admission
    preferences.write_text('[{"faculty_code":0,"use_day_preference":false}]', encoding="utf-8")
    settings.write_text(json.dumps(ga_service.GASetting().to_dict()), encoding="utf-8")
    original = preferences.read_bytes(), settings.read_bytes(), random.getstate()
    validate_ga_inputs()
    assert (preferences.read_bytes(), settings.read_bytes(), random.getstate()) == original


@pytest.mark.parametrize("endpoint", ["generate", "run", "stream"])
@pytest.mark.parametrize("role,expected", [("anonymous", 401), ("faculty", 403)])
def test_authentication_precedes_input_diagnostics(admission, monkeypatch, endpoint, role, expected):
    from services.preference_authorization import current_principal, PreferencePrincipal
    preferences, _, _ = admission
    preferences.write_text("{broken", encoding="utf-8")
    if role == "anonymous":
        monkeypatch.delitem(app.dependency_overrides, current_principal)
    else:
        monkeypatch.setitem(app.dependency_overrides, current_principal, lambda: PreferencePrincipal("faculty"))
    with TestClient(app) as client:
        response = client.post(f"/api/ga/{endpoint}")
    assert response.status_code == expected
    assert "GA_INPUT" not in response.text
    assert router._run_registry.active() is None


def test_unreadable_file_is_not_a_missing_default(admission, monkeypatch):
    from pathlib import Path
    from fastapi import HTTPException
    from services.ga_input_validation_service import validate_ga_inputs
    preferences, _, _ = admission
    original = Path.read_text
    def denied(path, *args, **kwargs):
        if path == preferences:
            raise PermissionError("private details must not be returned")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", denied)
    with pytest.raises(HTTPException) as error:
        validate_ga_inputs()
    assert error.value.status_code == 503
    assert error.value.detail["code"] == "GA_INPUT_UNAVAILABLE"
    assert "private details" not in str(error.value.detail)


def test_corruption_between_admission_and_worker_is_rechecked(admission, monkeypatch):
    from fastapi import HTTPException
    preferences, _, _ = admission
    control = RunControl()
    preferences.write_text("{broken", encoding="utf-8")
    called = []
    monkeypatch.setattr(router, "run_genetic_algorithm", lambda **kw: called.append(True))
    with pytest.raises(HTTPException):
        router._execute_with_history(control)
    assert not called


def test_resume_rejects_bad_current_inputs_without_changing_paused_run(admission):
    from fastapi import HTTPException
    preferences, _, _ = admission
    control = RunControl()
    control.state = "PAUSED"
    control.execution_active = False
    control.ended_clock = control.started_clock
    original = copy.deepcopy(control.snapshot())
    preferences.write_text("{broken", encoding="utf-8")
    with pytest.raises(HTTPException) as error:
        router._launch_resume(control)
    assert error.value.status_code == 503
    assert control.snapshot() == original
    assert not router._ga_execution_lock.locked()


def test_valid_admission_keeps_seeded_rng_scores_and_fitness_call_counts(admission, bounded_run, monkeypatch):
    from services.ga_input_validation_service import validate_ga_inputs
    calls = []
    original = ga_service.faculty_preference_fitness
    def counted(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)
    monkeypatch.setattr(ga_service, "faculty_preference_fitness", counted)
    before = random.getstate()
    try:
        random.seed(417)
        plain = ga_service.run_genetic_algorithm(3, 1, 1)
        plain_rng, plain_calls = random.getstate(), len(calls)
        calls.clear()
        random.seed(417)
        validate_ga_inputs()
        checked = ga_service.run_genetic_algorithm(3, 1, 1)
        assert random.getstate() == plain_rng
        assert len(calls) == plain_calls
        for field in ("schedule", "best_fitness", "fitness_breakdown", "faculty_analysis", "history"):
            assert checked[field] == plain[field]
    finally:
        random.setstate(before)
