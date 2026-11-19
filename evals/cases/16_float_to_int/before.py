from typing import List
from pydantic import BaseModel, validator


class Reading(BaseModel):
    sensor: str
    count: int

    @validator("sensor")
    def upper_sensor(cls, v):
        return v.upper()


def total(readings: List[dict]) -> int:
    return sum(Reading.parse_obj(r).count for r in readings)
