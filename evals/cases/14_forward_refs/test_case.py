from target import Node, total


def test_nested_tree():
    tree = Node.model_validate({"value": 1, "children": [{"value": 2}, {"value": 3, "children": [{"value": 4}]}]})
    assert total(tree) == 10
