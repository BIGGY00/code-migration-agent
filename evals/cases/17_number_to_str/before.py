from pydantic import BaseModel


class Product(BaseModel):
    sku: str
    name: str
    price: float

    class Config:
        anystr_strip_whitespace = True


def from_row(row: dict) -> Product:
    return Product(**row)


def label(p: Product) -> str:
    return f"{p.sku}: {p.name}"
