"""
Bundle repository
=================
All DB access for bundles, categories, levels, items, user downloads,
and item-usage analytics.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.bundle import (
    Bundle,
    BundleCategory,
    BundleItem,
    BundleItemUsage,
    BundleLevel,
    UserBundle,
)


# ── Bundle queries ─────────────────────────────────────────────────────────────

def get_all_published(db: Session) -> List[Bundle]:
    """Return all published bundles (no sub-structure loaded)."""
    return (
        db.query(Bundle)
        .filter(Bundle.is_published.is_(True))
        .order_by(Bundle.created_at.desc())
        .all()
    )


def get_by_slug(db: Session, slug: str) -> Optional[Bundle]:
    """Return a published bundle matched by slug."""
    return (
        db.query(Bundle)
        .filter(Bundle.slug == slug, Bundle.is_published.is_(True))
        .first()
    )


def get_full_structure(db: Session, slug: str) -> Optional[Bundle]:
    """
    Return a published bundle with its full hierarchy eagerly loaded:
      bundle → categories → levels → items
                          ↘ items (direct-on-category)
             ↘ items (direct-on-bundle)
    """
    return (
        db.query(Bundle)
        .options(
            joinedload(Bundle.categories)
            .joinedload(BundleCategory.levels)
            .joinedload(BundleLevel.items),
            joinedload(Bundle.categories)
            .joinedload(BundleCategory.items),
        )
        .filter(Bundle.slug == slug, Bundle.is_published.is_(True))
        .first()
    )


# ── Category / Level / Item helpers ───────────────────────────────────────────

def get_items_in_level(db: Session, level_id: str) -> List[BundleItem]:
    return (
        db.query(BundleItem)
        .filter(BundleItem.level_id == level_id)
        .order_by(BundleItem.order_index)
        .all()
    )


def get_items_direct_in_category(db: Session, category_id: str) -> List[BundleItem]:
    """Items that live directly under a category (no level)."""
    return (
        db.query(BundleItem)
        .filter(
            BundleItem.category_id == category_id,
            BundleItem.level_id.is_(None),
        )
        .order_by(BundleItem.order_index)
        .all()
    )


def get_items_direct_in_bundle(db: Session, bundle_id: str) -> List[BundleItem]:
    """Items that live directly under a bundle (no category, no level)."""
    return (
        db.query(BundleItem)
        .filter(
            BundleItem.bundle_id == bundle_id,
            BundleItem.category_id.is_(None),
            BundleItem.level_id.is_(None),
        )
        .order_by(BundleItem.order_index)
        .all()
    )


# ── User download tracking ─────────────────────────────────────────────────────

def get_user_bundles(db: Session, user_id: int) -> List[UserBundle]:
    return (
        db.query(UserBundle)
        .filter(UserBundle.user_id == user_id)
        .order_by(UserBundle.downloaded_at.desc())
        .all()
    )


def get_user_bundle(db: Session, user_id: int, bundle_id: str) -> Optional[UserBundle]:
    return (
        db.query(UserBundle)
        .filter(UserBundle.user_id == user_id, UserBundle.bundle_id == bundle_id)
        .first()
    )


def mark_downloaded(db: Session, user_id: int, bundle_id: str, version: int) -> UserBundle:
    """
    Upsert a UserBundle row marking the bundle as downloaded for the user.
    Returns the UserBundle record.
    """
    record = get_user_bundle(db, user_id, bundle_id)
    now = datetime.utcnow()
    if record is None:
        record = UserBundle(
            user_id=user_id,
            bundle_id=bundle_id,
            downloaded_version=version,
            is_downloaded=True,
            downloaded_at=now,
            last_opened_at=now,
        )
        db.add(record)
    else:
        record.downloaded_version = version
        record.is_downloaded = True
        record.downloaded_at = now
        record.last_opened_at = now
    db.commit()
    db.refresh(record)
    return record


def update_last_opened(db: Session, user_id: int, bundle_id: str) -> Optional[UserBundle]:
    record = get_user_bundle(db, user_id, bundle_id)
    if record:
        record.last_opened_at = datetime.utcnow()
        db.commit()
        db.refresh(record)
    return record


# ── Usage analytics ────────────────────────────────────────────────────────────

def track_item_usage(
    db: Session,
    item_id: str,
    user_id: Optional[int] = None,
    device_id: Optional[int] = None,
) -> BundleItemUsage:
    record = BundleItemUsage(
        item_id=item_id,
        user_id=user_id,
        device_id=device_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
