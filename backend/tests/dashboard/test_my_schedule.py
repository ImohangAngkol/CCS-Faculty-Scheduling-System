"""Real FastAPI password/session/ownership tests; SQLite and synthetic inputs only."""
import copy
from datetime import timedelta
import hashlib
import json
import random
import secrets
from types import SimpleNamespace
from uuid import UUID

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import Session

from database import get_identity_db
from identity_models import Base, FacultyIdentityRecord, User, LoginSession, now
from main import app
from routers import genetic_algorithm as ga_router
from services import auth_service as auth, ga_service, metadata_service, identity_service, schedule_service
from services.identity_service import FacultyIdentity
from genetic_algorithm.models.Faculty import Faculty
from genetic_algorithm.models.Subject import Subject
from genetic_algorithm.models.Section import Section
from genetic_algorithm.models.Room import Room

ORIGIN = "http://localhost:5173"
IDS = [UUID(f"20000000-0000-4000-8000-{i+1:012d}") for i in range(3)]


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path/'identity.sqlite'}", connect_args={"check_same_thread": False})
    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine, tables=[FacultyIdentityRecord.__table__, User.__table__, LoginSession.__table__])
    identities = tuple(FacultyIdentity(str(identity), i, f"Synthetic Faculty {i}", f"Synthetic Lecturer {i}") for i, identity in enumerate(IDS))
    monkeypatch.setattr(identity_service, "load_faculty_identities", lambda: identities)
    members = [Faculty(i, 1, admin_load=24, eligible_subjects={"SYN101", "SYN202"}) for i in range(3)]
    for member, identity in zip(members, identities):
        member.stable_id = identity.faculty_id
        member.display_code = identity.display_code
        member.name = identity.name
    courses = [Subject("SYN101", "Synthetic Programming", 4, 3, 3, Section("SYN-A")),
               Subject("SYN202", "Other private synthetic assignment", 3, 3, 0, Section("SYN-B"))]
    rooms = [Room("SYN LEC", "Lecture"), Room("SYN LAB", "Laboratory")]
    monkeypatch.setattr(metadata_service.scheduling, "list_faculty", members)
    for key, value in [("list_faculty", members), ("list_subjects", courses), ("lst_rooms", rooms)]:
        monkeypatch.setattr(ga_service, key, value)
    rows = [dict(subject="SYN101", title="Synthetic Programming", section="SYN-A", type="Lecture", day="M", start="07:30", end="10:30", room="SYN LEC", faculty="0"),
            dict(subject="SYN101", title="Synthetic Programming", section="SYN-A", type="Laboratory", day="W", start="13:00", end="16:00", room="SYN LAB", faculty="0"),
            dict(subject="SYN202", title="Other private synthetic assignment", section="SYN-B", type="Lecture", day="T", start="07:30", end="10:30", room="SYN LEC", faculty="1")]
    payload = {"status": "COMPLETED", "best_fitness": 1234567, "fitness_breakdown": {"private": "not-returned"},
               "run_id": "not-returned", "faculty_analysis": [{"private": "not-returned"}], "schedule": rows}
    path = tmp_path / "latest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(ga_router, "LATEST_RESULT_FILE", path)
    password = secrets.token_urlsafe(24)
    hashed = auth.hash_password(password)
    with Session(engine) as db, db.begin():
        for i, identity in enumerate(identities):
            db.add(FacultyIdentityRecord(id=IDS[i], display_code=identity.display_code, name=identity.name))
        db.flush()
        for i in range(3):
            db.add(User(username=f"faculty{i}@example.invalid", password_hash=hashed, role="faculty", faculty_id=IDS[i], is_active=True))
        db.add(User(username="admin@example.invalid", password_hash=hashed, role="admin", is_active=True))
    def db_session():
        with Session(engine) as db:
            yield db
    monkeypatch.setattr(app, "dependency_overrides", {get_identity_db: db_session, auth.authenticated_db: db_session})
    monkeypatch.setattr(auth, "LOGIN_LIMITER", auth.LoginLimiter())
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", ORIGIN)
    with TestClient(app, base_url="http://localhost") as client:
        yield SimpleNamespace(client=client, engine=engine, password=password, payload=payload, path=path, members=members, courses=courses, rooms=rooms)
    engine.dispose()


