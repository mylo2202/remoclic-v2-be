from pydantic import BaseModel


class DroughtRefDateToggleRequest(BaseModel):
    ref_date: str
    is_active: bool
