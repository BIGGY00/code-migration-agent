from typing import Generic, List, TypeVar
from pydantic.generics import GenericModel

T = TypeVar("T")


class Page(GenericModel, Generic[T]):
    items: List[T]
    total: int


def first_page(items):
    return Page[int](items=items, total=len(items))
