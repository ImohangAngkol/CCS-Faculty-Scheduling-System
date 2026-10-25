"""Retained profile offline tests. All real network entry points blocked."""
import copy
import io
import json
import runpy
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations

import d15_workflow_guard as guard
from test_d15_target_guard import FakeConnection, environment, deny_real_connections


@pytest.mark.parametrize('path', ['physical','checkout','begin','statement','migration','fixture','cleanup','commit'])
@pytest.mark.parametrize('change', [{'database':'ccs_faculty_scheduling_dev'}, {'database':'postgres'},
    {'database':'template0'}, {'database':'template1'}, {'session_user':'postgres'}, {'current_user':'postgres'},
    {'host':'::1'}, {'host':'192.0.2.1'}, {'port':5433}])
def test_retained_paths_check_actual_identity_before_writes(monkeypatch,path,change):
    run = guard.WorkflowRun(environ=environment())
    run.active = True
    run.retained = {}
    connection = FakeConnection(change=change)
    converted = []
    connection.set_session = lambda **kw:converted.append(kw)
    monkeypatch.setattr(run,'_open',lambda:connection)
    monkeypatch.setattr(guard.base,'verify_academic_profile',lambda *args,**kw:None)
    monkeypatch.setattr(guard,'catalog',lambda *args:{})
    sa = SimpleNamespace(connection=SimpleNamespace(driver_connection=connection))
    with pytest.raises(guard.SafetyError, match='CONNECTED_IDENTITY_MISMATCH'):
        if path == 'physical':run._creator()
        elif path == 'checkout':run._checkout(connection,None,None)
        elif path == 'begin':run._begin(sa)
        elif path == 'commit':run._commit(sa)
        else:
            sql = guard.UPGRADES[0] if path == 'migration' else 'INSERT INTO users (id) VALUES (%s)' if path == 'fixture' else 'SELECT 1'
            run._before(sa,None,sql,{},None,False)
    assert not converted and all(q.startswith('SELECT') for q in connection.queries)


@pytest.mark.parametrize('sql', ['DROP TABLE academic_scopes','DROP TABLE gec_records','TRUNCATE users',
    'UPDATE academic_terms SET lifecycle=%s','INSERT INTO academic_scopes VALUES (%s)','DELETE FROM academic_courses',
    'ALTER TABLE users ADD COLUMN unwanted int','CREATE TABLE gec_records (wrong int)','SET ROLE postgres',
    'CREATE DATABASE wrong','CREATE SCHEMA wrong','LOCK TABLE other.gec_records IN SHARE MODE'])
def test_retained_schema_and_data_destruction_rejected(sql):
    with pytest.raises(guard.SafetyError):guard.validate_statement(sql)


def test_all_real_upgrade_statements_and_only_explicit_revisions():
    statements = []
    context = MigrationContext.configure(dialect_name='postgresql',opts={'as_sql':True,'output_buffer':io.StringIO()})
    def collect(sql,*args,**kwargs):
        guard.validate_statement(sql)
        statements.append(sql)
    with patch.object(context.impl,'_exec',side_effect=collect), Operations.context(context):
        for module in guard.MODULES:module['upgrade']()
    assert len(statements) == len(guard.UPGRADES)
    assert len(guard.TABLES) == 20 and len(guard.NEW_TABLES) == 9
    assert [m['down_revision'] for m in guard.MODULES] == ['4c_0001','d9_0001','d11_0001','d12_0001']


def compatible():
    frozen = runpy.run_path(str(guard.ROOT/'backend/migrations/versions/4c_0001_academic_foundation.py'))
    fixture = pg18_fixture()
    value = {'server_version_num':fixture['server_version_num'],
        'columns':[[t,n,k,required,None] for t,columns in guard.expected_columns().items() for n,k,required in columns],
        'constraints':fixture['constraints'],
        'indexes':[[t,n,'fixture-defined'] for t,n in guard.expected_constraints_and_indexes()[1]],
        'functions':[], 'triggers':[]}
    for key in ('WRITE_LOCK_SQL','ROW_GUARD_SQL','CALENDAR_SQL'):
        sql=frozen[key]
        import re
        name=re.search(r'FUNCTION public\.(\w+)\(',sql)[1]
        value['functions'].append([name,sql.split('$$')[1],False,'v',['search_path=pg_catalog, public'],'plpgsql'])
    for table in frozen['TABLE_KEYS']:
        for trigger in ('academic_write_gate','academic_row_guard'):
            value['triggers'].append([table,trigger,'fixture-defined','O'])
    for table in ('academic_years','academic_terms'):
        value['triggers'].append([table,'academic_calendar_guard','fixture-defined','O'])
    return value


