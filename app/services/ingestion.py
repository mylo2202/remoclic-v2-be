import logging
import math
import os
import re
import tempfile
import urllib.request
from datetime import datetime, date
from typing import Any

import requests
import xarray as xr
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal, engine, Base
from app.models.drought_forecast import DroughtForecast
from app.models.monthly_clim_model import MonthlyClimModel
from app.models.monthly_clim_observed import MonthlyClimObserved
from app.models.pr_t2_forecast import PrT2Forecast

logger = logging.getLogger(__name__)


def init_db():
    """Ensures database tables are created."""
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)


def run_drought_ingestion():
    """
    Main ingestion task: scans remote directory, identifies new/missing data files,
    downloads and parses them, and stores the results in the database.
    """
    init_db()
    db: Session = SessionLocal()
    try:
        base_url = settings.DROUGHT_DATA_URL.rstrip('/')
        file_name = settings.DROUGHT_DATA_FILE_NAME

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
                ingest_drought_file(db, file_url, subdir)
                logger.info("Successfully ingested %s", file_url)
            except Exception as e:
                db.rollback()
                logger.error("Failed to ingest %s: %s", file_url, e, exc_info=True)

    finally:
        db.close()


def ingest_drought_file(db: Session, url: str, subdir_name: str):
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
        ref_date = parse_ref_date(ref_date_attr, subdir_name)

        # Clean existing data for this ref_date to avoid duplicates if re-running
        db.execute(delete(DroughtForecast).where(DroughtForecast.ref_date == ref_date))
        db.commit()

        # 4 mảng 4 chiều:
        # các biến: mild, mod, seve (xác suất, 0-100%), dr_ens (sự kiện tổng hợp, z-score)
        # các chiều: lat, lon, timescale, leadtime
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
                        if mild is None or mord is None or seve is None or dr_ens is None:
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


def run_pr_t2_ingestion():
    """
    Main ingestion task: scans remote directory, identifies new/missing data files,
    downloads and parses them, and stores the results in the database.
    """
    init_db()
    db: Session = SessionLocal()
    try:
        base_url = settings.PR_T2_DATA_URL.rstrip('/')
        file_name = settings.PR_T2_DATA_FILE_NAME

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
        existing_dates_query = db.execute(select(PrT2Forecast.ref_date.distinct())).scalars().all()
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
                ingest_pr_t2_file(db, file_url, subdir)
                logger.info("Successfully ingested %s", file_url)
            except Exception as e:
                db.rollback()
                logger.error("Failed to ingest %s: %s", file_url, e, exc_info=True)

    finally:
        db.close()


def ingest_pr_t2_file(db: Session, url: str, subdir_name: str):
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
        ref_date = parse_ref_date(ref_date_attr, subdir_name)

        # Clean existing data for this ref_date to avoid duplicates if re-running
        db.execute(delete(PrT2Forecast).where(PrT2Forecast.ref_date == ref_date))
        db.commit()

        # 6 mảng 3 chiều:
        # các biến: pr_ano, pr_fcs (dị thường, dự báo mưa, mm/tháng), t2_ano, t2_fcs (dị thường, dự báo nhiệt độ, C)
        # các chiều: lat, lon, leadtime
        leads = ds["lead"].values
        lats = ds["lat"].values
        lons = ds["lon"].values

        # Transpose variables to a standard order ('lead', 'lat', 'lon')
        # to ensure that loop indexing is correct regardless of file dimension order.
        da_pr = ds["pr"].transpose("lead", "lat", "lon")
        da_t2 = ds["t2"].transpose("lead", "lat", "lon")
        da_pr_ano = ds["pr_ano"].transpose("lead", "lat", "lon")
        da_t2_ano = ds["t2_ano"].transpose("lead", "lat", "lon")
        da_pr_fcs = ds["pr_fcs"].transpose("lead", "lat", "lon")
        da_t2_fcs = ds["t2_fcs"].transpose("lead", "lat", "lon")

        # Prepare records for bulk insert
        records = []
        for l_idx, lead in enumerate(leads):
            for lat_idx, lat in enumerate(lats):
                for lon_idx, lon in enumerate(lons):
                    # Extract variable values from transposed DataArrays
                    pr_val = float(da_pr[l_idx, lat_idx, lon_idx].values)
                    t2_val = float(da_t2[l_idx, lat_idx, lon_idx].values)
                    pr_ano_val = float(da_pr_ano[l_idx, lat_idx, lon_idx].values)
                    t2_ano_val = float(da_t2_ano[l_idx, lat_idx, lon_idx].values)
                    pr_fcs_val = float(da_pr_fcs[l_idx, lat_idx, lon_idx].values)
                    t2_fcs_val = float(da_t2_fcs[l_idx, lat_idx, lon_idx].values)

                    # Convert typical NetCDF fill values (-99.0 or NaN) to None
                    pr = pr_val if (pr_val != -99.0 and not math.isnan(pr_val)) else None
                    t2 = t2_val if (t2_val != -99.0 and not math.isnan(t2_val)) else None
                    pr_ano = pr_ano_val if (pr_ano_val != -99.0 and not math.isnan(pr_ano_val)) else None
                    t2_ano = t2_ano_val if (t2_ano_val != -99.0 and not math.isnan(t2_ano_val)) else None
                    pr_fcs = pr_fcs_val if (pr_fcs_val != -99.0 and not math.isnan(pr_fcs_val)) else None
                    t2_fcs = t2_fcs_val if (t2_fcs_val != -99.0 and not math.isnan(t2_fcs_val)) else None

                    # Skip inserting records that do not contain any forecast data
                    if pr is None or t2 is None or pr_ano is None or t2_ano is None or pr_fcs is None or t2_fcs is None:
                        continue

                    records.append({
                        "ref_date": ref_date,
                        "lat": float(lat),
                        "lon": float(lon),
                        "lead": int(lead),
                        "pr": pr,
                        "t2": t2,
                        "pr_ano": pr_ano,
                        "t2_ano": t2_ano,
                        "pr_fcs": pr_fcs,
                        "t2_fcs": t2_fcs,
                    })

        # Bulk insert
        if records:
            logger.info("Inserting %d records for ref_date %s", len(records), ref_date)
            # Batch size of 5000 to balance memory and roundtrips
            batch_size = 5000
            for i in range(0, len(records), batch_size):
                db.bulk_insert_mappings(PrT2Forecast, records[i:i + batch_size])
            db.commit()

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def parse_ref_date(ref_date_attr: Any | None, subdir_name: str) -> date:
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
    return ref_date


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


def ingest_monthly_clim_file(db: Session, url: str):
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

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
