"""Safety-gate regressions do not require a configured PostgreSQL server."""
from contextlib import contextmanager

import pytest

from tests import phase4b_database_safety as safety


def test_missing_test_url_never_uses_application_database(monkeypatch):
    monkeypatch.setattr(safety, "create_engine", lambda *a, **k: pytest.fail("Unexpected connection"))
    with pytest.raises(safety.SafetyError, match="missing"):
        safety.designated_url({"DATABASE_URL": "postgresql://private.invalid/live"})


def test_designated_target_parses_without_reading_other_configuration():
    url = safety.designated_url({"PHASE4B_TEST_DATABASE_URL":
        "postgresql+psycopg2://ccs_ga_phase4b_tester@127.0.0.1:5432/ccs_ga_phase4b_test"})
    assert url.database == safety.EXPECTED_DATABASE and url.username == safety.EXPECTED_ROLE


def test_connection_setup_failure_does_not_disclose_private_exception(monkeypatch):
    def fail(*_args, **_kwargs): raise RuntimeError("synthetic private connection detail")
    monkeypatch.setattr(safety, "create_engine", fail)
    with pytest.raises(safety.SafetyError) as error: safety.inspect_empty_database(None)
    assert "synthetic private" not in str(error.value)


def test_empty_database_preflight_can_pass_using_selects_only(monkeypatch):
    from types import SimpleNamespace
    statements = []
    row = dict(database=safety.EXPECTED_DATABASE, role=safety.EXPECTED_ROLE, host="127.0.0.1",
               port=5432, schema="public", read_only="on", server_version="synthetic",
               rolsuper=False, rolcreatedb=False, rolcreaterole=False)
    class Result:
        def mappings(self): return self
        def one(self): return row
        def all(self): return []
    class Engine:
        disposed = False
        @contextmanager
        def connect(self): yield self
        def execute(self, statement):
            sql = str(statement)
            statements.append(sql)
            if "inet_server_addr()" in sql:
                # PostgreSQL's explicit inet::text includes /32. Request the
                # mask-free host, while retaining the exact IPv4 comparison.
                # This is an offline query contract, not a PostgreSQL execution.
                assert "host(inet_server_addr()) AS host" in sql
                assert "inet_server_addr()::text" not in sql
            return Result()
        def dispose(self): self.disposed = True
    engine = Engine()
    def connect(_url, **kwargs):
        assert "default_transaction_read_only=on" in kwargs["connect_args"]["options"]
        assert "statement_timeout=5000" in kwargs["connect_args"]["options"]
        assert "lock_timeout=2000" in kwargs["connect_args"]["options"]
        assert kwargs["connect_args"]["connect_timeout"] == 5
        assert kwargs["hide_parameters"]
        return engine
    monkeypatch.setattr(safety, "create_engine", connect)
    monkeypatch.setattr(safety, "inspect", lambda _connection: SimpleNamespace(get_table_names=lambda: []))
    result = safety.inspect_empty_database(None)
    assert result["tables_before"] == [] and result["migration_before"] is None
    assert result["read_only_preflight"] and engine.disposed
    assert result["host"] == "127.0.0.1"
    assert all(s.startswith("SELECT") for s in statements)
    assert "n.nspname NOT IN ('pg_catalog','information_schema')" in statements[1]
    assert "n.nspname NOT LIKE 'pg_%'" in statements[1]
    assert "c.relkind IN ('r','p','v','m','S','f')" in statements[1]


@pytest.mark.parametrize("override", [
    {"drivername": "sqlite"}, {"database": "institutional"}, {"username": "postgres"},
    {"host": "localhost"}, {"port": 5433}, {"query": {"service": "unexpected"}},
    {"host": "::1"}, {"host": "127.0.0.2"}, {"port": None},
])
def test_wrong_target_is_rejected_without_disclosing_credentials(override):
    from sqlalchemy.engine import URL
    values = dict(drivername="postgresql+psycopg2", username=safety.EXPECTED_ROLE,
                  password="synthetic-private-safety-value", host="127.0.0.1", port=5432,
                  database=safety.EXPECTED_DATABASE)
    values.update(override)
    with pytest.raises(safety.SafetyError) as error:
        safety.designated_url({"PHASE4B_TEST_DATABASE_URL": URL.create(**values).render_as_string(hide_password=False)})
    assert values["password"] not in str(error.value)


@pytest.mark.parametrize("problem", [
    "superuser", "createdb", "createrole", "nonempty", "wrong_database",
    "wrong_role", "wrong_port", "wrong_schema", "writable", "ipv6",
    "mapped_ipv6", "unexpected_address", "raw_netmask", "missing_address",
])
def test_catalog_gate_is_readonly_and_rejects_unsafe_server(monkeypatch, problem):
    statements = []
    row = dict(database=safety.EXPECTED_DATABASE, role=safety.EXPECTED_ROLE, host="127.0.0.1",
               port=5432, schema="public", read_only="on", server_version="synthetic",
               rolsuper=False, rolcreatedb=False, rolcreaterole=False)
    if problem in {"superuser", "createdb", "createrole"}:
        row["rol" + problem] = True
    if problem == "wrong_database": row["database"] = "unexpected"
    overrides = {
        "wrong_role": {"role": "postgres"},
        "wrong_port": {"port": 5433},
        "wrong_schema": {"schema": "private"},
        "writable": {"read_only": "off"},
        "ipv6": {"host": "::1"},
        "mapped_ipv6": {"host": "::ffff:127.0.0.1"},
        "unexpected_address": {"host": "127.0.0.2"},
        "raw_netmask": {"host": "127.0.0.1/32"},
        "missing_address": {"host": None},
    }
    row.update(overrides.get(problem, {}))
    class Result:
        def mappings(self): return self
        def one(self): return row
        def all(self): return [("unexpected",)] if problem == "nonempty" else []
    class Engine:
        disposed = False
        @contextmanager
        def connect(self): yield self
        def execute(self, statement):
            statements.append(str(statement))
            return Result()
        def dispose(self): self.disposed = True
    engine = Engine()
    def connect(_url, **kwargs):
        assert "default_transaction_read_only=on" in kwargs["connect_args"]["options"]
        assert kwargs["hide_parameters"]
        return engine
    monkeypatch.setattr(safety, "create_engine", connect)
    with pytest.raises(safety.SafetyError): safety.inspect_empty_database(None)
    assert engine.disposed and all(s.startswith("SELECT") for s in statements)
