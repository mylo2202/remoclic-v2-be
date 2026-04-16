from app.repositories.netcdf_repository import NetCDFRepository

class DatasetService:
    def __init__(self, repository: NetCDFRepository):
        self.repository = repository

    def get_dataset_metadata(self) -> dict:
        """Fetches the dataset from the repository and extracts metadata."""
        ds = self.repository.get_dataset()
        return {
            "dataset_info": "Successfully loaded dataset",
            "dimensions": dict(ds.dims),
            "variables": list(ds.data_vars.keys())
        }

    def get_data_at_point(self, variable: str, lead: float, timescale: float, lat: float, lon: float) -> list:
        """Extract netCDF values given a specific data point."""
        ds = self.repository.get_dataset()
        if variable not in ds.data_vars:
            raise ValueError(f"Variable {variable} not found in dataset")
        
        values = ds[variable].sel(
            lead=lead,
            timescale=timescale,
            lat=lat,
            lon=lon,
            method='nearest'
        )
        
        # .tolist() converts numpy types (like numpy.float32) into native python types 
        # so they can be JSON serialized. 
        return values.values.tolist()
