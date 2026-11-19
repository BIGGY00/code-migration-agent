import pytest
from pydantic import ValidationError
from target import load, endpoint, is_secure


def test_endpoint_on_bare_host():
    cfg = load('{"base_url": "https://api.example.com"}')
    url = endpoint(cfg, "/v1/items")
    assert isinstance(url, str)
    assert url == "https://api.example.com/v1/items"


def test_endpoint_on_base_path():
    cfg = load('{"base_url": "https://api.example.com/base"}')
    assert endpoint(cfg, "/x") == "https://api.example.com/base/x"


def test_is_secure():
    assert is_secure(load('{"base_url": "https://a.example.com"}')) is True
    assert is_secure(load('{"base_url": "http://a.example.com"}')) is False


def test_invalid_url_rejected():
    with pytest.raises(ValidationError):
        load('{"base_url": "not a url"}')
