from fastapi import APIRouter

router = APIRouter(
    prefix="/api/faculty",
    tags=["Faculty"],
)


@router.get("/")
def get_faculty():
    return {
        "message": "Faculty endpoint is working",
        "data": []
    }


@router.get("/{faculty_id}")
def get_faculty_by_id(faculty_id: int):
    return {
        "message": "Faculty endpoint is working",
        "faculty_id": faculty_id
    }