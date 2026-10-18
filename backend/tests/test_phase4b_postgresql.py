"""Opt-in, one-shot acceptance against the explicitly designated empty database.

No downgrade, database deletion, cleanup of existing accounts, or DATABASE_URL
fallback. The synthetic records are retained for owner inspection after the run.
"""
import copy
import json
import os
import secrets
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid5

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.phase4b_database_safety import SafetyError, designated_url, inspect_empty_database

ORIGIN = "http://localhost:5173"
NAMESPACE = UUID("86ae0e9b-9d67-485b-ad05-8ac6ba9e98d9")


@pytest.fixture(scope="module")
def pg_acceptance(tmp_path_factory):
    if not os.environ.get("PHASE4B_TEST_DATABASE_URL"):
        pytest.skip("BLOCKED: PHASE4B_TEST_DATABASE_URL missing; no PostgreSQL connection attempted")
    try:
        url = designated_url()
        preflight = inspect_empty_database(url)
    except SafetyError as error:
        pytest.fail(str(error), pytrace=False)

    # Import application code only after the read-only server/catalog gate.
    from database import get_identity_db
    from identity_admin import bootstrap_admin, import_faculty
    from identity_models import FacultyIdentityRecord, User
    from main import app
    from routers import preferences
    from services import auth_service as auth, identity_service, metadata_service
    import identity_admin

    folder = tmp_path_factory.mktemp("phase4b-postgresql")
    identities = tuple(identity_service.FacultyIdentity(
        str(uuid5(NAMESPACE, str(code))), code, f"Phase4B Faculty {code}",
        f"Phase4B Synthetic Faculty {code}") for code in (0, 1))
    password = secrets.token_urlsafe(24)
    engine = create_engine(url, hide_parameters=True, connect_args={
        "connect_timeout": 5, "options": "-c statement_timeout=5000 -c lock_timeout=5000"})
    patch = pytest.MonkeyPatch()
    try:
        # Alembic's existing env.py reads DATABASE_URL. Set it explicitly to the
        # already verified test URL for this command only, never as a fallback.
        with pytest.MonkeyPatch.context() as migration_environment:
            migration_environment.setenv("DATABASE_URL", url.render_as_string(hide_password=False))
            command.upgrade(Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")), "head")
        patch.setattr(identity_service, "load_faculty_identities", lambda: identities)
        patch.setattr(identity_admin, "load_faculty_identities", lambda: identities)
        faculty = copy.deepcopy([member for member in metadata_service.scheduling.list_faculty if member.code in (0, 1)])
        for member in faculty:
            match = next((row for row in identities if row.faculty_code == member.code), None)
            if match: member.stable_id = match.faculty_id
        patch.setattr(metadata_service.scheduling, "list_faculty", faculty)
        with Session(engine) as db, db.begin():
            assert import_faculty(db) == 2
        barrier = Barrier(2)
        def first_admin(index):
            barrier.wait(timeout=10)
            try:
                with Session(engine) as db, db.begin():
                    created = bootstrap_admin(db, f"phase4b-bootstrap-{index}@test.invalid", password)
                return "created" if created else "retained"
            except ValueError:
                return "already_exists"
        with ThreadPoolExecutor(2) as pool:
            bootstrap_results = list(pool.map(first_admin, (0, 1)))
        with Session(engine) as db:
            admin = db.scalar(select(User).where(User.role == "admin"))
            admin_name = admin.username
            admin_id = admin.id
        def isolated_db():
            with Session(engine) as db:
                yield db
        patch.setattr(app, "dependency_overrides", {
            get_identity_db: isolated_db, auth.authenticated_db: isolated_db})
        patch.setattr(preferences, "PREFERENCE_FILE", folder / "preferences.json")
        patch.setattr(preferences, "GA_SETTINGS_FILE", folder / "settings.json")
        patch.setattr(auth, "LOGIN_LIMITER", auth.LoginLimiter())
        patch.setenv("AUTH_COOKIE_SECURE", "false")
        patch.setenv("AUTH_ALLOWED_ORIGINS", ORIGIN)
        from fastapi.middleware.cors import CORSMiddleware
        for middleware in app.user_middleware:
            if middleware.cls is CORSMiddleware:
                patch.setitem(middleware.kwargs, "allow_origins", [ORIGIN])
        patch.setattr(app, "middleware_stack", None)
        yield dict(app=app, engine=engine, password=password, identities=identities,
                   admin_name=admin_name, admin_id=admin_id, preflight=preflight,
                   bootstrap_results=bootstrap_results, folder=folder, patch=patch)
    finally:
        patch.undo()
        engine.dispose()


def login(state, username=None):
    client = TestClient(state["app"], base_url="http://localhost")
    response = client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={
        "username": username or state["admin_name"], "password": state["password"]})
    assert response.status_code == 200
    return client, {"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}


def test_real_migration_and_constraints(pg_acceptance):
    engine = pg_acceptance["engine"]
    with engine.connect() as connection:
        assert set(inspect(connection).get_table_names()) == {"alembic_version", "faculty_identities", "users", "login_sessions"}
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "4a_0001"
        assert {x["name"] for x in inspect(connection).get_check_constraints("users")} == {
            "ck_user_role", "ck_user_binding", "ck_username_lower"}
        assert len(inspect(connection).get_foreign_keys("users")) == 1
        assert len(inspect(connection).get_foreign_keys("login_sessions")) == 1
    assert pg_acceptance["preflight"]["read_only_preflight"]


def test_synthetic_identity_import_and_concurrent_bootstrap(pg_acceptance):
    from identity_admin import import_faculty
    from identity_models import FacultyIdentityRecord, User
    state = pg_acceptance
    assert sorted(state["bootstrap_results"]) == ["already_exists", "created"]
    with Session(state["engine"]) as db, db.begin():
        assert import_faculty(db) == 0
        assert len(list(db.scalars(select(FacultyIdentityRecord)))) == 2
        assert len(list(db.scalars(select(User).where(User.role == "admin")))) == 1


def test_faculty_creation_binding_and_duplicates(pg_acceptance):
    state = pg_acceptance
    with login(state)[0] as client:
        session = client.get("/api/auth/me").json()
        headers = {"Origin": ORIGIN, "X-CSRF-Token": session["csrf_token"]}
        for code in (0, 1):
            payload = dict(username=f"phase4b-faculty-{code}@test.invalid", password=state["password"],
                           role="faculty", faculty_id=state["identities"][code].faculty_id)
            assert client.post("/api/auth/users", headers=headers, json=payload).status_code == 201
        duplicate = dict(username="phase4b-faculty-0@test.invalid", password=state["password"], role="admin")
        assert client.post("/api/auth/users", headers=headers, json=duplicate).status_code == 409
        duplicate.update(username="phase4b-duplicate-binding@test.invalid", role="faculty", faculty_id=state["identities"][0].faculty_id)
        assert client.post("/api/auth/users", headers=headers, json=duplicate).status_code == 409


def test_integrity_failure_rolls_back_transaction(pg_acceptance):
    from identity_models import User
    with Session(pg_acceptance["engine"]) as db:
        db.add(User(username=pg_acceptance["admin_name"], password_hash="synthetic-unusable", role="admin"))
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()
        assert db.scalar(select(User.id).where(User.username == pg_acceptance["admin_name"]))


def test_genuine_login_ownership_and_preferences(pg_acceptance):
    state = pg_acceptance
    with login(state, "phase4b-faculty-0@test.invalid")[0] as client:
        session = client.get("/api/auth/me").json()
        headers = {"Origin": ORIGIN, "X-CSRF-Token": session["csrf_token"]}
        payload = {"gap_preference": "Compact", "gap_importance": 5, "use_gap_preference": True}
        assert client.put("/preferences/0", headers=headers, json=payload).status_code == 200
        assert client.get("/preferences/0").json()["gap_preference"] == "Compact"
        assert client.get("/preferences/1").status_code == 403
        assert client.put("/preferences/1", headers=headers, json=payload).status_code == 403
        assert client.get("/api/auth/users").status_code == 403
        assert client.get("/api/ga/status").status_code == 403


def test_session_persists_across_fresh_backend_processes(pg_acceptance):
    from services import auth_service as auth
    state = pg_acceptance
    client, _headers = login(state)
    script = """
import json,sys
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tests.phase4b_database_safety import designated_url
from routers.auth import router
from services import auth_service as auth
from database import get_identity_db
engine=create_engine(designated_url(),hide_parameters=True,connect_args={'connect_timeout':5,'options':'-c default_transaction_read_only=on'})
def db():
    with Session(engine) as session: yield session
app=FastAPI();app.include_router(router)
app.dependency_overrides={get_identity_db:db,auth.authenticated_db:db}
try:
    with TestClient(app,base_url='http://localhost') as client:
        client.cookies.set(auth.COOKIE_NAME,json.load(sys.stdin)['token'])
        print(json.dumps({'status':client.get('/api/auth/me').status_code}))
finally: engine.dispose()
"""
    try:
        token = client.cookies.get(auth.COOKIE_NAME)
        for _restart in range(2):
            child = subprocess.run([sys.executable, "-c", script],
                cwd=Path(__file__).resolve().parents[1], input=json.dumps({"token": token}),
                capture_output=True, text=True, timeout=30,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            assert token not in child.stdout + child.stderr
            assert child.returncode == 0, "Fresh backend process failed; private diagnostics withheld"
            assert json.loads(child.stdout.splitlines()[-1])["status"] == 200
    finally:
        client.close()


@pytest.mark.parametrize("violation", ["role", "binding", "username_case", "foreign_key"])
def test_real_database_rejects_invalid_rows(pg_acceptance, violation):
    from identity_models import User
    values = dict(username=f"phase4b-invalid-{violation}@test.invalid", password_hash="synthetic-unusable", role="admin")
    if violation == "role": values["role"] = "chair"
    if violation == "binding": values["role"] = "faculty"
    if violation == "username_case": values["username"] = "PHASE4B-INVALID@test.invalid"
    if violation == "foreign_key": values.update(role="faculty", faculty_id=uuid5(NAMESPACE, "unknown"))
    with Session(pg_acceptance["engine"]) as db:
        db.add(User(**values))
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()
        assert db.scalar(text("SELECT 1")) == 1


def test_logout_expiration_and_account_revocation(pg_acceptance):
    from identity_models import LoginSession, now
    from services import auth_service as auth
    state = pg_acceptance
    with login(state, "phase4b-faculty-0@test.invalid")[0] as faculty:
        headers = {"Origin": ORIGIN, "X-CSRF-Token": faculty.get("/api/auth/me").json()["csrf_token"]}
        assert faculty.post("/api/auth/logout", headers=headers).status_code == 204
        assert faculty.get("/api/auth/me").status_code == 401
    with login(state, "phase4b-faculty-0@test.invalid")[0] as faculty:
        digest = auth.token_hash(faculty.cookies.get(auth.COOKIE_NAME))
        with Session(state["engine"]) as db, db.begin():
            db.scalar(select(LoginSession).where(LoginSession.token_hash == digest)).expires_at = now() - timedelta(seconds=1)
        assert faculty.get("/api/auth/me").status_code == 401
    with login(state, "phase4b-faculty-0@test.invalid")[0] as faculty, login(state)[0] as admin:
        account = faculty.get("/api/auth/me").json()["user"]["id"]
        headers = {"Origin": ORIGIN, "X-CSRF-Token": admin.get("/api/auth/me").json()["csrf_token"]}
        assert admin.patch(f"/api/auth/users/{account}", headers=headers, json={"password": state["password"]}).status_code == 200
        assert faculty.get("/api/auth/me").status_code == 401


def test_database_unavailability_is_sanitized(pg_acceptance):
    from database import get_identity_db
    from services import auth_service as auth
    from sqlalchemy.exc import OperationalError
    state = pg_acceptance
    with login(state)[0] as client:
        class Unavailable:
            def __enter__(self): raise OperationalError("unavailable", {}, RuntimeError("synthetic outage"))
            def __exit__(self, *_args): return False
        def engine_unavailable():
            import database
            with pytest.MonkeyPatch.context() as patch:
                patch.setattr(database, "identity_engine", lambda: state["engine"])
                patch.setattr(database, "sessionmaker", lambda *_args, **_kwargs: Unavailable)
                yield from get_identity_db()
        with pytest.MonkeyPatch.context() as patch:
            patch.setitem(state["app"].dependency_overrides, auth.authenticated_db, engine_unavailable)
            response = client.get("/api/auth/me")
        assert response.status_code == 503
        assert "synthetic outage" not in response.text


def test_real_lock_timeout_rolls_back(pg_acceptance):
    from identity_models import User
    state = pg_acceptance
    with Session(state["engine"]) as holder, Session(state["engine"]) as waiter:
        holder.get(User, state["admin_id"], with_for_update=True)
        waiter.execute(text("SET LOCAL lock_timeout = '200ms'"))
        from sqlalchemy.exc import OperationalError
        with pytest.raises(OperationalError): waiter.get(User, state["admin_id"], with_for_update=True)
        waiter.rollback()
        assert waiter.scalar(text("SELECT 1")) == 1
        holder.rollback()


def test_concurrent_last_administrator_protection(pg_acceptance):
    from identity_models import User
    from routers.auth import update_user
    from schemas.auth import UpdateAccount
    from services import auth_service as auth
    state = pg_acceptance
    with Session(state["engine"]) as db, db.begin():
        second = User(username="phase4b-second-admin@test.invalid", password_hash=auth.hash_password(state["password"]), role="admin")
        db.add(second); db.flush(); ids = [state["admin_id"], second.id]
    barrier = Barrier(2)
    def disable(identity):
        with Session(state["engine"]) as db:
            barrier.wait(timeout=10)
            try:
                update_user(identity, UpdateAccount(is_active=False), db=db)
                return 200
            except HTTPException as error:
                db.rollback(); return error.status_code
    with ThreadPoolExecutor(2) as pool: results = list(pool.map(disable, ids))
    assert sorted(results) == [200, 409]
    with Session(state["engine"]) as db:
        assert len(list(db.scalars(select(User).where(User.role == "admin", User.is_active.is_(True))))) == 1
