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

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Reranker:
    """Cross-encoder reranker with passthrough fallback."""

    _instance: Optional["Reranker"] = None
    _model = None
    _available = False
    _attempted = False
    _remote = False

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

        # Prefer the model sidecar: it keeps the cross-encoder out of this
        # process, so web replicas stay small enough to scale on request count.
        if self._probe_sidecar():
            self._available = True
            self._remote = True
            logger.info("Reranker served by model sidecar")
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

    @staticmethod
    def _model_server_url() -> str:
        return (os.environ.get("IPSAKTI_MODEL_SERVER_URL") or "").strip().rstrip("/")

    def _probe_sidecar(self) -> bool:
        if not self._model_server_url():
            return False
        try:
            import httpx

            resp = httpx.get(f"{self._model_server_url()}/health", timeout=3.0)
            return resp.status_code == 200 and bool(resp.json().get("reranker_loaded"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Reranker sidecar unreachable (%s); loading in-process", exc)
            return False

    def _rerank_sidecar(
        self, query: str, documents: list[str], top_k: int
    ) -> tuple[list[float], list[int]] | None:
        try:
            import httpx

            resp = httpx.post(
                f"{self._model_server_url()}/rerank",
                json={"query": query, "documents": documents, "top_k": top_k},
                timeout=120.0,
            )
            resp.raise_for_status()
            payload = resp.json()
            return payload["scores"], payload["order"]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Sidecar rerank failed (%s); using passthrough", exc)
            return None

    @classmethod
    def is_available(cls) -> bool:
        if cls._instance is None:
            cls()
        return cls._available

    def rerank(
        self,
        query: str,
        passages: list[dict[str, Any]],
        top_k: int = 5,
        content_key: str = "content",
    ) -> list[dict[str, Any]]:
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

        if not self._available:
            return self._passthrough_rerank(passages, top_k)

        try:
            pairs = [(query, p.get(content_key, "")[:512]) for p in passages]

            if self._remote:
                remote = self._rerank_sidecar(
                    query, [doc for _, doc in pairs], top_k
                )
                if remote is None:
                    return self._passthrough_rerank(passages, top_k)
                scores, order = remote
            else:
                if self._model is None:
                    return self._passthrough_rerank(passages, top_k)
                predicted = self._model.predict(pairs, show_progress_bar=False)
                scores = [float(s) for s in predicted]
                order = sorted(
                    range(len(scores)), key=lambda i: scores[i], reverse=True
                )[:top_k]

            scored_passages = [
                {
                    **passages[i],
                    "rerank_score": float(scores[i]),
                    "original_rank": i,
                }
                for i in order
            ]
            return scored_passages[:top_k]

        except Exception as e:
            logger.warning(f"Reranking failed: {e} — falling back to original order")
            return self._passthrough_rerank(passages, top_k)

    def _passthrough_rerank(
        self, passages: list[dict[str, Any]], top_k: int
    ) -> list[dict[str, Any]]:
        """When reranker is unavailable, preserve original ranking but add score field."""
        result = []
        for i, p in enumerate(passages[:top_k]):
            result.append({
                **p,
                "rerank_score": p.get("score", 1.0 / (i + 1)),
                "original_rank": i,
            })
        return result
