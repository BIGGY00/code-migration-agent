"""The static scan must flag every before.py and stay quiet on every reference.py."""

from migrate_agent.harness import load_cases
from migrate_agent.scan import queries, scan


def test_scan_flags_every_before_and_no_reference():
    for case in load_cases():
        assert scan(case.before.read_text()), f"{case.id}: no v1 pattern found in before.py"
        assert not scan(case.reference.read_text()), f"{case.id}: false positive in reference.py"


def test_validator_with_pre_is_reported_once_as_specific_pattern():
    found = scan("class A(BaseModel):\n    @validator('x', pre=True)\n    def f(cls, v):\n        return v\n")
    assert [f.pattern for f in found] == ["@validator(pre=/always=)"]


def test_optional_without_default_needs_missing_value():
    src = "class A(BaseModel):\n    a: Optional[int]\n    b: Optional[int] = None\n    c: int | None\n"
    assert [(f.pattern, f.line) for f in scan(src)] == [
        ("Optional field without default", 2),
        ("Optional field without default", 4),
    ]


def test_queries_are_deduplicated():
    src = "a.dict()\nb.dict()\n"
    assert len(scan(src)) == 2 and len(queries(scan(src))) == 1
