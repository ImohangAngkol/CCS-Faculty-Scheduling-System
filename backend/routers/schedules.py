"""Authenticated own-assignment view; no faculty selector or admin result API."""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from identity_models import FacultyIdentityRecord
from schemas.schedule import MyScheduleResponse,PublishedFacultyResponse
from database import get_identity_db
from services import auth_service as auth, identity_service
from services.schedule_service import own_schedule, problem

router = APIRouter(prefix="/api/schedules", tags=["Faculty Schedules"])


def bound_faculty(account=Depends(auth.authenticated_session),
                  db=Depends(auth.authenticated_db, scope="function")):
    user, _session = account
    if user.role != "faculty":
        raise problem(403, "SCHEDULE_FACULTY_REQUIRED", "This timetable is available only to the signed-in faculty account.")
    try:
        faculty_id = UUID(str(user.faculty_id))
        if db.get(FacultyIdentityRecord, faculty_id) is None:
            raise ValueError("Missing registered binding")
        identity = identity_service.resolve_faculty_identity(str(faculty_id))
        from services.metadata_service import resolve_normal_faculty
        member = resolve_normal_faculty(str(faculty_id))
        if str(member.stable_id) != str(faculty_id) or member.code != identity.faculty_code:
            raise ValueError("Inconsistent registered binding")
    except (ValueError, AttributeError, TypeError):
        raise problem(403, "SCHEDULE_BINDING_INVALID", "Your faculty binding could not be verified. Contact an administrator; no faculty record has been selected.") from None
    return identity


@router.get("/me", response_model=MyScheduleResponse|PublishedFacultyResponse)
def my_schedule(request: Request, identity=Depends(bound_faculty), db=Depends(get_identity_db)):
    if request.query_params:
        raise problem(400, "SCHEDULE_SELECTOR_NOT_ALLOWED", "This endpoint accepts no faculty selectors or query parameters. It shows only the signed-in faculty schedule.")
    from services.published_schedule_views import own
    return own(db,identity) or own_schedule(identity)
