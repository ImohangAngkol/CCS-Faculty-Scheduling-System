"""Seven-table academic identity foundation; no engine, files or GA imports.

PostgreSQL mutation/calendar guards are installed by revision 4c_0001.
Creating this metadata directly is NOT equivalent to applying that migration.
"""
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (BigInteger, Boolean, CheckConstraint, Date, DateTime,
                        ForeignKey, ForeignKeyConstraint, Index, Integer,
                        SmallInteger, String, Text, UniqueConstraint, Uuid, func, true)
from sqlalchemy.orm import Mapped, mapped_column

from identity_models import Base


def administrative_checks(prefix):
    return (
        CheckConstraint("row_version > 0", name=f"ck_{prefix}_version"),
        CheckConstraint("archived_at IS NULL OR NOT is_active", name=f"ck_{prefix}_archive"),
    )


def calendar_checks(prefix):
    return (
        CheckConstraint("calendar_status IN ('unresolved','confirmed')", name=f"ck_{prefix}_calendar"),
        CheckConstraint("(start_date IS NULL AND end_date IS NULL) OR "
                        "(start_date IS NOT NULL AND end_date IS NOT NULL AND start_date <= end_date)",
                        name=f"ck_{prefix}_dates"),
        CheckConstraint("calendar_status <> 'confirmed' OR start_date IS NOT NULL", name=f"ck_{prefix}_confirmed"),
    )


