"""Prompts for the migration agent.

The model gets three things: the v1 patterns the static scan found (what and
where, not how to fix them), excerpts from the official migration guide (how to
fix them), and the file. It must answer with the complete migrated file.
"""

from __future__ import annotations

from migrate_agent.retrieval import Hit
from migrate_agent.scan import Finding

SYSTEM = """\
You migrate Python code from Pydantic v1 to Pydantic v2.

Rules:
- Return the COMPLETE migrated file in a single ```python code block and nothing else.
- Keep behaviour and every public name (classes, functions, signatures, field names) the same.
- Use only Pydantic v2 APIs. Do not import `pydantic.v1` and do not keep deprecated v1 methods,
  decorators or class-based `Config`: the code is tested with Pydantic deprecation warnings
  turned into errors.
- Change only what the migration needs. Do not add tests, prints or explanations.
- Base your changes on the migration-guide excerpts provided. Each excerpt starts with its id in
  square brackets.
"""


def format_findings(findings: list[Finding]) -> str:
    if not findings:
        return "(the static scan found no known v1 patterns; check the whole file)"
    return "\n".join(f"- line {f.line}: {f.pattern} — `{f.snippet}`" for f in findings)


def format_excerpts(hits: list[Hit]) -> str:
    return "\n\n".join(f"[{h.chunk.id}] {h.chunk.title}\n{h.chunk.text}" for h in hits)


def first_turn(source: str, findings: list[Finding], hits: list[Hit]) -> str:
    return f"""\
## Pydantic v1 patterns found by a static scan
{format_findings(findings)}

## Migration guide excerpts
{format_excerpts(hits)}

## File to migrate
```python
{source}
```

Return the complete migrated file."""


def fix_turn(test_output: str, new_hits: list[Hit]) -> str:
    extra = f"\n\n## More migration guide excerpts\n{format_excerpts(new_hits)}" if new_hits else ""
    return f"""\
Your migrated file failed its tests. Here is the end of the pytest output:

```
{test_output}
```{extra}

Fix the problem and return the complete corrected file."""
