from pydantic import BaseModel


class Product(BaseModel):
    name: str
    price: float


def with_price(p: Product, price: float) -> Product:
    return p.copy(update={"price": price})


def product_schema() -> dict:
    return Product.schema()
