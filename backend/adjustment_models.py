"""D11 requests and append-only history; no schedule ownership or startup DDL."""
import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from identity_models import FacultyIdentityRecord, User, now


class AdjustmentBase(DeclarativeBase):
    pass


class AdjustmentRequest(AdjustmentBase):
    __tablename__ = 'faculty_adjustment_requests'
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT','SUBMITTED','WITHDRAWN')", name='ck_adjustment_status'),
        CheckConstraint('version > 0', name='ck_adjustment_version'),
        CheckConstraint('length(content_digest)=64', name='ck_adjustment_digest'),
        UniqueConstraint('owner_id', 'create_operation', name='uq_adjustment_create_operation'),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(User.id, ondelete='RESTRICT'), index=True)
    faculty_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(FacultyIdentityRecord.id, ondelete='RESTRICT'))
    create_operation: Mapped[uuid.UUID] = mapped_column(Uuid)
    command_digest: Mapped[str] = mapped_column(String(64))
    content_json: Mapped[str] = mapped_column(Text)
    content_digest: Mapped[str] = mapped_column(String(64))
    active_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(16))
    version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AdjustmentEvent(AdjustmentBase):
    __tablename__ = 'faculty_adjustment_events'
    __table_args__ = (
        UniqueConstraint('request_id', 'sequence', name='uq_adjustment_event_sequence'),
        UniqueConstraint('actor_id', 'operation_id', name='uq_adjustment_event_operation'),
        CheckConstraint("action IN ('CREATED','SUBMITTED','WITHDRAWN')", name='ck_adjustment_event_action'),
        CheckConstraint('sequence > 0', name='ck_adjustment_event_sequence'),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(AdjustmentRequest.id, ondelete='RESTRICT'), index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(User.id, ondelete='RESTRICT'))
    operation_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    command_digest: Mapped[str] = mapped_column(String(64))
    sequence: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(16))
    previous_digest: Mapped[str | None] = mapped_column(String(64))
    payload_json: Mapped[str] = mapped_column(Text)
    event_digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
