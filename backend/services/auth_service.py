"""Verified database sessions; client roles and faculty IDs are never principals."""
import hashlib
import hmac
import os
import secrets
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from urllib.parse import urlsplit
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from database import get_identity_db
from identity_models import LoginSession, User
from services.identity_service import resolve_faculty_identity

PASSWORDS = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
COOKIE_NAME = "ccs_session"


def allowed_origins():
    origins = [item.strip() for item in os.environ.get("AUTH_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if item.strip()]
    try:
        if not origins:
            raise ValueError()
        for origin in origins:
            parsed = urlsplit(origin)
            if (parsed.scheme not in {"http", "https"} or not parsed.hostname or "*" in origin
                    or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment):
                raise ValueError()
            _ = parsed.port  # Reject malformed ports, not just malformed schemes.
    except ValueError as error:
        raise HTTPException(503, "Configure exact HTTP/HTTPS authentication origins without paths or wildcards.") from error
    return origins


def cookie_secure():
    # Only explicit loopback HTTP development is permitted without Secure.
    insecure = os.environ.get("AUTH_COOKIE_SECURE", "true").lower() == "false"
    if insecure and any(urlsplit(origin).scheme != "http" or urlsplit(origin).hostname not in {"localhost", "127.0.0.1", "::1"} for origin in allowed_origins()):
        raise HTTPException(503, "Insecure cookies are permitted only for loopback development origins.")
    return not insecure


def session_seconds():
    try:
        value = int(os.environ.get("AUTH_SESSION_SECONDS", "28800"))
        if not 60 <= value <= 86400:
            raise ValueError()
        return value
    except ValueError as error:
        raise HTTPException(503, "Invalid authentication session lifetime.") from error


def check_origin(request):
    if request.headers.get("origin") not in allowed_origins():
        raise HTTPException(403, "Request origin is not authorized.")


def hash_password(password):
    if len(password) < 12 or len(password.encode("utf-8")) > 1024:
        raise ValueError("Passwords require at least 12 characters and at most 1024 UTF-8 bytes.")
    return PASSWORDS.hash(password)


def verify_password(encoded, password):
    if len(password.encode("utf-8")) > 1024:
        return False
    try:
        return PASSWORDS.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def authenticated_db(request: Request):
    if not request.cookies.get(COOKIE_NAME):
        raise HTTPException(401, "Sign in to continue.")
    yield from get_identity_db()


def authenticated_session(request: Request, db=Depends(authenticated_db, scope="function")):
    token = request.cookies.get(COOKIE_NAME)
    if not token or len(token) > 128:
        raise HTTPException(401, "Sign in to continue.")
    session = db.scalar(select(LoginSession).where(LoginSession.token_hash == token_hash(token)))
    user = db.get(User, session.user_id) if session else None
    if not session or not user or not user.is_active or utc(session.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(401, "Session expired or account disabled. Sign in again.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        check_origin(request)
        submitted = request.headers.get("x-csrf-token", "")
        if len(submitted) > 128 or not hmac.compare_digest(submitted.encode("utf-8"), session.csrf_token.encode("utf-8")):
            raise HTTPException(403, "Session security check failed. Reload and try again.")
    return user, session


def user_payload(user):
    binding = None
    if user.role == "faculty" and user.faculty_id:
        try:
            identity = resolve_faculty_identity(str(user.faculty_id))
            binding = {"faculty_id": identity.faculty_id, "faculty_code": identity.faculty_code,
                       "display_code": identity.display_code, "name": identity.name}
        except ValueError:
            pass
    return {"id": str(user.id), "username": user.username, "role": user.role,
            "faculty_id": str(user.faculty_id) if user.faculty_id else None,
            "faculty": binding, "is_active": user.is_active}


class LoginLimiter:
    """Bounded process-local throttling. Deployment requires one API worker."""
    def __init__(self):
        self.lock = threading.Lock()
        self.attempts = OrderedDict()

    def check(self, request, username):
        key = token_hash(f"{request.client.host if request.client else 'unknown'}:{username}")
        clock = time.monotonic()
        with self.lock:
            attempts = [stamp for stamp in self.attempts.pop(key, []) if clock - stamp < 300]
            if len(attempts) >= 10:
                self.attempts[key] = attempts
                raise HTTPException(429, "Too many sign-in attempts. Wait five minutes and retry.")
            self.attempts[key] = [*attempts, clock]
            while len(self.attempts) > 4096:
                self.attempts.popitem(last=False)


LOGIN_LIMITER = LoginLimiter()
# Unknown users perform the same expensive verification; no predictable account.
DUMMY_HASH = PASSWORDS.hash(secrets.token_urlsafe(32))
