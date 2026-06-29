"""Module defining API routes for dataset operations."""

from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.dependencies import get_dataset_service
from app.services.dataset_service import DatasetService

router = APIRouter()


@router.get("/")
async def read_dataset(service: DatasetService = Depends(get_dataset_service)):
    """Read the NetCDF dataset and return its metadata."""
    return service.get_dataset_metadata()


@router.get("/forecast")
async def get_forecast(
        lat: float = Query(..., description="Latitude"),
        lng: float = Query(..., description="Longitude"),
        ref_date: str = Query(None, description="Reference date (YYYY-MM-DD or YYYYMM)"),
        timescale: float = Query(1.0, description="Forecast timescale"),
        service: DatasetService = Depends(get_dataset_service)
):
    """Get multi-month drought forecast for a location."""
    try:
        return service.get_forecast(lat=lat, lng=lng, ref_date_str=ref_date, timescale=timescale)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e
