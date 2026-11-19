from typing import List
from pydantic import BaseModel


class Event(BaseModel):
    kind: str


class Click(Event):
    x: int
    y: int


class Session(BaseModel):
    user: str
    events: List[Event]


def export(session: Session) -> dict:
    return session.dict()
