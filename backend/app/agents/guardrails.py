"""Component 8 — Guardrails / Abstention Module, Master Prompt v7.0.0.

Reviews a generated answer BEFORE it reaches the user. Deterministic checks
(source-grounding, scope, medical advice, jurisdiction mixing, uncertainty)
run first and are STICKY (an LLM can add a rejection, never remove one);
the ``guardrails_prompt.txt`` judge is consulted only when a live provider
is configured and the deterministic pass approved.

Output: ``{verdict: APPROVE|REJECT, reason, suggested_action:
answer|abstain|escalate, failed_checks, reject_message}``.
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.base import AgentBase
from app.agents.input_defenses import find_injections
from app.agents.orchestrator import _OUT_OF_SCOPE_PATTERNS
from app.rag.pipeline import _CITATION_RE, DISCLAIMER, RagPipeline

_MEDICAL_PATTERNS = (
    r"\b\d+\s?mg\b",
    r"\bdosage\b(?! form)",
    r"\bdose\b(?! form)",
    r"\bprescribe",
    r"\btreat(ing)? my\b",
    r"\bhow (much|many) (to )?take\b",
)

REJECT_MESSAGE = (
    "I cannot answer this confidently from authoritative sources. "
    "This question is best directed to a human IP facilitator "
    "[contact path]. Meanwhile, here is what I CAN tell you: "
    "[any safe, well-sourced general context]."
)


class GuardrailJudge(AgentBase):
    """Component 8: APPROVE/REJECT judge over generated answers."""

    name = "guardrails"
    prompt_file = "guardrails_prompt.txt"

    def review(
        self,
        query: str,
        answer: str,
        sources: list[dict[str, Any]] | None = None,
        jurisdiction: str = "india",
        confidence: str | None = None,
    ) -> dict[str, Any]:
        """Run all five checks; returns the master-prompt verdict JSON."""
        sources = sources or []
        failed: list[dict[str, str]] = []

        # 1. SOURCE-GROUNDED — every citation must exist in retrieved context.
        citations = _CITATION_RE.findall(answer or "")
        unverified = [
            c for c in citations
            if not RagPipeline._citation_in_sources(c, sources)
        ]
        if unverified:
            failed.append(
                {
                    "check": "source_grounded",
                    "reason": (
                        "Citation(s) not found in retrieved context: "
                        + "; ".join(unverified[:3])
                    ),
                    "suggested_action": "abstain",
                }
            )

        # 2. SCOPE — personal legal advice / court strategy → escalate.
        lowered_query = (query or "").lower()
        for pattern in _OUT_OF_SCOPE_PATTERNS:
            if re.search(pattern, lowered_query):
                failed.append(
                    {
                        "check": "scope",
                        "reason": (
                            "Query asks for personal legal/strategic advice: "
                            f"pattern {pattern!r}"
                        ),
                        "suggested_action": "escalate",
                    }
                )
                break

        # 3. MEDICAL — dosage/treatment advice is never allowed.
        combined = f"{lowered_query} {(answer or '').lower()}"
        for pattern in _MEDICAL_PATTERNS:
            if re.search(pattern, combined):
                failed.append(
                    {
                        "check": "medical",
                        "reason": f"Medical dosage/treatment content: {pattern!r}",
                        "suggested_action": "escalate",
                    }
                )
                break

        # 4. JURISDICTION MIXING — India answers must not rely on international
        #    corpus sources (and vice versa); `both` keeps sides separate.
        norm_jur = (jurisdiction or "india").strip().lower()
        if norm_jur in ("india", "international"):
            expected = "India" if norm_jur == "india" else "International"
            for src in sources:
                src_jur = str(src.get("jurisdiction") or "")
                if not src_jur or src_jur == expected:
                    continue
                title = str(src.get("title") or src.get("source") or "")
                if title and title.lower() in (answer or "").lower():
                    failed.append(
                        {
                            "check": "jurisdiction_mixing",
                            "reason": (
                                f"Answer cites {src_jur} source {title!r} for a "
                                f"{expected} answer"
                            ),
                            "suggested_action": "abstain",
                        }
                    )
                    break

        # 5. UNCERTAINTY — insufficient retrieval or low confidence.
        if not sources or (confidence or "").upper() == "LOW":
            failed.append(
                {
                    "check": "uncertainty",
                    "reason": (
                        "No retrieved sources" if not sources
                        else f"Confidence is LOW ({confidence})"
                    ),
                    "suggested_action": "abstain",
                }
            )

        # 6. CONTEXT-INJECTION (rule R7) — retrieved context is DATA, not
        #    instructions; a chunk carrying jailbreak text forces abstention.
        for src in sources:
            body = " ".join(
                str(src.get(key) or "")
                for key in ("text", "snippet", "content", "title", "source")
            )
            hits = find_injections(body)
            if hits:
                failed.append(
                    {
                        "check": "context_injection",
                        "reason": (
                            "Retrieved context contains instruction-like text "
                            f"(rule R7): {', '.join(hits[:3])}"
                        ),
                        "suggested_action": "abstain",
                    }
                )
                break

        verdict = "REJECT" if failed else "APPROVE"
        action = failed[0]["suggested_action"] if failed else "answer"
        reason = (
            "; ".join(f["reason"] for f in failed)
            if failed
            else "All guardrail checks passed."
        )
        result = {
            "verdict": verdict,
            "reason": reason,
            "suggested_action": action,
            "failed_checks": [f["check"] for f in failed],
            "reject_message": REJECT_MESSAGE if verdict == "REJECT" else None,
            "disclaimer": DISCLAIMER,
        }
        if verdict == "REJECT":
            # Sticky: deterministic REJECT never goes back to APPROVE.
            return result

        # Optional LLM judge when a live provider is configured.
        refined = self.llm_json(
            "Review this answer:\n"
            f"Query: {query}\nAnswer: {answer}\n"
            f"Confidence: {confidence}\nDeterministic verdict: APPROVE",
            fallback=result,
        )
        if str(refined.get("verdict", "")).upper() == "REJECT":
            return {
                "verdict": "REJECT",
                "reason": str(refined.get("reason") or "LLM judge rejected."),
                "suggested_action": str(
                    refined.get("suggested_action") or "abstain"
                ),
                "failed_checks": ["llm_judge"],
                "reject_message": REJECT_MESSAGE,
                "disclaimer": DISCLAIMER,
            }
        return result
