"""Auto mode: route every query to the single combined RAG engine.

The four architectures (hybrid / production / graph / agentic) are now fused
into one engine (``combined``). "Auto" therefore always resolves to the
combined engine so the user gets the union of evidence from every architecture
in a single response — there is no per-query engine choice any more.
"""

from __future__ import annotations

AUTO = "auto"


def select_rag_type(query: str, default: str = "combined") -> dict[str, str]:
    """Return the combined engine for every query.

    Preserves the call signature used by ``/rag/search`` and keeps ``auto`` a
    valid request value while the underlying routing decision is now trivial.
    """
    del query  # engine selection is unified; query no longer picks an engine
    return {"rag_type": "combined", "reason": "all RAG engines combined into one"}
