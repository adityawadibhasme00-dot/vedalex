"""Component 4 — RAG Pipeline, Master Prompt v7.0.0.

Jurisdiction-filtered hybrid retrieval + grounded answer generation built
ON TOP of the existing ``HybridRetriever`` (BM25 + dense + rerank) — it does
not rebuild any of it.

Contract:
- ``india`` / ``international`` → one-sided retrieval; sources are never
  mixed with the other jurisdiction's corpus.
- ``both`` → two independent retrievals, answers emitted as separate
  sections (the two sides are never merged into one blended answer).
- Zero usable sources → deterministic abstention (no fabrication).
- Generation uses ``app/prompts/rag_prompt.txt`` through the existing
  llm_adapter providers; offline (provider ``off``) it falls back to a
  deterministic grounded answer built strictly from retrieved sources.
- Post-generation citation verification: every ``[Source: ...]`` tag is
  checked against the retrieved context; confidence is derived from that.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import date
from typing import Any

from app.agents.base import AgentBase
from app.rag import llm_adapter
from app.rag.retrieval_pipeline import HybridRetriever

logger = logging.getLogger(__name__)

_CITATION_RE = re.compile(r"\[Source:\s*([^\]]+)\]")

_JURISDICTION_CANON = {
    "india": "India",
    "in": "India",
    "international": "International",
    "global": "International",
}

DISCLAIMER = "This is general information, not legal advice."
ABSTAIN_MESSAGE = (
    "I don't have sufficient authoritative sources for this. "
    "Please consult a human IP facilitator."
)


def canonical_jurisdiction(value: str | None) -> str:
    """Normalise user/toggle input to ``India`` / ``International`` / ``both``."""
    norm = (value or "india").strip().lower()
    if norm in ("both", "all", "any"):
        return "both"
    return _JURISDICTION_CANON.get(norm, "India")


class RagPipeline(AgentBase):
    """Component 4: retrieval + grounded generation + citation verification."""

    name = "rag_pipeline"
    prompt_file = "rag_prompt.txt"

    # -- retrieval ---------------------------------------------------------

    def retrieve(
        self,
        query: str,
        jurisdiction: str | None = "india",
        top_k: int = 5,
        category: str | None = None,
        domains: list[str] | None = None,
    ) -> dict[str, Any]:
        """Jurisdiction-filtered hybrid retrieval.

        Returns ``{jurisdiction, sources, sides, retrieval_stats, ...}``.
        For ``both`` the per-side results stay separated in ``sides`` while
        ``sources`` carries jurisdiction-tagged entries for inspection only.
        """
        side = canonical_jurisdiction(jurisdiction)
        if side == "both":
            india = self._retrieve_side(query, "India", top_k, category, domains)
            international = self._retrieve_side(
                query, "International", top_k, category, domains
            )
            merged: list[dict[str, Any]] = []
            for key, res in (("india", india), ("international", international)):
                for src in res.get("sources", []):
                    tagged = dict(src)
                    # The side being retrieved is the source of truth for the tag.
                    tagged["jurisdiction"] = (
                        "India" if key == "india" else "International"
                    )
                    merged.append(tagged)
            return {
                "jurisdiction": "both",
                "sources": merged,
                "sides": {"india": india, "international": international},
                "retrieval_stats": {
                    "india": india.get("retrieval_stats"),
                    "international": international.get("retrieval_stats"),
                },
            }
        single = self._retrieve_side(query, side, top_k, category, domains)
        return {
            "jurisdiction": side,
            "sources": single.get("sources", []),
            "sides": {side.lower(): single},
            "retrieval_stats": single.get("retrieval_stats"),
        }

    def _retrieve_side(
        self,
        query: str,
        jurisdiction: str,
        top_k: int,
        category: str | None,
        domains: list[str] | None,
    ) -> dict[str, Any]:
        try:
            return HybridRetriever.retrieve(
                query,
                top_k=top_k,
                jurisdiction=jurisdiction,
                category=category,
                domains=domains,
            )
        except Exception as exc:  # noqa: BLE001 — retrieval must never 500
            logger.warning("RAG retrieval failed (%s): %s", jurisdiction, exc)
            return {"sources": [], "should_refuse": True, "refusal_reason": str(exc)}

    # -- generation --------------------------------------------------------

    def answer(
        self,
        query: str,
        jurisdiction: str | None = "india",
        top_k: int = 5,
        category: str | None = None,
        domains: list[str] | None = None,
    ) -> dict[str, Any]:
        """Full RAG pass: retrieve → generate → verify citations → confidence."""
        retrieval = self.retrieve(query, jurisdiction, top_k, category, domains)
        sides: dict[str, dict[str, Any]] = retrieval.get("sides") or {}

        total_sources = sum(len(r.get("sources", [])) for r in sides.values())
        refused = all(r.get("should_refuse") for r in sides.values()) and sides
        if total_sources == 0:
            reason = ""
            if sides:
                reason = "; ".join(
                    str(r.get("refusal_reason") or "") for r in sides.values()
                )
            return self._abstain(retrieval, reason)

        sections: list[dict[str, Any]] = []
        for side_name, res in sides.items():
            sources = res.get("sources", [])
            if not sources:
                continue
            text, generated, provider = self._generate(query, sources, side_name)
            citations = _CITATION_RE.findall(text)
            verified = [c for c in citations if self._citation_in_sources(c, sources)]
            sections.append(
                {
                    "jurisdiction": side_name,
                    "text": text,
                    "citations": citations,
                    "verified_citations": verified,
                    "generated": generated,
                    "provider": provider,
                }
            )

        if not sections:
            return self._abstain(retrieval, "no usable sources after filtering")

        confidence = self._confidence(
            sections, sum(len(r.get("sources", [])) for r in sides.values())
        )
        combined_text = "\n\n".join(
            (
                f"### {s['jurisdiction'].title()}\n{s['text']}"
                if len(sections) > 1
                else s["text"]
            )
            for s in sections
        )
        all_citations = [c for s in sections for c in s["citations"]]
        all_verified = [c for s in sections for c in s["verified_citations"]]

        return {
            "text": combined_text,
            "confidence": confidence,
            "citations": all_citations,
            "verification": {
                "verified": len(all_verified),
                "unverified": [c for c in all_citations if c not in all_verified],
            },
            "sections": sections,
            "sources": retrieval.get("sources", []),
            "jurisdiction": retrieval.get("jurisdiction"),
            "retrieval_stats": retrieval.get("retrieval_stats"),
            "generated": any(s["generated"] for s in sections),
            "provider": sections[0]["provider"],
            "refused": bool(refused),
            "disclaimer": DISCLAIMER,
        }

    # -- internals ---------------------------------------------------------

    def _generate(
        self, query: str, sources: list[dict[str, Any]], jurisdiction: str
    ) -> tuple[str, bool, str]:
        """LLM generation via llm_adapter providers; deterministic offline."""
        provider = llm_adapter._resolve_provider()
        if provider not in ("gemini", "openai"):
            return self._deterministic_answer(sources, jurisdiction), False, provider
        model = llm_adapter._pick_model(provider)
        key_env = "GEMINI_API_KEY" if provider == "gemini" else "OPENAI_API_KEY"
        api_key = os.environ.get(key_env, "").strip()
        if model is None or not api_key:
            return self._deterministic_answer(sources, jurisdiction), False, provider
        try:
            user_prompt = (
                f"Jurisdiction: {jurisdiction}\n"
                f"Current date: {date.today().isoformat()}\n"
                f"User query: {query}\n\n"
                "Retrieved context:\n"
                + "\n".join(
                    f"- [{s.get('title') or s.get('source') or 'source'}] "
                    f"{str(s.get('content') or s.get('snippet') or '')[:600]}"
                    for s in sources[:8]
                )
            )
            if provider == "gemini":
                result = llm_adapter._call_gemini(
                    self.system_prompt, user_prompt, api_key, model
                )
            else:
                result = llm_adapter._call_openai(
                    self.system_prompt, user_prompt, api_key, model
                )
        except Exception as exc:  # noqa: BLE001 — provider failures are expected
            logger.warning("RAG generation failed (%s): %s", provider, exc)
            return self._deterministic_answer(sources, jurisdiction), False, provider
        text = str(result.get("text") or "").strip()
        if not result.get("generated") or not text:
            return self._deterministic_answer(sources, jurisdiction), False, provider
        if DISCLAIMER not in text:
            text = f"{text}\n\n{DISCLAIMER}"
        return text, True, provider

    @staticmethod
    def _deterministic_answer(sources: list[dict[str, Any]], jurisdiction: str) -> str:
        """Offline grounded answer — only what the retrieved sources contain."""
        lines = [
            f"Direct answer (from retrieved {jurisdiction} sources):",
        ]
        for i, src in enumerate(sources[:4], 1):
            title = (
                src.get("title")
                or src.get("act_title")
                or src.get("source")
                or f"Source {i}"
            )
            content = " ".join(str(src.get("content") or src.get("snippet") or "").split())
            snippet = content[:260] + ("…" if len(content) > 260 else "")
            if snippet:
                lines.append(f"{i}. {snippet} [Source: {title}]")
        if len(lines) == 1:
            lines.append("No extractable content in the retrieved sources.")
        lines.append(
            "Note: summaries above are extracted verbatim from the retrieved "
            "sources; consult a human IP facilitator for interpretation."
        )
        lines.append("")
        lines.append(f"Confidence: {'HIGH' if len(sources) >= 3 else 'MEDIUM'}")
        lines.append("")
        lines.append(DISCLAIMER)
        return "\n".join(lines)

    @staticmethod
    def _citation_in_sources(citation: str, sources: list[dict[str, Any]]) -> bool:
        """True when the citation's source name appears in retrieved context."""
        head = citation.split(",")[0].strip()
        if len(head) < 4:
            return False
        needle = head.casefold()
        for src in sources:
            haystack = " ".join(
                str(src.get(k) or "")
                for k in ("title", "act_title", "source", "content", "snippet", "document")
            ).casefold()
            if needle in haystack:
                return True
        return False

    @staticmethod
    def _confidence(sections: list[dict[str, Any]], total_sources: int) -> str:
        citations = sum(len(s["citations"]) for s in sections)
        verified = sum(len(s["verified_citations"]) for s in sections)
        if citations == 0:
            return "HIGH" if total_sources >= 3 else "MEDIUM"
        if verified == citations:
            return "HIGH"
        if verified > 0:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _abstain(retrieval: dict[str, Any], reason: str) -> dict[str, Any]:
        return {
            "text": ABSTAIN_MESSAGE,
            "confidence": "LOW",
            "citations": [],
            "verification": {"verified": 0, "unverified": []},
            "sections": [],
            "sources": retrieval.get("sources", []),
            "jurisdiction": retrieval.get("jurisdiction"),
            "retrieval_stats": retrieval.get("retrieval_stats"),
            "generated": False,
            "provider": "abstain",
            "refused": True,
            "reason": reason,
            "disclaimer": DISCLAIMER,
        }
