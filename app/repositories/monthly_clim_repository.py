import logging
from typing import Optional, List, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.monthly_clim_model import MonthlyClimModel
from app.models.monthly_clim_observed import MonthlyClimObserved

logger = logging.getLogger(__name__)


class MonthlyClimRepository:
    """Data access for monthly climatology model and observed tables."""

    def __init__(self, db: Session):
        self.db = db

    def find_nearest_grid_point(self, lat: float, lon: float) -> Optional[Tuple[float, float]]:
        """Find the nearest grid cell using observed coordinates as reference."""
        stmt = (
            select(MonthlyClimObserved.lat, MonthlyClimObserved.lon)
            .order_by(func.abs(MonthlyClimObserved.lat - lat) + func.abs(MonthlyClimObserved.lon - lon))
            .limit(1)
        )
        result = self.db.execute(stmt).first()
        return result if result else None

    def get_observed_points(self, lat: float, lon: float) -> List[MonthlyClimObserved]:
        """Return observed monthly climatology rows for a given grid point ordered by month."""
        stmt = (
            select(MonthlyClimObserved)
            .where(MonthlyClimObserved.lat == lat, MonthlyClimObserved.lon == lon)
            .order_by(MonthlyClimObserved.month.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_model_points(self, lat: float, lon: float, lead: int) -> List[MonthlyClimModel]:
        """Return model monthly climatology rows for a given grid point and lead ordered by month."""
        stmt = (
            select(MonthlyClimModel)
            .where(MonthlyClimModel.lat == lat, MonthlyClimModel.lon == lon, MonthlyClimModel.lead == lead)
            .order_by(MonthlyClimModel.month.asc())
        )
        return list(self.db.execute(stmt).scalars().all())
