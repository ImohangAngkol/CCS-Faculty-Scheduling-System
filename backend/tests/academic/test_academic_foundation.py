"""Offline relational checks use private SQLite, NOT PostgreSQL trigger evidence."""
import importlib.util
import io
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from alembic.config import Config
from sqlalchemy import create_engine, event, insert, select, update
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateTable, CreateIndex

from academic_models import (ACADEMIC_TABLES, AcademicCourse, AcademicCourseOffering,
                             AcademicFacultyLegacyCode, AcademicScope, AcademicSection,
                             AcademicTerm, AcademicYear)
from identity_models import Base, FacultyIdentityRecord, User
from repositories.academic_repository import AcademicReadError, AcademicRepository
from services.academic_metadata_adapter import compare_projections

ROOT = Path(__file__).resolve().parents[2]


def uid(number): return UUID(int=number)


def migration():
    spec = importlib.util.spec_from_file_location("academic_revision", ROOT / "migrations/versions/4c_0001_academic_foundation.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_rows():
    return (
        (AcademicScope, dict(id=uid(1), scope_key="synthetic:ccs", institution_label="Synthetic", department_label="Synthetic")),
        (AcademicYear, dict(id=uid(2), scope_id=uid(1), year_key="synthetic-year", label="Synthetic")),
        (AcademicTerm, dict(id=uid(3), scope_id=uid(1), year_id=uid(2), term_key="synthetic-term", identity_scope="synthetic:term", label="Synthetic", timezone="Asia/Manila")),
        (AcademicCourse, dict(id=uid(4), scope_id=uid(1), identity_code="SYN101")),
        (AcademicSection, dict(id=uid(5), scope_id=uid(1), term_id=uid(3), identity_code="1A")),
        (AcademicCourseOffering, dict(id=uid(6), scope_id=uid(1), term_id=uid(3), course_id=uid(4), section_id=uid(5), identity_key="SYN101::1A")),
        (FacultyIdentityRecord, dict(id=uid(7), display_code="Synthetic Faculty", name="Synthetic Faculty")),
        (AcademicFacultyLegacyCode, dict(faculty_id=uid(7), legacy_code=17)),
    )


@pytest.fixture
def engine():
    e = create_engine("sqlite://")
    @event.listens_for(e, "connect")
    def foreign_keys(connection, record): connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(e, tables=[FacultyIdentityRecord.__table__, *ACADEMIC_TABLES])
    with e.begin() as c:
        for model, values in fixture_rows(): c.execute(insert(model), values)
    yield e
    e.dispose()


def test_exact_seven_tables_and_shared_existing_base():
    assert {table.name for table in ACADEMIC_TABLES} == {
        "academic_scopes", "academic_years", "academic_terms", "academic_faculty_legacy_codes",
        "academic_courses", "academic_sections", "academic_course_offerings"}
    assert len(Base.metadata.tables) == 10
    assert next(iter(AcademicFacultyLegacyCode.__table__.c.faculty_id.foreign_keys)).target_fullname == "faculty_identities.id"
    assert next(iter(User.__table__.c.faculty_id.foreign_keys)).target_fullname == "faculty_identities.id"


def test_migration_chain_and_frozen_ddl_match_models():
    m = migration()
    assert m.revision == "4c_0001" and m.down_revision == "4a_0001"
    script = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    assert script.get_heads() == ["d13_0001"]
    assert script.get_revision("d13_0001").down_revision == "d12_0001"
    assert script.get_revision("d12_0001").down_revision == "d11_0001"
    assert script.get_revision("d11_0001").down_revision == "d9_0001"
    assert script.get_revision("d9_0001").down_revision == "4c_0001"
    statements = []
    for table in ACADEMIC_TABLES:
        statements.append(str(CreateTable(table).compile(dialect=postgresql.dialect())).strip())
        statements.extend(str(CreateIndex(index).compile(dialect=postgresql.dialect())).strip()
                          for index in sorted(table.indexes, key=lambda i: i.name))
    def normalized(statement):
        return "\n".join(line.rstrip() for line in statement.splitlines())
    assert tuple(map(normalized, statements)) == tuple(map(normalized, m.TABLE_DDL))


@pytest.mark.parametrize("direction", ["upgrade", "downgrade"])
def test_offline_migration_rendering_without_connection(direction):
    output = io.StringIO()
    context = MigrationContext.configure(url="postgresql://", opts={"as_sql": True, "output_buffer": output})
    with Operations.context(context): getattr(migration(), direction)()
    sql = output.getvalue()
    if direction == "upgrade":
        assert sql.count("CREATE TABLE ") == 7
        assert "pg_try_advisory_xact_lock" in sql and "AFTER INSERT OR UPDATE" in sql
        assert "READ COMMITTED" in sql and "VOLATILE" in sql
        assert "CREATE TABLE users" not in sql and "ALTER TABLE users" not in sql
    else:
        assert sql.count("DROP TABLE public.academic_") == 7
        assert sql.index("ACCESS EXCLUSIVE") < sql.index("IF EXISTS") < sql.index("DROP TABLE")
        assert "DROP TABLE users" not in sql


@pytest.mark.parametrize("model,values", [
    (AcademicScope, dict(id=uid(11), scope_key="synthetic:ccs", institution_label="S", department_label="S")),
    (AcademicYear, dict(id=uid(12), scope_id=uid(1), year_key="synthetic-year", label="S")),
    (AcademicTerm, dict(id=uid(13), scope_id=uid(1), term_key="synthetic-term", identity_scope="other", label="S", timezone="Asia/Manila")),
    (AcademicTerm, dict(id=uid(13), scope_id=uid(1), term_key="other", identity_scope="synthetic:term", label="S", timezone="Asia/Manila")),
    (AcademicCourse, dict(id=uid(14), scope_id=uid(1), identity_code="SYN101")),
    (AcademicSection, dict(id=uid(15), scope_id=uid(1), term_id=uid(3), identity_code="1A")),
    (AcademicCourseOffering, dict(id=uid(16), scope_id=uid(1), term_id=uid(3), course_id=uid(4), section_id=uid(5), identity_key="OTHER")),
    (AcademicFacultyLegacyCode, dict(faculty_id=uid(99), legacy_code=18)),
])
def test_duplicate_or_missing_parent_rejected(engine, model, values):
    with pytest.raises(IntegrityError), engine.begin() as c: c.execute(insert(model), values)


@pytest.mark.parametrize("changes", [
    {"start_date": date(2026, 1, 1)},
    {"calendar_status": "confirmed"}, {"calendar_status": "invented"}, {"row_version": 0},
    {"archived_at": datetime(2026, 1, 1)},
])
def test_scalar_calendar_and_archive_constraints(engine, changes):
    with pytest.raises(IntegrityError), engine.begin() as c:
        c.execute(update(AcademicYear).where(AcademicYear.id == uid(2)).values(**changes))


def test_cross_scope_and_cross_term_composite_fks(engine):
    with engine.begin() as c:
        c.execute(insert(AcademicScope), dict(id=uid(10), scope_key="other", institution_label="S", department_label="S"))
        c.execute(insert(AcademicTerm), dict(id=uid(30), scope_id=uid(1), term_key="other", identity_scope="other", label="S", timezone="Asia/Manila"))
    with pytest.raises(IntegrityError), engine.begin() as c:
        c.execute(insert(AcademicTerm), dict(id=uid(31), scope_id=uid(10), year_id=uid(2), term_key="bad", identity_scope="bad", label="S", timezone="Asia/Manila"))
    with pytest.raises(IntegrityError), engine.begin() as c:
        c.execute(insert(AcademicSection), dict(id=uid(32), scope_id=uid(10), term_id=uid(3), identity_code="2A"))
    with pytest.raises(IntegrityError), engine.begin() as c:
        c.execute(insert(AcademicCourseOffering), dict(id=uid(33), scope_id=uid(1), term_id=uid(30), section_id=uid(5), course_id=uid(4), identity_key="SYN101::1A"))


def test_archive_does_not_release_reserved_key(engine):
    from datetime import datetime
    with engine.begin() as c:
        c.execute(update(AcademicCourse).where(AcademicCourse.id == uid(4)).values(is_active=False, archived_at=datetime(2026, 1, 1)))
    with pytest.raises(IntegrityError), engine.begin() as c:
        c.execute(insert(AcademicCourse), dict(id=uid(40), scope_id=uid(1), identity_code="SYN101"))


def test_transaction_rollback_preserves_existing_rows(engine):
    with pytest.raises(IntegrityError), engine.begin() as c:
        c.execute(insert(AcademicCourse), dict(id=uid(40), scope_id=uid(1), identity_code="SYN102"))
        c.execute(insert(AcademicSection), dict(id=uid(41), scope_id=uid(99), term_id=uid(3), identity_code="2A"))
    with engine.connect() as c:
        assert c.execute(select(AcademicCourse.id).where(AcademicCourse.id == uid(40))).first() is None
        assert c.execute(select(AcademicCourse.id)).all() == [(uid(4),)]


def test_repository_requires_read_only_explicit_context(engine):
    with engine.connect() as c:
        repository = AcademicRepository(c)
        with pytest.raises(AcademicReadError): repository.read_projection(uid(1), uid(3))
        with c.begin():
            with pytest.raises(AcademicReadError): repository.read_projection(uid(1), uid(3))


def test_shadow_identity_projection_and_missing_term(engine):
    with engine.connect() as c:
        c.exec_driver_sql("PRAGMA query_only=ON")
        projection = AcademicRepository(c).read_projection(uid(1), uid(3))
        assert len(projection.records) == 7
        assert projection.faculty_mapping_scope == "global_legacy_bridge"
        assert compare_projections(projection, projection).equal
        with pytest.raises(AcademicReadError, match="no fallback"):
            AcademicRepository(c).read_projection(uid(1), uid(99))
        with pytest.raises(Exception): c.execute(insert(AcademicCourse), dict(id=uid(99), scope_id=uid(1), identity_code="SYN999"))


def test_repository_unavailability_is_sanitized(engine, monkeypatch):
    from sqlalchemy.exc import OperationalError
    with engine.connect() as c:
        c.exec_driver_sql("PRAGMA query_only=ON")
        def unavailable(*args, **kwargs):
            raise OperationalError("PRIVATE-SENTINEL", {}, Exception("PRIVATE-SENTINEL"))
        monkeypatch.setattr(c, "execute", unavailable)
        with pytest.raises(AcademicReadError) as error:
            AcademicRepository(c).read_projection(uid(1), uid(3))
        assert "PRIVATE-SENTINEL" not in str(error.value)


def test_alembic_environment_renders_full_chain_without_connecting(monkeypatch):
    from alembic import command
    output = io.StringIO()
    config = Config(str(ROOT / "alembic.ini"), output_buffer=output)
    monkeypatch.setenv("DATABASE_URL", "postgresql://offline-render-only/unused")
    command.upgrade(config, "4c_0001", sql=True)
    sql = output.getvalue()
    assert sql.count("CREATE TABLE academic_") == 7
    assert "CREATE TABLE faculty_identities" in sql and "4c_0001" in sql


def test_alembic_injected_connection_does_not_read_url_or_create_engine(monkeypatch):
    import runpy
    from contextlib import nullcontext
    from types import SimpleNamespace
    from alembic import context
    import sqlalchemy
    connection, seen = object(), []
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(context, "config", SimpleNamespace(attributes={"connection": connection}), raising=False)
    monkeypatch.setattr(context, "is_offline_mode", lambda: False)
    monkeypatch.setattr(context, "configure", lambda **kwargs: seen.append(kwargs))
    monkeypatch.setattr(context, "begin_transaction", nullcontext)
    monkeypatch.setattr(context, "run_migrations", lambda: None)
    def denied(*args, **kwargs): raise AssertionError("No engine creation permitted")
    monkeypatch.setattr(sqlalchemy, "create_engine", denied)
    runpy.run_path(str(ROOT / "migrations/env.py"))
    assert seen[0]["connection"] is connection
    from confirmation_models import ConfirmationBase
    from adjustment_models import AdjustmentBase
    from chair_models import ChairBase
    from application_models import ApplicationBase
    assert seen[0]["target_metadata"] == [Base.metadata, ConfirmationBase.metadata, AdjustmentBase.metadata, ChairBase.metadata, ApplicationBase.metadata]
