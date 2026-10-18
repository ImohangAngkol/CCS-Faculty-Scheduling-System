"""Offline fixture proofs: in-memory SQLite/ASGI, no PostgreSQL or TCP service."""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys

import pytest
import sqlalchemy
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from tests import phase4b_browser_support as support
from tests.phase4b_database_safety import SafetyError

ROOT = Path(__file__).resolve().parents[2]


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "docs/testing/phase-4b" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def forbid_online_actions(monkeypatch):
    original = sqlalchemy.create_engine
    def offline_engine(url, *args, **kwargs):
        if str(url) != "sqlite://":
            pytest.fail("Only isolated in-memory SQLite permitted in offline fixture tests")
        return original(url, *args, **kwargs)
    monkeypatch.setattr(sqlalchemy, "create_engine", offline_engine)
    from tests import phase4b_browser_safety
    monkeypatch.setattr(phase4b_browser_safety, "create_engine",
                        lambda *_a, **_k: pytest.fail("PostgreSQL preflight forbidden in offline fixture tests"))
    from alembic import command
    import uvicorn
    monkeypatch.setattr(command, "upgrade", lambda *_a, **_k: pytest.fail("Migration forbidden offline"))
    monkeypatch.setattr(uvicorn.Server, "run", lambda *_a, **_k: pytest.fail("Service startup forbidden offline"))


@pytest.fixture
def browser_app(tmp_path):
    from identity_models import Base
    engine = sqlalchemy.create_engine("sqlite://", poolclass=StaticPool,
                                     connect_args={"check_same_thread": False}, hide_parameters=True)
    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)  # temporary memory fixture, not Alembic
    try:
        with support.isolated_application(tmp_path / "storage", engine, unavailable=tmp_path / "fault") as state:
            password = "offline-fixture-private-password"
            state.update(engine=engine, password=password,
                         admin=support.seed_browser_accounts(engine, password))
            with TestClient(state["app"], base_url="http://localhost") as client:
                state["client"] = client
                yield state
    finally:
        engine.dispose()


def login(state, client=None, name=None):
    client = client or state["client"]
    result = client.post("/api/auth/login", headers={"Origin": support.ORIGIN},
                         json={"username": name or state["admin"], "password": state["password"]})
    assert result.status_code == 200
    return {"Origin": support.ORIGIN, "X-CSRF-Token": result.json()["csrf_token"]}


def create_faculty(state, headers, code=0):
    payload = {"username": f"browser-faculty-{code}@test.invalid", "password": state["password"],
               "role": "faculty", "faculty_id": state["identities"][code].faculty_id}
    response = state["client"].post("/api/auth/users", headers=headers, json=payload)
    assert response.status_code == 201
    return payload["username"]


def test_missing_browser_variable_never_uses_other_urls_or_writes_handoff(tmp_path):
    ready = tmp_path / "phase4b-browser-missing" / "ready.json"
    environment = {key: value for key, value in os.environ.items()
                   if key != "PHASE4B_BROWSER_DATABASE_URL"}
    environment.update(DATABASE_URL="postgresql://unused.invalid/application",
                       PHASE4B_TEST_DATABASE_URL="postgresql://unused.invalid/acceptance",
                       PYTHONDONTWRITEBYTECODE="1")
    child = subprocess.run([sys.executable, str(ROOT / "docs/testing/phase-4b/serve_browser_fixture.py"),
                            "--ready-file", str(ready), "--allow-browser-database-initialization"],
                           env=environment, capture_output=True, text=True, timeout=15)
    assert child.returncode == 2 and "BLOCKED" in child.stdout
    assert "unused.invalid" not in child.stdout + child.stderr
    assert not ready.parent.exists()


def test_initialization_opt_in_required_before_any_connection(tmp_path, monkeypatch):
    tool = load_tool("serve_browser_fixture")
    monkeypatch.setattr(tool, "reserve_listener", lambda: pytest.fail("Must not reserve a port"))
    with pytest.raises(SafetyError, match="Stage B approval"):
        tool.run_fixture(tmp_path / "phase4b-browser-no-approval" / "ready.json")
    assert not (tmp_path / "phase4b-browser-no-approval").exists()


