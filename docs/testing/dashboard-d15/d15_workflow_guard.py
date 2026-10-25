"""Explicit second-phase profile: retained 4c -> additive d13, never reset.

No database access at import. The pristine first-phase profile stays the default.
Only frozen reviewed upgrade DDL is admitted; old academic/identity DDL and
academic DML, DROP and TRUNCATE are forbidden in this phase.
"""
import hashlib
import ast
import json
from pathlib import Path
import re
import runpy
from functools import lru_cache

from sqlalchemy.dialects import postgresql
from sqlalchemy import text

import d15_target_guard as target
import d15_write_guard as base
from d15_target_guard import SafetyError

ROOT = Path(__file__).resolve().parents[3]
REVISIONS = ('d9_0001_confirmation_ledger', 'd11_0001_faculty_adjustments',
             'd12_0001_chair_decisions', 'd13_0001_schedule_application')
MODULES = tuple(runpy.run_path(str(ROOT/'backend/migrations/versions'/f'{name}.py')) for name in REVISIONS)
UPGRADES = tuple(sql for module in MODULES for sql in module['DDL']) + (
    'CREATE INDEX ix_gec_revisions_record_id ON gec_revisions (record_id)',
    'CREATE INDEX ix_gec_events_record_id ON gec_events (record_id)')


def names(pattern):
    return frozenset(value.lower() for sql in UPGRADES for value in re.findall(pattern, sql, re.I))


NEW_TABLES = names(r'CREATE TABLE (\w+)')
TABLES = base.TABLES | NEW_TABLES
FUNCTIONS = base.FUNCTIONS | names(r'CREATE FUNCTION (\w+)')
TRIGGERS = base.TRIGGERS | names(r'CREATE TRIGGER (\w+)')
INDEXES = base.INDEXES | names(r'CREATE INDEX (\w+)')


def normalized(sql):
    return re.sub(r'\s+', ' ', sql.strip().rstrip(';')).strip()


REFUSAL_CHECKS = frozenset(node.value for name in REVISIONS
    for node in ast.walk(ast.parse((ROOT/'backend/migrations/versions'/f'{name}.py').read_text(encoding='utf-8')))
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith('DO $$ BEGIN IF EXISTS'))


@lru_cache(maxsize=8)
def compiled_statements(dialect):
    """Compile trusted frozen SQL, never rewrite the incoming wire statement."""
    if (dialect.name, dialect.driver, dialect.paramstyle) != ('postgresql','psycopg2','pyformat'):
        raise SafetyError('WORKFLOW_DIALECT_REJECTED')
    def compile_all(statements):
        result = []
        for statement in statements:
            compiled = text(statement).compile(dialect=dialect)
            if compiled.params:
                raise SafetyError('FROZEN_DDL_HAS_UNEXPECTED_BINDINGS')
            result.append(str(compiled))
        return frozenset(result)
    return compile_all(UPGRADES), compile_all(REFUSAL_CHECKS)


def validate_statement(sql, *, dialect=None, parameters=None, executemany=False):
    stripped = sql.lstrip()
    if re.match(r'(CREATE|ALTER|DO)\b', stripped, re.I):
        if executemany or (parameters is not None and
                (not isinstance(parameters,(dict,tuple)) or len(parameters) != 0)):
            raise SafetyError('WORKFLOW_DDL_BINDINGS_REJECTED')
        ddl, programs = (frozenset(UPGRADES), REFUSAL_CHECKS) if dialect is None else compiled_statements(dialect)
        if re.match(r'DO\b', stripped, re.I):
            if sql not in programs:
                raise SafetyError('UNREVIEWED_WORKFLOW_PROGRAM_REJECTED')
        elif sql not in ddl:
            raise SafetyError('UNREVIEWED_WORKFLOW_DDL_REJECTED')
    if re.match(r'(DROP|TRUNCATE)\b', stripped, re.I):
        raise SafetyError('RETAINED_SCHEMA_DESTRUCTION_REJECTED')
    if re.search(r'\b(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+"?(academic_\w+)', sql, re.I):
        raise SafetyError('RETAINED_ACADEMIC_WRITE_REJECTED')
    return base.validate_statement(sql, tables=TABLES, functions=FUNCTIONS, triggers=TRIGGERS, indexes=INDEXES)


