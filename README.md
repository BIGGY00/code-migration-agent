# code-migration-agent

An LLM agent that migrates Python code from **Pydantic v1 to v2**: it finds v1 patterns, retrieves the matching section of the official migration guide (RAG), patches the code, runs the tests, and fixes its own failures. An eval harness measures pass rate, cost and latency against a rule-based baseline.

> Status: **step 1 of 5 done** — eval set + harness are in place. Agent, RAG and results are next (see `TASKS.md`).

## Why this exists

Version migrations are slow, file-by-file work. This project tests one claim with numbers: *a retrieval-grounded, test-driven agent loop migrates more code correctly than a single LLM call or a rule-based tool.*

## How it works (planned)

```
v1 code ──► find v1 patterns ──► retrieve guide sections ──► patch ──► run tests
                                         ▲                                │
                                         └────── failure output ◄─────────┘
                                              (max N rounds, then escalate)
```

## Eval set

`evals/cases/` holds 14 cases, each with:

| File | Purpose |
|---|---|
| `before.py` | Pydantic v1 code to migrate |
| `reference.py` | A correct v2 migration (proves the tests are achievable) |
| `test_case.py` | Behaviour tests, run under Pydantic v2 |
| `meta.json` | Patterns covered and difficulty |

Tests run with Pydantic deprecation warnings turned into errors, so code that only works through v1 compatibility shims counts as a failure.

Covered patterns: `.dict()`/`.json()`, `parse_obj`/`parse_raw`, `@validator` (incl. `pre`/`always`), `@root_validator`, class-based `Config` (`orm_mode`, `allow_population_by_field_name`, `Extra`, `allow_mutation`), implicit `Optional` defaults, `regex=`/`min_items=`, `__root__`, `parse_obj_as`, `.copy()`/`.schema()`, `GenericModel`, `update_forward_refs`.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[rag]"
python scripts/validate_cases.py      # every case: reference passes, before fails
pytest                                # harness tests
cp .env.example .env                  # set MIGRATE_AGENT_MODEL + API key
python scripts/smoke_llm.py           # one cheap LLM call
```

## Results

_Coming in step 4: pass rate, average fix rounds, cost per migration and latency for the agent vs. a single LLM call vs. `bump-pydantic`._

## License

MIT
