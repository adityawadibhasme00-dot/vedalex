"""Combined RAG — one unified engine that fuses every RAG architecture.

Runs Production (Hybrid + cache + rate-limit), Graph (knowledge-graph fusion)
and Agentic (parallel specialised agents) in parallel, then merges their ranked
result sets with Reciprocal Rank Fusion (RRF) and de-duplication into a SINGLE
combined output. ``rag_type="combined"`` is the only surface the frontend uses,
so a user always gets the union of evidence from every engine in one response.
"""

from __future__ import annotations

import concurrent.futures
import logging
import time
from collections import defaultdict
from typing import Any

from app.services.rag.agentic_rag import AgenticRAG
from app.services.rag.base_rag import BaseRAG, RagResult, _elapsed_ns, register
from app.services.rag.config import get as cfg_get
from app.services.rag.graph_rag import GraphRAG
from app.services.rag.production_rag import ProductionRAG

logger = logging.getLogger(__name__)

_RRF_K = 60.0
_ENGINE_NAMES = ("production", "graph", "agentic")


def _doc_key(doc: dict[str, Any]) -> str:
    doc_id = doc.get("document_id") or doc.get("doc_id") or doc.get("id") or ""
    source = doc.get("source") or ""
    title = doc.get("title") or ""
    content = (doc.get("content") or "")[:90]
    return f"{doc_id}|{source}|{title}|{content}"


@register
class CombinedRAG(BaseRAG):
    rag_type = "combined"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.production = ProductionRAG(config)
        self.graph = GraphRAG(config)
        self.agentic = AgenticRAG(config)
        self._engines = {
            "production": self.production,
            "graph": self.graph,
            "agentic": self.agentic,
        }

    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        jurisdiction: str | None = None,
        category: str | None = None,
        top_k: int = 10,
        user_key: str = "anonymous",
        domains: list[str] | None = None,
    ) -> RagResult:
        start = time.perf_counter_ns()

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(self._engines), thread_name_prefix="rag-combined"
        ) as pool:
            futures = {
                pool.submit(
                    engine.search,
                    query=query,
                    filters=filters,
                    jurisdiction=jurisdiction,
                    category=category,
                    top_k=top_k,
                    user_key=user_key,
                    domains=domains,
                ): name
                for name, engine in self._engines.items()
            }
            results: dict[str, RagResult] = {}
            failed: list[str] = []
            for future in concurrent.futures.as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result()
                except Exception as exc:
                    logger.warning("combined engine %r failed: %s", name, exc)
                    failed.append(name)
                    results[name] = RagResult(rag_type=name)

        merged = self._rff_merge([(name, results[name]) for name in _ENGINE_NAMES])

        active = [name for name in _ENGINE_NAMES if results[name].sources]
        confidence = self._blend_confidence([results[name] for name in active])

        grounding: dict[str, Any] = {}
        for name in _ENGINE_NAMES:
            g = results[name].grounding
            if g:
                grounding = {**g, "engines_agreement": len(active)}
                break
        if not grounding and active:
            grounding = {"engines_agreement": len(active)}

        should_refuse = bool(active) and all(results[name].should_refuse for name in active)
        refusal_reason = ""
        if should_refuse:
            refusal_reason = next(
                (results[name].refusal_reason for name in active if results[name].refusal_reason),
                "No verified evidence retrieved across any RAG engine.",
            )

        retrieval_stats: dict[str, Any] = {}
        for name in _ENGINE_NAMES:
            stats = results[name].retrieval_stats or {}
            for key, value in stats.items():
                if key.endswith("_time_ms") or key == "total_time_ms":
                    retrieval_stats[f"{name}_{key}"] = value
        retrieval_stats["merged_count"] = len(merged)
        retrieval_stats["engines_failed"] = failed

        per_engine = {
            name: {
                "sources": len(results[name].sources),
                "confidence": results[name].confidence,
            }
            for name in _ENGINE_NAMES
        }

        result = RagResult(
            sources=merged[:top_k],
            confidence=confidence,
            grounding=grounding,
            should_refuse=should_refuse,
            refusal_reason=refusal_reason,
            retrieval_stats=retrieval_stats,
            rag_type=self.rag_type,
            latency_ms=_elapsed_ns(start),
            meta={
                "architecture": "Combined: Production + Graph + Agentic (RRF fusion)",
                "engines_used": [name for name in active],
                "engines_failed": failed,
                "per_engine": per_engine,
                "per_engine_sources": sum(per_engine[n]["sources"] for n in _ENGINE_NAMES),
                "cache_hit": bool(
                    results.get("production")
                    and results["production"].meta.get("cache_hit")
                ),
            },
        )
        return result

    def _rff_merge(self, ranked: list[tuple[str, RagResult]]) -> list[dict[str, Any]]:
        rrf: dict[str, float] = defaultdict(float)
        first_doc: dict[str, dict[str, Any]] = {}
        engines_by_doc: dict[str, list[str]] = defaultdict(list)

        for name, result in ranked:
            for rank, doc in enumerate(result.sources, start=1):
                key = _doc_key(doc)
                rrf[key] += 1.0 / (_RRF_K + rank)
                if key not in first_doc:
                    first_doc[key] = doc
                if name not in engines_by_doc[key]:
                    engines_by_doc[key].append(name)

        ordered = sorted(rrf.items(), key=lambda kv: kv[1], reverse=True)
        merged: list[dict[str, Any]] = []
        for key, score in ordered:
            doc = first_doc[key]
            merged.append(
                {
                    **doc,
                    "combined_score": round(score, 6),
                    "engines_hit": engines_by_doc[key],
                    "source_type": f"{doc.get('source_type') or 'hybrid'}|combined",
                }
            )
        return merged

    def _blend_confidence(self, results: list[RagResult]) -> float:
        if not results:
            return 0.05
        best = max((r.confidence or 0.05) for r in results)
        agreement = min(1.0, len(results) / len(_ENGINE_NAMES))
        return round(best * (0.5 + 0.5 * agreement) + 0.05 * agreement, 4)

    def status(self) -> dict[str, Any]:
        return {
            "rag_type": self.rag_type,
            "available": True,
            "default": cfg_get("default") == self.rag_type,
            "engines": [name for name in _ENGINE_NAMES],
            "per_engine": {name: self._engines[name].status() for name in _ENGINE_NAMES},
        }