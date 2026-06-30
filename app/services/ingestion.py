import logging
import math
import os
import re
import tempfile
import urllib.request
from datetime import datetime

import requests
import xarray as xr
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal, engine, Base
from app.models.draught_forecast import DroughtForecast

logger = logging.getLogger(__name__)


def init_db():
    """Ensures database tables are created."""
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)


def run_ingestion():
    """
    Main ingestion task: scans remote directory, identifies new/missing data files,
    downloads and parses them, and stores the results in the database.
    """
    init_db()
    db: Session = SessionLocal()
    try:
        base_url = settings.DATA_BASE_URL.rstrip('/')
        file_name = settings.DATA_FILE_NAME

        logger.info("Scanning for remote data files at %s", base_url)
        response = requests.get(base_url, timeout=15)
        response.raise_for_status()

        # Find all YYYYMM/ subdirectories and deduplicate preserving order
        all_matches = re.findall(r'(\d{6})/', response.text)
        subdirs = list(dict.fromkeys(all_matches))
        if not subdirs:
            logger.warning("No YYYYMM subdirectories found on remote server.")
            return

        logger.info("Found %d directories: %s", len(subdirs), subdirs)

        # Get already ingested ref_dates from database
        existing_dates_query = db.execute(select(DroughtForecast.ref_date.distinct())).scalars().all()
        existing_dates = {d.strftime("%Y%m") for d in existing_dates_query}

        # Determine which directories need ingestion
        missing_subdirs = [s for s in subdirs if s not in existing_dates]

        if not missing_subdirs:
            logger.info("Database is up-to-date. No new files to ingest.")
            return

        logger.info("Directories to ingest: %s", missing_subdirs)

        for subdir in sorted(missing_subdirs):
            file_url = f"{base_url}/{subdir}/{file_name}"
            logger.info("Processing file: %s", file_url)
            try:
                ingest_file(db, file_url, subdir)
                logger.info("Successfully ingested %s", file_url)
            except Exception as e:
                db.rollback()
                logger.error("Failed to ingest %s: %s", file_url, e, exc_info=True)

    finally:
        db.close()


def ingest_file(db: Session, url: str, subdir_name: str):
    """Downloads a single NetCDF file, parses it, and bulk inserts into DB."""
    fd, temp_path = tempfile.mkstemp(suffix=".nc")
    os.close(fd)

    try:
        logger.info("Downloading temp file from %s", url)
        urllib.request.urlretrieve(url, temp_path)

        # Open and load dataset
        ds = xr.open_dataset(temp_path, decode_times=False)
        ds.load()
        ds.close()

        # Parse ref_date
        ref_date_attr = ds.attrs.get("ref_date")
        if ref_date_attr:
            # ref_date is e.g. 20260301 or 202603 (int or str)
            ref_date_str = str(ref_date_attr)
            if len(ref_date_str) == 8:
                ref_date = datetime.strptime(ref_date_str, "%Y%m%d").date()
            elif len(ref_date_str) == 6:
                ref_date = datetime.strptime(ref_date_str, "%Y%m").date()
            else:
                ref_date = datetime.strptime(subdir_name, "%Y%m").date()
        else:
            ref_date = datetime.strptime(subdir_name, "%Y%m").date()

        # Clean existing data for this ref_date to avoid duplicates if re-running
        db.execute(delete(DroughtForecast).where(DroughtForecast.ref_date == ref_date))
        db.commit()

        # Extract coordinates and dimensions
        timescales = ds["timescale"].values
        leads = ds["lead"].values
        lats = ds["lat"].values
        lons = ds["lon"].values

        # Transpose variables to a standard order ('timescale', 'lead', 'lat', 'lon')
        # to ensure that loop indexing is correct regardless of file dimension order.
        da_mild = ds["mild"].transpose("timescale", "lead", "lat", "lon")
        da_mord = ds["mord"].transpose("timescale", "lead", "lat", "lon")
        da_seve = ds["seve"].transpose("timescale", "lead", "lat", "lon")
        da_dr_ens = ds["dr_ens"].transpose("timescale", "lead", "lat", "lon")

        # Prepare records for bulk insert
        records = []
        for t_idx, timescale in enumerate(timescales):
            for l_idx, lead in enumerate(leads):
                for lat_idx, lat in enumerate(lats):
                    for lon_idx, lon in enumerate(lons):
                        # Extract variable values from transposed DataArrays
                        mild_val = float(da_mild[t_idx, l_idx, lat_idx, lon_idx].values)
                        mord_val = float(da_mord[t_idx, l_idx, lat_idx, lon_idx].values)
                        seve_val = float(da_seve[t_idx, l_idx, lat_idx, lon_idx].values)
                        dr_ens_val = float(da_dr_ens[t_idx, l_idx, lat_idx, lon_idx].values)

                        # Convert typical NetCDF fill values (-99.0 or NaN) to None
                        mild = mild_val if (mild_val != -99.0 and not math.isnan(mild_val)) else None
                        mord = mord_val if (mord_val != -99.0 and not math.isnan(mord_val)) else None
                        seve = seve_val if (seve_val != -99.0 and not math.isnan(seve_val)) else None
                        dr_ens = dr_ens_val if (dr_ens_val != -99.0 and not math.isnan(dr_ens_val)) else None

                        # Skip inserting records that do not contain any forecast data
                        if mild is None and mord is None and seve is None and dr_ens is None:
                            continue

                        records.append({
                            "ref_date": ref_date,
                            "lat": float(lat),
                            "lon": float(lon),
                            "timescale": float(timescale),
                            "lead": int(lead),
                            "mild": mild,
                            "mord": mord,
                            "seve": seve,
                            "dr_ens": dr_ens
                        })

        # Bulk insert
        if records:
            logger.info("Inserting %d records for ref_date %s", len(records), ref_date)
            # Batch size of 5000 to balance memory and roundtrips
            batch_size = 5000
            for i in range(0, len(records), batch_size):
                db.bulk_insert_mappings(DroughtForecast, records[i:i + batch_size])
            db.commit()

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
