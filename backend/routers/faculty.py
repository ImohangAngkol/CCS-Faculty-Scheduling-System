from fastapi import APIRouter, HTTPException

from schemas.faculty import FacultyDetailResponse, FacultyListResponse, FacultySubjectsResponse
from services.metadata_service import (
    faculty_metadata,
    list_faculty_metadata,
    list_subject_metadata,
    resolve_normal_faculty,
)

router = APIRouter(
    prefix="/api/faculty",
    tags=["Faculty"]
)


@router.get("/", response_model=FacultyListResponse)
def get_all_faculty():
    return FacultyListResponse(
        message="Faculty retrieved successfully.", data=list_faculty_metadata(),
    )


def _resolve_faculty(faculty_id):
    try:
        return resolve_normal_faculty(faculty_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{faculty_id}", response_model=FacultyDetailResponse)
def get_faculty(faculty_id: str):
    return FacultyDetailResponse(
        message="Faculty retrieved successfully.",
        data=faculty_metadata(_resolve_faculty(faculty_id)),
    )


@router.get("/{faculty_id}/eligible-subjects", response_model=FacultySubjectsResponse)
def get_faculty_subjects(faculty_id: str, eligible_only: bool = True):
    faculty = _resolve_faculty(faculty_id)
    return FacultySubjectsResponse(
        message="Faculty subject metadata retrieved successfully.",
        faculty=faculty_metadata(faculty),
        eligible_only=eligible_only,
        data=list_subject_metadata(faculty, eligible_only=eligible_only),
    )
