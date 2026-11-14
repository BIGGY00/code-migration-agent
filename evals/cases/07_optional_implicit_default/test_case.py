from target import Profile, display_name


def test_optional_fields_default_to_none():
    p = Profile(name="Jarupong")
    assert p.nickname is None and p.age is None


def test_display_name():
    assert display_name(Profile(name="Jarupong", nickname="Big")) == "Big"
    assert display_name(Profile(name="Jarupong")) == "Jarupong"
