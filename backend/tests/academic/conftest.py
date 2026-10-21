"""Academic tests must not inherit the legacy fixture that imports real GA inputs."""
import pytest


@pytest.fixture(autouse=True)
def isolated_checkpoints():
    # Override the parent fixture by name. No academic test executes a GA or uses
    # checkpoint/history services, whose legacy import chain reads institutional CSVs.
    yield


@pytest.fixture(autouse=True)
def deny_unapproved_database_and_data_reads(request, monkeypatch):
    import builtins
    import io
    from pathlib import Path
    import socket

    data = (Path(__file__).resolve().parents[2] / "data").resolve()
    def protect(original):
        def guarded(file, *args, **kwargs):
            if isinstance(file, (str, bytes, Path)):
                try:
                    path = Path(file).resolve()
                    if path == data or data in path.parents:
                        raise AssertionError("Institutional data access is forbidden in academic tests.")
                except (TypeError, ValueError):
                    pass
            return original(file, *args, **kwargs)
        return guarded
    monkeypatch.setattr(builtins, "open", protect(builtins.open))
    monkeypatch.setattr(io, "open", protect(io.open))
    if request.module.__name__.endswith("test_academic_postgresql"):
        # That module has its own explicit opt-in + exact target gate.
        return
    def deny(*args, **kwargs):
        raise AssertionError("Network access is forbidden in offline academic tests.")
    monkeypatch.setattr(socket.socket, "connect", deny)
    import psycopg2
    monkeypatch.setattr(psycopg2, "connect", deny)
