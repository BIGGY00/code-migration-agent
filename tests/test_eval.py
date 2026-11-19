"""Unit tests for the Step 4 evaluation harness and report generator."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import make_report  # noqa: E402
import run_eval  # noqa: E402
from migrate_agent.harness import load_cases  # noqa: E402
from migrate_agent.llm import LLMResult  # noqa: E402


def _case(case_id: str):
    return next(c for c in load_cases() if c.id == case_id)


def test_run_single_shot_uses_one_call_without_rag(tmp_path):
    c = _case("01_dict_json")
    seen_prompts = []

    def fake_complete(messages, model=None):
        seen_prompts.append(messages)
        return LLMResult(
            text=f"```python\n{c.reference.read_text()}```",
            model="fake-model",
            input_tokens=80,
            output_tokens=40,
            cost_usd=0.0005,
            latency_s=0.1,
        )

    log = tmp_path / "single.jsonl"
    res = run_eval.run_single_shot(c, model="fake-model", complete_fn=fake_complete, log_path=log)
    assert res.passed is True
    assert res.rounds == 1
    assert len(seen_prompts) == 1
    assert "Migration guide excerpts" not in seen_prompts[0][1]["content"]
    assert json.loads(log.read_text().splitlines()[0])["mode"] == "single_shot"


def test_run_bump_pydantic_baseline_executes():
    c = _case("03_validator")
    res = run_eval.run_bump_pydantic(c)
    assert res.model == "bump-pydantic"
    assert res.cost_usd == 0.0
    assert res.passed is True


def test_summarize_and_format_report(tmp_path):
    c1 = _case("01_dict_json")
    c2 = _case("02_parse_obj_raw")
    r1 = run_eval.CaseEvalResult(c1.id, c1.difficulty, "passed", True, 1, "anthropic/claude-haiku-5-5", 100, 50, 0.001, 0.5, [])
    r2 = run_eval.CaseEvalResult(c2.id, c2.difficulty, "escalated", False, 3, "anthropic/claude-haiku-5-5", 300, 150, 0.003, 1.5, ["parse_obj@10"], "AssertionError")
    summary = run_eval.summarize("agent", "anthropic/claude-haiku-5-5", [r1, r2])
    assert summary["passed_cases"] == 1
    assert summary["pass_rate"] == 0.5
    assert summary["avg_rounds_to_pass"] == 1.0
    assert summary["total_cost_usd"] == 0.004

    (tmp_path / "summary_agent.json").write_text(json.dumps(summary))
    md = make_report.format_report(tmp_path)
    assert "anthropic/claude-haiku-5-5" in md
    assert "1/2 (50.0%)" in md
    assert "01_dict_json" in md
