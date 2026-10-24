"""Fixture-owned D13 SQL guards; application startup never creates schema."""
from application_models import ApplicationBase


def install(engine):
    ApplicationBase.metadata.create_all(engine)
    with engine.begin() as db:
        for table in ('published_schedule_versions','schedule_adjustment_applications'):
            for action in ('UPDATE','DELETE'):
                db.exec_driver_sql(f"CREATE TRIGGER d13_{table}_{action} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'immutable publication history'); END")
        db.exec_driver_sql("CREATE TRIGGER d13_head_delete BEFORE DELETE ON published_schedule_heads BEGIN SELECT RAISE(ABORT,'immutable publication head'); END")
        db.exec_driver_sql("""CREATE TRIGGER d13_version_insert BEFORE INSERT ON published_schedule_versions BEGIN
          SELECT CASE WHEN NOT ((NEW.sequence=1 AND NEW.previous_id IS NULL) OR EXISTS(SELECT 1 FROM published_schedule_versions p WHERE p.id=NEW.previous_id AND p.schedule_key=NEW.schedule_key AND p.sequence=NEW.sequence-1)) THEN RAISE(ABORT,'invalid publication lineage') END; END""")
        db.exec_driver_sql("""CREATE TRIGGER d13_head_insert BEFORE INSERT ON published_schedule_heads BEGIN
          SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM published_schedule_versions v WHERE v.id=NEW.version_id AND v.schedule_key=NEW.schedule_key AND v.sequence=1 AND NEW.sequence=1) THEN RAISE(ABORT,'invalid initial head') END; END""")
        db.exec_driver_sql("""CREATE TRIGGER d13_head_update BEFORE UPDATE ON published_schedule_heads BEGIN
          SELECT CASE WHEN NEW.schedule_key<>OLD.schedule_key OR NEW.sequence<>OLD.sequence+1 OR NOT EXISTS(SELECT 1 FROM published_schedule_versions v JOIN schedule_adjustment_applications a ON a.new_version_id=v.id WHERE v.id=NEW.version_id AND v.previous_id=OLD.version_id AND v.schedule_key=NEW.schedule_key AND v.sequence=NEW.sequence) THEN RAISE(ABORT,'invalid publication transition') END; END""")
        db.exec_driver_sql("""CREATE TRIGGER d13_application_insert BEFORE INSERT ON schedule_adjustment_applications BEGIN
          SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM faculty_adjustment_requests r JOIN faculty_adjustment_decisions d ON d.request_id=r.id JOIN users u ON u.id=NEW.actor_id JOIN published_schedule_versions p ON p.id=NEW.previous_version_id JOIN published_schedule_versions n ON n.id=NEW.new_version_id WHERE r.id=NEW.request_id AND r.status='SUBMITTED' AND d.id=NEW.decision_id AND d.action='APPROVE' AND d.department_id=NEW.department_id AND u.is_active=1 AND n.previous_id=p.id AND n.schedule_key=p.schedule_key AND n.sequence=p.sequence+1) THEN RAISE(ABORT,'invalid application') END; END""")
