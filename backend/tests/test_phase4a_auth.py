"""Real credential/session requests against isolated relational and JSON storage."""
import importlib.util
import json
import random
import secrets
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from database import get_identity_db
from identity_models import Base, FacultyIdentityRecord, LoginSession, User, now
from identity_admin import bootstrap_admin, import_faculty
from main import app
from routers import preferences
from services import auth_service as auth
from services.identity_service import load_faculty_identities

ORIGIN = "http://localhost:5173"


@pytest.fixture
def identity_app(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'identity.sqlite'}", connect_args={"check_same_thread": False})
    @event.listens_for(engine, "connect")
    def enforce_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    password = secrets.token_urlsafe(24)
    ids = load_faculty_identities()
    with Session(engine) as db, db.begin():
        import_faculty(db)
        for name, role, code in [("admin@test.invalid", "admin", None), ("faculty@test.invalid", "faculty", 0), ("other@test.invalid", "faculty", 1)]:
            db.add(User(username=name, role=role, faculty_id=UUID(ids[code].faculty_id) if code is not None else None,
                        password_hash=auth.hash_password(password)))
    def isolated_db():
        with Session(engine) as db:
            yield db
    monkeypatch.setattr(app, "dependency_overrides", {get_identity_db: isolated_db, auth.authenticated_db: isolated_db})
    monkeypatch.setattr(preferences, "PREFERENCE_FILE", tmp_path / "preferences.json")
    monkeypatch.setattr(preferences, "GA_SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr(auth, "LOGIN_LIMITER", auth.LoginLimiter())
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", ORIGIN)
    # CORS is configured at application startup, not by a later environment edit.
    from fastapi.middleware.cors import CORSMiddleware
    for middleware in app.user_middleware:
        if middleware.cls is CORSMiddleware:
            monkeypatch.setitem(middleware.kwargs, "allow_origins", [ORIGIN, "http://localhost:5189"])
    monkeypatch.setattr(app, "middleware_stack", None)
    with TestClient(app, base_url="http://localhost") as client:
        yield client, engine, password, tmp_path
    engine.dispose()


def sign_in(client, password, username="faculty@test.invalid"):
    response = client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}


def test_password_hashing():
    password = secrets.token_urlsafe(24)
    first, second = auth.hash_password(password), auth.hash_password(password)
    assert first != second and password not in first and first.startswith("$argon2id$")
    assert auth.verify_password(first, password)
    assert not auth.verify_password(first, "wrong")
    assert not auth.verify_password("invalid", password)
    with pytest.raises(ValueError):
        auth.hash_password("short")
    with pytest.raises(ValueError):
        auth.hash_password("😀" * 300)


@pytest.mark.parametrize("origin", ["*", "https://trusted.invalid/path", "https://user:secret@trusted.invalid", "http://localhost:badport"])
def test_cors_requires_exact_valid_origins(monkeypatch, origin):
    from fastapi import HTTPException
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", origin)
    with pytest.raises(HTTPException) as error:
        auth.allowed_origins()
    assert error.value.status_code == 503


def test_insecure_cookies_reject_nonlocal_deployment(monkeypatch):
    from fastapi import HTTPException
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", "https://college.example")
    with pytest.raises(HTTPException):
        auth.cookie_secure()


def test_cookie_login_reload_logout(identity_app):
    client, engine, password, _ = identity_app
    headers = sign_in(client, password)
    assert client.cookies.get(auth.COOKIE_NAME)
    response = client.get("/api/auth/me")
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json()["user"]["faculty"]["faculty_code"] == 0
    with Session(engine) as db:
        session = db.scalar(select(LoginSession))
        assert session.token_hash != client.cookies.get(auth.COOKIE_NAME)
        assert session.token_hash == auth.token_hash(client.cookies.get(auth.COOKIE_NAME))
    cookie = client.cookies.get(auth.COOKIE_NAME)
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    with TestClient(app, base_url="http://localhost") as stolen:
        stolen.cookies.set(auth.COOKIE_NAME, cookie)
        assert stolen.get("/api/auth/me").status_code == 401


@pytest.mark.parametrize("username,password_value", [("unknown@test.invalid", "wrong"), ("faculty@test.invalid", "wrong")])
def test_login_failure_is_generic(identity_app, username, password_value):
    client, _engine, _password, _ = identity_app
    reply = client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={"username": username, "password": password_value})
    assert reply.status_code == 401 and reply.json()["detail"] == "Invalid credentials or account unavailable."
    assert not client.cookies.get(auth.COOKIE_NAME)


