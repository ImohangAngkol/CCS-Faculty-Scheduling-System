"""Exact D15 target verification. Importing/parsing never opens a connection.

This entry point permits SELECT-only pristine preflight, not migrations or tests.
A future writing runner must reuse connected identity verification on every
owned connection and validate its explicit expected schema profile separately.
"""
from dataclasses import dataclass, field
import os

from sqlalchemy.engine import make_url

DATABASE = 'ccs_ga_d15_test'
ROLE = 'ccs_ga_d15_tester'
HOST = '127.0.0.1'
PORT = 5432


class SafetyError(RuntimeError):
    """Public error consists of a fixed code, never driver/configuration details."""
    def __init__(self, code):
        self.code = code
        super().__init__('D15 safety preflight rejected: '+code+'; connection details withheld.')


@dataclass(frozen=True)
class Target:
    password: str = field(repr=False)


def designated_target(environ=None):
    environment = os.environ if environ is None else environ
    raw = environment.get('D15_TEST_DATABASE_URL')
    try:
        url = make_url(raw) if raw else None
        valid = (url is not None and url.drivername in {'postgresql', 'postgresql+psycopg2'}
                 and url.database == DATABASE and url.username == ROLE
                 and url.host == HOST and url.port == PORT and not url.query
                 and isinstance(url.password, str) and bool(url.password))
        if valid:
            return Target(url.password)
    except Exception:
        pass
    raise SafetyError('CONFIGURATION_TARGET_MISMATCH') from None


def connect_dbapi(target):
    # All address/database/role fields are constants; environment/libpq defaults
    # cannot replace them. Explicit password prevents implicit password-file use.
    import psycopg2
    return psycopg2.connect(dbname=DATABASE, user=ROLE, password=target.password,
        host=HOST, hostaddr=HOST, port=PORT, connect_timeout=5, sslmode='prefer',
        application_name='ccs_d15_read_only_preflight',
        options='-c default_transaction_read_only=on -c search_path=public,pg_catalog '
                '-c statement_timeout=5000 -c lock_timeout=2000 '
                '-c idle_in_transaction_session_timeout=10000')


FIELDS = ('database', 'session_user', 'current_user', 'host', 'port', 'schema', 'read_only',
          'owner', 'rolcanlogin', 'rolsuper', 'rolcreatedb', 'rolcreaterole', 'rolreplication',
          'rolbypassrls', 'rolconnlimit', 'can_connect', 'can_create', 'schema_usage', 'schema_create',
          'server_version', 'server_version_num')
IDENTITY_SQL = """SELECT pg_catalog.current_database(), session_user, current_user,
    pg_catalog.host(pg_catalog.inet_server_addr()), pg_catalog.inet_server_port(),
    pg_catalog.current_schema(), pg_catalog.current_setting('transaction_read_only'),
    pg_catalog.pg_get_userbyid(d.datdba), r.rolcanlogin, r.rolsuper, r.rolcreatedb,
    r.rolcreaterole, r.rolreplication, r.rolbypassrls, r.rolconnlimit,
    pg_catalog.has_database_privilege(current_user, d.oid, 'CONNECT'),
    pg_catalog.has_database_privilege(current_user, d.oid, 'CREATE'),
    pg_catalog.has_schema_privilege(current_user, 'public', 'USAGE'),
    pg_catalog.has_schema_privilege(current_user, 'public', 'CREATE'),
    pg_catalog.current_setting('server_version'), pg_catalog.current_setting('server_version_num')
    FROM pg_catalog.pg_database d JOIN pg_catalog.pg_roles r ON r.rolname = session_user
    WHERE d.datname = pg_catalog.current_database()"""


def verify_connected_identity(cursor, *, read_only='on'):
    """Check actual session identity before considering permissions or fixtures."""
    cursor.execute(IDENTITY_SQL)
    row = cursor.fetchone()
    try:
        data = dict(zip(FIELDS, row, strict=True))
    except Exception:
        raise SafetyError('CONNECTED_IDENTITY_UNAVAILABLE') from None
    if (data['database'] != DATABASE or data['session_user'] != ROLE or data['current_user'] != ROLE
            or data['host'] != HOST or data['port'] != PORT or data['owner'] != ROLE
            or data['schema'] != 'public' or data['read_only'] not in ({'on', 'off'} if read_only == 'either' else {read_only})):
        raise SafetyError('CONNECTED_IDENTITY_MISMATCH')
    if (data['rolcanlogin'] is not True or data['rolconnlimit'] != 20
            or any(data[k] is not False for k in ('rolsuper', 'rolcreatedb', 'rolcreaterole', 'rolreplication', 'rolbypassrls'))
            or any(data[k] is not True for k in ('can_connect', 'can_create', 'schema_usage', 'schema_create'))):
        raise SafetyError('ROLE_OR_REQUIRED_PRIVILEGES_REJECTED')
    try:
        if int(data['server_version_num']) // 10000 != 18:
            raise ValueError
    except (ValueError, TypeError):
        raise SafetyError('SERVER_VERSION_MISMATCH') from None
    cursor.execute("""SELECT 1 FROM pg_catalog.pg_auth_members
        WHERE member = (SELECT oid FROM pg_catalog.pg_roles WHERE rolname = current_user)
           OR roleid = (SELECT oid FROM pg_catalog.pg_roles WHERE rolname = current_user)""")
    if cursor.fetchone() is not None:
        raise SafetyError('ROLE_MEMBERSHIPS_REJECTED')
    return data


