"""Prepared live tests. DEFAULT SKIP: no connection without separate approval.

Only the exact fresh Phase 4C target is accepted. Schema is retained after tests;
synthetic per-test data is rolled back. No reset/drop of another database exists.
"""
import os
from datetime import date, datetime, timezone

import pytest
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, insert, inspect, select, text, update
from sqlalchemy.exc import DBAPIError

from academic_models import (ACADEMIC_TABLES, AcademicCourse, AcademicCourseOffering,
                             AcademicScope, AcademicSection, AcademicTerm, AcademicYear)
from repositories.academic_repository import AcademicRepository
from tests.academic.postgresql_safety import (APPROVAL, designated_url,
                                            inspect_empty_test_database)
from tests.academic.test_academic_foundation import ROOT, fixture_rows, migration, uid

pytestmark = pytest.mark.skipif(
    os.environ.get("PHASE4C_POSTGRESQL_APPROVAL") != APPROVAL,
    reason="Separate explicit approval and fresh exact-gated Phase 4C PostgreSQL target required",
)


@pytest.fixture(scope="module")
def pg_engine():
    # URL parse precedes engine construction; SELECT-only preflight precedes DDL.
    url = designated_url()
    inspect_empty_test_database(allow_connect=True)
    engine = create_engine(url, hide_parameters=True, connect_args={
        "connect_timeout": 5, "options": "-c statement_timeout=5000 -c lock_timeout=1000",
    })
    try:
        with engine.begin() as c:
            config = Config(str(ROOT / "alembic.ini"))
            config.attributes["connection"] = c
            command.upgrade(config, "4c_0001")
        yield engine
    finally:
        engine.dispose()  # Retain the database/schema; no automatic cleanup DDL.


@pytest.fixture
def pg_rows(pg_engine):
    with pg_engine.connect() as c:
        transaction = c.begin()
        try:
            for model, values in fixture_rows(): c.execute(insert(model), values)
            yield c
        finally:
            transaction.rollback()


def test_online_revision_and_exact_inventory(pg_engine):
    with pg_engine.connect() as c:
        assert c.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "4c_0001"
        assert set(inspect(c).get_table_names()) == {"faculty_identities", "users", "login_sessions", "alembic_version", *(t.name for t in ACADEMIC_TABLES)}
        assert inspect(c).get_foreign_keys("users")[0]["referred_table"] == "faculty_identities"


@pytest.mark.parametrize("model,changes", [
    (AcademicScope, {"scope_key": "changed", "row_version": 2}),
    (AcademicCourse, {"identity_code": "CHANGED", "row_version": 2}),
    (AcademicSection, {"term_id": uid(90), "row_version": 2}),
    (AcademicCourseOffering, {"identity_key": "CHANGED", "row_version": 2}),
    (AcademicYear, {"label": "changed"}),  # missing next revision
])
def test_direct_identity_and_revision_mutations_rejected(pg_rows, model, changes):
    with pytest.raises(DBAPIError):
        with pg_rows.begin_nested(): pg_rows.execute(update(model).values(**changes))


def test_calendar_containment_and_year_shrink(pg_rows):
    pg_rows.execute(update(AcademicYear).values(start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), calendar_status="confirmed", row_version=2))
    pg_rows.execute(update(AcademicTerm).values(start_date=date(2026, 2, 1), end_date=date(2026, 6, 30), calendar_status="confirmed", kind="first", ordinal=1, row_version=2))
    with pytest.raises(DBAPIError), pg_rows.begin_nested():
        pg_rows.execute(update(AcademicYear).values(end_date=date(2026, 5, 1), row_version=3))
    with pytest.raises(DBAPIError), pg_rows.begin_nested():
        pg_rows.execute(update(AcademicTerm).values(end_date=date(2027, 1, 1), row_version=3))


def test_timezone_archive_and_delete_guards(pg_rows):
    with pytest.raises(DBAPIError), pg_rows.begin_nested():
        pg_rows.execute(update(AcademicTerm).values(timezone="Invalid/Synthetic", row_version=2))
    pg_rows.execute(update(AcademicCourse).values(is_active=False, archived_at=datetime.now(timezone.utc), row_version=2))
    with pytest.raises(DBAPIError), pg_rows.begin_nested():
        pg_rows.execute(update(AcademicCourse).values(is_active=True, archived_at=None, row_version=3))
    with pytest.raises(DBAPIError), pg_rows.begin_nested():
        pg_rows.execute(text("DELETE FROM academic_courses"))
    with pytest.raises(DBAPIError), pg_rows.begin_nested():
        pg_rows.execute(text("TRUNCATE academic_faculty_legacy_codes"))


def test_cross_term_fk_and_offering_key(pg_rows):
    pg_rows.execute(insert(AcademicTerm), dict(id=uid(30), scope_id=uid(1), term_key="other", identity_scope="other", label="Synthetic", timezone="Asia/Manila"))
    with pytest.raises(DBAPIError), pg_rows.begin_nested():
        pg_rows.execute(insert(AcademicCourseOffering), dict(id=uid(31), scope_id=uid(1), term_id=uid(30), course_id=uid(4), section_id=uid(5), identity_key="SYN101::1A"))
    with pytest.raises(DBAPIError), pg_rows.begin_nested():
        pg_rows.execute(insert(AcademicCourseOffering), dict(id=uid(32), scope_id=uid(1), term_id=uid(3), course_id=uid(4), section_id=uid(5), identity_key="WRONG::1A"))


