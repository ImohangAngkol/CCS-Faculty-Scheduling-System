"""The original 17 Phase4C assertions, unchanged, using the D15-only fixture.

Collected with --noconftest: no legacy GA/data/autouse fixtures. There is no
Phase4C URL/approval substitution and no patch to its original safety helper.
"""
import importlib
import os
import sys
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'backend'))
from d15_write_guard import GuardedRun
from d15_target_guard import SafetyError

original = importlib.import_module('tests.academic.test_academic_postgresql')
for name in vars(original):
    if name.startswith('test_'):
        globals()[name] = getattr(original, name)
pg_rows = original.pg_rows


@pytest.fixture(scope='module')
def pg_engine():
    if os.environ.get('D15_ACCEPTANCE_RUN') != 'I_APPROVE_D15_PHASE4C_ACCEPTANCE':
        raise SafetyError('CONTROLLED_ACCEPTANCE_RUNNER_REQUIRED')
    run = GuardedRun()
    try:
        with run:
            engine = run.build_engine()
            with engine.begin() as connection:
                config = Config(str(ROOT/'backend/alembic.ini'))
                config.attributes['connection'] = connection
                command.upgrade(config, '4c_0001')
            yield engine
            # No cleanup DDL/reset/reseed. Downgrade assertions execute only in
            # rollback-only transactions on tables freshly created by this run.
    finally:
        from d15_phase4c_plugin import write_record
        write_record('connection-guard-summary.json', {'guard': 'd15-academic-write.1',
            'target': 'ccs_ga_d15_test', 'role': 'ccs_ga_d15_tester', 'counts': run.counts,
            'owned_connections_closed': all(getattr(c, 'closed', False) for c in run._connections),
            'schema_retained': True, 'cleanup_DDL_executed': False})
