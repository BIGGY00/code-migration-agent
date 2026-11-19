"""Run the 14-case Pydantic v1 -> v2 evaluation harness across modes.

Modes:
  * ``bump_pydantic``: rule-based baseline (`bump-pydantic target.py`), $0 API cost.
  * ``single_shot``:   one LLM call with raw file only (no scan, no RAG, no test loop).
  * ``agent``:         scan -> BM25 retrieval -> patch -> pytest -> fix loop.
  * ``agent_no_rag``:  ablation: same scan and pytest fix loop, no guide retrieval.

Usage:
    python scripts/run_eval.py --mode bump_pydantic
    python scripts/run_eval.py --mode single_shot --model anthropic/claude-haiku-5-5
    python scripts/run_eval.py --mode agent --model anthropic/claude-haiku-5-5
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from migrate_agent import llm  # noqa: E402
from migrate_agent.agent import extract_code, make_diff, migrate  # noqa: E402
from migrate_agent.harness import Case, load_cases, run_tests  # noqa: E402
from migrate_agent.retrieval import BM25Retriever  # noqa: E402
from migrate_agent.scan import scan  # noqa: E402

RESULTS_DIR = ROOT / "results"
RUNS_DIR = RESULTS_DIR / "runs"

SINGLE_SHOT_SYSTEM = """\
You migrate Python code from Pydantic v1 to Pydantic v2.