def test_populated_downgrade_refuses_without_losing_rows(pg_rows):
    with pytest.raises(DBAPIError), pg_rows.begin_nested():
        with Operations.context(MigrationContext.configure(pg_rows)): migration().downgrade()
    assert pg_rows.execute(select(AcademicCourse.id)).scalar_one() == uid(4)


def test_failed_upgrade_rolls_back_all_ddl(pg_engine):
    # Within a rollback-only test transaction, remove EMPTY academic tables,
    # inject a failure after rebuilding them, then verify transactional restoration.
    with pg_engine.connect() as c:
        outer = c.begin()
        try:
            with Operations.context(MigrationContext.configure(c)): migration().downgrade()
            with pytest.raises(RuntimeError), c.begin_nested():
                with Operations.context(MigrationContext.configure(c)): migration().upgrade()
                raise RuntimeError("Synthetic failure before transaction completion")
            assert not any(name.startswith("academic_") for name in inspect(c).get_table_names())
        finally:
            outer.rollback()
    with pg_engine.connect() as c:
        assert all(t.name in inspect(c).get_table_names() for t in ACADEMIC_TABLES)


def test_concurrent_writer_rejected_then_retry_after_rollback(pg_engine):
    with pg_engine.connect() as first, pg_engine.connect() as second:
        one, two = first.begin(), second.begin()
        try:
            first.execute(insert(AcademicScope), dict(id=uid(91), scope_key="synthetic:race", institution_label="S", department_label="S"))
            with pytest.raises(DBAPIError) as error:
                second.execute(insert(AcademicScope), dict(id=uid(92), scope_key="synthetic:race", institution_label="S", department_label="S"))
            assert error.value.orig.pgcode == "55P03"
        finally:
            two.rollback(); one.rollback()
        with second.begin():
            second.execute(insert(AcademicScope), dict(id=uid(92), scope_key="synthetic:race", institution_label="S", department_label="S"))
            second.rollback()  # No persistent synthetic rows.


def test_higher_isolation_writes_rejected(pg_engine):
    with pg_engine.connect().execution_options(isolation_level="REPEATABLE READ") as c:
        with pytest.raises(DBAPIError), c.begin():
            c.execute(insert(AcademicScope), dict(id=uid(93), scope_key="synthetic:rr", institution_label="S", department_label="S"))


def test_read_only_snapshot_and_no_default_term(pg_engine):
    with pg_engine.connect().execution_options(isolation_level="REPEATABLE READ") as c:
        with c.begin():
            c.execute(text("SET TRANSACTION READ ONLY"))
            from repositories.academic_repository import AcademicReadError
            with pytest.raises(AcademicReadError, match="no fallback"):
                AcademicRepository(c).read_projection(uid(1), uid(3))


def test_empty_downgrade_upgrade_roundtrip_keeps_identity_revision(pg_engine):
    with pg_engine.connect() as c:
        transaction = c.begin()
        try:
            config = Config(str(ROOT / "alembic.ini"))
            config.attributes["connection"] = c
            command.downgrade(config, "4a_0001")
            assert c.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "4a_0001"
            assert not any(t.startswith("academic_") for t in inspect(c).get_table_names())
            command.upgrade(config, "4c_0001")
            assert len([t for t in inspect(c).get_table_names() if t.startswith("academic_")]) == 7
        finally:
            transaction.rollback()


def test_calendar_writer_race_is_fail_closed(pg_engine):
    with pg_engine.connect() as first, pg_engine.connect() as second:
        a, b = first.begin(), second.begin()
        try:
            for model, values in fixture_rows(): first.execute(insert(model), values)
            first.execute(update(AcademicYear).values(start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), calendar_status="confirmed", row_version=2))
            first.execute(update(AcademicTerm).values(start_date=date(2026, 2, 1), end_date=date(2026, 6, 30), calendar_status="confirmed", kind="first", ordinal=1, row_version=2))
            # BEFORE STATEMENT gate fires even though this snapshot cannot yet see
            # the other transaction's year. No concurrent shrink can bypass it.
            with pytest.raises(DBAPIError) as error:
                second.execute(update(AcademicYear).where(AcademicYear.id == uid(2)).values(end_date=date(2026, 5, 1), row_version=3))
            assert error.value.orig.pgcode == "55P03"
        finally:
            b.rollback(); a.rollback()


def test_locked_parent_rejects_even_inactive_new_child(pg_rows):
    pg_rows.execute(update(AcademicTerm).values(lifecycle="locked", row_version=2))
    with pytest.raises(DBAPIError), pg_rows.begin_nested():
        pg_rows.execute(insert(AcademicSection), dict(id=uid(50), scope_id=uid(1), term_id=uid(3), identity_code="2A", is_active=False))
    # Closing an existing child retains it; no cascading delete or renumbering.
    pg_rows.execute(update(AcademicSection).values(is_active=False, row_version=2))
    assert pg_rows.execute(select(AcademicSection.id)).scalar_one() == uid(5)
