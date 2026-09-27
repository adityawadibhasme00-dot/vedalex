"""Component 2 — Formulation Classifier Agent, Master Prompt v7.0.0.

Classifies a user's Ayurvedic product into one of six regulatory categories
with a rule-based pre-classifier (deterministic, offline) and optional LLM
refinement through ``app/prompts/classifier_prompt.txt``.

Never issues a definitive legal opinion — every basis line is framed as
"based on your description", per the prompt contract.
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.base import AgentBase, AgentContext

CLASSICAL_MEDICINE = "CLASSICAL_MEDICINE"
PROPRIETARY_MEDICINE = "PROPRIETARY_MEDICINE"
NEW_DRUG = "NEW_DRUG"
PHYTOPHARMACEUTICAL = "PHYTOPHARMACEUTICAL"
AYURVEDA_AAHR = "AYURVEDA_AAHR"
COSMETIC = "COSMETIC"

CATEGORIES = (
    CLASSICAL_MEDICINE,
    PROPRIETARY_MEDICINE,
    NEW_DRUG,
    PHYTOPHARMACEUTICAL,
    AYURVEDA_AAHR,
    COSMETIC,
)

_IP_POSTURE = {
    CLASSICAL_MEDICINE: (
        "Based on your description: Section 3(p) patent bar likely; TKDL prior "
        "art applies; GI/trademark route recommended; no ABS needed if "
        "cultivated from notified cultivars."
    ),
    PROPRIETARY_MEDICINE: (
        "Based on your description: patent possible if an inventive step exists; "
        "ABS approval from the NBA likely."
    ),
    NEW_DRUG: (
        "Based on your description: strongest patent potential; clinical "
        "evidence required; ABS mandatory."
    ),
    PHYTOPHARMACEUTICAL: (
        "Based on your description: patent on the extraction process possible; "
        "drug regulatory route applies."
    ),
    AYURVEDA_AAHR: (
        "Based on your description: FSSAI regime; trademark & trade dress "
        "protection; no drug claims allowed."
    ),
    COSMETIC: (
        "Based on your description: DCA cosmetic rules; trademark/design "
        "protection."
    ),
}

_ABS_POSTURE = {
    CLASSICAL_MEDICINE: (
        "Based on your description: no ABS approval expected for cultivated "
        "notified-cultivar ingredients; verify wild collection."
    ),
    PROPRIETARY_MEDICINE: (
        "Based on your description: ABS approval from the NBA likely before "
        "commercialisation."
    ),
    NEW_DRUG: (
        "Based on your description: ABS approval mandatory for use of "
        "biological resources."
    ),
    PHYTOPHARMACEUTICAL: (
        "Based on your description: ABS approval applies to the source "
        "biological resource."
    ),
    AYURVEDA_AAHR: (
        "Based on your description: check cultivation status; ABS may apply to "
        "wild-collected ingredients."
    ),
    COSMETIC: (
        "Based on your description: ABS applies only if biological resources "
        "are used in the formulation."
    ),
}

_CLARIFYING_QUESTIONS = [
    "Is the formulation taken verbatim from a classical text? Which one?",
    "Have you changed the composition, ratio, or preparation method?",
    "What is the intended use: treatment, health supplement, or cosmetic?",
    "Do you claim a new indication or dosage?",
    "Is any ingredient a purified/standardised plant extract?",
]

_COSMETIC_RE = re.compile(
    r"\b(cosmetic|cream|lotion|soap|face pack|external use|skin care|moisturi[sz]er)\b",
    re.IGNORECASE,
)
_AAHAR_RE = re.compile(
    r"\b(aahar|aahara|nutraceutical|fssai|dietary (supplement|food)|"
    r"health (drink|supplement)|food supplement|edible)\b",
    re.IGNORECASE,
)
_PHYTO_RE = re.compile(
    r"\b(purified extract|standardi[sz]ed extract|marker compound|"
    r"phytopharmaceutical|extract of|fraction of)\b",
    re.IGNORECASE,
)
_NEW_DRUG_RE = re.compile(
    r"\b(new indication|novel indication|new molecule|non-classical|"
    r"first-in-class|new therapeutic)\b",
    re.IGNORECASE,
)
_MODIFICATION_RE = re.compile(
    r"\b(modified|changed|our own|proprietary composition|reformulat|"
    r"enhanced ratio|new ratio|novel composition|different ratio)\b",
    re.IGNORECASE,
)
_CLASSICAL_RE = re.compile(
    r"\b(charaka|sushruta|susruta|sharangadhara|bhaishajya ratnavali|"
    r"ayurvedic formulary|first schedule|classical (text|formula|formulation)|"
    r"as per the formulary)\b",
    re.IGNORECASE,
)


class FormulationClassifier(AgentBase):
    """Component 2: 6-category regulatory classification with clarifying Qs."""

    name = "classifier"
    prompt_file = "classifier_prompt.txt"

    def classify(
        self,
        query: str,
        context: AgentContext | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Classify the formulation described in ``query`` (+ optional detail).

        Returns ``{category, basis, ip_posture_summary, abs_posture_summary,
        clarifying_questions, next_question, needs_clarification}``.
        """
        text = " ".join(p for p in (query, description) if p).strip()
        category = self._rule_category(text)
        if category is None:
            questions = list(_CLARIFYING_QUESTIONS)
            result = {
                "category": None,
                "basis": (
                    "Based on your description: not enough information yet to "
                    "assign one of the six categories."
                ),
                "ip_posture_summary": "Pending classification.",
                "abs_posture_summary": "Pending classification.",
                "clarifying_questions": questions,
                "next_question": questions[0],
                "needs_clarification": True,
            }
        else:
            questions = self._residual_questions(text, category)
            result = {
                "category": category,
                "basis": (
                    "Based on your description: rule-based signals → "
                    f"{category.replace('_', ' ').title()}."
                ),
                "ip_posture_summary": _IP_POSTURE[category],
                "abs_posture_summary": _ABS_POSTURE[category],
                "clarifying_questions": questions,
                "next_question": questions[0] if questions else None,
                "needs_clarification": False,
            }
        if context is not None and category is not None:
            context.product_category = category
        return self.llm_json(
            f"Query:\n{text}\n\nRule-based classification:\n{result}",
            fallback=result,
        )

    # -- rule pre-classifier ------------------------------------------------

    @staticmethod
    def _rule_category(text: str) -> str | None:
        if _COSMETIC_RE.search(text):
            return COSMETIC
        if _AAHAR_RE.search(text):
            return AYURVEDA_AAHR
        if _PHYTO_RE.search(text):
            return PHYTOPHARMACEUTICAL
        if _NEW_DRUG_RE.search(text):
            return NEW_DRUG
        if _MODIFICATION_RE.search(text):
            return PROPRIETARY_MEDICINE
        if _CLASSICAL_RE.search(text):
            return CLASSICAL_MEDICINE
        return None

    @staticmethod
    def _residual_questions(text: str, category: str) -> list[str]:
        """Confirmatory questions that still matter after a rule hit."""
        lowered = text.lower()
        out: list[str] = []
        if category == CLASSICAL_MEDICINE and not re.search(
            r"charaka|sushruta|sharangadhara|formulary", lowered
        ):
            out.append(_CLARIFYING_QUESTIONS[0])
        if category in (CLASSICAL_MEDICINE, PROPRIETARY_MEDICINE):
            out.append(_CLARIFYING_QUESTIONS[1])
        if category == NEW_DRUG:
            out.append(_CLARIFYING_QUESTIONS[3])
        if category == PHYTOPHARMACEUTICAL:
            out.append(_CLARIFYING_QUESTIONS[4])
        if category == COSMETIC:
            out.append(_CLARIFYING_QUESTIONS[2])
        if category == AYURVEDA_AAHR:
            out.append(_CLARIFYING_QUESTIONS[2])
        return out[:5]
