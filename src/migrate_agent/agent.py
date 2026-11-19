"""The migration agent: scan → retrieve → patch → test → fix, in bounded rounds.

    result = migrate(source, case=case, max_rounds=3)

Round 1: the static scan lists v1 patterns, retrieval pulls the matching guide
sections, and the LLM returns the full migrated file. If the case's tests fail,
the next round sends the end of the pytest output plus any guide sections the
failure points to (not already sent), and asks for a corrected file. After
``max_rounds`` failed rounds the agent stops and returns ``status="escalated"``
with the last diff and the failure reason, so a human can take over.

Without a test case (any file from the CLI) the agent makes a single pass and
returns ``status="unverified"`` plus any v1 patterns still left in the output.
"""

from __future__ import annotations

import difflib
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from migrate_agent import llm, prompts
from migrate_agent.harness import Case, run_tests
from migrate_agent.retrieval import BM25Retriever, Hit, multi_search
from migrate_agent.scan import queries, scan

PROMPT_TAIL_LINES = 40  # lines of pytest output sent back to the model
LOG_TAIL_LINES = 15  # lines of pytest output kept in the JSONL log
EXTRA_CHUNKS_PER_FIX = 2

_CODE_BLOCK = re.compile(r"```(?:python|py)?[ \t]*\n(.*?)```", re.DOTALL)


@dataclass
class RoundLog:
    case_id: str | None
    round: int
    findings: list[str]
    retrieved: list[str]  # chunk ids sent to the model this round
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    llm_latency_s: float
    test_seconds: float | None
    passed: bool | None  # None = no tests run
    test_output_tail: str


@dataclass
class MigrationResult:
    status: str  # "passed" | "escalated" | "unverified" | "error"
    source: str  # final candidate file
    rounds: list[RoundLog] = field(default_factory=list)
    reason: str | None = None
    diff: str = ""
    remaining_patterns: list[str] = field(default_factory=list)
    latency_s: float = 0.0

    @property
    def cost_usd(self) -> float:
        return sum(r.cost_usd for r in self.rounds)

    @property
    def tokens(self) -> tuple[int, int]:
        return sum(r.input_tokens for r in self.rounds), sum(r.output_tokens for r in self.rounds)


def extract_code(text: str) -> str:
    """Pull the file out of the model's reply (the longest fenced block, else the raw text)."""
    blocks = _CODE_BLOCK.findall(text)
    code = max(blocks, key=len) if blocks else text
    return code.strip("\n") + "\n"


def make_diff(before: str, after: str, name: str = "target.py") -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True), f"a/{name}", f"b/{name}"
        )
    )


def _tail(text: str, n: int) -> str:
    return "\n".join(text.splitlines()[-n:])


def _failure_reason(test_output: str) -> str:
    """Last informative line of pytest output, e.g. ``FAILED test_case.py::test_x - AssertionError``."""
    lines = [ln for ln in test_output.splitlines() if ln.strip()]
    for ln in reversed(lines):
        if ln.startswith(("FAILED", "ERROR", "E ")):
            return ln.strip()
    return lines[-1].strip() if lines else "unknown failure"


def _new_hits(retriever, queries_: list[str], seen: set[str], n: int) -> list[Hit]:
    hits = multi_search(retriever, queries_, k=n + len(seen), depth=n + len(seen))
    return [h for h in hits if h.chunk.id not in seen][:n]


def migrate(
    source: str,
    case: Case | None = None,
    max_rounds: int = 3,
    k: int = 3,
    model: str | None = None,
    retriever=None,
    complete_fn: Callable[..., llm.LLMResult] | None = None,
    log_path: Path | None = None,
) -> MigrationResult:
    start = time.perf_counter()
    retriever = retriever or BM25Retriever()
    complete_fn = complete_fn or llm.complete
    case_id = case.id if case else None

    findings = scan(source)
    hits = multi_search(retriever, queries(findings), k=k) if findings else retriever.search(source, k=k)
    seen = {h.chunk.id for h in hits}
    messages = [
        {"role": "system", "content": prompts.SYSTEM},
        {"role": "user", "content": prompts.first_turn(source, findings, hits)},
    ]

    result = MigrationResult(status="error", source=source)
    round_hits = hits
    for rnd in range(1, max_rounds + 1 if case else 2):
        try:
            resp = complete_fn(messages, model=model)
        except Exception as exc:  # network, auth, rate limit: record and stop
            result.status, result.reason = "error", f"LLM call failed: {type(exc).__name__}: {exc}"
            break
        candidate = extract_code(resp.text)
        result.source = candidate

        test = run_tests(case, candidate) if case else None
        log = RoundLog(
            case_id=case_id,
            round=rnd,
            findings=[f"{f.pattern}@{f.line}" for f in findings] if rnd == 1 else [],
            retrieved=[h.chunk.id for h in round_hits],
            model=resp.model,
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
            cost_usd=resp.cost_usd,
            llm_latency_s=round(resp.latency_s, 3),
            test_seconds=round(test.seconds, 3) if test else None,
            passed=test.passed if test else None,
            test_output_tail=_tail(test.output, LOG_TAIL_LINES) if test else "",
        )
        result.rounds.append(log)
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a") as fh:
                fh.write(json.dumps(asdict(log)) + "\n")

        if test is None:
            result.status = "unverified"
            break
        if test.passed:
            result.status, result.reason = "passed", None
            break

        result.status, result.reason = "escalated", _failure_reason(test.output)
        if rnd == max_rounds:
            break
        # Next round: search the guide with the failure text and any v1 patterns still present.
        tail = _tail(test.output, PROMPT_TAIL_LINES)
        round_hits = _new_hits(retriever, [tail, *queries(scan(candidate))], seen, EXTRA_CHUNKS_PER_FIX)
        seen.update(h.chunk.id for h in round_hits)
        messages += [
            {"role": "assistant", "content": resp.text},
            {"role": "user", "content": prompts.fix_turn(tail, round_hits)},
        ]

    result.diff = make_diff(source, result.source)
    result.remaining_patterns = [f"{f.pattern}@{f.line}" for f in scan(result.source)]
    result.latency_s = round(time.perf_counter() - start, 3)
    return result
