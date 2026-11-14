"""Fast checks on guide chunking, BM25 retrieval and case labels (no network)."""

from migrate_agent.harness import load_cases
from migrate_agent.retrieval import BM25Retriever, chunk_markdown, guide_headings, load_chunks, tokenize

SAMPLE = """---
description: front matter is skipped
---

Intro text.

## Top

Top body.

```python
# V1  <- a comment inside code, not a heading
x = 1
```

### Child

Child body.

## Empty parent

### Only child

Leaf body.
"""


def test_chunker_ignores_headings_inside_code_and_keeps_paths():
    chunks = chunk_markdown(SAMPLE)
    assert [c.title for c in chunks] == [
        "Introduction",
        "Top",
        "Top > Child",
        "Empty parent > Only child",
    ]
    top = chunks[1]
    assert "# V1" in top.text and "description" not in chunks[0].text


def test_chunk_ids_are_unique():
    ids = [c.id for c in load_chunks()]
    assert len(ids) == len(set(ids))


def test_tokenize_keeps_identifiers_and_parts():
    toks = tokenize("parse_obj_as(GenericModel, self.__root__)")
    assert {"parse_obj_as", "parse", "obj", "genericmodel", "generic", "model", "root"} <= set(toks)
    assert "self" not in toks and "as" not in toks


def test_every_case_has_labels_that_are_real_guide_headings():
    headings = guide_headings()
    for case in load_cases():
        assert case.guide_sections, f"{case.id} has no guide_sections"
        for section in case.guide_sections:
            assert section in headings, f"{case.id}: {section!r} is not a heading in the guide"


def test_bm25_finds_obvious_section():
    hits = BM25Retriever().search("orm_mode allow_population_by_field_name class Config", k=3)
    assert "Changes to config" in [h.chunk.heading for h in hits]