USER_SCHEMA = "n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_%'"
EMPTY_QUERIES = (
    ('UNEXPECTED_RELATIONS', 'SELECT 1 FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE '+USER_SCHEMA),
    ('UNEXPECTED_ROUTINES', 'SELECT 1 FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace WHERE '+USER_SCHEMA),
    ('UNEXPECTED_TYPES', 'SELECT 1 FROM pg_catalog.pg_type t JOIN pg_catalog.pg_namespace n ON n.oid=t.typnamespace WHERE '+USER_SCHEMA),
    ('UNEXPECTED_EXTENSIONS', "SELECT 1 FROM pg_catalog.pg_extension WHERE extname <> 'plpgsql'"),
    ('UNEXPECTED_DEFAULT_PRIVILEGES', 'SELECT 1 FROM pg_catalog.pg_default_acl'),
    ('UNEXPECTED_LARGE_OBJECTS', 'SELECT 1 FROM pg_catalog.pg_largeobject_metadata'),
    ('UNEXPECTED_FOREIGN_SERVERS', 'SELECT 1 FROM pg_catalog.pg_foreign_server'),
    ('UNEXPECTED_EVENT_TRIGGERS', 'SELECT 1 FROM pg_catalog.pg_event_trigger'),
    ('UNEXPECTED_USER_MAPPINGS', 'SELECT 1 FROM pg_catalog.pg_user_mappings'),
    ('UNEXPECTED_DATABASE_SETTINGS', 'SELECT 1 FROM pg_catalog.pg_db_role_setting WHERE setdatabase = (SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database())'),
)


def verify_pristine_objects(cursor):
    cursor.execute('SELECT n.nspname, pg_catalog.pg_get_userbyid(n.nspowner) FROM pg_catalog.pg_namespace n WHERE '+USER_SCHEMA)
    schemas = cursor.fetchall()
    if len(schemas) != 1 or schemas[0][0] != 'public' or schemas[0][1] not in {ROLE, 'pg_database_owner'}:
        raise SafetyError('UNEXPECTED_SCHEMA_OR_OWNER')
    for code, query in EMPTY_QUERIES:
        cursor.execute(query)
        if cursor.fetchone() is not None:
            raise SafetyError(code)
    cursor.execute("""SELECT 1 FROM pg_catalog.pg_namespace n,
        LATERAL pg_catalog.aclexplode(COALESCE(n.nspacl, pg_catalog.acldefault('n', n.nspowner))) a
        WHERE n.nspname='public' AND
        ((a.grantee=0 AND a.privilege_type='CREATE') OR
         (a.grantee<>0 AND a.grantee NOT IN
          (SELECT oid FROM pg_catalog.pg_roles WHERE rolname IN (%s,'pg_database_owner'))))""", (ROLE,))
    if cursor.fetchone() is not None:
        raise SafetyError('UNEXPECTED_SCHEMA_GRANTS')
    cursor.execute("""SELECT 1 FROM pg_catalog.pg_database d,
        LATERAL pg_catalog.aclexplode(COALESCE(d.datacl, pg_catalog.acldefault('d', d.datdba))) a
        WHERE d.datname=current_database() AND
        ((a.grantee=0 AND a.privilege_type='CREATE') OR
         (a.grantee<>0 AND a.grantee<>(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=%s)))""", (ROLE,))
    if cursor.fetchone() is not None:
        raise SafetyError('UNEXPECTED_DATABASE_GRANTS')


def read_only_preflight(*, allow_connect=False, environ=None):
    if allow_connect is not True:
        raise SafetyError('EXPLICIT_READ_ONLY_FLAG_REQUIRED')
    target = designated_target(environ)
    connection = None
    failure = None
    result = None
    try:
        connection = connect_dbapi(target)
        with connection.cursor() as cursor:
            data = verify_connected_identity(cursor)
            verify_pristine_objects(cursor)
        result = {k: data[k] for k in ('database', 'session_user', 'current_user', 'host', 'port', 'schema', 'owner', 'server_version')}
        result.update(read_only=True, empty=True, role_restrictions_verified=True,
                      object_inventory_verified=True, writes_performed=False,
                      scope='Pristine read-only preflight only; migrations and acceptance not executed')
    except SafetyError as error:
        failure = error
    except Exception:
        failure = SafetyError('CONNECTION_OR_CATALOG_CHECK_FAILED')
    finally:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                failure = failure or SafetyError('CONNECTION_CLEANUP_FAILED')
            try:
                connection.close()
            except Exception:
                failure = failure or SafetyError('CONNECTION_CLEANUP_FAILED')
    if failure is not None:
        raise failure from None
    return result
