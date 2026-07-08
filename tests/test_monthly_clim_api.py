import os
import shutil
import sys
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import Base
from app.services.monthly_clim_ingestion_service import ingest_monthly_clim_file

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db

# Path to the test SQLite database
DB_PATH = "test_monthly_clim_api.db"
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

    # Ingest test data so the API has something to query
    sample_nc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../samples/Monthly_Clim.nc"))

    def mock_urlretrieve(_url, temp_path):
        shutil.copy(sample_nc_path, temp_path)

    with patch("urllib.request.urlretrieve", side_effect=mock_urlretrieve):
        ingest_monthly_clim_file(db, "http://example.com/Monthly_Clim.nc")

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


def test_monthly_clim_endpoints(client):
    # Observed endpoint
    response = client.get(
        "/monthly-clim/observed",
        params={"lat": 8.625, "lng": 104.875}
    )
    assert response.status_code == 200
    data = response.json()
    assert "location" in data
    assert "labels" in data
    assert data["labels"] == ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    assert "data" in data
    assert "pr_o" in data["data"] and "t2_o" in data["data"]
    assert len(data["data"]["pr_o"]) == 12
    assert len(data["data"]["t2_o"]) == 12

    # Model endpoint (lead 1)
    response = client.get(
        "/monthly-clim/model",
        params={"lat": 8.625, "lng": 104.875, "lead": 1}
    )
    assert response.status_code == 200
    data = response.json()
    assert "location" in data
    assert "labels" in data
    assert data["labels"] == ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    assert "data" in data
    assert "pr_m" in data["data"] and "t2_m" in data["data"]
    assert len(data["data"]["pr_m"]) == 12
    assert len(data["data"]["t2_m"]) == 12
