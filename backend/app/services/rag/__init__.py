"""IP-SAKTI RAG service layer — Hybrid / Production / Graph / Agentic.

Public API:
    get_rag(rag_type, config=None) -> BaseRAG      # lazily-created singleton
    available_types() -> list[str]
    RAG_TYPES / config helpers (get, update, snapshot, reset_runtime)

The services wrap the existing production pipeline (``app.rag.retrieval_pipeline``)
and existing local knowledge graph; nothing in the legacy pipeline is rewritten.
"""

import app.services.rag.agentic_rag as _agentic  # noqa: F401
import app.services.rag.graph_rag as _graph  # noqa: F401
import app.services.rag.hybrid_rag as _hybrid  # noqa: F401  (register side-effect)
import app.services.rag.production_rag as _production  # noqa: F401
from app.services.rag.base_rag import BaseRAG, RagResult, available_types, get_rag, register
from app.services.rag.config import RAG_TYPES, get, reset_runtime, snapshot, update

__all__ = [
    "BaseRAG",
    "RagResult",
    "get_rag",
    "available_types",
    "register",
    "RAG_TYPES",
    "get",
    "snapshot",
    "update",
    "reset_runtime",
]