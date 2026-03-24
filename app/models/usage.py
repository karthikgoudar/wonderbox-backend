from sqlalchemy import Column, Integer, Date, ForeignKey
from app.db.base import Base


class Usage(Base):
    __tablename__ = "usages"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    date = Column(Date)
    count = Column(Integer, default=0)