class Administrative:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    row_version: Mapped[int] = mapped_column(BigInteger, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AcademicScope(Administrative, Base):
    __tablename__ = "academic_scopes"
    __table_args__ = (
        UniqueConstraint("scope_key", name="uq_ac_scope_key"),
        CheckConstraint("length(trim(scope_key)) > 0 AND scope_key = trim(scope_key)", name="ck_ac_scope_key"),
        *administrative_checks("ac_scope"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    scope_key: Mapped[str] = mapped_column(String(100))
    institution_label: Mapped[str] = mapped_column(Text)
    department_label: Mapped[str] = mapped_column(Text)


class AcademicYear(Administrative, Base):
    __tablename__ = "academic_years"
    __table_args__ = (
        UniqueConstraint("scope_id", "year_key", name="uq_ac_year_key"),
        UniqueConstraint("id", "scope_id", name="uq_ac_year_scope"),
        CheckConstraint("length(trim(year_key)) > 0 AND year_key = trim(year_key)", name="ck_ac_year_key"),
        *calendar_checks("ac_year"), *administrative_checks("ac_year"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    scope_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("academic_scopes.id", ondelete="RESTRICT"))
    year_key: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(100))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    calendar_status: Mapped[str] = mapped_column(String(20), server_default="unresolved")


class AcademicTerm(Administrative, Base):
    __tablename__ = "academic_terms"
    __table_args__ = (
        ForeignKeyConstraint(["year_id", "scope_id"], ["academic_years.id", "academic_years.scope_id"], ondelete="RESTRICT", name="fk_ac_term_year_scope"),
        UniqueConstraint("scope_id", "term_key", name="uq_ac_term_key"),
        UniqueConstraint("identity_scope", name="uq_ac_term_identity"),
        UniqueConstraint("year_id", "ordinal", name="uq_ac_term_ordinal"),
        UniqueConstraint("id", "scope_id", name="uq_ac_term_scope"),
        CheckConstraint("length(trim(term_key)) > 0 AND term_key = trim(term_key)", name="ck_ac_term_key"),
        CheckConstraint("length(trim(identity_scope)) > 0 AND identity_scope = trim(identity_scope)", name="ck_ac_term_identity"),
        CheckConstraint("length(trim(timezone)) > 0", name="ck_ac_term_timezone"),
        CheckConstraint("ordinal IS NULL OR ordinal > 0", name="ck_ac_term_ordinal"),
        CheckConstraint("kind IN ('legacy_unknown','first','second','midyear','other')", name="ck_ac_term_kind"),
        CheckConstraint("lifecycle IN ('draft','open','locked','archived')", name="ck_ac_term_lifecycle"),
        CheckConstraint("calendar_status <> 'confirmed' OR (year_id IS NOT NULL AND ordinal IS NOT NULL AND kind <> 'legacy_unknown')", name="ck_ac_term_confirmed_year"),
        CheckConstraint("lifecycle <> 'open' OR calendar_status = 'confirmed'", name="ck_ac_term_open"),
        CheckConstraint("(lifecycle = 'archived') = (archived_at IS NOT NULL)", name="ck_ac_term_archived"),
        *calendar_checks("ac_term"), *administrative_checks("ac_term"),
        Index("ix_ac_term_year_scope", "year_id", "scope_id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    scope_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("academic_scopes.id", ondelete="RESTRICT"))
    year_id: Mapped[UUID | None] = mapped_column(Uuid)
    term_key: Mapped[str] = mapped_column(String(80))
    identity_scope: Mapped[str] = mapped_column(String(160))
    label: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(24), server_default="legacy_unknown")
    ordinal: Mapped[int | None] = mapped_column(SmallInteger)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    timezone: Mapped[str] = mapped_column(String(64))
    calendar_status: Mapped[str] = mapped_column(String(20), server_default="unresolved")
    lifecycle: Mapped[str] = mapped_column(String(20), server_default="draft")


class AcademicFacultyLegacyCode(Base):
    __tablename__ = "academic_faculty_legacy_codes"
    __table_args__ = (
        UniqueConstraint("legacy_code", name="uq_ac_faculty_code"),
        CheckConstraint("legacy_code >= 0", name="ck_ac_faculty_code"),
    )
    faculty_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("faculty_identities.id", ondelete="RESTRICT"), primary_key=True)
    legacy_code: Mapped[int] = mapped_column(Integer)
    allocated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AcademicCourse(Administrative, Base):
    __tablename__ = "academic_courses"
    __table_args__ = (
        UniqueConstraint("scope_id", "identity_code", name="uq_ac_course_key"),
        UniqueConstraint("id", "scope_id", name="uq_ac_course_scope"),
        CheckConstraint("length(trim(identity_code)) > 0 AND identity_code = upper(trim(identity_code))", name="ck_ac_course_key"),
        CheckConstraint("catalog_status IN ('descriptor_only','verified')", name="ck_ac_course_status"),
        *administrative_checks("ac_course"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    scope_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("academic_scopes.id", ondelete="RESTRICT"))
    identity_code: Mapped[str] = mapped_column(String(64))
    catalog_status: Mapped[str] = mapped_column(String(24), server_default="descriptor_only")


class AcademicSection(Administrative, Base):
    __tablename__ = "academic_sections"
    __table_args__ = (
        ForeignKeyConstraint(["term_id", "scope_id"], ["academic_terms.id", "academic_terms.scope_id"], ondelete="RESTRICT", name="fk_ac_section_term_scope"),
        UniqueConstraint("term_id", "identity_code", name="uq_ac_section_key"),
        UniqueConstraint("id", "term_id", "scope_id", name="uq_ac_section_term_scope"),
        CheckConstraint("length(trim(identity_code)) > 0 AND identity_code = upper(trim(identity_code))", name="ck_ac_section_key"),
        *administrative_checks("ac_section"),
        Index("ix_ac_section_scope", "scope_id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    term_id: Mapped[UUID] = mapped_column(Uuid)
    scope_id: Mapped[UUID] = mapped_column(Uuid)
    identity_code: Mapped[str] = mapped_column(String(40))


class AcademicCourseOffering(Administrative, Base):
    __tablename__ = "academic_course_offerings"
    __table_args__ = (
        ForeignKeyConstraint(["term_id", "scope_id"], ["academic_terms.id", "academic_terms.scope_id"], ondelete="RESTRICT", name="fk_ac_offering_term_scope"),
        ForeignKeyConstraint(["course_id", "scope_id"], ["academic_courses.id", "academic_courses.scope_id"], ondelete="RESTRICT", name="fk_ac_offering_course_scope"),
        ForeignKeyConstraint(["section_id", "term_id", "scope_id"], ["academic_sections.id", "academic_sections.term_id", "academic_sections.scope_id"], ondelete="RESTRICT", name="fk_ac_offering_section_term_scope"),
        UniqueConstraint("term_id", "course_id", "section_id", name="uq_ac_offering_membership"),
        UniqueConstraint("term_id", "identity_key", name="uq_ac_offering_key"),
        CheckConstraint("length(trim(identity_key)) > 0 AND identity_key = upper(trim(identity_key))", name="ck_ac_offering_key"),
        *administrative_checks("ac_offering"),
        Index("ix_ac_offering_course_scope", "course_id", "scope_id"),
        Index("ix_ac_offering_section_term_scope", "section_id", "term_id", "scope_id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    term_id: Mapped[UUID] = mapped_column(Uuid)
    scope_id: Mapped[UUID] = mapped_column(Uuid)
    course_id: Mapped[UUID] = mapped_column(Uuid)
    section_id: Mapped[UUID] = mapped_column(Uuid)
    identity_key: Mapped[str] = mapped_column(String(160))


ACADEMIC_TABLES = tuple(cls.__table__ for cls in (
    AcademicScope, AcademicYear, AcademicTerm, AcademicFacultyLegacyCode,
    AcademicCourse, AcademicSection, AcademicCourseOffering,
))
