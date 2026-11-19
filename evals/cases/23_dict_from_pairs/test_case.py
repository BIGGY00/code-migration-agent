import json

from target import Request, build, as_json


def test_pairs_become_headers():
    req = build("GET", [("Accept", "application/json"), ("X-Id", "7")])
    assert req.headers == {"Accept": "application/json", "X-Id": "7"}


def test_no_pairs():
    assert build("POST", []).headers == {}


def test_dict_still_accepted():
    assert Request(method="GET", headers={"A": "b"}).headers == {"A": "b"}


def test_json_roundtrip():
    data = json.loads(as_json(build("GET", [("A", "b")])))
    assert data == {"method": "GET", "headers": {"A": "b"}}
