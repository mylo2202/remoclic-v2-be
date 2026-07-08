import logging
from datetime import date, datetime
from typing import Optional, List, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.pr_t2_forecast import PrT2Forecast
from app.models.pr_t2_ref_date import PrT2RefDate

logger = logging.getLogger(__name__)


class PrT2ForecastRepository:
    """Module for abstracting data access to PostgreSQL precipitation and temperature forecast data."""

    def __init__(self, db: Session):
        """Initializes the repository with a database session."""
        self.db = db

    def get_latest_ref_date(self) -> Optional[date]:
        """Retrieves the latest available reference date from the database."""
        stmt = (
            select(PrT2Forecast.ref_date)
            .join(
                PrT2RefDate,
                PrT2RefDate.ref_date == PrT2Forecast.ref_date,
                isouter=True,
            )
            .where((PrT2RefDate.is_active.is_(True)) | (PrT2RefDate.id.is_(None)))
            .distinct()
            .order_by(PrT2Forecast.ref_date.desc())
            .limit(1)
        )
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
            .join(
                PrT2RefDate,
                PrT2RefDate.ref_date == PrT2Forecast.ref_date,
                isouter=True,
            )
            .where(
                PrT2Forecast.lat == lat,
                PrT2Forecast.lon == lon,
                PrT2Forecast.ref_date == ref_date,
                ((PrT2RefDate.is_active.is_(True)) | (PrT2RefDate.id.is_(None))),
            )
            .order_by(PrT2Forecast.lead.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_active_ref_dates(self) -> List[date]:
        """Retrieves all active reference dates from the availability table, sorted in descending order."""
        stmt = (
            select(PrT2RefDate.ref_date)
            .where(PrT2RefDate.is_active.is_(True))
            .order_by(PrT2RefDate.ref_date.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def set_ref_date_status(self, ref_date: date | str, is_active: bool) -> None:
        """Marks a reference date as active or inactive for API use."""
        if isinstance(ref_date, str):
            ref_date = datetime.strptime(ref_date, "%Y-%m-%d").date() if "-" in ref_date else datetime.strptime(ref_date, "%Y%m").date()

        status = self.db.execute(
            select(PrT2RefDate).where(PrT2RefDate.ref_date == ref_date)
        ).scalars().one_or_none()

        if status is None:
            status = PrT2RefDate(ref_date=ref_date, is_active=is_active)
            self.db.add(status)
        else:
            status.is_active = is_active
            self.db.add(status)

        self.db.commit()

    def is_ref_date_active(self, ref_date: date) -> bool:
        """Returns whether a reference date should be exposed through the API."""
        status = self.db.execute(
            select(PrT2RefDate).where(PrT2RefDate.ref_date == ref_date)
        ).scalars().one_or_none()
        return status is None or status.is_active

    def set_ref_date_active(self, ref_date: date) -> None:
        """Marks a reference date as active."""
        self.set_ref_date_status(ref_date, is_active=True)

