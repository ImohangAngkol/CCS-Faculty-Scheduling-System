"""Frozen seven-table foundation. No seed, backfill, engine or runtime imports.

Revision ID: 4c_0001
Revises: 4a_0001

DDL is intentionally frozen here, independent of future model edits.
"""
from alembic import op

revision = "4c_0001"
down_revision = "4a_0001"
branch_labels = None
depends_on = None

TABLE_DDL = (
    """CREATE TABLE academic_scopes (
	id UUID NOT NULL,
	scope_key VARCHAR(100) NOT NULL,
	institution_label TEXT NOT NULL,
	department_label TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version BIGINT DEFAULT '1' NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	archived_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT uq_ac_scope_key UNIQUE (scope_key),
	CONSTRAINT ck_ac_scope_key CHECK (length(trim(scope_key)) > 0 AND scope_key = trim(scope_key)),
	CONSTRAINT ck_ac_scope_version CHECK (row_version > 0),
	CONSTRAINT ck_ac_scope_archive CHECK (archived_at IS NULL OR NOT is_active)
)""",
    """CREATE TABLE academic_years (
	id UUID NOT NULL,
	scope_id UUID NOT NULL,
	year_key VARCHAR(40) NOT NULL,
	label VARCHAR(100) NOT NULL,
	start_date DATE,
	end_date DATE,
	calendar_status VARCHAR(20) DEFAULT 'unresolved' NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version BIGINT DEFAULT '1' NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	archived_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT uq_ac_year_key UNIQUE (scope_id, year_key),
	CONSTRAINT uq_ac_year_scope UNIQUE (id, scope_id),
	CONSTRAINT ck_ac_year_key CHECK (length(trim(year_key)) > 0 AND year_key = trim(year_key)),
	CONSTRAINT ck_ac_year_calendar CHECK (calendar_status IN ('unresolved','confirmed')),
	CONSTRAINT ck_ac_year_dates CHECK ((start_date IS NULL AND end_date IS NULL) OR (start_date IS NOT NULL AND end_date IS NOT NULL AND start_date <= end_date)),
	CONSTRAINT ck_ac_year_confirmed CHECK (calendar_status <> 'confirmed' OR start_date IS NOT NULL),
	CONSTRAINT ck_ac_year_version CHECK (row_version > 0),
	CONSTRAINT ck_ac_year_archive CHECK (archived_at IS NULL OR NOT is_active),
	FOREIGN KEY(scope_id) REFERENCES academic_scopes (id) ON DELETE RESTRICT
)""",
    """CREATE TABLE academic_terms (
	id UUID NOT NULL,
	scope_id UUID NOT NULL,
	year_id UUID,
	term_key VARCHAR(80) NOT NULL,
	identity_scope VARCHAR(160) NOT NULL,
	label VARCHAR(100) NOT NULL,
	kind VARCHAR(24) DEFAULT 'legacy_unknown' NOT NULL,
	ordinal SMALLINT,
	start_date DATE,
	end_date DATE,
	timezone VARCHAR(64) NOT NULL,
	calendar_status VARCHAR(20) DEFAULT 'unresolved' NOT NULL,
	lifecycle VARCHAR(20) DEFAULT 'draft' NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version BIGINT DEFAULT '1' NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	archived_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT fk_ac_term_year_scope FOREIGN KEY(year_id, scope_id) REFERENCES academic_years (id, scope_id) ON DELETE RESTRICT,
	CONSTRAINT uq_ac_term_key UNIQUE (scope_id, term_key),
	CONSTRAINT uq_ac_term_identity UNIQUE (identity_scope),
	CONSTRAINT uq_ac_term_ordinal UNIQUE (year_id, ordinal),
	CONSTRAINT uq_ac_term_scope UNIQUE (id, scope_id),
	CONSTRAINT ck_ac_term_key CHECK (length(trim(term_key)) > 0 AND term_key = trim(term_key)),
	CONSTRAINT ck_ac_term_identity CHECK (length(trim(identity_scope)) > 0 AND identity_scope = trim(identity_scope)),
	CONSTRAINT ck_ac_term_timezone CHECK (length(trim(timezone)) > 0),
	CONSTRAINT ck_ac_term_ordinal CHECK (ordinal IS NULL OR ordinal > 0),
	CONSTRAINT ck_ac_term_kind CHECK (kind IN ('legacy_unknown','first','second','midyear','other')),
	CONSTRAINT ck_ac_term_lifecycle CHECK (lifecycle IN ('draft','open','locked','archived')),
	CONSTRAINT ck_ac_term_confirmed_year CHECK (calendar_status <> 'confirmed' OR (year_id IS NOT NULL AND ordinal IS NOT NULL AND kind <> 'legacy_unknown')),
	CONSTRAINT ck_ac_term_open CHECK (lifecycle <> 'open' OR calendar_status = 'confirmed'),
	CONSTRAINT ck_ac_term_archived CHECK ((lifecycle = 'archived') = (archived_at IS NOT NULL)),
	CONSTRAINT ck_ac_term_calendar CHECK (calendar_status IN ('unresolved','confirmed')),
	CONSTRAINT ck_ac_term_dates CHECK ((start_date IS NULL AND end_date IS NULL) OR (start_date IS NOT NULL AND end_date IS NOT NULL AND start_date <= end_date)),
	CONSTRAINT ck_ac_term_confirmed CHECK (calendar_status <> 'confirmed' OR start_date IS NOT NULL),
	CONSTRAINT ck_ac_term_version CHECK (row_version > 0),
	CONSTRAINT ck_ac_term_archive CHECK (archived_at IS NULL OR NOT is_active),
	FOREIGN KEY(scope_id) REFERENCES academic_scopes (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX ix_ac_term_year_scope ON academic_terms (year_id, scope_id)""",
    """CREATE TABLE academic_faculty_legacy_codes (
	faculty_id UUID NOT NULL,
	legacy_code INTEGER NOT NULL,
	allocated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (faculty_id),
	CONSTRAINT uq_ac_faculty_code UNIQUE (legacy_code),
	CONSTRAINT ck_ac_faculty_code CHECK (legacy_code >= 0),
	FOREIGN KEY(faculty_id) REFERENCES faculty_identities (id) ON DELETE RESTRICT
)""",
    """CREATE TABLE academic_courses (
	id UUID NOT NULL,
	scope_id UUID NOT NULL,
	identity_code VARCHAR(64) NOT NULL,
	catalog_status VARCHAR(24) DEFAULT 'descriptor_only' NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version BIGINT DEFAULT '1' NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	archived_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT uq_ac_course_key UNIQUE (scope_id, identity_code),
	CONSTRAINT uq_ac_course_scope UNIQUE (id, scope_id),
	CONSTRAINT ck_ac_course_key CHECK (length(trim(identity_code)) > 0 AND identity_code = upper(trim(identity_code))),
	CONSTRAINT ck_ac_course_status CHECK (catalog_status IN ('descriptor_only','verified')),
	CONSTRAINT ck_ac_course_version CHECK (row_version > 0),
	CONSTRAINT ck_ac_course_archive CHECK (archived_at IS NULL OR NOT is_active),
	FOREIGN KEY(scope_id) REFERENCES academic_scopes (id) ON DELETE RESTRICT
)""",
    """CREATE TABLE academic_sections (
	id UUID NOT NULL,
	term_id UUID NOT NULL,
	scope_id UUID NOT NULL,
	identity_code VARCHAR(40) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version BIGINT DEFAULT '1' NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	archived_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT fk_ac_section_term_scope FOREIGN KEY(term_id, scope_id) REFERENCES academic_terms (id, scope_id) ON DELETE RESTRICT,
	CONSTRAINT uq_ac_section_key UNIQUE (term_id, identity_code),
	CONSTRAINT uq_ac_section_term_scope UNIQUE (id, term_id, scope_id),
	CONSTRAINT ck_ac_section_key CHECK (length(trim(identity_code)) > 0 AND identity_code = upper(trim(identity_code))),
	CONSTRAINT ck_ac_section_version CHECK (row_version > 0),
	CONSTRAINT ck_ac_section_archive CHECK (archived_at IS NULL OR NOT is_active)
)""",
    """CREATE INDEX ix_ac_section_scope ON academic_sections (scope_id)""",
    """CREATE TABLE academic_course_offerings (
	id UUID NOT NULL,
	term_id UUID NOT NULL,
	scope_id UUID NOT NULL,
	course_id UUID NOT NULL,
	section_id UUID NOT NULL,
	identity_key VARCHAR(160) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version BIGINT DEFAULT '1' NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	archived_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT fk_ac_offering_term_scope FOREIGN KEY(term_id, scope_id) REFERENCES academic_terms (id, scope_id) ON DELETE RESTRICT,
	CONSTRAINT fk_ac_offering_course_scope FOREIGN KEY(course_id, scope_id) REFERENCES academic_courses (id, scope_id) ON DELETE RESTRICT,
	CONSTRAINT fk_ac_offering_section_term_scope FOREIGN KEY(section_id, term_id, scope_id) REFERENCES academic_sections (id, term_id, scope_id) ON DELETE RESTRICT,
	CONSTRAINT uq_ac_offering_membership UNIQUE (term_id, course_id, section_id),
	CONSTRAINT uq_ac_offering_key UNIQUE (term_id, identity_key),
	CONSTRAINT ck_ac_offering_key CHECK (length(trim(identity_key)) > 0 AND identity_key = upper(trim(identity_key))),
	CONSTRAINT ck_ac_offering_version CHECK (row_version > 0),
	CONSTRAINT ck_ac_offering_archive CHECK (archived_at IS NULL OR NOT is_active)
)""",
    """CREATE INDEX ix_ac_offering_course_scope ON academic_course_offerings (course_id, scope_id)""",
    """CREATE INDEX ix_ac_offering_section_term_scope ON academic_course_offerings (section_id, term_id, scope_id)""",
)

