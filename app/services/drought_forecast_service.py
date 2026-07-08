import logging
from datetime import datetime, date
from typing import Optional

from app.models import DroughtForecast
from app.repositories.drought_forecast_repository import DroughtForecastRepository

logger = logging.getLogger(__name__)


def _generate_date_labels(ref_date: date, leads: list[int]) -> list[str]:
    labels = []
    for lead in leads:
        months_to_add = int(lead)
        new_month = (ref_date.month + months_to_add - 1) % 12 + 1
        new_year = ref_date.year + (ref_date.month + months_to_add - 1) // 12
        labels.append(f"{new_month:02d}-{new_year}")
    return labels


def _clean_vals(vals) -> list[float | None]:
    return [round(float(v), 2) if (v is not None and v != -99.0) else None for v in vals]


class DroughtForecastService:
    def __init__(self, repository: DroughtForecastRepository):
        self.repository = repository

    def get_drought_forecast_tuple(self, lat: float, lng: float, ref_date_str: Optional[str] = None, timescale: float = 1.0):
        if ref_date_str:
            try:
                if "-" in ref_date_str:
                    ref_date = datetime.strptime(ref_date_str, "%Y-%m-%d").date()
                else:
                    ref_date = datetime.strptime(ref_date_str, "%Y%m").date()
            except ValueError as e:
                raise ValueError(f"Invalid reference date format: {ref_date_str}") from e
        else:
            ref_date = self.repository.get_latest_ref_date()
            if not ref_date:
                raise ValueError("No probability forecast data is currently available in the database.")

        if not self.repository.is_ref_date_active(ref_date):
            raise ValueError(f"Reference date {ref_date} is temporarily unavailable.")

        coord = self.repository.find_nearest_grid_point(lat, lng)
        if not coord:
            raise ValueError("No grid coordinates found in database.")

        nearest_lat, nearest_lon = coord
        points = self.repository.get_forecast_points(lat=nearest_lat, lon=nearest_lon, ref_date=ref_date, timescale=timescale)

        if not points:
            raise ValueError(f"No forecast data found for coords ({nearest_lat}, {nearest_lon}) and date {ref_date}")

        labels = _generate_date_labels(ref_date, [p.lead for p in points])
        return nearest_lat, nearest_lon, ref_date, labels, points

    def get_probability_forecast(self, lat: float, lng: float, ref_date_str: Optional[str] = None, timescale: float = 1.0) -> dict:
        nearest_lat, nearest_lon, ref_date, labels, points = self.get_drought_forecast_tuple(lat, lng, ref_date_str, timescale)
        return {
            "location": {"lat": nearest_lat, "lng": nearest_lon},
            "ref_date": ref_date,
            "timescale": timescale,
            "labels": labels,
            "data": {
                "mild": _clean_vals([p.mild for p in points]),
                "mord": _clean_vals([p.mord for p in points]),
                "seve": _clean_vals([p.seve for p in points]),
            },
        }

    def get_event_forecast(self, lat: float, lng: float, ref_date_str: Optional[str] = None, timescale: float = 1.0) -> dict:
        nearest_lat, nearest_lon, ref_date, labels, points = self.get_drought_forecast_tuple(lat, lng, ref_date_str, timescale)
        return {
            "location": {"lat": nearest_lat, "lng": nearest_lon},
            "ref_date": ref_date,
            "timescale": timescale,
            "labels": labels,
            "data": {
                "dr_ens": _clean_vals([p.dr_ens for p in points]),
            },
        }

    def get_distinct_ref_dates(self) -> list[date]:
        return self.repository.get_active_ref_dates()

    def set_ref_date_status(self, ref_date_str: str, is_active: bool) -> None:
        try:
            self.repository.set_ref_date_status(ref_date_str, is_active)
        except ValueError as e:
            raise ValueError(f"Invalid reference date format: {ref_date_str}") from e