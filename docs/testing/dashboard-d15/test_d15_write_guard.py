"""Offline enforcement tests. No network or PostgreSQL server is accessed."""
import io
import runpy
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

import psycopg2
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import event
from sqlalchemy.dialects import postgresql

import d15_target_guard as read_guard
import d15_write_guard as guard
from test_d15_target_guard import FakeConnection, environment, deny_real_connections


def shell(monkeypatch, connection=None):
    run = guard.GuardedRun(environ=environment())
    run.active = True
    monkeypatch.setattr(guard, 'verify_academic_profile', lambda cursor: None)
    return run, connection or FakeConnection()


@pytest.mark.parametrize('path', ['physical', 'checkout', 'begin', 'statement', 'migration', 'fixture', 'cleanup', 'commit'])
@pytest.mark.parametrize('change', [{'database': 'ccs_faculty_scheduling_dev'}, {'database': 'postgres'},
    {'database': 'template0'}, {'database': 'template1'}, {'session_user': 'postgres'}, {'current_user': 'postgres'},
    {'host': '::1'}, {'host': '192.0.2.1'}, {'port': 5433}])
def test_each_execution_boundary_checks_actual_identity_before_writes(monkeypatch, path, change):
    connection = FakeConnection(change=change)
    run, _ = shell(monkeypatch, connection)
    monkeypatch.setattr(run, '_open', lambda: connection)
    converted = []
    connection.set_session = lambda **kwargs: converted.append(kwargs)
    sa = SimpleNamespace(connection=SimpleNamespace(driver_connection=connection))
    with pytest.raises(read_guard.SafetyError, match='CONNECTED_IDENTITY_MISMATCH'):
        if path == 'physical':
            run._creator()
        elif path == 'checkout':
            run._checkout(connection, None, None)
        elif path == 'begin':
            run._begin(sa)
        elif path == 'commit':
            run._commit(sa)
        else:
            statement = {'migration': 'CREATE TABLE academic_scopes (id uuid)', 'fixture': 'INSERT INTO academic_scopes (id) VALUES (%s)',
                         'cleanup': 'DROP TABLE public.academic_scopes'}.get(path, 'UPDATE academic_scopes SET row_version=2')
            run._before(sa, None, statement, {}, None, False)
    assert not converted
    assert all(sql.startswith('SELECT') for sql in connection.queries)


@pytest.mark.parametrize('key,value', [('database', 'ccs_faculty_scheduling_dev'), ('username', 'postgres'), ('host', 'localhost'), ('port', 5433)])
def test_wrong_factory_configuration_rejected_without_driver(key, value):
    with pytest.raises(read_guard.SafetyError, match='CONFIGURATION_TARGET_MISMATCH'):
        guard.GuardedRun(environ=environment(**{key: value}))


@pytest.mark.parametrize('query', [
    'CREATE DATABASE wrong', 'ALTER DATABASE ccs_ga_d15_test OWNER TO postgres', 'DROP DATABASE ccs_ga_d15_test',
    'CREATE ROLE wrong', 'ALTER USER ccs_ga_d15_tester SUPERUSER', 'DROP ROLE wrong', 'CREATE EXTENSION dblink',
    'CREATE SERVER wrong FOREIGN DATA WRAPPER postgres_fdw', 'CREATE SCHEMA wrong', 'DROP SCHEMA public CASCADE',
    'SET ROLE postgres', 'SET SESSION AUTHORIZATION postgres', 'RESET ROLE', 'RESET ALL', 'SET search_path=other',
    'SET/**/ROLE postgres', "SELECT set_config('role','postgres',false)", 'SELECT dblink_connect(%s)',
    'COPY academic_scopes TO PROGRAM %s', 'CREATE TABLE surprise (id int)', 'CREATE TABLE other.academic_scopes (id int)',
    'DROP TABLE users', 'DROP TABLE alembic_version', 'INSERT INTO pg_catalog.pg_database VALUES (%s)',
    'UPDATE surprise SET id=1', 'DELETE FROM surprise', 'TRUNCATE surprise',
    'LOCK TABLE other.academic_scopes IN ACCESS EXCLUSIVE MODE',
    "SET LOCAL lock_timeout='1s'; SET ROLE postgres", 'CREATE FUNCTION surprise() RETURNS int LANGUAGE SQL AS %s',
    'CREATE TYPE surprise AS ENUM (%s)', 'ALTER TYPE surprise RENAME TO other', 'DROP INDEX arbitrary',
    'SET session_replication_role=replica', 'SET TRANSACTION READ WRITE',
    'DROP TABLE academic_scopes, users', 'TRUNCATE academic_scopes, users', 'SELECT 1; DELETE FROM academic_scopes',
])
def test_cluster_session_foreign_schema_and_unknown_object_operations_rejected(query):
    with pytest.raises(read_guard.SafetyError):
        guard.validate_statement(query)


