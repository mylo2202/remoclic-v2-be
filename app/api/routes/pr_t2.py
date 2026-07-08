from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_pr_t2_forecast_service
from app.request_models.pr_t2_ref_date_toggle_request import PrT2RefDateToggleRequest
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
async def get_active_ref_dates(
        service: PrT2ForecastService = Depends(get_pr_t2_forecast_service),
):
    """Get active reference dates exposed to clients."""
    try:
        return service.get_active_ref_dates()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/ref-dates/toggle")
async def toggle_ref_date_status(
        payload: PrT2RefDateToggleRequest,
        service: PrT2ForecastService = Depends(get_pr_t2_forecast_service),
):
    """Enable or disable a PR/T2 reference date for public API access."""
    try:
        service.set_ref_date_status(payload.ref_date, payload.is_active)
        return {"ref_date": payload.ref_date, "is_active": payload.is_active}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e
