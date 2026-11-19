from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Extra, Field, root_validator, validator


class Address(BaseModel):
    city: str
    postcode: str = Field(..., regex=r"^\d{6}$")


class Customer(BaseModel):
    id: int
    name: str = Field(alias="fullName")
    email: Optional[str]
    tier: str = "basic"
    tags: List[str] = Field(default_factory=list, max_items=5)
    address: Optional[Address]
    created_at: datetime

    class Config:
        allow_population_by_field_name = True
        extra = Extra.forbid
        anystr_strip_whitespace = True
        json_encoders = {datetime: lambda d: d.strftime("%Y-%m-%d")}

    @root_validator(pre=True)
    def legacy_keys(cls, values):
        if "customer_id" in values:
            values["id"] = values.pop("customer_id")
        return values

    @validator("tier")
    def known_tier(cls, v):
        if v not in {"basic", "gold"}:
            raise ValueError("unknown tier")
        return v

    @validator("email")
    def lower_email(cls, v):
        return v.lower() if v is not None else v


def parse_customer(raw: str) -> Customer:
    return Customer.parse_raw(raw)


def to_api(c: Customer) -> dict:
    return c.dict(by_alias=True, exclude_none=True)


def to_json(c: Customer) -> str:
    return c.json(by_alias=True)


def upgrade(c: Customer) -> Customer:
    return c.copy(update={"tier": "gold"})


def json_schema() -> dict:
    return Customer.schema(by_alias=True)
