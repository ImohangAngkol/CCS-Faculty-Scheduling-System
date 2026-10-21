"""Preview DTOs only. No durable commitment or confirmation state."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ExternalRow(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    supplier: str = Field(default="", max_length=120)
    subject_code: str = Field(default="", max_length=40)
    title: str = Field(default="", max_length=200)
    sections: list[str] = Field(default_factory=list, max_length=12)
    academic_term: str = Field(default="", max_length=120)
    days: list[str] = Field(default_factory=list, max_length=7)
    start: str = Field(default="", max_length=20)
    end: str = Field(default="", max_length=20)
    room: str = Field(default="", max_length=120)
    instructor: str = Field(default="", max_length=160)
    source_reference: str = Field(default="", max_length=250)
    notes: str = Field(default="", max_length=1000)
    status: Literal["draft", "tentative"] = "draft"


class ManualPreview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    rows: list[ExternalRow] = Field(min_length=1, max_length=200)


class Discrepancy(BaseModel):
    code: str
    severity: Literal["error", "review"]
    field: str
    message: str
    related_rows: list[int] = Field(default_factory=list)


class ReferenceMatch(BaseModel):
    value: str
    id: str | None
    state: Literal["resolved", "unresolved", "not_supplied"]


class ReviewedRow(BaseModel):
    source_row: int
    input: ExternalRow
    status: Literal["draft", "tentative", "needs_review", "invalid"]
    sections: list[ReferenceMatch]
    room: ReferenceMatch
    instructor: ReferenceMatch
    discrepancies: list[Discrepancy]


class PreviewResult(BaseModel):
    schema_version: Literal[1] = 1
    preview_only: Literal[True] = True
    persisted: Literal[False] = False
    activated: Literal[False] = False
    source_kind: Literal["manual", "csv", "xlsx"]
    source_name: str | None = None
    source_sha256: str | None = None
    parser_version: Literal["d3.1"] = "d3.1"
    term_verification: Literal["not_configured"] = "not_configured"
    rows: list[ReviewedRow]
    review_token: str | None = None


class SectionMapping(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    reference_index: int = Field(ge=0, lt=12)
    target_id: str = Field(min_length=1, max_length=120)


class RowMapping(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source_row: int = Field(gt=0)
    sections: list[SectionMapping] = Field(default_factory=list, max_length=12)
    room_id: str | None = Field(default=None, min_length=1, max_length=120)
    instructor_id: str | None = Field(default=None, min_length=1, max_length=120)


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    review_token: str = Field(min_length=1, max_length=1600000)
    mappings: list[RowMapping] = Field(default_factory=list, max_length=200)


class ResourceResolution(BaseModel):
    original: str
    id: str | None
    label: str | None
    state: Literal["resolved", "unresolved", "ambiguous", "unsupported", "missing_optional"]
    method: Literal["recognized", "explicit", "none"] = "none"
    candidate_ids: list[str] = Field(default_factory=list)


class ReviewMeeting(BaseModel):
    source_row: int
    original: ExternalRow
    status: Literal["draft", "tentative", "needs_review", "invalid"]
    sections: list[ResourceResolution]
    room: ResourceResolution
    instructor: ResourceResolution
    discrepancies: list[Discrepancy]
    calendar_supported: bool


class ReviewProjection(BaseModel):
    schema_version: Literal[2] = 2
    preview_only: Literal[True] = True
    persisted: Literal[False] = False
    activated: Literal[False] = False
    source_kind: Literal["manual", "csv", "xlsx"]
    source_name: str | None
    source_sha256: str | None
    source_parser_version: Literal["d3.1"] = "d3.1"
    projection_version: Literal["d4.1"] = "d4.1"
    term_verification: Literal["not_configured"] = "not_configured"
    reference_digest: str
    rows: list[ReviewMeeting]
