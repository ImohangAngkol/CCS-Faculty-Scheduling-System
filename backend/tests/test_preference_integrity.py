"""Real API authorization/atomic persistence; all artifacts are temporary."""
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from main import app
from routers import preferences
from services import preference_storage_service as storage
from services.preference_authorization import current_principal, PreferencePrincipal
from services.metadata_service import resolve_normal_faculty


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(preferences, "PREFERENCE_FILE", tmp_path / "preferences.json")
    monkeypatch.setattr(preferences, "GA_SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr(app, "dependency_overrides", {})
    with TestClient(app) as instance:
        yield instance


def identity(role="admin", code=None):
    app.dependency_overrides[current_principal] = lambda: PreferencePrincipal(role, resolve_normal_faculty(code).stable_id if code is not None else None)


@pytest.mark.parametrize("method,path", [("put", "/preferences/0"), ("delete", "/preferences/0"), ("put", "/preferences/ga-settings")])
def test_anonymous_writes_and_spoofed_client_identity_are_denied(client, method, path):
    options = {"headers": {"Authorization": "Bearer fake", "X-Faculty-ID": resolve_normal_faculty(0).stable_id, "X-Role": "admin"}}
    if method == "put":
        options["json"] = {}
    response = getattr(client, method)(path, **options)
    assert response.status_code == 401
    assert not preferences.PREFERENCE_FILE.exists() and not preferences.GA_SETTINGS_FILE.exists()


def test_faculty_ownership_and_administrator_fields_are_enforced(client):
    identity("faculty", 0)
    assert client.put("/preferences/0", json={"use_day_preference": False}).status_code == 200
    before = preferences.PREFERENCE_FILE.read_bytes()
    assert client.put("/preferences/1", json={}).status_code == 403
    assert client.put("/preferences/0", json={"faculty_priority": 2}).status_code == 403
    assert client.put("/preferences/ga-settings", json={}).status_code == 403
    assert client.delete("/preferences/0").status_code == 403
    assert preferences.PREFERENCE_FILE.read_bytes() == before
    identity()
    assert client.put("/preferences/0", json={"faculty_priority": 2}).status_code == 200


@pytest.mark.parametrize("content", ['{broken', '{}', 'null', '[{}]', '[{"faculty_code":0},{"faculty_code":0}]', '[{"faculty_code":99}]', '[{"faculty_code":0,"faculty_code":1}]', '[{"faculty_code":true}]', '[' * 2000 + '0' + ']' * 2000])
def test_corrupt_structural_storage_never_becomes_empty_or_replaced(client, content):
    identity()
    preferences.PREFERENCE_FILE.write_text(content, encoding="utf-8")
    before = preferences.PREFERENCE_FILE.read_bytes()
    assert client.get("/preferences").status_code == 503
    assert client.put("/preferences/0", json={}).status_code == 503
    assert client.delete("/preferences/0").status_code == 503
    assert preferences.PREFERENCE_FILE.read_bytes() == before


@pytest.mark.parametrize("payload", [{"faculty_code":1}, {"unrecognized":True}, {"use_day_preference":"false"}, {"day_importance":99}, {"day_importance":None}, {"preferred_subjects":None}])
def test_invalid_payload_preserves_existing_storage(client, payload):
    identity()
    assert client.put("/preferences/0", json={}).status_code == 200
    before = preferences.PREFERENCE_FILE.read_bytes()
    assert client.put("/preferences/0", json=payload).status_code == 422
    assert preferences.PREFERENCE_FILE.read_bytes() == before


def test_malformed_json_and_invalid_faculty_are_rejected(client):
    identity()
    assert client.put("/preferences/0", content='{bad', headers={"Content-Type":"application/json"}).status_code == 422
    assert client.put("/preferences/99", json={}).status_code == 422
    assert client.get("/preferences/99").status_code == 404
    assert not preferences.PREFERENCE_FILE.exists()


@pytest.mark.parametrize("failure", ["fsync", "replace"])
def test_failed_atomic_write_preserves_previous_valid_version(client, monkeypatch, failure):
    identity()
    assert client.put("/preferences/0", json={}).status_code == 200
    before = preferences.PREFERENCE_FILE.read_bytes()
    def fail(*args):
        raise OSError("Simulated storage interruption")
    monkeypatch.setattr(storage.os, failure, fail)
    assert client.put("/preferences/0", json={"day_importance":4}).status_code == 503
    assert preferences.PREFERENCE_FILE.read_bytes() == before
    assert not list(preferences.PREFERENCE_FILE.parent.glob(".preference-*.tmp"))


def test_unreadable_storage_preserves_file(client, monkeypatch):
    identity()
    assert client.put("/preferences/0", json={}).status_code == 200
    before = preferences.PREFERENCE_FILE.read_bytes()
    original = storage.Path.read_text
    def denied(path, *args, **kwargs):
        if path == preferences.PREFERENCE_FILE:
            raise PermissionError("Simulated access failure")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(storage.Path, "read_text", denied)
    assert client.put("/preferences/0", json={}).status_code == 503
    assert preferences.PREFERENCE_FILE.read_bytes() == before


def test_partial_update_preserves_omitted_fields_and_unrelated_legacy_records(client):
    identity()
    assert client.put("/preferences/0", json={"day_importance":4, "use_time_preference":False}).status_code == 200
    assert client.put("/preferences/1", json={"day_importance":5}).status_code == 200
    data = json.loads(preferences.PREFERENCE_FILE.read_bytes()); data[1]["legacy_note"] = "preserve"
    preferences.PREFERENCE_FILE.write_text(json.dumps(data), encoding="utf-8")
    before_other = data[1]
    result = client.put("/preferences/0", json={"use_day_preference":False})
    assert result.status_code == 200
    assert result.json()["day_importance"] == 4 and result.json()["use_time_preference"] is False
    assert result.json() == client.get("/preferences/0").json()
    assert json.loads(preferences.PREFERENCE_FILE.read_bytes())[1] == before_other


def test_concurrent_updates_do_not_lose_unrelated_changes(client):
    identity()
    with ThreadPoolExecutor(max_workers=4) as pool:
        replies = list(pool.map(lambda code: client.put(f"/preferences/{code}", json={"day_importance":code % 5}), range(11)))
    assert all(reply.status_code == 200 for reply in replies)
    records = json.loads(preferences.PREFERENCE_FILE.read_bytes())
    assert len(records) == 11
    assert {row["faculty_code"]:row["day_importance"] for row in records} == {code:code % 5 for code in range(11)}
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda payload: client.put("/preferences/0", json=payload), [{"use_time_preference":False}, {"use_day_preference":False}]))
    assert all(reply.status_code == 200 for reply in replies)
    result = client.get("/preferences/0").json()
    assert result["use_day_preference"] is False and result["use_time_preference"] is False


def test_corrupt_settings_cannot_be_reset_by_an_authorized_save(client):
    identity()
    preferences.GA_SETTINGS_FILE.write_text('{bad', encoding="utf-8")
    assert client.get("/preferences/ga-settings").status_code == 503
    assert client.put("/preferences/ga-settings", json={}).status_code == 503
    assert preferences.GA_SETTINGS_FILE.read_text(encoding="utf-8") == '{bad'
