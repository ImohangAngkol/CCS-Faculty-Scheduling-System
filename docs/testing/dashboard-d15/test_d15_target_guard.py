"""Offline negative/admission tests. No real network, credential or DB access."""
import socket

import psycopg2
import pytest
from sqlalchemy.engine import URL

import d15_target_guard as guard


def environment(**changes):
    fields = dict(drivername='postgresql+psycopg2', username=guard.ROLE, password='fictional-unit-only',
                  host=guard.HOST, port=guard.PORT, database=guard.DATABASE)
    fields.update(changes)
    return {'D15_TEST_DATABASE_URL': URL.create(**fields).render_as_string(hide_password=False)}


@pytest.fixture(autouse=True)
def deny_real_connections(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('Real connection forbidden in offline guard tests')
    monkeypatch.setattr(psycopg2, 'connect', denied)
    monkeypatch.setattr(socket.socket, 'connect', denied)


@pytest.mark.parametrize('environ', [{}, {'DATABASE_URL': 'ignored'}, {'PHASE4C_TEST_DATABASE_URL': 'ignored'},
    {'PHASE4B_TEST_DATABASE_URL': 'ignored'}, {'D15_TEST_DATABASE_URL': 'malformed'}])
def test_missing_configuration_never_falls_back(environ):
    with pytest.raises(guard.SafetyError, match='CONFIGURATION_TARGET_MISMATCH'):
        guard.designated_target(environ)


@pytest.mark.parametrize('change', [
    {'database': 'ccs_faculty_scheduling_dev'}, {'database': 'postgres'}, {'database': 'template0'}, {'database': 'template1'},
    {'database': 'ccs_ga_phase4b_test'}, {'database': 'ccs_ga_phase4b_browser_test'}, {'database': 'ccs_ga_phase4c_test'},
    {'database': 'ccs_ga_d15_test_copy'}, {'username': 'postgres'}, {'host': 'localhost'}, {'host': '::1'},
    {'host': '192.0.2.1'}, {'port': 5433}, {'port': None}, {'drivername': 'sqlite'}, {'drivername': 'postgresql+asyncpg'},
    {'query': {'options': '-c role=postgres'}}, {'query': {'hostaddr': '192.0.2.1'}}, {'password': ''}, {'password': None},
])
def test_wrong_configuration_rejected_without_connection(change):
    with pytest.raises(guard.SafetyError):
        guard.read_only_preflight(allow_connect=True, environ=environment(**change))


def test_parse_never_prints_password():
    target = guard.designated_target(environment())
    assert 'fictional-unit-only' not in repr(target)
    assert 'fictional-unit-only' not in str(target)


def test_explicit_flag_before_connector(monkeypatch):
    monkeypatch.setattr(guard, 'connect_dbapi', lambda *args: pytest.fail('Connection attempted'))
    with pytest.raises(guard.SafetyError, match='EXPLICIT_READ_ONLY_FLAG_REQUIRED'):
        guard.read_only_preflight(environ=environment())


def identity(**changes):
    data = dict(database=guard.DATABASE, session_user=guard.ROLE, current_user=guard.ROLE, host=guard.HOST,
                port=guard.PORT, schema='public', read_only='on', owner=guard.ROLE, rolcanlogin=True, rolsuper=False,
                rolcreatedb=False, rolcreaterole=False, rolreplication=False, rolbypassrls=False, rolconnlimit=20,
                can_connect=True, can_create=True, schema_usage=True, schema_create=True,
                server_version='18.6', server_version_num='180006')
    return data | changes


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.query = ''
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.connection.cursor_closed = True
    def execute(self, query, parameters=None):
        assert query.lstrip().startswith('SELECT'), 'Non-SELECT preflight SQL'
        self.query = query
        self.connection.queries.append(query)
        if self.connection.fails_in_query:
            raise RuntimeError('PRIVATE-DRIVER-SENTINEL')
    def fetchone(self):
        if self.query == guard.IDENTITY_SQL:
            return tuple(self.connection.identity[k] for k in guard.FIELDS)
        return (1,) if self.connection.occupied and self.connection.occupied in self.query else None
    def fetchall(self):
        return self.connection.schemas


class FakeConnection:
    def __init__(self, *, change=None, occupied=None, schemas=None, fails_in_query=False, cleanup_failure=None):
        self.identity = identity(**(change or {}))
        self.occupied = occupied
        self.schemas = [('public', 'pg_database_owner')] if schemas is None else schemas
        self.fails_in_query = fails_in_query
        self.cleanup_failure = cleanup_failure
        self.queries = []
        self.rolled_back = self.closed = self.cursor_closed = False
    def cursor(self):
        return FakeCursor(self)
    def rollback(self):
        self.rolled_back = True
        if self.cleanup_failure == 'rollback':
            raise RuntimeError('PRIVATE-ROLLBACK-SENTINEL')
    def close(self):
        self.closed = True
        if self.cleanup_failure == 'close':
            raise RuntimeError('PRIVATE-CLOSE-SENTINEL')


def run(monkeypatch, connection):
    monkeypatch.setattr(guard, 'connect_dbapi', lambda target: connection)
    return guard.read_only_preflight(allow_connect=True, environ=environment())


def test_exact_fake_catalog_passes_selects_only_and_closes(monkeypatch):
    connection = FakeConnection()
    result = run(monkeypatch, connection)
    assert result['database'] == guard.DATABASE and result['session_user'] == guard.ROLE
    assert result['empty'] and result['read_only'] and not result['writes_performed']
    assert connection.rolled_back and connection.closed and connection.cursor_closed
    assert all(q.startswith('SELECT') for q in connection.queries)


@pytest.mark.parametrize('change', [
    {'database': 'ccs_faculty_scheduling_dev'}, {'database': 'postgres'}, {'database': 'template0'}, {'database': 'template1'},
    {'database': 'ccs_ga_phase4b_test'}, {'session_user': 'postgres'}, {'current_user': 'postgres'},
    {'session_user': 'postgres', 'current_user': guard.ROLE}, {'session_user': guard.ROLE, 'current_user': 'other'},
    {'host': '::1'}, {'host': '192.0.2.1'}, {'port': 5433}, {'owner': 'postgres'}, {'schema': 'other'}, {'read_only': 'off'},
])
def test_actual_identity_overrides_apparently_valid_configuration(monkeypatch, change):
    connection = FakeConnection(change=change)
    with pytest.raises(guard.SafetyError, match='CONNECTED_IDENTITY_MISMATCH'):
        run(monkeypatch, connection)
    assert len(connection.queries) == 1 and connection.closed and connection.rolled_back


@pytest.mark.parametrize('change', [
    {'rolcanlogin': False}, {'rolsuper': True}, {'rolcreatedb': True}, {'rolcreaterole': True},
    {'rolreplication': True}, {'rolbypassrls': True}, {'rolconnlimit': -1}, {'rolconnlimit': 50},
    {'can_connect': False}, {'can_create': False}, {'schema_usage': False}, {'schema_create': False},
    {'server_version_num': '170006'}, {'server_version_num': 'not-a-version'},
])
def test_privileges_version_and_required_permissions_fail_closed(monkeypatch, change):
    connection = FakeConnection(change=change)
    with pytest.raises(guard.SafetyError):
        run(monkeypatch, connection)
    assert connection.closed and connection.rolled_back


@pytest.mark.parametrize('schemas', [[], [('public', 'postgres')], [('other', guard.ROLE)],
    [('public', guard.ROLE), ('other', guard.ROLE)]])
def test_unexpected_schemas_fail_closed(monkeypatch, schemas):
    with pytest.raises(guard.SafetyError, match='UNEXPECTED_SCHEMA_OR_OWNER'):
        run(monkeypatch, FakeConnection(schemas=schemas))


@pytest.mark.parametrize('occupied', ['pg_auth_members', *[query for code, query in guard.EMPTY_QUERIES],
    'WHERE n.nspname=\'public\' AND', 'WHERE d.datname=current_database() AND'])
def test_every_unexpected_inventory_or_grant_branch_rejects(monkeypatch, occupied):
    connection = FakeConnection(occupied=occupied)
    with pytest.raises(guard.SafetyError):
        run(monkeypatch, connection)
    assert connection.closed and connection.rolled_back


@pytest.mark.parametrize('failure', ['connect', 'query', 'rollback', 'close'])
def test_driver_and_cleanup_errors_are_sanitized(monkeypatch, failure):
    connection = FakeConnection(fails_in_query=failure == 'query', cleanup_failure=failure)
    if failure == 'connect':
        def failed(target):
            raise RuntimeError('PRIVATE-CONNECTION-SENTINEL')
        monkeypatch.setattr(guard, 'connect_dbapi', failed)
        execute = lambda: guard.read_only_preflight(allow_connect=True, environ=environment())
    else:
        execute = lambda: run(monkeypatch, connection)
    with pytest.raises(guard.SafetyError) as error:
        execute()
    assert 'PRIVATE-' not in str(error.value) and 'fictional-unit-only' not in str(error.value)
    if failure != 'connect':
        assert connection.closed and connection.rolled_back


def test_driver_parameters_pin_hostaddr_database_role_and_read_only(monkeypatch):
    captured = {}
    def fake(**kwargs):
        captured.update(kwargs)
        return FakeConnection()
    monkeypatch.setattr(psycopg2, 'connect', fake)
    guard.connect_dbapi(guard.designated_target(environment()))
    assert captured['dbname'] == guard.DATABASE and captured['user'] == guard.ROLE
    assert captured['host'] == captured['hostaddr'] == guard.HOST and captured['port'] == guard.PORT
    assert captured['connect_timeout'] == 5
    assert 'default_transaction_read_only=on' in captured['options']
    assert 'search_path=public,pg_catalog' in captured['options']
    assert 'statement_timeout=5000' in captured['options'] and 'lock_timeout=2000' in captured['options']


@pytest.mark.parametrize('mode', ['pass', 'missing-flag', 'preservation', 'driver'])
def test_cli_records_only_sanitized_result_and_never_logs_credentials(monkeypatch, tmp_path, capsys, mode):
    import json
    import preflight
    monkeypatch.setattr(preflight, 'BASE', tmp_path)
    monkeypatch.setattr(preflight, 'ROOT', tmp_path)
    def preservation():
        if mode == 'preservation':
            raise guard.SafetyError('REPOSITORY_PRESERVATION_CHANGED')
    monkeypatch.setattr(preflight, 'verify_preservation', preservation)
    def connect(target):
        if mode == 'driver':
            raise RuntimeError('PRIVATE-DRIVER-SENTINEL')
        return FakeConnection()
    monkeypatch.setattr(guard, 'connect_dbapi', connect)
    monkeypatch.setenv('D15_TEST_DATABASE_URL', environment()['D15_TEST_DATABASE_URL'])
    monkeypatch.setattr('sys.argv', ['preflight.py', *([] if mode == 'missing-flag' else ['--read-only'])])
    assert preflight.main() == (0 if mode == 'pass' else 1)
    output = capsys.readouterr().out
    document = next(tmp_path.glob('*/result.json')).read_text(encoding='utf-8')
    assert 'fictional-unit-only' not in output+document and 'PRIVATE-' not in output+document
    assert 'postgresql://' not in output+document and 'postgresql+psycopg2://' not in output+document
    result = json.loads(output)
    assert result['status'] == ('READ_ONLY_PREFLIGHT_PASSED' if mode == 'pass' else 'REJECTED')
    assert result['writes_performed'] is False


def test_unsupported_command_arguments_do_not_echo_values(monkeypatch, capsys):
    import preflight
    monkeypatch.setattr('sys.argv', ['preflight.py', '--unsupported', 'PRIVATE-ARGUMENT-SENTINEL'])
    with pytest.raises(SystemExit) as error:
        preflight.main()
    assert error.value.code == 2
    output = capsys.readouterr()
    assert 'PRIVATE-ARGUMENT-SENTINEL' not in output.out+output.err
