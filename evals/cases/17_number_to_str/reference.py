from pydantic import BaseModel, ConfigDict


class Product(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, coerce_numbers_to_str=True)

    sku: str
    name: str
    price: float


def from_row(row: dict) -> Product:
    return Product(**row)


def label(p: Product) -> str:
    return f"{p.sku}: {p.name}"
