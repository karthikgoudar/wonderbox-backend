import uuid
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Uuid, UniqueConstraint, Index

from app.db.base import Base


class UserStoryProgress(Base):
    __tablename__ = "user_story_progress"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    story_id = Column(Uuid, ForeignKey("stories.id"), nullable=False, index=True)
    language = Column(String(2), nullable=False, index=True)
    last_played_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "story_id", "language", name="uq_user_story_language"),
        Index("idx_user_language", "user_id", "language"),
    )
