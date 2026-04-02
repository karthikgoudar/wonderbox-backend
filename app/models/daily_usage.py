from datetime import date

from sqlalchemy import Column, Integer, Date, ForeignKey

from app.db.base import Base


class DailyUsage(Base):
    __tablename__ = "daily_usage"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    date = Column(Date, default=date.today, nullable=False, index=True)
    count = Column(Integer, default=0, nullable=False)
