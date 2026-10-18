"""Independent browser-only target. Importing this module never connects or writes."""
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from tests.phase4b_database_safety import SafetyError

BROWSER_DATABASE = "ccs_ga_phase4b_browser_test"
BROWSER_ROLE = "ccs_ga_phase4b_browser_tester"
BROWSER_VARIABLE = "PHASE4B_BROWSER_DATABASE_URL"


def designated_browser_url(environ=None):
    raw = (os.environ if environ is None else environ).get(BROWSER_VARIABLE)
    if not raw:
        raise SafetyError(f"{BROWSER_VARIABLE} missing; no connection attempted.")
    try:
        url = make_url(raw)
        valid = (url.drivername in {"postgresql", "postgresql+psycopg2"}
                 and url.database == BROWSER_DATABASE and url.username == BROWSER_ROLE
                 and url.host == "127.0.0.1" and url.port == 5432 and not url.query)
    except Exception:
        valid = False
    if not valid:
        raise SafetyError("Browser target rejected; only the exact browser database/role/IPv4/port are permitted. URL withheld.")
    return url


def inspect_empty_browser_database(url):
    # Validate even caller-supplied URL objects; never accept the original test DB.
    try:
        designated_browser_url({BROWSER_VARIABLE: url.render_as_string(hide_password=False)})
    except SafetyError:
        raise
    except Exception:
        raise SafetyError("Invalid browser URL object; no connection attempted.") from None
    engine = None
    try:
        engine = create_engine(url, hide_parameters=True, connect_args={
            "connect_timeout": 5,
            "options": "-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=2000",
        })
        with engine.connect() as db:
            row = db.execute(text(
                "SELECT current_database() AS database, current_user AS role, "
                "host(inet_server_addr()) AS host, inet_server_port() AS port, "
                "current_schema() AS schema, current_setting('transaction_read_only') AS read_only, "
                "current_setting('server_version') AS server_version, "
                "rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls, "
                "pg_get_userbyid(d.datdba) AS owner, "
                "has_schema_privilege(current_user, 'public', 'CREATE') AS can_create "
                "FROM pg_roles r CROSS JOIN pg_database d "
                "WHERE r.rolname=current_user AND d.datname=current_database()"
            )).mappings().one()
            if (row["database"] != BROWSER_DATABASE or row["role"] != BROWSER_ROLE
                    or row["owner"] != BROWSER_ROLE or row["host"] != "127.0.0.1"
                    or row["port"] != 5432 or row["schema"] != "public"
                    or row["read_only"] != "on" or row["can_create"] is not True
                    or any(row[key] is not False for key in (
                        "rolsuper", "rolcreatedb", "rolcreaterole", "rolreplication", "rolbypassrls"))):
                raise SafetyError("Browser server identity/ownership/privilege/read-only gate failed; no writes permitted.")
            schemas = db.execute(text(
                "SELECT nspname FROM pg_namespace WHERE nspname <> 'information_schema' "
                "AND nspname !~ '^pg_'"
            )).scalars().all()
            if schemas != ["public"]:
                raise SafetyError("Unexpected browser database schemas; no migration/reset permitted.")
            # Check more than relations: unexpected functions/types/extensions
            # also indicate a previously used target, even in an empty public schema.
            occupied = db.execute(text(
                "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname <> 'information_schema' AND n.nspname !~ '^pg_' "
                "UNION ALL SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
                "WHERE n.nspname <> 'information_schema' AND n.nspname !~ '^pg_' "
                "UNION ALL SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace "
                "WHERE n.nspname <> 'information_schema' AND n.nspname !~ '^pg_' "
                "UNION ALL SELECT 1 FROM pg_depend d JOIN pg_namespace n ON n.oid=d.refobjid "
                "WHERE d.refclassid='pg_namespace'::regclass "
                "AND n.nspname <> 'information_schema' AND n.nspname !~ '^pg_' "
                "UNION ALL SELECT 1 FROM pg_event_trigger "
                "UNION ALL SELECT 1 FROM pg_publication "
                "UNION ALL SELECT 1 FROM pg_extension WHERE extname <> 'plpgsql' LIMIT 1"
            )).first()
            if occupied is not None:
                raise SafetyError("Browser database is not empty; no migration/reset permitted.")
            return {"database": BROWSER_DATABASE, "role": BROWSER_ROLE, "host": row["host"],
                    "port": row["port"], "schema": "public", "owner": row["owner"],
                    "server_version": row["server_version"], "read_only_preflight": True,
                    "empty": True, "migration_before": None}
    except SafetyError:
        raise
    except Exception:
        raise SafetyError("Browser PostgreSQL read-only preflight failed; private diagnostics withheld.") from None
    finally:
        if engine is not None:
            engine.dispose()
