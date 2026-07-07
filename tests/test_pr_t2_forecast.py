import os
import shutil
import sys
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import Base
from app.services.ingestion import ingest_pr_t2_file

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db

# Path to the test SQLite database - we do not clean this up so the user can inspect it.
DB_PATH = "test_pr_t2_forecast.db"
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

    # Ingest test data so the API has something to query
    sample_nc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../samples/Forecast_Ope_Pr_T2_and_Anomaly.nc"))

    # Mock urllib.request.urlretrieve to copy the local sample file instead of downloading
    def mock_urlretrieve(_url, temp_path):
        shutil.copy(sample_nc_path, temp_path)

    with patch("urllib.request.urlretrieve", side_effect=mock_urlretrieve):
        ingest_pr_t2_file(db, "http://example.com/202605/Forecast_Ope_Pr_T2_and_Anomaly.nc", "202605")

    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_pr_t2_api_endpoints(client, db_session):
    """Test the PR/T2 API endpoints end to end."""

    precipitation_response = client.get(
        "/pr-t2/precipitation-forecast",
        params={"lat": 13.7, "lng": 100.5, "ref_date": "202605"},
    )
    assert precipitation_response.status_code == 200
    precipitation_data = precipitation_response.json()
    assert precipitation_data["location"]["lat"] is not None
    assert "pr" in precipitation_data["data"]

    temperature_response = client.get(
        "/pr-t2/temperature-forecast",
        params={"lat": 13.7, "lng": 100.5, "ref_date": "202605"},
    )
    assert temperature_response.status_code == 200
    temperature_data = temperature_response.json()
    assert temperature_data["location"]["lat"] is not None
    assert "t2" in temperature_data["data"]

    combined_response = client.get(
        "/pr-t2/combined-forecast",
        params={"lat": 13.7, "lng": 100.5, "ref_date": "202605"},
    )
    assert combined_response.status_code == 200
    combined_data = combined_response.json()
    assert "precipitation" in combined_data
    assert "temperature" in combined_data

    ref_dates_response = client.get("/pr-t2/ref-dates")
    assert ref_dates_response.status_code == 200
    ref_dates = ref_dates_response.json()
    assert isinstance(ref_dates, list)
    assert len(ref_dates) > 0