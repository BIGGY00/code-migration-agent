from typing import List
from pydantic import BaseModel, ValidationInfo, field_validator


class Batch(BaseModel):
    name: str
    max_items: int = 3
    items: List[str]

    @field_validator("items", mode="before")
    @classmethod
    def check_size(cls, v, info: ValidationInfo):
        try:
            size = len(v)
        except TypeError:
            raise ValueError("items must be a list")
        if size > info.data.get("max_items", 3):
            raise ValueError("too many items")
        return v
