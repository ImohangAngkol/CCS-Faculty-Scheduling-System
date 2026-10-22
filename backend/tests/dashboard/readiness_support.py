"""Test-only receipt binding using the actual synthetic client's verified session."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from identity_models import User, LoginSession
from services import auth_service as auth, external_schedule_preview_lifecycle as lifecycle


def bind_client_preview(source, fixture):
    with Session(fixture.engine) as db:
        session = db.scalar(select(LoginSession).where(LoginSession.token_hash == auth.token_hash(fixture.client.cookies.get(auth.COOKIE_NAME))))
        user = db.get(User,session.user_id)
        return lifecycle.bind(source,(user,session))
