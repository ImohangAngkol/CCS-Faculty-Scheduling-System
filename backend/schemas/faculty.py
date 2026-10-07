"""Public faculty metadata; numeric codes are legacy compatibility values."""

from typing import Literal

from pydantic import BaseModel

from schemas.subject import SubjectMetadata


class FacultyMetadata(BaseModel):
    faculty_id: str
    faculty_code: int
    display_code: str
    name: str
    instructor_type: Literal["optimization_faculty"] = "optimization_faculty"
    seniority_level: int
    admin_load: int
    research_load: int
    extension_load: int
    current_teaching_load: int
    required_teaching_load: int
    absolute_max_teaching_load: int
    specializations: list[str]
    eligible_subject_codes: list[str]


class FacultyListResponse(BaseModel):
    message: str
    data: list[FacultyMetadata]


class FacultyDetailResponse(BaseModel):
    message: str
    data: FacultyMetadata


class FacultySubjectsResponse(BaseModel):
    message: str
    faculty: FacultyMetadata
    eligible_only: bool
    data: list[SubjectMetadata]
