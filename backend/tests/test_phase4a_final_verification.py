"""Final security verification: real sessions/CSRF; only storage is isolated.

No principal, role, ownership, credential, CSRF or origin dependency is bypassed.
Existing institutional PostgreSQL/JSON records are never touched.
"""
import hashlib
import json
import secrets
import sys
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from database import get_identity_db
from identity_admin import import_faculty
from identity_models import Base, User
from main import app
from routers import preferences
from services import auth_service as auth
from services.identity_service import load_faculty_identities
from services.preference_authorization import current_principal, require_admin, authorize_faculty

ORIGIN = "http://localhost:5173"


@dataclass(repr=False)
class Verification:
    admin: TestClient
    faculty1: TestClient
    faculty2: TestClient
    anonymous: TestClient
    engine: object
    storage: Path
    password: SecretStr = field(repr=False)
    security: dict = field(default_factory=dict, repr=False)
    users: dict = field(default_factory=dict)

    def __repr__(self):
        return "Verification(isolated_storage=True, credentials=REDACTED)"

    def login(self, client, username):
        response = client.post("/api/auth/login", headers={"Origin": ORIGIN},
                               json={"username": username, "password": self.password.get_secret_value()})
        assert response.status_code == 200
        self.security[id(client)] = SecretStr(response.json()["csrf_token"])
        return response.json()["user"]

    def headers(self, client):
        return {"Origin": ORIGIN, "X-CSRF-Token": self.security[id(client)].get_secret_value()}

    def stored(self):
        return json.loads(self.storage.read_text(encoding="utf-8"))

    def checksum(self):
        return hashlib.sha256(self.storage.read_bytes()).hexdigest()


@pytest.fixture
def verified(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'identity.sqlite'}", connect_args={"check_same_thread": False})
    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    password = SecretStr(secrets.token_urlsafe(24))
    with Session(engine) as db, db.begin():
        import_faculty(db)
        db.add(User(username="verification-admin@test.invalid", password_hash=auth.hash_password(password.get_secret_value()), role="admin"))
    def isolated_db():
        with Session(engine) as db:
            yield db
    # Only persistence is replaced. No permission/authentication overrides.
    monkeypatch.setattr(app, "dependency_overrides", {get_identity_db: isolated_db, auth.authenticated_db: isolated_db})
    assert all(dependency not in app.dependency_overrides for dependency in
               (auth.authenticated_session, current_principal, require_admin, authorize_faculty))
    storage = tmp_path / "preferences.json"
    monkeypatch.setattr(preferences, "PREFERENCE_FILE", storage)
    monkeypatch.setattr(preferences, "GA_SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", ORIGIN)
    monkeypatch.setattr(auth, "LOGIN_LIMITER", auth.LoginLimiter())
    for middleware in app.user_middleware:
        if middleware.cls is CORSMiddleware:
            monkeypatch.setitem(middleware.kwargs, "allow_origins", [ORIGIN])
    monkeypatch.setattr(app, "middleware_stack", None)
    with ExitStack() as stack:
        clients = [stack.enter_context(TestClient(app, base_url="http://localhost")) for _ in range(4)]
        state = Verification(*clients, engine, storage, password)
        state.users["admin"] = state.login(state.admin, "verification-admin@test.invalid")
        registry = load_faculty_identities()
        for code in (1, 2):
            identity = next(row for row in registry if row.faculty_code == code)
            response = state.admin.post("/api/auth/users", headers=state.headers(state.admin), json={
                "username": f"verification-faculty{code}@test.invalid", "password": password.get_secret_value(),
                "role": "faculty", "faculty_id": identity.faculty_id})
            assert response.status_code == 201
            state.users[f"faculty{code}"] = response.json()
            assert state.admin.put(f"/preferences/{code}", headers=state.headers(state.admin),
                                   json={"use_subject_preference": False, "use_day_preference": False}).status_code == 200
        state.login(state.faculty1, "verification-faculty1@test.invalid")
        state.login(state.faculty2, "verification-faculty2@test.invalid")
        yield state
    engine.dispose()