@pytest.mark.parametrize("mode", ["expired", "disabled"])
def test_expired_and_disabled_accounts(identity_app, mode):
    client, engine, password, _ = identity_app
    sign_in(client, password)
    with Session(engine) as db, db.begin():
        if mode == "expired":
            db.scalar(select(LoginSession)).expires_at = now() - timedelta(seconds=1)
        else:
            db.scalar(select(User).where(User.role == "faculty")).is_active = False
    assert client.get("/api/auth/me").status_code == 401
    if mode == "disabled":
        assert client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={"username": "faculty@test.invalid", "password": password}).status_code == 401


def test_cookie_flags_and_rotation(identity_app, monkeypatch):
    client, engine, password, _ = identity_app
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    response = client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={"username": "admin@test.invalid", "password": password})
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie and "Path=/" in cookie
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    client.cookies.clear()
    sign_in(client, password)
    previous = client.cookies.get(auth.COOKIE_NAME)
    sign_in(client, password)
    assert client.cookies.get(auth.COOKIE_NAME) != previous
    with Session(engine) as db:
        assert db.scalar(select(LoginSession).where(LoginSession.token_hash == auth.token_hash(previous))) is None


@pytest.mark.parametrize("headers", [{}, {"Origin": "https://hostile.invalid"}, {"Origin": ORIGIN, "X-CSRF-Token": "forged"}])
def test_csrf_rejects_without_storage_writes(identity_app, headers):
    client, _engine, password, tmp_path = identity_app
    sign_in(client, password)
    response = client.put("/preferences/0", headers=headers, json={"use_time_preference": False})
    assert response.status_code == 403
    assert not (tmp_path / "preferences.json").exists()


def test_login_origin_and_throttling(identity_app):
    client, _engine, _password, _ = identity_app
    payload = {"username": "nobody@test.invalid", "password": "wrong"}
    assert client.post("/api/auth/login", json=payload).status_code == 403
    for _ in range(10):
        assert client.post("/api/auth/login", headers={"Origin": ORIGIN}, json=payload).status_code == 401
    assert client.post("/api/auth/login", headers={"Origin": ORIGIN}, json=payload).status_code == 429


def test_faculty_save_reload_and_ownership(identity_app):
    client, _engine, password, tmp_path = identity_app
    headers = sign_in(client, password)
    user = client.get("/api/auth/me").json()["user"]
    assert client.get(f"/api/faculty/{user['faculty_id']}/eligible-subjects").status_code == 200
    assert client.get("/api/faculty/1/eligible-subjects").status_code == 403
    old_rng = random.getstate()
    reply = client.put("/preferences/0", headers=headers, json={"use_day_preference": False, "use_time_preference": False})
    assert reply.status_code == 200 and not reply.json()["use_time_preference"]
    assert client.get("/preferences/0").json() == reply.json()
    before = (tmp_path / "preferences.json").read_bytes()
    assert client.put("/preferences/1", headers=headers, json={}).status_code == 403
    assert client.get("/preferences/1").status_code == 403
    assert client.put("/preferences/0", headers=headers, json={"faculty_priority": 99}).status_code == 403
    assert client.put("/preferences/0", headers=headers, json={"faculty_id": user["faculty_id"]}).status_code == 422
    assert (tmp_path / "preferences.json").read_bytes() == before
    assert random.getstate() == old_rng


def test_concurrent_preference_partial_updates(identity_app):
    client, _engine, password, _ = identity_app
    headers = sign_in(client, password, "admin@test.invalid")
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda code: client.put(f"/preferences/{code}", headers=headers, json={"use_day_preference": False}), range(4)))
    assert all(reply.status_code == 200 for reply in responses)
    assert {row["faculty_code"] for row in client.get("/preferences").json()} == set(range(4))


def test_corrupt_and_invalid_preference_storage_preserved(identity_app):
    client, _engine, password, tmp_path = identity_app
    headers = sign_in(client, password)
    file = tmp_path / "preferences.json"
    file.write_text("{broken", encoding="utf-8")
    assert client.put("/preferences/0", headers=headers, json={}).status_code == 503
    assert file.read_text() == "{broken"
    file.unlink()  # owned temporary fixture only
    assert client.put("/preferences/0", headers=headers, json={"use_day_preference": "false"}).status_code == 422
    assert not file.exists()


