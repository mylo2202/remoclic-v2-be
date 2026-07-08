import os
import shutil
import sys
from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import Base
from app.services.pr_t2_ingestion_service import ingest_pr_t2_file
from app.repositories.pr_t2_forecast_repository import PrT2ForecastRepository
from app.services.pr_t2_forecast_service import PrT2ForecastService

# Path to the test SQLite database
DB_PATH = "test_pr_t2_ingestion.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"


@pytest.fixture(scope="module")
def db_session():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables
    Base.metadata.create_all(bind=engine)

    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()


def test_pr_t2_ingestion_and_forecast(db_session):
    """Test PR/T2 ingestion and verify forecast retrieval functionality."""
    sample_nc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../samples/Forecast_Ope_Pr_T2_and_Anomaly.nc"))

    # Mock urllib.request.urlretrieve to copy the local sample file instead of downloading
    def mock_urlretrieve(_url, temp_path):
        shutil.copy(sample_nc_path, temp_path)

    with patch("urllib.request.urlretrieve", side_effect=mock_urlretrieve):
        # Ingest the file using a dummy URL and subdir name
        ingest_pr_t2_file(db_session, "http://example.com/202605/Forecast_Ope_Pr_T2_and_Anomaly.nc", "202605")

    # Verify that data was ingested
    repository = PrT2ForecastRepository(db_session)
    latest_date = repository.get_latest_ref_date()
    assert latest_date == date(2026, 5, 1)

    # Query a coordinate (e.g., near Bangkok lat=13.7, lon=100.5)
    # The nearest grid point in NetCDF is lat=13.875, lon=101.125
    nearest_coord = repository.find_nearest_grid_point(13.7, 100.5)
    assert nearest_coord is not None
    nearest_lat, nearest_lon = nearest_coord

    # Initialize the service
    service = PrT2ForecastService(repository)

    # Test precipitation forecast
    precip_result = service.get_precipitation_forecast(
        lat=13.7,
        lng=100.5,
        ref_date_str="202605"
    )
    assert precip_result["location"]["lat"] == nearest_lat
    assert precip_result["location"]["lng"] == nearest_lon
    assert "pr" in precip_result["data"]
    assert "pr_ano" in precip_result["data"]
    assert "pr_fcs" in precip_result["data"]
    assert len(precip_result["data"]["pr"]) > 0  # Should have lead times

    # Test temperature forecast
    temp_result = service.get_temperature_forecast(
        lat=13.7,
        lng=100.5,
        ref_date_str="202605"
    )
    assert temp_result["location"]["lat"] == nearest_lat
    assert temp_result["location"]["lng"] == nearest_lon
    assert "t2" in temp_result["data"]
    assert "t2_ano" in temp_result["data"]
    assert "t2_fcs" in temp_result["data"]
    assert len(temp_result["data"]["t2"]) > 0  # Should have lead times

    # Test combined forecast
    combined_result = service.get_combined_forecast(
        lat=13.7,
        lng=100.5,
        ref_date_str="202605"
    )
    assert combined_result["location"]["lat"] == nearest_lat
    assert combined_result["location"]["lng"] == nearest_lon
    assert "precipitation" in combined_result
    assert "temperature" in combined_result
    assert "pr" in combined_result["precipitation"]
    assert "t2" in combined_result["temperature"]
    assert len(combined_result["precipitation"]["pr"]) > 0
    assert len(combined_result["temperature"]["t2"]) > 0

def test_pr_t2_nearest_grid_point(db_session):
    """Test finding the nearest grid point for a given coordinate."""
    sample_nc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../samples/Forecast_Ope_Pr_T2_and_Anomaly.nc"))

    def mock_urlretrieve(_url, temp_path):
        shutil.copy(sample_nc_path, temp_path)

    with patch("urllib.request.urlretrieve", side_effect=mock_urlretrieve):
        ingest_pr_t2_file(db_session, "http://example.com/202605/Forecast_Ope_Pr_T2_and_Anomaly.nc", "202605")

    repository = PrT2ForecastRepository(db_session)

    # Test multiple coordinates to verify nearest grid point finding
    test_coords = [
        (13.7, 100.5),  # Bangkok area
        (20.0, 106.0),  # Hanoi area
        (10.0, 105.0),  # Central Vietnam
    ]

    for lat, lon in test_coords:
        nearest = repository.find_nearest_grid_point(lat, lon)
        assert nearest is not None
        assert isinstance(nearest[0], float)
        assert isinstance(nearest[1], float)


def test_pr_t2_active_ref_dates(db_session):
    """Test retrieving all distinct reference dates."""
    sample_nc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../samples/Forecast_Ope_Pr_T2_and_Anomaly.nc"))

    def mock_urlretrieve(_url, temp_path):
        shutil.copy(sample_nc_path, temp_path)

    with patch("urllib.request.urlretrieve", side_effect=mock_urlretrieve):
        ingest_pr_t2_file(db_session, "http://example.com/202605/Forecast_Ope_Pr_T2_and_Anomaly.nc", "202605")

    repository = PrT2ForecastRepository(db_session)
    active_ref_dates = repository.get_active_ref_dates()

    assert len(active_ref_dates) > 0
    assert date(2026, 5, 1) in active_ref_dates


def test_pr_t2_forecast_by_ref_date_string(db_session):
    """Test retrieving forecasts using different ref_date string formats."""
    sample_nc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../samples/Forecast_Ope_Pr_T2_and_Anomaly.nc"))

    def mock_urlretrieve(_url, temp_path):
        shutil.copy(sample_nc_path, temp_path)

    with patch("urllib.request.urlretrieve", side_effect=mock_urlretrieve):
        ingest_pr_t2_file(db_session, "http://example.com/202605/Forecast_Ope_Pr_T2_and_Anomaly.nc", "202605")

    repository = PrT2ForecastRepository(db_session)
    service = PrT2ForecastService(repository)

    # Test with YYYYMM format
    result_yyyymm = service.get_precipitation_forecast(
        lat=13.7,
        lng=100.5,
        ref_date_str="202605"
    )
    assert result_yyyymm["ref_date"] == date(2026, 5, 1)

    # Test with YYYY-MM-DD format
    result_yyyy_mm_dd = service.get_precipitation_forecast(
        lat=13.7,
        lng=100.5,
        ref_date_str="2026-05-01"
    )
    assert result_yyyy_mm_dd["ref_date"] == date(2026, 5, 1)

    # Both should return the same data
    assert result_yyyymm["data"]["pr"] == result_yyyy_mm_dd["data"]["pr"]


def test_pr_t2_invalid_ref_date_format(db_session):
    """Test that invalid ref_date formats raise appropriate errors."""
    sample_nc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../samples/Forecast_Ope_Pr_T2_and_Anomaly.nc"))

    def mock_urlretrieve(_url, temp_path):
        shutil.copy(sample_nc_path, temp_path)

    with patch("urllib.request.urlretrieve", side_effect=mock_urlretrieve):
        ingest_pr_t2_file(db_session, "http://example.com/202605/Forecast_Ope_Pr_T2_and_Anomaly.nc", "202605")

    repository = PrT2ForecastRepository(db_session)
    service = PrT2ForecastService(repository)

    # Test invalid format
    with pytest.raises(ValueError, match="Invalid reference date format"):
        service.get_precipitation_forecast(
            lat=13.7,
            lng=100.5,
            ref_date_str="invalid_date"
        )
