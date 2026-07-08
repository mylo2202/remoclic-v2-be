from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, Index

from app.core.database import Base


class PrT2RefDate(Base):
    """Tracks whether a PR/T2 reference date is currently available for API use."""

    __tablename__ = "pr_t2_ref_date"

    id = Column(Integer, primary_key=True, index=True)
    ref_date = Column(Date, nullable=False, unique=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_pr_t2_ref_date_active", "ref_date", "is_active"),
    )
