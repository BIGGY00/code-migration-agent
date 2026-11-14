"""Thin LiteLLM wrapper that records tokens, cost and latency for every call.

Any LiteLLM model id works (Anthropic, Bedrock, OpenAI, Gemini, ...). Set the
default in ``.env`` as ``MIGRATE_AGENT_MODEL``. Every call returns an
``LLMResult`` so the eval harness can report cost per migration.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import litellm
from dotenv import load_dotenv

load_dotenv()
litellm.suppress_debug_info = True


@dataclass
class LLMResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_s: float


def default_model() -> str:
    model = os.environ.get("MIGRATE_AGENT_MODEL")
    if not model:
        raise RuntimeError("Set MIGRATE_AGENT_MODEL in .env (any LiteLLM model id).")
    return model


def complete(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> LLMResult:
    model = model or default_model()
    start = time.perf_counter()
    resp = litellm.completion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    latency = time.perf_counter() - start
    usage = getattr(resp, "usage", None)
    try:
        cost = float(litellm.completion_cost(completion_response=resp))
    except Exception:  # unknown pricing for this model id
        cost = 0.0
    return LLMResult(
        text=resp.choices[0].message.content or "",
        model=model,
        input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
        output_tokens=getattr(usage, "completion_tokens", 0) or 0,
        cost_usd=cost,
        latency_s=latency,
    )
