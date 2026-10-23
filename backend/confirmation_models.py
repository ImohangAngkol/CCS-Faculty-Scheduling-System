"""D9 append-only ledger, separate metadata from the seven-table foundation.

Create/apply schema only through explicit migrations. No engine or startup DDL.
"""
import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from identity_models import User, now


class ConfirmationBase(DeclarativeBase):
    pass


class ExternalRecord(ConfirmationBase):
    __tablename__='gec_records'
    __table_args__=(CheckConstraint('version >= 0',name='ck_gec_record_version'),
        ForeignKeyConstraint(['head_event_id','id'],['gec_events.id','gec_events.record_id'],name='fk_gec_head',use_alter=True,deferrable=True,initially='DEFERRED'))
    id: Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True)
    academic_year: Mapped[str]=mapped_column(String(40))
    term: Mapped[str]=mapped_column(String(120))
    supplier: Mapped[str]=mapped_column(String(120))
    version: Mapped[int]=mapped_column(Integer,default=0)
    head_event_id: Mapped[uuid.UUID|None]=mapped_column(Uuid)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)


class ExternalRevision(ConfirmationBase):
    __tablename__='gec_revisions'
    __table_args__=(UniqueConstraint('id','record_id',name='uq_gec_revision_record'),
        CheckConstraint('length(content_digest)=64',name='ck_gec_revision_digest'),
        ForeignKeyConstraint(['base_event_id','record_id'],['gec_events.id','gec_events.record_id'],name='fk_gec_revision_base',use_alter=True,ondelete='RESTRICT'))
    id: Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True)
    record_id: Mapped[uuid.UUID]=mapped_column(Uuid,ForeignKey('gec_records.id',ondelete='RESTRICT'),index=True)
    base_event_id: Mapped[uuid.UUID|None]=mapped_column(Uuid)
    created_by: Mapped[uuid.UUID]=mapped_column(Uuid,ForeignKey(User.id,ondelete='RESTRICT'))
    reason: Mapped[str]=mapped_column(String(500))
    content_json: Mapped[str]=mapped_column(Text)
    content_digest: Mapped[str]=mapped_column(String(64))
    evidence_json: Mapped[str]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)


class ConfirmationEvent(ConfirmationBase):
    __tablename__='gec_events'
    __table_args__=(
        UniqueConstraint('record_id','sequence',name='uq_gec_event_sequence'),
        UniqueConstraint('id','record_id',name='uq_gec_event_record'),
        CheckConstraint("action IN ('CONFIRM','REVOKE')",name='ck_gec_event_action'),
        CheckConstraint('sequence > 0',name='ck_gec_event_sequence'),
        ForeignKeyConstraint(['revision_id','record_id'],['gec_revisions.id','gec_revisions.record_id'],name='fk_gec_event_revision',ondelete='RESTRICT'),
        ForeignKeyConstraint(['previous_event_id','record_id'],['gec_events.id','gec_events.record_id'],name='fk_gec_event_previous',ondelete='RESTRICT'),
        CheckConstraint('length(content_digest)=64 AND length(evidence_digest)=64 AND length(policy_digest)=64',name='ck_gec_event_digests'),
    )
    id: Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True)
    record_id: Mapped[uuid.UUID]=mapped_column(Uuid,ForeignKey('gec_records.id',ondelete='RESTRICT'),index=True)
    revision_id: Mapped[uuid.UUID]=mapped_column(Uuid)
    previous_event_id: Mapped[uuid.UUID|None]=mapped_column(Uuid)
    sequence: Mapped[int]=mapped_column(Integer)
    action: Mapped[str]=mapped_column(String(12))
    actor_id: Mapped[uuid.UUID]=mapped_column(Uuid,ForeignKey(User.id,ondelete='RESTRICT'))
    policy_reference: Mapped[str]=mapped_column(String(120))
    policy_digest: Mapped[str]=mapped_column(String(64))
    evidence_digest: Mapped[str]=mapped_column(String(64))
    content_digest: Mapped[str]=mapped_column(String(64))
    evidence_json: Mapped[str]=mapped_column(Text)
    reason: Mapped[str]=mapped_column(String(500))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)


