from target import Product, with_price, product_schema


def test_copy_does_not_mutate():
    p = Product(name="pen", price=1.0)
    q = with_price(p, 2.0)
    assert q.price == 2.0 and p.price == 1.0


def test_schema_fields():
    s = product_schema()
    assert set(s["properties"]) == {"name", "price"}
    assert set(s["required"]) == {"name", "price"}
