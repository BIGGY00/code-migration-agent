import pytest
from pydantic import ValidationError
from target import Settings


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        Settings(region="ap-southeast-1", debug=True)


def test_is_immutable():
    s = Settings(region="ap-southeast-1")
    with pytest.raises(ValidationError):
        s.retries = 5