def login(fixture, number=0):
    username = "admin@example.invalid" if number == "admin" else f"faculty{number}@example.invalid"
    reply = fixture.client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={"username": username, "password": fixture.password})
    assert reply.status_code == 200


def test_real_sessions_receive_only_their_own_allowlisted_assignments(fixture):
    for i, expected in [(0, ["SYN101", "SYN101"]), (1, ["SYN202"])]:
        login(fixture, i)
        reply = fixture.client.get("/api/schedules/me")
        assert reply.status_code == 200, reply.json()
        data = reply.json()
        assert data["faculty_id"] == str(IDS[i]) and data["faculty_code"] == i
        assert [row["subject"] for row in data["assignments"]] == expected
        assert set(data) == {"schema_version", "availability", "faculty_id", "faculty_code", "source", "assignments"}
        assert set(data["assignments"][0]) == {"subject", "title", "section", "type", "day", "start", "end", "room"}
        assert data["source"]["label"] == "GA-generated proposal"
        assert data["source"]["freshness"] == "not_recorded"
        assert "best_fitness" not in reply.text and "not-returned" not in reply.text
        assert reply.headers["cache-control"] == "no-store"
        if i == 0:
            assert "Other private" not in reply.text and "SYN202" not in reply.text
            assert [row["type"] for row in data["assignments"]] == ["Lecture", "Laboratory"]


@pytest.mark.parametrize("query", ["faculty_code=1", f"faculty_id={IDS[1]}", "user_id=other", "path=other.json"])
def test_query_selectors_are_rejected_without_data(fixture, query):
    login(fixture)
    reply = fixture.client.get("/api/schedules/me?"+query)
    assert reply.status_code == 400 and "assignments" not in reply.json()


def test_forged_headers_and_get_body_do_not_change_identity(fixture):
    login(fixture)
    reply = fixture.client.request("GET", "/api/schedules/me", headers={"X-Faculty-ID": str(IDS[1]), "X-Faculty-Code": "1", "X-Role": "admin"}, json={"faculty_id": str(IDS[1])})
    assert reply.status_code == 200 and reply.json()["faculty_id"] == str(IDS[0])
    assert "SYN202" not in reply.text
    assert fixture.client.get(f"/api/schedules/{IDS[1]}").status_code == 404
    assert fixture.client.get("/api/ga/latest").status_code == 403


@pytest.mark.parametrize("mode", ["anonymous", "forged", "expired", "disabled", "revoked", "admin"])
def test_authentication_and_role_fail_before_source_access(fixture, monkeypatch, mode):
    if mode != "anonymous":
        login(fixture, "admin" if mode == "admin" else 0)
    with Session(fixture.engine) as db, db.begin():
        if mode == "expired": db.scalar(select(LoginSession)).expires_at = now()-timedelta(seconds=1)
        if mode == "disabled": db.scalar(select(User).where(User.username=="faculty0@example.invalid")).is_active = False
        if mode == "revoked": db.delete(db.scalar(select(LoginSession)))
    if mode == "forged": fixture.client.cookies.set(auth.COOKIE_NAME, "forged-session")
    monkeypatch.setattr(schedule_service, "_read", lambda path: pytest.fail("Unauthorized source access"))
    reply = fixture.client.get("/api/schedules/me")
    assert reply.status_code == (403 if mode == "admin" else 401)
    assert "assignments" not in reply.json()


@pytest.mark.parametrize("mode", ["missing", "unknown", "renumbered", "wrong_stable_id"])
def test_binding_failures_never_guess_an_identity(fixture, monkeypatch, mode):
    login(fixture)
    if mode in {"missing", "unknown"}:
        # Simulate legacy/corrupt binding without weakening production constraints.
        with fixture.engine.connect() as c:
            c.exec_driver_sql("PRAGMA foreign_keys=OFF")
            c.exec_driver_sql("PRAGMA ignore_check_constraints=ON")
            c.execute(text("UPDATE users SET faculty_id=:value WHERE username='faculty0@example.invalid'"), {"value": None if mode=="missing" else "30000000000040008000000000000009"})
            c.commit()
    elif mode == "renumbered": fixture.members[0].code = 99
    else: fixture.members[0].stable_id = str(IDS[1])
    monkeypatch.setattr(schedule_service, "_read", lambda path: pytest.fail("Invalid binding read source"))
    reply = fixture.client.get("/api/schedules/me")
    assert reply.status_code == 403 and reply.json()["detail"]["code"] == "SCHEDULE_BINDING_INVALID"