TABLE_KEYS = {
    "academic_scopes": ("id", "scope_key"),
    "academic_years": ("id", "scope_id", "year_key"),
    "academic_terms": ("id", "scope_id", "term_key", "identity_scope"),
    "academic_faculty_legacy_codes": ("faculty_id", "legacy_code", "allocated_at"),
    "academic_courses": ("id", "scope_id", "identity_code"),
    "academic_sections": ("id", "scope_id", "term_id", "identity_code"),
    "academic_course_offerings": ("id", "scope_id", "term_id", "course_id", "section_id", "identity_key"),
}

WRITE_LOCK_SQL = """
CREATE FUNCTION public.academic_4c_write_lock() RETURNS trigger
LANGUAGE plpgsql VOLATILE SET search_path = pg_catalog, public AS $$
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'Academic identity truncation is forbidden';
    END IF;
    -- A single conservative gate also serializes archive-vs-child-insert races.
    -- Fail immediately instead of waiting indefinitely on an administrative writer.
    IF current_setting('transaction_isolation') <> 'read committed' THEN
        RAISE EXCEPTION USING ERRCODE = '0A000', MESSAGE = 'Academic writes require READ COMMITTED';
    END IF;
    IF NOT pg_try_advisory_xact_lock(41002, 1) THEN
        RAISE EXCEPTION USING ERRCODE = '55P03', MESSAGE = 'Concurrent academic write; rollback and review retry';
    END IF;
    RETURN NULL;
END $$
"""

