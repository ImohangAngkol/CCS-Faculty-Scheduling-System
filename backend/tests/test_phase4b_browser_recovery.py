"""Offline recovery tests. Fake PG catalogs; no real socket, service or PG DB."""
from contextlib import contextmanager
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import random
import sqlite3
import subprocess
import sys
import threading
from types import SimpleNamespace
from uuid import uuid4

import pytest
import sqlalchemy
from sqlalchemy.dialects import postgresql as pg

from tests import phase4b_browser_recovery as recovery
from tests import phase4b_browser_safety as safety
from tests import phase4b_browser_support as support
from tests.phase4b_database_safety import SafetyError

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    def forbidden(*_a, **_k): pytest.fail("Real PostgreSQL/service/migration forbidden in offline recovery tests")
    monkeypatch.setattr(recovery, "create_engine", forbidden)
    monkeypatch.setattr(safety, "create_engine", forbidden)
    monkeypatch.setattr(sqlalchemy, "create_engine", forbidden)
    from alembic import command
    import uvicorn
    monkeypatch.setattr(command, "upgrade", forbidden)
    monkeypatch.setattr(uvicorn.Server, "run", forbidden)


class Result:
    def __init__(self, rows=(), scalar=None, rowcount=1):
        self.rows, self.scalar, self.rowcount = list(rows), scalar, rowcount
    def mappings(self): return self
    def scalars(self): return self
    def one(self): return self.rows[0]
    def all(self): return self.rows
    def first(self): return self.rows[0] if self.rows else None
    def scalar_one(self): return self.scalar


class Catalog:
    def __init__(self):
        self.schemas = ["information_schema", "pg_catalog", "public"]
        self.tables = list(recovery.COLUMNS)
        self.columns, self.pks, self.uniques, self.fks, self.checks, self.indexes = ({ } for _ in range(6))
        types = {"uuid": pg.UUID(), "boolean": pg.BOOLEAN(), "timestamptz": pg.TIMESTAMP(timezone=True)}
        for table, columns in recovery.COLUMNS.items():
            self.columns[table] = [dict(name=name, type=pg.VARCHAR(int(kind.split(":")[1])) if kind.startswith("varchar:") else types[kind], nullable=nullable, default=None)
                                   for name, (kind, nullable) in columns.items()]
            self.pks[table] = dict(name="alembic_version_pkc" if table == "alembic_version" else table+"_pkey",
                                  constrained_columns=["version_num" if table == "alembic_version" else "id"])
            unique = {"alembic_version": [], "faculty_identities": ["display_code"], "users": ["username", "faculty_id"], "login_sessions": ["token_hash"]}[table]
            self.uniques[table] = [dict(name=table+"_"+col+"_key", column_names=[col], dialect_options={"postgresql_nulls_not_distinct": False}) for col in unique]
            self.indexes[table] = [dict(name=u["name"], column_names=u["column_names"], unique=True, dialect_options={"postgresql_include": []}) for u in self.uniques[table]]
            self.fks[table] = []
            if table in ("users", "login_sessions"):
                col, target, ondelete = ("faculty_id", "faculty_identities", "RESTRICT") if table == "users" else ("user_id", "users", "CASCADE")
                self.fks[table] = [dict(name=table+"_"+col+"_fkey", constrained_columns=[col], referred_table=target,
                                       referred_schema=None, referred_columns=["id"], options={"ondelete": ondelete})]
            self.checks[table] = [dict(name=name, sqltext=sql) for name, sql in recovery.CHECKS.items()] if table == "users" else []
        self.indexes["login_sessions"] += [dict(name="ix_login_sessions_"+col, column_names=[col], unique=False) for col in ("user_id", "expires_at")]
    def get_schema_names(self): return self.schemas
    def get_table_names(self, **_kw): return self.tables
    def get_columns(self, name, **_kw): return self.columns[name]
    def get_pk_constraint(self, name, **_kw): return self.pks[name]
    def get_unique_constraints(self, name, **_kw): return self.uniques[name]
    def get_foreign_keys(self, name, **_kw): return self.fks[name]
    def get_check_constraints(self, name, **_kw): return self.checks[name]
    def get_indexes(self, name, **_kw): return self.indexes[name]


