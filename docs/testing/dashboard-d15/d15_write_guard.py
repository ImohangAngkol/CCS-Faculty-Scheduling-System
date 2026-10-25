"""D15-only acceptance engine. No engine/connection is made at import time.

Only owned, initially pristine targets may enter. Every physical connection,
checkout, transaction start and non-control statement rechecks actual identity.
This controls the trusted acceptance harness, not hostile Python code or a DBA.
"""
from contextvars import ContextVar
import re

import psycopg2
from sqlalchemy import create_engine, event
from sqlalchemy.pool import NullPool

import d15_target_guard as target_guard
from d15_target_guard import SafetyError

_FACTORY_PERMISSION = ContextVar('d15_owned_factory_permission', default=False)
TABLES = frozenset({'alembic_version', 'faculty_identities', 'users', 'login_sessions',
    'academic_scopes', 'academic_years', 'academic_terms', 'academic_faculty_legacy_codes',
    'academic_courses', 'academic_sections', 'academic_course_offerings'})
FUNCTIONS = frozenset({'academic_4c_write_lock', 'academic_4c_row_guard', 'academic_4c_calendar_guard'})
TRIGGERS = frozenset({'academic_write_gate', 'academic_row_guard', 'academic_calendar_guard'})
INDEXES = frozenset({'ix_login_sessions_user_id', 'ix_login_sessions_expires_at', 'ix_ac_term_year_scope',
                     'ix_ac_section_scope', 'ix_ac_offering_course_scope', 'ix_ac_offering_section_term_scope'})


def _identifier(value):
    parts = value.replace('"', '').lower().split('.')
    if len(parts) > 2 or (len(parts) == 2 and parts[0] != 'public'):
        raise SafetyError('FOREIGN_SCHEMA_OPERATION_REJECTED')
    return parts[-1]


