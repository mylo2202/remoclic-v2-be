import logging
import os
import re
import tempfile
import urllib.request
from typing import Optional

import requests
import xarray as xr

from app.core.config import settings

logger = logging.getLogger(__name__)


class NetCDFRepository:
    """Module for abstracting data access to NetCDF files with dynamic discovery."""

    # Class-level cache for the discovered file path to avoid redundant network calls
    _cached_file_url: Optional[str] = None

    def __init__(self):
        """Initializes the repository. No explicit file path required as it is discovered."""
        pass

    def get_dataset(self) -> xr.Dataset:
        """
        Reads and returns the NetCDF dataset. 
        Automatically discovers the latest file URL if not already cached.
        """
        file_url = self._get_latest_file_url()

        if file_url.startswith("http://") or file_url.startswith("https://"):
            try:
                # Try opening directly (e.g., via OPeNDAP if supported by the server)
                return xr.open_dataset(file_url, decode_times=False)
            except Exception as e:
                logger.debug("Direct open failed, falling back to download: %s", e)
                return self._download_and_open(file_url)
        else:
            return xr.open_dataset(file_url, decode_times=False)

    def _get_latest_file_url(self) -> str:
        """
        Discovers the latest YYYYMM subdirectory from the base URL defined in settings.
        Returns the full URL to the NetCDF file.
        """
        if NetCDFRepository._cached_file_url:
            return NetCDFRepository._cached_file_url

        base_url = settings.DATA_BASE_URL.rstrip('/')
        file_name = settings.DATA_FILE_NAME

        try:
            logger.info("Discovering latest data directory at %s", base_url)
            response = requests.get(base_url, timeout=10)
            response.raise_for_status()

            # Find all YYYYMM/ patterns in the directory listing
            subdirs = re.findall(r'(\d{6})/', response.text)

            if subdirs:
                latest_subdir = sorted(subdirs)[-1]
                NetCDFRepository._cached_file_url = f"{base_url}/{latest_subdir}/{file_name}"
                logger.info("Discovered latest file: %s", NetCDFRepository._cached_file_url)
                return NetCDFRepository._cached_file_url

            logger.warning("No YYYYMM subdirectories found. Using default fallback.")
        except Exception as e:
            logger.error("Failed to discover latest data: %s. Falling back to default.", e)

        # Fallback to a hardcoded default if discovery fails (e.g. 2026/03)
        return f"{base_url}/202603/{file_name}"

    def _download_and_open(self, url: str) -> xr.Dataset:
        """Downloads the file to a temporary location and opens it with xarray."""
        fd, temp_path = tempfile.mkstemp(suffix=".nc")
        os.close(fd)

        try:
            logger.info("Downloading NetCDF file from %s", url)
            urllib.request.urlretrieve(url, temp_path)

            # Load data into memory so we can delete the temp file
            ds = xr.open_dataset(temp_path, decode_times=False)
            ds.load()
            ds.close()
            return ds
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @classmethod
    def clear_cache(cls):
        """Clears the discovered URL cache."""
        cls._cached_file_url = None
