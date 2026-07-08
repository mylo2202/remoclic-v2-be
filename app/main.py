import logging
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.main_router import api_router
from app.core.config import settings
from app.core.database import init_db
from app.services.drought_ingestion_service import run_drought_ingestion
from app.services.monthly_clim_ingestion_service import run_monthly_clim_ingestion
from app.services.pr_t2_ingestion_service import run_pr_t2_ingestion

# Configure root logging based on app settings
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    logger.info(fastapi_app.title)

    # Initialize DB tables on startup
    init_db()

    # Configure background scheduler
    scheduler = BackgroundScheduler()
    # Run daily (every 24 hours)
    scheduler.add_job(run_drought_ingestion, 'interval', days=1, id='drought_ingestion_task')
    scheduler.add_job(run_pr_t2_ingestion, 'interval', days=1, id='pr_t2_ingestion_task')
    scheduler.add_job(run_monthly_clim_ingestion, 'interval', days=1, id='monthly_clim_ingestion_task')
    # Run once immediately on startup to catch up
    scheduler.add_job(run_drought_ingestion, 'date', run_date=datetime.now(), id='drought_ingestion_startup')
    scheduler.add_job(run_pr_t2_ingestion, 'date', run_date=datetime.now(), id='pr_t2_ingestion_startup')
    scheduler.add_job(run_monthly_clim_ingestion, 'date', run_date=datetime.now(), id='monthly_clim_ingestion_startup')

    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown()


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.include_router(api_router)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