def validate_statement(statement, *, tables=TABLES, functions=FUNCTIONS, triggers=TRIGGERS, indexes=INDEXES):
    if not isinstance(statement, str):
        raise SafetyError('UNSUPPORTED_ACCEPTANCE_STATEMENT')
    # The controlled fixture has no SQL assembled from imported text. Strip
    # comments conservatively for operation checks, including SET/**/ROLE.
    sql = re.sub(r'/\*.*?\*/', ' ', statement, flags=re.S)
    sql = re.sub(r'--[^\n]*', ' ', sql).lstrip()
    if (re.search(r'\b(?:CREATE|ALTER|DROP)\s+(?:DATABASE|ROLE|USER\b|TABLESPACE|EXTENSION|SERVER|SUBSCRIPTION|PUBLICATION|SCHEMA|FOREIGN|EVENT\s+TRIGGER)\b', sql, re.I)
            or re.search(r'(?:\A|;)\s*(?:SET|RESET)\s+(?:(?:LOCAL|SESSION)\s+)?(?:ROLE|SESSION\s+AUTHORIZATION|SEARCH_PATH|ALL)\b', sql, re.I)
            or re.search(r'\b(?:set_config|dblink\w*|pg_(?:read|write)_file|pg_ls_dir|lo_import|lo_export|pg_terminate_backend|pg_reload_conf)\s*\(', sql, re.I)
            or re.match(r'COPY\b', sql, re.I)):
        raise SafetyError('FORBIDDEN_ACCEPTANCE_OPERATION')
    if not re.match(r'(?:SELECT|SHOW|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|DO|LOCK|SET|SAVEPOINT|RELEASE|ROLLBACK)\b', sql, re.I):
        raise SafetyError('UNSUPPORTED_ACCEPTANCE_STATEMENT')
    program = bool(re.match(r'(?:DO\b|CREATE\s+FUNCTION\b)', sql, re.I))
    if not program and ';' in sql.strip().rstrip(';'):
        raise SafetyError('MULTIPLE_ACCEPTANCE_STATEMENTS_REJECTED')
    if re.match(r'CREATE\b', sql, re.I) and not re.match(r'CREATE\s+(?:TABLE|FUNCTION|TRIGGER|(?:UNIQUE\s+)?INDEX)\b', sql, re.I):
        raise SafetyError('UNSUPPORTED_ACCEPTANCE_DDL')
    if re.match(r'DROP\b', sql, re.I) and not re.match(r'DROP\s+(?:TABLE|FUNCTION)\b', sql, re.I):
        raise SafetyError('UNSUPPORTED_ACCEPTANCE_DDL')
    if re.match(r'ALTER\b', sql, re.I) and not re.match(r'ALTER\s+TABLE\b', sql, re.I):
        raise SafetyError('UNSUPPORTED_ACCEPTANCE_DDL')
    if re.match(r'(?:DROP\s+TABLE|TRUNCATE)\b', sql, re.I) and ',' in sql:
        raise SafetyError('MULTIPLE_CLEANUP_TARGETS_REJECTED')
    name = r'([A-Za-z_".][A-Za-z0-9_".]*)'
    for pattern, permitted in (
        (r'\b(?:CREATE|ALTER|DROP)\s+TABLE\s+'+name, tables),
        (r'\b(?:CREATE|DROP)\s+FUNCTION\s+'+name, functions),
        (r'\bCREATE\s+TRIGGER\s+'+name, triggers),
        (r'\bCREATE\s+(?:UNIQUE\s+)?INDEX\s+'+name, indexes),
        (r'\bINSERT\s+INTO\s+'+name, tables),
        (r'\AUPDATE\s+'+name, tables),
        (r'\bDELETE\s+FROM\s+'+name, tables),
        (r'\ATRUNCATE\s+(?:TABLE\s+)?'+name, tables)):
        if any(_identifier(value) not in permitted for value in re.findall(pattern, sql, re.I)):
            raise SafetyError('UNEXPECTED_STATEMENT_OBJECT')
    if re.search(r'\bDROP\s+TABLE\s+', sql, re.I):
        dropped = re.findall(r'\bDROP\s+TABLE\s+'+name, sql, re.I)
        if any(not _identifier(value).startswith('academic_') for value in dropped):
            raise SafetyError('IDENTITY_OR_VERSION_DROP_REJECTED')
    if re.match(r'LOCK\s+TABLE\s+', sql, re.I):
        names = re.split(r'\s+IN\s+', re.sub(r'\ALOCK\s+TABLE\s+', '', sql, flags=re.I), maxsplit=1, flags=re.I)[0]
        if any(_identifier(value.strip()) not in tables for value in names.split(',')):
            raise SafetyError('UNEXPECTED_STATEMENT_OBJECT')
    # These only restrict a transaction or recover a failed transaction; a guard
    # SELECT before SET TRANSACTION could otherwise change snapshot semantics.
    control = bool(re.match(r'(?:SAVEPOINT|RELEASE|ROLLBACK)\b|SET\s+(?:LOCAL\s+(?:lock_timeout|statement_timeout)\s*=\s*\x27?[0-9.]+[a-z]*\x27?\s*;?\s*\Z|TRANSACTION\s+READ\s+ONLY\s*;?\s*\Z)', sql, re.I))
    if re.match(r'SET\b', sql, re.I) and not control:
        raise SafetyError('UNSUPPORTED_TRANSACTION_SETTING')
    return control


