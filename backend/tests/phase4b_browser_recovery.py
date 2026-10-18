"""Explicit browser-only recovery. Import is inert; never selects stored secrets.

The original empty-database gate is deliberately unchanged. This separate gate
accepts only the pristine, already-seeded 4a_0001 browser fixture.
"""
from contextlib import contextmanager
import re
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String, Uuid, create_engine, inspect, text

from tests.phase4b_browser_safety import BROWSER_DATABASE, BROWSER_ROLE, BROWSER_VARIABLE, designated_browser_url
from tests.phase4b_database_safety import SafetyError

LOCK_KEY = 414002
ADMIN = "browser-admin@test.invalid"
REVISION = "4a_0001"
IDENTITIES = {
    (UUID("befabf1e-9ca8-5a2b-8761-08ed21395626"), "Browser Faculty 0", "Browser Synthetic Faculty 0"),
    (UUID("e7755980-4ff1-5e4f-bee6-20484c45b6b4"), "Browser Faculty 1", "Browser Synthetic Faculty 1"),
}
# name -> (type, nullable). No server defaults, generated or identity columns.
COLUMNS = {
    "alembic_version": {"version_num": ("varchar:32", False)},
    "faculty_identities": {"id": ("uuid", False), "display_code": ("varchar:100", False), "name": ("varchar:200", False)},
    "users": {"id": ("uuid", False), "username": ("varchar:254", False), "password_hash": ("varchar:512", False),
              "role": ("varchar:20", False), "faculty_id": ("uuid", True), "is_active": ("boolean", False),
              "created_at": ("timestamptz", False), "updated_at": ("timestamptz", False)},
    "login_sessions": {"id": ("uuid", False), "token_hash": ("varchar:64", False), "user_id": ("uuid", False),
                       "csrf_token": ("varchar:64", False), "expires_at": ("timestamptz", False), "created_at": ("timestamptz", False)},
}
CHECKS = {
    "ck_user_role": "role IN ('admin', 'faculty')",
    "ck_user_binding": "(role = 'admin' AND faculty_id IS NULL) OR (role = 'faculty' AND faculty_id IS NOT NULL)",
    "ck_username_lower": "username = lower(username)",
}


def check_tree(source):
    """Parse the small supported CHECK grammar, preserving boolean grouping.

    PG reflects IN as = ANY(ARRAY[...]) and inserts text casts/parentheses.
    Unknown syntax fails closed, rather than stripping SQL into a loose match.
    """
    pattern = re.compile(r"\s+|'(?:''|[^'])*'|\"[a-z_]+\"|[a-z_]+|::|[(),=\[\]]", re.I)
    tokens, position = [], 0
    for match in pattern.finditer(source):
        if match.start() != position:
            raise SafetyError("Unsupported browser CHECK expression.")
        position = match.end()
        token = match.group()
        if not token.isspace():
            tokens.append(token if token.startswith("'") else token.lower().strip('"'))
    if position != len(source):
        raise SafetyError("Unsupported browser CHECK expression.")
    cursor = 0

    def peek(): return tokens[cursor] if cursor < len(tokens) else None
    def take(wanted=None):
        nonlocal cursor
        token = peek()
        if token is None or (wanted is not None and token != wanted):
            raise SafetyError("Unsupported browser CHECK expression.")
        cursor += 1
        return token
    def primary():
        token = take()
        if token == "(":
            value = boolean_or(); take(")")
        elif token.startswith("'"):
            value = ("string", token[1:-1].replace("''", "'"))
        elif token in {"lower", "any"}:
            take("("); value = (token, boolean_or()); take(")")
        elif token == "array":
            take("["); values = [boolean_or()]
            while peek() == ",": take(","); values.append(boolean_or())
            take("]"); value = ("array", tuple(values))
        elif token in {"role", "faculty_id", "username"}:
            value = ("column", token)
        else:
            raise SafetyError("Unsupported browser CHECK expression.")
        while peek() == "::":
            take("::"); cast = take()
            if cast == "character": take("varying")
            elif cast != "text": raise SafetyError("Unsupported browser CHECK cast.")
            if peek() == "[": take("["); take("]")
        return value
    def comparison():
        left = primary()
        if peek() == "=":
            take("="); right = primary()
            if right[0] == "any" and right[1][0] == "array":
                return ("in", left, right[1][1])
            return ("equal", left, right)
        if peek() == "in":
            take("in"); take("("); values = [primary()]
            while peek() == ",": take(","); values.append(primary())
            take(")"); return ("in", left, tuple(values))
        if peek() == "is":
            take("is"); negated = peek() == "not"
            if negated: take("not")
            take("null"); return ("not_null" if negated else "null", left)
        return left
    def boolean_and():
        values = [comparison()]
        while peek() == "and": take("and"); values.append(comparison())
        return values[0] if len(values) == 1 else ("and", tuple(values))
    def boolean_or():
        values = [boolean_and()]
        while peek() == "or": take("or"); values.append(boolean_and())
        return values[0] if len(values) == 1 else ("or", tuple(values))
    result = boolean_or()
    if cursor != len(tokens):
        raise SafetyError("Unsupported browser CHECK expression.")
    return result