class Database:
    def __init__(self):
        self.server = dict(database=safety.BROWSER_DATABASE, role=safety.BROWSER_ROLE, owner=safety.BROWSER_ROLE,
                           host="127.0.0.1", port=5432, schema="public", read_only="on", can_create=True,
                           rolsuper=False, rolcreatedb=False, rolcreaterole=False, rolreplication=False, rolbypassrls=False)
        self.revisions, self.identities = [recovery.REVISION], list(recovery.IDENTITIES)
        self.users = [dict(id=uuid4(), username=recovery.ADMIN, role="admin", faculty_id=None, is_active=True)]
        self.sessions, self.extra, self.lock_available = 0, False, True
        self.version = 180006
        self.not_null = [(table, name, table+'_'+name+'_not_null') for table, columns in recovery.COLUMNS.items()
                         for name, (_, nullable) in columns.items() if not nullable]
        self.info, self.sql, self.writes = {}, [], []
        self.closed = self.disposed = self.committed = self.aborted = False
        self.update_count = 1
    def execute(self, statement, parameters=None):
        sql = str(statement); self.sql.append(sql)
        if sql.startswith("SELECT current_database"): return Result([self.server.copy()])
        if "pg_try_advisory_lock" in sql: return Result(scalar=self.lock_available)
        if "pg_advisory_unlock" in sql: return Result(scalar=True)
        if sql.startswith("SELECT 1 FROM pg_proc"): return Result([(1,)] if self.extra else [])
        if sql.startswith("SELECT current_setting"): return Result(scalar=self.version)
        if sql.startswith("SELECT t.relname"): return Result(self.not_null)
        if sql.startswith("SELECT version_num"): return Result(self.revisions)
        if sql.startswith("SELECT id, display_code"): return Result(self.identities)
        if sql.startswith("SELECT id, username"): return Result(self.users)
        if sql.startswith("SELECT count(*)"): return Result(scalar=self.sessions)
        if sql.startswith("SET TRANSACTION READ WRITE"):
            self.server["read_only"] = "off"; return Result()
        if sql.startswith("LOCK TABLE"): return Result()
        if sql.startswith("UPDATE public.users"):
            self.writes.append((sql, parameters.copy())); return Result(rowcount=self.update_count)
        raise AssertionError("Unexpected offline SQL shape")
    def rollback(self): pass
    @contextmanager
    def begin(self):
        before = len(self.writes)
        try:
            yield self
            self.committed = True
        except BaseException:
            self.writes[before:] = []
            self.aborted = True
            raise
        finally:
            self.server["read_only"] = "on"
    def connect(self): return self
    def __enter__(self): return self
    def __exit__(self, *_a): self.close()
    def execution_options(self, **kw):
        assert kw == {"isolation_level": "REPEATABLE READ"}; return self
    def close(self): self.closed = True
    def dispose(self): self.disposed = True


@pytest.fixture
def catalog_db(monkeypatch):
    db, catalog = Database(), Catalog()
    monkeypatch.setattr(recovery, "inspect", lambda connection: catalog)
    return db, catalog


def url(**overrides):
    return sqlalchemy.URL.create(**dict(dict(drivername="postgresql+psycopg2", username=safety.BROWSER_ROLE,
        host="127.0.0.1", port=5432, database=safety.BROWSER_DATABASE), **overrides))


def test_pristine_profile_is_read_only_and_never_selects_secrets(catalog_db):
    db, _ = catalog_db
    assert recovery.verify_recovery(db) == db.users[0]["id"]
    assert all(sql.startswith("SELECT") for sql in db.sql)
    projections = [sql.split("FROM")[0].lower() for sql in db.sql]
    assert not any(secret in projection for projection in projections for secret in ("password_hash", "token_hash", "csrf_token"))
    assert not db.writes


