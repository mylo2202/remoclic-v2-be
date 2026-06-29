import os
import sys
from datetime import date
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.dataset_service import DatasetService


class FakeRepository:
    def __init__(self):
        self.last_timescale = None

    def get_latest_ref_date(self):
        return date(2026, 1, 1)

    def get_available_ref_dates(self):
        return []

    def get_total_records(self):
        return 0

    def find_nearest_grid_point(self, lat, lon):
        return (1.0, 2.0)

    def get_forecast_points(self, lat, lon, ref_date, timescale=1.0):
        self.last_timescale = timescale
        return [SimpleNamespace(lead=1, mild=1.0, mord=2.0, seve=3.0)]


def test_get_forecast_passes_timescale_to_repository():
    repo = FakeRepository()
    service = DatasetService(repository=repo)

    result = service.get_forecast(1.0, 2.0, ref_date_str="202601", timescale=3.0)

    assert repo.last_timescale == 3.0
    assert result["data"]["mild"] == [1.0]
