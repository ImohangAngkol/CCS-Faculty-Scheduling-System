"""D9 additive confirmation ledger; frozen SQL, no runtime model imports or seed.

Online execution is NOT authorized by implementation. Downgrade refuses data.
"""
from alembic import op
revision='d9_0001'
down_revision='4c_0001'
branch_labels=None
depends_on=None
DDL = ('CREATE TABLE gec_records (\n'
 '\tid UUID NOT NULL, \n'
 '\tacademic_year VARCHAR(40) NOT NULL, \n'
 '\tterm VARCHAR(120) NOT NULL, \n'
 '\tsupplier VARCHAR(120) NOT NULL, \n'
 '\tversion INTEGER NOT NULL, \n'
 '\thead_event_id UUID, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tCONSTRAINT ck_gec_record_version CHECK (version >= 0)\n'
 ')',
 'CREATE TABLE gec_revisions (\n'
 '\tid UUID NOT NULL, \n'
 '\trecord_id UUID NOT NULL, \n'
 '\tbase_event_id UUID, \n'
 '\tcreated_by UUID NOT NULL, \n'
 '\treason VARCHAR(500) NOT NULL, \n'
 '\tcontent_json TEXT NOT NULL, \n'
 '\tcontent_digest VARCHAR(64) NOT NULL, \n'
 '\tevidence_json TEXT NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tCONSTRAINT uq_gec_revision_record UNIQUE (id, record_id), \n'
 '\tCONSTRAINT ck_gec_revision_digest CHECK (length(content_digest)=64), \n'
 '\tFOREIGN KEY(record_id) REFERENCES gec_records (id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT\n'
 ')',
 'CREATE TABLE gec_events (\n'
 '\tid UUID NOT NULL, \n'
 '\trecord_id UUID NOT NULL, \n'
 '\trevision_id UUID NOT NULL, \n'
 '\tprevious_event_id UUID, \n'
 '\tsequence INTEGER NOT NULL, \n'
 '\taction VARCHAR(12) NOT NULL, \n'
 '\tactor_id UUID NOT NULL, \n'
 '\tpolicy_reference VARCHAR(120) NOT NULL, \n'
 '\tpolicy_digest VARCHAR(64) NOT NULL, \n'
 '\tevidence_digest VARCHAR(64) NOT NULL, \n'
 '\tcontent_digest VARCHAR(64) NOT NULL, \n'
 '\tevidence_json TEXT NOT NULL, \n'
 '\treason VARCHAR(500) NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tCONSTRAINT uq_gec_event_sequence UNIQUE (record_id, sequence), \n'
 '\tCONSTRAINT uq_gec_event_record UNIQUE (id, record_id), \n'
 "\tCONSTRAINT ck_gec_event_action CHECK (action IN ('CONFIRM','REVOKE')), \n"
 '\tCONSTRAINT ck_gec_event_sequence CHECK (sequence > 0), \n'
 '\tCONSTRAINT fk_gec_event_revision FOREIGN KEY(revision_id, record_id) REFERENCES gec_revisions (id, '
 'record_id) ON DELETE RESTRICT, \n'
 '\tCONSTRAINT fk_gec_event_previous FOREIGN KEY(previous_event_id, record_id) REFERENCES gec_events (id, '
 'record_id) ON DELETE RESTRICT, \n'
 '\tCONSTRAINT ck_gec_event_digests CHECK (length(content_digest)=64 AND length(evidence_digest)=64 AND '
 'length(policy_digest)=64), \n'
 '\tFOREIGN KEY(record_id) REFERENCES gec_records (id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE RESTRICT\n'
 ')',
 'ALTER TABLE gec_records ADD CONSTRAINT fk_gec_head FOREIGN KEY(head_event_id, id) REFERENCES gec_events '
 '(id, record_id) DEFERRABLE INITIALLY DEFERRED',
 'ALTER TABLE gec_revisions ADD CONSTRAINT fk_gec_revision_base FOREIGN KEY(base_event_id, record_id) '
 'REFERENCES gec_events (id, record_id) ON DELETE RESTRICT',
 "CREATE FUNCTION d9_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable GEC "
 "history'; END $$",
 'CREATE TRIGGER gec_revisions_immutable BEFORE UPDATE OR DELETE ON gec_revisions FOR EACH ROW EXECUTE '
 'FUNCTION d9_immutable()',
 'CREATE TRIGGER gec_events_immutable BEFORE UPDATE OR DELETE ON gec_events FOR EACH ROW EXECUTE FUNCTION '
 'd9_immutable()',
 'CREATE TRIGGER gec_records_delete BEFORE DELETE ON gec_records FOR EACH ROW EXECUTE FUNCTION '
 'd9_immutable()',
 'CREATE FUNCTION d9_guard_head() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN\n'
 '        IF (NEW.id,NEW.academic_year,NEW.term,NEW.supplier,NEW.created_at) IS DISTINCT FROM\n'
 '           (OLD.id,OLD.academic_year,OLD.term,OLD.supplier,OLD.created_at) OR NEW.version <> OLD.version+1 '
 'OR\n'
 '           NOT EXISTS (SELECT 1 FROM gec_events e WHERE e.id=NEW.head_event_id AND e.record_id=OLD.id\n'
 '             AND e.sequence=NEW.version AND e.previous_event_id IS NOT DISTINCT FROM OLD.head_event_id)\n'
 "        THEN RAISE EXCEPTION 'invalid GEC head transition'; END IF; RETURN NEW; END $$",
 'CREATE TRIGGER gec_records_head BEFORE UPDATE ON gec_records FOR EACH ROW EXECUTE FUNCTION d9_guard_head()',
 'CREATE FUNCTION d9_initial_record() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN\n'
 "      IF NEW.version<>0 OR NEW.head_event_id IS NOT NULL THEN RAISE EXCEPTION 'invalid initial GEC head'; "
 'END IF; RETURN NEW; END $$',
 'CREATE TRIGGER gec_record_insert BEFORE INSERT ON gec_records FOR EACH ROW EXECUTE FUNCTION '
 'd9_initial_record()',
 'CREATE FUNCTION d9_guard_event() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE r gec_records%ROWTYPE; v '
 'gec_revisions%ROWTYPE; BEGIN\n'
 '      SELECT * INTO r FROM gec_records WHERE id=NEW.record_id FOR UPDATE;\n'
 '      SELECT * INTO v FROM gec_revisions WHERE id=NEW.revision_id AND record_id=NEW.record_id;\n'
 '      IF r.id IS NULL OR v.id IS NULL OR NEW.sequence <> r.version+1 OR NEW.previous_event_id IS DISTINCT '
 'FROM r.head_event_id\n'
 "       OR (NEW.action='CONFIRM' AND v.base_event_id IS DISTINCT FROM r.head_event_id)\n"
 "       OR (NEW.action='REVOKE' AND NOT EXISTS(SELECT 1 FROM gec_events h WHERE h.id=r.head_event_id AND "
 "h.action='CONFIRM' AND h.revision_id=v.id))\n"
 "      THEN RAISE EXCEPTION 'stale GEC transition'; END IF; RETURN NEW; END $$",
 'CREATE TRIGGER gec_event_insert BEFORE INSERT ON gec_events FOR EACH ROW EXECUTE FUNCTION d9_guard_event()',
 'CREATE FUNCTION d9_move_head() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN\n'
 '      UPDATE gec_records SET head_event_id=NEW.id, version=NEW.sequence WHERE id=NEW.record_id; RETURN '
 'NEW; END $$',
 'CREATE TRIGGER gec_event_head AFTER INSERT ON gec_events FOR EACH ROW EXECUTE FUNCTION d9_move_head()')


def upgrade():
    for statement in DDL: op.execute(statement)
    op.execute('CREATE INDEX ix_gec_revisions_record_id ON gec_revisions (record_id)')
    op.execute('CREATE INDEX ix_gec_events_record_id ON gec_events (record_id)')


def downgrade():
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM gec_records) OR EXISTS(SELECT 1 FROM gec_revisions) OR EXISTS(SELECT 1 FROM gec_events)
    THEN RAISE EXCEPTION 'D9 downgrade refuses retained history'; END IF; END $$""")
    op.execute('ALTER TABLE gec_records DROP CONSTRAINT fk_gec_head')
    op.execute('ALTER TABLE gec_revisions DROP CONSTRAINT fk_gec_revision_base')
    op.execute('DROP TABLE gec_events')
    op.execute('DROP TABLE gec_revisions')
    op.execute('DROP TABLE gec_records')
    for name in ['d9_initial_record','d9_guard_event','d9_move_head','d9_guard_head','d9_immutable']:
        op.execute('DROP FUNCTION '+name+'()')
