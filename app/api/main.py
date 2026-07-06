"""Main API router module combining all route definitions."""

from fastapi import APIRouter

from app.api.routes import drought

api_router = APIRouter()
api_router.include_router(drought.router, prefix="/drought", tags=["drought"])
