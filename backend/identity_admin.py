"""Explicit local administrative CLI. Never called by application startup."""
import argparse
import os
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import identity_engine
from identity_models import FacultyIdentityRecord, User
from services.auth_service import hash_password
from services.identity_service import load_faculty_identities


def import_faculty(db):
    count = 0
    for identity in load_faculty_identities():
        row = db.get(FacultyIdentityRecord, UUID(identity.faculty_id))
        if row:
            if row.display_code != identity.display_code or row.name != identity.name:
                raise ValueError("Existing database identity differs from registry. Resolve explicitly; nothing was overwritten.")
        else:
            db.add(FacultyIdentityRecord(id=UUID(identity.faculty_id), display_code=identity.display_code, name=identity.name))
            count += 1
    db.flush()
    return count


def bootstrap_admin(db, username, password):
    from schemas.auth import LoginInput
    normalized = LoginInput(username=username, password=password).username
    existing = db.scalar(select(User).where(User.username == normalized))
    if existing:
        if existing.role != "admin" or not existing.is_active:
            raise ValueError("Existing username is not an active administrator. Bootstrap will not change it.")
        return False
    # PostgreSQL transaction-scoped lock serializes first-admin bootstrap commands.
    if db.bind.dialect.name == "postgresql":
        from sqlalchemy import text
        db.execute(text("SELECT pg_advisory_xact_lock(414001)"))
    if db.scalar(select(User.id).where(User.role == "admin")):
        raise ValueError("An administrator already exists. Use authenticated account administration.")
    db.add(User(username=normalized, password_hash=hash_password(password), role="admin"))
    db.flush()
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["import-faculty", "bootstrap-admin"])
    parser.add_argument("--confirm-local-identity-database", action="store_true", required=True)
    args = parser.parse_args()
    with Session(identity_engine()) as db, db.begin():
        if args.command == "import-faculty":
            print(f"Imported {import_faculty(db)} missing stable faculty identities.")
        else:
            username = os.environ.get("BOOTSTRAP_ADMIN_USERNAME")
            password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD")
            if not username or not password:
                raise ValueError("Supply BOOTSTRAP_ADMIN_USERNAME and BOOTSTRAP_ADMIN_PASSWORD privately in this process environment.")
            created = bootstrap_admin(db, username, password)
            print("Administrator created." if created else "Existing administrator retained; password unchanged.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Avoid dumping SQL parameters, URLs or credential-bearing validation input.
        raise SystemExit("Identity setup failed. Check private environment variables, migrations and existing bindings; no automatic reset was performed.")
