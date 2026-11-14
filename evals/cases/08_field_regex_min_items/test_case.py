import pytest
from pydantic import ValidationError
from target import Shipment


def test_valid():
    assert Shipment(country_code="SG", parcels=["p1"]).country_code == "SG"


def test_bad_country_code():
    with pytest.raises(ValidationError):
        Shipment(country_code="sgp", parcels=["p1"])


def test_empty_parcels():
    with pytest.raises(ValidationError):
        Shipment(country_code="TH", parcels=[])
