from typing import Generic, List, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int


def first_page(items):
    return Page[int](items=items, total=len(items))
