"""Main API router module combining all route definitions."""

from fastapi import APIRouter

from app.api.routes import draught

api_router = APIRouter()
api_router.include_router(draught.router, prefix="/draught", tags=["draught"])