Rules:
- Return the COMPLETE migrated file in a single ```python code block and nothing else.
- Keep behaviour and every public name (classes, functions, signatures, field names) the same.
- Use only Pydantic v2 APIs. Do not import `pydantic.v1` and do not keep deprecated v1 methods,
  decorators or class-based `Config`: the code is tested with Pydantic deprecation warnings
  turned into errors.
- Change only what the migration needs. Do not add tests, prints or explanations.
"""


@dataclass
class CaseEvalResult:
    case_id: str
    difficulty: str
    status: str  # "passed" | "failed" | "escalated" | "error"
    passed: bool
    rounds: int
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_s: float
    remaining_patterns: list[str]
    reason: str | None = None
    suite: str = "core"


def _save_source(out_dir: Path | None, case: Case, source: str) -> None:
    """Keep the migrated file next to the JSONL log so results can be audited."""
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{case.id}.py").write_text(source)


def _failure_line(output: str) -> str:
    lines = [ln.strip() for ln in output.splitlines() if ln.strip()]
    for ln in reversed(lines):
        if ln.startswith(("FAILED", "ERROR", "E ")):
            return ln
    return lines[-1] if lines else "tests failed"


def run_single_shot(
    case: Case,
    model: str | None = None,
    complete_fn: Callable[..., llm.LLMResult] | None = None,
    log_path: Path | None = None,
    out_dir: Path | None = None,
) -> CaseEvalResult:
    """Single LLM call with no retrieval, no static scan hints, and no retry loop."""
    complete_fn = complete_fn or llm.complete
    before = case.before.read_text()
    start = time.perf_counter()
    messages = [
        {"role": "system", "content": SINGLE_SHOT_SYSTEM},
        {
            "role": "user",
            "content": f"Migrate this Python file from Pydantic v1 to Pydantic v2:\n\n```python\n{before}```",
        },
    ]
    try:
        resp = complete_fn(messages, model=model)
    except Exception as exc:
        return CaseEvalResult(
            case_id=case.id,
            difficulty=case.difficulty,
            suite=case.suite,
            status="error",
            passed=False,
            rounds=0,
            model=model or "unknown",
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            latency_s=round(time.perf_counter() - start, 3),
            remaining_patterns=[],
            reason=f"LLM call failed: {type(exc).__name__}: {exc}",
        )

    candidate = extract_code(resp.text)
    _save_source(out_dir, case, candidate)
    test = run_tests(case, candidate)
    latency = round(time.perf_counter() - start, 3)
    remaining = [f"{f.pattern}@{f.line}" for f in scan(candidate)]

    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "case_id": case.id,
            "mode": "single_shot",
            "round": 1,
            "model": resp.model,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
            "cost_usd": resp.cost_usd,
            "llm_latency_s": round(resp.latency_s, 3),
            "test_seconds": round(test.seconds, 3),
            "passed": test.passed,
            "test_output_tail": "\n".join(test.output.splitlines()[-15:]),
        }
        with log_path.open("a") as fh:
            fh.write(json.dumps(row) + "\n")

    return CaseEvalResult(
        case_id=case.id,
        difficulty=case.difficulty,
        suite=case.suite,
        status="passed" if test.passed else "failed",
        passed=test.passed,
        rounds=1,
        model=resp.model,
        input_tokens=resp.input_tokens,
        output_tokens=resp.output_tokens,
        cost_usd=resp.cost_usd,
        latency_s=latency,
        remaining_patterns=remaining,
        reason=None if test.passed else _failure_line(test.output),
    )


def _find_bump_pydantic(executable: str | None = None) -> str:
    if executable:
        return executable
    sibling = Path(sys.executable).parent / "bump-pydantic"
    if sibling.exists():
        return str(sibling)
    found = shutil.which("bump-pydantic")
    if found:
        return found
    raise RuntimeError("bump-pydantic executable not found. Install with: pip install -e '.[baseline]'")


def run_bump_pydantic(
    case: Case,
    executable: str | None = None,
    log_path: Path | None = None,
    out_dir: Path | None = None,
) -> CaseEvalResult:
    """Rule-based baseline: run `bump-pydantic target.py` then evaluate with pytest."""
    exe = _find_bump_pydantic(executable)
    before = case.before.read_text()
    start = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix=f"bump-{case.id}-") as tmp:
        tmp_path = Path(tmp)
        target = tmp_path / "target.py"
        target.write_text(before)
        proc = subprocess.run(
            [exe, "target.py"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout).strip().splitlines()
            return CaseEvalResult(
                case_id=case.id,
                difficulty=case.difficulty,
                suite=case.suite,
                status="error",
                passed=False,
                rounds=0,
                model="bump-pydantic",
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                latency_s=round(time.perf_counter() - start, 3),
                remaining_patterns=[],
                reason=f"bump-pydantic exited {proc.returncode}: {err[-1] if err else 'unknown'}",
            )
        migrated = target.read_text()
    _save_source(out_dir, case, migrated)

    test = run_tests(case, migrated)
    latency = round(time.perf_counter() - start, 3)
    remaining = [f"{f.pattern}@{f.line}" for f in scan(migrated)]
    changed = bool(make_diff(before, migrated))

    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "case_id": case.id,
            "mode": "bump_pydantic",
            "changed": changed,
            "test_seconds": round(test.seconds, 3),
            "passed": test.passed,
            "test_output_tail": "\n".join(test.output.splitlines()[-15:]),
        }
        with log_path.open("a") as fh:
            fh.write(json.dumps(row) + "\n")

    return CaseEvalResult(
        case_id=case.id,
        difficulty=case.difficulty,
        suite=case.suite,
        status="passed" if test.passed else "failed",
        passed=test.passed,
        rounds=0,
        model="bump-pydantic",
        input_tokens=0,
        output_tokens=0,
        cost_usd=0.0,
        latency_s=latency,
        remaining_patterns=remaining,
        reason=None if test.passed else _failure_line(test.output),
    )


def run_agent_case(
    case: Case,
    max_rounds: int = 3,
    k: int = 3,
    model: str | None = None,
    retriever=None,
    complete_fn: Callable[..., llm.LLMResult] | None = None,
    log_path: Path | None = None,
    out_dir: Path | None = None,
    use_retrieval: bool = True,
) -> CaseEvalResult:
    """Full RAG + static scan + test-driven fix loop (``use_retrieval=False`` for the ablation)."""
    res = migrate(
        case.before.read_text(),
        case=case,
        max_rounds=max_rounds,
        k=k,
        model=model,
        retriever=retriever,
        complete_fn=complete_fn,
        log_path=log_path,
        use_retrieval=use_retrieval,
    )
    _save_source(out_dir, case, res.source)
    tin, tout = res.tokens
    used_model = res.rounds[-1].model if res.rounds else (model or "unknown")
    return CaseEvalResult(
        case_id=case.id,
        difficulty=case.difficulty,
        suite=case.suite,
        status=res.status,
        passed=res.status == "passed",
        rounds=len(res.rounds),
        model=used_model,
        input_tokens=tin,
        output_tokens=tout,
        cost_usd=res.cost_usd,
        latency_s=res.latency_s,
        remaining_patterns=res.remaining_patterns,
        reason=res.reason,
    )


def summarize(mode: str, model_label: str, results: list[CaseEvalResult]) -> dict:
    total = len(results)
    passed_rows = [r for r in results if r.passed]
    passed = len(passed_rows)
    avg_rounds_passed = (
        round(sum(r.rounds for r in passed_rows) / passed, 2) if passed else None
    )
    avg_rounds_all = round(sum(r.rounds for r in results) / total, 2) if total else 0.0
    total_cost = round(sum(r.cost_usd for r in results), 6)
    avg_cost = round(total_cost / total, 6) if total else 0.0
    avg_latency = round(sum(r.latency_s for r in results) / total, 3) if total else 0.0
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": mode,
        "model": model_label,
        "total_cases": total,
        "passed_cases": passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "avg_rounds_to_pass": avg_rounds_passed,
        "avg_rounds_all": avg_rounds_all,
        "total_input_tokens": sum(r.input_tokens for r in results),
        "total_output_tokens": sum(r.output_tokens for r in results),
        "total_cost_usd": total_cost,
        "avg_cost_usd": avg_cost,
        "avg_latency_s": avg_latency,
        "by_suite": {
            su: {
                "total_cases": sum(r.suite == su for r in results),
                "passed_cases": sum(r.passed for r in results if r.suite == su),
                "total_cost_usd": round(sum(r.cost_usd for r in results if r.suite == su), 6),
            }
            for su in sorted({r.suite for r in results})
        },
        "cases": [asdict(r) for r in results],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", required=True, choices=["agent", "agent_no_rag", "single_shot", "bump_pydantic"])
    ap.add_argument("--model", default=None, help="LiteLLM model id (default: $MIGRATE_AGENT_MODEL)")
    ap.add_argument("--max-rounds", type=int, default=3)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--cases", nargs="*", help="Optional subset of case ids")
    ap.add_argument("--out", type=Path, default=None, help="Output summary JSON path")
    args = ap.parse_args(argv)

    all_cases = load_cases()
    if args.cases:
        wanted = set(args.cases)
        cases = [c for c in all_cases if c.id in wanted]
        missing = wanted - {c.id for c in cases}
        if missing:
            ap.error(f"unknown case id(s): {', '.join(sorted(missing))}")
    else:
        cases = all_cases

    model_label = "bump-pydantic" if args.mode == "bump_pydantic" else (args.model or llm.default_model())
    out_path = args.out or (RESULTS_DIR / f"summary_{args.mode}.json")
    stamp = f"{datetime.now():%Y%m%d-%H%M%S}-{args.mode}"
    log_path = RUNS_DIR / f"{stamp}.jsonl"
    out_dir = RUNS_DIR / stamp  # migrated files, one per case

    retriever = BM25Retriever() if args.mode == "agent" else None
    results: list[CaseEvalResult] = []
    for case in cases:
        if args.mode == "bump_pydantic":
            res = run_bump_pydantic(case, log_path=log_path, out_dir=out_dir)
        elif args.mode == "single_shot":
            res = run_single_shot(case, model=model_label, log_path=log_path, out_dir=out_dir)
        else:
            res = run_agent_case(
                case,
                max_rounds=args.max_rounds,
                k=args.k,
                model=model_label,
                retriever=retriever,
                log_path=log_path,
                out_dir=out_dir,
                use_retrieval=args.mode == "agent",
            )
        results.append(res)
        verdict = "PASS" if res.passed else res.status.upper()
        print(
            f"{case.id:30} {verdict:9} rounds={res.rounds} "
            f"cost=${res.cost_usd:.5f} time={res.latency_s:.2f}s"
            + (f"  ({res.reason[:70]})" if res.reason else "")
        )

    summary = summarize(args.mode, model_label, results)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(
        f"\n{args.mode} ({model_label}): {summary['passed_cases']}/{summary['total_cases']} passed "
        f"({summary['pass_rate']:.1%}), total_cost=${summary['total_cost_usd']:.5f}, "
        f"avg_latency={summary['avg_latency_s']:.2f}s -> {out_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
