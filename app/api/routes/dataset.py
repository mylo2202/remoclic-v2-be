from enum import Enum
from fastapi import APIRouter, Depends, Query, HTTPException
from app.api.dependencies import get_dataset_service
from app.services.dataset_service import DatasetService

class DatasetVariable(str, Enum):
    mild = "mild"
    mord = "mord"
    seve = "seve"
    dr_ens = "dr_ens"

router = APIRouter()

@router.get("/")
async def read_dataset(service: DatasetService = Depends(get_dataset_service)):
    """Read the NetCDF dataset and return its metadata."""
    return service.get_dataset_metadata()

@router.get("/point")
async def read_data_at_point(
    variable: DatasetVariable = Query(..., description="The data variable to extract"),
    lead: float = Query(..., description="Lead time"),
    timescale: float = Query(..., description="Timescale"),
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    service: DatasetService = Depends(get_dataset_service)
):
    """Read a specific variable value at a given point using nearest neighbor."""
    try:
        value = service.get_data_at_point(
            variable=variable.value,
            lead=lead,
            timescale=timescale,
            lat=lat,
            lon=lon
        )
        return {"variable": variable.value, "value": value}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/forecast")
async def get_forecast(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    service: DatasetService = Depends(get_dataset_service)
):
    """Get multi-month drought forecast for a location."""
    try:
        return service.get_forecast(lat=lat, lng=lng)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
