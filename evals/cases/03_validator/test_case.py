import pytest
from pydantic import ValidationError
from target import Signup


def test_lowercases():
    assert Signup(username="Ann42", password="x").username == "ann42"


def test_rejects_symbols():
    with pytest.raises(ValidationError):
        Signup(username="ann!", password="x")