def test_all_administrative_routes_reject_anonymous_and_faculty(identity_app):
    client, _engine, password, _ = identity_app
    paths = []
    for route, methods in app.openapi()["paths"].items():
        if (route.startswith(("/api/ga/", "/api/chromosomes/"))
                or route in {"/api/faculty/", "/preferences", "/preferences/ga-settings", "/api/auth/users"}
                or route.startswith("/api/auth/users/")):
            path = route.replace("{run_id}", str(uuid4())).replace("{generation}", "0").replace("{user_id}", str(uuid4()))
            paths.extend((method.upper(), path) for method in methods)
    assert len(paths) >= 35
    for method, path in paths:
        assert client.request(method, path, json={}).status_code == 401, (method, path)
    headers = sign_in(client, password)
    for method, path in paths:
        assert client.request(method, path, headers=headers, json={}).status_code == 403, (method, path)


def test_administrator_creation_binding_revocation_and_last_admin(identity_app):
    client, engine, password, _ = identity_app
    headers = sign_in(client, password, "admin@test.invalid")
    faculty_id = load_faculty_identities()[2].faculty_id
    payload = {"username": "new@test.invalid", "password": password, "role": "faculty", "faculty_id": faculty_id}
    response = client.post("/api/auth/users", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    user_id = response.json()["id"]
    duplicate = {**payload, "username": "duplicate@test.invalid"}
    assert client.post("/api/auth/users", headers=headers, json=duplicate).status_code == 409
    assert client.patch(f"/api/auth/users/{user_id}", headers=headers, json={"faculty_id": load_faculty_identities()[3].faculty_id}).status_code == 200
    with TestClient(app, base_url="http://localhost") as faculty:
        sign_in(faculty, password, "new@test.invalid")
        assert client.patch(f"/api/auth/users/{user_id}", headers=headers, json={"is_active": False}).status_code == 200
        assert faculty.get("/api/auth/me").status_code == 401
    me = client.get("/api/auth/me").json()["user"]
    assert client.patch(f"/api/auth/users/{me['id']}", headers=headers, json={"is_active": False}).status_code == 409
    with Session(engine) as db:
        assert db.get(User, UUID(me["id"])).is_active
    data = client.get("/api/auth/users").json()
    assert all("password_hash" not in user for user in data)


@pytest.mark.parametrize("bad", [
    {"role": "faculty", "faculty_id": None},
    {"role": "admin", "faculty_id": "a1746741-97b6-4e55-990e-06a4cc98dd00"},
    {"role": "faculty", "faculty_id": "a1746741-97b6-4e55-990e-06a4cc98dd99"},
    {"role": "superuser", "faculty_id": None},
])
def test_bad_bindings_rejected(identity_app, bad):
    client, _engine, password, _ = identity_app
    headers = sign_in(client, password, "admin@test.invalid")
    assert client.post("/api/auth/users", headers=headers, json={"username": "bad@test.invalid", "password": password, **bad}).status_code == 422


def test_missing_registry_binding_never_guesses_identity(identity_app, monkeypatch):
    client, _engine, password, _ = identity_app
    sign_in(client, password)
    monkeypatch.setattr(auth, "resolve_faculty_identity", lambda _value: (_ for _ in ()).throw(ValueError("missing")))
    assert client.get("/api/auth/me").json()["user"]["faculty"] is None


def test_invalid_credentials_not_echoed(identity_app):
    client, _engine, _password, _ = identity_app
    secret = secrets.token_urlsafe(24)
    response = client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={"username": "bad name", "password": secret})
    assert response.status_code == 422 and secret not in response.text


def test_bootstrap_and_import_are_idempotent(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'bootstrap.sqlite'}")
    Base.metadata.create_all(engine)
    password = secrets.token_urlsafe(24)
    with Session(engine) as db, db.begin():
        assert import_faculty(db) == 11
        assert import_faculty(db) == 0
        assert bootstrap_admin(db, "First@test.invalid", password)
        assert not bootstrap_admin(db, "first@test.invalid", secrets.token_urlsafe(24))
        assert auth.verify_password(db.scalar(select(User)).password_hash, password)
        with pytest.raises(ValueError):
            bootstrap_admin(db, "second@test.invalid", password)
    engine.dispose()