def validate_url(url):
    try:
        designated_browser_url({BROWSER_VARIABLE: url.render_as_string(hide_password=False)})
    except Exception:
        raise SafetyError("Recovery target rejected; private URL withheld.") from None


def verify_server(db, *, read_only="on"):
    row = db.execute(text(
        "SELECT current_database() AS database, current_user AS role, host(inet_server_addr()) AS host, "
        "inet_server_port() AS port, current_schema() AS schema, current_setting('transaction_read_only') AS read_only, "
        "rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls, "
        "pg_get_userbyid(d.datdba) AS owner, has_schema_privilege(current_user,'public','CREATE') AS can_create "
        "FROM pg_roles r CROSS JOIN pg_database d WHERE r.rolname=current_user AND d.datname=current_database()"
    )).mappings().one()
    expected = dict(database=BROWSER_DATABASE, role=BROWSER_ROLE, host="127.0.0.1", port=5432,
                    schema="public", read_only=read_only, owner=BROWSER_ROLE)
    if (any(row[key] != value for key, value in expected.items()) or row["can_create"] is not True
            or any(row[key] is not False for key in ("rolsuper", "rolcreatedb", "rolcreaterole", "rolreplication", "rolbypassrls"))):
        raise SafetyError("Browser recovery server identity/privilege gate failed.")


def _kind(column):
    value = column["type"]
    if isinstance(value, Uuid): return "uuid"
    if isinstance(value, String): return f"varchar:{value.length}" if value.__class__.__name__.upper() == "VARCHAR" else "unsupported"
    if isinstance(value, Boolean): return "boolean"
    if isinstance(value, DateTime) and value.timezone: return "timestamptz"
    return "unsupported"


