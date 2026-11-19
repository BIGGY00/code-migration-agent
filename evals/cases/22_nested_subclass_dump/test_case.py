from target import Click, Event, Session, export


def test_export_keeps_subclass_fields():
    s = Session(user="u1", events=[Click(kind="click", x=1, y=2), Event(kind="open")])
    assert export(s) == {
        "user": "u1",
        "events": [{"kind": "click", "x": 1, "y": 2}, {"kind": "open"}],
    }


def test_export_plain_events():
    assert export(Session(user="u2", events=[])) == {"user": "u2", "events": []}
