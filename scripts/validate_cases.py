"""Sanity-check the eval set.

Every case must satisfy two rules under Pydantic v2:
  1. reference.py passes its tests  (the tests are correct and achievable)
  2. before.py fails its tests      (the case really needs migrating)

Usage:  python scripts/validate_cases.py
Exit code is non-zero if any case breaks a rule.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pydantic  # noqa: E402

from migrate_agent.harness import load_cases, run_tests  # noqa: E402


def main() -> int:
    cases = load_cases()
    print(f"Pydantic {pydantic.VERSION} | {len(cases)} cases\n")
    print(f"{'case':32} {'difficulty':10} {'reference':10} {'before':10} ok")
    bad = []
    for case in cases:
        ref = run_tests(case, case.reference.read_text())
        bef = run_tests(case, case.before.read_text())
        ok = ref.passed and not bef.passed
        print(
            f"{case.id:32} {case.difficulty:10} "
            f"{'pass' if ref.passed else 'FAIL':10} {'fail' if not bef.passed else 'PASS':10} "
            f"{'yes' if ok else 'NO'}"
        )
        if not ok:
            bad.append((case.id, ref, bef))
    for cid, ref, bef in bad:
        print(f"\n--- {cid} ---")
        if not ref.passed:
            print("reference.py failed:\n" + ref.output)
        if bef.passed:
            print("before.py unexpectedly passed under v2")
    print(f"\n{len(cases) - len(bad)}/{len(cases)} cases valid")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
