import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Uuid

from app.db.base import Base


class PresetSticker(Base):
    __tablename__ = "preset_stickers"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String, nullable=False, index=True)
    image_url = Column(String, nullable=False)
    age_group = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