def guard_sql(dialect):
    """Frozen migration copies this SQL; tests install it only in owned SQLite."""
    immutable=('gec_revisions','gec_events')
    if dialect=='sqlite':
        statements=[f"CREATE TRIGGER {table}_{operation.lower()} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, 'immutable GEC history'); END" for table in immutable for operation in ('UPDATE','DELETE')]
        statements += ["CREATE TRIGGER gec_records_delete BEFORE DELETE ON gec_records BEGIN SELECT RAISE(ABORT, 'immutable GEC record'); END",
        """CREATE TRIGGER gec_records_head BEFORE UPDATE ON gec_records BEGIN
          SELECT CASE WHEN NEW.id IS NOT OLD.id OR NEW.academic_year IS NOT OLD.academic_year OR NEW.term IS NOT OLD.term
           OR NEW.supplier IS NOT OLD.supplier OR NEW.created_at IS NOT OLD.created_at OR NEW.version != OLD.version+1
           OR NOT EXISTS (SELECT 1 FROM gec_events e WHERE e.id=NEW.head_event_id AND e.record_id=OLD.id
             AND e.sequence=NEW.version AND e.previous_event_id IS OLD.head_event_id)
          THEN RAISE(ABORT, 'invalid GEC head transition') END; END"""]
        return statements
    return ["""CREATE FUNCTION d9_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable GEC history'; END $$""",
        *[f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION d9_immutable()" for table in immutable],
        "CREATE TRIGGER gec_records_delete BEFORE DELETE ON gec_records FOR EACH ROW EXECUTE FUNCTION d9_immutable()",
        """CREATE FUNCTION d9_guard_head() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
        IF (NEW.id,NEW.academic_year,NEW.term,NEW.supplier,NEW.created_at) IS DISTINCT FROM
           (OLD.id,OLD.academic_year,OLD.term,OLD.supplier,OLD.created_at) OR NEW.version <> OLD.version+1 OR
           NOT EXISTS (SELECT 1 FROM gec_events e WHERE e.id=NEW.head_event_id AND e.record_id=OLD.id
             AND e.sequence=NEW.version AND e.previous_event_id IS NOT DISTINCT FROM OLD.head_event_id)
        THEN RAISE EXCEPTION 'invalid GEC head transition'; END IF; RETURN NEW; END $$""",
        "CREATE TRIGGER gec_records_head BEFORE UPDATE ON gec_records FOR EACH ROW EXECUTE FUNCTION d9_guard_head()"]


def transition_sql(dialect):
    # Head movement is owned by the event insert, not by a mutable service flag.
    if dialect=='sqlite':
        return ["""CREATE TRIGGER gec_record_insert BEFORE INSERT ON gec_records BEGIN
          SELECT CASE WHEN NEW.version<>0 OR NEW.head_event_id IS NOT NULL THEN RAISE(ABORT, 'invalid initial GEC head') END; END""",
        """CREATE TRIGGER gec_event_insert BEFORE INSERT ON gec_events BEGIN
        SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM gec_records r JOIN gec_revisions v ON v.record_id=r.id
          WHERE r.id=NEW.record_id AND v.id=NEW.revision_id AND NEW.sequence=r.version+1
           AND NEW.previous_event_id IS r.head_event_id AND
           ((NEW.action='CONFIRM' AND v.base_event_id IS r.head_event_id) OR
            (NEW.action='REVOKE' AND EXISTS (SELECT 1 FROM gec_events h WHERE h.id=r.head_event_id AND h.action='CONFIRM' AND h.revision_id=v.id))))
        THEN RAISE(ABORT, 'stale GEC transition') END; END""",
        """CREATE TRIGGER gec_event_head AFTER INSERT ON gec_events BEGIN
        UPDATE gec_records SET head_event_id=NEW.id, version=NEW.sequence WHERE id=NEW.record_id; END"""]
    return ["""CREATE FUNCTION d9_initial_record() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
      IF NEW.version<>0 OR NEW.head_event_id IS NOT NULL THEN RAISE EXCEPTION 'invalid initial GEC head'; END IF; RETURN NEW; END $$""",
      "CREATE TRIGGER gec_record_insert BEFORE INSERT ON gec_records FOR EACH ROW EXECUTE FUNCTION d9_initial_record()",
      """CREATE FUNCTION d9_guard_event() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE r gec_records%ROWTYPE; v gec_revisions%ROWTYPE; BEGIN
      SELECT * INTO r FROM gec_records WHERE id=NEW.record_id FOR UPDATE;
      SELECT * INTO v FROM gec_revisions WHERE id=NEW.revision_id AND record_id=NEW.record_id;
      IF r.id IS NULL OR v.id IS NULL OR NEW.sequence <> r.version+1 OR NEW.previous_event_id IS DISTINCT FROM r.head_event_id
       OR (NEW.action='CONFIRM' AND v.base_event_id IS DISTINCT FROM r.head_event_id)
       OR (NEW.action='REVOKE' AND NOT EXISTS(SELECT 1 FROM gec_events h WHERE h.id=r.head_event_id AND h.action='CONFIRM' AND h.revision_id=v.id))
      THEN RAISE EXCEPTION 'stale GEC transition'; END IF; RETURN NEW; END $$""",
      "CREATE TRIGGER gec_event_insert BEFORE INSERT ON gec_events FOR EACH ROW EXECUTE FUNCTION d9_guard_event()",
      """CREATE FUNCTION d9_move_head() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
      UPDATE gec_records SET head_event_id=NEW.id, version=NEW.sequence WHERE id=NEW.record_id; RETURN NEW; END $$""",
      "CREATE TRIGGER gec_event_head AFTER INSERT ON gec_events FOR EACH ROW EXECUTE FUNCTION d9_move_head()"]
