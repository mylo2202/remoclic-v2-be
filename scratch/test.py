import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.repositories.netcdf_repository import NetCDFRepository
from app.core.config import settings

print(f"Project Name: {settings.PROJECT_NAME}")
repo = NetCDFRepository()
print("Initialized Repository (no arguments passed)")

# First access triggers discovery
ds = repo.get_dataset()
print("Dataset loaded successfully")
print(f"Dimensions: {dict(ds.dims)}")

# Check if cached path was set
print(f"Cached URL: {NetCDFRepository._cached_file_url}")
