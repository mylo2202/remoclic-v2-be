import os
import shutil
import sys
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import Base
from app.models.monthly_clim_model import MonthlyClimModel
from app.models.monthly_clim_observed import MonthlyClimObserved
from app.models.monthly_clim_ingestion_state import MonthlyClimIngestionState
from app.services.ingestion import ingest_monthly_clim_file

DB_PATH = "test_monthly_clim_ingestion.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"


@pytest.fixture(scope="module")
def db_session():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_monthly_clim_ingestion(db_session):
    sample_nc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../samples/Monthly_Clim.nc"))

    def mock_urlretrieve(_url, temp_path):
        shutil.copy(sample_nc_path, temp_path)

    with patch("urllib.request.urlretrieve", side_effect=mock_urlretrieve):
        ingest_monthly_clim_file(db_session, "http://example.com/Monthly_Clim.nc")

    model_count = db_session.query(MonthlyClimModel).count()
    observed_count = db_session.query(MonthlyClimObserved).count()

    assert model_count > 0
    assert observed_count > 0

    # Verify a sample model record exists for a known coordinate and lead/time combination.
    sample_model = db_session.query(MonthlyClimModel).filter_by(
        month=1,
        lead=1,
        lat=8.625,
        lon=104.875
    ).first()
    assert sample_model is not None
    assert sample_model.pr_m is not None and sample_model.t2_m is not None

    sample_observed = db_session.query(MonthlyClimObserved).filter_by(
        month=1,
        lat=8.625,
        lon=104.875
    ).first()
    assert sample_observed is not None
    assert sample_observed.pr_o is not None and sample_observed.t2_o is not None


def test_monthly_clim_ingestion_clears_previous_data(db_session):
    sample_nc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../samples/Monthly_Clim.nc"))

    def mock_urlretrieve(_url, temp_path):
        shutil.copy(sample_nc_path, temp_path)

    with patch("urllib.request.urlretrieve", side_effect=mock_urlretrieve):
        ingest_monthly_clim_file(db_session, "http://example.com/Monthly_Clim.nc")
        first_model_count = db_session.query(MonthlyClimModel).count()

        ingest_monthly_clim_file(db_session, "http://example.com/Monthly_Clim.nc")
        second_model_count = db_session.query(MonthlyClimModel).count()

    assert first_model_count == second_model_count
    assert first_model_count > 0


def test_monthly_clim_ingestion_skips_unchanged_file(db_session):
    sample_nc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../samples/Monthly_Clim.nc"))
    url = "http://example.com/Monthly_Clim.nc"

    class DummyHeadResponse:
        def __init__(self, headers):
            self.headers = headers
            self.ok = True

        def raise_for_status(self):
            return None

    def mock_head(_url, allow_redirects=True, timeout=None):
        return DummyHeadResponse({
            "ETag": "\"fake-etag\"",
            "Last-Modified": "Tue, 01 Jan 2030 00:00:00 GMT",
        })

    def mock_urlretrieve(_url, temp_path):
        shutil.copy(sample_nc_path, temp_path)

    with patch("app.services.ingestion.requests.head", side_effect=mock_head) as mock_head_fn:
        with patch("urllib.request.urlretrieve", side_effect=mock_urlretrieve) as mock_url_fn:
            first_result = ingest_monthly_clim_file(db_session, url)
            assert first_result is True
            state = db_session.query(MonthlyClimIngestionState).filter_by(file_name="Monthly_Clim.nc").one_or_none()
            assert state is not None
            assert state.etag == "\"fake-etag\""
            assert state.last_modified == "Tue, 01 Jan 2030 00:00:00 GMT"

            mock_url_fn.reset_mock()
            second_result = ingest_monthly_clim_file(db_session, url)
            assert second_result is False
            mock_url_fn.assert_not_called()