def verify_academic_profile(cursor, *, tables=TABLES, functions=FUNCTIONS, triggers=TRIGGERS):
    """Only the objects created by this first, initially-empty run are admitted.

    Indexes and composite types must belong to the admitted tables. There is no
    populated-database resume/reset mode and no D9-D13 allowlist yet.
    """
    cursor.execute('SELECT n.nspname, pg_catalog.pg_get_userbyid(n.nspowner) FROM pg_catalog.pg_namespace n WHERE '+target_guard.USER_SCHEMA)
    rows = cursor.fetchall()
    if len(rows) != 1 or rows[0][0] != 'public' or rows[0][1] not in {target_guard.ROLE, 'pg_database_owner'}:
        raise SafetyError('WRITE_PROFILE_SCHEMA_REJECTED')
    cursor.execute("""SELECT c.relname, c.relkind, pg_catalog.pg_get_userbyid(c.relowner), parent.relname
        FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
        LEFT JOIN pg_catalog.pg_index i ON i.indexrelid=c.oid
        LEFT JOIN pg_catalog.pg_class parent ON parent.oid=i.indrelid WHERE """+target_guard.USER_SCHEMA)
    for name, kind, owner, parent in cursor.fetchall():
        if owner != target_guard.ROLE or not ((kind == 'r' and name in tables) or (kind == 'i' and parent in tables)):
            raise SafetyError('WRITE_PROFILE_RELATION_REJECTED')
    cursor.execute('SELECT p.proname, pg_catalog.pg_get_userbyid(p.proowner), p.pronargs FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace WHERE '+target_guard.USER_SCHEMA)
    if any(name not in functions or owner != target_guard.ROLE or nargs != 0 for name, owner, nargs in cursor.fetchall()):
        raise SafetyError('WRITE_PROFILE_ROUTINE_REJECTED')
    cursor.execute('SELECT t.typname FROM pg_catalog.pg_type t JOIN pg_catalog.pg_namespace n ON n.oid=t.typnamespace WHERE '+target_guard.USER_SCHEMA)
    if any(name not in tables and not (name.startswith('_') and name[1:] in tables) for name, in cursor.fetchall()):
        raise SafetyError('WRITE_PROFILE_TYPE_REJECTED')
    cursor.execute("""SELECT t.tgname, c.relname FROM pg_catalog.pg_trigger t
        JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
        WHERE NOT t.tgisinternal AND """+target_guard.USER_SCHEMA)
    if any(name not in triggers or table not in tables for name, table in cursor.fetchall()):
        raise SafetyError('WRITE_PROFILE_TRIGGER_REJECTED')
    # These categories never belong to the academic fixture.
    for code, query in target_guard.EMPTY_QUERIES[3:]:
        cursor.execute(query)
        if cursor.fetchone() is not None:
            raise SafetyError(code)
    # Recheck the exact same ACLs as the pristine preflight without requiring
    # relations/routines/types to remain empty while migrations execute.
    for kind, query in (
        ('SCHEMA', """SELECT 1 FROM pg_catalog.pg_namespace n,
            LATERAL pg_catalog.aclexplode(COALESCE(n.nspacl, pg_catalog.acldefault('n', n.nspowner))) a
            WHERE n.nspname='public' AND ((a.grantee=0 AND a.privilege_type='CREATE') OR
            (a.grantee<>0 AND a.grantee NOT IN (SELECT oid FROM pg_catalog.pg_roles WHERE rolname IN (%s,'pg_database_owner'))))"""),
        ('DATABASE', """SELECT 1 FROM pg_catalog.pg_database d,
            LATERAL pg_catalog.aclexplode(COALESCE(d.datacl, pg_catalog.acldefault('d', d.datdba))) a
            WHERE d.datname=current_database() AND ((a.grantee=0 AND a.privilege_type='CREATE') OR
            (a.grantee<>0 AND a.grantee<>(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=%s)))""")):
        cursor.execute(query, (target_guard.ROLE,))
        if cursor.fetchone() is not None:
            raise SafetyError('WRITE_PROFILE_'+kind+'_GRANTS_REJECTED')


