import pytest
from pydantic import ValidationError
from target import DateRange


def test_valid_range():
    assert DateRange(start="2026-01-01", end="2026-01-11").days() == 10


def test_reversed_range_raises():
    with pytest.raises(ValidationError):
        DateRange(start="2026-02-01", end="2026-01-01")
