"""Roadmap audit reproductions; no institutional files or workers are changed."""
import json
import random
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from main import app
from routers import preferences
from services.preference_authorization import current_principal, PreferencePrincipal
from genetic_algorithm.operators.FitnessFunction import _score_exact_subject_schedule_blocks


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(preferences, "PREFERENCE_FILE", tmp_path / "preferences.json")
    monkeypatch.setattr(preferences, "GA_SETTINGS_FILE", tmp_path / "settings.json")
    with TestClient(app) as instance:
        yield instance


@pytest.mark.parametrize("endpoint,file_attribute", [
    ("/preferences/0", "PREFERENCE_FILE"), ("/preferences/ga-settings", "GA_SETTINGS_FILE"),
])
def test_default_reads_do_not_create_files(client, endpoint, file_attribute):
    state = random.getstate()
    response = client.get(endpoint)
    assert response.status_code == 200, response.text
    assert client.get(endpoint).json() == response.json()
    assert not getattr(preferences, file_attribute).exists()
    assert random.getstate() == state


def test_reading_missing_faculty_preserves_existing_preferences(client):
    preferences.PREFERENCE_FILE.write_text('[{"faculty_code": 1}]', encoding="utf-8")
    before = preferences.PREFERENCE_FILE.read_bytes()
    assert client.get("/preferences/0").status_code == 200
    assert preferences.PREFERENCE_FILE.read_bytes() == before


def test_explicit_save_still_persists_defaults(client):
    payload = client.get("/preferences/0").json()
    payload.pop("faculty_code")
    app.dependency_overrides[current_principal] = lambda: PreferencePrincipal("admin")
    try:
        response = client.put("/preferences/0", json=payload)
    finally:
        app.dependency_overrides.pop(current_principal, None)
    assert response.status_code == 200, response.text
    assert json.loads(preferences.PREFERENCE_FILE.read_text(encoding="utf-8"))[0] == response.json()


def test_readonly_metadata_and_openapi_expose_actual_capabilities(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    faculty = client.get("/api/faculty/").json()["data"]
    assert len(faculty) == 11
    assert all(row["instructor_type"] == "optimization_faculty" for row in faculty)
    assert client.get("/api/subjects/available").status_code == 200
    paths = app.openapi()["paths"]
    assert "post" not in paths["/api/faculty/"]
    assert "/api/rooms" not in paths
    assert "/api/ga/fitness-analysis/latest" in paths
    assert client.get("/api/rooms").status_code == 404


def test_anonymous_preference_writes_are_rejected(client):
    response = client.put("/preferences/0", json={})
    assert response.status_code == 401
    assert not preferences.PREFERENCE_FILE.exists()
    assert client.get("/preferences/0").status_code == 200
    assert not app.openapi().get("components", {}).get("securitySchemes")


def test_corrupt_preferences_are_preserved_on_authorized_save(client):
    preferences.PREFERENCE_FILE.write_text('{broken', encoding="utf-8")
    assert client.get("/preferences").status_code == 503
    app.dependency_overrides[current_principal] = lambda: PreferencePrincipal("admin")
    try:
        assert client.put("/preferences/0", json={}).status_code == 503
    finally:
        app.dependency_overrides.pop(current_principal, None)
    assert preferences.PREFERENCE_FILE.read_text(encoding="utf-8") == '{broken'


def test_subject_blocks_respect_disabled_day_time_flags():
    # Bounded scorer helper call outside optimization; no equation or RNG change.
    subject = SimpleNamespace(number="CCC121",
                              lecture_time_blocks=[("Monday", SimpleNamespace(start_time="09:00", end_time="11:00"))],
                              laboratory_time_blocks=[])
    preference = {"use_day_preference": False, "use_time_preference": False,
                  "day_importance": 4, "time_importance": 3,
                  "preferred_schedule_blocks": [{"kind": "subject", "subject_code": "CCC121",
                                                  "component": "Lecture", "day": "Tuesday", "start_time": "10:30"}]}
    state = random.getstate()
    result = _score_exact_subject_schedule_blocks(subject, preference,
                                                  SimpleNamespace(day_penalty=5, time_penalty=10), 1)
    assert result == {"has_exact_blocks": True, "day_penalty": 0, "time_penalty": 0}
    assert random.getstate() == state
