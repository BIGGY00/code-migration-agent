from typing import Dict, List, Tuple
from pydantic import BaseModel, field_validator


class Request(BaseModel):
    method: str
    headers: Dict[str, str] = {}

    @field_validator("headers", mode="before")
    @classmethod
    def pairs_to_dict(cls, v):
        if isinstance(v, (list, tuple)):
            return dict(v)
        return v


def build(method: str, header_pairs: List[Tuple[str, str]]) -> Request:
    return Request(method=method, headers=header_pairs)


def as_json(req: Request) -> str:
    return req.model_dump_json()