def verify_schema(db):
    catalog = inspect(db)
    schemas = {name for name in catalog.get_schema_names() if name != "information_schema" and not name.startswith("pg_")}
    if schemas != {"public"} or set(catalog.get_table_names(schema="public")) != set(COLUMNS):
        raise SafetyError("Unexpected recovery schema/tables.")
    # Reject programmable/hidden behavior and extra user types as well as tables.
    unexpected = db.execute(text(
        "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
        "WHERE n.nspname <> 'information_schema' AND n.nspname !~ '^pg_' "
        "UNION ALL SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname <> 'information_schema' AND n.nspname !~ '^pg_' "
        "AND (c.relkind NOT IN ('r','i') OR c.relrowsecurity OR c.relforcerowsecurity OR c.relispartition "
        "OR pg_get_userbyid(c.relowner) <> current_user) "
        "UNION ALL SELECT 1 FROM pg_index WHERE NOT indisvalid OR NOT indisready OR NOT indislive "
        "UNION ALL SELECT 1 FROM pg_rewrite r JOIN pg_class c ON c.oid=r.ev_class "
        "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' "
        "UNION ALL SELECT 1 FROM pg_trigger WHERE NOT tgisinternal "
        "UNION ALL SELECT 1 FROM pg_policy "
        "UNION ALL SELECT 1 FROM pg_inherits "
        "UNION ALL SELECT 1 FROM pg_event_trigger "
        "UNION ALL SELECT 1 FROM pg_publication "
        "UNION ALL SELECT 1 FROM pg_extension WHERE extname <> 'plpgsql' "
        "UNION ALL SELECT 1 FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace "
        "WHERE n.nspname='public' AND (c.contype NOT IN ('p','u','f','c','n') OR NOT c.convalidated "
        "OR c.condeferrable OR c.condeferred OR (c.contype IN ('c','n') AND c.connoinherit) "
        "OR to_jsonb(c)->>'conenforced'='false' OR to_jsonb(c)->>'conperiod'='true') "
        "UNION ALL SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace "
        "WHERE n.nspname <> 'information_schema' AND n.nspname !~ '^pg_' AND NOT EXISTS "
        "(SELECT 1 FROM pg_class c WHERE c.relnamespace=n.oid AND c.relname IN "
        "('alembic_version','faculty_identities','users','login_sessions') AND c.relkind='r' "
        "AND ((t.typrelid=c.oid AND t.typtype='c') OR (t.typelem=c.reltype AND t.typcategory='A'))) LIMIT 1"
    )).first()
    if unexpected is not None:
        raise SafetyError("Unexpected recovery schema objects or behavior.")
    # PG18 stores NOT NULL constraints in pg_constraint (contype='n'). Older
    # releases expose nullability through pg_attribute only. Validate, don't
    # mistake the PG18 built-ins for arbitrary extra constraints.
    version = db.execute(text("SELECT current_setting('server_version_num')::int")).scalar_one()
    not_null = db.execute(text(
        "SELECT t.relname, a.attname, c.conname FROM pg_constraint c "
        "JOIN pg_class t ON t.oid=c.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace "
        "JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=c.conkey[1] "
        "WHERE n.nspname='public' AND c.contype='n' AND cardinality(c.conkey)=1"
    )).all()
    expected_not_null = {(table, name, table+'_'+name+'_not_null')
                         for table, columns in COLUMNS.items() for name, (_, nullable) in columns.items() if not nullable} if version >= 180000 else set()
    if set(not_null) != expected_not_null or len(not_null) != len(expected_not_null):
        raise SafetyError("Unexpected recovery NOT NULL constraints.")
    unique_columns = {"alembic_version": [], "faculty_identities": ["display_code"],
                      "users": ["username", "faculty_id"], "login_sessions": ["token_hash"]}
    for table, expected_columns in COLUMNS.items():
        columns = catalog.get_columns(table, schema="public")
        actual = {c["name"]: (_kind(c), c["nullable"]) for c in columns}
        if actual != expected_columns or any(c.get("default") is not None or c.get("computed") or c.get("identity") for c in columns):
            raise SafetyError("Unexpected recovery columns/defaults.")
        pk = catalog.get_pk_constraint(table, schema="public")
        pk_column = "version_num" if table == "alembic_version" else "id"
        pk_name = "alembic_version_pkc" if table == "alembic_version" else table + "_pkey"
        if pk.get("constrained_columns") != [pk_column] or pk.get("name") != pk_name:
            raise SafetyError("Unexpected recovery primary key.")
        uniques = catalog.get_unique_constraints(table, schema="public")
        expected_unique = {(table + "_" + col + "_key", (col,)) for col in unique_columns[table]}
        if ({(u["name"], tuple(u["column_names"])) for u in uniques} != expected_unique
                or len(uniques) != len(expected_unique) or any(any(u.get("dialect_options", {}).values()) for u in uniques)):
            raise SafetyError("Unexpected recovery uniqueness constraints.")
        fks = catalog.get_foreign_keys(table, schema="public")
        expected_fk = []
        if table == "users": expected_fk = [("users_faculty_id_fkey", ("faculty_id",), "faculty_identities", "RESTRICT")]
        if table == "login_sessions": expected_fk = [("login_sessions_user_id_fkey", ("user_id",), "users", "CASCADE")]
        normalized = [(f["name"], tuple(f["constrained_columns"]), f["referred_table"], f.get("options", {}).get("ondelete")) for f in fks]
        if (sorted(normalized) != sorted(expected_fk) or any(f.get("referred_schema") not in (None, "public")
                or f["referred_columns"] != ["id"] or any(v for k, v in f.get("options", {}).items() if k != "ondelete") for f in fks)):
            raise SafetyError("Unexpected recovery foreign keys.")
        checks = catalog.get_check_constraints(table, schema="public")
        expected_checks = CHECKS if table == "users" else {}
        if ({c["name"]: check_tree(c["sqltext"]) for c in checks} != {k: check_tree(v) for k, v in expected_checks.items()}
                or len(checks) != len(expected_checks)):
            raise SafetyError("Unexpected recovery CHECK constraints.")
        indexes = catalog.get_indexes(table, schema="public")
        expected_indexes = {(name, cols, True) for name, cols in expected_unique}
        if table == "login_sessions":
            expected_indexes |= {("ix_login_sessions_" + col, (col,), False) for col in ("user_id", "expires_at")}
        if ({(i["name"], tuple(i["column_names"]), bool(i["unique"])) for i in indexes} != expected_indexes
                or len(indexes) != len(expected_indexes) or any(i.get("column_sorting") or i.get("expressions")
                or any(i.get("dialect_options", {}).values()) for i in indexes)):
            raise SafetyError("Unexpected recovery indexes.")


