"""Component 7 — Citation & Confidence Module, Master Prompt v7.0.0.

Post-generation verification pass: every ``[Source: ...]`` citation in the
answer is checked against the retrieved context (delegating the detailed
per-citation analysis to the existing ``citation_validity_checker``), then an
overall HIGH / MEDIUM / LOW confidence is derived from source support.

Output: ``{verified, confidence, total_citations, valid_citations,
unverified, checks, note}``.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentBase
from app.rag.citation_validity_checker import check_citation_validity

_NO_CITATIONS_NOTE = (
    "The answer contains no explicit citations; confidence is limited to the "
    "breadth of the retrieved sources."
)


class CitationChecker(AgentBase):
    """Component 7: verify every citation exists in retrieved context."""

    name = "citation_checker"
    prompt_file = ""  # rule-based module — no LLM prompt per master prompt

    def verify(self, answer: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
        """Verify citations in ``answer`` against ``sources``."""
        report = check_citation_validity(answer or "", sources or [])
        checks = []
        unverified: list[str] = []
        for c in report.checks:
            checks.append(
                {
                    "citation": c.citation_text,
                    "valid": c.valid,
                    "document_found": c.document_found,
                    "section_found": c.section_found,
                    "source_matched": c.source_matched,
                    "note": c.note,
                }
            )
            if not c.valid:
                unverified.append(c.citation_text)

        total = report.total_citations
        valid = report.valid_citations
        if total == 0:
            confidence = "MEDIUM"
            note = _NO_CITATIONS_NOTE
        elif valid == total:
            confidence = "HIGH"
            note = "Every citation resolves to the retrieved context."
        elif valid > 0:
            confidence = "MEDIUM"
            note = "Some citations could not be verified against the context."
        else:
            confidence = "LOW"
            note = "No citation could be verified against the retrieved context."

        return {
            "verified": total > 0 and valid == total,
            "confidence": confidence,
            "total_citations": total,
            "valid_citations": valid,
            "invalid_citations": report.invalid_citations,
            "validity_ratio": report.validity_ratio,
            "unverified": unverified,
            "checks": checks,
            "note": note,
        }