def test_preflight_failure_closes_only_owned_socket_before_migration(tmp_path, monkeypatch):
    tool = load_tool("serve_browser_fixture")
    from tests import phase4b_browser_safety as safety
    from sqlalchemy.engine import URL
    monkeypatch.setattr(safety, "designated_browser_url", lambda: URL.create(
        "postgresql", username=safety.BROWSER_ROLE, host="127.0.0.1",
        port=5432, database=safety.BROWSER_DATABASE))
    def reject(_url): raise SafetyError("Rejected fake preflight")
    monkeypatch.setattr(safety, "inspect_empty_browser_database", reject)
    monkeypatch.setattr(support, "secure_private_directory", lambda _root: None)
    class OwnedSocket:
        closed = False
        def close(self): self.closed = True
    owned = OwnedSocket()
    monkeypatch.setattr(tool, "reserve_listener", lambda: owned)
    ready = tmp_path / "phase4b-browser-rejected" / "ready.json"
    with pytest.raises(SafetyError, match="Rejected fake"):
        tool.run_fixture(ready, allow_initialization=True)
    assert owned.closed and not ready.exists()
    assert list(ready.parent.iterdir()) == []


def test_bind_failure_never_runs_preflight_or_changes_existing_marker(tmp_path, monkeypatch):
    tool = load_tool("serve_browser_fixture")
    from tests import phase4b_browser_safety as safety
    monkeypatch.setattr(safety, "designated_browser_url", lambda: object())
    monkeypatch.setattr(safety, "inspect_empty_browser_database", lambda _url: pytest.fail("No preflight after bind failure"))
    def occupied(): raise OSError("synthetic bind failure")
    monkeypatch.setattr(tool, "reserve_listener", occupied)
    existing = tmp_path / "existing-service-sentinel"
    existing.write_text("untouched")
    ready = tmp_path / "phase4b-browser-bind" / "ready.json"
    with pytest.raises(OSError):
        tool.run_fixture(ready, allow_initialization=True)
    assert existing.read_text() == "untouched" and not ready.parent.exists()


@pytest.mark.parametrize("location", ["existing", "wrong_name", "outside_temp"])
def test_unsafe_ready_locations_are_rejected(tmp_path, location):
    ready = tmp_path / "phase4b-browser-private" / "ready.json"
    if location == "existing":
        ready.parent.mkdir()
    elif location == "wrong_name":
        ready = tmp_path / "other" / "ready.json"
    else:
        ready = ROOT / "phase4b-browser-forbidden" / "ready.json"
    with pytest.raises(SafetyError): support.validate_ready_path(ready)


def test_migration_without_approval_is_inert():
    with pytest.raises(SafetyError, match="Stage B approval"):
        support.migrate_browser_database(object())


def test_complete_reader_writer_inventory_and_empty_result_visibility(browser_app):
    state = browser_app
    support.assert_storage_isolated(state["root"])
    bindings = {(module.__name__, attr) for module, attr, _ in support.storage_bindings()}
    assert len(bindings) == 14
    assert ("routers.chromosomes", "LATEST_RESULT_FILE") in bindings
    assert ("routers.genetic_algorithm", "LATEST_RESULT_FILE") in bindings
    headers = login(state)
    assert headers["X-CSRF-Token"]
    assert state["client"].get("/api/ga/status").status_code == 200
    from routers import chromosomes
    assert chromosomes._load_latest_ga_result() is None
    assert not (state["root"] / "latest.json").exists()


def test_all_metadata_and_offered_subjects_are_synthetic(browser_app):
    state = browser_app
    login(state)
    rows = state["client"].get("/api/faculty/").json()["data"]
    assert len(rows) == 2
    for index, row in enumerate(rows):
        assert row["name"] == f"Browser Synthetic Faculty {index}"
        assert row["specializations"] == row["eligible_subject_codes"] == []
        assert row["admin_load"] == row["research_load"] == row["extension_load"] == 0
        assert row["seniority_level"] == 1 and row["required_teaching_load"] == 24
        assert state["client"].get(f"/api/faculty/{row['faculty_id']}/eligible-subjects").json()["data"] == []
    marker = state["client"].get("/__phase4b_fixture").json()
    assert marker["synthetic_profiles"] and marker["ga_execution"] is False


def test_source_faculty_and_subject_collections_are_not_read_or_copied(tmp_path, monkeypatch):
    from services import metadata_service
    class PrivateCollection:
        def __iter__(self): pytest.fail("Private academic profiles must not be read")
        def __deepcopy__(self, _memo): pytest.fail("Private profiles must not be copied")
    monkeypatch.setattr(metadata_service.scheduling, "list_faculty", PrivateCollection())
    monkeypatch.setattr(metadata_service.scheduling, "list_subjects", PrivateCollection())
    with support.isolated_application(tmp_path / "synthetic", object()):
        assert len(metadata_service.list_faculty_metadata()) == 2
        assert metadata_service.list_subject_metadata() == []


