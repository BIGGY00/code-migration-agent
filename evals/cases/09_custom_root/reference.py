from typing import List
from pydantic import RootModel


class Tags(RootModel[List[str]]):
    pass


def parse_tags(data) -> Tags:
    return Tags.model_validate(data)


def tag_count(tags: Tags) -> int:
    return len(tags.root)
