"""Course, offering and meeting requirements, independent of GA run state."""

from typing import Literal

from pydantic import BaseModel, Field


class MeetingPatternMetadata(BaseModel):
    meetings_per_week: int
    duration_minutes: int
    continuous: bool = True
    day_combinations: list[list[str]]


class SubjectComponentMetadata(BaseModel):
    type: Literal["Lecture", "Laboratory"]
    weekly_hours: float
    metadata_status: Literal["supported", "unsupported"]
    # Null for multiple alternatives or an unknown backend meeting pattern.
    duration_minutes: int | None
    meetings_per_week: int | None
    continuous: bool | None
    fixed_duration: bool
    meeting_patterns: list[MeetingPatternMetadata]


class EligibilityRecordMetadata(BaseModel):
    status: str
    basis: str | None
    source: str | None
    notes: str | None


class FacultyEligibilityMetadata(BaseModel):
    explicitly_eligible: bool
    authority: Literal["faculty_subject_eligibility.csv"] = "faculty_subject_eligibility.csv"
    records: list[EligibilityRecordMetadata]


class PreassignedInstructorMetadata(BaseModel):
    instructor_id: str
    display_name: str
    instructor_type: Literal["preassigned_external"] = "preassigned_external"
    locked_room: str


class OfferedSubjectMetadata(BaseModel):
    offering_id: str
    offering_key: str
    offering_scope: str
    course_id: str
    subject_code: str
    subject_title: str
    section_id: str
    section: str
    year_level: int
    units: float
    lecture_hours: float
    laboratory_hours: float
    prefix: str
    category: Literal["CCC", "ITD", "ITN", "ITE", "ISY", "OTHER"]
    primary_domain: str | None
    domains: list[str]
    components: list[SubjectComponentMetadata]
    is_preassigned: bool
    assignment_type: Literal["ga_managed", "preassigned_external"]
    preassigned_instructor: PreassignedInstructorMetadata | None
    can_be_assigned: bool | None = None


class SubjectMetadata(BaseModel):
    course_id: str
    subject_code: str
    subject_title: str
    units: float
    lecture_hours: float
    laboratory_hours: float
    prefix: str
    category: Literal["CCC", "ITD", "ITN", "ITE", "ISY", "OTHER"]
    primary_domain: str | None
    domains: list[str]
    components: list[SubjectComponentMetadata]
    is_preassigned: bool
    preassignment_status: Literal["none", "some", "all"]
    offerings: list[OfferedSubjectMetadata]
    eligibility: FacultyEligibilityMetadata | None = None


class AvailableSubjectsResponse(BaseModel):
    message: str
    categories: list[str] = Field(default_factory=lambda: ["ALL", "CCC", "ITD", "ITN", "ITE", "ISY", "OTHER"])
    data: list[SubjectMetadata]
