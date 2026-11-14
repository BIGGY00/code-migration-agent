"""One cheap call to check that .env and the LiteLLM model id work.

Usage:  python scripts/smoke_llm.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from migrate_agent.llm import complete  # noqa: E402

r = complete([{"role": "user", "content": "Reply with exactly: ok"}], max_tokens=5)
print(f"model={r.model} reply={r.text!r} in={r.input_tokens} out={r.output_tokens} "
      f"cost=${r.cost_usd:.6f} latency={r.latency_s:.2f}s")
