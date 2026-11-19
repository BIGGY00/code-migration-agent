"""Cheap static scan for Pydantic v1 patterns.

The scan does not fix anything. It answers two questions for the agent:

1. *What* v1 patterns are in this file, and on which lines? (shown to the LLM)
2. *What should we search the migration guide for?* Each pattern carries a
   short retrieval query naming the v1 API and its v2 replacement, which finds
   the right guide section far more reliably than searching with the whole file.

Most patterns are regexes. Implicit ``Optional`` defaults need the AST, because
the v1 pattern is the *absence* of a default value.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Pattern:
    name: str
    regex: str | None  # None = detected by an AST rule
    query: str  # retrieval query for the guide


@dataclass(frozen=True)
class Finding:
    pattern: str
    line: int
    snippet: str
    query: str


PATTERNS: list[Pattern] = [
    # BaseModel methods
    Pattern("BaseModel.dict()", r"\.dict\(", "dict() model_dump BaseModel method renamed"),
    Pattern("BaseModel.json()", r"\.json\(", "json() model_dump_json BaseModel method renamed"),
    Pattern("BaseModel.parse_obj()", r"\.parse_obj\(", "parse_obj model_validate BaseModel method renamed"),
    Pattern("BaseModel.parse_raw()/parse_file()", r"\.parse_(raw|file)\(", "parse_raw parse_file model_validate_json deprecated"),
    Pattern("BaseModel.from_orm()", r"\.from_orm\(", "from_orm model_validate from_attributes"),
    Pattern("BaseModel.copy()", r"\.copy\(", "copy model_copy BaseModel method renamed"),
    Pattern("BaseModel.schema()/schema_json()", r"\.schema(_json)?\(", "schema schema_json model_json_schema BaseModel method renamed"),
    Pattern("BaseModel.update_forward_refs()", r"\.update_forward_refs\(", "update_forward_refs model_rebuild"),
    Pattern("__root__ custom root type", r"\b__root__\b", "__root__ custom root RootModel"),
    # Validators
    Pattern("@validator(pre=/always=)", r"@validator\([^)]*\b(pre|always)\s*=", "validator pre always field_validator mode before validate_default"),
    Pattern("@validator", r"@validator\b", "validator deprecated field_validator"),
    Pattern("@root_validator", r"@root_validator\b", "root_validator deprecated model_validator"),
    # Config
    Pattern("class Config", r"^\s+class Config\b", "class Config model_config ConfigDict deprecated"),
    Pattern("Config.orm_mode", r"\borm_mode\b", "orm_mode from_attributes config renamed"),
    Pattern("Config.allow_population_by_field_name", r"\ballow_population_by_field_name\b", "allow_population_by_field_name populate_by_name config renamed"),
    Pattern("Config.allow_mutation", r"\ballow_mutation\b", "allow_mutation frozen config removed"),
    Pattern("Extra enum", r"\bExtra\.\w+", "Extra forbid allow ignore extra config"),
    # Fields and types
    Pattern("Field(regex=)", r"\bregex\s*=", "Field regex pattern removed"),
    Pattern("Field(min_items=/max_items=)", r"\b(min|max)_items\s*=", "Field min_items max_items min_length max_length removed"),
    Pattern("Optional field without default", None, "Optional required nullable field default None"),
    # Moved / removed APIs
    Pattern("parse_obj_as()", r"\bparse_obj_as\b", "parse_obj_as TypeAdapter validate_python"),
    Pattern("GenericModel", r"\bGenericModel\b", "pydantic.generics GenericModel removed Generic BaseModel"),
]

_BY_NAME = {p.name: p for p in PATTERNS}


def _optional_without_default(tree: ast.AST) -> list[tuple[int, str]]:
    """Class-body annotations like ``x: Optional[str]`` with no ``= ...``.

    In v1 these defaulted to ``None``; in v2 they are required.
    """
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or not node.bases:
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and stmt.value is None and isinstance(stmt.target, ast.Name):
                ann = ast.unparse(stmt.annotation)
                if re.search(r"\bOptional\[|\bNone\b", ann):
                    out.append((stmt.lineno, f"{stmt.target.id}: {ann}"))
    return out


def scan(source: str) -> list[Finding]:
    """Return v1 findings in source order (one per pattern per line)."""
    lines = source.splitlines()
    findings: dict[tuple[str, int], Finding] = {}
    validator_lines: set[int] = set()

    for p in PATTERNS:
        if p.regex is None:
            continue
        for m in re.finditer(p.regex, source, flags=re.MULTILINE):
            line = source.count("\n", 0, m.start()) + 1
            # ``@validator(pre=...)`` is reported once, as the more specific pattern.
            if p.name == "@validator" and line in validator_lines:
                continue
            if p.name.startswith("@validator("):
                validator_lines.add(line)
            findings.setdefault((p.name, line), Finding(p.name, line, lines[line - 1].strip(), p.query))

    try:
        tree = ast.parse(source)
    except SyntaxError:
        tree = None
    if tree is not None:
        p = _BY_NAME["Optional field without default"]
        for line, snippet in _optional_without_default(tree):
            findings.setdefault((p.name, line), Finding(p.name, line, snippet, p.query))

    return sorted(findings.values(), key=lambda f: (f.line, f.pattern))


def queries(findings: list[Finding]) -> list[str]:
    """Distinct retrieval queries, in order of first appearance."""
    return list(dict.fromkeys(f.query for f in findings))
