"""SELECT-only academic projection from an already-owned read-only connection."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError

from academic_models import (AcademicCourse, AcademicCourseOffering, AcademicFacultyLegacyCode,
                             AcademicScope, AcademicSection, AcademicTerm, AcademicYear)
from schemas.academic import (CourseIdentity, FacultyCodeIdentity, IdentityProjection,
                             OfferingIdentity, ScopeIdentity, SectionIdentity,
                             TermIdentity, YearIdentity)


class AcademicReadError(RuntimeError):
    pass


class AcademicRepository:
    def __init__(self, connection: Connection):
        # Never create an engine, open a transaction, flush, commit or load an env URL.
        self.connection = connection

    def _check_read_only(self):
        c = self.connection
        if not c.in_transaction():
            raise AcademicReadError("An explicit read-only transaction is required.")
        if c.dialect.name == "postgresql":
            if (c.exec_driver_sql("SHOW transaction_read_only").scalar_one() != "on"
                    or c.get_isolation_level() not in {"REPEATABLE READ", "SERIALIZABLE"}):
                raise AcademicReadError("A read-only consistent snapshot is required.")
        elif c.dialect.name == "sqlite":
            if c.exec_driver_sql("PRAGMA query_only").scalar_one() != 1:
                raise AcademicReadError("SQLite offline fixtures must be query-only.")
        else:
            raise AcademicReadError("Unsupported academic read dialect.")

    def read_projection(self, scope_id: UUID, term_id: UUID) -> IdentityProjection:
        try:
            return self._read_projection(scope_id, term_id)
        except DBAPIError:
            raise AcademicReadError("Academic storage unavailable; details withheld; no fallback.") from None

    def _read_projection(self, scope_id: UUID, term_id: UUID) -> IdentityProjection:
        self._check_read_only()
        c = self.connection
        scope = c.execute(select(AcademicScope.id, AcademicScope.scope_key)
                          .where(AcademicScope.id == scope_id)).mappings().one_or_none()
        term = c.execute(select(AcademicTerm.id, AcademicTerm.scope_id, AcademicTerm.year_id,
                                AcademicTerm.term_key, AcademicTerm.identity_scope)
                         .where(AcademicTerm.id == term_id, AcademicTerm.scope_id == scope_id)).mappings().one_or_none()
        if scope is None or term is None:
            raise AcademicReadError("Requested academic scope/term was not found; no fallback.")
        records = [ScopeIdentity(**scope), TermIdentity(**term)]
        if term["year_id"] is not None:
            row = c.execute(select(AcademicYear.id, AcademicYear.scope_id, AcademicYear.year_key)
                            .where(AcademicYear.id == term["year_id"], AcademicYear.scope_id == scope_id)).mappings().one()
            records.append(YearIdentity(**row))
        specifications = (
            (FacultyCodeIdentity, select(AcademicFacultyLegacyCode.faculty_id.label("id"), AcademicFacultyLegacyCode.legacy_code)),
            (CourseIdentity, select(AcademicCourse.id, AcademicCourse.scope_id, AcademicCourse.identity_code).where(AcademicCourse.scope_id == scope_id)),
            (SectionIdentity, select(AcademicSection.id, AcademicSection.scope_id, AcademicSection.term_id, AcademicSection.identity_code).where(AcademicSection.term_id == term_id, AcademicSection.scope_id == scope_id)),
            (OfferingIdentity, select(AcademicCourseOffering.id, AcademicCourseOffering.scope_id, AcademicCourseOffering.term_id, AcademicCourseOffering.course_id, AcademicCourseOffering.section_id, AcademicCourseOffering.identity_key).where(AcademicCourseOffering.term_id == term_id, AcademicCourseOffering.scope_id == scope_id)),
        )
        for schema, query in specifications:
            records.extend(schema(**row) for row in c.execute(query).mappings())
        # Canonical comparison order only. This is NOT GA construction order.
        records.sort(key=lambda row: (row.kind, str(row.id)))
        return IdentityProjection(scope_id=scope_id, term_id=term_id, records=tuple(records))