def catalog(cursor, tables=base.TABLES, functions=base.FUNCTIONS):
    """Canonical metadata only. Never exports user rows or credentials."""
    cursor.execute("SELECT pg_catalog.current_setting('server_version_num')")
    version = int(cursor.fetchone()[0])
    # conenforced was added in PG18. Earlier servers enforce these constraints
    # implicitly; do not reference a nonexistent catalog column on those servers.
    enforced = 'k.conenforced' if version >= 180000 else 'TRUE'
    selected = tuple(sorted(tables))
    result = {'server_version_num': version}
    for key, query, parameters in (
        ('columns', """SELECT c.relname,a.attname,pg_catalog.format_type(a.atttypid,a.atttypmod),a.attnotnull,
            pg_catalog.pg_get_expr(d.adbin,d.adrelid) FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
            JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
            LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
            WHERE n.nspname='public' AND c.relkind='r' AND c.relname IN %s ORDER BY c.relname,a.attnum""", (selected,)),
        ('constraints', """SELECT c.relname,k.conname,k.contype,pg_catalog.pg_get_constraintdef(k.oid),k.convalidated,
            """+enforced+""", ARRAY(SELECT a.attname FROM unnest(k.conkey) WITH ORDINALITY u(num,pos)
            LEFT JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid AND a.attnum=u.num AND NOT a.attisdropped
            ORDER BY u.pos)
            FROM pg_catalog.pg_constraint k JOIN pg_catalog.pg_class c ON c.oid=k.conrelid
            JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public'
            AND c.relname IN %s ORDER BY c.relname,k.conname""", (selected,)),
        ('indexes', """SELECT tablename,indexname,indexdef FROM pg_catalog.pg_indexes
            WHERE schemaname='public' AND tablename IN %s ORDER BY tablename,indexname""", (selected,)),
        ('triggers', """SELECT c.relname,t.tgname,pg_catalog.pg_get_triggerdef(t.oid),t.tgenabled FROM pg_catalog.pg_trigger t
            JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND NOT t.tgisinternal AND c.relname IN %s ORDER BY c.relname,t.tgname""", (selected,)),
        ('functions', """SELECT p.proname,p.prosrc,p.prosecdef,p.provolatile,p.proconfig,l.lanname
            FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
            JOIN pg_catalog.pg_language l ON l.oid=p.prolang WHERE n.nspname='public' AND p.proname IN %s ORDER BY p.proname""", (tuple(sorted(functions)),))):
        cursor.execute(query, parameters)
        result[key] = [list(row) for row in cursor.fetchall()]
    return result


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def expected_columns():
    from identity_models import Base
    import academic_models  # noqa: F401
    values = {}
    for name in base.TABLES - {'alembic_version'}:
        table = Base.metadata.tables[name]
        values[name] = [(c.name, str(c.type.compile(dialect=postgresql.dialect())).lower(), not c.nullable) for c in table.columns]
    values['alembic_version'] = [('version_num', 'varchar(32)', True)]
    return values


