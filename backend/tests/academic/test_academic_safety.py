"""Negative target gate tests never create an engine or read real credentials."""
import pytest

from tests.academic import postgresql_safety as safety

URL = "postgresql+psycopg2://ccs_ga_phase4c_tester:dummy@127.0.0.1:5432/ccs_ga_phase4c_test"


@pytest.mark.parametrize("environment", [
    {}, {"DATABASE_URL": URL}, {"PHASE4B_TEST_DATABASE_URL": URL},
    {"PHASE4C_TEST_DATABASE_URL": URL.replace("phase4c_test", "phase4b_test")},
    {"PHASE4C_TEST_DATABASE_URL": URL.replace("phase4c_test", "phase4b_browser_test")},
    {"PHASE4C_TEST_DATABASE_URL": URL.replace("127.0.0.1", "localhost")},
    {"PHASE4C_TEST_DATABASE_URL": URL.replace("5432", "5433")},
    {"PHASE4C_TEST_DATABASE_URL": URL.replace("ccs_ga_phase4c_tester", "postgres")},
    {"PHASE4C_TEST_DATABASE_URL": URL + "?options=unsafe"},
])
def test_wrong_target_rejected_without_fallback(environment):
    with pytest.raises(safety.SafetyError) as error: safety.designated_url(environment)
    assert URL not in str(error.value) and "dummy" not in str(error.value)


def test_exact_target_parse_is_not_a_connection():
    url = safety.designated_url({"PHASE4C_TEST_DATABASE_URL": URL})
    assert url.database == safety.EXPECTED_DATABASE


@pytest.mark.parametrize("allow,approval", [(False, None), (True, None), (False, safety.APPROVAL), (True, "yes")])
def test_preflight_requires_both_explicit_switches(monkeypatch, allow, approval):
    def forbidden(*args, **kwargs): raise AssertionError("An engine must not be created")
    monkeypatch.setattr(safety, "create_engine", forbidden)
    with pytest.raises(safety.SafetyError, match="no connection attempted"):
        safety.inspect_empty_test_database(environ={"PHASE4C_TEST_DATABASE_URL": URL, "PHASE4C_POSTGRESQL_APPROVAL": approval}, allow_connect=allow)


class CatalogResult:
    def __init__(self, value): self.value = value
    def mappings(self): return self
    def one(self): return self.value
    def all(self): return self.value
    def first(self): return self.value[0] if self.value else None


class CatalogEngine:
    def __init__(self, *, row_change=None, occupied=None, schema_owner=None):
        self.row_change = row_change or {}
        self.occupied = occupied
        self.schema_owner = schema_owner or safety.EXPECTED_ROLE
        self.disposed = False
        self.queries = []
    def connect(self): return self
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def dispose(self): self.disposed = True
    def execute(self, statement, parameters=None):
        query = str(statement)
        self.queries.append(query)
        if "SELECT current_database()" in query:
            return CatalogResult(dict(database=safety.EXPECTED_DATABASE, role=safety.EXPECTED_ROLE,
                host="127.0.0.1", port=5432, schema="public", read_only="on", owner=safety.EXPECTED_ROLE,
                rolsuper=False, rolcreatedb=False, rolcreaterole=False, rolreplication=False,
                rolbypassrls=False, **{} ) | self.row_change)
        if "SELECT nspname," in query: return CatalogResult([("public", self.schema_owner)])
        return CatalogResult([(1,)] if self.occupied and self.occupied in query else [])


def enabled():
    return {"PHASE4C_TEST_DATABASE_URL": URL, "PHASE4C_POSTGRESQL_APPROVAL": safety.APPROVAL}


def test_fake_empty_catalog_only_selects_and_disposes(monkeypatch):
    engine = CatalogEngine(schema_owner="pg_database_owner")
    def construct(url, **options):
        assert options["hide_parameters"]
        assert "default_transaction_read_only=on" in options["connect_args"]["options"]
        return engine
    monkeypatch.setattr(safety, "create_engine", construct)
    assert safety.inspect_empty_test_database(environ=enabled(), allow_connect=True)["empty"]
    assert engine.disposed and all(q.lstrip().startswith("SELECT") for q in engine.queries)


@pytest.mark.parametrize("change", [{"owner": "other"}, {"read_only": "off"},
    {"rolsuper": True}, {"rolcreatedb": True}, {"rolcreaterole": True},
    {"rolreplication": True}, {"rolbypassrls": True}, {"host": "::1"}])
def test_fake_catalog_identity_or_privilege_rejection(monkeypatch, change):
    engine = CatalogEngine(row_change=change)
    monkeypatch.setattr(safety, "create_engine", lambda *a, **k: engine)
    with pytest.raises(safety.SafetyError): safety.inspect_empty_test_database(environ=enabled(), allow_connect=True)
    assert engine.disposed


@pytest.mark.parametrize("occupied", ["pg_auth_members", "pg_class", "pg_proc", "pg_type", "pg_extension", "pg_default_acl", "LATERAL aclexplode"])
def test_fake_nonempty_or_granted_target_rejected(monkeypatch, occupied):
    engine = CatalogEngine(occupied=occupied)
    monkeypatch.setattr(safety, "create_engine", lambda *a, **k: engine)
    with pytest.raises(safety.SafetyError): safety.inspect_empty_test_database(environ=enabled(), allow_connect=True)
    assert engine.disposed


def test_fake_connection_failure_does_not_disclose_details(monkeypatch):
    def failed(*args, **kwargs): raise RuntimeError("PRIVATE-SENTINEL")
    monkeypatch.setattr(safety, "create_engine", failed)
    with pytest.raises(safety.SafetyError) as error:
        safety.inspect_empty_test_database(environ=enabled(), allow_connect=True)
    assert "PRIVATE-SENTINEL" not in str(error.value)
