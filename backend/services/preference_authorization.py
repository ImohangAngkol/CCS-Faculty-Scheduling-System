"""Fail-closed boundary awaiting Phase 4's real server identity provider.

No client header, role, faculty code, token or environment bypass grants access.
Dependency overrides are used only by isolated tests. A future authenticated
provider must verify credentials and construct this principal on the server.
"""
from dataclasses import dataclass
from fastapi import Depends, HTTPException
from services.metadata_service import resolve_normal_faculty


@dataclass(frozen=True)
class PreferencePrincipal:
    role: str
    faculty_id: str | None = None


def current_principal() -> PreferencePrincipal | None:
    return None  # No trustworthy authentication subsystem is installed.


def require_principal(principal=Depends(current_principal)):
    if principal is None:
        raise HTTPException(401, "Preference writes require authenticated accounts. Authentication is not configured; no changes were saved.")
    return principal


def require_admin(principal=Depends(require_principal)):
    if principal.role != "admin":
        raise HTTPException(403, "Only an authorized administrator may perform this operation.")
    return principal


def authorize_faculty(faculty_code: int, principal=Depends(require_principal)):
    try:
        faculty = resolve_normal_faculty(faculty_code)
    except ValueError as error:
        raise HTTPException(422, "Unknown optimization faculty ID.") from error
    if principal.role == "admin":
        return principal
    if principal.role != "faculty" or principal.faculty_id != faculty.stable_id:
        raise HTTPException(403, "You may only update your own faculty preferences.")
    return principal
