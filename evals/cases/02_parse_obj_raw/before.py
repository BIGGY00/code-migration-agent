from pydantic import BaseModel


class Order(BaseModel):
    order_id: str
    quantity: int


def load_order(data: dict) -> Order:
    return Order.parse_obj(data)


def load_order_json(raw: str) -> Order:
    return Order.parse_raw(raw)
