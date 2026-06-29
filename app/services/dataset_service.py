import logging
from datetime import datetime, date
from typing import Optional

from app.repositories.netcdf_repository import NetCDFRepository

logger = logging.getLogger(__name__)


class DatasetService:
    """Module providing core business logic for dataset operations using database storage."""

    def __init__(self, repository: NetCDFRepository):
        self.repository = repository

    def get_dataset_metadata(self) -> dict:
        """Extracts dataset metadata from the database records."""
        latest_date = self.repository.get_latest_ref_date()
        available_dates = self.repository.get_available_ref_dates()
        total_records = self.repository.get_total_records()

        return {
            "dataset_info": "Successfully loaded database dataset",
            "total_records": total_records,
            "latest_reference_date": latest_date.strftime("%Y-%m-%d") if latest_date else None,
            "available_reference_dates": [d.strftime("%Y-%m-%d") for d in available_dates],
            "variables": ["mild", "mord", "seve"]
        }

    def get_forecast(self, lat: float, lng: float, ref_date_str: Optional[str] = None) -> dict:
        """Extract multi-month forecast for mild, mord, and seve drought levels from database."""
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
                raise ValueError("No forecast data is currently available in the database.")

        # 2. Find nearest grid point
        coord = self.repository.find_nearest_grid_point(lat, lng)
        if not coord:
            raise ValueError(f"No grid coordinates found in database.")

        nearest_lat, nearest_lon = coord

        # 3. Retrieve forecast points
        points = self.repository.get_forecast_points(
            lat=nearest_lat, lon=nearest_lon, ref_date=ref_date, timescale=1.0
        )

        if not points:
            raise ValueError(
                f"No forecast data found for coords ({nearest_lat}, {nearest_lon}) and date {ref_date}"
            )

        # 4. Format response
        leads = [p.lead for p in points]
        labels = self._generate_date_labels(ref_date, leads)

        return {
            "location": {"lat": nearest_lat, "lng": nearest_lon},
            "labels": labels,
            "data": {
                "mild": self._clean_vals([p.mild for p in points]),
                "mord": self._clean_vals([p.mord for p in points]),
                "seve": self._clean_vals([p.seve for p in points])
            }
        }

    def _generate_date_labels(self, ref_date: date, leads: list[int]) -> list[str]:
        """Generates human-readable labels from reference date and lead offsets."""
        labels = []
        for lead in leads:
            months_to_add = int(lead)
            new_month = (ref_date.month + months_to_add - 1) % 12 + 1
            new_year = ref_date.year + (ref_date.month + months_to_add - 1) // 12
            labels.append(f"{new_month:02d}-{new_year}")
        return labels

    @staticmethod
    def _clean_vals(vals) -> list[float | None]:
        """Rounds values and replaces placeholders/NaNs with None."""
        return [round(float(v), 2) if (v is not None and v != -99.0) else None for v in vals]