def test_recovery_column_and_check_profile_matches_actual_migration(monkeypatch):
    """Execute only migration declarations into metadata, never an engine/DDL."""
    metadata = sqlalchemy.MetaData()
    class Declarations:
        def create_table(self, name, *columns): return sqlalchemy.Table(name, metadata, *columns)
        def create_index(self, name, table, columns): sqlalchemy.Index(name, *(metadata.tables[table].c[c] for c in columns))
    spec = importlib.util.spec_from_file_location("offline_identity_declarations", ROOT/"backend/migrations/versions/4a_0001_identity.py")
    migration = importlib.util.module_from_spec(spec); spec.loader.exec_module(migration)
    monkeypatch.setattr(migration, "op", Declarations())
    migration.upgrade()  # declarations only; no Alembic command/context/connection
    assert migration.revision == recovery.REVISION
    for name, table in metadata.tables.items():
        actual = {}
        for column in table.columns:
            rendered = column.type.compile(dialect=pg.dialect())
            kind = "varchar:"+str(column.type.length) if rendered.startswith("VARCHAR(") else {
                "UUID": "uuid", "BOOLEAN": "boolean", "TIMESTAMP WITH TIME ZONE": "timestamptz"}[rendered]
            actual[column.name] = kind, column.nullable
            assert column.server_default is None
        assert actual == recovery.COLUMNS[name]
    assert {c.name: recovery.check_tree(str(c.sqltext)) for c in metadata.tables["users"].constraints
            if isinstance(c, sqlalchemy.CheckConstraint)} == {k: recovery.check_tree(v) for k, v in recovery.CHECKS.items()}


@pytest.mark.parametrize("key,value", [
    ("database", "ccs_ga_phase4b_test"), ("role", "postgres"), ("host", "::1"), ("host", "127.0.0.1/32"),
    ("port", 5433), ("schema", "other"), ("owner", "postgres"), ("read_only", "off"),
    ("rolsuper", True), ("rolcreatedb", True), ("rolcreaterole", True), ("rolreplication", True),
    ("rolbypassrls", True), ("can_create", False), ("rolsuper", None),
])
def test_server_mismatch_rejected_before_catalog(catalog_db, key, value):
    db, _ = catalog_db; db.server[key] = value
    with pytest.raises(SafetyError): recovery.verify_recovery(db)
    assert len(db.sql) == 1 and not db.writes


@pytest.mark.parametrize("override", [dict(database="ccs_ga_phase4b_test"), dict(database="ccs_faculty_scheduling_dev"),
    dict(username="postgres"), dict(host="localhost"), dict(host="::1"), dict(port=5433), dict(query={"sslmode": "disable"})])
def test_bad_target_never_constructs_engine(override):
    with pytest.raises(SafetyError):
        with recovery.claim_browser_database(url(**override)): pytest.fail("Must not own wrong target")


@pytest.mark.parametrize("case", ["schema", "table", "column", "type", "nullable", "default", "computed", "identity",
    "pk", "unique", "unique_semantics", "fk", "fk_target", "fk_delete", "check", "check_grouping", "index", "partial_index", "objects"])
def test_schema_drift_rejected(catalog_db, case):
    db, catalog = catalog_db
    if case == "schema": catalog.schemas.append("other")
    if case == "table": catalog.tables.append("unexpected")
    if case == "column": catalog.columns["users"].append(dict(name="extra", type=pg.VARCHAR(1), nullable=True))
    if case == "type": catalog.columns["users"][1]["type"] = pg.VARCHAR(255)
    if case == "nullable": catalog.columns["users"][1]["nullable"] = True
    if case in ("default", "computed", "identity"): catalog.columns["users"][0][case] = "unexpected"
    if case == "pk": catalog.pks["users"]["constrained_columns"] = ["username"]
    if case == "unique": catalog.uniques["users"].pop()
    if case == "unique_semantics": catalog.uniques["users"][0]["dialect_options"]["postgresql_nulls_not_distinct"] = True
    if case == "fk": catalog.fks["users"].clear()
    if case == "fk_target": catalog.fks["users"][0]["referred_schema"] = "other"
    if case == "fk_delete": catalog.fks["users"][0]["options"]["ondelete"] = "CASCADE"
    if case == "check": catalog.checks["users"][0]["sqltext"] = "role IN ('admin', 'faculty', 'other')"
    if case == "check_grouping": catalog.checks["users"][1]["sqltext"] = "(role = 'admin' AND faculty_id IS NULL OR role = 'faculty') AND faculty_id IS NOT NULL"
    if case == "index": catalog.indexes["users"].append(dict(name="extra", column_names=["id"], unique=False))
    if case == "partial_index": catalog.indexes["users"][0]["dialect_options"] = {"postgresql_where": "is_active"}
    if case == "objects": db.extra = True
    with pytest.raises(SafetyError): recovery.verify_recovery(db)
    assert not db.writes


@pytest.mark.parametrize("case", ["revision", "extra_revision", "missing_identity", "extra_identity", "changed_identity",
    "extra_account", "wrong_account", "faculty_account", "disabled", "bound_admin", "session"])