def verify_contents(db):
    if db.execute(text("SELECT version_num FROM public.alembic_version")).scalars().all() != [REVISION]:
        raise SafetyError("Unexpected browser migration revision; no migration permitted.")
    # Explicit projection: never load password_hash, token_hash or csrf_token.
    identities = set(db.execute(text("SELECT id, display_code, name FROM public.faculty_identities")).all())
    if identities != IDENTITIES:
        raise SafetyError("Unexpected synthetic browser identities.")
    users = db.execute(text("SELECT id, username, role, faculty_id, is_active FROM public.users")).mappings().all()
    if (len(users) != 1 or users[0]["username"] != ADMIN or users[0]["role"] != "admin"
            or users[0]["faculty_id"] is not None or users[0]["is_active"] is not True):
        raise SafetyError("Unexpected synthetic browser accounts.")
    if db.execute(text("SELECT count(*) FROM public.login_sessions")).scalar_one() != 0:
        raise SafetyError("Existing browser sessions; explicit review required, no automatic revocation.")
    return users[0]["id"]


def verify_recovery(db, *, read_only="on"):
    verify_server(db, read_only=read_only)
    verify_schema(db)
    return verify_contents(db)


def inspect_browser_recovery_database(url):
    """Public SELECT-only preflight. No lock, rotation, migration or seeding."""
    validate_url(url)
    engine = None
    try:
        engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 5,
            "options": "-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=2000"})
        with engine.connect() as db:
            db.execution_options(isolation_level="REPEATABLE READ")
            verify_recovery(db)
        return dict(database=BROWSER_DATABASE, revision=REVISION, synthetic_identities=2,
                    active_unbound_administrators=1, sessions=0, recovery_profile_valid=True,
                    read_only_preflight=True)
    except SafetyError:
        raise
    except Exception:
        raise SafetyError("Browser recovery read-only preflight failed; private diagnostics withheld.") from None
    finally:
        if engine is not None: engine.dispose()


@contextmanager
def claim_browser_database(url):
    """Read-only exact-target check, then one session lock for the whole fixture."""
    validate_url(url)
    engine = db = None
    acquired = False
    try:
        engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 5,
            "options": "-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=2000"})
        db = engine.connect()
        verify_server(db)
        acquired = db.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY}).scalar_one() is True
        if not acquired:
            raise SafetyError("Another browser fixture owns this database; no startup permitted.")
        db.rollback()  # session-level advisory lock intentionally survives
        db.info["phase4b_browser_claim"] = True
        yield db
    except SafetyError:
        raise
    except Exception:
        raise SafetyError("Browser ownership/recovery failed; private diagnostics withheld.") from None
    finally:
        if db is not None:
            try:
                db.info.pop("phase4b_browser_claim", None)
                db.rollback()
                if acquired:
                    db.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_KEY})
                    db.rollback()
            finally:
                db.close()
                if engine is not None: engine.dispose()
        elif engine is not None:
            engine.dispose()


def rotate_browser_administrator(db, password, *, approved=False):
    if not approved:
        raise SafetyError("Live browser credential rotation requires explicit recovery approval.")
    if not db.info.get("phase4b_browser_claim"):
        raise SafetyError("Browser recovery requires the owned database lock.")
    from services.auth_service import hash_password
    encoded = hash_password(password)  # new value only, never read the stored hash
    db.rollback()
    with db.begin():
        db.execute(text("SET TRANSACTION READ WRITE"))
        db.execute(text("LOCK TABLE public.alembic_version, public.faculty_identities, public.users, public.login_sessions IN SHARE ROW EXCLUSIVE MODE"))
        admin_id = verify_recovery(db, read_only="off")  # under table locks, immediately before UPDATE
        changed = db.execute(text("UPDATE public.users SET password_hash=:encoded, updated_at=CURRENT_TIMESTAMP "
                                  "WHERE id=:id AND username=:username AND role='admin' AND faculty_id IS NULL AND is_active=true"),
                             {"encoded": encoded, "id": admin_id, "username": ADMIN})
        if changed.rowcount != 1:
            raise SafetyError("Browser administrator rotation did not affect exactly one account.")
    return ADMIN
