import json
from datetime import datetime

import pytest
from pydantic import ValidationError
from target import Address, Customer, json_schema, parse_customer, to_api, to_json, upgrade

RAW = '{"customer_id": 1, "fullName": "  Ann Lee ", "created_at": "2024-01-02T03:04:05"}'


def test_parse_legacy_payload_with_optional_fields_missing():
    c = parse_customer(RAW)
    assert (c.id, c.name, c.email, c.address, c.tier, c.tags) == (1, "Ann Lee", None, None, "basic", [])


def test_to_api_uses_aliases_and_drops_none():
    assert to_api(parse_customer(RAW)) == {
        "id": 1,
        "fullName": "Ann Lee",
        "tier": "basic",
        "tags": [],
        "created_at": datetime(2024, 1, 2, 3, 4, 5),
    }


def test_to_json_formats_dates():
    data = json.loads(to_json(parse_customer(RAW)))
    assert data["fullName"] == "Ann Lee"
    assert data["created_at"] == "2024-01-02"


def test_populate_by_field_name_and_lower_email():
    c = Customer(id=2, name="Bo", email="Bo@Example.COM", created_at=datetime(2024, 5, 6))
    assert c.name == "Bo" and c.email == "bo@example.com"


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        Customer(id=3, name="Cy", created_at=datetime(2024, 1, 1), nickname="c")


def test_too_many_tags_rejected():
    with pytest.raises(ValidationError):
        Customer(id=4, name="Di", created_at=datetime(2024, 1, 1), tags=list("abcdef"))


def test_bad_postcode_rejected():
    with pytest.raises(ValidationError):
        Address(city="SG", postcode="12345")


def test_unknown_tier_rejected():
    with pytest.raises(ValidationError):
        Customer(id=5, name="Ed", created_at=datetime(2024, 1, 1), tier="platinum")


def test_upgrade():
    assert upgrade(parse_customer(RAW)).tier == "gold"


def test_schema_uses_alias():
    assert "fullName" in json_schema()["properties"]
