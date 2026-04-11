from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.db.base import Base


class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False)
    token = Column(String, unique=True, index=True, nullable=True)
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=True)
    daily_limit = Column(Integer, default=10)
    paused = Column(Boolean, default=False)
