"""Additive D12 final decisions; explicit migration only, never automatic."""
from alembic import op
revision = 'd12_0001'
down_revision = 'd11_0001'
branch_labels = None
depends_on = None

DDL = ("CREATE TABLE faculty_adjustment_decisions (\n\tid UUID NOT NULL, \n\trequest_id UUID NOT NULL, \n\trequest_version INTEGER NOT NULL, \n\tactor_id UUID NOT NULL, \n\tdepartment_id UUID NOT NULL, \n\toperation_id UUID NOT NULL, \n\taction VARCHAR(16) NOT NULL, \n\tcommand_digest VARCHAR(64) NOT NULL, \n\tpayload_json TEXT NOT NULL, \n\tpayload_digest VARCHAR(64) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_chair_final_request UNIQUE (request_id), \n\tCONSTRAINT uq_chair_operation UNIQUE (actor_id, operation_id), \n\tCONSTRAINT ck_chair_action CHECK (action IN ('APPROVE','REJECT')), \n\tCONSTRAINT ck_chair_version CHECK (request_version > 0), \n\tCONSTRAINT ck_chair_digests CHECK (length(payload_digest)=64 AND length(command_digest)=64), \n\tFOREIGN KEY(request_id) REFERENCES faculty_adjustment_requests (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE RESTRICT\n)", "CREATE FUNCTION d12_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable Chair decision'; END $$", 'CREATE TRIGGER chair_decision_immutable BEFORE UPDATE OR DELETE ON faculty_adjustment_decisions FOR EACH ROW EXECUTE FUNCTION d12_immutable()', "CREATE FUNCTION d12_guard_insert() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE r faculty_adjustment_requests%ROWTYPE; BEGIN\n SELECT * INTO r FROM faculty_adjustment_requests WHERE id=NEW.request_id FOR UPDATE;\n IF NOT FOUND OR r.status<>'SUBMITTED' OR r.version<>NEW.request_version OR r.owner_id=NEW.actor_id\n THEN RAISE EXCEPTION 'ineligible Chair decision'; END IF;\n IF EXISTS(SELECT 1 FROM users WHERE id=NEW.actor_id AND (NOT is_active OR faculty_id=r.faculty_id))\n THEN RAISE EXCEPTION 'ineligible Chair actor'; END IF; RETURN NEW; END $$", 'CREATE TRIGGER chair_decision_insert BEFORE INSERT ON faculty_adjustment_decisions FOR EACH ROW EXECUTE FUNCTION d12_guard_insert()', "CREATE FUNCTION d12_guard_withdraw() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF EXISTS(SELECT 1 FROM faculty_adjustment_decisions WHERE request_id=OLD.id) THEN RAISE EXCEPTION 'request already decided'; END IF; RETURN NEW; END $$", 'CREATE TRIGGER chair_request_guard BEFORE UPDATE ON faculty_adjustment_requests FOR EACH ROW EXECUTE FUNCTION d12_guard_withdraw()')

def upgrade():
    for statement in DDL: op.execute(statement)

def downgrade():
    op.execute("DO $$ BEGIN IF EXISTS(SELECT 1 FROM faculty_adjustment_decisions) THEN RAISE EXCEPTION 'D12 downgrade refuses retained decisions'; END IF; END $$")
    op.execute('DROP TRIGGER chair_request_guard ON faculty_adjustment_requests')
    op.execute('DROP TABLE faculty_adjustment_decisions')
    op.execute('DROP FUNCTION d12_guard_insert()')
    op.execute('DROP FUNCTION d12_guard_withdraw()')
    op.execute('DROP FUNCTION d12_immutable()')
