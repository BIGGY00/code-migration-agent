from typing import Dict, List, Tuple
from pydantic import BaseModel


class Request(BaseModel):
    method: str
    headers: Dict[str, str] = {}


def build(method: str, header_pairs: List[Tuple[str, str]]) -> Request:
    return Request(method=method, headers=header_pairs)


def as_json(req: Request) -> str:
    return req.json()
