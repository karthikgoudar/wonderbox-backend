import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Resolve and normalize database URL
raw_database_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
if raw_database_url.startswith("postgres://"):
    DATABASE_URL = raw_database_url.replace("postgres://", "postgresql://", 1)
else:
    DATABASE_URL = raw_database_url

# Configure engine arguments based on dialect
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Production settings for PostgreSQL / relational DBs
    engine_kwargs.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,
            "pool_recycle": 300,
        }
    )

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    FastAPI dependency that yields a SQLAlchemy database session
    and ensures it is closed after request handling.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
