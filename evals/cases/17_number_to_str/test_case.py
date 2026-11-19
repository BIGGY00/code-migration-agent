import pytest
from pydantic import ValidationError
from target import from_row, label


def test_numeric_sku_becomes_text():
    p = from_row({"sku": 10042, "name": "  Mug ", "price": 9.5})
    assert p.sku == "10042"
    assert label(p) == "10042: Mug"


def test_text_sku_and_strip():
    assert from_row({"sku": " A-1 ", "name": "Cup", "price": 3}).sku == "A-1"


def test_missing_price_rejected():
    with pytest.raises(ValidationError):
        from_row({"sku": "A-2", "name": "Bowl"})
