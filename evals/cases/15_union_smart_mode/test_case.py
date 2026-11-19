import pytest
from pydantic import ValidationError
from target import load_invoice, numeric_refs

DATA = {"items": [{"ref": "42", "qty": 1}, {"ref": "SKU-9", "qty": 2}, {"ref": 7, "qty": 3}]}


def test_numeric_strings_become_ids():
    inv = load_invoice(DATA)
    assert inv.items[0].ref == 42
    assert numeric_refs(inv) == [42, 7]


def test_text_refs_stay_text():
    assert load_invoice(DATA).items[1].ref == "SKU-9"


def test_bad_qty_rejected():
    with pytest.raises(ValidationError):
        load_invoice({"items": [{"ref": "1", "qty": "many"}]})
