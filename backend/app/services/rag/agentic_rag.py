"""Agentic RAG — specialised agents, intent routing, parallel execution.

Routes a query to a set of domain-specialised agents (Patent, Regulatory,
TKDL), runs the matching agents in parallel, then merges their ranked results
with de-duplication. When no agent claims the query it falls back to the plain
hybrid pipeline so recall is never lost.

Agent selection reuses the deterministic domain-intent classifier
(``app.services.intent_classifier``) so behaviour is unit-testable without an
LLM or embedding call.
"""

from __future__ import annotations

import concurrent.futures
import logging
import time
from collections.abc import Callable
from typing import Any

from app.services.rag.base_rag import BaseRAG, RagResult, _elapsed_ns, register
from app.services.rag.config import get as cfg_get
from app.services.rag.hybrid_rag import HybridRAG

logger = logging.getLogger(__name__)


class Agent:
    """A specialised executor that declares what queries it can handle."""

    def __init__(self, name: str, can_handle: Callable[[str], bool], execute: Callable[[str], list[dict[str, Any]]]):
        self.name = name
        self.can_handle = can_handle
        self.execute = execute


@register
class AgenticRAG(BaseRAG):
    rag_type = "agentic"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.hybrid = HybridRAG(config)

        self.agents: list[Agent] = [
            Agent(
                name="patent_agent",
                can_handle=lambda q: self._intent_any(q, {"patent"}),
                execute=lambda q: self.hybrid.search(
                    q, domains=["patents", "traditional_knowledge"], top_k=8, user_key="agent:patent"
                ).sources,
            ),
            Agent(
                name="regulatory_agent",
                can_handle=lambda q: self._intent_any(
                    q, {"regulatory", "fssai", "trademark", "export"}
                ),
                execute=lambda q: self.hybrid.search(
                    q, domains=["regulations"], top_k=8, user_key="agent:regulatory"
                ).sources,
            ),
            Agent(
                name="abs_agent",
                can_handle=lambda q: self._intent_any(q, {"abs"}),
                execute=lambda q: self.hybrid.search(
                    q, domains=["biodiversity", "regulations"], top_k=8, user_key="agent:abs"
                ).sources,
            ),
            Agent(
                name="tkdl_agent",
                can_handle=lambda q: self._intent_any(q, {"patent"})
                and self._keyword_any(q, ["tkdl", "traditional knowledge", "classical", "charaka", "sushruta", "prior art"]),
                execute=lambda q: [
                    {**s, "agent": "tkdl"}
                    for s in self.hybrid.search(
                        q, domains=["traditional_knowledge"], top_k=8, user_key="agent:tkdl"
                    ).sources
                ],
            ),
        ]

    @staticmethod
    def _intent_any(query: str, intents: set) -> bool:
        try:
            from app.services.intent_classifier import classify_domain_intent

            return classify_domain_intent(query).get("id") in intents
        except Exception:
            return False

    @staticmethod
    def _keyword_any(query: str, keywords: list[str]) -> bool:
        low = (query or "").lower()
        return any(k in low for k in keywords)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

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

        relevant = [a for a in self.agents if a.can_handle(query)]
        if not relevant:
            result = self.hybrid.search(query, filters, jurisdiction, category, top_k, user_key, domains)
            result.rag_type = self.rag_type
            result.meta = {"architecture": "Agentic (fallback → hybrid)", "agents_used": []}
            result.latency_ms = _elapsed_ns(start)
            return result

        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(relevant))) as pool:
            futures = {pool.submit(a.execute, query): a.name for a in relevant}
            per_agent: list[list[dict[str, Any]]] = []
            completed: list[str] = []
            for fut in concurrent.futures.as_completed(futures):
                name = futures[fut]
                completed.append(name)
                try:
                    per_agent.append(fut.result() or [])
                except Exception as exc:
                    logger.warning("Agent %s failed: %s", name, exc)
                    per_agent.append([])

        merged = self._merge_and_rank(per_agent)

        # If none of the specialised collections are warm on this deployment,
        # fall back to an unrestricted hybrid search so the user still gets
        # the best available evidence instead of an empty result set.
        fallback_used = False
        if not merged:
            fallback = self.hybrid.search(query, filters, jurisdiction, category, top_k, user_key)
            merged = fallback.sources
            fallback_used = True

        result = RagResult(
            sources=merged[:top_k],
            confidence=0.0,
            rag_type=self.rag_type,
            latency_ms=_elapsed_ns(start),
            meta={
                "architecture": "Agentic (parallel specialised agents)",
                "agents_used": [a.name for a in relevant],
                "agents_completed": completed,
                "agent_results_per_agent": [len(r) for r in per_agent],
                "fallback_used": fallback_used,
            },
        )
        return result

    def _merge_and_rank(self, lists: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        seen: set = set()
        merged: list[dict[str, Any]] = []

        def _key(doc: dict[str, Any]) -> str:
            doc_id = doc.get("document_id") or doc.get("doc_id") or doc.get("id") or ""
            source = doc.get("source") or ""
            content = (doc.get("content") or "")[:80]
            return f"{doc_id}|{source}|{content}"

        for group in lists:
            for doc in group:
                k = _key(doc)
                if k in seen:
                    continue
                seen.add(k)
                if "agent" in doc:
                    doc["source_type"] = f"{doc.get('source_type') or 'hybrid'}|agent:{doc['agent']}"
                merged.append(doc)

        def _score(doc: dict[str, Any]) -> float:
            rerank = float(doc.get("rerank_score", doc.get("score", 0.0)) or 0.0)
            boost = 0.0
            if isinstance(doc.get("source_type"), str) and "patent" in doc["source_type"]:
                boost = 0.02
            return rerank + boost

        merged.sort(key=_score, reverse=True)
        return merged

    def status(self) -> dict[str, Any]:
        return {
            "rag_type": self.rag_type,
            "available": True,
            "default": cfg_get("default") == self.rag_type,
            "agents": [a.name for a in self.agents],
            "hybrid": self.hybrid.status(),
        }