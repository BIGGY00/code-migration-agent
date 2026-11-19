from typing import List, Union
from pydantic import BaseModel


class LineItem(BaseModel):
    ref: Union[int, str]
    qty: int


class Invoice(BaseModel):
    items: List[LineItem]


def load_invoice(data: dict) -> Invoice:
    return Invoice.parse_obj(data)


def numeric_refs(invoice: Invoice) -> List[int]:
    """Return the refs that are numeric ids."""
    return [item.ref for item in invoice.items if isinstance(item.ref, int)]
