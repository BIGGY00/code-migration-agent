from typing import List, Union
from pydantic import BaseModel, Field


class LineItem(BaseModel):
    ref: Union[int, str] = Field(union_mode="left_to_right")
    qty: int


class Invoice(BaseModel):
    items: List[LineItem]


def load_invoice(data: dict) -> Invoice:
    return Invoice.model_validate(data)


def numeric_refs(invoice: Invoice) -> List[int]:
    """Return the refs that are numeric ids."""
    return [item.ref for item in invoice.items if isinstance(item.ref, int)]
