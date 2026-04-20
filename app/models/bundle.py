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
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import types
from sqlalchemy.orm import relationship

from app.db.base import Base


# Use UUID that works for both SQLite (dev) and PostgreSQL (prod)
class _UUID(types.TypeDecorator):
    impl = types.String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return str(value)


def _uuid():
    return str(uuid.uuid4())


class Bundle(Base):
    __tablename__ = "bundles"

    id = Column(_UUID, primary_key=True, default=_uuid)
    slug = Column(String, nullable=False, unique=True, index=True)   # stable URL-safe ID
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    type = Column(String, nullable=False, index=True)                # sticker|story|mixed|game
    age_group = Column(String, nullable=True, index=True)
    language = Column(String, nullable=False, default="en", index=True)
    is_free = Column(Boolean, nullable=False, default=True)
    price_paise = Column(Integer, nullable=True)                     # smallest currency unit
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    version = Column(Integer, nullable=False, default=1)
    is_published = Column(Boolean, nullable=False, default=False, index=True)
    thumbnail_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    categories = relationship(
        "BundleCategory",
        back_populates="bundle",
        cascade="all, delete-orphan",
        order_by="BundleCategory.order_index",
    )
    items = relationship(
        "BundleItem",
        primaryjoin="and_(BundleItem.bundle_id == Bundle.id, BundleItem.category_id == None)",
        back_populates="bundle",
        cascade="all, delete-orphan",
        order_by="BundleItem.order_index",
        overlaps="items",
        foreign_keys="BundleItem.bundle_id",
        viewonly=True,
    )
    user_bundles = relationship("UserBundle", back_populates="bundle", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "type IN ('sticker', 'story', 'mixed', 'game')",
            name="ck_bundles_type",
        ),
    )


class BundleCategory(Base):
    __tablename__ = "bundle_categories"

    id = Column(_UUID, primary_key=True, default=_uuid)
    bundle_id = Column(_UUID, ForeignKey("bundles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    bundle = relationship("Bundle", back_populates="categories")
    levels = relationship(
        "BundleLevel",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="BundleLevel.order_index",
    )
    items = relationship(
        "BundleItem",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="BundleItem.order_index",
        foreign_keys="BundleItem.category_id",
    )

    __table_args__ = (
        Index("ix_bundle_categories_bundle_order", "bundle_id", "order_index"),
    )


class BundleLevel(Base):
    __tablename__ = "bundle_levels"

    id = Column(_UUID, primary_key=True, default=_uuid)
    category_id = Column(_UUID, ForeignKey("bundle_categories.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    category = relationship("BundleCategory", back_populates="levels")
    items = relationship(
        "BundleItem",
        back_populates="level",
        cascade="all, delete-orphan",
        order_by="BundleItem.order_index",
        foreign_keys="BundleItem.level_id",
    )

    __table_args__ = (
        Index("ix_bundle_levels_category_order", "category_id", "order_index"),
    )


class BundleItem(Base):
    """
    Flexible hierarchy:
      - Direct under bundle  : bundle_id set, category_id=NULL, level_id=NULL
      - Under category       : bundle_id set, category_id set,  level_id=NULL
      - Under level          : bundle_id set, category_id set,  level_id set
    """
    __tablename__ = "bundle_items"

    id = Column(_UUID, primary_key=True, default=_uuid)
    bundle_id = Column(_UUID, ForeignKey("bundles.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(_UUID, ForeignKey("bundle_categories.id", ondelete="CASCADE"), nullable=True, index=True)
    level_id = Column(_UUID, ForeignKey("bundle_levels.id", ondelete="CASCADE"), nullable=True, index=True)
    type = Column(String, nullable=False, index=True)               # sticker|story|game
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    extra_data = Column(JSON, nullable=False, default=dict)           # type-specific payload
    order_index = Column(Integer, nullable=False, default=0)
    is_premium = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    bundle = relationship(
        "Bundle",
        back_populates=None,
        foreign_keys=[bundle_id],
        overlaps="items,user_bundles",
    )
    category = relationship(
        "BundleCategory",
        back_populates="items",
        foreign_keys=[category_id],
        overlaps="items",
    )
    level = relationship(
        "BundleLevel",
        back_populates="items",
        foreign_keys=[level_id],
        overlaps="items",
    )
    usage = relationship("BundleItemUsage", back_populates="item", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("type IN ('sticker', 'story', 'game')", name="ck_bundle_items_type"),
        Index("ix_bundle_items_bundle", "bundle_id"),
        Index("ix_bundle_items_category_order", "category_id", "order_index"),
        Index("ix_bundle_items_level_order", "level_id", "order_index"),
    )


class UserBundle(Base):
    """Tracks which bundles a user has downloaded and the version they have."""
    __tablename__ = "user_bundles"

    id = Column(_UUID, primary_key=True, default=_uuid)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bundle_id = Column(_UUID, ForeignKey("bundles.id", ondelete="CASCADE"), nullable=False, index=True)
    downloaded_version = Column(Integer, nullable=False, default=1)
    is_downloaded = Column(Boolean, nullable=False, default=False)
    downloaded_at = Column(DateTime, nullable=True)
    last_opened_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    bundle = relationship("Bundle", back_populates="user_bundles")

    __table_args__ = (
        UniqueConstraint("user_id", "bundle_id", name="uq_user_bundles_user_bundle"),
    )


class BundleItemUsage(Base):
    """Analytics: records every time a user uses an item (print/play)."""
    __tablename__ = "bundle_item_usage"

    id = Column(_UUID, primary_key=True, default=_uuid)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    item_id = Column(_UUID, ForeignKey("bundle_items.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)
    used_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    item = relationship("BundleItem", back_populates="usage")
