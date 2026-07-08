import logging
from datetime import datetime, date
from typing import Optional

from app.models import PrT2Forecast
from app.repositories.pr_t2_forecast_repository import PrT2ForecastRepository

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


def _clean_vals(vals) -> list[float | None]:
    """Rounds values and replaces placeholders/NaNs with None."""
    return [round(float(v), 2) if (v is not None and v != -99.0) else None for v in vals]


class PrT2ForecastService:
    """Module providing core business logic for precipitation and temperature forecast operations using database storage."""

    def __init__(self, repository: PrT2ForecastRepository):
        self.repository = repository

    def get_pr_t2_forecast_tuple(
            self,
            lat: float,
            lng: float,
            ref_date_str: Optional[str] = None,
    ) -> tuple[float, float, date, list[str], list[PrT2Forecast]]:
        """Extract precipitation and temperature forecast tuple."""
        # Resolve ref_date
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
                raise ValueError(
                    "No precipitation and temperature forecast data is currently available in the database.")

        if not self.repository.is_ref_date_active(ref_date):
            raise ValueError(f"Reference date {ref_date} is temporarily unavailable.")

        # Find nearest grid point
        coord = self.repository.find_nearest_grid_point(lat, lng)
        if not coord:
            raise ValueError(f"No grid coordinates found in database.")

        nearest_lat, nearest_lon = coord

        # Retrieve forecast points
        points = self.repository.get_forecast_points(
            lat=nearest_lat, lon=nearest_lon, ref_date=ref_date
        )

        if not points:
            raise ValueError(
                f"No forecast data found for coords ({nearest_lat}, {nearest_lon}) and date {ref_date}"
            )

        # Format response
        leads = [p.lead for p in points]
        labels = _generate_date_labels(ref_date, leads)

        return nearest_lat, nearest_lon, ref_date, labels, points

    def get_precipitation_forecast(
            self,
            lat: float,
            lng: float,
            ref_date_str: Optional[str] = None,
    ) -> dict:
        """Extract multi-month precipitation forecast (pr, pr_ano, pr_fcs) from database."""
        nearest_lat, nearest_lon, ref_date, labels, points = self.get_pr_t2_forecast_tuple(lat, lng, ref_date_str)

        return {
            "location": {"lat": nearest_lat, "lng": nearest_lon},
            "ref_date": ref_date,
            "labels": labels,
            "data": {
                "pr": _clean_vals([p.pr for p in points]),
                "pr_ano": _clean_vals([p.pr_ano for p in points]),
                "pr_fcs": _clean_vals([p.pr_fcs for p in points])
            }
        }

    def get_temperature_forecast(
            self,
            lat: float,
            lng: float,
            ref_date_str: Optional[str] = None,
    ) -> dict:
        """Extract multi-month temperature forecast (t2, t2_ano, t2_fcs) from database."""
        nearest_lat, nearest_lon, ref_date, labels, points = self.get_pr_t2_forecast_tuple(lat, lng, ref_date_str)

        return {
            "location": {"lat": nearest_lat, "lng": nearest_lon},
            "ref_date": ref_date,
            "labels": labels,
            "data": {
                "t2": _clean_vals([p.t2 for p in points]),
                "t2_ano": _clean_vals([p.t2_ano for p in points]),
                "t2_fcs": _clean_vals([p.t2_fcs for p in points])
            }
        }

    def get_combined_forecast(
            self,
            lat: float,
            lng: float,
            ref_date_str: Optional[str] = None,
    ) -> dict:
        """Extract combined precipitation and temperature forecast from database."""
        nearest_lat, nearest_lon, ref_date, labels, points = self.get_pr_t2_forecast_tuple(lat, lng, ref_date_str)

        return {
            "location": {"lat": nearest_lat, "lng": nearest_lon},
            "ref_date": ref_date,
            "labels": labels,
            "precipitation": {
                "pr": _clean_vals([p.pr for p in points]),
                "pr_ano": _clean_vals([p.pr_ano for p in points]),
                "pr_fcs": _clean_vals([p.pr_fcs for p in points])
            },
            "temperature": {
                "t2": _clean_vals([p.t2 for p in points]),
                "t2_ano": _clean_vals([p.t2_ano for p in points]),
                "t2_fcs": _clean_vals([p.t2_fcs for p in points])
            }
        }

    def get_active_ref_dates(self) -> list[date]:
        """Retrieves all active reference dates from the database."""
        return self.repository.get_active_ref_dates()

    def set_ref_date_status(self, ref_date_str: str, is_active: bool) -> None:
        """Enable or disable a PR/T2 reference date for public API access."""
        try:
            self.repository.set_ref_date_status(ref_date_str, is_active)
        except ValueError as e:
            raise ValueError(f"Invalid reference date format: {ref_date_str}") from e
