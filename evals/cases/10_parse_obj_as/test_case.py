import pytest
from pydantic import ValidationError
from target import Item, load_items


def test_loads_list():
    items = load_items([{"sku": "a", "price": "1.5"}, {"sku": "b", "price": 2}])
    assert [i.sku for i in items] == ["a", "b"]
    assert isinstance(items[0], Item) and items[0].price == 1.5


def test_invalid_item():
    with pytest.raises(ValidationError):
        load_items([{"sku": "a"}])
