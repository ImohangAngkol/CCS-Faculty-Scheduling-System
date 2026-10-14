"""Identity foundation only; no institutional JSON or GA data migration.

Revision ID: 4a_0001
Revises: None
"""
from alembic import op
import sqlalchemy as sa

revision = "4a_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("faculty_identities",
                    sa.Column("id", sa.Uuid(), primary_key=True),
                    sa.Column("display_code", sa.String(100), nullable=False, unique=True),
                    sa.Column("name", sa.String(200), nullable=False))
    op.create_table("users",
                    sa.Column("id", sa.Uuid(), primary_key=True),
                    sa.Column("username", sa.String(254), nullable=False, unique=True),
                    sa.Column("password_hash", sa.String(512), nullable=False),
                    sa.Column("role", sa.String(20), nullable=False),
                    sa.Column("faculty_id", sa.Uuid(), sa.ForeignKey("faculty_identities.id", ondelete="RESTRICT"), unique=True),
                    sa.Column("is_active", sa.Boolean(), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
                    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
                    sa.CheckConstraint("role IN ('admin', 'faculty')", name="ck_user_role"),
                    sa.CheckConstraint("(role = 'admin' AND faculty_id IS NULL) OR (role = 'faculty' AND faculty_id IS NOT NULL)", name="ck_user_binding"),
                    sa.CheckConstraint("username = lower(username)", name="ck_username_lower"))
    op.create_table("login_sessions",
                    sa.Column("id", sa.Uuid(), primary_key=True),
                    sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
                    sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
                    sa.Column("csrf_token", sa.String(64), nullable=False),
                    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_login_sessions_user_id", "login_sessions", ["user_id"])
    op.create_index("ix_login_sessions_expires_at", "login_sessions", ["expires_at"])


def downgrade():
    # Explicitly destructive rollback of identity tables only; back up accounts first.
    op.drop_table("login_sessions")
    op.drop_table("users")
    op.drop_table("faculty_identities")
