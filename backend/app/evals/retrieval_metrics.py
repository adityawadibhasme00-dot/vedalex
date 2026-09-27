"""
Retrieval-quality metrics for the hybrid RAG pipeline (master prompt §evaluation).

Measures, over fixed benchmark questions:
  - Recall@5, Recall@10
  - Precision@5, Precision@10
  - Mean Reciprocal Rank (MRR)
  - Citation accuracy  — fraction of top-k sources carrying full provenance
                         (source_url + authority), the "can you back it up?" gate
  - Source hit rate    — whether the expected authority's corpus appears in top-k

Qrels are substring/identity matches against retrieved content because doc_ids
change as the corpus is re-ingested; expected_source ties each question to its
authoritative issuer.
"""

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

BENCHMARK_FILE = os.path.join(os.path.dirname(__file__), "retrieval_benchmarks.json")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "exports", "retrieval_eval_report.json")


def load_benchmarks() -> list[dict[str, Any]]:
    with open(BENCHMARK_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def _qrel_match(doc: dict[str, Any], qrels: dict[str, Any]) -> bool:
    content = (doc.get("content") or "").lower()
    for sub in qrels.get("relevant_substrings", []):
        if sub.lower() in content:
            return True
    doc_id = doc.get("doc_id", "")
    for rel_id in qrels.get("relevant_ids", []):
        if rel_id in doc_id or doc_id in rel_id:
            return True
    expected = qrels.get("expected_source", "")
    if expected:
        hay = " ".join([
            doc.get("source", ""), doc.get("authority", ""),
            doc.get("title", ""), doc.get("jurisdiction", ""),
        ]).lower()
        if expected.lower() in hay:
            return True
    return False


def _citation_accuracy(sources: list[dict[str, Any]]) -> float:
    if not sources:
        return 0.0
    complete = sum(
        1 for s in sources
        if s.get("source_url") and s.get("authority")
    )
    return round(complete / len(sources), 4)


def evaluate_one(query: str, qrels: dict[str, Any], top_k: int = 10) -> dict[str, Any]:
    from app.rag.retrieval_pipeline import HybridRetriever

    result = HybridRetriever.retrieve(query, top_k=top_k)
    sources = result.get("sources", [])

    relevant_ranks: list[int] = []
    for i, doc in enumerate(sources, start=1):
        if _qrel_match(doc, qrels):
            relevant_ranks.append(i)

    relevant_count = max(1, len(qrels.get("relevant_substrings", [])) or 1)
    recall5 = len([r for r in relevant_ranks if r <= 5]) / relevant_count
    recall10 = len([r for r in relevant_ranks if r <= 10]) / relevant_count
    precision5 = len([r for r in relevant_ranks if r <= 5]) / 5
    precision10 = len([r for r in relevant_ranks if r <= 10]) / 10
    mrr = (1.0 / relevant_ranks[0]) if relevant_ranks else 0.0
    source_hit = any(_qrel_match(doc, qrels) for doc in sources)
    expected = qrels.get("expected_source", "")
    expected_hit = bool(expected) and any(
        expected.lower() in " ".join([
            d.get("source", ""), d.get("authority", ""),
        ]).lower()
        for d in sources
    )

    return {
        "question": query,
        "language": qrels.get("language", "en"),
        "expected_source": expected,
        "retrieved_count": len(sources),
        "relevant_ranks": relevant_ranks,
        "recall@5": round(recall5, 4),
        "recall@10": round(recall10, 4),
        "precision@5": round(precision5, 4),
        "precision@10": round(precision10, 4),
        "mrr": round(mrr, 4),
        "source_hit": source_hit,
        "expected_source_hit": expected_hit,
        "citation_accuracy": _citation_accuracy(sources[:5]),
        "confidence": result.get("confidence"),
        "grounding_coverage": (result.get("grounding") or {}).get("coverage_ratio"),
        "should_refuse": result.get("should_refuse"),
        "retrieval_stats": result.get("retrieval_stats"),
    }


def run_evaluation(limit: int | None = None) -> dict[str, Any]:
    """Evaluate the pipeline over the benchmark set and persist a JSON report."""
    questions = load_benchmarks()
    if limit:
        questions = questions[:limit]

    per_query: list[dict[str, Any]] = []
    for q in questions:
        t0 = time.time()
        try:
            row = evaluate_one(q["query"], q)
            row["elapsed_s"] = round(time.time() - t0, 2)
            per_query.append(row)
        except Exception as exc:
            logger.exception("Retrieval eval failed for %r", q.get("query"))
            per_query.append({
                "question": q["query"],
                "error": str(exc)[:200],
                "elapsed_s": round(time.time() - t0, 2),
            })

    valid = [r for r in per_query if "error" not in r]
    n = len(valid)

    def avg(key: str) -> float:
        return round(sum(r.get(key, 0) for r in valid) / n, 4) if n else 0.0

    aggregate: dict[str, Any] = {
        "total_queries": len(per_query),
        "completed": n,
        "failed": len(per_query) - n,
        "avg_recall@5": avg("recall@5"),
        "avg_recall@10": avg("recall@10"),
        "avg_precision@5": avg("precision@5"),
        "avg_precision@10": avg("precision@10"),
        "avg_mrr": avg("mrr"),
        "avg_citation_accuracy": avg("citation_accuracy"),
        "source_hit_rate": avg("source_hit"),
        "expected_source_hit_rate": avg("expected_source_hit"),
    }
    aggregate["gates"] = {
        "mrr_gate": aggregate["avg_mrr"] >= 0.6,
        "recall5_gate": aggregate["avg_recall@5"] >= 0.6,
        "citation_accuracy_gate": aggregate["avg_citation_accuracy"] >= 0.8,
    }
    aggregate["gates_pass"] = all(aggregate["gates"].values())

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "framework": "Retrieval-quality benchmarks (Recall/Precision/MRR/Citation accuracy)",
        "aggregate": aggregate,
        "per_query": per_query,
    }

    try:
        os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
        with open(REPORT_PATH, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning("Could not persist retrieval eval report: %s", exc)

    return report


if __name__ == "__main__":
    print(json.dumps(run_evaluation(), indent=2, ensure_ascii=False))