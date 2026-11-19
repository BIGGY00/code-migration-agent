# TASKS — code-migration-agent

Goal: public repo with real results within ~1 week. Tick each box when its "Done when" holds.

## Step 1 — Eval set and harness ✅
- [x] Repo layout, `pyproject.toml`, `.env.example`, MIT license
- [x] 14 eval cases (`before.py`, `reference.py`, `test_case.py`, `meta.json`)
- [x] `harness.run_tests` runs a candidate under Pydantic v2 with deprecation warnings as errors
- [x] `scripts/validate_cases.py` → 14/14 valid (Pydantic 2.14.3, 2026-11-14)
- [x] LiteLLM wrapper with token/cost/latency (`llm.py`) — default model `anthropic/claude-haiku-5-5` (Claude API); smoke test passed 2026-11-20

## Step 2 — RAG over the migration guide ✅
- [x] Snapshot the official Pydantic migration guide (`data/migration_guide.md`, commit `91c44cd`, 2026-10-31, MIT)
- [x] `src/migrate_agent/retrieval.py`: 35 chunks + BM25 index (`rank-bm25`); optional embeddings behind `--embeddings`
- [x] `guide_sections` labels in each `meta.json` + unit tests in `tests/test_retrieval.py`
- [x] `scripts/eval_retrieval.py`: BM25 recall@3 = **0.929** (13/14 whole-file), **1.000** (14/14 per-pattern scan)

## Step 3 — Agent loop ✅
- [x] `src/migrate_agent/scan.py`: 22 regex/AST rules; flags all 14 `before.py`, 0 false positives on `reference.py`
- [x] `src/migrate_agent/agent.py`: `migrate(source, case=None, max_rounds=3)` loop + JSONL logging + escalation
- [x] `src/migrate_agent/prompts.py` + `python -m migrate_agent` CLI
- [x] Done when: the agent passes at least one easy and one hard case end to end with a real model — **2026-11-20, `anthropic/claude-haiku-5-5`: `01_dict_json` (easy), `09_custom_root` (hard), `13_generic_model` (hard) all passed in round 1, $0.001436 total** (`results/agent_step3_check.json`)

## Step 4 — Eval + baselines ✅
- [x] `scripts/run_eval.py --mode {agent,single_shot,bump_pydantic} [--model ...]`
- [x] `bump-pydantic` baseline run across all 14 cases → `results/summary_bump_pydantic.json` (**4/14 = 28.6%**, $0, 1.33s avg)
- [x] `scripts/make_report.py` → markdown results table + `--update-readme`
- [x] `tests/test_eval.py` unit tests passing
- [x] Done when: `single_shot` and `agent` modes run on all 14 cases with `anthropic/claude-haiku-5-5` and `README.md` shows all three modes — **2026-11-20: bump-pydantic 4/14, single_shot 14/14 ($0.00210), agent 14/14 ($0.00660, all in round 1). The eval set is saturated; the agent shows no accuracy gain yet.**
- [x] Follow-up: 10 hard cases (15–24, silent v2 behaviour changes + one 80-line multi-pattern module), 24/24 valid — **2026-11-20, 24 cases: bump-pydantic 4/24, single_shot 20/24, agent 24/24. Hard set over 4 runs: single_shot 6, 5, 5, 6 /10; agent 10/10 every run** (`results/repeats/hard_summary.json`)
- [x] Ablation `--mode agent_no_rag` (scan + test loop, no retrieval) — **2026-11-20: 24/24, $0.0072; hard set 10/10 in 4 of 4 runs ($0.0218 for 4 runs vs $0.0533 with retrieval). The gain comes from the test loop; retrieval added cost, not accuracy.**

## Step 5 — Packaging, CI & Ship (Docker + CI + README ready; GitHub push pending Big's review)
- [x] `Dockerfile` & `.dockerignore` (slim Python 3.11 image, runs `validate_cases.py && pytest`)
- [x] `.github/workflows/ci.yml` (`push`/`pull_request` offline tests + baseline; `workflow_dispatch` LLM eval with `ANTHROPIC_API_KEY` secret)
- [x] `README.md`: problem, Mermaid architecture diagram, retrieval & baseline results, limitations, Claude API quick start
- [ ] Done when: repo is public on github.com/BIGGY00, CI is green, README has all 3 mode results
