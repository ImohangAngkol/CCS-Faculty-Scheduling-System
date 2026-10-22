"""D7 claims and assessments; client data cannot declare authoritative verification."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from schemas.external_schedule import ReviewRequest, ReviewProjection, ReviewHandoff


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class MeetingProposal(Strict):
    days: list[str] = Field(max_length=7)
    start: str = Field(max_length=20)
    end: str = Field(max_length=20)
    reason: str = Field(max_length=500)
    evidence_reference: str = Field(max_length=250)


class RowCompletion(Strict):
    source_row: int = Field(gt=0)
    title: str = Field(default="", max_length=200)
    component: Literal["unknown", "lecture", "laboratory", "external_meeting"] = "unknown"
    section_ids: list[str] = Field(default_factory=list, max_length=12)
    shared: Literal["unknown", "single_section", "shared"] = "unknown"
    room_applicability: Literal["unknown", "applicable", "not_applicable"] = "unknown"
    instructor_applicability: Literal["unknown", "applicable", "not_applicable"] = "unknown"
    evidence_reference: str = Field(default="", max_length=250)
    proposed_meeting: MeetingProposal | None = None


class CompletionMetadata(Strict):
    supplier: str = Field(default="", max_length=120)
    source_reference: str = Field(default="", max_length=250)
    source_revision: str = Field(default="", max_length=120)
    evidence_reference: str = Field(default="", max_length=250)
    academic_year: str = Field(default="", max_length=40)
    term: str = Field(default="", max_length=120)
    effective_start: str = Field(default="", max_length=10)
    effective_end: str = Field(default="", max_length=10)
    timezone: str = Field(default="", max_length=80)
    recurrence: Literal["unknown", "weekly", "unsupported"] = "unknown"
    exceptions: Literal["unknown", "none_reported", "listed_unsupported"] = "unknown"
    exception_notes: str = Field(default="", max_length=1000)
    rows: list[RowCompletion] = Field(default_factory=list, max_length=200)


class AssessmentRequest(ReviewRequest):
    metadata: CompletionMetadata


class AssessedHandoffRequest(AssessmentRequest):
    assessment_receipt: str = Field(min_length=1, max_length=4000)


class HandoffRequest(ReviewRequest):
    metadata: CompletionMetadata | None = None
    assessment_receipt: str | None = Field(default=None, min_length=1, max_length=4000)


class ReadinessFinding(Strict):
    code: str
    severity: Literal["blocker", "warning"]
    field: str
    source_row: int | None = None
    related_rows: list[int] = Field(default_factory=list)
    explanation: str
    action: str


READINESS_LABEL = "CONFIRMATION-READINESS REVIEW ONLY — NOT CONFIRMED OR ACTIVE IN GA"


class ReadinessAssessment(BaseModel):
    policy_version: Literal["d7.1"] = "d7.1"
    label: Literal["CONFIRMATION-READINESS REVIEW ONLY — NOT CONFIRMED OR ACTIVE IN GA"] = READINESS_LABEL
    status: Literal["READY", "BLOCKED"]
    approved: Literal[False] = False
    activated: Literal[False] = False
    persisted: Literal[False] = False
    metadata_origin: Literal["administrator_provided"] = "administrator_provided"
    verification_status: Literal["unavailable", "requires_verification", "verified_for_readiness"]
    verification_reference: str | None = None
    authority_policy_version: str | None = None
    metadata: CompletionMetadata
    source_fingerprint: str
    input_fingerprint: str
    assessment_fingerprint: str
    reference_digest: str
    blocker_count: int
    warning_count: int
    findings: list[ReadinessFinding]
    effective_review: ReviewProjection
    original_row_count: int
    assessed_at: str
    expires_at: str
    assessment_receipt: str | None = None


class ReadinessHandoff(ReviewHandoff):
    readiness: ReadinessAssessment
