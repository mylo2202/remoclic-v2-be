import sys
import os

# Add project root to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
# Override the database URL to use SQLite for this test run
settings.DATABASE_URL = "sqlite:///scratch/test.db"

import logging
logging.basicConfig(level=logging.INFO)

from app.services.ingestion import run_ingestion
from app.core.database import SessionLocal
from app.models.forecast import DroughtForecast
from sqlalchemy import select, func

def main():
    print("Starting test ingestion using SQLite...")
    
    # Ensure scratch dir exists
    os.makedirs("scratch", exist_ok=True)
    if os.path.exists("scratch/test.db"):
        os.remove("scratch/test.db")
        print("Removed existing test database.")

    # Run the ingestion function
    run_ingestion()

    # Query the test database to verify records
    db = SessionLocal()
    try:
        total_records = db.execute(select(func.count(DroughtForecast.id))).scalar()
        print(f"\nVerification Success!")
        print(f"Total forecast records inserted: {total_records}")

        # Show distinct ref_dates
        ref_dates = db.execute(select(DroughtForecast.ref_date.distinct())).scalars().all()
        print(f"Available reference dates: {[d.strftime('%Y-%m-%d') for d in ref_dates]}")

        # Show a sample record
        sample = db.execute(select(DroughtForecast).limit(1)).scalar()
        if sample:
            print(f"Sample Record:")
            print(f"  Ref Date: {sample.ref_date}")
            print(f"  Location: ({sample.lat}, {sample.lon})")
            print(f"  Timescale: {sample.timescale}")
            print(f"  Lead: {sample.lead}")
            print(f"  Mild: {sample.mild}")
            print(f"  Mord: {sample.mord}")
            print(f"  Seve: {sample.seve}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