def pg18_fixture():
    return json.loads((guard.ROOT/'docs/testing/dashboard-d15/fixtures/pg18-constraint-inventory.json').read_text(encoding='utf-8'))


class Cursor:
    def __init__(self, *, revision='4c_0001', extra=False, rows=False):
        self.revision,self.extra,self.rows=revision,extra,rows
    def execute(self,sql,*args):
        assert sql.startswith('SELECT')
        self.sql=sql
    def fetchall(self):
        if 'SELECT relname' in self.sql:
            return [(n,) for n in guard.base.TABLES | ({'surprise'} if self.extra else set())]
        return [(self.revision,)]
    def fetchone(self):return (int(self.rows),)


@pytest.mark.parametrize('defect', ['none','revision','extra','rows','column','nullable','constraint','index','function','security','search_path','trigger','disabled'])
def test_select_only_retained_compatibility_gate(monkeypatch,defect):
    value=compatible()
    cursor=Cursor(revision='d9_0001' if defect=='revision' else '4c_0001',extra=defect=='extra',rows=defect=='rows')
    if defect=='column':value['columns'].pop()
    if defect=='nullable':value['columns'][0][3]=not value['columns'][0][3]
    if defect=='constraint':value['constraints'][0][4]=False
    if defect=='index':value['indexes'].append(['users','unexpected_index','fixture-defined'])
    if defect=='function':value['functions'][0][1]='BEGIN RETURN NEW; END'
    if defect=='security':value['functions'][0][2]=True
    if defect=='search_path':value['functions'][0][4]=None
    if defect=='trigger':value['triggers'].pop()
    if defect=='disabled':value['triggers'][0][3]='D'
    monkeypatch.setattr(guard.base,'verify_academic_profile',lambda *args,**kwargs:None)
    monkeypatch.setattr(guard,'catalog',lambda *args:value)
    if defect=='none':assert guard.verify_retained(cursor)==value
    else:
        with pytest.raises(guard.SafetyError):guard.verify_retained(cursor)


def test_catalog_change_stops_write_mode_without_repair(monkeypatch):
    run=guard.WorkflowRun(environ=environment());run.retained={'columns':[]}
    connection=FakeConnection()
    monkeypatch.setattr(guard.base,'verify_academic_profile',lambda *args,**kwargs:None)
    monkeypatch.setattr(guard,'catalog',lambda *args:{'columns':['changed']})
    with pytest.raises(guard.SafetyError,match='RETAINED_SCHEMA_CHANGED'):run._check(connection)


def test_first_phase_defaults_stay_pristine_and_academic_only():
    with pytest.raises(guard.SafetyError):guard.base.validate_statement(guard.UPGRADES[0])
    assert guard.base.GuardedRun._check is not guard.WorkflowRun._check


def test_independent_pg18_fixture_has_all_reported_constraint_categories():
    from collections import Counter
    import hashlib
    fixture = pg18_fixture()
    assert Counter(row[2] for row in fixture['constraints']) == {'n':76,'p':11,'c':37,'f':11,'u':18}
    assert len(fixture['required_not_null_columns']) == 76
    for record in fixture['source_files']:
        assert hashlib.sha256((guard.ROOT/record['path']).read_bytes()).hexdigest() == record['sha256']
    value = compatible()
    before = copy.deepcopy(value)
    guard.verify_constraint_inventory(value, guard.expected_columns())
    assert value == before  # Do not remove NOT NULL records from fingerprints.


@pytest.mark.parametrize('defect', ['missing','unexpected','nullable','wrong_column','wrong_table','empty_binding',
    'multiple_columns','repeated_columns','unresolved_attribute','duplicate_name','duplicate_binding',
    'unvalidated','unenforced','numeric_validation','numeric_enforcement','missing_enforcement_field',
    'wrong_definition','inconsistent_definition','unknown_constraint_type','wrong_non_nn_type',
    'extra_non_nn','missing_non_nn','duplicate_non_nn','non_nn_unvalidated','non_nn_unenforced'])
