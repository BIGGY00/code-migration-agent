from datetime import date
from pydantic import BaseModel, model_validator


class DateRange(BaseModel):
    start: date
    end: date

    @model_validator(mode="after")
    def check_order(self) -> "DateRange":
        if self.end < self.start:
            raise ValueError("end must not be before start")
        return self

    def days(self) -> int:
        return (self.end - self.start).days
