import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Uuid, CheckConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class Story(Base):
    __tablename__ = "stories"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    cover_image_url = Column(String, nullable=True)
    age_group = Column(String, nullable=True, index=True)
    language = Column(String(2), nullable=True, index=True)
    duration_seconds = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        CheckConstraint("language IN ('en', 'hi', 'kn') OR language IS NULL", name="ck_stories_language"),
    )

    scenes = relationship(
        "StoryScene",
        back_populates="story",
        cascade="all, delete",
        order_by="StoryScene.order_index",
    )


class StoryScene(Base):
    __tablename__ = "story_scenes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    story_id = Column(Uuid, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False, index=True)
    order_index = Column(Integer, nullable=False, index=True)
    audio_url = Column(String, nullable=False)
    image_url = Column(String, nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    story = relationship("Story", back_populates="scenes")
