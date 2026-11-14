from typing import List
from pydantic import BaseModel


class Node(BaseModel):
    value: int
    children: List["Node"] = []


Node.update_forward_refs()


def total(node: Node) -> int:
    return node.value + sum(total(c) for c in node.children)
