from app.repositories.netcdf_repository import NetCDFRepository
from datetime import datetime

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

    def get_forecast(self, lat: float, lng: float) -> dict:
        """Extract multi-month forecast for mild, mord, and seve drought levels."""
        ds = self.repository.get_dataset()
        
        try:
            # We assume timescale=1.0 for the standard forecast (z=1).
            # We select all lead times.
            point_data = ds.sel(lat=lat, lon=lng, timescale=1.0, method='nearest')
            
            mild_vals = point_data['mild'].values.tolist()
            mord_vals = point_data['mord'].values.tolist()
            seve_vals = point_data['seve'].values.tolist()
            
            # Generate dynamic labels derived from 'lead' time dimension
            units = ds['lead'].attrs.get('units')
            if not units:
                raise ValueError("The 'lead' dimension is missing the 'units' attribute.")
                
            parts = units.split(' since ')
            if len(parts) != 2:
                raise ValueError(f"Invalid 'units' format in 'lead' dimension: {units}. Expected format like 'months since YYYY-MM-DD'.")
                
            ref_date_str = parts[1].strip().split()[0] # Grabs just the YYYY-MM-DD part
            
            try:
                ref_date = datetime.strptime(ref_date_str, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Could not parse date '{ref_date_str}' from 'units' attribute: {units}.")

            labels = []
            for val in ds['lead'].values:
                months_to_add = int(val)
                new_month = ref_date.month + months_to_add
                new_year = ref_date.year + (new_month - 1) // 12
                new_month = (new_month - 1) % 12 + 1
                labels.append(f"{new_month:02d}-{new_year}")
            
            def clean_vals(vals):
                return [round(float(v), 2) if v != -99.0 else None for v in vals]
                
            return {
                "location": {
                    "lat": float(lat),
                    "lng": float(lng)
                },
                "labels": labels,
                "data": {
                    "mild": clean_vals(mild_vals),
                    "mord": clean_vals(mord_vals),
                    "seve": clean_vals(seve_vals)
                }
            }
        except Exception as e:
            raise ValueError(f"Error extracting forecast: {str(e)}")


