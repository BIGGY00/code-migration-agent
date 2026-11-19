import pytest
from pydantic import ValidationError
from target import Reading, total


def test_float_counts_are_truncated():
    assert total([{"sensor": "a", "count": 2.7}, {"sensor": "b", "count": 3}]) == 5


def test_numeric_string_count():
    assert Reading(sensor="t1", count="4").count == 4


def test_sensor_upper():
    assert Reading(sensor="ab", count=1).sensor == "AB"


def test_non_numeric_count_rejected():
    with pytest.raises(ValidationError):
        Reading(sensor="x", count="abc")
