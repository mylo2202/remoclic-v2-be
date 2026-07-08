from pydantic import BaseModel

class PrT2RefDateToggleRequest(BaseModel):
    ref_date: str
    is_active: bool
