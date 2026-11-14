from target import Event


def test_default_is_validated():
    assert Event(title="t").tags == ["general"]


def test_comma_string_is_split():
    assert Event(title="t", tags="a, b,,c").tags == ["a", "b", "c"]


def test_list_passes_through():
    assert Event(title="t", tags=["x"]).tags == ["x"]
