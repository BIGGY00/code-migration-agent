from typing import List
from pydantic import BaseModel, validator


class Event(BaseModel):
    title: str
    tags: List[str] = None

    @validator("tags", pre=True, always=True)
    def split_tags(cls, v):
        if v is None:
            return ["general"]
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v
