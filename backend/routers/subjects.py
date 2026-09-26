from fastapi import APIRouter

from genetic_algorithm.utils.Functions import list_subjects


router = APIRouter(
    prefix="/api/subjects",
    tags=["Subjects"],
)


@router.get("/available")
def get_available_subjects():

    unique_subjects = {}

    for subject in list_subjects:

        code = str(
            getattr(
                subject,
                "number",
                ""
            )
        ).strip().upper()

        title = str(
            getattr(
                subject,
                "title",
                ""
            )
            or ""
        ).strip()

        if not code:
            continue

        if code not in unique_subjects:

            unique_subjects[code] = {
                "subject_code": code,
                "subject_title": title,
            }

    subjects = sorted(
        unique_subjects.values(),
        key=lambda item:
            item["subject_code"]
    )

    return {
        "message":
            "Available subjects retrieved successfully.",

        "data":
            subjects,
    }