def test_pg18_rejects_bad_constraints_without_ignoring_type_n(defect):
    value = compatible()
    rows = value['constraints']
    row = next(r for r in rows if r[0]=='users' and r[2]=='n' and r[6]==['username'])
    ordinary = next(r for r in rows if r[2]=='p')
    if defect=='missing':rows.remove(row)
    elif defect=='unexpected':rows.append(['surprise','unexpected_nn','n','NOT NULL id',True,True,['id']])
    elif defect=='nullable':row[6]=['faculty_id'];row[3]='NOT NULL faculty_id'
    elif defect=='wrong_column':row[6]=['unknown'];row[3]='NOT NULL unknown'
    elif defect=='wrong_table':row[0]='academic_scopes'
    elif defect=='empty_binding':row[6]=[]
    elif defect=='multiple_columns':row[6]=['username','id']
    elif defect=='repeated_columns':row[6]=['username','username']
    elif defect=='unresolved_attribute':row[6]=[None]
    elif defect=='duplicate_name':rows.append(copy.deepcopy(row))
    elif defect=='duplicate_binding':rows.append([row[0],'different_nn_name',*row[2:]])
    elif defect=='unvalidated':row[4]=False
    elif defect=='unenforced':row[5]=False
    elif defect=='numeric_validation':row[4]=1
    elif defect=='numeric_enforcement':row[5]=1
    elif defect=='missing_enforcement_field':row.pop(5)
    elif defect=='wrong_definition':row[3]='CHECK (username IS NOT NULL)'
    elif defect=='inconsistent_definition':row[3]='NOT NULL id'
    elif defect=='unknown_constraint_type':rows.append(['users','unexpected','x','EXCLUDE',True,True,[]])
    elif defect=='wrong_non_nn_type':ordinary[2]='c'
    elif defect=='extra_non_nn':rows.append(['users','extra','c','CHECK (true)',True,True,[]])
    elif defect=='missing_non_nn':rows.remove(ordinary)
    elif defect=='duplicate_non_nn':rows.append(copy.deepcopy(ordinary))
    elif defect=='non_nn_unvalidated':ordinary[4]=False
    elif defect=='non_nn_unenforced':ordinary[5]=False
    with pytest.raises(guard.SafetyError):
        guard.verify_constraint_inventory(value, guard.expected_columns())


@pytest.mark.parametrize('version', [160000,170000,180006])
def test_catalog_version_handling_does_not_broaden_live_target_allowlist(version):
    value = compatible()
    value['server_version_num'] = version
    if version < 180000:
        value['constraints'] = [r for r in value['constraints'] if r[2]!='n']
    guard.verify_constraint_inventory(value, guard.expected_columns())
    # The exact D15 live identity verifier remains separately pinned to PG18.
    if version < 180000:
        value['constraints'].append(['users','nn','n','NOT NULL username',True,True,['username']])
        with pytest.raises(guard.SafetyError):guard.verify_constraint_inventory(value,guard.expected_columns())


@pytest.mark.parametrize('version', [170000,180006])
def test_catalog_captures_binding_and_enforcement_without_dropping_rows(version):
    fixture = pg18_fixture()
    constraints = [r for r in fixture['constraints'] if version>=180000 or r[2]!='n']
    class CatalogCursor:
        def __init__(self):self.queries=[]
        def execute(self,sql,parameters=None):
            assert sql.startswith('SELECT')
            self.queries.append(sql)
        def fetchone(self):return (str(version),)
        def fetchall(self):return copy.deepcopy(constraints) if 'pg_catalog.pg_constraint' in self.queries[-1] else []
    cursor = CatalogCursor()
    value = guard.catalog(cursor)
    assert value['constraints'] == constraints and value['server_version_num'] == version
    query = next(q for q in cursor.queries if 'pg_catalog.pg_constraint' in q)
    assert ('k.conenforced' in query) is (version>=180000)
    assert 'unnest(k.conkey) WITH ORDINALITY' in query and 'LEFT JOIN pg_catalog.pg_attribute' in query
    guard.verify_constraint_inventory(value,guard.expected_columns())
    before = guard.fingerprint(value)
    value['constraints'][0][5] = False
    assert guard.fingerprint(value) != before


@pytest.mark.parametrize('field,replacement', [(1,'changed_name'),(2,'c'),(3,'NOT NULL other'),(4,False),(5,False),(6,['other'])])
def test_every_not_null_metadata_field_remains_fingerprinted(field,replacement):
    value = compatible()
    before = guard.fingerprint(value)
    row = next(r for r in value['constraints'] if r[2]=='n')
    row[field] = replacement
    assert guard.fingerprint(value) != before


def test_quoted_not_null_definition_and_distinct_names_for_distinct_columns():
    value = compatible()
    for row in value['constraints']:
        if row[2]=='n':row[3]='NOT NULL "'+row[6][0]+'"'
    guard.verify_constraint_inventory(value,guard.expected_columns())
