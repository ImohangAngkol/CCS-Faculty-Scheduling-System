"""Cookie sessions and explicit administrator account operations."""
import secrets
from datetime import timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from database import get_identity_db
from identity_models import FacultyIdentityRecord, LoginSession, User, now
from schemas.auth import CreateAccount, LoginInput, UpdateAccount
from services import auth_service as auth
from services.preference_authorization import require_admin

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def validate_binding(db, role, faculty_id):
    if role == "admin" and faculty_id is not None:
        raise HTTPException(422, "Administrator accounts must not have faculty bindings.")
    if role == "faculty":
        if faculty_id is None or not db.get(FacultyIdentityRecord, faculty_id):
            raise HTTPException(422, "Select an imported, registered optimization faculty identity.")
        try:
            auth.resolve_faculty_identity(str(faculty_id))
        except ValueError as error:
            raise HTTPException(422, "Faculty identity is unavailable in the scheduling registry. Ask an administrator to repair the binding.") from error


def password_hash(value):
    try:
        return auth.hash_password(value)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


def commit(db):
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, "Username or faculty binding already exists, or account constraints failed.") from error


@router.post("/login")
def login(payload: LoginInput, request: Request, response: Response, db=Depends(get_identity_db, scope="function")):
    auth.check_origin(request)
    auth.LOGIN_LIMITER.check(request, payload.username)
    user = db.scalar(select(User).where(User.username == payload.username))
    valid = auth.verify_password(user.password_hash if user else auth.DUMMY_HASH, payload.password.get_secret_value())
    if not user or not valid or not user.is_active:
        raise HTTPException(401, "Invalid credentials or account unavailable.")
    secure = auth.cookie_secure()
    lifetime = auth.session_seconds()
    # Revoke the previous browser session before rotating its identifier.
    previous = request.cookies.get(auth.COOKIE_NAME)
    if previous:
        db.execute(delete(LoginSession).where(LoginSession.token_hash == auth.token_hash(previous)))
    db.execute(delete(LoginSession).where(LoginSession.expires_at <= now()))
    token = secrets.token_urlsafe(32)
    session = LoginSession(token_hash=auth.token_hash(token), user_id=user.id,
                           csrf_token=secrets.token_urlsafe(32), expires_at=now() + timedelta(seconds=lifetime))
    db.add(session)
    commit(db)
    response.set_cookie(auth.COOKIE_NAME, token, max_age=lifetime, httponly=True,
                        secure=secure, samesite="lax", path="/")
    response.headers["Cache-Control"] = "no-store"
    return {"user": auth.user_payload(user), "csrf_token": session.csrf_token,
            "expires_at": session.expires_at}


@router.get("/me")
def me(response: Response, account=Depends(auth.authenticated_session)):
    user, session = account
    response.headers["Cache-Control"] = "no-store"
    return {"user": auth.user_payload(user), "csrf_token": session.csrf_token,
            "expires_at": session.expires_at}


@router.post("/logout", status_code=204)
def logout(response: Response, account=Depends(auth.authenticated_session), db=Depends(auth.authenticated_db, scope="function")):
    _user, session = account
    db.execute(delete(LoginSession).where(LoginSession.id == session.id))
    commit(db)
    response.delete_cookie(auth.COOKIE_NAME, httponly=True, secure=auth.cookie_secure(), samesite="lax", path="/")
    response.headers["Cache-Control"] = "no-store"


@router.get("/users", dependencies=[Depends(require_admin)])
def users(db=Depends(auth.authenticated_db, scope="function")):
    return [auth.user_payload(user) for user in db.scalars(select(User).order_by(User.username))]


@router.post("/users", status_code=201, dependencies=[Depends(require_admin)])
def create_user(payload: CreateAccount, db=Depends(auth.authenticated_db, scope="function")):
    validate_binding(db, payload.role, payload.faculty_id)
    user = User(username=payload.username, password_hash=password_hash(payload.password.get_secret_value()),
                role=payload.role, faculty_id=payload.faculty_id)
    db.add(user)
    commit(db)
    return auth.user_payload(user)


@router.patch("/users/{user_id}", dependencies=[Depends(require_admin)])
def update_user(user_id: UUID, payload: UpdateAccount, db=Depends(auth.authenticated_db, scope="function")):
    # Lock active admins in deterministic order before a possible last-admin change.
    admins = list(db.scalars(select(User).where(User.role == "admin", User.is_active.is_(True))
                            .order_by(User.id).with_for_update()))
    user = db.get(User, user_id, with_for_update=True)
    if not user:
        raise HTTPException(404, "Account not found.")
    values = payload.model_dump(exclude_unset=True)
    if any(values.get(key) is None for key in ("role", "is_active") if key in values):
        raise HTTPException(422, "Role and active status cannot be null.")
    role = values.get("role", user.role)
    binding = values.get("faculty_id", user.faculty_id)
    validate_binding(db, role, binding)
    if user in admins and len(admins) == 1 and (role != "admin" or values.get("is_active") is False):
        raise HTTPException(409, "The last active administrator cannot be disabled or demoted.")
    for key in ("role", "faculty_id", "is_active"):
        if key in values:
            setattr(user, key, values[key])
    if payload.password is not None:
        user.password_hash = password_hash(payload.password.get_secret_value())
    # All permission, password and binding changes invalidate existing sessions.
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    commit(db)
    return auth.user_payload(user)
