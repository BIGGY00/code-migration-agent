"""Agent loop tests with a scripted fake LLM (no network, no API cost)."""

import json

from migrate_agent.agent import extract_code, migrate
from migrate_agent.harness import load_cases
from migrate_agent.llm import LLMResult


class FakeLLM:
    """Returns scripted replies in order and records the messages it was sent."""

    def __init__(self, *replies: str):
        self.replies = list(replies)
        self.calls: list[list[dict]] = []

    def __call__(self, messages, model=None):
        self.calls.append([dict(m) for m in messages])
        text = self.replies[min(len(self.calls), len(self.replies)) - 1]
        return LLMResult(text=text, model="fake", input_tokens=100, output_tokens=50, cost_usd=0.001, latency_s=0.01)


def fenced(code: str) -> str:
    return f"Here you go:\n```python\n{code}```\n"


def case(case_id: str):
    return next(c for c in load_cases() if c.id == case_id)


def test_extract_code_takes_fenced_block_or_raw_text():
    assert extract_code(fenced("x = 1\n")) == "x = 1\n"
    assert extract_code("x = 1") == "x = 1\n"


def test_passes_in_first_round_with_grounded_prompt(tmp_path):
    c = case("01_dict_json")
    fake = FakeLLM(fenced(c.reference.read_text()))
    log = tmp_path / "run.jsonl"
    result = migrate(c.before.read_text(), case=c, complete_fn=fake, log_path=log)

    assert result.status == "passed" and len(result.rounds) == 1
    prompt = fake.calls[0][1]["content"]
    assert "BaseModel.dict()" in prompt and "[c06-changes-to-pydantic-basemodel]" in prompt
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    assert rows[0]["case_id"] == "01_dict_json" and rows[0]["passed"] is True
    assert "c06-changes-to-pydantic-basemodel" in rows[0]["retrieved"]


def test_feeds_test_failure_back_and_passes_in_round_two():
    c = case("09_custom_root")
    fake = FakeLLM(fenced(c.before.read_text()), fenced(c.reference.read_text()))
    result = migrate(c.before.read_text(), case=c, complete_fn=fake)

    assert result.status == "passed"
    assert [r.passed for r in result.rounds] == [False, True]
    fix_prompt = fake.calls[1][-1]["content"]
    assert "failed its tests" in fix_prompt
    assert fake.calls[1][-2]["role"] == "assistant"
    sent = result.rounds[0].retrieved + result.rounds[1].retrieved
    assert len(sent) == len(set(sent)), "a guide chunk was sent twice"


def test_escalates_after_max_rounds_with_reason_and_diff():
    c = case("13_generic_model")
    bad = c.before.read_text().replace("Page[int]", "Page[int]  # still v1")
    fake = FakeLLM(fenced(bad))
    result = migrate(c.before.read_text(), case=c, complete_fn=fake, max_rounds=3)

    assert result.status == "escalated" and len(result.rounds) == 3
    assert result.reason and result.diff
    assert any(p.startswith("GenericModel") for p in result.remaining_patterns)
    assert abs(result.cost_usd - 0.003) < 1e-9


def test_without_case_makes_one_unverified_pass():
    c = case("11_copy_schema")
    fake = FakeLLM(fenced(c.reference.read_text()))
    result = migrate(c.before.read_text(), complete_fn=fake, max_rounds=3)
    assert result.status == "unverified" and len(result.rounds) == 1
    assert result.rounds[0].passed is None and result.remaining_patterns == []


def test_llm_error_is_recorded_not_raised():
    def boom(messages, model=None):
        raise RuntimeError("no key")

    c = case("01_dict_json")
    result = migrate(c.before.read_text(), case=c, complete_fn=boom)
    assert result.status == "error" and "no key" in result.reason
