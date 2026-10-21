"""D2 tests use synthetic identity/GA resources and explicitly isolated storage."""
import pytest


@pytest.fixture(autouse=True)
def isolated_checkpoints():
    # Override the legacy parent fixture; no checkpoint service is needed here.
    yield


@pytest.fixture(autouse=True)
def no_postgresql(monkeypatch):
    import psycopg2
    import database
    def deny(*args, **kwargs):
        raise AssertionError("PostgreSQL/default identity connections are forbidden in D2 tests")
    monkeypatch.setattr(psycopg2, "connect", deny)
    monkeypatch.setattr(database, "identity_engine", deny)
