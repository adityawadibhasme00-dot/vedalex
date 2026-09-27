"""Base RAG interface + result contract for IP-SAKTI Sahayak.

All four RAG architectures (Hybrid, Production, Graph, Agentic) implement a
single unified interface so the API layer and the frontend can treat them
interchangeably. Backward compatibility is preserved: the existing
``/rag/ask`` endpoint is untouched and the new ``/rag/search`` endpoint is the
only surface that switches on ``rag_type``.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RagResult:
    """Normalised output of every RAG search.

    Mirrors the envelope already returned by ``HybridRetriever.retrieve`` and
    adds a ``rag_type`` marker plus per-search ``meta`` for metrics.
    """

    sources: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.05
    grounding: dict[str, Any] = field(default_factory=dict)
    should_refuse: bool = False
    refusal_reason: str = ""
    retrieval_stats: dict[str, Any] = field(default_factory=dict)
    rag_type: str = "hybrid"
    latency_ms: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sources": self.sources,
            "confidence": self.confidence,
            "grounding": self.grounding,
            "should_refuse": self.should_refuse,
            "refusal_reason": self.refusal_reason,
            "retrieval_stats": self.retrieval_stats,
            "rag_type": self.rag_type,
            "latency_ms": round(self.latency_ms, 2),
            "meta": self.meta,
        }


class BaseRAG(ABC):
    """Unified interface for every RAG architecture."""

    rag_type: str = "base"

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    @abstractmethod
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
        """Run a search and return a normalised :class:`RagResult`.

        ``domains`` restricts retrieval to the given Qdrant collections
        (e.g. ``["regulations", "patents"]``); ``None`` searches all of them.
        """

    def status(self) -> dict[str, Any]:
        """Health/configuration summary for this architecture."""
        return {
            "rag_type": self.rag_type,
            "available": True,
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_registry: dict[str, type] = {}
_instances: dict[str, BaseRAG] = {}
_registry_lock = __import__("threading").Lock()


def register(cls: type) -> type:
    if not hasattr(cls, "rag_type") or not cls.rag_type:
        raise ValueError(f"{cls.__name__} must define rag_type")
    _registry[cls.rag_type] = cls
    return cls


def get_rag(rag_type: str, config: dict[str, Any] | None = None) -> BaseRAG:
    """Return a lazily-created singleton for a RAG architecture."""
    from app.services.rag.config import RAG_TYPES

    if rag_type not in RAG_TYPES or rag_type not in _registry:
        raise ValueError(f"Invalid rag_type '{rag_type}'. Choose from {RAG_TYPES}")
    cls = _registry[rag_type]
    with _registry_lock:
        if rag_type not in _instances:
            _instances[rag_type] = cls(config)
        return _instances[rag_type]


def available_types() -> list[str]:
    return list(_registry.keys())


def _elapsed_ns(start_ns: int) -> float:
    return (time.perf_counter_ns() - start_ns) / 1_000_000.0