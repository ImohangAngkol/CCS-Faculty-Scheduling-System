"""Faculty-only schedule projection; no administrator result/report fields."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FacultyAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    subject: str
    title: str | None
    section: str
    type: Literal["Lecture", "Laboratory"]
    day: str
    start: str
    end: str
    room: str | None


class FacultyScheduleSource(BaseModel):
    kind: Literal["latest_completed_ga_result"] = "latest_completed_ga_result"
    label: Literal["GA-generated proposal"] = "GA-generated proposal"
    compatibility: Literal["checked_against_loaded_inputs", "not_available"]
    # Legacy latest results do not persist the complete run input fingerprint.
    freshness: Literal["not_recorded"] = "not_recorded"
    saved_at: datetime | None = None


class MyScheduleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    availability: Literal["available", "empty", "missing"]
    faculty_id: UUID
    faculty_code: int = Field(ge=0)
    source: FacultyScheduleSource
    assignments: list[FacultyAssignment]


class PublishedFacultySource(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind: Literal['published_schedule']
    label: Literal['Published schedule with authorized post-GA changes','Verified published source']
    version_id: UUID | None
    sequence: int=Field(ge=1)
    revision: str
    academic_year: str
    term: str
    post_ga_changes: bool
    constraint_status: Literal['NOT_RECHECKED_READ_ONLY']


class PublishedFacultyResponse(BaseModel):
    model_config=ConfigDict(extra='forbid')
    schema_version: Literal[2]=2
    availability: Literal['available','empty']
    faculty_id: UUID
    faculty_code: int=Field(ge=0)
    source: PublishedFacultySource
    assignments: list[FacultyAssignment]
