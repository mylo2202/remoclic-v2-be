import hashlib
import logging
import math
import os
import tempfile
import urllib.request
from datetime import datetime

import requests
import xarray as xr
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from core.database import init_db
from app.models.monthly_clim_model import MonthlyClimModel
from app.models.monthly_clim_observed import MonthlyClimObserved
from app.models.monthly_clim_ingestion_state import MonthlyClimIngestionState

logger = logging.getLogger(__name__)

def run_monthly_clim_ingestion():
    """
    Main ingestion task for monthly climatological model and observed datasets.
    """
    init_db()
    db: Session = SessionLocal()
    try:
        file_url = f"{settings.MONTHLY_CLIM_DATA_URL.rstrip('/')}/{settings.MONTHLY_CLIM_DATA_FILE_NAME}"
        logger.info("Processing monthly climate file: %s", file_url)
        ingest_monthly_clim_file(db, file_url)
        logger.info("Successfully ingested monthly climate file")
    except Exception as e:
        db.rollback()
        logger.error("Failed to ingest monthly climate file: %s", e, exc_info=True)
    finally:
        db.close()


def compute_sha256_checksum(file_path: str) -> str:
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def get_remote_file_metadata(url: str) -> tuple[str | None, str | None]:
    try:
        response = requests.head(url, allow_redirects=True, timeout=15)
        response.raise_for_status()
        headers = response.headers
        return headers.get("ETag"), headers.get("Last-Modified")
    except Exception as e:
        logger.warning("Unable to fetch remote metadata for %s: %s", url, e)
        return None, None


def get_monthly_clim_state(db: Session, file_name: str):
    return db.execute(
        select(MonthlyClimIngestionState).where(MonthlyClimIngestionState.file_name == file_name)
    ).scalars().one_or_none()


def upsert_monthly_clim_state(
    db: Session,
    file_name: str,
    source_url: str,
    etag: str | None,
    last_modified: str | None,
    checksum: str,
):
    state = get_monthly_clim_state(db, file_name)
    if state:
        state.source_url = source_url
        state.etag = etag
        state.last_modified = last_modified
        state.checksum = checksum
        state.ingested_at = datetime.utcnow()
        db.add(state)
    else:
        db.add(MonthlyClimIngestionState(
            file_name=file_name,
            source_url=source_url,
            etag=etag,
            last_modified=last_modified,
            checksum=checksum,
            ingested_at=datetime.utcnow(),
        ))
    db.commit()


def ingest_monthly_clim_file(db: Session, url: str) -> bool:
    """Downloads a single NetCDF file, parses it, and bulk inserts into DB."""
    file_name = os.path.basename(url)
    etag, last_modified = get_remote_file_metadata(url)
    existing_state = get_monthly_clim_state(db, file_name)

    if existing_state:
        if (etag and existing_state.etag and etag == existing_state.etag) or (
            last_modified and existing_state.last_modified and last_modified == existing_state.last_modified
        ):
            logger.info(
                "Monthly climate file %s unchanged by remote metadata, skipping ingestion.",
                file_name,
            )
            return False

    fd, temp_path = tempfile.mkstemp(suffix=".nc")
    os.close(fd)

    try:
        logger.info("Downloading temp file from %s", url)
        urllib.request.urlretrieve(url, temp_path)

        checksum = compute_sha256_checksum(temp_path)
        if existing_state and existing_state.checksum == checksum:
            logger.info("Monthly climate file %s unchanged by checksum, skipping ingestion.", file_name)
            return False

        # Open and load dataset
        ds = xr.open_dataset(temp_path, decode_times=False)
        ds.load()
        ds.close()

        # Clear existing monthly climate data before ingesting the new file.
        db.execute(delete(MonthlyClimModel))
        db.execute(delete(MonthlyClimObserved))
        db.commit()

        months = ds["month"].values
        leads = ds["lead"].values
        lats = ds["lat"].values
        lons = ds["lon"].values

        da_pr_m = ds["pr_m"].transpose("month", "lead", "lat", "lon")
        da_t2_m = ds["t2_m"].transpose("month", "lead", "lat", "lon")
        da_pr_o = ds["pr_o"].transpose("month", "lat", "lon")
        da_t2_o = ds["t2_o"].transpose("month", "lat", "lon")

        model_records = []
        observed_records = []

        for m_idx, month in enumerate(months):
            for l_idx, lead in enumerate(leads):
                for lat_idx, lat in enumerate(lats):
                    for lon_idx, lon in enumerate(lons):
                        pr_m_val = float(da_pr_m[m_idx, l_idx, lat_idx, lon_idx].values)
                        t2_m_val = float(da_t2_m[m_idx, l_idx, lat_idx, lon_idx].values)

                        pr_m = pr_m_val if (pr_m_val != -99.0 and pr_m_val != 0.0 and not math.isnan(pr_m_val)) else None
                        t2_m = t2_m_val if (t2_m_val != -99.0 and t2_m_val != 0.0 and not math.isnan(t2_m_val)) else None

                        if pr_m is None or t2_m is None:
                            continue

                        model_records.append({
                            "month": int(month),
                            "lead": int(lead),
                            "lat": float(lat),
                            "lon": float(lon),
                            "pr_m": pr_m,
                            "t2_m": t2_m,
                        })

        for m_idx, month in enumerate(months):
            for lat_idx, lat in enumerate(lats):
                for lon_idx, lon in enumerate(lons):
                    pr_o_val = float(da_pr_o[m_idx, lat_idx, lon_idx].values)
                    t2_o_val = float(da_t2_o[m_idx, lat_idx, lon_idx].values)

                    pr_o = pr_o_val if (pr_o_val != -99.0 and pr_o_val != 0.0 and not math.isnan(pr_o_val)) else None
                    t2_o = t2_o_val if (t2_o_val != -99.0 and t2_o_val != 0.0 and not math.isnan(t2_o_val)) else None

                    if pr_o is None or t2_o is None:
                        continue

                    observed_records.append({
                        "month": int(month),
                        "lat": float(lat),
                        "lon": float(lon),
                        "pr_o": pr_o,
                        "t2_o": t2_o,
                    })

        if model_records:
            logger.info("Inserting %d model records", len(model_records))
            batch_size = 5000
            for i in range(0, len(model_records), batch_size):
                db.bulk_insert_mappings(MonthlyClimModel, model_records[i:i + batch_size])
            db.commit()

        if observed_records:
            logger.info("Inserting %d observed records", len(observed_records))
            batch_size = 5000
            for i in range(0, len(observed_records), batch_size):
                db.bulk_insert_mappings(MonthlyClimObserved, observed_records[i:i + batch_size])
            db.commit()

        upsert_monthly_clim_state(
            db,
            file_name=file_name,
            source_url=url,
            etag=etag,
            last_modified=last_modified,
            checksum=checksum,
        )

        return True

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