@pytest.mark.parametrize('query,control', [('SET TRANSACTION READ ONLY', True), ('SAVEPOINT sa_savepoint_1', True),
    ('ROLLBACK TO SAVEPOINT sa_savepoint_1', True), ('RELEASE SAVEPOINT sa_savepoint_1', True),
    ("SET LOCAL statement_timeout='5s'", True), ('SELECT 1', False), ('INSERT INTO academic_scopes (id) VALUES (%s)', False),
    ('TRUNCATE academic_faculty_legacy_codes', False), ('DROP TABLE public.academic_courses', False)])
def test_transaction_and_recovery_controls_preserve_original_test_semantics(query, control):
    assert guard.validate_statement(query) is control


def test_real_frozen_academic_upgrade_and_guarded_downgrade_sql_is_admitted():
    root = Path(__file__).resolve().parents[3]
    context = MigrationContext.configure(dialect_name='postgresql', opts={'as_sql': True, 'output_buffer': io.StringIO()})
    statements = []
    def collect(statement, *args, **kwargs):
        sql = statement if isinstance(statement, str) else str(statement.compile(dialect=postgresql.dialect()))
        guard.validate_statement(sql)
        statements.append(sql)
    with patch.object(context.impl, '_exec', side_effect=collect), Operations.context(context):
        runpy.run_path(str(root/'backend/migrations/versions/4a_0001_identity.py'))['upgrade']()
        module = runpy.run_path(str(root/'backend/migrations/versions/4c_0001_academic_foundation.py'))
        module['upgrade']()
        module['downgrade']()
    assert len(statements) > 40 and any('CREATE TRIGGER' in s for s in statements)


def test_unguarded_or_mismatched_driver_calls_fail_before_real_driver(monkeypatch):
    run = guard.GuardedRun(environ=environment())
    called = []
    run._original_connect = lambda **kwargs: called.append(kwargs)
    with pytest.raises(read_guard.SafetyError, match='UNGATED_DRIVER_CONNECTION_REJECTED'):
        run._driver_barrier(dbname=read_guard.DATABASE)
    token = guard._FACTORY_PERMISSION.set(True)
    try:
        with pytest.raises(read_guard.SafetyError, match='DRIVER_TARGET_MISMATCH'):
            run._driver_barrier(dbname='ccs_faculty_scheduling_dev', user=read_guard.ROLE,
                host=read_guard.HOST, hostaddr=read_guard.HOST, port=read_guard.PORT)
    finally:
        guard._FACTORY_PERMISSION.reset(token)
    assert called == []


def test_engine_wires_nullpool_creator_and_all_enforcement_callbacks(monkeypatch):
    run, _ = shell(monkeypatch)
    engine = run.build_engine()
    try:
        assert event.contains(engine, 'checkout', run._checkout)
        assert event.contains(engine, 'begin', run._begin)
        assert event.contains(engine, 'before_cursor_execute', run._before)
        assert event.contains(engine, 'commit', run._commit)
        assert engine.pool.__class__.__name__ == 'NullPool' and engine.hide_parameters
        assert engine.url.password is None and engine.url.database is None
        with pytest.raises(read_guard.SafetyError, match='ENGINE_FACTORY_REJECTED'):
            run.build_engine()
    finally:
        run.close()


def test_creator_checks_before_and_after_write_mode_switch(monkeypatch):
    run, connection = shell(monkeypatch)
    monkeypatch.setattr(run, '_open', lambda: connection)
    switches = []
    def configure(**kwargs):
        switches.append(kwargs)
        connection.identity['read_only'] = 'off'
    connection.set_session = configure
    assert run._creator() is connection
    assert len(switches) == 1 and switches[0]['readonly'] is False
    assert run.counts['identity_checks'] == 2 and connection.rolled_back


def test_guard_checks_read_write_identity_without_forcing_transactions_read_only(monkeypatch):
    run, connection = shell(monkeypatch, FakeConnection(change={'read_only': 'off'}))
    sa = SimpleNamespace(connection=SimpleNamespace(driver_connection=connection))
    run._before(sa, None, 'UPDATE academic_scopes SET row_version=2', {}, None, False)
    assert run.counts['identity_checks'] == run.counts['guarded_statements'] == 1