def test_faculty1_reads_and_updates_own_preferences_and_reload(verified):
    reply = verified.faculty1.get("/preferences/1")
    assert reply.status_code == 200 and reply.json()["faculty_code"] == 1
    target_before = next(row for row in verified.stored() if row["faculty_code"] == 2)
    reply = verified.faculty1.put("/preferences/1", headers=verified.headers(verified.faculty1),
                                 json={"use_day_preference": True, "use_time_preference": False})
    assert reply.status_code == 200
    assert reply.json()["use_day_preference"] is True and reply.json()["use_time_preference"] is False
    assert verified.faculty1.get("/preferences/1").json() == reply.json()
    assert next(row for row in verified.stored() if row["faculty_code"] == 2) == target_before


def test_faculty1_cannot_read_faculty2_preferences(verified):
    before = verified.checksum()
    response = verified.faculty1.get("/preferences/2")
    assert response.status_code == 403
    assert response.json()["detail"] == "You may only update your own faculty preferences."
    assert verified.checksum() == before


def test_valid_csrf_cross_faculty_put_reaches_ownership_check(verified):
    before = verified.checksum()
    response = verified.faculty1.put("/preferences/2", headers=verified.headers(verified.faculty1),
                                    json={"use_day_preference": True})
    assert response.status_code == 403
    assert response.json()["detail"] == "You may only update your own faculty preferences."
    assert verified.checksum() == before
    assert verified.faculty2.get("/preferences/2").json()["use_day_preference"] is False


def test_bad_csrf_and_valid_csrf_ownership_failures_are_distinct(verified):
    before = verified.checksum()
    invalid = verified.faculty1.put("/preferences/2", headers={"Origin": ORIGIN, "X-CSRF-Token": "invalid-test-value"}, json={})
    valid = verified.faculty1.put("/preferences/2", headers=verified.headers(verified.faculty1), json={})
    assert invalid.status_code == valid.status_code == 403
    assert invalid.json()["detail"] == "Session security check failed. Reload and try again."
    assert valid.json()["detail"] == "You may only update your own faculty preferences."
    assert verified.checksum() == before


@pytest.mark.parametrize("method,path", [("GET", "/preferences/1"), ("PUT", "/preferences/1"),
                                          ("GET", "/api/auth/me"), ("GET", "/api/auth/users")])
def test_anonymous_requests_rejected_without_storage_change(verified, method, path):
    before = verified.checksum()
    assert verified.anonymous.request(method, path, headers={"Origin": ORIGIN}, json={}).status_code == 401
    assert verified.checksum() == before


def test_spoofed_headers_body_and_metadata_identity_do_not_change_ownership(verified):
    before = verified.checksum()
    headers = {**verified.headers(verified.faculty1), "X-Role": "admin", "X-Faculty-ID": verified.users["faculty2"]["faculty_id"]}
    assert verified.faculty1.put("/preferences/2", headers=headers, json={}).status_code == 403
    assert verified.faculty1.put("/preferences/1", headers=headers, json={"faculty_id": verified.users["faculty2"]["faculty_id"]}).status_code == 422
    assert verified.faculty1.get(f"/api/faculty/{verified.users['faculty2']['faculty_id']}").status_code == 403
    assert verified.faculty1.get(f"/api/faculty/{verified.users['faculty1']['faculty_id']}").status_code == 200
    assert verified.checksum() == before


def test_admin_preferences_and_configuration_operations_are_permitted(verified):
    for code in (1, 2):
        assert verified.admin.get(f"/preferences/{code}").status_code == 200
        assert verified.admin.put(f"/preferences/{code}", headers=verified.headers(verified.admin),
                                  json={"faculty_priority": 3}).status_code == 200
    assert verified.admin.get("/preferences").status_code == 200
    assert verified.admin.get("/preferences/ga-settings").status_code == 200
    assert verified.admin.put("/preferences/ga-settings", headers=verified.headers(verified.admin), json={}).status_code == 200
    assert verified.admin.get("/api/ga/status").status_code == 200  # Read only; no worker started.
    assert verified.admin.delete("/preferences/2", headers=verified.headers(verified.admin)).status_code == 200
    assert verified.faculty2.get("/preferences/2").status_code == 200  # In-memory unsaved default.
    assert all(row["faculty_code"] != 2 for row in verified.stored())


