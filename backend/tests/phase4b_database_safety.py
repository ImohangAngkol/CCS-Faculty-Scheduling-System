"""One-shot PostgreSQL acceptance gate; no DATABASE_URL fallback or cleanup DDL."""
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

EXPECTED_DATABASE = "ccs_ga_phase4b_test"
EXPECTED_ROLE = "ccs_ga_phase4b_tester"


class SafetyError(RuntimeError):
    pass


def designated_url(environ=None):
    raw = (os.environ if environ is None else environ).get("PHASE4B_TEST_DATABASE_URL")
    if not raw:
        raise SafetyError("PHASE4B_TEST_DATABASE_URL is missing; no database connection attempted.")
    try:
        url = make_url(raw)
        valid = (url.drivername in {"postgresql", "postgresql+psycopg2"}
                 and url.database == EXPECTED_DATABASE and url.username == EXPECTED_ROLE
                 and url.host == "127.0.0.1" and url.port == 5432 and not url.query)
    except Exception:
        valid = False
    if not valid:
        raise SafetyError("Disposable database URL failed the exact database/role/host/port gate; URL withheld.")
    return url


def inspect_empty_database(url):
    """Every connection starts read-only, before any catalog inspection."""
    engine = None
    try:
        engine = create_engine(url, hide_parameters=True, connect_args={
            "connect_timeout": 5,
            "options": "-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=2000",
        })
        with engine.connect() as connection:
            row = connection.execute(text(
                "SELECT current_database() AS database, current_user AS role, "
                "host(inet_server_addr()) AS host, inet_server_port() AS port, "
                "current_schema() AS schema, current_setting('transaction_read_only') AS read_only, "
                "current_setting('server_version') AS server_version, "
                "rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = current_user"
            )).mappings().one()
            if (row["database"] != EXPECTED_DATABASE or row["role"] != EXPECTED_ROLE
                    or row["host"] != "127.0.0.1" or row["port"] != 5432
                    or row["schema"] != "public" or row["read_only"] != "on"
                    or row["rolsuper"] or row["rolcreatedb"] or row["rolcreaterole"]):
                raise SafetyError("Connected server identity/privileges failed the safety gate; no writes permitted.")
            relations = connection.execute(text(
                "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname NOT IN ('pg_catalog','information_schema') "
                "AND n.nspname NOT LIKE 'pg_%' AND c.relkind IN ('r','p','v','m','S','f')"
            )).all()
            if relations:
                # Never infer approval from a plausible table/name prefix.
                # A previously executed acceptance database needs owner review.
                raise SafetyError("Disposable database is not empty. Stop for explicit review of existing data; no migration/reset attempted.")
            return {"database": row["database"], "role": row["role"], "host": row["host"],
                    "port": row["port"], "schema": row["schema"], "server_version": row["server_version"],
                    "read_only_preflight": True, "tables_before": inspect(connection).get_table_names(),
                    "migration_before": None, "elevated_role_privileges": False}
    except SafetyError:
        raise
    except Exception:
        raise SafetyError("Disposable PostgreSQL preflight failed; connection details withheld. No migration or write attempted.") from None
    finally:
        if engine is not None:
            engine.dispose()
