"""Retrieval over the official Pydantic V2 migration guide.

The guide (``data/migration_guide.md``) is split into one chunk per markdown
heading. Each chunk keeps its full heading path as its title, e.g.
``Migration guide > Changes to validators > `@validator` and `@root_validator` are deprecated``,
so the agent can cite exactly where an instruction came from.

Two retrievers share one interface, ``search(query, k) -> list[Hit]``:

* ``BM25Retriever`` (default): keyword search with ``rank-bm25``. No API cost.
* ``EmbeddingRetriever`` (opt-in): cosine similarity over ``litellm`` embeddings,
  cached on disk under ``data/index/`` so the guide is embedded once per model.

Queries are usually raw Python source, so the tokenizer is code-aware: it keeps
whole identifiers (``parse_obj_as``) and also their parts (``parse``, ``obj``).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE_PATH = ROOT / "data" / "migration_guide.md"
INDEX_DIR = ROOT / "data" / "index"

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CAMEL = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")

# English filler plus Python syntax that appears in every code sample.
STOPWORDS = frozenset(
    """
    a an and are as at be by can do does for from has have if in into is it its
    no not of on or so than that the then there these this to was we were will
    with you your use used using
    def class return import self cls pass else elif lambda true false
    """.split()
)


@dataclass(frozen=True)
class Chunk:
    id: str  # stable, e.g. "c12-changes-to-config"
    heading: str  # the chunk's own heading text, exactly as in the guide
    title: str  # full heading path joined with " > "
    text: str  # section body (without the heading line)


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float


# --------------------------------------------------------------------------- #
# Loading and chunking
# --------------------------------------------------------------------------- #


def guide_sha256(path: Path = GUIDE_PATH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]


def _strip_front_matter(lines: list[str]) -> list[str]:
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[i + 1 :]
    return lines


def chunk_markdown(markdown: str) -> list[Chunk]:
    """Split markdown into one chunk per heading.

    Lines that look like headings inside fenced code blocks (``# V1`` comments
    in Python examples) are treated as text. Sections with no body text (a
    heading followed directly by a sub-heading) produce no chunk; their heading
    still appears in the children's titles.
    """
    lines = _strip_front_matter(markdown.splitlines())
    sections: list[tuple[list[str], list[str]]] = []  # (heading path, body lines)
    path: list[tuple[int, str]] = []
    body: list[str] = []
    in_fence = False

    def flush() -> None:
        if any(line.strip() for line in body):
            heading_path = [h for _, h in path] or ["Introduction"]
            sections.append((heading_path, body.copy()))

    for line in lines:
        if _FENCE.match(line):
            in_fence = not in_fence
        m = None if in_fence else _HEADING.match(line)
        if m is None:
            body.append(line)
            continue
        flush()
        body = []
        level = len(m.group(1))
        while path and path[-1][0] >= level:
            path.pop()
        path.append((level, m.group(2)))
    flush()

    return [
        Chunk(
            id=f"c{i:02d}-{_slug(heading_path[-1])}",
            heading=heading_path[-1],
            title=" > ".join(heading_path),
            text="\n".join(body_lines).strip(),
        )
        for i, (heading_path, body_lines) in enumerate(sections)
    ]


def load_chunks(path: Path = GUIDE_PATH) -> list[Chunk]:
    return chunk_markdown(path.read_text(encoding="utf-8"))


def guide_headings(path: Path = GUIDE_PATH) -> set[str]:
    """Every heading text in the guide (outside code blocks), for label checks."""
    headings, in_fence = set(), False
    for line in _strip_front_matter(path.read_text(encoding="utf-8").splitlines()):
        if _FENCE.match(line):
            in_fence = not in_fence
        elif not in_fence and (m := _HEADING.match(line)):
            headings.add(m.group(2))
    return headings


# --------------------------------------------------------------------------- #
# BM25
# --------------------------------------------------------------------------- #


def tokenize(text: str) -> list[str]:
    """Code-aware tokens: whole identifiers plus their snake/camel-case parts."""
    tokens: list[str] = []
    for ident in _IDENT.findall(text):
        whole = ident.strip("_").lower()
        parts = [p.lower() for piece in ident.split("_") for p in _CAMEL.findall(piece)]
        for tok in [whole, *parts] if len(parts) > 1 else [whole]:
            if len(tok) > 1 and not tok.isdigit() and tok not in STOPWORDS:
                tokens.append(tok)
    return tokens


def _query_tokens(query: str) -> list[str]:
    # Each distinct term counts once, so a field name repeated ten times in
    # the source does not drown out a single ``orm_mode = True``.
    return list(dict.fromkeys(tokenize(query)))


class BM25Retriever:
    name = "bm25"

    def __init__(self, chunks: list[Chunk] | None = None):
        from rank_bm25 import BM25Okapi

        self.chunks = chunks if chunks is not None else load_chunks()
        self._bm25 = BM25Okapi([tokenize(f"{c.title}\n{c.text}") for c in self.chunks])

    def search(self, query: str, k: int = 3) -> list[Hit]:
        scores = self._bm25.get_scores(_query_tokens(query))
        order = sorted(range(len(self.chunks)), key=lambda i: scores[i], reverse=True)
        return [Hit(self.chunks[i], float(scores[i])) for i in order[:k]]


# --------------------------------------------------------------------------- #
# Embeddings (opt-in, costs API calls)
# --------------------------------------------------------------------------- #


class EmbeddingRetriever:
    """Cosine similarity over LiteLLM embeddings. Off by default.

    The chunk vectors are cached in ``data/index/`` keyed by model id and guide
    hash, so re-running only pays for embedding the queries.
    """

    name = "embedding"

    def __init__(self, chunks: list[Chunk] | None = None, model: str | None = None):
        import numpy as np

        from migrate_agent import llm

        self._np = np
        self._llm = llm
        self.model = model or llm.default_embed_model()
        self.chunks = chunks if chunks is not None else load_chunks()
        self.cost_usd = 0.0
        self._matrix = self._load_or_build_index()

    def _cache_path(self) -> Path:
        key = hashlib.sha256(
            (self.model + "\n" + "\n".join(f"{c.id}:{c.title}\n{c.text}" for c in self.chunks)).encode()
        ).hexdigest()[:16]
        return INDEX_DIR / f"{_slug(self.model)}-{key}.json"

    def _normalize(self, vectors):
        m = self._np.asarray(vectors, dtype=float)
        return m / self._np.linalg.norm(m, axis=1, keepdims=True)

    def _load_or_build_index(self):
        path = self._cache_path()
        if path.exists():
            data = json.loads(path.read_text())
            return self._normalize(data["vectors"])
        res = self._llm.embed([f"{c.title}\n\n{c.text}" for c in self.chunks], model=self.model)
        self.cost_usd += res.cost_usd
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"model": self.model, "ids": [c.id for c in self.chunks], "vectors": res.vectors}))
        return self._normalize(res.vectors)

    def search(self, query: str, k: int = 3) -> list[Hit]:
        res = self._llm.embed([query], model=self.model)
        self.cost_usd += res.cost_usd
        scores = self._matrix @ self._normalize(res.vectors)[0]
        order = self._np.argsort(-scores)[:k]
        return [Hit(self.chunks[i], float(scores[i])) for i in order]


def make_retriever(kind: str = "bm25", **kwargs) -> BM25Retriever | EmbeddingRetriever:
    if kind == "bm25":
        return BM25Retriever(**kwargs)
    if kind == "embedding":
        return EmbeddingRetriever(**kwargs)
    raise ValueError(f"unknown retriever {kind!r} (use 'bm25' or 'embedding')")


def multi_search(retriever, queries: list[str], k: int = 3, depth: int = 5) -> list[Hit]:
    """Search several queries and merge the results round-robin.

    BM25 scores from different queries are not comparable, so instead of
    sorting by score we take each query's best chunk first, then each query's
    second best, and so on, skipping duplicates. A file with three different v1
    patterns therefore gets one relevant section per pattern before any
    pattern gets two.
    """
    if not queries:
        return []
    ranked = [retriever.search(q, k=depth) for q in queries]
    out: list[Hit] = []
    seen: set[str] = set()
    for rank in range(depth):
        for hits in ranked:
            if rank < len(hits) and hits[rank].chunk.id not in seen:
                seen.add(hits[rank].chunk.id)
                out.append(hits[rank])
                if len(out) == k:
                    return out
    return out
