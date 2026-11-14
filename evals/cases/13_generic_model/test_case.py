import pytest
from pydantic import ValidationError
from target import Page, first_page


def test_typed_page():
    p = first_page(["1", "2"])
    assert p.items == [1, 2] and p.total == 2


def test_type_enforced():
    with pytest.raises(ValidationError):
        Page[int](items=["x"], total=1)
