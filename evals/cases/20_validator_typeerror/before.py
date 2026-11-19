from typing import List
from pydantic import BaseModel, validator


class Batch(BaseModel):
    name: str
    max_items: int = 3
    items: List[str]

    @validator("items", pre=True)
    def check_size(cls, v, values):
        if len(v) > values.get("max_items", 3):
            raise ValueError("too many items")
        return v
