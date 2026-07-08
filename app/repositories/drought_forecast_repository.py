import logging
from datetime import date, datetime
from typing import Optional, List, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.drought_forecast import DroughtForecast
from app.models.drought_ref_date import DroughtRefDate

logger = logging.getLogger(__name__)


class DroughtForecastRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_latest_ref_date(self) -> Optional[date]:
        stmt = (
            select(DroughtForecast.ref_date)
            .join(
                DroughtRefDate,
                DroughtRefDate.ref_date == DroughtForecast.ref_date,
                isouter=True,
            )
            .where((DroughtRefDate.is_active.is_(True)) | (DroughtRefDate.id.is_(None)))
            .distinct()
            .order_by(DroughtForecast.ref_date.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar()

    def find_nearest_grid_point(self, lat: float, lon: float) -> Optional[Tuple[float, float]]:
        stmt = (
            select(DroughtForecast.lat, DroughtForecast.lon)
            .order_by(func.abs(DroughtForecast.lat - lat) + func.abs(DroughtForecast.lon - lon))
            .limit(1)
        )
        result = self.db.execute(stmt).first()
        return result if result else None

    def get_forecast_points(self, lat: float, lon: float, ref_date: date, timescale: float = 1.0) -> List[
        DroughtForecast]:
        stmt = (
            select(DroughtForecast)
            .join(
                DroughtRefDate,
                DroughtRefDate.ref_date == DroughtForecast.ref_date,
                isouter=True,
            )
            .where(
                DroughtForecast.lat == lat,
                DroughtForecast.lon == lon,
                DroughtForecast.ref_date == ref_date,
                DroughtForecast.timescale == timescale,
                ((DroughtRefDate.is_active.is_(True)) | (DroughtRefDate.id.is_(None))),
            )
            .order_by(DroughtForecast.lead.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_active_ref_dates(self) -> List[date]:
        stmt = (
            select(DroughtRefDate.ref_date)
            .where(DroughtRefDate.is_active.is_(True))
            .order_by(DroughtRefDate.ref_date.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def set_ref_date_status(self, ref_date: date | str, is_active: bool) -> None:
        if isinstance(ref_date, str):
            ref_date = (
                datetime.strptime(ref_date, "%Y-%m-%d").date()
                if "-" in ref_date
                else datetime.strptime(ref_date, "%Y%m").date()
            )

        # Check if reference date exists in forecast data
        exists_stmt = select(DroughtForecast.ref_date).where(DroughtForecast.ref_date == ref_date).limit(1)
        ref_exists = self.db.execute(exists_stmt).scalar()
        if not ref_exists:
            raise ValueError(f"Reference date {ref_date} does not exist in forecast data.")

        status = self.db.execute(
            select(DroughtRefDate).where(DroughtRefDate.ref_date == ref_date)
        ).scalars().one_or_none()

        if status is None:
            status = DroughtRefDate(ref_date=ref_date, is_active=is_active)
            self.db.add(status)
        else:
            status.is_active = is_active
            self.db.add(status)

        self.db.commit()

    def is_ref_date_active(self, ref_date: date) -> bool:
        status = self.db.execute(
            select(DroughtRefDate).where(DroughtRefDate.ref_date == ref_date)
        ).scalars().one_or_none()
        return status is None or status.is_active
