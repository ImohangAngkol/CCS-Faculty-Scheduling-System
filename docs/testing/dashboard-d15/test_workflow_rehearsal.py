"""Only SQLite fixture rehearsal; not PostgreSQL acceptance. No PG connector."""
from pathlib import Path
import sys

import psycopg2
import pytest
from sqlalchemy import create_engine, event

sys.path.insert(0, str(Path(__file__).resolve().parents[3]/'backend'))
from test_workflows_d15 import (
    test_02_durable_confirmation_revision_and_concurrent_one_winner,
    test_04_actual_v2_generation_from_postgresql_heads,
    test_05_owned_request_submit_unauthorized_and_idempotency,
    test_06_independent_chair_concurrency_and_no_schedule_mutation,
    test_07_application_failure_rolls_back_and_same_command_recovers,
    test_08_independent_applications_publish_once_and_retry_is_idempotent,
    test_10_revocation_blocks_fresh_v2_scope_and_preserves_history,
)


@pytest.fixture(scope='module')
def workflow(tmp_path_factory):
    patch = pytest.MonkeyPatch()
    def forbidden(*args, **kwargs):
        pytest.fail('Network/PostgreSQL forbidden in rehearsal')
    patch.setattr(psycopg2, 'connect', forbidden)
    root = tmp_path_factory.mktemp('sqlite-only')
    engine = create_engine('sqlite:///'+str(root/'fictional.sqlite'), connect_args={'check_same_thread':False})
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    from identity_models import Base
    from confirmation_models import ConfirmationBase, guard_sql, transition_sql
    from adjustment_models import AdjustmentBase
    from tests.dashboard.chair_sqlite import install as chair
    from tests.dashboard.application_sqlite import install as application
    for metadata in (Base.metadata, ConfirmationBase.metadata, AdjustmentBase.metadata):
        metadata.create_all(engine)
    chair(engine)
    application(engine)
    with engine.begin() as connection:
        for statement in guard_sql('sqlite')+transition_sql('sqlite'):
            connection.exec_driver_sql(statement)
        for operation in ('UPDATE','DELETE'):
            connection.exec_driver_sql(f"CREATE TRIGGER d11_events_{operation} BEFORE {operation} ON faculty_adjustment_events BEGIN SELECT RAISE(ABORT,'immutable history'); END")
        connection.exec_driver_sql("CREATE TRIGGER d11_requests_delete BEFORE DELETE ON faculty_adjustment_requests BEGIN SELECT RAISE(ABORT,'immutable history'); END")
    from workflow_fixture import resources
    try:
        with resources(engine, patch, root) as f:
            yield f
    finally:
        engine.dispose()
        patch.undo()
