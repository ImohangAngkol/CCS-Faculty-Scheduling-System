"""Additive D11 request/history schema. No seed, schedule update or automatic DDL.
PostgreSQL execution requires separate approval. Downgrade refuses retained data.
"""
from alembic import op
revision = 'd11_0001'
down_revision = 'd9_0001'
branch_labels = None
depends_on = None
DDL = ("CREATE TABLE faculty_adjustment_requests (\n\tid UUID NOT NULL, \n\towner_id UUID NOT NULL, \n\tfaculty_id UUID NOT NULL, \n\tcreate_operation UUID NOT NULL, \n\tcommand_digest VARCHAR(64) NOT NULL, \n\tcontent_json TEXT NOT NULL, \n\tcontent_digest VARCHAR(64) NOT NULL, \n\tactive_key VARCHAR(64), \n\tstatus VARCHAR(16) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tsubmitted_at TIMESTAMP WITH TIME ZONE, \n\twithdrawn_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_adjustment_status CHECK (status IN ('DRAFT','SUBMITTED','WITHDRAWN')), \n\tCONSTRAINT ck_adjustment_version CHECK (version > 0), \n\tCONSTRAINT ck_adjustment_digest CHECK (length(content_digest)=64), \n\tCONSTRAINT uq_adjustment_create_operation UNIQUE (owner_id, create_operation), \n\tFOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(faculty_id) REFERENCES faculty_identities (id) ON DELETE RESTRICT, \n\tUNIQUE (active_key)\n)", "CREATE TABLE faculty_adjustment_events (\n\tid UUID NOT NULL, \n\trequest_id UUID NOT NULL, \n\tactor_id UUID NOT NULL, \n\toperation_id UUID NOT NULL, \n\tcommand_digest VARCHAR(64) NOT NULL, \n\tsequence INTEGER NOT NULL, \n\taction VARCHAR(16) NOT NULL, \n\tprevious_digest VARCHAR(64), \n\tpayload_json TEXT NOT NULL, \n\tevent_digest VARCHAR(64) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_adjustment_event_sequence UNIQUE (request_id, sequence), \n\tCONSTRAINT uq_adjustment_event_operation UNIQUE (actor_id, operation_id), \n\tCONSTRAINT ck_adjustment_event_action CHECK (action IN ('CREATED','SUBMITTED','WITHDRAWN')), \n\tCONSTRAINT ck_adjustment_event_sequence CHECK (sequence > 0), \n\tFOREIGN KEY(request_id) REFERENCES faculty_adjustment_requests (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE RESTRICT\n)", 'CREATE INDEX ix_faculty_adjustment_requests_owner_id ON faculty_adjustment_requests (owner_id)', 'CREATE INDEX ix_faculty_adjustment_events_request_id ON faculty_adjustment_events (request_id)', "CREATE FUNCTION d11_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable adjustment history'; END $$", 'CREATE TRIGGER adjustment_events_immutable BEFORE UPDATE OR DELETE ON faculty_adjustment_events FOR EACH ROW EXECUTE FUNCTION d11_immutable()', 'CREATE TRIGGER adjustment_requests_delete BEFORE DELETE ON faculty_adjustment_requests FOR EACH ROW EXECUTE FUNCTION d11_immutable()', "CREATE FUNCTION d11_guard_request() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN\n IF (NEW.id,NEW.owner_id,NEW.faculty_id,NEW.create_operation,NEW.command_digest,NEW.content_json,NEW.content_digest,NEW.created_at)\n IS DISTINCT FROM (OLD.id,OLD.owner_id,OLD.faculty_id,OLD.create_operation,OLD.command_digest,OLD.content_json,OLD.content_digest,OLD.created_at)\n OR NEW.version<>OLD.version+1\n OR NOT ((OLD.status='DRAFT' AND NEW.status IN ('SUBMITTED','WITHDRAWN')) OR (OLD.status='SUBMITTED' AND NEW.status='WITHDRAWN'))\n THEN RAISE EXCEPTION 'invalid adjustment transition'; END IF; RETURN NEW; END $$", 'CREATE TRIGGER adjustment_request_update BEFORE UPDATE ON faculty_adjustment_requests FOR EACH ROW EXECUTE FUNCTION d11_guard_request()')


def upgrade():
    for statement in DDL:
        op.execute(statement)


def downgrade():
    op.execute("DO $$ BEGIN IF EXISTS(SELECT 1 FROM faculty_adjustment_requests) OR EXISTS(SELECT 1 FROM faculty_adjustment_events) THEN RAISE EXCEPTION 'D11 downgrade refuses retained request history'; END IF; END $$")
    op.execute('DROP TABLE faculty_adjustment_events')
    op.execute('DROP TABLE faculty_adjustment_requests')
    op.execute('DROP FUNCTION d11_guard_request()')
    op.execute('DROP FUNCTION d11_immutable()')
