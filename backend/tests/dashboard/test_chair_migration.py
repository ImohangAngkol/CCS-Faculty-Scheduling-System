"""PostgreSQL SQL rendering only: never connect or execute migrations."""
from io import StringIO
from pathlib import Path
import runpy
from alembic import command
from alembic.config import Config
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects.postgresql import dialect
from chair_models import ChairDecision

def test_frozen_additive_schema_and_guards():
    value=runpy.run_path(str(Path('migrations/versions/d12_0001_chair_decisions.py')))
    assert value['down_revision']=='d11_0001'
    assert str(CreateTable(ChairDecision.__table__).compile(dialect=dialect())).strip() in value['DDL']
    sql='\n'.join(value['DDL'])
    assert 'FOR UPDATE' in sql and 'request already decided' in sql
    assert 'UNIQUE (request_id)' in sql and 'BEFORE UPDATE OR DELETE' in sql
    assert 'ALTER TABLE' not in sql and 'faculty_preferences' not in sql

def test_offline_render_and_refuse_retained_downgrade(monkeypatch):
    monkeypatch.setenv('DATABASE_URL','postgresql://offline.invalid/disposable')
    out=StringIO();config=Config('alembic.ini',output_buffer=out)
    command.upgrade(config,'d11_0001:d12_0001',sql=True)
    assert 'CREATE TABLE faculty_adjustment_decisions' in out.getvalue()
    assert 'CREATE TABLE faculty_adjustment_requests' not in out.getvalue()
    out.seek(0);out.truncate()
    command.downgrade(config,'d12_0001:d11_0001',sql=True)
    sql=out.getvalue();assert sql.index('downgrade refuses retained decisions')<sql.index('DROP TABLE')