def expected_constraints_and_indexes(*, with_kinds=False):
    from identity_models import Base
    from sqlalchemy import PrimaryKeyConstraint, UniqueConstraint, ForeignKeyConstraint, CheckConstraint
    kinds = {PrimaryKeyConstraint:'p', UniqueConstraint:'u', ForeignKeyConstraint:'f', CheckConstraint:'c'}
    constraints = {('alembic_version', 'alembic_version_pkc'):'p'}
    indexes = {('alembic_version', 'alembic_version_pkc')}
    for name in base.TABLES - {'alembic_version'}:
        table = Base.metadata.tables[name]
        for constraint in table.constraints:
            columns = '_'.join(c.name for c in constraint.columns)
            label = constraint.name
            if label is None:
                suffix = ('pkey' if isinstance(constraint, PrimaryKeyConstraint) else
                          'key' if isinstance(constraint, UniqueConstraint) else 'fkey')
                label = name+'_'+('' if suffix == 'pkey' else columns+'_')+suffix
            constraints[name,label] = kinds[type(constraint)]
            if isinstance(constraint, (PrimaryKeyConstraint, UniqueConstraint)):
                indexes.add((name,label))
        indexes |= {(name,i.name) for i in table.indexes}
    return (constraints if with_kinds else set(constraints)),indexes


def verify_constraint_inventory(value, expected):
    """Validate PG18 NOT NULL by binding, not by server-generated names.

    Names/definitions/flags/bindings of every constraint remain in catalog()
    and hence in the full preservation fingerprint. No type-n row is discarded.
    """
    required, _ = expected_constraints_and_indexes(with_kinds=True)
    required_nn = {(table,column) for table,columns in expected.items()
                   for column,kind,notnull in columns if notnull}
    seen_names, actual, actual_nn = set(), {}, set()
    modern = value['server_version_num'] >= 180000
    for row in value['constraints']:
        if not isinstance(row, (list,tuple)) or len(row) != 7:
            raise SafetyError('RETAINED_CONSTRAINT_METADATA_INVALID')
        table,name,kind,definition,validated,enforced,columns = row
        if (not isinstance(table,str) or not isinstance(name,str) or not name
                or not isinstance(definition,str) or not isinstance(columns,(list,tuple))
                or any(not isinstance(c,str) or not c for c in columns)
                or len(set(columns)) != len(columns)):
            raise SafetyError('RETAINED_CONSTRAINT_METADATA_INVALID')
        if (table,name) in seen_names:
            raise SafetyError('RETAINED_CONSTRAINT_DUPLICATE')
        seen_names.add((table,name))
        if validated is not True or enforced is not True:
            raise SafetyError('RETAINED_CONSTRAINT_NOT_ENFORCED_OR_VALIDATED')
        if kind == 'n':
            if not modern or len(columns) != 1 or (table,columns[0]) not in required_nn:
                raise SafetyError('RETAINED_NOT_NULL_BINDING_MISMATCH')
            binding = table,columns[0]
            if binding in actual_nn:
                raise SafetyError('RETAINED_NOT_NULL_DUPLICATE')
            column = columns[0]
            quoted = '"'+column.replace('"','""')+'"'
            if definition not in {'NOT NULL '+column, 'NOT NULL '+quoted}:
                raise SafetyError('RETAINED_NOT_NULL_DEFINITION_MISMATCH')
            actual_nn.add(binding)
        else:
            actual[table,name] = kind
    if actual != required:
        raise SafetyError('RETAINED_CONSTRAINT_CONTRACT_MISMATCH')
    if modern and actual_nn != required_nn:
        raise SafetyError('RETAINED_NOT_NULL_INVENTORY_MISMATCH')


