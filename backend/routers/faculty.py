from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/api/faculty",
    tags=["Faculty"]
)


@router.get("/")
def get_all_faculty():
    """
    Return all faculty members.

    Database integration will be added later.
    """
    return {
        "message": "Faculty retrieved successfully.",
        "data": []
    }


@router.get("/{faculty_id}")
def get_faculty(faculty_id: int):
    """
    Return one faculty member.

    Database integration will be added later.
    """

    # No database yet, so there is currently
    # no faculty record to retrieve.
    raise HTTPException(
        status_code=404,
        detail=f"Faculty with ID {faculty_id} was not found."
    )