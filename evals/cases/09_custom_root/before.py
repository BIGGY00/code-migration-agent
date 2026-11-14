from typing import List
from pydantic import BaseModel


class Tags(BaseModel):
    __root__: List[str]


def parse_tags(data) -> Tags:
    return Tags.parse_obj(data)


def tag_count(tags: Tags) -> int:
    return len(tags.__root__)