def verify_retained(cursor):
    """SELECT-only entry gate, repeated under the owned lifetime session lock."""
    base.verify_academic_profile(cursor)
    cursor.execute("SELECT relname FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND relkind='r'")
    if {row[0] for row in cursor.fetchall()} != base.TABLES:
        raise SafetyError('RETAINED_TABLE_INVENTORY_MISMATCH')
    cursor.execute('SELECT version_num FROM public.alembic_version')
    if cursor.fetchall() != [('4c_0001',)]:
        raise SafetyError('RETAINED_REVISION_MISMATCH')
    value = catalog(cursor)
    actual = {}
    for table, name, kind, required, default in value['columns']:
        actual.setdefault(table, []).append((name, kind.replace('character varying', 'varchar'), required))
    expected = expected_columns()
    # Column order is not semantic. Nullability/type/length and complete names are.
    if {k: sorted(v) for k, v in actual.items()} != {k: sorted(v) for k, v in expected.items()}:
        raise SafetyError('RETAINED_COLUMN_CONTRACT_MISMATCH')
    verify_constraint_inventory(value, expected)
    _, required_indexes = expected_constraints_and_indexes()
    if {(row[0],row[1]) for row in value['indexes']} != required_indexes:
        raise SafetyError('RETAINED_INDEX_INVENTORY_MISMATCH')
    if {row[0] for row in value['functions']} != base.FUNCTIONS:
        raise SafetyError('RETAINED_FUNCTION_INVENTORY_MISMATCH')
    # Compare actual PL/pgSQL bodies with the frozen Phase4C migration.
    frozen = runpy.run_path(str(ROOT/'backend/migrations/versions/4c_0001_academic_foundation.py'))
    bodies = {re.search(r'FUNCTION public\.(\w+)\(', frozen[key])[1]: frozen[key].split('$$')[1]
              for key in ('WRITE_LOCK_SQL', 'ROW_GUARD_SQL', 'CALENDAR_SQL')}
    for name, body, security, volatility, config, language in value['functions']:
        if (normalized(body) != normalized(bodies[name]) or security or volatility != 'v'
                or config != ['search_path=pg_catalog, public'] or language != 'plpgsql'):
            raise SafetyError('RETAINED_FUNCTION_CONTRACT_MISMATCH')
    expected_triggers = {(table, trigger) for table in frozen['TABLE_KEYS']
                         for trigger in ('academic_write_gate', 'academic_row_guard')}
    expected_triggers |= {(table, 'academic_calendar_guard') for table in ('academic_years', 'academic_terms')}
    if {(r[0], r[1]) for r in value['triggers']} != expected_triggers or any(row[3] != 'O' for row in value['triggers']):
        raise SafetyError('RETAINED_TRIGGER_CONTRACT_MISMATCH')
    for table in sorted(base.TABLES - {'alembic_version'}):
        cursor.execute('SELECT count(*) FROM public.'+table)
        if cursor.fetchone() != (0,):
            raise SafetyError('RETAINED_UNEXPECTED_ROWS')
    return value


class WorkflowRun(base.GuardedRun):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.retained = None
        self.upgrade_committed = False
        self.fixture_preparation_started = False
        self.cleanup_verified = False

    def close(self):
        self.cleanup_verified = False
        super().close()
        self.cleanup_verified = True

    def _check(self, connection, *, pristine=False, rollback=False):
        try:
            with connection.cursor() as cursor:
                target.verify_connected_identity(cursor, read_only='on' if pristine else 'either')
                self.counts['identity_checks'] += 1
                if pristine:
                    value = verify_retained(cursor)
                    if self.retained is not None and value != self.retained:
                        raise SafetyError('RETAINED_SCHEMA_CHANGED_DURING_PREFLIGHT')
                    self.retained = value
                else:
                    base.verify_academic_profile(cursor, tables=TABLES, functions=FUNCTIONS, triggers=TRIGGERS)
                    if self.retained is None or catalog(cursor) != self.retained:
                        raise SafetyError('RETAINED_SCHEMA_CHANGED')
        except SafetyError:
            raise
        except Exception:
            raise SafetyError('WORKFLOW_IDENTITY_OR_PROFILE_FAILED') from None
        finally:
            if rollback:
                try:
                    connection.rollback()
                except Exception:
                    raise SafetyError('GUARDED_CHECK_ROLLBACK_FAILED') from None

    def _before(self, connection, cursor, statement, parameters, context, executemany):
        if not self.active:
            raise SafetyError('RUN_NOT_ACTIVE')
        if not validate_statement(statement, dialect=getattr(connection,'dialect',None),
                                  parameters=parameters, executemany=executemany):
            self._check(connection.connection.driver_connection)
        self.counts['guarded_statements'] += 1
