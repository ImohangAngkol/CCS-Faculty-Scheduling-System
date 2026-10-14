"""Identity-only database access. Startup never creates tables or runs migrations."""
import os
from functools import lru_cache
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker


@lru_cache(maxsize=1)
def identity_engine():
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith(("postgresql://", "postgresql+psycopg2://")):
        raise HTTPException(503, "Identity database is not configured. Follow Phase 4A local setup.")
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5,
                         "options": "-c statement_timeout=5000 -c lock_timeout=5000"},
                         hide_parameters=True)


def get_identity_db():
    try:
        with sessionmaker(identity_engine())() as db:
            yield db
    except SQLAlchemyError as error:
        raise HTTPException(503, "Identity database unavailable or migrations missing. Check backend configuration.") from error
