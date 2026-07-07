from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Index

from app.core.database import Base


class MonthlyClimIngestionState(Base):
    """Tracks the latest ingested monthly climate file and its source metadata."""

    __tablename__ = "monthly_clim_ingestion_state"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False, unique=True)
    source_url = Column(String, nullable=False)
    etag = Column(String, nullable=True)
    last_modified = Column(String, nullable=True)
    checksum = Column(String, nullable=True)
    ingested_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_monthly_clim_ingestion_file_name", "file_name"),
    )
