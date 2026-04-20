"""
Bundle Pydantic schemas
=======================
Request / response shapes for the /bundles/* endpoints.

Naming convention: *Response for API responses, *Request for bodies.
Legacy *Out aliases are retained so existing code keeps working.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# ItemResponse
# ---------------------------------------------------------------------------
class ItemResponse(BaseModel):
    id: str
    bundle_id: str
    category_id: Optional[str] = None
    level_id: Optional[str] = None
    type: str                          # sticker | story | game
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    asset_path: Optional[str] = None   # local / CDN path to the asset
    extra_data: Dict[str, Any] = {}
    order_index: int
    is_premium: bool

    class Config:
        from_attributes = True

# Backward-compat alias
ItemOut = ItemResponse


# ---------------------------------------------------------------------------
# LevelResponse
# ---------------------------------------------------------------------------
class LevelResponse(BaseModel):
    id: str
    bundle_id: str
    category_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    order_index: int
    items: List[ItemResponse] = []

    class Config:
        from_attributes = True

LevelOut = LevelResponse


# ---------------------------------------------------------------------------
# CategoryResponse
# ---------------------------------------------------------------------------
class CategoryResponse(BaseModel):
    id: str
    bundle_id: str
    name: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    order_index: int
    levels: List[LevelResponse] = []
    items: List[ItemResponse] = []     # items placed directly under this category

    class Config:
        from_attributes = True

CategoryOut = CategoryResponse


# ---------------------------------------------------------------------------
# BundleResponse  (list / summary view)
# ---------------------------------------------------------------------------
class BundleResponse(BaseModel):
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

BundleOut = BundleResponse


# ---------------------------------------------------------------------------
# NestedBundleResponse  (full hierarchy for offline bundle download)
# ---------------------------------------------------------------------------
class NestedBundleResponse(BundleResponse):
    """
    Full bundle hierarchy returned by GET /bundles/{id}/full.
    categories → levels → items
    items (direct on bundle, no category)
    """
    categories: List[CategoryResponse] = []
    items: List[ItemResponse] = []     # items placed directly on the bundle

    class Config:
        from_attributes = True

# Backward-compat alias
BundleStructureOut = NestedBundleResponse


# ---------------------------------------------------------------------------
# UserBundleResponse
# ---------------------------------------------------------------------------
class UserBundleResponse(BaseModel):
    id: str
    bundle_id: str
    local_path: Optional[str] = None
    version: int
    downloaded_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

UserBundleOut = UserBundleResponse


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------
class DownloadBundleRequest(BaseModel):
    """Sent by the client after it finishes downloading a bundle to device."""
    version: Optional[int] = None      # defaults to current bundle.version
    local_path: Optional[str] = None   # on-device path after extraction


class TrackItemUsageRequest(BaseModel):
    """Sent when a user interacts with an item."""
    item_id: str
    action: str = "use"                # print | play | use
