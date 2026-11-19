from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator


class Address(BaseModel):
    city: str
    postcode: str = Field(..., pattern=r"^\d{6}$")


class Customer(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid", str_strip_whitespace=True)

    id: int
    name: str = Field(alias="fullName")
    email: Optional[str] = None
    tier: str = "basic"
    tags: List[str] = Field(default_factory=list, max_length=5)
    address: Optional[Address] = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def legacy_keys(cls, values: Any) -> Any:
        if isinstance(values, dict) and "customer_id" in values:
            values = dict(values)
            values["id"] = values.pop("customer_id")
        return values

    @field_validator("tier")
    @classmethod
    def known_tier(cls, v):
        if v not in {"basic", "gold"}:
            raise ValueError("unknown tier")
        return v

    @field_validator("email")
    @classmethod
    def lower_email(cls, v):
        return v.lower() if v is not None else v

    @field_serializer("created_at", when_used="json")
    def date_only(self, d: datetime) -> str:
        return d.strftime("%Y-%m-%d")


def parse_customer(raw: str) -> Customer:
    return Customer.model_validate_json(raw)


def to_api(c: Customer) -> dict:
    return c.model_dump(by_alias=True, exclude_none=True)


def to_json(c: Customer) -> str:
    return c.model_dump_json(by_alias=True)


def upgrade(c: Customer) -> Customer:
    return c.model_copy(update={"tier": "gold"})


def json_schema() -> dict:
    return Customer.model_json_schema(by_alias=True)
