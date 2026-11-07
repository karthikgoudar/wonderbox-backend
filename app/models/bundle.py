import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy import types
from sqlalchemy.orm import relationship

from app.db.base import Base


# ---------------------------------------------------------------------------
# Portable UUID type — String(36) on SQLite, native UUID on PostgreSQL
# ---------------------------------------------------------------------------
class _UUID(types.TypeDecorator):
    impl = types.String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return str(value) if value is not None else None

    def process_result_value(self, value, dialect):
        return str(value) if value is not None else None


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Bundle  (top-level content container)
# ---------------------------------------------------------------------------
class Bundle(Base):
    """
    A bundle is the top-level unit of content (e.g. "Farm Animals Pack").
    It can optionally have categories, levels, and/or items directly.
    """
    __tablename__ = "bundles"

    id          = Column(_UUID,    primary_key=True, default=_uuid)
    slug        = Column(String,   nullable=False, unique=True, index=True)  # URL-safe stable ID
    name        = Column(String,   nullable=False, index=True)
    description = Column(String,   nullable=True)
    type        = Column(String,   nullable=False, index=True)   # sticker|story|mixed|game
    age_group   = Column(String,   nullable=True,  index=True)
    language    = Column(String,   nullable=False, default="en", index=True)
    is_free     = Column(Boolean,  nullable=False, default=True)
    price_paise = Column(Integer,  nullable=True)                # smallest currency unit
    creator_id  = Column(Integer,  ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    version     = Column(Integer,  nullable=False, default=1)
    is_published = Column(Boolean, nullable=False, default=False, index=True)
    thumbnail_url = Column(String, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    categories   = relationship(
        "BundleCategory", back_populates="bundle",
        cascade="all, delete-orphan", order_by="BundleCategory.order_index",
    )
    # All items whose bundle_id points here (includes items at any level)
    all_items    = relationship(
        "BundleItem", back_populates="bundle",
        cascade="all, delete-orphan", foreign_keys="BundleItem.bundle_id",
    )
    user_bundles = relationship("UserBundle", back_populates="bundle", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("type IN ('sticker','story','mixed','game')", name="ck_bundles_type"),
    )


# ---------------------------------------------------------------------------
# BundleCategory  (optional grouping inside a bundle)
# ---------------------------------------------------------------------------
class BundleCategory(Base):
    """Optional mid-tier grouping. A bundle may have zero or more categories."""
    __tablename__ = "bundle_categories"

    id            = Column(_UUID,    primary_key=True, default=_uuid)
    bundle_id     = Column(_UUID,    ForeignKey("bundles.id", ondelete="CASCADE"), nullable=False, index=True)
    name          = Column(String,   nullable=False, index=True)
    description   = Column(String,   nullable=True)
    thumbnail_url = Column(String,   nullable=True)
    order_index   = Column(Integer,  nullable=False, default=0)
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    bundle = relationship("Bundle", back_populates="categories")
    levels = relationship(
        "BundleLevel", back_populates="category",
        cascade="all, delete-orphan", order_by="BundleLevel.order_index",
    )
    items  = relationship(
        "BundleItem", back_populates="category",
        foreign_keys="BundleItem.category_id", order_by="BundleItem.order_index",
    )

    __table_args__ = (
        Index("ix_bundle_categories_bundle_order", "bundle_id", "order_index"),
    )


# ---------------------------------------------------------------------------
# BundleLevel  (optional sub-grouping inside a category)
# ---------------------------------------------------------------------------
class BundleLevel(Base):
    """
    Optional 3rd tier (e.g. difficulty levels).
    Always belongs to a bundle; category_id is nullable so a level can
    live directly under a bundle without a category.
    """
    __tablename__ = "bundle_levels"

    id          = Column(_UUID,    primary_key=True, default=_uuid)
    bundle_id   = Column(_UUID,    ForeignKey("bundles.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(_UUID,    ForeignKey("bundle_categories.id", ondelete="CASCADE"), nullable=True, index=True)
    name        = Column(String,   nullable=False)
    description = Column(String,   nullable=True)
    order_index = Column(Integer,  nullable=False, default=0)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    category = relationship("BundleCategory", back_populates="levels")
    items    = relationship(
        "BundleItem", back_populates="level",
        foreign_keys="BundleItem.level_id", order_by="BundleItem.order_index",
    )

    __table_args__ = (
        Index("ix_bundle_levels_bundle", "bundle_id"),
        Index("ix_bundle_levels_category_order", "category_id", "order_index"),
    )


# ---------------------------------------------------------------------------
# BundleItem  (atomic content unit — sticker, story, game)
# ---------------------------------------------------------------------------
class BundleItem(Base):
    """
    Flexible placement:
      - bundle only   : bundle_id set, category_id=NULL, level_id=NULL
      - in category   : bundle_id set, category_id set,  level_id=NULL
      - in level      : bundle_id set, category_id set,  level_id set

    Items always carry bundle_id so they can be fetched without joins.
    """
    __tablename__ = "bundle_items"

    id            = Column(_UUID,    primary_key=True, default=_uuid)
    bundle_id     = Column(_UUID,    ForeignKey("bundles.id",           ondelete="CASCADE"), nullable=False, index=True)
    category_id   = Column(_UUID,    ForeignKey("bundle_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    level_id      = Column(_UUID,    ForeignKey("bundle_levels.id",     ondelete="SET NULL"), nullable=True, index=True)
    type          = Column(String,   nullable=False, index=True)  # sticker|story|game
    title         = Column(String,   nullable=False)
    description   = Column(String,   nullable=True)
    thumbnail_url = Column(String,   nullable=True)
    asset_path    = Column(String,   nullable=True)               # local/CDN path to the asset
    extra_data    = Column(JSON,     nullable=False, default=dict) # type-specific payload
    order_index   = Column(Integer,  nullable=False, default=0)
    is_premium    = Column(Boolean,  nullable=False, default=False)
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    bundle   = relationship("Bundle",         back_populates="all_items",  foreign_keys=[bundle_id])
    category = relationship("BundleCategory", back_populates="items",      foreign_keys=[category_id])
    level    = relationship("BundleLevel",    back_populates="items",      foreign_keys=[level_id])
    usage    = relationship("BundleItemUsage", back_populates="item",       cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("type IN ('sticker','story','game')", name="ck_bundle_items_type"),
        Index("ix_bundle_items_bundle",          "bundle_id"),
        Index("ix_bundle_items_category_order",  "category_id", "order_index"),
        Index("ix_bundle_items_level_order",     "level_id",    "order_index"),
    )


# ---------------------------------------------------------------------------
# UserBundle  (offline download tracking)
# ---------------------------------------------------------------------------
class UserBundle(Base):
    """Records which version of a bundle a user has downloaded locally."""
    __tablename__ = "user_bundles"

    id           = Column(_UUID,    primary_key=True, default=_uuid)
    user_id      = Column(Integer,  ForeignKey("users.id",   ondelete="CASCADE"), nullable=False, index=True)
    bundle_id    = Column(_UUID,    ForeignKey("bundles.id", ondelete="CASCADE"), nullable=False, index=True)
    local_path   = Column(String,   nullable=True)   # on-device path after extraction
    version      = Column(Integer,  nullable=False, default=1)
    downloaded_at = Column(DateTime, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)

    bundle = relationship("Bundle", back_populates="user_bundles")

    __table_args__ = (
        UniqueConstraint("user_id", "bundle_id", name="uq_user_bundles_user_bundle"),
    )


# ---------------------------------------------------------------------------
# BundleItemUsage  (analytics — print / play events)
# ---------------------------------------------------------------------------
class BundleItemUsage(Base):
    """Append-only log of user interactions with individual items."""
    __tablename__ = "bundle_item_usage"

    id        = Column(_UUID,    primary_key=True, default=_uuid)
    user_id   = Column(Integer,  ForeignKey("users.id",        ondelete="SET NULL"), nullable=True, index=True)
    item_id   = Column(_UUID,    ForeignKey("bundle_items.id", ondelete="CASCADE"),  nullable=False, index=True)
    device_id = Column(Integer,  ForeignKey("devices.id",      ondelete="SET NULL"), nullable=True)
    action    = Column(String,   nullable=False, default="use") # print | play | use
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    item = relationship("BundleItem", back_populates="usage")
