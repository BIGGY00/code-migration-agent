from types import SimpleNamespace
from target import UserOut, from_record


def test_from_object_attributes():
    rec = SimpleNamespace(id=7, fullName="Ann Lee")
    assert from_record(rec).full_name == "Ann Lee"


def test_populate_by_field_name():
    assert UserOut(id=1, full_name="Bo").full_name == "Bo"


def test_populate_by_alias():
    assert UserOut(id=1, fullName="Cy").full_name == "Cy"
