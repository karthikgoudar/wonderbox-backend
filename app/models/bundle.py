import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, CheckConstraint, Uuid
from sqlalchemy.orm import relationship

from app.db.base import Base


class Bundle(Base):
    __tablename__ = "bundles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    type = Column(String, nullable=False, index=True)
    age_group = Column(String, nullable=True, index=True)
    is_free = Column(Boolean, nullable=False, default=True)
    price = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    categories = relationship(
        "BundleCategory",
        back_populates="bundle",
        cascade="all, delete",
        order_by="BundleCategory.order_index",
    )

    __table_args__ = (
        CheckConstraint("type IN ('sticker', 'story', 'mixed')", name="ck_bundles_type"),
    )


class BundleCategory(Base):
    __tablename__ = "bundle_categories"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    bundle_id = Column(Uuid, ForeignKey("bundles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    order_index = Column(Integer, nullable=False, default=0, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    bundle = relationship("Bundle", back_populates="categories")
    items = relationship(
        "BundleItem",
        back_populates="category",
        cascade="all, delete",
        order_by="BundleItem.order_index",
    )


class BundleItem(Base):
    __tablename__ = "bundle_items"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    category_id = Column(Uuid, ForeignKey("bundle_categories.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String, nullable=False, index=True)
    reference_id = Column(Uuid, nullable=False, index=True)
    order_index = Column(Integer, nullable=False, default=0, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    category = relationship("BundleCategory", back_populates="items")

    __table_args__ = (
        CheckConstraint("type IN ('sticker', 'story')", name="ck_bundle_items_type"),
    )
