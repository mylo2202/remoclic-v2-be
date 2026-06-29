"""Module containing FastAPI dependencies for the application."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.netcdf_repository import NetCDFRepository
from app.services.dataset_service import DatasetService


def get_netcdf_repository(db: Session = Depends(get_db)) -> NetCDFRepository:
    """Dependency: Initialize the data access layer with database session."""
    return NetCDFRepository(db=db)


def get_dataset_service(
        repository: NetCDFRepository = Depends(get_netcdf_repository),
) -> DatasetService:
    """Dependency: Initialize the business logic layer with the repository."""
    return DatasetService(repository=repository)
