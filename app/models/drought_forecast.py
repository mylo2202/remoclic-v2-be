from sqlalchemy import Column, Integer, Float, Date, Index

from app.core.database import Base


class DroughtForecast(Base):
    """Database model for storing individual grid point drought forecasts."""

    __tablename__ = "drought_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    ref_date = Column(Date, nullable=False, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    timescale = Column(Float, nullable=False)
    lead = Column(Integer, nullable=False)
    mild = Column(Float, nullable=True)
    mord = Column(Float, nullable=True)
    seve = Column(Float, nullable=True)
    dr_ens = Column(Float, nullable=True)

    __table_args__ = (
        Index("idx_forecast_coords", "lat", "lon"),
        Index("idx_forecast_query", "lat", "lon", "ref_date"),
    )
