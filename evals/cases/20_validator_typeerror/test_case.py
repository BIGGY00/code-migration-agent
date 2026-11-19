import pytest
from pydantic import ValidationError
from target import Batch


def test_valid_batch():
    assert Batch(name="b", items=["a", "b"]).items == ["a", "b"]


def test_too_many_items():
    with pytest.raises(ValidationError):
        Batch(name="b", max_items=1, items=["a", "b"])


def test_none_items_is_a_validation_error():
    with pytest.raises(ValidationError):
        Batch(name="b", items=None)


def test_number_items_is_a_validation_error():
    with pytest.raises(ValidationError):
        Batch(name="b", items=7)
