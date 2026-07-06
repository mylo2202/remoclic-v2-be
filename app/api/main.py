"""Main API router module combining all route definitions."""

from fastapi import APIRouter

from app.api.routes import drought, pr_t2

api_router = APIRouter()
api_router.include_router(drought.router, prefix="/drought", tags=["drought"])
api_router.include_router(pr_t2.router, prefix="/pr-t2", tags=["pr-t2"])
