"""Server-verified role and stable faculty ownership boundary."""
from dataclasses import dataclass
from fastapi import Depends, HTTPException, Request
from services.metadata_service import resolve_normal_faculty
from services.auth_service import authenticated_session


@dataclass(frozen=True)
class PreferencePrincipal:
    role: str
    faculty_id: str | None = None
    user_id: str | None = None


def current_principal(account=Depends(authenticated_session)) -> PreferencePrincipal:
    user, _session = account
    return PreferencePrincipal(user.role, str(user.faculty_id) if user.faculty_id else None, str(user.id))


def require_principal(principal=Depends(current_principal)):
    if principal is None:
        raise HTTPException(401, "Sign in to continue. No changes were saved.")
    return principal


def require_admin(principal=Depends(require_principal)):
    if principal.role != "admin":
        raise HTTPException(403, "Only an authorized administrator may perform this operation.")
    return principal


def authorize_faculty(faculty_code: int, request: Request, principal=Depends(require_principal)):
    try:
        faculty = resolve_normal_faculty(faculty_code)
    except ValueError as error:
        raise HTTPException(404 if request.method == "GET" else 422, "Unknown optimization faculty ID.") from error
    if principal.role == "admin":
        return principal
    if principal.role != "faculty" or principal.faculty_id != faculty.stable_id:
        raise HTTPException(403, "You may only update your own faculty preferences.")
    return principal


def authorize_faculty_metadata(faculty_id: str, principal=Depends(require_principal)):
    try:
        faculty = resolve_normal_faculty(faculty_id)
    except ValueError as error:
        raise HTTPException(404, "Unknown optimization faculty ID.") from error
    if principal.role != "admin" and (principal.role != "faculty" or principal.faculty_id != faculty.stable_id):
        raise HTTPException(403, "You may only view your own faculty profile and eligibility.")
    return principal
