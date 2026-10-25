"""Offline transport, abort and public-report regressions. No PG connections."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import psycopg2

import d15_workflow_guard as guard
import d15_workflow_plugin as plugin
import test_workflows_d15 as acceptance
from test_d15_target_guard import environment, deny_real_connections


@pytest.mark.parametrize('sql', guard.UPGRADES)
def test_each_frozen_upgrade_at_actual_psycopg2_transport_boundary(sql, monkeypatch):
    # Expected input is independently compiled by SQLAlchemy, not supplied by
    # the guard's expected-string helper. No engine or connection is constructed.
    dialect = psycopg2.dialect()
    compiled = text(sql).compile(dialect=dialect)
    wire = str(compiled)
    assert not compiled.params
    assert guard.validate_statement(wire,dialect=dialect,parameters=compiled.params) is False
    run = guard.WorkflowRun(environ=environment());run.active=True
    checked=[]
    monkeypatch.setattr(run,'_check',lambda connection:checked.append(connection))
    connection=SimpleNamespace(dialect=dialect,connection=SimpleNamespace(driver_connection='fictional-owned-driver'))
    run._before(connection,None,wire,compiled.params,None,False)
    assert checked==['fictional-owned-driver'] and run.counts['guarded_statements']==1


@pytest.mark.parametrize('change', ['single_percent','triple_percent','quad_percent','extra_percent','placeholder',
    'named_placeholder','extra_ddl','extra_comment','body','identifier','literal_spacing','trailing_semicolon'])
def test_compiled_ddl_tampering_is_rejected(change):
    dialect=psycopg2.dialect()
    original=guard.MODULES[0]['DDL'][13]
    wire=str(text(original).compile(dialect=dialect))
    assert '%ROWTYPE' in original and '%%ROWTYPE' in wire
    if change=='single_percent':wire=wire.replace('%%ROWTYPE','%ROWTYPE')
    elif change=='triple_percent':wire=wire.replace('%%ROWTYPE','%%%ROWTYPE')
    elif change=='quad_percent':wire=wire.replace('%%ROWTYPE','%%%%ROWTYPE')
    elif change=='extra_percent':wire=wire.replace('DECLARE','DECLARE %')
    elif change=='placeholder':wire=wire.replace('gec_records%%ROWTYPE','%s')
    elif change=='named_placeholder':wire=wire.replace('gec_records%%ROWTYPE','%(record)s')
    elif change=='extra_ddl':wire+='; CREATE TABLE surprise (id int)'
    elif change=='extra_comment':wire+=' -- modified'
    elif change=='body':wire=wire.replace('FOR UPDATE','FOR SHARE')
    elif change=='identifier':wire=wire.replace('d9_guard_event','other_function')
    elif change=='literal_spacing':wire=wire.replace('stale GEC transition','stale  GEC transition')
    elif change=='trailing_semicolon':wire+=';'
    with pytest.raises(guard.SafetyError,match='UNREVIEWED_WORKFLOW_DDL_REJECTED'):
        guard.validate_statement(wire,dialect=dialect)


@pytest.mark.parametrize('parameters,executemany', [({'unexpected':1},False),((1,),False),([],False),({},True)])
def test_frozen_ddl_cannot_gain_bindings_or_executemany(parameters,executemany):
    dialect=psycopg2.dialect();wire=str(text(guard.UPGRADES[0]).compile(dialect=dialect))
    with pytest.raises(guard.SafetyError,match='WORKFLOW_DDL_BINDINGS_REJECTED'):
        guard.validate_statement(wire,dialect=dialect,parameters=parameters,executemany=executemany)


def test_actual_configured_driver_is_required():
    with pytest.raises(guard.SafetyError,match='WORKFLOW_DIALECT_REJECTED'):
        guard.validate_statement(guard.UPGRADES[0],dialect=psycopg2.dialect(paramstyle='named'))


@pytest.mark.parametrize('primary,teardown', [(True,False),(True,True),(False,True),(False,False)])
def test_phase_reports_preserve_primary_and_teardown_independently(monkeypatch,primary,teardown):
    monkeypatch.setattr(plugin,'CASES',{})
    monkeypatch.setattr(plugin,'COLLECTED',['case-one','case-two'])
    def record(when,failed,error=None):
        plugin.record_report('case-one',SimpleNamespace(when=when,failed=failed,skipped=False),error)
    record('setup',False)
    record('call',primary,guard.SafetyError('UNREVIEWED_WORKFLOW_DDL_REJECTED') if primary else None)
    original=copy.deepcopy(plugin.CASES['case-one']['phases']['call'])
    record('teardown',teardown,AssertionError('private exception payload omitted') if teardown else None)
    result=plugin.outcome_summary()
    assert plugin.CASES['case-one']['phases']['call']==original
    assert result['counts']=={'PASSED':int(not primary),'FAILED':int(primary),'ERROR':int(teardown),'SKIPPED':0,'NOT_RUN':1}
    encoded=json.dumps(result)
    assert 'private exception payload' not in encoded
    assert ('safety_code' in plugin.CASES['case-one']['phases']['teardown']) is False


def test_setup_error_and_skips_have_truthful_report_counts(monkeypatch):
    monkeypatch.setattr(plugin,'CASES',{})
    monkeypatch.setattr(plugin,'COLLECTED',['error','skipped','not-run'])
    plugin.record_report('error',SimpleNamespace(when='setup',failed=True,skipped=False),RuntimeError('password=fictional-secret'))
    plugin.record_report('skipped',SimpleNamespace(when='setup',failed=False,skipped=True))
    result=plugin.outcome_summary()
    assert result['counts']=={'PASSED':0,'FAILED':0,'ERROR':1,'SKIPPED':1,'NOT_RUN':1}
    assert 'fictional-secret' not in json.dumps(result)


def test_safety_error_message_is_rebuilt_without_serializing_exception_arguments(monkeypatch):
    monkeypatch.setattr(plugin,'CASES',{});monkeypatch.setattr(plugin,'COLLECTED',['case'])
    error=guard.SafetyError('UNREVIEWED_WORKFLOW_DDL_REJECTED')
    error.args=('password=fictional-private-error',)
    plugin.record_report('case',SimpleNamespace(when='call',failed=True,skipped=False),error)
    record=plugin.outcome_summary()
    assert 'fictional-private-error' not in json.dumps(record)
    assert record['cases'][0]['phases']['call']['safety_code']=='UNREVIEWED_WORKFLOW_DDL_REJECTED'


class EndConnection:
    def __init__(self,revision,counts):
        self.revision,self.counts=revision,counts;self.queries=[]
        self.connection=SimpleNamespace(driver_connection=SimpleNamespace(cursor=lambda:self))
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def exec_driver_sql(self,sql):
        assert sql.startswith('SELECT')
        self.queries.append(sql)
        return SimpleNamespace(scalar_one=lambda:self.counts.get(sql.rsplit('.',1)[-1],0) if 'count(*)' in sql else self.revision)


@pytest.mark.parametrize('committed,rows', [(False,False),(True,False),(True,True)])
def test_end_verification_distinguishes_abort_from_committed_upgrade(monkeypatch,committed,rows):
    connection=EndConnection('d13_0001' if committed else '4c_0001',{'users':int(rows)})
    run=SimpleNamespace(upgrade_committed=committed,fixture_preparation_started=rows,retained={'fixture':'retained'})
    monkeypatch.setattr(acceptance,'verify_retained',lambda cursor:copy.deepcopy(run.retained))
    monkeypatch.setattr(acceptance,'catalog',lambda cursor:copy.deepcopy(run.retained))
    result=acceptance.verify_run_end(run,SimpleNamespace(connect=lambda:connection))
    assert result['revision']==('d13_0001' if committed else '4c_0001')
    assert result['fictional_rows_retained'] is rows
    assert result['status']==('COMPLETED_UPGRADE_VERIFIED' if committed else 'ABORT_RECOVERY_VERIFIED')
    if not committed:assert not connection.queries  # No demand for d13 on abort.


@pytest.mark.parametrize('defect', ['schema','revision','academic_rows','unexpected_rows','abort_recovery'])
def test_end_verification_does_not_hide_bad_state_or_repair_it(monkeypatch,defect):
    run=SimpleNamespace(upgrade_committed=defect!='abort_recovery',fixture_preparation_started=False,retained={'fixture':'retained'})
    counts={'academic_scopes':1} if defect=='academic_rows' else {'users':1} if defect=='unexpected_rows' else {}
    connection=EndConnection('4c_0001' if defect=='revision' else 'd13_0001',counts)
    monkeypatch.setattr(acceptance,'catalog',lambda cursor:{} if defect=='schema' else run.retained)
    monkeypatch.setattr(acceptance,'verify_retained',lambda cursor:{})
    with pytest.raises(guard.SafetyError):acceptance.verify_run_end(run,SimpleNamespace(connect=lambda:connection))
    assert all(sql.startswith('SELECT') for sql in connection.queries)


@pytest.mark.parametrize('end_error', [False,True])
def test_actual_fixture_abort_closes_owned_resources_and_preserves_diagnostic(monkeypatch,end_error):
    saved=[]
    class Run:
        def __init__(self):
            self.retained={};self.counts={};self._connections=[];self.upgrade_committed=False
            self.fixture_preparation_started=False;self.cleanup_verified=False
        def __enter__(self):return self
        def __exit__(self,*args):self.cleanup_verified=True
        def build_engine(self):return 'owned-engine'
    monkeypatch.setenv('D15_ACCEPTANCE_RUN','I_APPROVE_D15_RETAINED_WORKFLOW_ACCEPTANCE')
    monkeypatch.setattr(acceptance,'WorkflowRun',Run)
    monkeypatch.setattr(acceptance,'write_record',lambda name,data:saved.append((name,data)))
    def verify(run,engine):
        assert run.upgrade_committed is False and engine=='owned-engine'
        if end_error:raise guard.SafetyError('ABORT_RECOVERY_SCHEMA_MISMATCH')
        return {'status':'ABORT_RECOVERY_VERIFIED','fictional_rows_retained':False}
    monkeypatch.setattr(acceptance,'verify_run_end',verify)
    generator=acceptance.pg.__wrapped__();next(generator)
    with pytest.raises(guard.SafetyError if end_error else StopIteration):next(generator)
    summary=next(data for name,data in saved if name=='connection-guard-summary.json')
    assert summary['owned_connection_cleanup_verified'] is True
    assert summary['fictional_rows_retained'] is (None if end_error else False)


@pytest.mark.parametrize('mode',['abort','abort_and_teardown_error','success'])
def test_real_synthetic_pytest_sqlite_phase_evidence(tmp_path,mode):
    """Actual pytest hook execution, owned SQLite rollback, no PG connection."""
    import os,subprocess,sys
    evidence=tmp_path/'synthetic-workflows-postgresql';evidence.mkdir()
    bridge=tmp_path/'bridge.py'
    bridge.write_text(
        'from pathlib import Path\nimport d15_workflow_plugin as p\n'
        'p.BASE=Path(__file__).resolve().parent\n'
        'p.SCOPE="Synthetic pytest/owned SQLite reporting rehearsal; no PostgreSQL"\n'
        'pytest_runtest_makereport=p.pytest_runtest_makereport\n'
        'pytest_sessionfinish=p.pytest_sessionfinish\n'
        'def pytest_collection_finish(session): p.COLLECTED[:]=[i.nodeid for i in session.items]\n',encoding='utf-8')
    source='''import pytest
from sqlalchemy import create_engine
from d15_target_guard import SafetyError
@pytest.fixture
def owned(tmp_path):
    engine=create_engine('sqlite:///'+str(tmp_path/'fictional.sqlite'))
    with engine.begin() as c:
        c.exec_driver_sql('CREATE TABLE retained (revision TEXT)')
        c.exec_driver_sql("INSERT INTO retained VALUES ('4c_0001')")
    try:
        yield engine
    finally:
        with engine.connect() as c:
            assert c.exec_driver_sql('SELECT revision FROM retained').scalar_one()=='4c_0001'
            assert c.exec_driver_sql("SELECT count(*) FROM sqlite_master WHERE name='transient'").scalar_one()==0
        engine.dispose()
        TEARDOWN
def test_transaction(owned):
    with owned.connect() as c:
        c.exec_driver_sql('BEGIN')
        c.exec_driver_sql('CREATE TABLE transient (id INTEGER)')
        ACTION
'''
    source=source.replace('TEARDOWN',"raise AssertionError('private teardown details omitted')" if mode=='abort_and_teardown_error' else 'pass')
    source=source.replace('ACTION',"raise SafetyError('UNREVIEWED_WORKFLOW_DDL_REJECTED')" if mode!='success' else 'c.rollback()')
    (tmp_path/'test_synthetic.py').write_text(source,encoding='utf-8')
    allowed={'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','PATHEXT'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',PYTHONPATH=os.pathsep.join((str(tmp_path),str(Path(__file__).resolve().parent))),D15_ACCEPTANCE_EVIDENCE=str(evidence))
    result=subprocess.run([sys.executable,'-B','-m','pytest','-p','no:cacheprovider','-p','bridge','--noconftest',
        'test_synthetic.py','-q','--tb=no','--show-capture=no'],cwd=tmp_path,env=env,capture_output=True,text=True,timeout=40)
    outcomes=json.loads((evidence/'pytest-results.json').read_text(encoding='utf-8'))
    assert result.returncode==(0 if mode=='success' else 1)
    assert outcomes['counts']=={'PASSED':int(mode=='success'),'FAILED':int(mode!='success'),
        'ERROR':int(mode=='abort_and_teardown_error'),'SKIPPED':0,'NOT_RUN':0}
    phases=outcomes['cases'][0]['phases']
    if mode!='success':assert phases['call']['safety_code']=='UNREVIEWED_WORKFLOW_DDL_REJECTED'
    if mode=='abort_and_teardown_error':assert phases['teardown']['exception_type']=='AssertionError'
    assert 'private teardown details' not in json.dumps(outcomes)
    assert outcomes['scope'].startswith('Synthetic')


@pytest.mark.parametrize('mode',['success','abort','both_failures','unverified_final'])
def test_parent_public_summary_matches_phase_counts_and_verified_state(monkeypatch,tmp_path,capsys,mode):
    import run_workflows
    monkeypatch.setattr(run_workflows,'ROOT',tmp_path)
    monkeypatch.setattr(run_workflows,'BASE',tmp_path)
    monkeypatch.setattr(run_workflows,'verify_preservation',lambda:None)
    monkeypatch.setenv('D15_TEST_DATABASE_URL',environment()['D15_TEST_DATABASE_URL'])
    monkeypatch.setattr('sys.argv',['run_workflows.py','--execute'])
    passing=mode in {'success','unverified_final'}
    counts={'PASSED':10 if passing else 0,'FAILED':0 if passing else 1,'ERROR':int(mode=='both_failures'),'SKIPPED':0,'NOT_RUN':0 if passing else 9}
    def execute(command,**kwargs):
        assert 'DATABASE_URL' not in kwargs['env'] and 'PGPASSWORD' not in kwargs['env']
        evidence=Path(kwargs['env']['D15_ACCEPTANCE_EVIDENCE'])
        phases={'call':{'outcome':'FAILED','exception_type':'SafetyError','safety_code':'UNREVIEWED_WORKFLOW_DDL_REJECTED'}} if not passing else {}
        if mode=='both_failures':phases['teardown']={'outcome':'FAILED','exception_type':'AssertionError'}
        (evidence/'pytest-results.json').write_text(json.dumps({'counts':counts,'cases':[{'id':'test-case','phases':phases}],'case_counts':counts}),encoding='utf-8')
        end={'status':'COMPLETED_UPGRADE_VERIFIED','revision':'d13_0001'} if passing else {'status':'ABORT_RECOVERY_VERIFIED','revision':'4c_0001'}
        if mode=='unverified_final':end={'status':'FAILED'}
        (evidence/'connection-guard-summary.json').write_text(json.dumps({'guard':'d15-retained-workflow-write.1',
            'target':'ccs_ga_d15_test','role':'ccs_ga_d15_tester','counts':{'physical_connections':3,'identity_checks':8},
            'owned_connections_closed':True,'owned_connection_cleanup_verified':True,'cleanup_DDL_executed':False,
            'schema_retained':True if mode!='unverified_final' else None,'migration_commit_completed':passing,
            'fictional_rows_retained':passing if mode!='unverified_final' else None,'end_state_verification':end}),encoding='utf-8')
        return SimpleNamespace(returncode=0 if passing else 1,stdout='password=fictional-private-sentinel',stderr='')
    monkeypatch.setattr(run_workflows.subprocess,'run',execute)
    assert run_workflows.main()==(0 if mode=='success' else 1)
    public=json.loads(capsys.readouterr().out)
    assert public['counts']==counts
    assert len(public['phase_failures'])==(2 if mode=='both_failures' else 0 if passing else 1)
    assert public['status']==('ACCEPTANCE_PHASE_PASSED' if mode=='success' else 'STOP_REVIEW_REQUIRED')
    if not passing:assert public['fictional_rows_retained'] is False
    record=next(tmp_path.glob('*-workflows-postgresql/command.json')).read_text(encoding='utf-8')
    assert 'fictional-private-sentinel' not in record
