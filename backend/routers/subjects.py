from fastapi import APIRouter

from schemas.subject import AvailableSubjectsResponse
from services.metadata_service import list_subject_metadata


router = APIRouter(
    prefix="/api/subjects",
    tags=["Subjects"],
)


@router.get("/available", response_model=AvailableSubjectsResponse)
def get_available_subjects():
    return AvailableSubjectsResponse(
        message="Available subjects retrieved successfully.",
        data=list_subject_metadata(),
    )
