"""
Bundle routes
=============

  GET  /bundles                  → list all published bundles (summary)
  GET  /bundles/my               → bundles the current user has downloaded
  GET  /bundles/{id}             → single bundle summary by UUID
  GET  /bundles/{id}/full        → full nested hierarchy (for offline download)
  GET  /bundles/{id}/items       → flat list of all items in the bundle
  POST /bundles/{id}/download    → mark bundle as downloaded for current user
  POST /bundles/items/use        → track item usage (analytics)

Note: /bundles/my and /bundles/items/use are registered BEFORE /{id} so
FastAPI does not accidentally match them as bundle IDs.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.infra.repositories import bundle_repository
from app.schemas.bundle_schema import (
    BundleResponse,
    DownloadBundleRequest,
    ItemResponse,
    NestedBundleResponse,
    TrackItemUsageRequest,
    UserBundleResponse,
)
from app.services.auth_service import decode_token

router = APIRouter(prefix="/bundles", tags=["bundles"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _optional_user_id(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[int]:
    """Decode JWT when present; None for guest requests."""
    if not token:
        return None
    try:
        return int(decode_token(token))
    except Exception:
        return None


def _required_user_id(token: Optional[str] = Depends(oauth2_scheme)) -> int:
    """Require a valid JWT; raises 401 otherwise."""
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        return int(decode_token(token))
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def _get_published_bundle_or_404(bundle_id: str, db: Session):
    bundle = bundle_repository.get_bundle_by_id(db, bundle_id)
    if not bundle:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Bundle '{bundle_id}' not found")
    return bundle


# ---------------------------------------------------------------------------
# Static-path routes (must come before /{id})
# ---------------------------------------------------------------------------

@router.get("", response_model=List[BundleResponse])
def list_bundles(db: Session = Depends(get_db)):
    """Return all published bundles (summary — no items loaded)."""
    return bundle_repository.get_all_bundles(db)


@router.get("/my", response_model=List[UserBundleResponse])
def my_bundles(
    db: Session = Depends(get_db),
    user_id: int = Depends(_required_user_id),
):
    """Return bundles the authenticated user has downloaded."""
    return bundle_repository.get_user_bundles(db, user_id)


@router.post("/items/use")
def use_item(
    payload: TrackItemUsageRequest,
    db: Session = Depends(get_db),
    user_id: Optional[int] = Depends(_optional_user_id),
):
    """
    Record that a user interacted with an item (print / play).
    Works for both authenticated users and guests.
    """
    bundle_repository.track_item_usage(
        db,
        item_id=payload.item_id,
        action=payload.action,
        user_id=user_id,
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# /{id} routes
# ---------------------------------------------------------------------------

@router.get("/{bundle_id}", response_model=BundleResponse)
def get_bundle(
    bundle_id: str,
    db: Session = Depends(get_db),
):
    """Return a single published bundle summary (no items / hierarchy)."""
    return _get_published_bundle_or_404(bundle_id, db)


@router.get("/{bundle_id}/full", response_model=NestedBundleResponse)
def get_bundle_full(
    bundle_id: str,
    db: Session = Depends(get_db),
):
    """
    Return the complete bundle hierarchy eagerly loaded:
      categories → levels → items
      items placed directly on the bundle (no category)
    Intended for the client to cache locally for offline use.
    """
    bundle = bundle_repository.get_full_bundle_structure(db, bundle_id)
    if not bundle:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Bundle '{bundle_id}' not found")
    return bundle


@router.get("/{bundle_id}/items", response_model=List[ItemResponse])
def get_bundle_items(
    bundle_id: str,
    db: Session = Depends(get_db),
):
    """
    Return a flat list of every item that belongs to this bundle,
    regardless of category / level placement.
    Useful for search, filtering, or bulk downloads.
    """
    _get_published_bundle_or_404(bundle_id, db)
    return bundle_repository.get_items_by_bundle(db, bundle_id)


@router.post("/{bundle_id}/download", response_model=UserBundleResponse)
def download_bundle(
    bundle_id: str,
    payload: DownloadBundleRequest = DownloadBundleRequest(),
    db: Session = Depends(get_db),
    user_id: int = Depends(_required_user_id),
):
    """
    Record that the authenticated user has downloaded this bundle.
    Call this after the on-device extraction is complete.
    """
    bundle = _get_published_bundle_or_404(bundle_id, db)
    version = payload.version if payload.version is not None else bundle.version
    return bundle_repository.mark_downloaded(
        db, user_id, str(bundle.id), version, local_path=payload.local_path
    )


# ---------------------------------------------------------------------------
# (kept for backwards compat — remove when clients migrate to /items/use)
# ---------------------------------------------------------------------------

@router.post("/items/{item_id}/use", deprecated=True)
def use_item_legacy(
    item_id: str,
    db: Session = Depends(get_db),
    user_id: Optional[int] = Depends(_optional_user_id),
):
    """Deprecated: use POST /bundles/items/use instead."""
    bundle_repository.track_item_usage(db, item_id=item_id, user_id=user_id)
    return {"ok": True}
