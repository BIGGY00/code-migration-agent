from typing import List
from pydantic import BaseModel, field_validator


class Reading(BaseModel):
    sensor: str
    count: int

    @field_validator("sensor")
    @classmethod
    def upper_sensor(cls, v):
        return v.upper()

    @field_validator("count", mode="before")
    @classmethod
    def truncate_float(cls, v):
        if isinstance(v, float):
            return int(v)
        return v


def total(readings: List[dict]) -> int:
    return sum(Reading.model_validate(r).count for r in readings)