@pytest.mark.parametrize("violation", ["username", "faculty", "foreign_key", "role", "binding", "case"])
def test_database_constraints(identity_app, violation):
    _client, engine, password, _ = identity_app
    with Session(engine) as db:
        identity = load_faculty_identities()[4]
        values = {"username": "constraint@test.invalid", "role": "faculty", "faculty_id": UUID(identity.faculty_id)}
        if violation == "username": values["username"] = "faculty@test.invalid"
        if violation == "faculty": values["faculty_id"] = UUID(load_faculty_identities()[0].faculty_id)
        if violation == "foreign_key": values["faculty_id"] = uuid4()
        if violation == "role": values["role"] = "fake"
        if violation == "binding": values["faculty_id"] = None
        if violation == "case": values["username"] = "UPPER@test.invalid"
        db.add(User(**values, password_hash=auth.hash_password(password)))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_migration_upgrade_downgrade_matches_models(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'migration.sqlite'}")
    source = Path(__file__).resolve().parents[1] / "migrations/versions/4a_0001_identity.py"
    spec = importlib.util.spec_from_file_location("phase4a_migration", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            module.upgrade()
            assert set(inspect(connection).get_table_names()) == set(Base.metadata.tables)
            for name, table in Base.metadata.tables.items():
                assert {row["name"] for row in inspect(connection).get_columns(name)} == set(table.columns.keys())
            module.downgrade()
            assert inspect(connection).get_table_names() == []
    engine.dispose()


def test_postgresql_offline_migration_sql(monkeypatch):
    import io
    from alembic.config import Config
    from alembic import command
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://unused:unused@localhost:5432/unused_offline")
    backend = Path(__file__).resolve().parents[1]
    output = io.StringIO()
    command.upgrade(Config(str(backend / "alembic.ini"), output_buffer=output), "head", sql=True)
    sql = output.getvalue()
    assert "UUID" in sql and "FOREIGN KEY" in sql and "4a_0001" in sql and "ck_user_binding" in sql
    output = io.StringIO()
    command.downgrade(Config(str(backend / "alembic.ini"), output_buffer=output), "4a_0001:base", sql=True)
    assert "DROP TABLE users" in output.getvalue()


def test_unconfigured_identity_database_is_actionable_and_never_falls_back(monkeypatch):
    from database import identity_engine
    from fastapi import HTTPException
    identity_engine.cache_clear()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(HTTPException) as error:
        identity_engine()
    assert error.value.status_code == 503
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    with pytest.raises(HTTPException):
        identity_engine()
    identity_engine.cache_clear()


def test_stream_auth_releases_database_before_streaming(identity_app):
    from fastapi import Depends, FastAPI
    from fastapi.responses import StreamingResponse
    from services.preference_authorization import require_admin
    client, engine, password, _tmp = identity_app
    sign_in(client, password, "admin@test.invalid")
    private_app = FastAPI()
    released = []
    def db_fixture():
        with Session(engine) as db:
            try:
                yield db
            finally:
                released.append(True)
    private_app.dependency_overrides[auth.authenticated_db] = db_fixture
    @private_app.get("/stream", dependencies=[Depends(require_admin)])
    def stream():
        def content():
            assert released == [True], "Long SSE responses must not hold an identity connection"
            yield "authorized"
        return StreamingResponse(content())
    with TestClient(private_app, base_url="http://localhost") as stream_client:
        stream_client.cookies.set(auth.COOKIE_NAME, client.cookies.get(auth.COOKIE_NAME))
        assert stream_client.get("/stream").text == "authorized"


def test_real_browser_identity_and_preferences(identity_app, monkeypatch):
    import os
    import shutil
    import socket
    import subprocess
    import threading
    import time
    import uvicorn
    _client, _engine, password, _tmp = identity_app
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", "http://localhost:5189")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error", lifespan="off"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert time.monotonic() < deadline, "Test API did not start"
            time.sleep(0.02)
        result = subprocess.run([shutil.which("node"), "--test", "tests/auth.browser.integration.mjs"],
                                cwd=Path(__file__).resolve().parents[2] / "frontend",
                                env={**os.environ, "AUTH_TEST_URL": f"http://localhost:{port}", "AUTH_TEST_PASSWORD": password},
                                capture_output=True, text=True, timeout=150)
        assert result.returncode == 0, result.stdout + result.stderr
        print(result.stdout)
    finally:
        server.should_exit = True
        thread.join(timeout=10)