class GuardedRun:
    """One process/run, one pinned target, no unguarded driver entry point."""
    def __init__(self, *, environ=None):
        self.target = target_guard.designated_target(environ)
        self.active = False
        self.control = None
        self.engine = None
        self._original_connect = None
        self._connections = []
        self.counts = {'physical_connections': 0, 'identity_checks': 0, 'guarded_statements': 0}

    def _driver_barrier(self, *args, **kwargs):
        if not _FACTORY_PERMISSION.get():
            raise SafetyError('UNGATED_DRIVER_CONNECTION_REJECTED')
        if args or any(kwargs.get(k) != v for k, v in {'dbname': target_guard.DATABASE, 'user': target_guard.ROLE,
                'host': target_guard.HOST, 'hostaddr': target_guard.HOST, 'port': target_guard.PORT}.items()):
            raise SafetyError('DRIVER_TARGET_MISMATCH')
        return self._original_connect(**kwargs)

    def _open(self):
        token = _FACTORY_PERMISSION.set(True)
        try:
            connection = target_guard.connect_dbapi(self.target)
            self._connections.append(connection)
            self.counts['physical_connections'] += 1
            return connection
        except SafetyError:
            raise
        except Exception:
            raise SafetyError('GUARDED_CONNECTION_FAILED') from None
        finally:
            _FACTORY_PERMISSION.reset(token)

    def _check(self, connection, *, pristine=False, rollback=False):
        try:
            with connection.cursor() as cursor:
                target_guard.verify_connected_identity(cursor, read_only='on' if pristine else 'either')
                self.counts['identity_checks'] += 1
                (target_guard.verify_pristine_objects if pristine else verify_academic_profile)(cursor)
        except SafetyError:
            raise
        except Exception:
            raise SafetyError('GUARDED_IDENTITY_OR_PROFILE_FAILED') from None
        finally:
            if rollback:
                try:
                    connection.rollback()
                except Exception:
                    raise SafetyError('GUARDED_CHECK_ROLLBACK_FAILED') from None

    def __enter__(self):
        if self.active or self._original_connect is not None:
            raise SafetyError('RUN_ALREADY_ACTIVE')
        self._original_connect = psycopg2.connect
        psycopg2.connect = self._driver_barrier
        try:
            self.control = self._open()
            self._check(self.control, pristine=True, rollback=True)
            with self.control.cursor() as cursor:
                cursor.execute('SELECT pg_catalog.pg_try_advisory_lock(41515, 1)')
                if cursor.fetchone() != (True,):
                    raise SafetyError('D15_RUN_OWNERSHIP_BUSY')
            self.control.rollback()  # Session lock survives rollback, no data write.
            self._check(self.control, pristine=True, rollback=True)
            self.active = True
            return self
        except SafetyError:
            self.close()
            raise
        except Exception:
            self.close()
            raise SafetyError('RUN_OWNERSHIP_CHECK_FAILED') from None

    def _creator(self):
        if not self.active:
            raise SafetyError('RUN_NOT_ACTIVE')
        connection = self._open()
        try:
            self._check(connection, rollback=True)
            connection.set_session(readonly=False, isolation_level='READ COMMITTED', autocommit=False)
            self._check(connection, rollback=True)
            return connection
        except SafetyError:
            try:
                connection.close()
            except Exception:
                raise SafetyError('GUARDED_CONNECTION_CLOSE_FAILED') from None
            raise
        except Exception:
            try:
                connection.close()
            except Exception:
                raise SafetyError('GUARDED_CONNECTION_CLOSE_FAILED') from None
            raise SafetyError('WRITE_MODE_ENABLE_FAILED') from None

    def _checkout(self, dbapi, record, proxy):
        if not self.active:
            raise SafetyError('RUN_NOT_ACTIVE')
        self._check(dbapi, rollback=True)

    def _begin(self, connection):
        if not self.active:
            raise SafetyError('RUN_NOT_ACTIVE')
        self._check(connection.connection.driver_connection, rollback=True)

    def _before(self, connection, cursor, statement, parameters, context, executemany):
        if not self.active:
            raise SafetyError('RUN_NOT_ACTIVE')
        control = validate_statement(statement)
        if not control:
            self._check(connection.connection.driver_connection)
        self.counts['guarded_statements'] += 1

    def _commit(self, connection):
        if not self.active:
            raise SafetyError('RUN_NOT_ACTIVE')
        self._check(connection.connection.driver_connection)

    def build_engine(self):
        if not self.active or self.engine is not None:
            raise SafetyError('ENGINE_FACTORY_REJECTED')
        self.engine = create_engine('postgresql+psycopg2://', creator=self._creator, poolclass=NullPool,
                                    hide_parameters=True, echo=False)
        event.listen(self.engine, 'checkout', self._checkout)
        event.listen(self.engine, 'begin', self._begin)
        event.listen(self.engine, 'before_cursor_execute', self._before)
        event.listen(self.engine, 'commit', self._commit)
        return self.engine

    def close(self):
        self.active = False
        failure = False
        try:
            if self.engine is not None:
                try:
                    self.engine.dispose()
                except Exception:
                    failure = True
        finally:
            try:
                for connection in reversed(self._connections):
                    if getattr(connection, 'closed', False):
                        continue
                    try:
                        connection.rollback()
                    except Exception:
                        failure = True
                    finally:
                        try:
                            connection.close()  # Releases only owned session locks.
                        except Exception:
                            failure = True
            finally:
                if self._original_connect is not None:
                    psycopg2.connect = self._original_connect
                    self._original_connect = None
        if failure:
            raise SafetyError('OWNED_CONNECTION_CLEANUP_FAILED')

    def __exit__(self, *args):
        self.close()
