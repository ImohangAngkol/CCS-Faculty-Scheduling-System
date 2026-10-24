"""D12 immutable decisions. D11 request rows/events are never rewritten."""
import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from adjustment_models import AdjustmentRequest
from identity_models import User, now


class ChairBase(DeclarativeBase):
    pass


class ChairDecision(ChairBase):
    __tablename__ = 'faculty_adjustment_decisions'
    __table_args__ = (
        UniqueConstraint('request_id', name='uq_chair_final_request'),
        UniqueConstraint('actor_id', 'operation_id', name='uq_chair_operation'),
        CheckConstraint("action IN ('APPROVE','REJECT')", name='ck_chair_action'),
        CheckConstraint('request_version > 0', name='ck_chair_version'),
        CheckConstraint('length(payload_digest)=64 AND length(command_digest)=64', name='ck_chair_digests'),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(AdjustmentRequest.id, ondelete='RESTRICT'))
    request_version: Mapped[int] = mapped_column(Integer)
    actor_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(User.id, ondelete='RESTRICT'))
    department_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    operation_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    action: Mapped[str] = mapped_column(String(16))
    command_digest: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[str] = mapped_column(Text)
    payload_digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