def test_missing_result_and_no_own_assignments_are_distinct(fixture):
    login(fixture, 2)
    data = fixture.client.get("/api/schedules/me").json()
    assert data["availability"] == "empty" and data["assignments"] == []
    fixture.path.unlink()  # Owned synthetic source only.
    data = fixture.client.get("/api/schedules/me").json()
    assert data["availability"] == "missing" and data["source"]["saved_at"] is None


@pytest.mark.parametrize("content", ['{broken', 'null', '{"schedule":[]}', '{"schedule":[],"schedule":[]}', '{"schedule":NaN}'])
def test_corrupt_or_incompatible_sources_never_leak_rows(fixture, content):
    login(fixture)
    fixture.path.write_text(content, encoding="utf-8")
    reply = fixture.client.get("/api/schedules/me")
    assert reply.status_code in {409, 503} and "assignments" not in reply.json()
    assert str(fixture.path) not in reply.text


@pytest.mark.parametrize("change", ["offering", "room", "hours", "status"])
def test_stale_source_fails_closed_with_sanitized_error(fixture, change):
    login(fixture)
    payload = copy.deepcopy(fixture.payload)
    if change == "offering": payload["schedule"][2]["subject"] = "PRIVATE-UNKNOWN"
    if change == "room": payload["schedule"][0]["room"] = "PRIVATE-ROOM"
    if change == "hours": payload["schedule"][0]["end"] = "08:00"
    if change == "status": payload["status"] = "STOPPED"
    fixture.path.write_text(json.dumps(payload), encoding="utf-8")
    reply = fixture.client.get("/api/schedules/me")
    assert reply.status_code == 409 and reply.json()["detail"]["code"] == "SCHEDULE_SOURCE_STALE"
    assert "PRIVATE" not in reply.text and "assignments" not in reply.json()


def test_source_replaced_during_validation_is_rejected(fixture, monkeypatch):
    login(fixture)
    real = ga_service.validate_saved_result
    def changed(payload):
        real(payload)
        fixture.path.write_text(json.dumps(fixture.payload)+" ", encoding="utf-8")
    monkeypatch.setattr(ga_service, "validate_saved_result", changed)
    reply = fixture.client.get("/api/schedules/me")
    assert reply.status_code == 409 and reply.json()["detail"]["code"] == "SCHEDULE_SOURCE_CHANGED"


def test_stable_source_after_overwrite_is_not_falsely_reported_changed(fixture):
    login(fixture)
    for i in range(2):
        fixture.path.write_text(json.dumps(fixture.payload)+(" "*i), encoding="utf-8")
        assert fixture.client.get("/api/schedules/me").status_code == 200


def test_reads_preserve_storage_templates_database_rng_and_do_not_score(fixture, monkeypatch):
    login(fixture)
    def digest_database():
        with fixture.engine.connect() as c:
            data = [c.exec_driver_sql(f"SELECT * FROM {table} ORDER BY id").all() for table in ["users", "login_sessions", "faculty_identities"]]
        return hashlib.sha256(repr(data).encode()).hexdigest()
    import genetic_algorithm.operators.FitnessFunction as fitness
    monkeypatch.setattr(fitness, "faculty_preference_fitness", lambda *a, **k: pytest.fail("Unexpected fitness call"))
    files = {p:p.read_bytes() for p in fixture.path.parent.iterdir() if p.is_file()}
    database = digest_database(); rng = random.getstate(); numpy_rng = np.random.get_state()
    profiles = [(copy.deepcopy(vars(member))) for member in fixture.members]
    for _ in range(2): assert fixture.client.get("/api/schedules/me").status_code == 200
    assert digest_database() == database and random.getstate() == rng
    current = np.random.get_state()
    assert current[0] == numpy_rng[0] and np.array_equal(current[1], numpy_rng[1]) and current[2:] == numpy_rng[2:]
    assert all(p.read_bytes()==value for p,value in files.items())
    assert all(member.current_teaching_load == before["current_teaching_load"] and member.subjects_assigned == before["subjects_assigned"] for member,before in zip(fixture.members, profiles))
