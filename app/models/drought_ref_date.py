from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, Index

from app.core.database import Base


class DroughtRefDate(Base):
    """Tracks whether a drought reference date is currently available for API use."""

    __tablename__ = "drought_ref_date"

    id = Column(Integer, primary_key=True, index=True)
    ref_date = Column(Date, nullable=False, unique=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_drought_ref_date_active", "ref_date", "is_active"),
    )
