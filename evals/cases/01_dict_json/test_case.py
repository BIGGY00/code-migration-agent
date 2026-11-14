import json
from target import User, to_payload, to_json


def test_payload_excludes_tags():
    u = User(id=1, name="ann", tags=["x"])
    assert to_payload(u) == {"id": 1, "name": "ann"}


def test_json_roundtrip():
    u = User(id=2, name="bo")
    assert json.loads(to_json(u)) == {"id": 2, "name": "bo", "tags": []}
