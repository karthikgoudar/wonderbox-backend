from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, ForeignKey

from app.db.base import Base


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    sticker_id = Column(Integer, ForeignKey("stickers.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
