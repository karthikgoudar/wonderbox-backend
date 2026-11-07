import os
import sys
from logging.config import fileConfig
from pathlib import Path

# Add project root to sys.path so app modules can be discovered
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from app.config.settings import settings
from app.db.base import Base

# Explicitly import all SQLAlchemy models so Base.metadata contains the full schema
from app.models.user import User
from app.models.auth_provider import AuthProvider
from app.models.child import Child
from app.models.device import Device
from app.models.sticker import Sticker
from app.models.favorite import Favorite
from app.models.daily_usage import DailyUsage
from app.models.subscription import Subscription
from app.models.notification import Notification
from app.models.usage import Usage
from app.models.analytics_event import AnalyticsEvent
from app.models.company_limit import CompanyLimit
from app.models.bundle import (
    Bundle,
    BundleCategory,
    BundleItem,
    BundleLevel,
    UserBundle,
    BundleItemUsage,
)
from app.models.preset_sticker import PresetSticker
from app.models.story import Story, StoryScene
from app.models.user_story_progress import UserStoryProgress

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for 'autogenerate' support
target_metadata = Base.metadata


def get_database_url() -> str:
    """
    Resolve and normalize the database URL.
    Handles Heroku / Render / Supabase 'postgres://' format by upgrading to 'postgresql://'.
    """
    url = os.getenv("DATABASE_URL") or settings.DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    """
    url = get_database_url()
    is_sqlite = url.startswith("sqlite")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=is_sqlite,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    url = get_database_url()
    is_sqlite = url.startswith("sqlite")

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
