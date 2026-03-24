from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from datetime import datetime
from app.db.base import Base


class Sticker(Base):
    __tablename__ = "stickers"
    id = Column(Integer, primary_key=True, index=True)
    original_text = Column(Text, nullable=True)
    normalized_prompt = Column(Text, nullable=True)
    language = Column(String(10), nullable=True)
    image_url = Column(String, nullable=True)
    is_favorited = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
