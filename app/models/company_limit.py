from datetime import datetime

from sqlalchemy import Column, Integer, DateTime

from app.db.base import Base


class CompanyLimit(Base):
    __tablename__ = "company_limits"

    id = Column(Integer, primary_key=True, index=True)
    free_daily_limit = Column(Integer, nullable=False, default=5)
    free_monthly_limit = Column(Integer, nullable=False, default=100)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
