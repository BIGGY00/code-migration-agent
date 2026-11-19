import pytest
from pydantic import ValidationError
from target import Team


def test_emails_lowercased():
    t = Team(domain="acme.io", emails=["Ann@ACME.io", "bo@acme.io"])
    assert t.emails == ["ann@acme.io", "bo@acme.io"]


def test_foreign_domain_rejected():
    with pytest.raises(ValidationError):
        Team(domain="acme.io", emails=["ann@acme.io", "eve@evil.com"])


def test_empty_list_ok():
    assert Team(domain="acme.io", emails=[]).emails == []
