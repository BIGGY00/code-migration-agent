# code-migration-agent

An LLM agent that migrates Python code from **Pydantic v1 to v2**: it finds v1 patterns, retrieves the matching section of the official migration guide (RAG), patches the code, runs the tests, and fixes its own failures. An eval harness measures pass rate, cost and latency against a rule-based baseline.

> Status: **step 2 of 5 done** — eval set, harness and retrieval are in place. The agent loop and end-to-end results are next (see `TASKS.md`).

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

## Retrieval

The agent grounds each fix in the official [Pydantic V2 migration guide](https://github.com/pydantic/pydantic/blob/91c44cd1bfc8c7cb909cefa8395e0a720957f1d1/docs/migration.md), pinned to one commit (`data/SOURCE.md` has the URL, commit, date and MIT license).

- **Chunking:** one chunk per markdown heading (35 chunks). Each chunk keeps its heading path as its title, e.g. `Migration guide > Changes to config`, so the agent can cite where an instruction came from. Lines like `# V1` inside code examples are not treated as headings.
- **Search:** BM25 (`rank-bm25`), no API cost. The tokenizer is code-aware: `parse_obj_as` is indexed as the whole identifier and as `parse`, `obj`. Embedding search (via LiteLLM) exists behind `--embeddings` but is off by default and has not been evaluated yet.
- **Labels:** each case's `meta.json` lists `guide_sections`, the exact guide headings that explain how to fix that case. A unit test fails if a label is not a real heading.
- **Query:** the raw `before.py` file, with no hand-written hints, because that is what the agent receives.

`python scripts/eval_retrieval.py` → `results/retrieval.json` (BM25, run 2026-11-14):

| Metric | @1 | @3 | @5 |
|---|---|---|---|
| Mean recall (expected sections found in top k) | 0.536 | **0.929** | 1.000 |
| Cases with every expected section in top k | 7/14 | 13/14 | 14/14 |

The one miss at k=3 is `01_dict_json`: it only calls `.dict()` and `.json()`, words that appear all over the guide, so BM25 ranks "Changes to `pydantic.BaseModel`" 5th behind the long "Removed in Pydantic V2" list. Recall@1 is low because the best section is often not ranked first. Both point to querying per detected v1 pattern instead of with the whole file, which is planned for the agent's static scan in step 3.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[rag]"
python scripts/validate_cases.py      # every case: reference passes, before fails
python scripts/eval_retrieval.py      # retrieval recall@k (BM25, no API cost)
pytest                                # harness tests
cp .env.example .env                  # set MIGRATE_AGENT_MODEL + API key
python scripts/smoke_llm.py           # one cheap LLM call
```

## Results

_Coming in step 4: pass rate, average fix rounds, cost per migration and latency for the agent vs. a single LLM call vs. `bump-pydantic`._

## License

MIT
