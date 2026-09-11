"""
BGE Reranker module for VEDALEX RAG pipeline.

Reranking is critical for patent/legal RAG because:
  1. Initial retrieval (semantic + BM25) returns candidates by rough relevance
  2. Reranker re-scores each (query, passage) pair with cross-attention
  3. This catches cases where keyword overlap is low but semantic match is high
  4. Patent claims require exact legal phrasing — rerankers understand this

Uses BAAI/bge-reranker-v2-m3 by default (multilingual, cross-encoder).
Falls back to a score-preserving passthrough if model is unavailable.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class Reranker:
    """Cross-encoder reranker with passthrough fallback."""

    _instance: Optional["Reranker"] = None
    _model = None
    _available = False
    _attempted = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._attempted:
            return
        self._attempted = True
        self._try_load()

    def _try_load(self):
        if os.environ.get("IPSAKTI_USE_RERANKER", "1").lower() == "0":
            logger.info("Reranker disabled via IPSAKTI_USE_RERANKER=0")
            return

        try:
            from sentence_transformers import CrossEncoder
            model_name = os.environ.get(
                "IPSAKTI_RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"
            )
            logger.info(f"Loading reranker model: {model_name}")
            self._model = CrossEncoder(
                model_name,
                max_length=512,
                device="cpu",
            )
            self._available = True
            logger.info("Reranker model loaded successfully")
        except Exception as e:
            logger.warning(f"Reranker load failed: {e} — using score-passthrough")
            self._available = False
            self._attempted = True

    @classmethod
    def is_available(cls) -> bool:
        if cls._instance is None:
            cls()
        return cls._available

    def rerank(
        self,
        query: str,
        passages: List[Dict[str, Any]],
        top_k: int = 5,
        content_key: str = "content",
    ) -> List[Dict[str, Any]]:
        """
        Rerank passages by cross-encoder relevance to query.

        Args:
            query: User query
            passages: List of passage dicts with content_key field
            top_k: Number of top passages to return
            content_key: Dict key containing passage text

        Returns:
            Reranked list with added 'rerank_score' field
        """
        if not passages:
            return []

        if not self._available or self._model is None:
            return self._passthrough_rerank(passages, top_k)

        try:
            pairs = [(query, p.get(content_key, "")[:512]) for p in passages]
            scores = self._model.predict(pairs, show_progress_bar=False)

            scored_passages = []
            for i, (passage, score) in enumerate(zip(passages, scores)):
                scored_passages.append({
                    **passage,
                    "rerank_score": float(score),
                    "original_rank": i,
                })

            scored_passages.sort(key=lambda x: x["rerank_score"], reverse=True)
            return scored_passages[:top_k]

        except Exception as e:
            logger.warning(f"Reranking failed: {e} — falling back to original order")
            return self._passthrough_rerank(passages, top_k)

    def _passthrough_rerank(
        self, passages: List[Dict[str, Any]], top_k: int
    ) -> List[Dict[str, Any]]:
        """When reranker is unavailable, preserve original ranking but add score field."""
        result = []
        for i, p in enumerate(passages[:top_k]):
            result.append({
                **p,
                "rerank_score": p.get("score", 1.0 / (i + 1)),
                "original_rank": i,
            })
        return result