def test_content_drift_rejected(catalog_db, case):
    db, _ = catalog_db
    if case == "revision": db.revisions = ["other"]
    if case == "extra_revision": db.revisions.append("other")
    if case == "missing_identity": db.identities.pop()
    if case == "extra_identity": db.identities.append((uuid4(), "extra", "extra"))
    if case == "changed_identity": db.identities[0] = (db.identities[0][0], "wrong", "wrong")
    if case == "extra_account": db.users.append(db.users[0].copy())
    if case == "wrong_account": db.users[0]["username"] = "unexpected@test.invalid"
    if case == "faculty_account": db.users[0]["role"] = "faculty"
    if case == "disabled": db.users[0]["is_active"] = False
    if case == "bound_admin": db.users[0]["faculty_id"] = uuid4()
    if case == "session": db.sessions = 1
    with pytest.raises(SafetyError): recovery.verify_recovery(db)
    assert not db.writes


def test_pg_reflected_checks_and_boolean_grouping():
    assert recovery.check_tree("((role)::text = ANY ((ARRAY['admin'::character varying, 'faculty'::character varying])::text[]))") == recovery.check_tree(recovery.CHECKS["ck_user_role"])
    assert recovery.check_tree("((username)::text = lower((username)::text))") == recovery.check_tree(recovery.CHECKS["ck_username_lower"])
    assert recovery.check_tree("(((role)::text = 'admin'::text) AND (faculty_id IS NULL)) OR (((role)::text = 'faculty'::text) AND (faculty_id IS NOT NULL))") == recovery.check_tree(recovery.CHECKS["ck_user_binding"])
    for sql in ("role = 'admin'; SELECT 1", "true", "role IN ('admin::text','faculty')", "role = lower(username)"):
        try: parsed = recovery.check_tree(sql)
        except SafetyError: continue
        assert parsed != recovery.check_tree(recovery.CHECKS["ck_user_role"])


@pytest.mark.parametrize("case", ["pre18", "missing", "renamed", "duplicate", "extra"])
def test_pg18_not_null_catalog_validation(catalog_db, case):
    db, _ = catalog_db
    if case == "pre18":
        db.version, db.not_null = 170000, []
        recovery.verify_recovery(db)
        return
    if case == "missing": db.not_null.pop()
    if case == "renamed": db.not_null[0] = (*db.not_null[0][:2], "unexpected")
    if case == "duplicate": db.not_null.append(db.not_null[0])
    if case == "extra": db.not_null.append(("users", "faculty_id", "users_faculty_id_not_null"))
    with pytest.raises(SafetyError, match="NOT NULL"): recovery.verify_recovery(db)


def test_claim_retained_until_exit_and_released_after_failure(catalog_db, monkeypatch):
    db, _ = catalog_db
    def engine(_url, **kw):
        assert kw["hide_parameters"] and "default_transaction_read_only=on" in kw["connect_args"]["options"]
        return db
    monkeypatch.setattr(recovery, "create_engine", engine)
    with pytest.raises(RuntimeError):
        with recovery.claim_browser_database(url()) as held:
            assert held.info["phase4b_browser_claim"] and not db.closed
            assert not any("pg_advisory_unlock" in sql for sql in db.sql)
            raise RuntimeError("offline injected failure")
    assert db.closed and db.disposed and not db.info
    assert any("pg_advisory_unlock" in sql for sql in db.sql)


def test_second_owner_rejected_without_unlocking_another_owner(catalog_db, monkeypatch):
    db, _ = catalog_db; db.lock_available = False
    monkeypatch.setattr(recovery, "create_engine", lambda *_a, **_kw: db)
    with pytest.raises(SafetyError, match="Another browser"):
        with recovery.claim_browser_database(url()): pytest.fail("Duplicate worker")
    assert db.closed and db.disposed and not any("pg_advisory_unlock" in s for s in db.sql)


def test_read_only_public_preflight_redacted_and_disposed(catalog_db, monkeypatch):
    db, _ = catalog_db
    monkeypatch.setattr(recovery, "create_engine", lambda *_a, **_k: db)
    report = recovery.inspect_browser_recovery_database(url())
    assert report["recovery_profile_valid"] and report["sessions"] == 0 and db.closed and db.disposed
    assert all(s.startswith("SELECT") for s in db.sql) and not db.writes
    assert "username" not in report and "id" not in report