@pytest.mark.parametrize("operation", ["list", "create", "other_account", "role", "binding", "self_role", "configuration", "start_ga"])
def test_faculty_cannot_perform_admin_operations_with_valid_csrf(verified, operation):
    before = verified.checksum()
    headers = verified.headers(verified.faculty1)
    target = verified.users["faculty2"]["id"]
    own = verified.users["faculty1"]["id"]
    if operation == "list": response = verified.faculty1.get("/api/auth/users")
    elif operation == "create": response = verified.faculty1.post("/api/auth/users", headers=headers, json={"username": "forbidden@test.invalid", "password": verified.password.get_secret_value(), "role": "admin"})
    elif operation == "other_account": response = verified.faculty1.patch(f"/api/auth/users/{target}", headers=headers, json={"is_active": False})
    elif operation == "role": response = verified.faculty1.patch(f"/api/auth/users/{target}", headers=headers, json={"role": "admin", "faculty_id": None})
    elif operation == "self_role": response = verified.faculty1.patch(f"/api/auth/users/{own}", headers=headers, json={"role": "admin", "faculty_id": None})
    elif operation == "binding": response = verified.faculty1.patch(f"/api/auth/users/{target}", headers=headers, json={"faculty_id": verified.users["faculty1"]["faculty_id"]})
    elif operation == "configuration": response = verified.faculty1.put("/preferences/ga-settings", headers=headers, json={})
    else: response = verified.faculty1.post("/api/ga/run", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Only an authorized administrator may perform this operation."
    assert verified.checksum() == before
    assert verified.faculty2.get("/api/auth/me").status_code == 200
    assert len(verified.admin.get("/api/auth/users").json()) == 3
    assert verified.faculty1.get("/api/auth/me").json()["user"]["role"] == "faculty"


@pytest.mark.parametrize("change", ["password", "role", "binding"])
def test_admin_account_changes_revoke_sessions_without_replacing_identity(verified, change):
    user_id = verified.users["faculty1"]["id"]
    if change == "password": payload = {"password": secrets.token_urlsafe(24)}
    elif change == "role": payload = {"role": "admin", "faculty_id": None}
    else: payload = {"faculty_id": next(row.faculty_id for row in load_faculty_identities() if row.faculty_code == 3)}
    reply = verified.admin.patch(f"/api/auth/users/{user_id}", headers=verified.headers(verified.admin), json=payload)
    assert reply.status_code == 200 and reply.json()["id"] == user_id
    assert verified.faculty1.get("/api/auth/me").status_code == 401
    assert verified.faculty1.put("/preferences/1", headers=verified.headers(verified.faculty1), json={}).status_code == 401
    assert verified.faculty2.get("/api/auth/me").status_code == 200


def test_duplicate_username_binding_and_invalid_identity_preserve_accounts(verified):
    before = verified.admin.get("/api/auth/users").json()
    first = verified.users["faculty1"]
    for username, binding, expected in [
        (first["username"], verified.users["faculty2"]["faculty_id"], 409),
        ("duplicate-binding@test.invalid", first["faculty_id"], 409),
        ("invalid-binding@test.invalid", "00000000-0000-4000-8000-000000000001", 422),
    ]:
        reply = verified.admin.post("/api/auth/users", headers=verified.headers(verified.admin),
                                    json={"username": username, "password": verified.password.get_secret_value(), "role": "faculty", "faculty_id": binding})
        assert reply.status_code == expected
        assert verified.admin.get("/api/auth/users").json() == before
    with Session(verified.engine) as db:
        identities = list(db.scalars(select(__import__('identity_models').FacultyIdentityRecord.id)))
        assert set(identities) == {UUID(row.faculty_id) for row in load_faculty_identities()}


def test_foreign_origin_and_missing_csrf_do_not_mutate_preferences(verified):
    before = verified.checksum()
    forbidden = {**verified.headers(verified.faculty1), "Origin": "https://untrusted.invalid"}
    assert verified.faculty1.put("/preferences/1", headers=forbidden, json={}).status_code == 403
    assert verified.faculty1.put("/preferences/1", headers={"Origin": ORIGIN}, json={}).status_code == 403
    assert verified.checksum() == before
