"""Module containing FastAPI dependencies for the application."""

from fastapi import Depends
from app.repositories.netcdf_repository import NetCDFRepository
from app.services.dataset_service import DatasetService
from app.core.config import settings

def get_netcdf_repository() -> NetCDFRepository:
    """Dependency: Initialize the data access layer using the configured file path."""
    return NetCDFRepository(file_path=settings.FILE_PATH)

def get_dataset_service(
    repository: NetCDFRepository = Depends(get_netcdf_repository),
) -> DatasetService:
    """Dependency: Initialize the business logic layer with the repository."""
    return DatasetService(repository=repository)
