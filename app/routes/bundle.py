"""
Bundle routes
=============

  GET  /bundles                       → list all published bundles
  GET  /bundles/{slug}                → full bundle structure (hierarchy)
  POST /bundles/{slug}/download       → mark bundle as downloaded for current user
  GET  /bundles/my                    → list bundles the current user has downloaded
  POST /bundles/items/{item_id}/use   → track item usage (analytics)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.infra.repositories import bundle_repository
from app.schemas.bundle_schema import (
    BundleOut,
    BundleStructureOut,
    DownloadBundleRequest,
    TrackItemUsageRequest,
    UserBundleOut,
)
from app.services.auth_service import decode_token

router = APIRouter(prefix="/bundles", tags=["bundles"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def _optional_user_id(
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[int]:
    """Decode JWT when present; returns None for unauthenticated requests."""
    if not token:
        return None
    try:
        return int(decode_token(token))
    except Exception:
        return None


def _required_user_id(
    token: Optional[str] = Depends(oauth2_scheme),
) -> int:
    """Require a valid JWT; raises 401 if missing or invalid."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    try:
        return int(decode_token(token))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


# ── Browse ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=List[BundleOut])
def list_bundles(db: Session = Depends(get_db)):
    """Return all published bundles (summary view, no items)."""
    return bundle_repository.get_all_published(db)


# ── My bundles ─────────────────────────────────────────────────────────────────

@router.get("/my", response_model=List[UserBundleOut])
def my_bundles(
    db: Session = Depends(get_db),
    user_id: int = Depends(_required_user_id),
):
    """Return all bundles the authenticated user has downloaded."""
    return bundle_repository.get_user_bundles(db, user_id)


# ── Full structure ─────────────────────────────────────────────────────────────

@router.get("/{slug}", response_model=BundleStructureOut)
def get_bundle(slug: str, db: Session = Depends(get_db)):
    """
    Return a published bundle with its full hierarchy:
    categories → levels → items, plus any items that live directly
    under the bundle or under a category.
    """
    bundle = bundle_repository.get_full_structure(db, slug)
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bundle '{slug}' not found",
        )
    return bundle


# ── Download ──────────────────────────────────────────────────────────────────

@router.post("/{slug}/download", response_model=UserBundleOut)
def download_bundle(
    slug: str,
    payload: DownloadBundleRequest = DownloadBundleRequest(),
    db: Session = Depends(get_db),
    user_id: int = Depends(_required_user_id),
):
    """
    Record that the authenticated user has downloaded this bundle.
    The client should call this after the local download completes.
    """
    bundle = bundle_repository.get_by_slug(db, slug)
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bundle '{slug}' not found",
        )
    version = payload.version if payload.version is not None else bundle.version
    return bundle_repository.mark_downloaded(db, user_id, str(bundle.id), version)


# ── Usage analytics ───────────────────────────────────────────────────────────

@router.post("/items/{item_id}/use")
def use_item(
    item_id: str,
    db: Session = Depends(get_db),
    user_id: Optional[int] = Depends(_optional_user_id),
):
    """
    Record that the user interacted with an item (e.g. printed a sticker,
    played a game level). Works for both authenticated and guest users.
    """
    bundle_repository.track_item_usage(db, item_id=item_id, user_id=user_id)
    return {"ok": True}
