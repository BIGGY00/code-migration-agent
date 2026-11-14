from typing import List
from pydantic import BaseModel, TypeAdapter


class Item(BaseModel):
    sku: str
    price: float


_items_adapter = TypeAdapter(List[Item])


def load_items(data) -> List[Item]:
    return _items_adapter.validate_python(data)
