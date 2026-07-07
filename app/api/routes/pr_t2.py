from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_pr_t2_forecast_service
from app.services.pr_t2_forecast_service import PrT2ForecastService

router = APIRouter()


@router.get("/precipitation-forecast")
async def get_precipitation_forecast(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    ref_date: str = Query(None, description="Reference date (YYYY-MM-DD or YYYYMM)"),
    service: PrT2ForecastService = Depends(get_pr_t2_forecast_service),
):
    """Get multi-month precipitation forecast for a location."""
    try:
        return service.get_precipitation_forecast(lat=lat, lng=lng, ref_date_str=ref_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/temperature-forecast")
async def get_temperature_forecast(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    ref_date: str = Query(None, description="Reference date (YYYY-MM-DD or YYYYMM)"),
    service: PrT2ForecastService = Depends(get_pr_t2_forecast_service),
):
    """Get multi-month temperature forecast for a location."""
    try:
        return service.get_temperature_forecast(lat=lat, lng=lng, ref_date_str=ref_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/combined-forecast")
async def get_combined_forecast(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    ref_date: str = Query(None, description="Reference date (YYYY-MM-DD or YYYYMM)"),
    service: PrT2ForecastService = Depends(get_pr_t2_forecast_service),
):
    """Get combined precipitation and temperature forecast for a location."""
    try:
        return service.get_combined_forecast(lat=lat, lng=lng, ref_date_str=ref_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/ref-dates", response_model=List[date])
async def get_distinct_ref_dates(
    service: PrT2ForecastService = Depends(get_pr_t2_forecast_service),
):
    """Get distinct reference dates available in the database."""
    try:
        return service.get_distinct_ref_dates()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e
