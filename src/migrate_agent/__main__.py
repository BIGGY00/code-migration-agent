"""Command line entry point.

    python -m migrate_agent path/to/file.py            # single pass, prints the diff
    python -m migrate_agent path/to/file.py --out new.py
    python -m migrate_agent --case 09_custom_root      # eval case: test-driven loop

Each run appends one JSON line per round to ``results/runs/<timestamp>-<name>.jsonl``.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from migrate_agent.agent import migrate
from migrate_agent.harness import CASES_DIR, load_cases

RUNS_DIR = CASES_DIR.parents[1] / "results" / "runs"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m migrate_agent", description="Migrate Pydantic v1 code to v2.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("file", nargs="?", type=Path, help="Python file to migrate (no tests: single pass)")
    src.add_argument("--case", help="eval case id from evals/cases (runs its tests each round)")
    ap.add_argument("--out", type=Path, help="write the migrated file here (default: print the diff only)")
    ap.add_argument("--max-rounds", type=int, default=3)
    ap.add_argument("--model", default=None, help="LiteLLM model id (default: $MIGRATE_AGENT_MODEL)")
    args = ap.parse_args(argv)

    if args.case:
        cases = {c.id: c for c in load_cases()}
        if args.case not in cases:
            ap.error(f"unknown case {args.case!r}; choose from: {', '.join(cases)}")
        case = cases[args.case]
        source, name = case.before.read_text(), case.id
    else:
        case, source, name = None, args.file.read_text(), args.file.stem

    log_path = RUNS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}-{name}.jsonl"
    result = migrate(source, case=case, max_rounds=args.max_rounds, model=args.model, log_path=log_path)

    for r in result.rounds:
        verdict = {True: "pass", False: "fail", None: "not tested"}[r.passed]
        print(
            f"round {r.round}: {verdict:10} chunks={','.join(r.retrieved) or '-'} "
            f"tokens={r.input_tokens}/{r.output_tokens} cost=${r.cost_usd:.5f} llm={r.llm_latency_s:.1f}s"
        )
    print(f"\nstatus: {result.status}" + (f"  ({result.reason})" if result.reason else ""))
    tin, tout = result.tokens
    print(f"total: {len(result.rounds)} round(s), tokens {tin}/{tout}, cost ${result.cost_usd:.5f}, {result.latency_s:.1f}s")
    if result.remaining_patterns:
        print(f"v1 patterns still present: {', '.join(result.remaining_patterns)}")
    print(f"log: {log_path if result.rounds else '(no rounds ran, nothing logged)'}\n")
    print(result.diff or "(no changes)")
    if args.out:
        args.out.write_text(result.source)
        print(f"\nwrote {args.out}")
    return 0 if result.status in ("passed", "unverified") else 1


if __name__ == "__main__":
    sys.exit(main())
