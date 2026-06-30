import logging
from datetime import datetime, date
from typing import Optional

from app.models import DroughtForecast
from app.repositories.draught_forecast_repository import DroughtForecastRepository

logger = logging.getLogger(__name__)


def _generate_date_labels(ref_date: date, leads: list[int]) -> list[str]:
    """Generates human-readable labels from reference date and lead offsets."""
    labels = []
    for lead in leads:
        months_to_add = int(lead)
        new_month = (ref_date.month + months_to_add - 1) % 12 + 1
        new_year = ref_date.year + (ref_date.month + months_to_add - 1) // 12
        labels.append(f"{new_month:02d}-{new_year}")
    return labels


class DroughtForecastService:
    """Module providing core business logic for dataset operations using database storage."""

    def __init__(self, repository: DroughtForecastRepository):
        self.repository = repository

    def get_draught_forecast_tuple(
        self,
        lat: float,
        lng: float,
        ref_date_str: Optional[str] = None,
        timescale: float = 1.0,
    ) -> tuple[float, float, list[str], list[DroughtForecast]]:
        """Extract draught forecast tuple."""
        # 1. Resolve ref_date
        if ref_date_str:
            try:
                # Expect YYYY-MM-DD or YYYYMM
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

        # 2. Find nearest grid point
        coord = self.repository.find_nearest_grid_point(lat, lng)
        if not coord:
            raise ValueError(f"No grid coordinates found in database.")

        nearest_lat, nearest_lon = coord

        # 3. Retrieve forecast points
        points = self.repository.get_forecast_points(
            lat=nearest_lat, lon=nearest_lon, ref_date=ref_date, timescale=timescale
        )

        if not points:
            raise ValueError(
                f"No forecast data found for coords ({nearest_lat}, {nearest_lon}) and date {ref_date}"
            )

        # 4. Format response
        leads = [p.lead for p in points]
        labels = _generate_date_labels(ref_date, leads)

        return nearest_lat, nearest_lon, labels, points

    def get_probability_forecast(
            self,
            lat: float,
            lng: float,
            ref_date_str: Optional[str] = None,
            timescale: float = 1.0,
    ) -> dict:
        """Extract multi-month probability forecast for mild, mord, and seve drought levels from database."""
        nearest_lat, nearest_lon, labels, points = self.get_draught_forecast_tuple(lat, lng, ref_date_str, timescale)

        return {
            "location": {"lat": nearest_lat, "lng": nearest_lon},
            "labels": labels,
            "data": {
                "mild": self._clean_vals([p.mild for p in points]),
                "mord": self._clean_vals([p.mord for p in points]),
                "seve": self._clean_vals([p.seve for p in points])
            }
        }

    def get_event_forecast(
            self,
            lat: float,
            lng: float,
            ref_date_str: Optional[str] = None,
            timescale: float = 1.0,
    ) -> dict:
        """Extract multi-month event forecast for mild, mord, and seve drought levels from database."""
        nearest_lat, nearest_lon, labels, points = self.get_draught_forecast_tuple(lat, lng, ref_date_str, timescale)

        return {
            "location": {"lat": nearest_lat, "lng": nearest_lon},
            "labels": labels,
            "data": {
                "dr_ens": self._clean_vals([p.dr_ens for p in points])
            }
        }

    @staticmethod
    def _clean_vals(vals) -> list[float | None]:
        """Rounds values and replaces placeholders/NaNs with None."""
        return [round(float(v), 2) if (v is not None and v != -99.0) else None for v in vals]
