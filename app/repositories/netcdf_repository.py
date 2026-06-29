import logging
from datetime import date
from typing import Optional, List, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.forecast import DroughtForecast

logger = logging.getLogger(__name__)


class NetCDFRepository:
    """Module for abstracting data access to PostgreSQL drought forecast data."""

    def __init__(self, db: Session):
        """Initializes the repository with a database session."""
        self.db = db

    def get_latest_ref_date(self) -> Optional[date]:
        """Retrieves the latest available reference date from the database."""
        stmt = select(func.max(DroughtForecast.ref_date))
        return self.db.execute(stmt).scalar()

    def get_available_ref_dates(self) -> List[date]:
        """Retrieves all unique reference dates sorted ascending."""
        stmt = select(DroughtForecast.ref_date).distinct().order_by(DroughtForecast.ref_date.asc())
        return list(self.db.execute(stmt).scalars().all())

    def get_total_records(self) -> int:
        """Retrieves the total number of records in the database."""
        stmt = select(func.count(DroughtForecast.id))
        return self.db.execute(stmt).scalar() or 0

    def find_nearest_grid_point(self, lat: float, lon: float) -> Optional[Tuple[float, float]]:
        """
        Finds the closest grid point coordinate (lat, lon) in the database.
        Uses Manhattan distance for simplicity.
        """
        # Query distinct coordinates to find the closest match
        stmt = (
            select(DroughtForecast.lat, DroughtForecast.lon)
            .distinct()
            .order_by(func.abs(DroughtForecast.lat - lat) + func.abs(DroughtForecast.lon - lon))
            .limit(1)
        )
        result = self.db.execute(stmt).first()
        return result if result else None

    def get_forecast_points(
        self, lat: float, lon: float, ref_date: date, timescale: float = 1.0
    ) -> List[DroughtForecast]:
        """Retrieves forecast points for a given location, date, and timescale sorted by lead time."""
        stmt = (
            select(DroughtForecast)
            .where(
                DroughtForecast.lat == lat,
                DroughtForecast.lon == lon,
                DroughtForecast.ref_date == ref_date,
                DroughtForecast.timescale == timescale,
            )
            .order_by(DroughtForecast.lead.asc())
        )
        return list(self.db.execute(stmt).scalars().all())
