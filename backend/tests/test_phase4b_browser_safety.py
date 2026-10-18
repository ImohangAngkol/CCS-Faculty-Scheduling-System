"""Offline browser target tests: no PostgreSQL engine may be constructed."""
from contextlib import contextmanager

import pytest
from sqlalchemy.engine import URL

from tests import phase4b_browser_safety as safety
from tests.phase4b_database_safety import SafetyError, designated_url


def browser_url(**overrides):
    values = dict(drivername="postgresql+psycopg2", username=safety.BROWSER_ROLE,
                  host="127.0.0.1", port=5432, database=safety.BROWSER_DATABASE)
    values.update(overrides)
    return URL.create(**values)


@pytest.fixture(autouse=True)
def no_real_engine(monkeypatch):
    monkeypatch.setattr(safety, "create_engine", lambda *_a, **_k: pytest.fail("Real browser engine forbidden offline"))


def test_no_application_or_acceptance_environment_fallback():
    with pytest.raises(SafetyError, match="missing"):
        safety.designated_browser_url({"DATABASE_URL": str(browser_url()),
                                      "PHASE4B_TEST_DATABASE_URL": str(browser_url())})


@pytest.mark.parametrize("override", [
    {"drivername": "sqlite"}, {"database": "ccs_ga_phase4b_test"},
    {"database": "ccs_faculty_scheduling_dev"}, {"username": "ccs_ga_phase4b_tester"},
    {"username": "postgres"}, {"host": "localhost"}, {"host": "::1"},
    {"host": "127.0.0.2"}, {"port": 5433}, {"port": None},
    {"query": {"service": "another_instance"}},
])
def test_wrong_browser_target_rejected_before_connection(override):
    with pytest.raises(SafetyError):
        safety.inspect_empty_browser_database(browser_url(**override))


def test_original_acceptance_target_not_broadened():
    with pytest.raises(SafetyError):
        designated_url({"PHASE4B_TEST_DATABASE_URL": str(browser_url())})


@pytest.fixture
def fake_catalog(monkeypatch):
    row = dict(database=safety.BROWSER_DATABASE, role=safety.BROWSER_ROLE,
               owner=safety.BROWSER_ROLE, host="127.0.0.1", port=5432,
               schema="public", read_only="on", server_version="offline-fake",
               rolsuper=False, rolcreatedb=False, rolcreaterole=False,
               rolreplication=False, rolbypassrls=False, can_create=True)
    state = dict(row=row, schemas=["public"], occupied=None, sql=[], disposed=False)

    class Result:
        def mappings(self): return self
        def one(self): return state["row"]
        def scalars(self): return self
        def all(self): return state["schemas"]
        def first(self): return state["occupied"]

    class Engine:
        @contextmanager
        def connect(self): yield self
        def execute(self, statement):
            state["sql"].append(str(statement))
            return Result()
        def dispose(self): state["disposed"] = True

    def connect(_url, **kwargs):
        assert kwargs["hide_parameters"] is True
        assert kwargs["connect_args"] == {
            "connect_timeout": 5,
            "options": "-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=2000"}
        return Engine()

    monkeypatch.setattr(safety, "create_engine", connect)
    return state


def test_valid_browser_catalog_select_only_and_mask_free(fake_catalog):
    result = safety.inspect_empty_browser_database(browser_url())
    assert result["empty"] and result["read_only_preflight"]
    assert result["database"] == safety.BROWSER_DATABASE and result["migration_before"] is None
    assert fake_catalog["disposed"]
    assert all(sql.startswith("SELECT") for sql in fake_catalog["sql"])
    assert "host(inet_server_addr()) AS host" in fake_catalog["sql"][0]
    assert "inet_server_addr()::text" not in fake_catalog["sql"][0]
    assert "nspname !~ '^pg_'" in fake_catalog["sql"][1]
    assert "NOT LIKE 'pg_%'" not in " ".join(fake_catalog["sql"])
    for source in ("pg_class", "pg_proc", "pg_type", "pg_depend", "pg_event_trigger", "pg_publication", "pg_extension"):
        assert source in fake_catalog["sql"][2]


@pytest.mark.parametrize("override", [
    {"database": "ccs_ga_phase4b_test"}, {"role": "ccs_ga_phase4b_tester"},
    {"owner": "postgres"}, {"host": "::1"}, {"host": "::ffff:127.0.0.1"},
    {"host": "127.0.0.2"}, {"host": "127.0.0.1/32"}, {"host": None},
    {"port": 5433}, {"schema": "private"}, {"read_only": "off"},
    {"rolsuper": True}, {"rolcreatedb": True}, {"rolcreaterole": True},
    {"rolreplication": True}, {"rolbypassrls": True}, {"rolsuper": None},
    {"can_create": False}, {"can_create": None},
])
def test_server_mismatch_prevents_further_inspection(fake_catalog, override):
    fake_catalog["row"].update(override)
    with pytest.raises(SafetyError, match="gate failed"):
        safety.inspect_empty_browser_database(browser_url())
    assert len(fake_catalog["sql"]) == 1 and fake_catalog["disposed"]


@pytest.mark.parametrize("schemas", [[], ["other"], ["public", "other"], ["public", "pgshadow"]])
def test_unexpected_or_missing_schema_rejected(fake_catalog, schemas):
    fake_catalog["schemas"] = schemas
    with pytest.raises(SafetyError, match="schemas"):
        safety.inspect_empty_browser_database(browser_url())
    assert len(fake_catalog["sql"]) == 2 and fake_catalog["disposed"]


def test_any_existing_objects_rejected_without_reset(fake_catalog):
    fake_catalog["occupied"] = (1,)
    with pytest.raises(SafetyError, match="not empty"):
        safety.inspect_empty_browser_database(browser_url())
    assert fake_catalog["disposed"] and all(sql.startswith("SELECT") for sql in fake_catalog["sql"])


def test_connection_errors_do_not_disclose_private_values(monkeypatch):
    def fail(*_a, **_k): raise RuntimeError("synthetic private connection diagnostics")
    monkeypatch.setattr(safety, "create_engine", fail)
    with pytest.raises(SafetyError) as error:
        safety.inspect_empty_browser_database(browser_url())
    assert "synthetic private" not in str(error.value)
