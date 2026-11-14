from datetime import date
from pydantic import BaseModel, root_validator


class DateRange(BaseModel):
    start: date
    end: date

    @root_validator
    def check_order(cls, values):
        start, end = values.get("start"), values.get("end")
        if start and end and end < start:
            raise ValueError("end must not be before start")
        return values

    def days(self) -> int:
        return (self.end - self.start).days
