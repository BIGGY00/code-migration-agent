"""Generate the Markdown evaluation report from results/summary_*.json.

Usage:
    python scripts/make_report.py
    python scripts/make_report.py --update-readme
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
README_PATH = ROOT / "README.md"

MODES = [
    ("bump_pydantic", "Rule-based (`bump-pydantic`)"),
    ("single_shot", "Single-shot LLM (no RAG / no loop)"),
    ("agent", "Agent (scan + BM25 RAG + pytest loop)"),
    ("agent_no_rag", "Ablation: agent without retrieval (scan + pytest loop)"),
]

START_MARKER = "<!-- RESULTS_START -->"
END_MARKER = "<!-- RESULTS_END -->"


def load_summary(results_dir: Path, mode: str) -> dict | None:
    path = results_dir / f"summary_{mode}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def format_report(results_dir: Path = RESULTS_DIR) -> str:
    summaries = {mode: load_summary(results_dir, mode) for mode, _ in MODES}
    lines = [
        "| Mode | Model / Tool | Core set | Hard set | All cases | Avg rounds (passed) | Total cost (USD) | Avg latency / case |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for mode, label in MODES:
        s = summaries[mode]
        if s is None:
            lines.append(f"| {label} | _pending LLM run_ | — | — | — | — | — | — |")
            continue
        passed = f"{s['passed_cases']}/{s['total_cases']} ({s['pass_rate']:.1%})"
        avg_r = "0 (rule)" if mode == "bump_pydantic" else (
            f"{s['avg_rounds_to_pass']:.2f}" if s["avg_rounds_to_pass"] is not None else "—"
        )
        cost = "$0.00000" if mode == "bump_pydantic" else f"${s['total_cost_usd']:.5f}"
        lat = f"{s['avg_latency_s']:.2f}s"
        suite_cells = []
        for su in ("core", "hard"):
            rows = [c for c in s["cases"] if c.get("suite", "core") == su]
            suite_cells.append(f"{sum(c['passed'] for c in rows)}/{len(rows)}" if rows else "—")
        lines.append(f"| {label} | `{s['model']}` | {suite_cells[0]} | {suite_cells[1]} | {passed} | {avg_r} | {cost} | {lat} |")

    available = [s for s in summaries.values() if s is not None]
    if available:
        case_ids = [c["case_id"] for c in available[0]["cases"]]
        by_mode = {
            mode: {c["case_id"]: c for c in summaries[mode]["cases"]}
            for mode, _ in MODES
            if summaries[mode] is not None
        }
        lines.extend([
            "",
            "<details>",
            f"<summary>Per-case breakdown across all {len(case_ids)} eval cases</summary>",
            "",
            "| Case | Set | Difficulty | " + " | ".join(f"`{m}`" for m, _ in MODES) + " |",
            "|---|---|---|" + "---|" * len(MODES),
        ])
        for cid in case_ids:
            first = available[0]["cases"][case_ids.index(cid)]
            diff, suite = first["difficulty"], first.get("suite", "core")
            cells = []
            for mode, _ in MODES:
                row = by_mode.get(mode, {}).get(cid)
                if row is None:
                    cells.append("pending")
                elif row["passed"]:
                    cells.append("PASS" if mode == "bump_pydantic" else f"PASS (r{row['rounds']})")
                else:
                    cells.append(f"FAIL ({row['status']})")
            lines.append(f"| `{cid}` | {suite} | {diff} | " + " | ".join(cells) + " |")
        lines.extend(["", "</details>"])

    return "\n".join(lines)


def update_readme(report_md: str, readme_path: Path = README_PATH) -> None:
    text = readme_path.read_text()
    block = f"{START_MARKER}\n{report_md}\n{END_MARKER}"
    if START_MARKER in text and END_MARKER in text:
        updated = re.sub(
            rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
            block,
            text,
            flags=re.DOTALL,
        )
    else:
        updated = text.rstrip() + f"\n\n{block}\n"
    readme_path.write_text(updated)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    ap.add_argument("--update-readme", action="store_true", help="write table into README.md")
    args = ap.parse_args(argv)

    md = format_report(args.results_dir)
    print(md)
    if args.update_readme:
        update_readme(md)
        print(f"\nUpdated {README_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
