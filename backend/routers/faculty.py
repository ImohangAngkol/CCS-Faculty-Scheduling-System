from fastapi import APIRouter, HTTPException

from genetic_algorithm.utils.Functions import (
    list_faculty,
    dct_fac_name,
)

router = APIRouter(
    prefix="/api/faculty",
    tags=["Faculty"]
)


@router.get("/")
def get_all_faculty():

    faculty_data = []

    for faculty in list_faculty:

        faculty_code = int(
            faculty.code
        )

        faculty_data.append(
            {
                "faculty_code": faculty_code,

                "name": dct_fac_name.get(
                    faculty_code,
                    f"Faculty {faculty_code}"
                ),

                "seniority_level":
                    faculty.seniority_level,

                "admin_load":
                    faculty.admin_load,

                "research_load":
                    faculty.research_load,

                "extension_load":
                    faculty.extension_load,

                "current_teaching_load":
                    faculty.current_teaching_load,
            }
        )

    return {
        "message":
            "Faculty retrieved successfully.",

        "data":
            faculty_data,
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