def test_real_account_binding_preferences_reload_admin_review_and_ownership(browser_app):
    state = browser_app
    headers = login(state)
    name = create_faculty(state, headers)
    other = create_faculty(state, headers, 1)
    assert other != name
    duplicate = state["client"].post("/api/auth/users", headers=headers, json={
        "username": "duplicate-browser@test.invalid", "password": state["password"],
        "role": "faculty", "faculty_id": state["identities"][0].faculty_id})
    assert duplicate.status_code == 409
    with TestClient(state["app"], base_url="http://localhost") as faculty:
        faculty_headers = login(state, faculty, name)
        desired = {"gap_preference": "Compact", "gap_importance": 5, "use_gap_preference": True}
        assert faculty.put("/preferences/0", json=desired, headers=faculty_headers).status_code == 200
        refreshed = faculty.get("/preferences/0").json()
        assert all(refreshed[key] == value for key, value in desired.items())
        assert faculty.get("/api/auth/users").status_code == 403
        assert faculty.get("/preferences/1").status_code == 403
        assert faculty.put("/preferences/1", json=desired, headers=faculty_headers).status_code == 403
        assert faculty.put("/preferences/0", json=desired, headers={"Origin": support.ORIGIN}).status_code == 403
        assert faculty.post("/api/auth/logout", headers=faculty_headers).status_code == 204
        assert faculty.get("/preferences/0").status_code == 401
    reviewed = state["client"].get("/preferences/0").json()
    assert reviewed["gap_preference"] == "Compact" and reviewed["gap_importance"] == 5
    assert state["client"].get("/preferences/1").json()["gap_preference"] == "No Preference"
    with TestClient(state["app"], base_url="http://localhost") as fresh:
        login(state, fresh, name)
        assert fresh.get("/preferences/0").json()["gap_importance"] == 5


def test_injected_outage_and_recovery_use_same_isolated_session(browser_app):
    state = browser_app
    login(state)
    state["unavailable"].write_text("owned test-only fault")
    result = state["client"].get("/api/auth/me")
    assert result.status_code == 503 and "injected acceptance fault" in result.json()["detail"]
    state["unavailable"].unlink()
    assert state["client"].get("/api/auth/me").status_code == 200


def test_ga_generation_resume_rng_and_fitness_never_execute(browser_app, monkeypatch):
    state = browser_app
    headers = login(state)
    ga = importlib.import_module("routers.genetic_algorithm")
    from genetic_algorithm.operators import FitnessFunction
    monkeypatch.setattr(FitnessFunction, "faculty_preference_fitness",
                        lambda *_a, **_k: pytest.fail("No additional fitness evaluations"))
    before = random.getstate()
    for path in ("/api/ga/generate", "/api/ga/run", "/api/ga/stream"):
        response = state["client"].post(path, headers=headers)
        assert response.status_code == 409
        assert "disabled" in response.json()["detail"]
    control = ga._run_registry.register()
    control.state, control.execution_active = "PAUSED", False
    ga._run_registry.active_id = None
    response = state["client"].post(f"/api/ga/runs/{control.run_id}/resume",
        headers={**headers, "X-GA-Process-ID": ga._run_registry.process_instance_id})
    assert response.status_code == 409 and "disabled" in response.json()["detail"]
    assert random.getstate() == before
    assert not (state["root"] / "checkpoints").exists()


def test_leaked_production_storage_binding_fails(tmp_path, monkeypatch):
    bindings = support.storage_bindings()
    module, attr, relative = bindings[0]
    monkeypatch.setattr(module, attr, ROOT / "backend/data/faculty_preferences.json")
    with pytest.raises(SafetyError, match="isolation"):
        support.assert_storage_isolated(tmp_path)


def test_existing_temporary_preferences_not_overwritten_and_globals_restore(tmp_path):
    bindings = support.storage_bindings()
    before = [(module, attr, getattr(module, attr)) for module, attr, _ in bindings]
    folder = tmp_path / "existing"
    folder.mkdir()
    sentinel = folder / "preferences.json"
    sentinel.write_text('["sentinel"]')
    with pytest.raises(FileExistsError):
        with support.isolated_application(folder, object()):
            pytest.fail("Existing storage must not be reused")
    assert sentinel.read_text() == '["sentinel"]'
    assert all(getattr(module, attr) == value for module, attr, value in before)


def test_private_temp_directory_acl_is_verified(tmp_path):
    root = tmp_path / "phase4b-browser-acl"
    root.mkdir()
    support.secure_private_directory(root)
    secret = root / "private-test-file"
    secret.write_text("synthetic only")
    assert secret.read_text() == "synthetic only"


def test_acl_failure_sanitizes_private_diagnostics(tmp_path, monkeypatch):
    if os.name != "nt":
        pytest.skip("Windows subprocess failure branch")
    root = tmp_path / "phase4b-browser-acl-failure"
    root.mkdir()
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: type(
        "Result", (), {"returncode": 1, "stderr": b"synthetic private detail"})())
    with pytest.raises(SafetyError) as error: support.secure_private_directory(root)
    assert "synthetic private" not in str(error.value)