class ProfileCursor:
    def __init__(self, change=None, occupied=None):
        self.change = change or {}
        self.occupied = occupied
        self.query = ''
        self.rows = {'schemas': [('public', read_guard.ROLE)],
            'relations': [('academic_scopes', 'r', read_guard.ROLE, None), ('academic_scopes_pkey', 'i', read_guard.ROLE, 'academic_scopes')],
            'routines': [('academic_4c_row_guard', read_guard.ROLE, 0)],
            'types': [('academic_scopes',), ('_academic_scopes',)], 'triggers': [('academic_write_gate', 'academic_scopes')]}
        self.rows.update(self.change)
    def execute(self, query, parameters=None):
        assert query.startswith('SELECT')
        self.query = query
    def fetchall(self):
        if 'SELECT n.nspname,' in self.query: return self.rows['schemas']
        if 'SELECT c.relname,' in self.query: return self.rows['relations']
        if 'SELECT p.proname,' in self.query: return self.rows['routines']
        if 'SELECT t.typname' in self.query: return self.rows['types']
        if 'SELECT t.tgname,' in self.query: return self.rows['triggers']
        raise AssertionError('Unknown profile query')
    def fetchone(self):
        return (1,) if self.occupied and self.occupied in self.query else None


def test_known_newly_created_academic_profile_and_automatic_objects_are_allowed():
    guard.verify_academic_profile(ProfileCursor())


@pytest.mark.parametrize('change', [
    {'schemas': [('public', 'postgres')]}, {'schemas': [('public', read_guard.ROLE), ('other', read_guard.ROLE)]},
    {'relations': [('surprise', 'r', read_guard.ROLE, None)]}, {'relations': [('users', 'r', 'postgres', None)]},
    {'relations': [('surprise', 'i', read_guard.ROLE, 'other')]}, {'relations': [('users', 'v', read_guard.ROLE, None)]},
    {'routines': [('surprise', read_guard.ROLE, 0)]}, {'routines': [('academic_4c_row_guard', 'postgres', 0)]},
    {'routines': [('academic_4c_row_guard', read_guard.ROLE, 1)]}, {'types': [('surprise',)]},
    {'triggers': [('surprise', 'academic_scopes')]}, {'triggers': [('academic_write_gate', 'other')]},
])
def test_unexpected_midrun_profile_fails_closed(change):
    with pytest.raises(read_guard.SafetyError):
        guard.verify_academic_profile(ProfileCursor(change))


@pytest.mark.parametrize('occupied', [q for code, q in read_guard.EMPTY_QUERIES[3:]]+['LATERAL pg_catalog.aclexplode'])
def test_midrun_nonacademic_objects_and_grants_are_rejected(occupied):
    with pytest.raises(read_guard.SafetyError):
        guard.verify_academic_profile(ProfileCursor(occupied=occupied))


def test_run_ownership_pristine_checks_factory_barrier_and_final_cleanup(monkeypatch):
    from test_d15_target_guard import FakeCursor
    created = []
    class Cursor(FakeCursor):
        def fetchone(self):
            return (True,) if 'pg_try_advisory_lock' in self.query else super().fetchone()
    class Connection(FakeConnection):
        def cursor(self): return Cursor(self)
        def set_session(self, **kwargs): self.identity['read_only'] = 'off'
    def driver(**kwargs):
        connection = Connection()
        created.append(connection)
        return connection
    monkeypatch.setattr(psycopg2, 'connect', driver)
    monkeypatch.setattr(guard, 'verify_academic_profile', lambda cursor: None)
    with guard.GuardedRun(environ=environment()) as run:
        assert run.active and run.counts['identity_checks'] == 2
        with pytest.raises(read_guard.SafetyError, match='UNGATED_DRIVER_CONNECTION_REJECTED'):
            psycopg2.connect(dbname='ccs_faculty_scheduling_dev')
        connection = run._creator()
        assert connection.identity['read_only'] == 'off'
    assert psycopg2.connect is driver and all(c.closed for c in created)
    assert not run.active
    with pytest.raises(read_guard.SafetyError, match='RUN_NOT_ACTIVE'):
        run._creator()


def test_pristine_rejection_never_enables_write_mode_and_restores_driver(monkeypatch):
    created = []
    def driver(**kwargs):
        connection = FakeConnection(occupied='pg_class')
        created.append(connection)
        return connection
    monkeypatch.setattr(psycopg2, 'connect', driver)
    with pytest.raises(read_guard.SafetyError, match='UNEXPECTED_RELATIONS'):
        with guard.GuardedRun(environ=environment()):
            pytest.fail('Unexpected target was admitted')
    assert psycopg2.connect is driver and all(c.closed for c in created)


