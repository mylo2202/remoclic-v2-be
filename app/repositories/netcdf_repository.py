import os
import xarray as xr
import urllib.request
import tempfile

class NetCDFRepository:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def get_dataset(self) -> xr.Dataset:
        """Reads and returns the NetCDF dataset."""
        if self.file_path.startswith("http://") or self.file_path.startswith("https://"):
            try:
                # Try opening as OPeNDAP
                return xr.open_dataset(self.file_path, decode_times=False)
            except Exception:
                # Fallback: Download the raw file locally first
                fd, temp_path = tempfile.mkstemp(suffix=".nc")
                os.close(fd) # Close the file descriptor immediately
                
                try:
                    urllib.request.urlretrieve(self.file_path, temp_path)
                    
                    # Open the file, load data into memory, and close file handlers
                    ds = xr.open_dataset(temp_path, decode_times=False)
                    ds.load()  
                    ds.close() 
                    
                    return ds
                finally:
                    # Automatically clean up the temporary file from the system
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
        else:
            return xr.open_dataset(self.file_path, decode_times=False)
