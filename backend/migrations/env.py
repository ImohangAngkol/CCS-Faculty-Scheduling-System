"""Explicit Alembic command only. Credentials never written into alembic.ini."""
import os
from alembic import context
from sqlalchemy import create_engine
from identity_models import Base
import academic_models  # noqa: F401 -- register additive tables; no engine or GA imports

from confirmation_models import ConfirmationBase
from adjustment_models import AdjustmentBase
target_metadata = [Base.metadata, ConfirmationBase.metadata, AdjustmentBase.metadata]

config = context.config
connection = config.attributes.get("connection")
url = None
if connection is None:
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith(("postgresql://", "postgresql+psycopg2://")):
        raise RuntimeError("Set DATABASE_URL to an explicitly selected PostgreSQL identity database.")

if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
elif connection is not None:
    # Explicit caller-owned connection (e.g. exact-gated synthetic migration tests).
    # No URL fallback, engine creation, or caller transaction commit here.
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    with create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 5}).connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
