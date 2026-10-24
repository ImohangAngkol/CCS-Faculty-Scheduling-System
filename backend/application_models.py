"""D13 append-only published versions/application audit; no GA artifact storage."""
from datetime import datetime
from uuid import UUID
from sqlalchemy import String, Text, Integer, DateTime, Uuid, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from adjustment_models import AdjustmentRequest
from chair_models import ChairDecision
from identity_models import User, now


class ApplicationBase(DeclarativeBase): pass


class PublishedVersion(ApplicationBase):
    __tablename__='published_schedule_versions'
    __table_args__=(UniqueConstraint('schedule_key','sequence',name='uq_published_sequence'),UniqueConstraint('schedule_key','revision',name='uq_published_revision'),CheckConstraint('sequence > 0',name='ck_published_sequence'))
    id: Mapped[UUID]=mapped_column(Uuid,primary_key=True)
    schedule_key: Mapped[str]=mapped_column(String(64))
    sequence: Mapped[int]=mapped_column(Integer)
    revision: Mapped[str]=mapped_column(String(64))
    previous_id: Mapped[UUID | None]=mapped_column(Uuid,ForeignKey('published_schedule_versions.id',ondelete='RESTRICT'))
    content_json: Mapped[str]=mapped_column(Text)
    content_digest: Mapped[str]=mapped_column(String(64))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)


class PublishedHead(ApplicationBase):
    __tablename__='published_schedule_heads'
    schedule_key: Mapped[str]=mapped_column(String(64),primary_key=True)
    version_id: Mapped[UUID]=mapped_column(Uuid,ForeignKey(PublishedVersion.id,ondelete='RESTRICT'),unique=True)
    sequence: Mapped[int]=mapped_column(Integer)


class ScheduleApplication(ApplicationBase):
    __tablename__='schedule_adjustment_applications'
    __table_args__=(UniqueConstraint('request_id',name='uq_application_request'),UniqueConstraint('decision_id',name='uq_application_decision'),UniqueConstraint('new_version_id',name='uq_application_publication'),UniqueConstraint('actor_id','operation_id',name='uq_application_operation'))
    id: Mapped[UUID]=mapped_column(Uuid,primary_key=True)
    request_id: Mapped[UUID]=mapped_column(Uuid,ForeignKey(AdjustmentRequest.id,ondelete='RESTRICT'))
    decision_id: Mapped[UUID]=mapped_column(Uuid,ForeignKey(ChairDecision.id,ondelete='RESTRICT'))
    actor_id: Mapped[UUID]=mapped_column(Uuid,ForeignKey(User.id,ondelete='RESTRICT'))
    department_id: Mapped[UUID]=mapped_column(Uuid)
    operation_id: Mapped[UUID]=mapped_column(Uuid)
    previous_version_id: Mapped[UUID]=mapped_column(Uuid,ForeignKey(PublishedVersion.id,ondelete='RESTRICT'))
    new_version_id: Mapped[UUID]=mapped_column(Uuid,ForeignKey(PublishedVersion.id,ondelete='RESTRICT'))
    command_digest: Mapped[str]=mapped_column(String(64))
    payload_json: Mapped[str]=mapped_column(Text)
    payload_digest: Mapped[str]=mapped_column(String(64))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
