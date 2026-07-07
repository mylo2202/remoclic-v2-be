from sqlalchemy import Column, Integer, Float, Index

from app.core.database import Base


class MonthlyClimModel(Base):
    """Database model for storing monthly climatological model data."""

    __tablename__ = "monthly_clim_model"

    id = Column(Integer, primary_key=True, index=True)
    month = Column(Integer, nullable=False)
    lead = Column(Integer, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    pr_m = Column(Float, nullable=True)
    t2_m = Column(Float, nullable=True)

    __table_args__ = (
        Index("idx_monthly_clim_model_coords", "lat", "lon"),
        Index("idx_monthly_clim_model_query", "month", "lat", "lon"),
    )
