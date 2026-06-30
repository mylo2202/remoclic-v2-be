"""Module defining API routes for dataset operations."""

from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.dependencies import get_draught_forecast_service
from app.services.draught_forecast_service import DroughtForecastService

router = APIRouter()


@router.get("/probability-forecast")
async def get_probability_forecast(
        lat: float = Query(..., description="Latitude"),
        lng: float = Query(..., description="Longitude"),
        ref_date: str = Query(None, description="Reference date (YYYY-MM-DD or YYYYMM)"),
        timescale: float = Query(1.0, description="Probability forecast timescale"),
        service: DroughtForecastService = Depends(get_draught_forecast_service)
):
    """Get multi-month drought probability forecast for a location."""
    try:
        return service.get_probability_forecast(lat=lat, lng=lng, ref_date_str=ref_date, timescale=timescale)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/event-forecast")
async def get_event_forecast(
        lat: float = Query(..., description="Latitude"),
        lng: float = Query(..., description="Longitude"),
        ref_date: str = Query(None, description="Reference date (YYYY-MM-DD or YYYYMM)"),
        timescale: float = Query(1.0, description="Event forecast timescale"),
        service: DroughtForecastService = Depends(get_draught_forecast_service)
):
    """Get multi-month drought event forecast for a location."""
    try:
        return service.get_event_forecast(lat=lat, lng=lng, ref_date_str=ref_date, timescale=timescale)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e
