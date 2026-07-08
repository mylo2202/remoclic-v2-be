import logging

from app.repositories.monthly_clim_repository import MonthlyClimRepository

logger = logging.getLogger(__name__)

MONTH_LABELS = ["T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08", "T09", "T10", "T11", "T12"]


def _clean_vals(vals) -> list[float | None]:
    return [round(float(v), 2) if (v is not None and v != -99.0) else None for v in vals]


class MonthlyClimService:
    """Business logic for monthly climatology observed and model retrieval."""

    def __init__(self, repository: MonthlyClimRepository):
        self.repository = repository

    def _resolve_nearest(self, lat: float, lng: float) -> tuple[float, float]:
        coord = self.repository.find_nearest_grid_point(lat, lng)
        if not coord:
            raise ValueError("No grid coordinates found in database.")
        return coord

    def get_observed_monthly(self, lat: float, lng: float) -> dict:
        """Return observed monthly climatology for a nearest grid point."""
        nearest_lat, nearest_lon = self._resolve_nearest(lat, lng)
        points = self.repository.get_observed_points(nearest_lat, nearest_lon)
        if not points:
            raise ValueError(f"No observed monthly climatology found for coords ({nearest_lat}, {nearest_lon})")

        pr_o = _clean_vals([p.pr_o for p in points])
        t2_o = _clean_vals([p.t2_o for p in points])

        return {
            "location": {"lat": nearest_lat, "lng": nearest_lon},
            "labels": MONTH_LABELS,
            "data": {"pr_o": pr_o, "t2_o": t2_o},
        }

    def get_model_monthly(self, lat: float, lng: float, lead: int) -> dict:
        """Return model monthly climatology for a nearest grid point and lead."""
        nearest_lat, nearest_lon = self._resolve_nearest(lat, lng)
        points = self.repository.get_model_points(nearest_lat, nearest_lon, lead)
        if not points:
            raise ValueError(
                f"No model monthly climatology found for coords ({nearest_lat}, {nearest_lon}) and lead {lead}")

        pr_m = _clean_vals([p.pr_m for p in points])
        t2_m = _clean_vals([p.t2_m for p in points])

        return {
            "location": {"lat": nearest_lat, "lng": nearest_lon},
            "lead": lead,
            "labels": MONTH_LABELS,
            "data": {"pr_m": pr_m, "t2_m": t2_m},
        }
