"""New isolated Phase 4C target only. Importing this module never connects."""
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

EXPECTED_DATABASE = "ccs_ga_phase4c_test"
EXPECTED_ROLE = "ccs_ga_phase4c_tester"
APPROVAL = "I_APPROVE_ISOLATED_PHASE4C_POSTGRESQL_TESTS"


class SafetyError(RuntimeError):
    pass


def designated_url(environ=None):
    environment = os.environ if environ is None else environ
    raw = environment.get("PHASE4C_TEST_DATABASE_URL")
    try:
        url = make_url(raw) if raw else None
        valid = (url is not None and url.drivername in {"postgresql", "postgresql+psycopg2"}
                 and url.host == "127.0.0.1" and url.port == 5432
                 and url.database == EXPECTED_DATABASE and url.username == EXPECTED_ROLE
                 and not url.query)
    except Exception:
        valid = False
    if not valid:
        raise SafetyError("Exact Phase 4C database/role/host/port gate rejected; URL withheld.")
    return url


def inspect_empty_test_database(*, environ=None, allow_connect=False):
    environment = os.environ if environ is None else environ
    if not allow_connect or environment.get("PHASE4C_POSTGRESQL_APPROVAL") != APPROVAL:
        raise SafetyError("Live Phase 4C inspection is not explicitly enabled; no connection attempted.")
    url = designated_url(environment)
    engine = None
    try:
        engine = create_engine(url, hide_parameters=True, connect_args={
            "connect_timeout": 5,
            "options": "-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=2000",
        })
        with engine.connect() as c:
            row = c.execute(text("""SELECT current_database() AS database, current_user AS role,
                host(inet_server_addr()) AS host, inet_server_port() AS port,
                current_schema() AS schema, current_setting('transaction_read_only') AS read_only,
                pg_get_userbyid(d.datdba) AS owner,
                r.rolsuper, r.rolcreatedb, r.rolcreaterole, r.rolreplication, r.rolbypassrls
                FROM pg_roles r JOIN pg_database d ON d.datname = current_database()
                WHERE r.rolname = current_user""")).mappings().one()
            if (row["database"] != EXPECTED_DATABASE or row["role"] != EXPECTED_ROLE
                    or row["owner"] != EXPECTED_ROLE or row["host"] != "127.0.0.1"
                    or row["port"] != 5432 or row["schema"] != "public" or row["read_only"] != "on"
                    or any(row[key] for key in ("rolsuper", "rolcreatedb", "rolcreaterole", "rolreplication", "rolbypassrls"))):
                raise SafetyError("Connected identity/owner/privileges rejected; no writes permitted.")
            if c.execute(text("SELECT 1 FROM pg_auth_members WHERE member = (SELECT oid FROM pg_roles WHERE rolname = current_user)")).first():
                raise SafetyError("Role memberships rejected; no writes permitted.")
            schemas = c.execute(text("SELECT nspname, pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname NOT IN ('pg_catalog','information_schema') AND nspname NOT LIKE 'pg_%'")).all()
            if len(schemas) != 1 or schemas[0][0] != "public" or schemas[0][1] not in {EXPECTED_ROLE, "pg_database_owner"}:
                raise SafetyError("Unexpected schema/ownership; no writes permitted.")
            # Inspect relations, routines, standalone types, extensions and default privileges.
            for query in (
                "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_%'",
                "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_%'",
                "SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_%'",
                "SELECT 1 FROM pg_extension WHERE extname <> 'plpgsql'",
                "SELECT 1 FROM pg_default_acl",
            ):
                if c.execute(text(query)).first():
                    raise SafetyError("Target is not pristine; no migration, reset or cleanup permitted.")
            # No third-party roles may hold database or public-schema privileges. PUBLIC
            # CONNECT/TEMP is accepted, but PUBLIC CREATE on public is not.
            if c.execute(text("""SELECT 1 FROM pg_namespace n,
                LATERAL aclexplode(COALESCE(n.nspacl, acldefault('n', n.nspowner))) a
                WHERE n.nspname='public' AND
                ((a.grantee=0 AND a.privilege_type='CREATE') OR
                 (a.grantee<>0 AND a.grantee NOT IN
                  (SELECT oid FROM pg_roles WHERE rolname IN (:role,'pg_database_owner'))))"""), {"role": EXPECTED_ROLE}).first():
                raise SafetyError("Unexpected public-schema privileges; no writes permitted.")
            if c.execute(text("""SELECT 1 FROM pg_database d,
                LATERAL aclexplode(COALESCE(d.datacl, acldefault('d', d.datdba))) a
                WHERE d.datname=current_database() AND
                ((a.grantee=0 AND a.privilege_type='CREATE') OR
                 (a.grantee<>0 AND a.grantee<>
                  (SELECT oid FROM pg_roles WHERE rolname=:role)))"""), {"role": EXPECTED_ROLE}).first():
                raise SafetyError("Unexpected database grants; no writes permitted.")
            return {"database": EXPECTED_DATABASE, "role": EXPECTED_ROLE,
                    "read_only_preflight": True, "empty": True, "writes_performed": False}
    except SafetyError:
        raise
    except Exception:
        raise SafetyError("Phase 4C preflight failed; connection details withheld; no writes attempted.") from None
    finally:
        if engine is not None: engine.dispose()
