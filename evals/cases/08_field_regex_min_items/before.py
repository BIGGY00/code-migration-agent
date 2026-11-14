from typing import List
from pydantic import BaseModel, Field


class Shipment(BaseModel):
    country_code: str = Field(..., regex=r"^[A-Z]{2}$")
    parcels: List[str] = Field(..., min_items=1)
