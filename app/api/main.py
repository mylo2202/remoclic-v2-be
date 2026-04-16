from fastapi import APIRouter

from app.api.routes import dataset, utils

api_router = APIRouter()
api_router.include_router(utils.router, tags=["utils"])
api_router.include_router(dataset.router, prefix="/dataset", tags=["dataset"])
