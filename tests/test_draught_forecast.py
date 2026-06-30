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
from app.services.ingestion import ingest_file
from app.repositories.draught_forecast_repository import DroughtForecastRepository
from app.services.draught_forecast_service import DroughtForecastService

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db

# Path to the test SQLite database - we do not clean this up so the user can inspect it.
DB_PATH = "test_draught_forecast.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"


@pytest.fixture(scope="module")
def db_session():
    # Remove old DB if exists from previous manual runs, but do NOT clean up at the end of the test.
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_ingestion_and_forecast(db_session):
    sample_nc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../samples/Dr_Prob.nc"))

    # Mock urllib.request.urlretrieve to copy the local sample file instead of downloading
    def mock_urlretrieve(url, temp_path):
        shutil.copy(sample_nc_path, temp_path)

    with patch("urllib.request.urlretrieve", side_effect=mock_urlretrieve):
        # Ingest the file using a dummy URL and subdir name
        ingest_file(db_session, "http://example.com/202605/Dr_Prob.nc", "202605")

    # Verify that data was ingested
    repository = DroughtForecastRepository(db_session)
    latest_date = repository.get_latest_ref_date()
    assert latest_date == date(2026, 5, 1)

    # Query a coordinate (e.g., near Bangkok lat=13.7, lon=100.5)
    # The nearest grid point in NetCDF is lat=13.875, lon=101.125
    nearest_coord = repository.find_nearest_grid_point(13.7, 100.5)
    assert nearest_coord is not None
    nearest_lat, nearest_lon = nearest_coord

    # Initialize the service
    service = DroughtForecastService(repository)

    # Test probability forecast
    prob_result = service.get_probability_forecast(
        lat=13.7,
        lng=100.5,
        ref_date_str="202605",
        timescale=1.0
    )
    assert prob_result["location"]["lat"] == nearest_lat
    assert prob_result["location"]["lng"] == nearest_lon
    assert "mild" in prob_result["data"]
    assert "mord" in prob_result["data"]
    assert "seve" in prob_result["data"]
    assert len(prob_result["data"]["mild"]) == 6  # 6 leads

    # Test event forecast
    event_result = service.get_event_forecast(
        lat=13.7,
        lng=100.5,
        ref_date_str="202605",
        timescale=1.0
    )
    assert event_result["location"]["lat"] == nearest_lat
    assert event_result["location"]["lng"] == nearest_lon
    assert "dr_ens" in event_result["data"]
    assert len(event_result["data"]["dr_ens"]) == 6  # 6 leads


@pytest.fixture(scope="module")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_api_endpoints(client):
    # Test probability-forecast endpoint
    response = client.get(
        "/draught/probability-forecast",
        params={"lat": 13.7, "lng": 100.5, "ref_date": "202605", "timescale": 1.0}
    )
    assert response.status_code == 200
    data = response.json()
    assert "location" in data
    assert "mild" in data["data"]
    assert "mord" in data["data"]
    assert "seve" in data["data"]
    assert len(data["data"]["mild"]) == 6

    # Test event-forecast endpoint
    response = client.get(
        "/draught/event-forecast",
        params={"lat": 13.7, "lng": 100.5, "ref_date": "202605", "timescale": 1.0}
    )
    assert response.status_code == 200
    data = response.json()
    assert "location" in data
    assert "dr_ens" in data["data"]
    assert len(data["data"]["dr_ens"]) == 6
