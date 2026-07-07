from sqlalchemy import Column, Integer, Float, Index

from app.core.database import Base


class MonthlyClimObserved(Base):
    """Database model for storing monthly climatological observed data."""

    __tablename__ = "monthly_clim_observed"

    id = Column(Integer, primary_key=True, index=True)
    month = Column(Integer, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    pr_o = Column(Float, nullable=True)
    t2_o = Column(Float, nullable=True)

    __table_args__ = (
        Index("idx_monthly_clim_observed_coords", "lat", "lon"),
        Index("idx_monthly_clim_observed_query", "month", "lat", "lon"),
    )
