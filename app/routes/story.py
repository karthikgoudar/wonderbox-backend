"""
Story Routes
============
Serves pre-recorded showcase stories and ordered scene sequences for V1.
Supports filtering by language ('en', 'hi', 'kn') and age group.

Endpoints:
  GET  /stories                 -> List all active stories
  GET  /stories/{story_id}       -> Get single story details
  GET  /stories/{story_id}/scenes -> Get ordered scene sequence for playback & printing
  POST /stories/{story_id}/progress -> Record story progress to avoid repetition
"""

import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.story import Story, StoryScene
from app.models.user_story_progress import UserStoryProgress

router = APIRouter(prefix="/stories", tags=["stories"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class StorySceneResponse(BaseModel):
    id: str
    order_index: int
    audio_url: str
    image_url: str
    print_url: Optional[str] = None
    duration_seconds: Optional[int] = None

    class Config:
        from_attributes = True


class StoryResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    age_group: Optional[str] = None
    language: Optional[str] = None
    duration_seconds: Optional[int] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class StoryDetailResponse(StoryResponse):
    scenes: List[StorySceneResponse] = []


class StoryProgressRequest(BaseModel):
    user_id: Optional[int] = None
    device_id: Optional[str] = None
    language: str = "en"


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=List[StoryResponse])
def list_stories(
    language: Optional[str] = Query(default=None, description="Language code: en, hi, kn"),
    age_group: Optional[str] = Query(default=None, description="Age group: early_childhood, middle_childhood, late_childhood, teen"),
    db: Session = Depends(get_db),
):
    """List all active pre-recorded showcase stories, optionally filtered by language and age group."""
    query = db.query(Story).filter(Story.is_active == True)
    if language:
        query = query.filter(Story.language == language)
    if age_group:
        query = query.filter(Story.age_group == age_group)
    
    stories = query.order_by(Story.created_at.desc()).all()
    # Format UUIDs as strings
    return [
        StoryResponse(
            id=str(s.id),
            title=s.title,
            description=s.description,
            cover_image_url=s.cover_image_url,
            age_group=s.age_group,
            language=s.language,
            duration_seconds=s.duration_seconds,
            is_active=s.is_active,
        )
        for s in stories
    ]


@router.get("/{story_id}", response_model=StoryDetailResponse)
def get_story(story_id: str, db: Session = Depends(get_db)):
    """Get single story details including all scene definitions."""
    try:
        story_uuid = uuid.UUID(story_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid story UUID format")

    story = db.query(Story).filter(Story.id == story_uuid, Story.is_active == True).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    scenes = (
        db.query(StoryScene)
        .filter(StoryScene.story_id == story_uuid)
        .order_by(StoryScene.order_index.asc())
        .all()
    )

    return StoryDetailResponse(
        id=str(story.id),
        title=story.title,
        description=story.description,
        cover_image_url=story.cover_image_url,
        age_group=story.age_group,
        language=story.language,
        duration_seconds=story.duration_seconds,
        is_active=story.is_active,
        scenes=[
            StorySceneResponse(
                id=str(sc.id),
                order_index=sc.order_index,
                audio_url=sc.audio_url,
                image_url=sc.image_url,
                print_url=sc.print_url,
                duration_seconds=sc.duration_seconds,
            )
            for sc in scenes
        ],
    )


@router.get("/{story_id}/scenes", response_model=List[StorySceneResponse])
def get_story_scenes(story_id: str, db: Session = Depends(get_db)):
    """
    Get ordered scene sequence for a story.
    Returns audio narration URLs, display illustration URLs, and 384px print strip URLs.
    """
    try:
        story_uuid = uuid.UUID(story_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid story UUID format")

    story = db.query(Story).filter(Story.id == story_uuid, Story.is_active == True).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    scenes = (
        db.query(StoryScene)
        .filter(StoryScene.story_id == story_uuid)
        .order_by(StoryScene.order_index.asc())
        .all()
    )

    return [
        StorySceneResponse(
            id=str(sc.id),
            order_index=sc.order_index,
            audio_url=sc.audio_url,
            image_url=sc.image_url,
            print_url=sc.print_url,
            duration_seconds=sc.duration_seconds,
        )
        for sc in scenes
    ]


@router.post("/{story_id}/progress")
def record_story_progress(
    story_id: str,
    payload: StoryProgressRequest = StoryProgressRequest(),
    db: Session = Depends(get_db),
):
    """Record that a user or device played this story to power non-repeating logic."""
    try:
        story_uuid = uuid.UUID(story_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid story UUID format")

    story = db.query(Story).filter(Story.id == story_uuid).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if payload.user_id:
        existing = (
            db.query(UserStoryProgress)
            .filter(
                UserStoryProgress.user_id == payload.user_id,
                UserStoryProgress.story_id == story_uuid,
                UserStoryProgress.language == payload.language,
            )
            .first()
        )
        if existing:
            existing.last_played_at = datetime.utcnow()
        else:
            progress = UserStoryProgress(
                user_id=payload.user_id,
                story_id=story_uuid,
                language=payload.language,
            )
            db.add(progress)
        db.commit()

    return {"status": "recorded", "story_id": story_id}