@pytest.mark.parametrize('argument', [[], ['--unsupported', 'PRIVATE-ARGUMENT-SENTINEL']])
def test_acceptance_cli_requires_explicit_flag_and_never_echoes_unknown_arguments(monkeypatch, capsys, argument):
    import run_phase4c
    monkeypatch.setattr('sys.argv', ['run_phase4c.py', *argument])
    if argument:
        with pytest.raises(SystemExit): run_phase4c.main()
    else:
        assert run_phase4c.main() == 1
    output = capsys.readouterr()
    assert 'PRIVATE-ARGUMENT-SENTINEL' not in output.out+output.err


def test_d15_wrapper_uses_original_unmodified_assertion_callables():
    import test_phase4c_d15 as wrapper
    assert all(getattr(wrapper, name) is value for name, value in vars(wrapper.original).items() if name.startswith('test_'))


@pytest.mark.parametrize('failure', ['rollback', 'set-session', 'close'])
def test_write_enable_and_cleanup_faults_never_expose_driver_details(monkeypatch, failure):
    connection = FakeConnection(cleanup_failure='rollback' if failure == 'rollback' else None)
    run, _ = shell(monkeypatch, connection)
    monkeypatch.setattr(run, '_open', lambda: connection)
    def configure(**kwargs):
        raise RuntimeError('PRIVATE-CONFIGURE-SENTINEL')
    connection.set_session = configure
    if failure == 'close':
        def close():
            raise RuntimeError('PRIVATE-CLOSE-SENTINEL')
        connection.close = close
    with pytest.raises(read_guard.SafetyError) as error:
        run._creator()
    assert 'PRIVATE-' not in str(error.value)


@pytest.mark.parametrize('success', [True, False])
def test_controlled_runner_isolates_child_environment_and_sanitizes_evidence(monkeypatch, tmp_path, capsys, success):
    import json
    import run_phase4c
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3]/'backend'))
    monkeypatch.setattr(run_phase4c, 'ROOT', tmp_path)
    monkeypatch.setattr(run_phase4c, 'BASE', tmp_path)
    monkeypatch.setattr(run_phase4c, 'verify_preservation', lambda: None)
    monkeypatch.setattr('sys.argv', ['run_phase4c.py', '--execute'])
    monkeypatch.setenv('D15_TEST_DATABASE_URL', environment()['D15_TEST_DATABASE_URL'])
    for name in ('DATABASE_URL', 'PGHOSTADDR', 'PGPASSWORD', 'PHASE4C_TEST_DATABASE_URL', 'PHASE4C_POSTGRESQL_APPROVAL'):
        monkeypatch.setenv(name, 'PRIVATE-NON-D15-SETTING')
    counts = {'PASSED': 17 if success else 0, 'FAILED': 0 if success else 1, 'ERROR': 0, 'SKIPPED': 0, 'NOT_RUN': 0 if success else 16}
    def execute(command, **kwargs):
        child = kwargs['env']
        assert all(name not in child for name in ('DATABASE_URL', 'PGHOSTADDR', 'PGPASSWORD', 'PHASE4C_TEST_DATABASE_URL', 'PHASE4C_POSTGRESQL_APPROVAL'))
        assert child['D15_TEST_DATABASE_URL'] == environment()['D15_TEST_DATABASE_URL']
        assert '--noconftest' in command and '-x' in command and '--tb=no' in command
        directory = Path(child['D15_ACCEPTANCE_EVIDENCE'])
        (directory/'pytest-results.json').write_text(json.dumps({'counts': counts}), encoding='utf-8')
        (directory/'connection-guard-summary.json').write_text(json.dumps({'guard': 'd15-academic-write.1', 'target': 'ccs_ga_d15_test',
            'role': 'ccs_ga_d15_tester', 'owned_connections_closed': True, 'cleanup_DDL_executed': False,
            'counts': {'physical_connections': 2, 'identity_checks': 5}}), encoding='utf-8')
        return SimpleNamespace(returncode=0 if success else 1, stdout='17 passed' if success else 'password=fictional-unit-only', stderr='')
    monkeypatch.setattr(run_phase4c.subprocess, 'run', execute)
    assert run_phase4c.main() == (0 if success else 1)
    output = capsys.readouterr().out
    public = json.loads(output)
    assert public['status'] == ('ACCEPTANCE_PHASE_PASSED' if success else 'STOP_REVIEW_REQUIRED')
    assert public['counts'] == counts
    record = next(tmp_path.glob('*-phase4c-postgresql/command.json')).read_text(encoding='utf-8')
    assert 'fictional-unit-only' not in record+output and 'PRIVATE-NON-D15-SETTING' not in record+output
