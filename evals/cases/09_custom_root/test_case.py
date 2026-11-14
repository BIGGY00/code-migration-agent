import pytest
from pydantic import ValidationError
from target import parse_tags, tag_count


def test_count():
    assert tag_count(parse_tags(["ai", "rag", "agents"])) == 3


def test_not_a_list():
    with pytest.raises(ValidationError):
        parse_tags({"tags": ["x"]})
