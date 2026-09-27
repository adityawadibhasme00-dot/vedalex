"""Auto mode: deterministic query-to-architecture selector for unified search.

Pure rules, no LLM, no network — fully testable offline:

1. **Entity lookup** (short lookup-style query: <= 6 words, <= 60 chars,
   no ``?``, no question words) -> ``graph`` (knowledge-graph entity fusion).
2. **Multi-aspect question** (markers like ``compare``, ``vs``, ``and``,
   ``step by step``) -> ``agentic`` (parallel specialised agents).
3. **Otherwise** -> the configured default architecture (``hybrid`` if the
   default itself is ``auto`` or invalid — never recurses).
"""

from __future__ import annotations

from app.services.rag.config import RAG_TYPES

AUTO = "auto"

_QUESTION_WORDS = frozenset(
    {
        "what",
        "why",
        "how",
        "when",
        "where",
        "who",
        "which",
        "is",
        "are",
        "can",
        "could",
        "should",
        "do",
        "does",
        "explain",
        "list",
    }
)

_MULTI_INTENT_MARKERS = (
    " compare ",
    " vs ",
    " versus ",
    " and ",
    " also ",
    " both ",
    " difference ",
    " step by step ",
    " end to end ",
)


def select_rag_type(query: str, default: str = "hybrid") -> dict[str, str]:
    """Route ``query`` to one of :data:`RAG_TYPES`.

    Returns ``{"rag_type": ..., "reason": ...}`` where ``reason`` explains
    the routing decision (surfaced in the response ``meta`` for transparency).
    """
    text = (query or "").strip()
    lowered = f" {text.lower()} "
    words = text.lower().split()

    is_entity_lookup = (
        len(text) <= 60
        and len(words) <= 6
        and "?" not in text
        and not any(word in words for word in _QUESTION_WORDS)
    )
    if is_entity_lookup:
        return {"rag_type": "graph", "reason": "short entity lookup"}

    if any(marker in lowered for marker in _MULTI_INTENT_MARKERS):
        return {"rag_type": "agentic", "reason": "multi-aspect question"}

    resolved = default if default in RAG_TYPES else "hybrid"
    return {"rag_type": resolved, "reason": "configured default"}