def test_read_only_preflight_masks_library_failure(monkeypatch):
    def fail(*_a, **_k): raise RuntimeError("offline secret URL and credentials")
    monkeypatch.setattr(recovery, "create_engine", fail)
    with pytest.raises(SafetyError) as error: recovery.inspect_browser_recovery_database(url())
    assert "offline secret" not in str(error.value)


def test_two_overlapping_owners_only_one_succeeds(catalog_db, monkeypatch):
    lock = threading.Lock(); acquired = threading.Event(); release = threading.Event(); errors = []
    class Shared(Database):
        def execute(self, statement, parameters=None):
            if "pg_try_advisory_lock" in str(statement): return Result(scalar=lock.acquire(blocking=False))
            if "pg_advisory_unlock" in str(statement): lock.release(); return Result(scalar=True)
            return super().execute(statement, parameters)
    monkeypatch.setattr(recovery, "create_engine", lambda *_a, **_k: Shared())
    def first():
        try:
            with recovery.claim_browser_database(url()):
                acquired.set(); assert release.wait(5)
        except BaseException as error: errors.append(type(error).__name__)
    worker = threading.Thread(target=first)
    worker.start()
    try:
        assert acquired.wait(5)
        with pytest.raises(SafetyError, match="Another browser"):
            with recovery.claim_browser_database(url()): pytest.fail("Duplicate owner")
    finally:
        release.set(); worker.join(timeout=5)
    assert not worker.is_alive() and not errors and not lock.locked()


def test_rotation_only_updates_verified_admin_without_rng_or_fitness(catalog_db, monkeypatch):
    db, _ = catalog_db; db.info["phase4b_browser_claim"] = True
    from services import auth_service
    monkeypatch.setattr(auth_service, "hash_password", lambda _password: "offline-new-encoded-value")
    from genetic_algorithm.operators import FitnessFunction
    monkeypatch.setattr(FitnessFunction, "faculty_preference_fitness", lambda *_a, **_k: pytest.fail("No fitness call"))
    before, identities, users = random.getstate(), deepcopy(db.identities), deepcopy(db.users)
    assert recovery.rotate_browser_administrator(db, "offline-private-password", approved=True) == recovery.ADMIN
    assert random.getstate() == before and db.identities == identities and db.users == users
    assert db.committed and len(db.writes) == 1
    statement, parameters = db.writes[0]
    assert "SET password_hash=:encoded, updated_at=CURRENT_TIMESTAMP" in statement
    assert parameters["id"] == users[0]["id"] and parameters["username"] == recovery.ADMIN
    last_select = max(i for i, s in enumerate(db.sql) if s.startswith("SELECT"))
    assert last_select == db.sql.index(statement) - 1
    assert next(i for i, s in enumerate(db.sql) if s.startswith("LOCK TABLE")) < last_select
    assert not any(s.startswith(("DELETE", "INSERT", "TRUNCATE", "CREATE", "ALTER", "DROP")) for s in db.sql)


@pytest.mark.parametrize("failure", ["approval", "lock", "concurrent_session", "rowcount"])
def test_rotation_fail_closed_and_transaction_rollback(catalog_db, monkeypatch, failure):
    db, _ = catalog_db
    from services import auth_service
    monkeypatch.setattr(auth_service, "hash_password", lambda _p: "offline-encoded")
    db.info["phase4b_browser_claim"] = failure != "lock"
    if failure == "concurrent_session": db.sessions = 1
    if failure == "rowcount": db.update_count = 0
    with pytest.raises(SafetyError): recovery.rotate_browser_administrator(db, "offline-password", approved=failure != "approval")
    assert not db.writes and not db.committed


