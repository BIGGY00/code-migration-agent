import pytest
from pydantic import ValidationError
from target import load_order, load_order_json


def test_load_dict():
    o = load_order({"order_id": "A1", "quantity": "3"})
    assert o.quantity == 3


def test_load_json():
    o = load_order_json('{"order_id": "B2", "quantity": 5}')
    assert o.order_id == "B2"


def test_invalid_raises():
    with pytest.raises(ValidationError):
        load_order({"order_id": "C3"})
