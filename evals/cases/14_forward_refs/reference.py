from typing import List
from pydantic import BaseModel


class Node(BaseModel):
    value: int
    children: List["Node"] = []


Node.model_rebuild()


def total(node: Node) -> int:
    return node.value + sum(total(c) for c in node.children)
