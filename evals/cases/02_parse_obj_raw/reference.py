from pydantic import BaseModel


class Order(BaseModel):
    order_id: str
    quantity: int


def load_order(data: dict) -> Order:
    return Order.model_validate(data)


def load_order_json(raw: str) -> Order:
    return Order.model_validate_json(raw)
