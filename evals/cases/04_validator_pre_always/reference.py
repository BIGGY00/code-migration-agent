from typing import List
from pydantic import BaseModel, Field, field_validator


class Event(BaseModel):
    title: str
    tags: List[str] = Field(default=None, validate_default=True)

    @field_validator("tags", mode="before")
    @classmethod
    def split_tags(cls, v):
        if v is None:
            return ["general"]
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v
