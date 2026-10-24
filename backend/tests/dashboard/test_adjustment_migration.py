"""No engine or PostgreSQL connection. Freeze/schema/upgrade/downgrade safety."""
from io import StringIO
import runpy
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects.postgresql import dialect
from adjustment_models import AdjustmentBase


def migration():
    return runpy.run_path(str(Path(__file__).resolve().parents[2]/'migrations/versions/d11_0001_faculty_adjustments.py'))


def test_frozen_schema_matches_models_and_only_adds_two_tables():
    m=migration()
    assert m['revision']=='d11_0001' and m['down_revision']=='d9_0001'
    assert set(AdjustmentBase.metadata.tables)=={'faculty_adjustment_requests','faculty_adjustment_events'}
    for table in AdjustmentBase.metadata.sorted_tables:
        assert str(CreateTable(table).compile(dialect=dialect())).strip() in m['DDL']
    sql='\n'.join(m['DDL'])
    assert 'd11_immutable' in sql and 'd11_guard_request' in sql
    assert 'faculty_preferences' not in sql and 'ALTER TABLE gec_' not in sql


def test_offline_upgrade_and_guarded_downgrade_render(monkeypatch):
    # Offline Alembic renders SQL without opening a socket. This is deliberately
    # not a live PostgreSQL test and does not execute the generated statements.
    monkeypatch.setenv('DATABASE_URL','postgresql://offline.invalid/disposable')
    stream=StringIO();config=Config('alembic.ini',output_buffer=stream)
    command.upgrade(config,'d9_0001:d11_0001',sql=True)
    sql=stream.getvalue()
    assert 'CREATE TABLE faculty_adjustment_requests' in sql and 'CREATE TABLE faculty_adjustment_events' in sql
    assert 'CREATE TABLE gec_' not in sql and 'CREATE TABLE academic_' not in sql
    stream.seek(0);stream.truncate()
    command.downgrade(config,'d11_0001:d9_0001',sql=True)
    sql=stream.getvalue()
    assert sql.index('downgrade refuses retained request history')<sql.index('DROP TABLE')