ROW_GUARD_SQL = """
CREATE FUNCTION public.academic_4c_row_guard() RETURNS trigger
LANGUAGE plpgsql VOLATILE SET search_path = pg_catalog, public AS $$
DECLARE key text; old_row jsonb; new_row jsonb; closing_only boolean := false;
        parent_term public.academic_terms%ROWTYPE;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'Academic identity deletion is forbidden; archive instead';
    END IF;
    new_row := to_jsonb(NEW);
    IF TG_OP = 'UPDATE' THEN
        old_row := to_jsonb(OLD);
        FOREACH key IN ARRAY TG_ARGV LOOP
            IF new_row -> key IS DISTINCT FROM old_row -> key THEN
                RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'Academic identity keys are immutable';
            END IF;
        END LOOP;
        IF TG_TABLE_NAME = 'academic_faculty_legacy_codes' THEN
            RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'Faculty code reservations are immutable';
        END IF;
        IF OLD.archived_at IS NOT NULL THEN
            RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'Archived academic records are immutable';
        END IF;
        IF NEW.created_at IS DISTINCT FROM OLD.created_at OR NEW.row_version <> OLD.row_version + 1 THEN
            RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'Academic update requires unchanged creation time and next revision';
        END IF;
        closing_only := NOT NEW.is_active AND
            (new_row - ARRAY['is_active','archived_at','row_version','updated_at']) =
            (old_row - ARRAY['is_active','archived_at','row_version','updated_at']);
        NEW.updated_at := clock_timestamp();
    ELSIF TG_TABLE_NAME <> 'academic_faculty_legacy_codes' THEN
        IF NEW.row_version <> 1 THEN
            RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'New academic records require revision one';
        END IF;
    END IF;
    IF TG_TABLE_NAME = 'academic_faculty_legacy_codes' THEN RETURN NEW; END IF;
    -- Only status-only closing updates may proceed under inactive parents.
    -- Even an inactive INSERT must not add a child to a locked/archived parent.
    IF NOT closing_only THEN
        IF TG_TABLE_NAME <> 'academic_scopes' THEN
            PERFORM 1 FROM public.academic_scopes WHERE id = NEW.scope_id AND is_active AND archived_at IS NULL;
            IF NOT FOUND THEN
                RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'Academic parent scope is missing or inactive';
            END IF;
        END IF;
        IF TG_TABLE_NAME = 'academic_terms' THEN
            IF NEW.year_id IS NOT NULL THEN
                PERFORM 1 FROM public.academic_years WHERE id = NEW.year_id AND scope_id = NEW.scope_id AND is_active AND archived_at IS NULL;
                IF NOT FOUND THEN
                    RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'Academic parent year is missing or inactive';
                END IF;
            END IF;
        END IF;
        IF TG_TABLE_NAME IN ('academic_sections', 'academic_course_offerings') THEN
            SELECT * INTO parent_term FROM public.academic_terms WHERE id = NEW.term_id AND scope_id = NEW.scope_id;
            IF NOT FOUND OR NOT parent_term.is_active OR parent_term.lifecycle IN ('locked','archived') THEN
                RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'Academic parent term is missing, inactive or locked';
            END IF;
        END IF;
        IF TG_TABLE_NAME = 'academic_course_offerings' THEN
            PERFORM 1 FROM public.academic_courses WHERE id = NEW.course_id AND scope_id = NEW.scope_id AND is_active AND archived_at IS NULL;
            IF NOT FOUND THEN
                RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'Academic parent course is missing or inactive';
            END IF;
            PERFORM 1 FROM public.academic_sections WHERE id = NEW.section_id AND term_id = NEW.term_id AND scope_id = NEW.scope_id AND is_active AND archived_at IS NULL;
            IF NOT FOUND THEN
                RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'Academic parent section is missing or inactive';
            END IF;
        END IF;
    END IF;
    IF TG_TABLE_NAME = 'academic_course_offerings' THEN
        PERFORM 1 FROM public.academic_courses c, public.academic_sections s
        WHERE c.id = NEW.course_id AND s.id = NEW.section_id
          AND NEW.identity_key = c.identity_code || '::' || s.identity_code;
        IF NOT FOUND THEN
            RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'Offering identity key does not match its parents';
        END IF;
    END IF;
    RETURN NEW;
END $$
"""

