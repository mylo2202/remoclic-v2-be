from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.dependencies import get_monthly_clim_service
from app.services.monthly_clim_service import MonthlyClimService

router = APIRouter()


@router.get("/observed")
async def get_monthly_observed(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    service: MonthlyClimService = Depends(get_monthly_clim_service),
):
    try:
        return service.get_observed_monthly(lat=lat, lng=lng)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/model")
async def get_monthly_model(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    lead: int = Query(..., description="Lead offset (months)"),
    service: MonthlyClimService = Depends(get_monthly_clim_service),
):
    try:
        return service.get_model_monthly(lat=lat, lng=lng, lead=lead)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e
