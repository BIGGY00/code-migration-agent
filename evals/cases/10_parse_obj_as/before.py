from typing import List
from pydantic import BaseModel, parse_obj_as


class Item(BaseModel):
    sku: str
    price: float


def load_items(data) -> List[Item]:
    return parse_obj_as(List[Item], data)
