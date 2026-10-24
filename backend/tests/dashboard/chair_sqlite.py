"""Fixture-owned SQLite equivalents; never installed by application startup."""
from chair_models import ChairBase


def install(engine):
    ChairBase.metadata.create_all(engine)
    with engine.begin() as db:
        for action in ('UPDATE','DELETE'):
            db.exec_driver_sql(f"CREATE TRIGGER d12_immutable_{action} BEFORE {action} ON faculty_adjustment_decisions BEGIN SELECT RAISE(ABORT,'immutable Chair decision'); END")
        db.exec_driver_sql("""CREATE TRIGGER d12_insert BEFORE INSERT ON faculty_adjustment_decisions BEGIN
          SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM faculty_adjustment_requests r JOIN users u ON u.id=NEW.actor_id
            WHERE r.id=NEW.request_id AND r.status='SUBMITTED' AND r.version=NEW.request_version
            AND r.owner_id<>NEW.actor_id AND u.is_active=1 AND (u.faculty_id IS NULL OR u.faculty_id<>r.faculty_id))
          THEN RAISE(ABORT,'ineligible Chair decision') END; END""")
        db.exec_driver_sql("CREATE TRIGGER d12_withdraw BEFORE UPDATE ON faculty_adjustment_requests WHEN EXISTS(SELECT 1 FROM faculty_adjustment_decisions WHERE request_id=OLD.id) BEGIN SELECT RAISE(ABORT,'request already decided'); END")