@pytest.mark.parametrize("fail_after_update", [False, True])
def test_real_sqlite_rotation_commit_or_rollback_without_reading_old_hash(monkeypatch, fail_after_update):
    """SQLite verifies UPDATE/transaction behavior only, not PostgreSQL locks."""
    store = sqlite3.connect(":memory:", isolation_level=None)
    store.execute("ATTACH DATABASE ':memory:' AS public")
    store.execute("CREATE TABLE public.users(id TEXT PRIMARY KEY, username TEXT, role TEXT, faculty_id TEXT, is_active BOOLEAN, password_hash TEXT, updated_at TEXT)")
    identifier = str(uuid4())
    store.execute("INSERT INTO public.users VALUES(?, ?, 'admin', NULL, true, 'offline-original', NULL)", (identifier, recovery.ADMIN))
    from services import auth_service
    monkeypatch.setattr(auth_service, "hash_password", lambda _p: "offline-rotated")
    checked = []
    def verify(_db, *, read_only): checked.append(read_only); return identifier
    monkeypatch.setattr(recovery, "verify_recovery", verify)
    class Adapter:
        info = {"phase4b_browser_claim": True}
        def rollback(self): pass
        @contextmanager
        def begin(self):
            store.execute("BEGIN")
            try: yield; store.execute("COMMIT")
            except BaseException: store.execute("ROLLBACK"); raise
        def execute(self, statement, parameters=None):
            if str(statement).startswith(("SET TRANSACTION", "LOCK TABLE")): return Result()
            assert str(statement).startswith("UPDATE public.users")
            cursor = store.execute(str(statement), parameters)
            return Result(rowcount=0 if fail_after_update else cursor.rowcount)
    try:
        if fail_after_update:
            with pytest.raises(SafetyError): recovery.rotate_browser_administrator(Adapter(), "offline-password", approved=True)
        else: recovery.rotate_browser_administrator(Adapter(), "offline-password", approved=True)
        # Return booleans only; no old credential value is selected by recovery.
        assert store.execute("SELECT password_hash='offline-rotated', username=?, role='admin', faculty_id IS NULL, is_active FROM public.users", (recovery.ADMIN,)).fetchone() == (not fail_after_update, 1, 1, 1, 1)
        assert checked == ["off"]
    finally: store.close()


