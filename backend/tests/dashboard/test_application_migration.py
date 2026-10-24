from io import StringIO
from pathlib import Path
import runpy
from alembic import command
from alembic.config import Config
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects.postgresql import dialect
from application_models import ApplicationBase

def test_frozen_additive_publication_schema():
    m=runpy.run_path('migrations/versions/d13_0001_schedule_application.py');assert m['down_revision']=='d12_0001'
    assert len(ApplicationBase.metadata.tables)==3
    for t in ApplicationBase.metadata.sorted_tables:assert str(CreateTable(t).compile(dialect=dialect())).strip() in m['DDL']
    sql='\n'.join(m['DDL']);assert 'invalid publication transition' in sql and 'BEFORE UPDATE OR DELETE' in sql and 'ALTER TABLE' not in sql

def test_offline_upgrade_downgrade_refuses_history(monkeypatch):
    monkeypatch.setenv('DATABASE_URL','postgresql://offline.invalid/disposable')
    out=StringIO();config=Config('alembic.ini',output_buffer=out);command.upgrade(config,'d12_0001:d13_0001',sql=True)
    assert out.getvalue().count('CREATE TABLE')==3
    out.seek(0);out.truncate();command.downgrade(config,'d13_0001:d12_0001',sql=True)
    assert out.getvalue().index('refuses retained publication history')<out.getvalue().index('DROP TABLE')
