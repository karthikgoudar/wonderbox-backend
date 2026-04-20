"""
Bundle Pydantic schemas
=======================
Request / response shapes for the /bundles/* endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ── Item ───────────────────────────────────────────────────────────────────────

class ItemOut(BaseModel):
    id: str
    type: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    extra_data: Dict[str, Any] = {}
    order_index: int
    is_premium: bool

    class Config:
        from_attributes = True


# ── Level ─────────────────────────────────────────────────────────────────────

class LevelOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    order_index: int
    items: List[ItemOut] = []

    class Config:
        from_attributes = True


# ── Category ──────────────────────────────────────────────────────────────────

class CategoryOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    order_index: int
    levels: List[LevelOut] = []
    items: List[ItemOut] = []   # items that live directly under this category

    class Config:
        from_attributes = True


# ── Bundle (list view) ────────────────────────────────────────────────────────

class BundleOut(BaseModel):
    id: str
    slug: str
    name: str
    description: Optional[str] = None
    type: str
    age_group: Optional[str] = None
    language: str
    is_free: bool
    price_paise: Optional[int] = None
    version: int
    thumbnail_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Bundle (full structure) ───────────────────────────────────────────────────

class BundleStructureOut(BundleOut):
    categories: List[CategoryOut] = []
    items: List[ItemOut] = []   # items that live directly under the bundle

    class Config:
        from_attributes = True


# ── User bundle (download record) ─────────────────────────────────────────────

class UserBundleOut(BaseModel):
    id: str
    bundle_id: str
    downloaded_version: int
    is_downloaded: bool
    downloaded_at: Optional[datetime] = None
    last_opened_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Requests ──────────────────────────────────────────────────────────────────

class DownloadBundleRequest(BaseModel):
    """Sent by client when it finishes downloading a bundle locally."""
    version: Optional[int] = None   # defaults to current bundle version if omitted


class TrackItemUsageRequest(BaseModel):
    item_id: str
