"""Identity-only shadow/import contracts, deliberately separate from live metadata."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints

Key = Annotated[str, StringConstraints(strip_whitespace=False, min_length=1, max_length=160)]


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ScopeIdentity(FrozenModel):
    kind: Literal["scope"] = "scope"
    id: UUID
    scope_key: Annotated[str, StringConstraints(min_length=1, max_length=100)]


class YearIdentity(FrozenModel):
    kind: Literal["year"] = "year"
    id: UUID
    scope_id: UUID
    year_key: Annotated[str, StringConstraints(min_length=1, max_length=40)]


class TermIdentity(FrozenModel):
    kind: Literal["term"] = "term"
    id: UUID
    scope_id: UUID
    year_id: UUID | None = None
    term_key: Annotated[str, StringConstraints(min_length=1, max_length=80)]
    identity_scope: Key


class FacultyCodeIdentity(FrozenModel):
    kind: Literal["faculty_code"] = "faculty_code"
    id: UUID  # existing faculty_identities.id, never a newly allocated identity
    legacy_code: Annotated[StrictInt, Field(ge=0, le=2147483647)]


class CourseIdentity(FrozenModel):
    kind: Literal["course"] = "course"
    id: UUID
    scope_id: UUID
    identity_code: Annotated[str, StringConstraints(min_length=1, max_length=64)]


class SectionIdentity(FrozenModel):
    kind: Literal["section"] = "section"
    id: UUID
    scope_id: UUID
    term_id: UUID
    identity_code: Annotated[str, StringConstraints(min_length=1, max_length=40)]


class OfferingIdentity(FrozenModel):
    kind: Literal["offering"] = "offering"
    id: UUID
    scope_id: UUID
    term_id: UUID
    course_id: UUID
    section_id: UUID
    identity_key: Key


IdentityRecord = Annotated[
    ScopeIdentity | YearIdentity | TermIdentity | FacultyCodeIdentity |
    CourseIdentity | SectionIdentity | OfferingIdentity,
    Field(discriminator="kind"),
]

UNSUPPORTED = (
    "workloads_and_release_credits", "capacity_and_enrollment", "faculty_profiles_and_qualifications",
    "eligibility_and_domains", "titles_units_components_and_templates", "rooms_and_fixed_blocks",
    "external_preassignments", "preferences", "datasets_and_run_snapshots", "GA_input_equivalence",
    "calendar_and_lifecycle_fact_comparison",
)


class IdentityProjection(FrozenModel):
    schema_version: Literal[1] = 1
    scope_id: UUID
    term_id: UUID
    records: tuple[IdentityRecord, ...]
    faculty_mapping_scope: Literal["global_legacy_bridge"] = "global_legacy_bridge"
    unsupported_fields: tuple[str, ...] = UNSUPPORTED


class SourceReference(FrozenModel):
    source_key: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.-]{1,80}$")]
    sha256: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]


class PlanItem(FrozenModel):
    classification: Literal["new", "matching", "conflicting", "unresolved", "deferred"]
    code: str
    source_key: str
    row_ordinal: int
    record_kind: str | None = None
    # No raw faculty fields, identifiers, input rows, or exception strings in reports.


class ImportPlan(FrozenModel):
    schema_version: Literal[1] = 1
    parser_version: Literal["4c2.identity-plan.v1"] = "4c2.identity-plan.v1"
    sources: tuple[SourceReference, ...]
    items: tuple[PlanItem, ...]
    supported_scope: Literal["identity_projection_only"] = "identity_projection_only"
    apply_available: Literal[False] = False

    @property
    def counts(self):
        return {key: sum(item.classification == key for item in self.items)
                for key in ("new", "matching", "conflicting", "unresolved", "deferred")}


class ProjectionComparison(FrozenModel):
    equal: bool
    missing: tuple[str, ...]
    unexpected: tuple[str, ...]
    changed: tuple[str, ...]
    unsupported_fields: tuple[str, ...] = UNSUPPORTED
