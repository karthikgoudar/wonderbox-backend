from sqlalchemy import Column, Integer, String, Date, ForeignKey
from app.db.base import Base


class Child(Base):
    __tablename__ = "children"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=True)
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=False)
