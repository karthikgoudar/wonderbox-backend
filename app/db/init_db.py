# TODO: Replace with Redis before scaling

import logging

from sqlalchemy import inspect, text

from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine

# Explicit model imports to register metadata
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
from app.models.bundle import Bundle, BundleCategory, BundleItem, BundleLevel, UserBundle, BundleItemUsage
from app.models.preset_sticker import PresetSticker
from app.models.story import Story, StoryScene
from app.models.user_story_progress import UserStoryProgress


logger = logging.getLogger(__name__)


def _ensure_device_token_column() -> None:
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    if "devices" not in tables:
        return

    columns = {col["name"] for col in inspector.get_columns("devices")}
    if "token" in columns:
        return

    logger.info("Adding missing devices.token column for backward compatibility")
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE devices ADD COLUMN token VARCHAR"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_devices_token ON devices (token)"))


def init_db():
    """
    Initialize database.
    Create all tables if they do not exist.
    """
    logger.info("Creating tables if not exist...")

    # Idempotent: creates only missing tables.
    Base.metadata.create_all(bind=engine)
    _ensure_device_token_column()

    # Optional default data insertion for global limits.
    with Session(engine) as db:
        has_limits = db.query(CompanyLimit).first()
        if not has_limits:
            db.add(CompanyLimit(free_daily_limit=5, free_monthly_limit=100))
            db.commit()

    logger.info("Database initialized successfully")
