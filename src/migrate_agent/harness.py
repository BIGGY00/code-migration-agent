"""Run one eval case's tests against a candidate file.

The candidate is copied into a temp dir as ``target.py`` next to the case's
``test_case.py`` and pytest runs there under Pydantic v2. Pydantic deprecation
warnings are turned into errors, so code that only "works" through v1
compatibility shims counts as a failed migration.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

CASES_DIR = Path(__file__).resolve().parents[2] / "evals" / "cases"

PYTEST_ARGS = [
    "-q",
    "-p",
    "no:cacheprovider",
    "-W",
    "error::pydantic.warnings.PydanticDeprecationWarning",
]


@dataclass
class Case:
    id: str
    dir: Path
    patterns: list[str] = field(default_factory=list)
    difficulty: str = "unknown"
    guide_sections: list[str] = field(default_factory=list)  # expected migration-guide headings

    @property
    def before(self) -> Path:
        return self.dir / "before.py"

    @property
    def reference(self) -> Path:
        return self.dir / "reference.py"

    @property
    def test(self) -> Path:
        return self.dir / "test_case.py"


@dataclass
class TestRun:
    passed: bool
    seconds: float
    output: str  # tail of pytest output, used as feedback for the fix step


def load_cases(cases_dir: Path = CASES_DIR) -> list[Case]:
    cases = []
    for d in sorted(p for p in cases_dir.iterdir() if p.is_dir()):
        meta = json.loads((d / "meta.json").read_text())
        cases.append(
            Case(
                id=meta["id"],
                dir=d,
                patterns=meta["patterns"],
                difficulty=meta["difficulty"],
                guide_sections=meta.get("guide_sections", []),
            )
        )
    return cases


def run_tests(case: Case, candidate_source: str, timeout: float = 60.0, tail_lines: int = 60) -> TestRun:
    """Run ``case``'s tests against ``candidate_source`` (the full text of target.py)."""
    with tempfile.TemporaryDirectory(prefix=f"cma-{case.id}-") as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "target.py").write_text(candidate_source)
        shutil.copy(case.test, tmp_path / "test_case.py")
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", *PYTEST_ARGS, "test_case.py"],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            passed = proc.returncode == 0
            out = (proc.stdout + proc.stderr).strip()
        except subprocess.TimeoutExpired:
            passed, out = False, f"TIMEOUT after {timeout}s"
        seconds = time.perf_counter() - start
    tail = "\n".join(out.splitlines()[-tail_lines:])
    return TestRun(passed=passed, seconds=seconds, output=tail)
