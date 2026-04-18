from datetime import datetime

from app.repositories.netcdf_repository import NetCDFRepository


class DatasetService:
    """Module providing core business logic for dataset operations."""

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

    def get_forecast(self, lat: float, lng: float) -> dict:
        """Extract multi-month forecast for mild, mord, and seve drought levels."""
        ds = self.repository.get_dataset()

        try:
            # We select all lead times for standard forecast (timescale=1.0)
            point_data = ds.sel(lat=lat, lon=lng, timescale=1.0, method='nearest')

            return {
                "location": {"lat": float(lat), "lng": float(lng)},
                "labels": self._generate_date_labels(ds),
                "data": {
                    var: self._clean_vals(point_data[var].values)
                    for var in ["mild", "mord", "seve"]
                }
            }
        except Exception as e:
            raise ValueError(f"Error extracting forecast: {str(e)}") from e

    def _generate_date_labels(self, ds) -> list[str]:
        """Generates human-readable labels from the 'lead' dimension units."""
        units = ds['lead'].attrs.get('units', "")
        if " since " not in units:
            raise ValueError(f"Invalid 'lead' units format: {units or 'Missing'}")

        ref_date_str = units.split(' since ')[1].strip().split()[0]
        try:
            ref_date = datetime.strptime(ref_date_str, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(f"Could not parse reference date: {ref_date_str}") from exc

        labels = []
        for val in ds['lead'].values:
            months_to_add = int(val)
            new_month = (ref_date.month + months_to_add - 1) % 12 + 1
            new_year = ref_date.year + (ref_date.month + months_to_add - 1) // 12
            labels.append(f"{new_month:02d}-{new_year}")
        return labels

    @staticmethod
    def _clean_vals(vals) -> list[float | None]:
        """Rounds values and replaces placeholders with None."""
        return [round(float(v), 2) if v != -99.0 else None for v in vals]
