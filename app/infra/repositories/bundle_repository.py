"""
Bundle repository
=================
All DB access for bundles, categories, levels, items, user downloads,
and item-usage analytics.

Design principles
-----------------
- Flat queries first: BundleItem always carries bundle_id, so we can
  fetch all items for a bundle in a single query without joining.
- Full structure uses a single query with eager loads (joinedload) so
  SQLAlchemy emits one round-trip per relationship level, not N+1.
- No recursive CTEs — hierarchy depth is capped at 3 (bundle/category/level).
"""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.bundle import (
    Bundle,
    BundleCategory,
    BundleItem,
    BundleItemUsage,
    BundleLevel,
    UserBundle,
)


# ---------------------------------------------------------------------------
# Bundle queries
# ---------------------------------------------------------------------------

def get_all_bundles(db: Session) -> List[Bundle]:
    """Return all published bundles ordered by newest first (summary, no items)."""
    return (
        db.query(Bundle)
        .filter(Bundle.is_published.is_(True))
        .order_by(Bundle.created_at.desc())
        .all()
    )


def get_bundle_by_id(db: Session, bundle_id: str) -> Optional[Bundle]:
    """Return a single published bundle by UUID."""
    return (
        db.query(Bundle)
        .filter(Bundle.id == bundle_id, Bundle.is_published.is_(True))
        .first()
    )


def get_bundle_by_slug(db: Session, slug: str) -> Optional[Bundle]:
    """Return a single published bundle by URL slug."""
    return (
        db.query(Bundle)
        .filter(Bundle.slug == slug, Bundle.is_published.is_(True))
        .first()
    )


def get_full_bundle_structure(db: Session, bundle_id: str) -> Optional[Bundle]:
    """
    Return a published bundle with its complete hierarchy eagerly loaded
    in the minimum number of SQL round-trips:

      Bundle
        └─ BundleCategory (ordered)
             └─ BundleLevel   (ordered)
                  └─ BundleItem (ordered)
             └─ BundleItem (direct on category, ordered)
        └─ BundleItem (direct on bundle — no category, no level)

    The caller receives a single ORM object; Pydantic serialisation
    (BundleResponse / NestedBundleResponse) handles flattening.
    """
    return (
        db.query(Bundle)
        .options(
            joinedload(Bundle.categories)
            .joinedload(BundleCategory.levels)
            .joinedload(BundleLevel.items),
            joinedload(Bundle.categories)
            .joinedload(BundleCategory.items),
            joinedload(Bundle.all_items),
        )
        .filter(Bundle.id == bundle_id, Bundle.is_published.is_(True))
        .first()
    )


# ---------------------------------------------------------------------------
# Item queries (flat — no joins needed because bundle_id is denormalised)
# ---------------------------------------------------------------------------

def get_items_by_bundle(db: Session, bundle_id: str) -> List[BundleItem]:
    """All items that belong to this bundle at any depth."""
    return (
        db.query(BundleItem)
        .filter(BundleItem.bundle_id == bundle_id)
        .order_by(BundleItem.order_index)
        .all()
    )


def get_items_by_category(db: Session, category_id: str) -> List[BundleItem]:
    """Items that live directly under a category (no level assigned)."""
    return (
        db.query(BundleItem)
        .filter(
            BundleItem.category_id == category_id,
            BundleItem.level_id.is_(None),
        )
        .order_by(BundleItem.order_index)
        .all()
    )


def get_items_by_level(db: Session, level_id: str) -> List[BundleItem]:
    """Items that belong to a specific level."""
    return (
        db.query(BundleItem)
        .filter(BundleItem.level_id == level_id)
        .order_by(BundleItem.order_index)
        .all()
    )


# ---------------------------------------------------------------------------
# User download tracking
# ---------------------------------------------------------------------------

def get_user_bundles(db: Session, user_id: int) -> List[UserBundle]:
    """Return all UserBundle records for a user, newest download first."""
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


def mark_downloaded(
    db: Session,
    user_id: int,
    bundle_id: str,
    version: int,
    local_path: Optional[str] = None,
) -> UserBundle:
    """
    Upsert a UserBundle row — creates it on first download, updates it on
    re-download (e.g. new bundle version).
    """
    record = get_user_bundle(db, user_id, bundle_id)
    now = datetime.utcnow()
    if record is None:
        record = UserBundle(
            user_id=user_id,
            bundle_id=bundle_id,
            version=version,
            local_path=local_path,
            downloaded_at=now,
        )
        db.add(record)
    else:
        record.version = version
        record.local_path = local_path or record.local_path
        record.downloaded_at = now
    db.commit()
    db.refresh(record)
    return record


# ---------------------------------------------------------------------------
# Usage analytics
# ---------------------------------------------------------------------------

def track_item_usage(
    db: Session,
    item_id: str,
    action: str = "use",
    user_id: Optional[int] = None,
    device_id: Optional[int] = None,
) -> BundleItemUsage:
    """Append one usage event. action should be 'print', 'play', or 'use'."""
    record = BundleItemUsage(
        item_id=item_id,
        user_id=user_id,
        device_id=device_id,
        action=action,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
