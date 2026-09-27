"""Hybrid RAG — unified wrapper over the existing VEDALEX hybrid pipeline.

The underlying engine (``app.rag.retrieval_pipeline.HybridRetriever``) already
combines:
  1. Qdrant dense semantic search
  2. BM25 lexical search (rank_bm25, in-memory index)
  3. Statutory passage search
  4. Reciprocal Rank Fusion + authority tiebreak
  5. BGE cross-encoder reranking
  6. Hallucination guard + confidence scoring

This class exposes that pipeline through the BaseRAG contract so it can be
selected from ``/rag/search`` via ``rag_type="hybrid"`` without any rewrite.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.services.rag.base_rag import BaseRAG, RagResult, _elapsed_ns, register
from app.services.rag.config import get as cfg_get

logger = logging.getLogger(__name__)


@register
class HybridRAG(BaseRAG):
    rag_type = "hybrid"

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
        from app.rag.retrieval_pipeline import HybridRetriever

        start = time.perf_counter_ns()
        effective_filters = dict(filters or {})
        if jurisdiction and "jurisdiction" not in effective_filters:
            effective_filters["jurisdiction"] = jurisdiction
        if category and "category" not in effective_filters:
            effective_filters["category"] = category

        try:
            result = HybridRetriever.retrieve(
                query=query,
                top_k=top_k,
                filters=effective_filters or None,
                jurisdiction=jurisdiction,
                category=category,
                domains=domains,
            )
        except Exception as exc:
            logger.error("HybridRAG search failed: %s", exc)
            return RagResult(
                rag_type=self.rag_type,
                latency_ms=_elapsed_ns(start),
                meta={"error": str(exc)},
            )

        return RagResult(
            sources=result.get("sources", []),
            confidence=result.get("confidence", 0.05),
            grounding=result.get("grounding", {}),
            should_refuse=result.get("should_refuse", False),
            refusal_reason=result.get("refusal_reason", ""),
            retrieval_stats=result.get("retrieval_stats", {}),
            rag_type=self.rag_type,
            latency_ms=_elapsed_ns(start),
            meta={
                "architecture": "BM25 + Dense (Qdrant) + RRF + Cross-encoder rerank",
                "all_candidates": result.get("all_candidates", [])[:20],
            },
        )

    def status(self) -> dict[str, Any]:
        try:
            from app.rag.retrieval_pipeline import HybridRetriever

            pipeline_status = HybridRetriever.get_status()
        except Exception as exc:
            pipeline_status = {"error": str(exc)}
        return {
            "rag_type": self.rag_type,
            "available": True,
            "default": cfg_get("default") == self.rag_type,
            "pipeline": pipeline_status,
        }