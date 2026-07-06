"""Module containing FastAPI dependencies for the application."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.drought_forecast_repository import DroughtForecastRepository
from app.services.drought_forecast_service import DroughtForecastService


def get_drought_forecast_repository(db: Session = Depends(get_db)) -> DroughtForecastRepository:
    """Dependency: Initialize the data access layer with database session."""
    return DroughtForecastRepository(db=db)


def get_drought_forecast_service(
        repository: DroughtForecastRepository = Depends(get_drought_forecast_repository),
) -> DroughtForecastService:
    """Dependency: Initialize the business logic layer with the repository."""
    return DroughtForecastService(repository=repository)
