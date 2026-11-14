from typing import Optional
from pydantic import BaseModel


class Profile(BaseModel):
    name: str
    nickname: Optional[str] = None
    age: Optional[int] = None


def display_name(p: Profile) -> str:
    return p.nickname or p.name