def tool():
    spec = importlib.util.spec_from_file_location("recovery_serve_tool", ROOT/"docs/testing/phase-4b/serve_browser_fixture.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("seconds", [0, 59, 14401, -1, True, "14400"])
def test_lifetime_rejected_before_any_startup(tmp_path, seconds):
    with pytest.raises(SafetyError, match="lifetime"):
        tool().run_fixture(tmp_path/"unused", allow_recovery=True, lifetime_seconds=seconds)
    assert not (tmp_path/"unused").exists()


def test_cli_modes_mutually_exclusive_and_no_private_errors(tmp_path):
    result = subprocess.run([sys.executable, "-B", str(ROOT/"docs/testing/phase-4b/serve_browser_fixture.py"),
        "--ready-file", str(tmp_path/"ready.json"), "--allow-browser-database-recovery", "--allow-browser-database-initialization"],
        capture_output=True, text=True, timeout=10)
    assert result.returncode == 2 and "not allowed" in result.stderr
    assert not list(tmp_path.iterdir())


def test_deadline_and_explicit_stop_report_without_real_sleep(tmp_path, monkeypatch):
    module = tool(); clock = [0.0]
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(module.time, "sleep", lambda value: clock.__setitem__(0, clock[0]+value))
    stop = tmp_path/"stop"
    assert module.wait_for_stop(stop, SimpleNamespace(is_alive=lambda: True), 60) == "deadline"
    stop.write_text("")
    assert module.wait_for_stop(stop, SimpleNamespace(is_alive=lambda: True), 14400) == "requested_stop"
    stop.unlink()
    with pytest.raises(RuntimeError): module.wait_for_stop(stop, SimpleNamespace(is_alive=lambda: False), 60)


def test_atomic_handoff_complete_and_refuses_existing_target(tmp_path):
    module = tool(); ready = tmp_path/"ready.json"
    module.write_handoff(ready, {"synthetic": True})
    assert json.loads(ready.read_text()) == {"synthetic": True} and not ready.with_suffix(".pending").exists()
    # Windows Path.rename refuses overwrite; explicit guard is also required on POSIX.
    with pytest.raises(FileExistsError): module.write_handoff(ready, {"synthetic": False})
    assert json.loads(ready.read_text()) == {"synthetic": True}


def test_hung_worker_exit_targets_only_this_process(monkeypatch, capsys):
    module = tool(); exits = []
    monkeypatch.setattr(module.os, "_exit", lambda code: exits.append(code))
    module.abort_owned_process()
    assert exits == [2] and "private artifacts retained" in capsys.readouterr().out


@pytest.mark.parametrize("initialize", [False, True])
@pytest.mark.parametrize("failure", [None, "validation", "server", "handoff", "rotation", "hung"])
def test_owned_lifecycle_modes_cleanup_no_real_services(tmp_path, monkeypatch, capsys, initialize, failure):
    module = tool(); db = Database(); events = []
    ready = tmp_path/("phase4b-browser-"+uuid4().hex)/"ready.json"
    monkeypatch.setattr(safety, "designated_browser_url", url)
    monkeypatch.setattr(safety, "inspect_empty_browser_database", lambda _u: events.append("empty_gate"))
    monkeypatch.setattr(support, "secure_private_directory", lambda _p: events.append("acl"))
    listener = SimpleNamespace(close=lambda: events.append("socket_closed"), getsockname=lambda: ("127.0.0.1", 12345))
    monkeypatch.setattr(module, "reserve_listener", lambda: listener)
    monkeypatch.setattr(sqlalchemy, "create_engine", lambda *_a, **_k: SimpleNamespace(dispose=lambda: events.append("engine_disposed")))
    @contextmanager
    def claim(_url):
        events.append("claimed")
        try: yield db
        finally: events.append("released")
    monkeypatch.setattr(recovery, "claim_browser_database", claim)
    def verify(_db):
        events.append("validated")
        if failure == "validation" and not initialize: raise SafetyError("offline validation")
    monkeypatch.setattr(recovery, "verify_recovery", verify)
    def rotate(_db, _password, *, approved):
        assert approved; events.append("rotated")
        if failure == "rotation" and not initialize: raise SafetyError("offline rotation")
        return recovery.ADMIN
    monkeypatch.setattr(recovery, "rotate_browser_administrator", rotate)
    monkeypatch.setattr(support, "migrate_browser_database", lambda *_a, **_k: events.append("migrated"))
    monkeypatch.setattr(support, "seed_browser_accounts", lambda *_a: events.append("seeded") or recovery.ADMIN)
    @contextmanager
    def isolated(root, _engine, **_kw):
        events.append("isolated"); root.mkdir()
        yield dict(root=root, app=object(), instance_id=str(uuid4()))
    monkeypatch.setattr(support, "isolated_application", isolated)
    monkeypatch.setattr(support, "assert_storage_isolated", lambda _r: events.append("paths_checked"))
    import uvicorn
    class Server:
        started = failure != "server"
        should_exit = False
        def __init__(self, _config): pass
    monkeypatch.setattr(uvicorn, "Server", Server)
    monkeypatch.setattr(uvicorn, "Config", lambda *_a, **_k: object())
    class Thread:
        hung = failure == "hung"
        def __init__(self, **_kw): pass
        def start(self): events.append("worker_started")
        def is_alive(self): return self.hung
        def join(self, **_kw): events.append("worker_joined")
    monkeypatch.setattr(module.threading, "Thread", Thread)
    def abort():
        events.append("aborted_before_release")
        Thread.hung = False  # emulate dead worker without exiting the test process
        raise SafetyError("offline intercepted own-process termination")
    monkeypatch.setattr(module, "abort_owned_process", abort)
    def waiting(stop, _thread, lifetime):
        assert lifetime == 14400
        payload = json.loads(ready.read_text())
        assert payload["database"] == safety.BROWSER_DATABASE and payload["instance_id"]
        assert not ready.with_suffix(".pending").exists()
        stop.write_text(""); return "requested_stop"
    monkeypatch.setattr(module, "wait_for_stop", waiting)
    if failure == "handoff": monkeypatch.setattr(module, "write_handoff", lambda *_a: (_ for _ in ()).throw(OSError("offline private handoff failure")))
    fails = failure in ("server", "handoff", "hung") or (not initialize and failure in ("validation", "rotation"))
    if fails:
        with pytest.raises((SafetyError, OSError)):
            module.run_fixture(ready, allow_initialization=initialize, allow_recovery=not initialize, lifetime_seconds=14400)
    else:
        module.run_fixture(ready, allow_initialization=initialize, allow_recovery=not initialize, lifetime_seconds=14400)
    assert not ready.exists() and not ready.with_suffix(".pending").exists()
    assert "released" in events and "socket_closed" in events and "engine_disposed" in events
    if failure == "hung": assert events.index("aborted_before_release") < events.index("released")
    if "worker_joined" in events: assert events.index("worker_joined") < events.index("released")
    if initialize:
        assert "rotated" not in events and "empty_gate" in events
    else:
        assert "migrated" not in events and "seeded" not in events and "empty_gate" not in events
        if "rotated" in events: assert events.index("paths_checked") < events.index("rotated")
    assert "password" not in capsys.readouterr().out.lower()
