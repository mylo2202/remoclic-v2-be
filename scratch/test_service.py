import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
settings.DATABASE_URL = "sqlite:///scratch/test.db"

from app.core.database import SessionLocal, engine
print("Engine URL:", engine.url)
from app.repositories.netcdf_repository import NetCDFRepository
from app.services.dataset_service import DatasetService

def main():
    db = SessionLocal()
    try:
        repo = NetCDFRepository(db=db)
        service = DatasetService(repository=repo)

        print("Testing get_dataset_metadata()...")
        meta = service.get_dataset_metadata()
        print("Metadata response:")
        print(meta)

        print("\nTesting get_forecast(8.1, 102.1) without ref_date (should pick latest: 2026-04-01)...")
        forecast = service.get_forecast(8.1, 102.1)
        print("Forecast response (Latest):")
        print(forecast)

        print("\nTesting get_forecast(8.1, 102.1, '2026-01-01') with specific ref_date...")
        forecast_historical = service.get_forecast(8.1, 102.1, ref_date_str="2026-01-01")
        print("Forecast response (Historical 2026-01-01):")
        print(forecast_historical)

    finally:
        db.close()

if __name__ == "__main__":
    main()
