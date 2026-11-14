from pydantic import BaseModel


class Product(BaseModel):
    name: str
    price: float


def with_price(p: Product, price: float) -> Product:
    return p.model_copy(update={"price": price})


def product_schema() -> dict:
    return Product.model_json_schema()
