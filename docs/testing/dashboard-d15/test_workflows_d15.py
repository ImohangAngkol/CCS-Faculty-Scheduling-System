"""Ordered, retained-data D9-D13 PostgreSQL acceptance. Stop at first failure.

Not a resettable suite. Exact retained 4c entry gate; migrate once, keep all
fictional rows. Import/collection never connects. No browser evidence claimed.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import event, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'backend'))
from d15_workflow_guard import WorkflowRun, TABLES, FUNCTIONS, TRIGGERS, catalog, fingerprint, verify_retained
from d15_target_guard import SafetyError
from d15_workflow_plugin import write_record


def configuration(connection):
    config = Config(str(ROOT/'backend/alembic.ini'))
    config.set_main_option('script_location', str(ROOT/'backend/migrations'))
    config.attributes['connection'] = connection
    return config


def verify_run_end(run, engine):
    """SELECT-only inspection; never repair an aborted or partially committed run."""
    with engine.connect() as connection:
        if not run.upgrade_committed:
            with connection.connection.driver_connection.cursor() as cursor:
                recovered = verify_retained(cursor)
            if recovered != run.retained:
                raise SafetyError('ABORT_RECOVERY_SCHEMA_MISMATCH')
            return {'status':'ABORT_RECOVERY_VERIFIED', 'revision':'4c_0001',
                    'schema_matches_entry':True, 'all_ten_fixture_tables_empty':True,
                    'fictional_rows_retained':False}
        revision = connection.exec_driver_sql('SELECT version_num FROM public.alembic_version').scalar_one()
        if revision != 'd13_0001':
            raise SafetyError('COMPLETED_UPGRADE_REVISION_MISMATCH')
        with connection.connection.driver_connection.cursor() as cursor:
            if catalog(cursor) != run.retained:
                raise SafetyError('RETAINED_SCHEMA_CHANGED')
        counts = {table:connection.exec_driver_sql('SELECT count(*) FROM public.'+table).scalar_one()
                  for table in sorted(TABLES-{'alembic_version'})}
        if any(count for table,count in counts.items() if table.startswith('academic_')):
            raise SafetyError('RETAINED_ACADEMIC_ROWS_CHANGED')
        if not run.fixture_preparation_started and any(counts.values()):
            raise SafetyError('UNEXPECTED_ROWS_BEFORE_FIXTURE')
        return {'status':'COMPLETED_UPGRADE_VERIFIED', 'revision':revision,
                'retained_schema_matches_entry':True, 'row_counts':counts,
                'fictional_rows_retained':any(counts.values())}


@pytest.fixture(scope='module')
def pg():
    if os.environ.get('D15_ACCEPTANCE_RUN') != 'I_APPROVE_D15_RETAINED_WORKFLOW_ACCEPTANCE':
        raise SafetyError('CONTROLLED_WORKFLOW_RUNNER_REQUIRED')
    run = WorkflowRun()
    end = {'status':'NOT_REACHED', 'fictional_rows_retained':None}
    try:
        with run:
            engine = run.build_engine()
            write_record('retained-schema.json', {'revision':'4c_0001', 'read_only_entry_verified':True,
                'schema_sha256':fingerprint(run.retained), 'catalog':run.retained, 'unexpected_rows':False})
            try:
                yield run, engine
            finally:
                try:
                    end = verify_run_end(run, engine)
                except BaseException:
                    end = {'status':'FAILED', 'fictional_rows_retained':None}
                    raise
    finally:
        write_record('connection-guard-summary.json', {'guard':'d15-retained-workflow-write.1', 'target':'ccs_ga_d15_test',
            'role':'ccs_ga_d15_tester', 'counts':run.counts,
            'owned_connections_closed':all(bool(getattr(c,'closed',False)) for c in run._connections),
            'owned_connection_cleanup_verified':run.cleanup_verified,
            'schema_retained':True if end['status'] in {'ABORT_RECOVERY_VERIFIED','COMPLETED_UPGRADE_VERIFIED'} else None,
            'migration_commit_completed':run.upgrade_committed,
            'fixture_preparation_started':run.fixture_preparation_started,
            'fictional_rows_retained':end['fictional_rows_retained'],
            'end_state_verification':end, 'cleanup_DDL_executed':False})


def test_01_additive_upgrade_atomic_rollback_then_commit(pg):
    run, engine = pg
    # First exercise rollback of the entire real migration chain. No downgrade,
    # DROP or cleanup is needed; PostgreSQL transactional DDL restores 4c.
    with engine.connect() as connection:
        transaction = connection.begin()
        command.upgrade(configuration(connection), 'd13_0001')
        assert connection.exec_driver_sql('SELECT version_num FROM public.alembic_version').scalar_one() == 'd13_0001'
        transaction.rollback()
        assert connection.exec_driver_sql('SELECT version_num FROM public.alembic_version').scalar_one() == '4c_0001'
        actual = set(connection.exec_driver_sql("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public'").scalars())
        from d15_write_guard import TABLES as old_tables
        assert actual == old_tables
    # Inject a real statement failure after all upgrade DDL and verify rollback.
    with pytest.raises(DBAPIError), engine.begin() as connection:
        command.upgrade(configuration(connection), 'd13_0001')
        connection.exec_driver_sql('SELECT 1/0')
    with engine.connect() as connection:
        assert connection.exec_driver_sql('SELECT version_num FROM public.alembic_version').scalar_one() == '4c_0001'
    with engine.begin() as connection:
        command.upgrade(configuration(connection), 'd13_0001')
    run.upgrade_committed = True  # Set only after the owned transaction commits.
    with engine.connect() as connection:
        actual = set(connection.exec_driver_sql("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public'").scalars())
        assert actual == TABLES and len(actual) == 20
        with connection.connection.driver_connection.cursor() as cursor:
            assert catalog(cursor) == run.retained
            upgraded = catalog(cursor, TABLES, FUNCTIONS)
        assert {r[0] for r in upgraded['functions']} == FUNCTIONS
        assert {r[1] for r in upgraded['triggers']} == TRIGGERS
        assert all(r[4] for r in upgraded['constraints'])
        write_record('upgraded-schema.json', {'revision':'d13_0001', 'catalog':upgraded,
            'schema_sha256':fingerprint(upgraded), 'retained_4c_schema_sha256':fingerprint(run.retained),
            'academic_schema_unchanged':True, 'migration_rollback_verified':True, 'statement_failure_rollback_verified':True})


@pytest.fixture(scope='module')
def workflow(pg, tmp_path_factory):
    from workflow_fixture import resources
    patch = pytest.MonkeyPatch()
    try:
        pg[0].fixture_preparation_started = True
        with resources(pg[1], patch, tmp_path_factory.mktemp('fictional-workflow')) as f:
            yield f
    finally:
        patch.undo()


def test_02_durable_confirmation_revision_and_concurrent_one_winner(workflow):
    from tests.dashboard.test_external_confirmations import proposal, decision, history
    from tests.dashboard.test_adjustments import session
    f = workflow
    headers = session(f,'admin')
    newer = proposal(f, headers, f.confirmation['record_id'], 1)
    with ThreadPoolExecutor(2) as pool:
        replies = list(pool.map(lambda _:decision(f,headers,newer).status_code, range(2)))
    assert sorted(replies) == [200,409]
    result = history(f,headers,newer)
    assert len(result['events']) == 2 and result['record']['version'] == 2
    f.confirmation = newer
    from services import ga_v2_constraints as constraints
    with Session(f.engine) as db:
        f.snapshot = constraints._read_snapshot(db, f.deployment.catalog, f.deployment.templates)
    assert f.snapshot.heads[0].revision_id == newer['revision_id']


def test_03_postgresql_ledger_triggers_and_row_lock_recovery(workflow):
    from confirmation_models import ExternalRecord, ExternalRevision, ConfirmationEvent
    f = workflow
    for statement in ('UPDATE gec_revisions SET reason=reason', 'DELETE FROM gec_events', 'UPDATE gec_records SET version=version'):
        with pytest.raises(DBAPIError) as caught, f.engine.begin() as connection:
            connection.exec_driver_sql(statement)
        assert caught.value.orig.pgcode == 'P0001'
    # Actual independent PG row-lock timeout; no service or driver mocked.
    id = UUID(f.confirmation['record_id'])
    with f.engine.begin() as first:
        first.execute(select(ExternalRecord).where(ExternalRecord.id==id).with_for_update()).all()
        with pytest.raises(DBAPIError) as caught, f.engine.begin() as second:
            second.exec_driver_sql("SET LOCAL lock_timeout='100ms'")
            second.execute(select(ExternalRecord).where(ExternalRecord.id==id).with_for_update()).all()
        assert caught.value.orig.pgcode == '55P03'
    with f.engine.begin() as connection:
        assert connection.execute(select(ExternalRecord.id).where(ExternalRecord.id==id).with_for_update()).scalar_one() == id
    # Downgrade guard must refuse populated history BEFORE any destructive SQL.
    from d15_workflow_guard import MODULES
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    with pytest.raises(DBAPIError), f.engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            MODULES[0]['downgrade']()
    with Session(f.engine) as db:
        assert db.get(ExternalRecord,id).version == 2


def test_04_actual_v2_generation_from_postgresql_heads(workflow):
    from tests.dashboard.test_system_acceptance import generate
    from services import ga_v2_store as store
    f = workflow
    f.run_id, f.result, elapsed = generate(f)
    assert f.result['revisions'][0]['revision_id'] == f.confirmation['revision_id']
    f.generated_bytes = store.path_for(f.run_id).read_bytes()
    assert f.result['source'] == 'GA-generated proposal' and not f.result['approved']


def test_05_owned_request_submit_unauthorized_and_idempotency(workflow):
    from tests.dashboard.test_system_acceptance import own_proposal
    from tests.dashboard.test_adjustments import create, command, session, ENDPOINT
    f = workflow
    body = {**own_proposal(f), 'operation_id':str(uuid4())}
    f.request = create(f,body)
    assert create(f,body)['id'] == f.request['id']
    reply = command(f,f.request,'submit')
    assert reply.status_code == 200
    f.request = reply.json()
    session(f,1)
    assert f.client.get(ENDPOINT+'/'+f.request['id']).status_code == 404
    f.client.cookies.clear()
    assert f.client.get(ENDPOINT+'/'+f.request['id']).status_code == 401
    f.headers = session(f,0)


def test_06_independent_chair_concurrency_and_no_schedule_mutation(workflow):
    from tests.dashboard.test_adjustments import session
    from tests.dashboard.test_chair_reviews import decide, decision_body
    from services import ga_v2_store as store
    f = workflow
    f.chair_headers = session(f,'admin')
    body = decision_body(f.request)
    with ThreadPoolExecutor(2) as pool:
        replies = list(pool.map(lambda _:decide(f,f.request,body={**body,'operation_id':str(uuid4())}).status_code,range(2)))
    assert sorted(replies) == [200,409]
    assert store.path_for(f.run_id).read_bytes() == f.generated_bytes
    from chair_models import ChairDecision
    with Session(f.engine) as db:
        decision = db.scalar(select(ChairDecision).where(ChairDecision.request_id==UUID(f.request['id'])))
        assert decision is not None and decision.action == 'APPROVE'


def test_07_application_failure_rolls_back_and_same_command_recovers(workflow):
    from tests.dashboard.test_schedule_applications import publisher, counts
    from application_models import ScheduleApplication, PublishedVersion
    f = workflow
    publisher(f)
    reply = f.client.get('/api/schedule-applications/'+f.request['id']+'/preview')
    assert reply.status_code == 200 and reply.json()['can_apply']
    f.apply_body = {**reply.json()['command'], 'operation_id':str(uuid4())}
    endpoint = '/api/schedule-applications/'+f.request['id']+'/apply'
    def failure(*args):
        raise IntegrityError('fictional transaction rollback probe',None,None)
    event.listen(ScheduleApplication,'after_insert',failure)
    try:
        assert f.client.post(endpoint,headers=f.apply_headers,json=f.apply_body).status_code == 409
    finally:
        event.remove(ScheduleApplication,'after_insert',failure)
    assert counts(f) == [0,0,0]
    def unavailable(*args):
        raise OperationalError('fictional dependency unavailable probe',None,None)
    event.listen(PublishedVersion,'before_insert',unavailable)
    try:
        response = f.client.post(endpoint,headers=f.apply_headers,json=f.apply_body)
        assert response.status_code == 503 and response.json()['detail']['code'] == 'APPLICATION_STORAGE_UNAVAILABLE'
    finally:
        event.remove(PublishedVersion,'before_insert',unavailable)
    assert counts(f) == [0,0,0]
    # Recovery is the next test's competing real transactions, same preview.


def test_08_independent_applications_publish_once_and_retry_is_idempotent(workflow):
    from tests.dashboard.test_schedule_applications import counts
    f = workflow
    endpoint = '/api/schedule-applications/'+f.request['id']+'/apply'
    with ThreadPoolExecutor(2) as pool:
        replies = list(pool.map(lambda _:f.client.post(endpoint,headers=f.apply_headers,
            json={**f.apply_body,'operation_id':str(uuid4())}),range(2)))
    assert sorted(r.status_code for r in replies) == [200,409]
    assert counts(f) == [2,1,1]
    successful = next(r.json() for r in replies if r.status_code == 200)
    from application_models import ScheduleApplication
    with Session(f.engine) as db:
        operation = db.scalar(select(ScheduleApplication.operation_id).where(ScheduleApplication.request_id==UUID(f.request['id'])))
    assert f.client.post(endpoint,headers=f.apply_headers,json={**f.apply_body,'operation_id':str(operation)}).json() == successful


def test_09_immutable_publication_history_own_view_and_new_connections(workflow):
    from tests.dashboard.test_adjustments import session
    from services import ga_v2_store as store
    from adjustment_models import AdjustmentRequest
    from services.adjustment_service import verify
    f = workflow
    for statement in ('UPDATE published_schedule_versions SET revision=revision', 'DELETE FROM schedule_adjustment_applications',
                      'DELETE FROM published_schedule_heads', 'DELETE FROM faculty_adjustment_decisions', 'DELETE FROM faculty_adjustment_events'):
        with pytest.raises(DBAPIError) as caught, f.engine.begin() as connection:
            connection.exec_driver_sql(statement)
        assert caught.value.orig.pgcode == 'P0001'
    with Session(f.engine) as db:
        record = db.get(AdjustmentRequest,UUID(f.request['id']))
        verify(db,record)
    session(f,0)
    own = f.client.get('/api/schedules/me').json()
    assert own['source']['post_ga_changes'] is True and own['source']['sequence'] == 2
    assert 'SYN202' not in json.dumps(own)
    assert store.path_for(f.run_id).read_bytes() == f.generated_bytes


def test_10_revocation_blocks_fresh_v2_scope_and_preserves_history(workflow):
    from tests.dashboard.test_adjustments import session
    from tests.dashboard.test_schedule_applications import counts
    from services import ga_v2_store as store
    f = workflow
    headers = session(f,'admin')
    response = f.client.post('/api/external-confirmations/records/'+f.confirmation['record_id']+'/revoke',headers=headers,
        json={'operation_id':str(uuid4()),'expected_version':2,'reason':'Fictional D15 revocation after retained publication'})
    assert response.status_code == 200
    # Changed complete head set invalidates a previously pinned V2 request.
    from services.ga_v2_constraints import ConstraintError
    with pytest.raises(ConstraintError) as caught:
        with f.deployment.authority.pinned(f.snapshot):
            pass
    assert caught.value.code == 'CONFIRMATION_NOT_CURRENT'
    assert counts(f) == [2,1,1] and store.path_for(f.run_id).read_bytes() == f.generated_bytes
