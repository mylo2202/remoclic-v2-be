from sqlalchemy import Column, Integer, Float, Date, Index

from app.core.database import Base


class PrT2Forecast(Base):
    """Database model for storing individual grid point precipitation and temperture forecasts."""

    __tablename__ = "pr_t2_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    ref_date = Column(Date, nullable=False, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    lead = Column(Integer, nullable=False)
    pr = Column(Float, nullable=True)
    t2 = Column(Float, nullable=True)
    pr_ano = Column(Float, nullable=True)
    t2_ano = Column(Float, nullable=True)
    pr_fcs = Column(Float, nullable=True)
    t2_fcs = Column(Float, nullable=True)

    __table_args__ = (
        Index("idx_pr_t2_forecast_coords", "lat", "lon"),
        Index("idx_pr_t2_forecast_query", "lat", "lon", "ref_date"),
    )
