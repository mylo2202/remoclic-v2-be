import logging
from datetime import date
from typing import Optional, List, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.pr_t2_forecast import PrT2Forecast

logger = logging.getLogger(__name__)


class PrT2ForecastRepository:
    """Module for abstracting data access to PostgreSQL precipitation and temperature forecast data."""

    def __init__(self, db: Session):
        """Initializes the repository with a database session."""
        self.db = db

    def get_latest_ref_date(self) -> Optional[date]:
        """Retrieves the latest available reference date from the database."""
        stmt = select(func.max(PrT2Forecast.ref_date))
        return self.db.execute(stmt).scalar()

    def find_nearest_grid_point(self, lat: float, lon: float) -> Optional[Tuple[float, float]]:
        """
        Finds the closest grid point coordinate (lat, lon) in the database.
        Uses Manhattan distance for simplicity.
        """
        # Query coordinates to find the closest match
        stmt = (
            select(PrT2Forecast.lat, PrT2Forecast.lon)
            .order_by(func.abs(PrT2Forecast.lat - lat) + func.abs(PrT2Forecast.lon - lon))
            .limit(1)
        )
        result = self.db.execute(stmt).first()
        return result if result else None

    def get_forecast_points(
        self, lat: float, lon: float, ref_date: date
    ) -> List[PrT2Forecast]:
        """Retrieves forecast points for a given location, date sorted by lead time."""
        stmt = (
            select(PrT2Forecast)
            .where(
                PrT2Forecast.lat == lat,
                PrT2Forecast.lon == lon,
                PrT2Forecast.ref_date == ref_date,
            )
            .order_by(PrT2Forecast.lead.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_distinct_ref_dates(self) -> List[date]:
        """Retrieves all distinct reference dates from the database, sorted in descending order."""
        stmt = select(PrT2Forecast.ref_date).distinct().order_by(PrT2Forecast.ref_date.desc())
        return list(self.db.execute(stmt).scalars().all())

