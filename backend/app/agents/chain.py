"""Architecture & Linking — Master Prompt v7.0.0, section 3.

Executes the full pipeline exactly as specified:

    User Query → Language detection (orchestrator) → Jurisdiction routing
    → Formulation Classifier (only if product-specific)
    → parallel agents: TKDL Prior-Art + ABS Compliance + RAG retrieval
    → Answer Generator (grounded) → Citation Verification Pass
    → Confidence gate → Guardrails (abstain/escalate on low)
    → Multilingual translation → Output + Disclaimer

Linking rules enforced:
1. Orchestrator is the traffic police — every query starts here.
2. Classifier output flows into every downstream agent (via routing context).
3. RAG retrieval is jurisdiction-filtered (india toggle → India corpus only).
4. Citation verification runs after generation (hallucination defence).
5. Low confidence / guardrail REJECT → abstention + human escalation.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.abs_agent import ABSComplianceAgent
from app.agents.citation_checker import CitationChecker
from app.agents.classifier import FormulationClassifier
from app.agents.guardrails import GuardrailJudge
from app.agents.input_defenses import InputDefenses
from app.agents.multilingual import MultilingualLayer
from app.agents.orchestrator import Orchestrator
from app.agents.tkdl_agent import TKDLPriorArtAgent
from app.rag.pipeline import DISCLAIMER, RagPipeline

logger = logging.getLogger(__name__)

_CONFIDENCE_ORDER = ("LOW", "MEDIUM", "HIGH")


def _lowest_confidence(*values: str) -> str:
    ranks = [
        _CONFIDENCE_ORDER.index(v) if v in _CONFIDENCE_ORDER else 0
        for v in values
    ]
    return _CONFIDENCE_ORDER[min(ranks)]


class AgenticChain:
    """End-to-end agentic RAG execution over the 12-component graph."""

    def __init__(self) -> None:
        self.orchestrator = Orchestrator()
        self.classifier = FormulationClassifier()
        self.tkdl = TKDLPriorArtAgent()
        self.abs_agent = ABSComplianceAgent()
        self.rag = RagPipeline()
        self.citation_checker = CitationChecker()
        self.guardrails = GuardrailJudge()
        self.multilingual = MultilingualLayer()
        self.input_defenses = InputDefenses()

    def execute(
        self,
        query: str,
        jurisdiction: str = "india",
        top_k: int = 5,
        category: str | None = None,
        domains: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run the whole graph for one user query."""
        # 0. Input defenses (B1 PII redaction + B2 injection sanitation) —
        #    the sanitized query is the only text any later stage sees.
        defense = self.input_defenses.defend(query)
        query = str(defense["query"])

        # 1. Orchestrator — language, jurisdiction, query type, context.
        routing = self.orchestrator.route(query, jurisdiction=jurisdiction)
        ingredients = list((routing.get("context") or {}).get("ingredients") or [])

        # 2. Formulation classifier — only for product-specific questions.
        classification: dict[str, Any] | None = None
        if routing.get("needs_classifier"):
            classification = self.classifier.classify(query)
            if classification.get("category"):
                routing.setdefault("context", {})["product_category"] = (
                    classification["category"]
                )

        # 3a. TKDL prior-art — for product questions or any named ingredient.
        prior_art: dict[str, Any] | None = None
        if routing.get("query_type") == "PRODUCT_SPECIFIC" or ingredients:
            prior_art = self.tkdl.assess(
                ingredients=ingredients, description=query
            )

        # 3b. ABS compliance — for access & benefit-sharing questions.
        abs_path: dict[str, Any] | None = None
        if routing.get("query_type") == "ABS_QUESTION":
            abs_path = self.abs_agent.compliance_path(ingredients=ingredients)

        # 3c. RAG retrieval + grounded generation (jurisdiction-filtered).
        answer = self.rag.answer(
            query,
            jurisdiction=routing.get("jurisdiction") or jurisdiction,
            top_k=top_k,
            category=category,
            domains=domains,
        )

        # 4. Citation verification pass (hallucination defence).
        citations = self.citation_checker.verify(
            answer.get("text") or "", answer.get("sources") or []
        )
        confidence = _lowest_confidence(
            str(answer.get("confidence") or "LOW"),
            str(citations.get("confidence") or "LOW"),
        )

        # 5. Guardrails — abstain / escalate before anything reaches the user.
        verdict = self.guardrails.review(
            query=query,
            answer=answer.get("text") or "",
            sources=answer.get("sources") or [],
            jurisdiction=str(routing.get("jurisdiction") or jurisdiction),
            confidence=confidence,
        )

        status = "answered"
        escalation = False
        final_confidence = confidence
        if answer.get("refused"):
            status = "abstained"
            final_confidence = "LOW"
            escalation = True
            final_text = str(answer.get("text") or "")
        elif verdict.get("verdict") == "REJECT":
            status = "rejected"
            final_confidence = "LOW"
            escalation = verdict.get("suggested_action") == "escalate"
            safe_context = self._safe_context(answer.get("sources") or [])
            final_text = str(verdict.get("reject_message") or "")
            if safe_context:
                final_text = f"{final_text}\n\n{safe_context}"
        else:
            final_text = str(answer.get("text") or "")
            if DISCLAIMER not in final_text:
                final_text = f"{final_text}\n\n{DISCLAIMER}"

        # 6. Multilingual translation — never touches citations.
        translation = self.multilingual.translate(
            final_text, target_lang=str(routing.get("language") or "en")
        )
        if translation.get("translated"):
            final_text = str(translation["text"])

        return {
            "answer": final_text,
            "status": status,
            "confidence": final_confidence,
            "escalation_required": escalation,
            "routing": routing,
            "classification": classification,
            "prior_art": prior_art,
            "abs_path": abs_path,
            "citations": citations,
            "guardrails": verdict,
            "translation": translation,
            "sources": answer.get("sources") or [],
            "jurisdiction": routing.get("jurisdiction"),
            "retrieval_stats": answer.get("retrieval_stats"),
            "disclaimer": DISCLAIMER,
            "components": self.component_names(),
            "input_defense": defense,
        }

    @staticmethod
    def _safe_context(sources: list[dict[str, Any]]) -> str:
        titles = [
            str(s.get("title") or s.get("source") or "")
            for s in sources[:3]
        ]
        titles = [t for t in titles if t]
        if not titles:
            return ""
        return "Here is what I CAN tell you from safe, retrieved sources: " + "; ".join(
            titles
        ) + "."

    @staticmethod
    def component_names() -> list[str]:
        return [
            "orchestrator",
            "classifier",
            "jurisdiction_filter",
            "rag_pipeline",
            "tkdl_agent",
            "abs_agent",
            "citation_checker",
            "guardrails",
            "multilingual",
        ]
