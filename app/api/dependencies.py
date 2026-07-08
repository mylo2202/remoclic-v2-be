"""Module containing FastAPI dependencies for the application."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.drought_forecast_repository import DroughtForecastRepository
from app.repositories.monthly_clim_repository import MonthlyClimRepository
from app.repositories.pr_t2_forecast_repository import PrT2ForecastRepository
from app.services.drought_forecast_service import DroughtForecastService
from app.services.monthly_clim_service import MonthlyClimService
from app.services.pr_t2_forecast_service import PrT2ForecastService


def get_drought_forecast_repository(db: Session = Depends(get_db)) -> DroughtForecastRepository:
    """Dependency: Initialize the data access layer with database session."""
    return DroughtForecastRepository(db=db)


def get_drought_forecast_service(
        repository: DroughtForecastRepository = Depends(get_drought_forecast_repository),
) -> DroughtForecastService:
    """Dependency: Initialize the business logic layer with the repository."""
    return DroughtForecastService(repository=repository)


def get_pr_t2_forecast_repository(db: Session = Depends(get_db)) -> PrT2ForecastRepository:
    """Dependency: Initialize the PR/T2 data access layer with database session."""
    return PrT2ForecastRepository(db=db)


def get_pr_t2_forecast_service(
        repository: PrT2ForecastRepository = Depends(get_pr_t2_forecast_repository),
) -> PrT2ForecastService:
    """Dependency: Initialize the PR/T2 business logic layer with the repository."""
    return PrT2ForecastService(repository=repository)


def get_monthly_clim_repository(db: Session = Depends(get_db)) -> MonthlyClimRepository:
    """Dependency: Initialize the monthly climatology repository with database session."""
    return MonthlyClimRepository(db=db)


def get_monthly_clim_service(
        repository: MonthlyClimRepository = Depends(get_monthly_clim_repository),
) -> MonthlyClimService:
    """Dependency: Initialize the monthly climatology service with the repository."""
    return MonthlyClimService(repository=repository)
