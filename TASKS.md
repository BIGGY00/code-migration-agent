# TASKS — code-migration-agent

Goal: public repo with real results within ~1 week. Tick each box when its "Done when" holds.

## Step 1 — Eval set and harness ✅
- [x] Repo layout, `pyproject.toml`, `.env.example`, MIT license
- [x] 14 eval cases (`before.py`, `reference.py`, `test_case.py`, `meta.json`)
- [x] `harness.run_tests` runs a candidate under Pydantic v2 with deprecation warnings as errors
- [x] `scripts/validate_cases.py` → 14/14 valid (Pydantic 2.14.3, 2026-11-14)
- [x] LiteLLM wrapper with token/cost/latency (`llm.py`) — **not yet run against a real model: Big runs `scripts/smoke_llm.py` after filling `.env`**

## Step 2 — RAG over the migration guide ✅
- [x] Snapshot the official Pydantic migration guide (markdown source from the pydantic GitHub repo, `docs/migration.md`) into `data/migration_guide.md`, with source URL, commit/date and license note in `data/SOURCE.md` — commit `91c44cd`, 2026-10-31, MIT
- [x] `src/migrate_agent/retrieval.py`: chunk by heading (keep heading path as chunk title), BM25 index (`rank-bm25`); optional embeddings via `litellm.embedding` behind a flag — 35 chunks; embeddings behind `--embeddings`, **implemented but not yet run** (needs `MIGRATE_AGENT_EMBED_MODEL`)
- [x] Add `guide_sections` (expected heading titles) to each case's `meta.json` — checked against real guide headings in `tests/test_retrieval.py`
- [x] `scripts/eval_retrieval.py`: recall@3 per case using `guide_sections`
- Done when: recall@3 is reported for all cases and saved to `results/retrieval.json` — **BM25 recall@3 = 0.929 (13/14 cases), 2026-11-14; miss: `01_dict_json`**

## Step 3 — Agent loop
- [ ] `src/migrate_agent/scan.py`: cheap static scan (regex/AST) for v1 patterns → hints + retrieval queries
- [ ] `src/migrate_agent/agent.py`: `migrate(source, case=None, max_rounds=3)` → find → retrieve → patch (LLM returns full file) → `run_tests` → on failure feed test-output tail + more retrieval → retry → return result with per-round log
- [ ] Prompt in `src/migrate_agent/prompts.py`; cite retrieved chunk ids in the log
- [ ] Escalation: after `max_rounds`, return `status="escalated"` with the last diff and failure reason
- [ ] `python -m migrate_agent path/to/file.py` CLI for any file (no tests → single pass + report)
- Done when: the agent passes at least one easy and one hard case end to end with a real model

## Step 4 — Eval + baselines
- [ ] `scripts/run_eval.py --mode {agent,single_shot,bump_pydantic} [--model ...]`
  - `single_shot`: one LLM call, no retrieval, no test loop
  - `bump_pydantic`: run the rule-based tool on a copy of `before.py`
- [ ] Metrics per case and overall: pass rate, rounds to pass, cost (USD), latency; save `results/summary_<mode>.json` + raw JSONL in `results/runs/`
- [ ] `scripts/make_report.py` → markdown results table pasted into README
- Done when: all three modes ran on all cases and the README table shows real numbers, failures included

## Step 5 — Ship
- [ ] `Dockerfile` (slim Python image, runs `validate_cases` by default)
- [ ] GitHub Actions: on push → `pip install`, `validate_cases.py`, `pytest`; on `workflow_dispatch` → LLM eval with repo secret
- [ ] README: problem, architecture diagram (mermaid), results table, limitations, what's next
- [ ] Optional: small Streamlit page to paste v1 code and watch the loop
- Done when: repo is public on github.com/BIGGY00, CI is green, README has results

## After shipping (Big + career Project)
- Fill the resume line in `career/portfolio-A-scope.md` with the real numbers and the GitHub link
- Add the project to the resume "Publication" section (rename to "Publication & Projects") and to LinkedIn Featured