CALENDAR_SQL = """
CREATE FUNCTION public.academic_4c_calendar_guard() RETURNS trigger
LANGUAGE plpgsql VOLATILE SET search_path = pg_catalog, public AS $$
BEGIN
    -- AFTER STATEMENT sees the whole command; VOLATILE queries use fresh RC snapshots
    -- after the shared write gate, including another writer's just-committed children.
    IF EXISTS (
        SELECT 1 FROM public.academic_terms t JOIN public.academic_years y ON y.id = t.year_id
        WHERE (t.calendar_status = 'confirmed' AND y.calendar_status <> 'confirmed')
           OR (t.start_date IS NOT NULL AND (y.start_date IS NULL OR y.end_date IS NULL
                OR t.start_date < y.start_date OR t.end_date > y.end_date))
    ) THEN
        RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'Academic term dates must be contained in their academic year';
    END IF;
    IF EXISTS (SELECT 1 FROM public.academic_terms t WHERE NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_timezone_names z WHERE z.name = t.timezone
    )) THEN
        RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'Academic term timezone is unknown';
    END IF;
    RETURN NULL;
END $$
"""


def upgrade():
    op.execute("""DO $$ BEGIN
        IF current_schema() <> 'public' THEN
            RAISE EXCEPTION 'Academic foundation requires explicit public schema';
        END IF;
    END $$""")
    for statement in TABLE_DDL:
        op.execute(statement)
    for statement in (WRITE_LOCK_SQL, ROW_GUARD_SQL, CALENDAR_SQL):
        op.execute(statement)
    for table, keys in TABLE_KEYS.items():
        arguments = ", ".join("'" + key + "'" for key in keys)
        op.execute(f"CREATE TRIGGER academic_write_gate BEFORE INSERT OR UPDATE OR DELETE OR TRUNCATE ON public.{table} FOR EACH STATEMENT EXECUTE FUNCTION public.academic_4c_write_lock()")
        op.execute(f"CREATE TRIGGER academic_row_guard BEFORE INSERT OR UPDATE OR DELETE ON public.{table} FOR EACH ROW EXECUTE FUNCTION public.academic_4c_row_guard({arguments})")
    for table in ("academic_years", "academic_terms"):
        op.execute(f"CREATE TRIGGER academic_calendar_guard AFTER INSERT OR UPDATE ON public.{table} FOR EACH STATEMENT EXECUTE FUNCTION public.academic_4c_calendar_guard()")


def downgrade():
    # Lock all seven before checking emptiness: no check/drop insertion race.
    tables = ", ".join("public." + table for table in TABLE_KEYS)
    op.execute(f"LOCK TABLE {tables} IN ACCESS EXCLUSIVE MODE")
    for table in TABLE_KEYS:
        op.execute(f"""DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM public.{table}) THEN
                RAISE EXCEPTION 'Populated academic downgrade refused; preserve records';
            END IF;
        END $$""")
    for table in reversed(TABLE_KEYS):
        op.execute(f"DROP TABLE public.{table}")
    for name in ("calendar_guard", "row_guard", "write_lock"):
        op.execute(f"DROP FUNCTION public.academic_4c_{name}()")
