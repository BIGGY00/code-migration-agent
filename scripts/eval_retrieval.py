"""Measure how well retrieval finds the right migration-guide section per case.

For each eval case the query is the raw ``before.py`` source (no hand-written
hints), which is what the agent sees. A case's expected sections are the
``guide_sections`` in its ``meta.json`` (real headings from the guide).

    recall@k = expected sections found in the top-k chunks / expected sections

Reported per case and as the mean over cases. ``hit@k`` is the share of cases
where *every* expected section was in the top k.

Usage:
    python scripts/eval_retrieval.py                 # BM25, no API cost
    python scripts/eval_retrieval.py --embeddings    # needs MIGRATE_AGENT_EMBED_MODEL, costs API calls
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from migrate_agent.harness import load_cases  # noqa: E402
from migrate_agent.retrieval import GUIDE_PATH, guide_sha256, load_chunks, make_retriever  # noqa: E402

KS = (1, 3, 5)


def recall(expected: list[str], headings: list[str]) -> float:
    return sum(s in headings for s in expected) / len(expected)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--k", type=int, default=3, help="headline k for recall@k (default 3)")
    ap.add_argument("--embeddings", action="store_true", help="use embedding retrieval instead of BM25")
    ap.add_argument("--embed-model", default=None, help="LiteLLM embedding model id (default: $MIGRATE_AGENT_EMBED_MODEL)")
    ap.add_argument("--out", type=Path, default=None, help="output JSON path")
    args = ap.parse_args()

    kind = "embedding" if args.embeddings else "bm25"
    out = args.out or ROOT / "results" / ("retrieval.json" if kind == "bm25" else "retrieval_embedding.json")
    chunks = load_chunks()
    kwargs = {"chunks": chunks}
    if kind == "embedding" and args.embed_model:
        kwargs["model"] = args.embed_model
    retriever = make_retriever(kind, **kwargs)

    ks = sorted({*KS, args.k})
    depth = max(ks)
    rows = []
    for case in load_cases():
        if not case.guide_sections:
            print(f"error: {case.id} has no guide_sections in meta.json", file=sys.stderr)
            return 1
        hits = retriever.search(case.before.read_text(), k=depth)
        headings = [h.chunk.heading for h in hits]
        top = headings[: args.k]
        rows.append(
            {
                "id": case.id,
                "difficulty": case.difficulty,
                "expected": case.guide_sections,
                "retrieved": [
                    {"rank": i + 1, "id": h.chunk.id, "title": h.chunk.title, "score": round(h.score, 4)}
                    for i, h in enumerate(hits)
                ],
                "recall": {f"@{k}": recall(case.guide_sections, headings[:k]) for k in ks},
                "found": [s for s in case.guide_sections if s in top],
                "missed": [s for s in case.guide_sections if s not in top],
            }
        )

    n = len(rows)
    summary = {
        f"@{k}": {
            "mean_recall": round(sum(r["recall"][f"@{k}"] for r in rows) / n, 4),
            "hit_rate": round(sum(r["recall"][f"@{k}"] == 1.0 for r in rows) / n, 4),
        }
        for k in ks
    }
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "retriever": kind,
        "model": getattr(retriever, "model", None),
        "cost_usd": round(getattr(retriever, "cost_usd", 0.0), 6),
        "query": "raw before.py source",
        "guide": {"path": str(GUIDE_PATH.relative_to(ROOT)), "sha256": guide_sha256(), "chunks": len(chunks)},
        "headline_k": args.k,
        "n_cases": n,
        "summary": summary,
        "cases": rows,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")

    k = args.k
    print(f"retriever={kind} | {len(chunks)} chunks | {n} cases | query = raw before.py\n")
    print(f"{'case':30} {'diff':7} {f'R@{k}':>5}  top-{k} headings (✓ = expected)")
    for r in rows:
        marks = [
            ("✓ " if h["title"].split(" > ")[-1] in r["expected"] else "  ") + h["title"].split(" > ")[-1]
            for h in r["retrieved"][:k]
        ]
        print(f"{r['id']:30} {r['difficulty']:7} {r['recall'][f'@{k}']:5.2f}  {' | '.join(marks)}")
        for m in r["missed"]:
            print(f"{'':45}missed: {m}")
    print()
    for kk in ks:
        s = summary[f"@{kk}"]
        print(f"recall@{kk}: {s['mean_recall']:.3f}   hit@{kk}: {s['hit_rate']:.3f}")
    print(f"\nsaved {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
