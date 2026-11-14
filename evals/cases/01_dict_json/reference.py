from typing import List
from pydantic import BaseModel


class User(BaseModel):
    id: int
    name: str
    tags: List[str] = []


def to_payload(user: User) -> dict:
    return user.model_dump(exclude={"tags"})


def to_json(user: User) -> str:
    return user.model_dump_json()
