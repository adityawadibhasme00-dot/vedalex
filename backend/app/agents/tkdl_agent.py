"""Component 5 — TKDL Prior-Art Agent, Master Prompt v7.0.0.

Matches formulation ingredients against the curated TK/prior-art dataset
(``knowledge/permitted_tk_prior_art.json`` via the existing novelty-search
loader) plus well-known contested-patent precedents (turmeric, neem,
karela–jamun), then emits a RED / AMBER / GREEN preliminary risk screen.

Output contract (from ``tkdl_prompt.txt``):
``{risk_level, ingredient_findings, matched_classical_texts, recommendations}``
— a preliminary screen, never a substitute for a professional prior-art search.
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.base import AgentBase, AgentContext
from app.services.novelty_search_service import _load_tk_prior_art

# Well-known contested/revoked biopiracy precedents — defensive citations.
_CONTESTED_CASES: list[dict[str, str]] = [
    {
        "keywords": "turmeric haldi curcumin",
        "case": "Turmeric healing patent (US 5,401,504) — revoked by USPTO",
        "lesson": "Traditional wound-healing use was already documented prior art.",
    },
    {
        "keywords": "neem",
        "case": "Neem (EPO T 356/93) — EPO opposition succeeded",
        "lesson": "Traditional pesticidal use of neem was held obvious.",
    },
    {
        "keywords": "karela jamun bitter gourd",
        "case": "Karela–Jamun (US 6,492,420) — opposed/rejected claims",
        "lesson": "Known hypoglycaemic traditional uses bar broad claims.",
    },
]

_NOVELTY_SIGNALS = (
    "nano",
    "sustained release",
    "controlled release",
    "film coated",
    "polymorph",
    "crystal form",
    "novel process",
    "new process",
    "extraction process",
    "synergistic",
    "novel combination",
    "dosage form",
    "tablet",
    "capsule",
    "granule",
    "microemulsion",
)


class TKDLPriorArtAgent(AgentBase):
    """Component 5: ingredient → TK/classical-text prior-art risk screen."""

    name = "tkdl_agent"
    prompt_file = "tkdl_prompt.txt"

    def assess(
        self,
        ingredients: list[str] | None = None,
        description: str = "",
        classical_text: str = "",
        context: AgentContext | None = None,
    ) -> dict[str, Any]:
        """Preliminary prior-art risk assessment for a formulation."""
        ings = [i.strip() for i in (ingredients or []) if i and i.strip()]
        if context is not None and not ings:
            ings = list(context.ingredients)
        desc = description or ""
        combined = f"{desc} {classical_text}".lower()

        records = _load_tk_prior_art()
        findings: list[dict[str, Any]] = []
        matched_texts: list[str] = []
        documented_count = 0

        for ing in ings:
            hits = self._records_for(ing, records)
            contested = [
                case
                for case in _CONTESTED_CASES
                if self._ingredient_in_keywords(ing, case["keywords"])
            ]
            documented = bool(hits) or bool(contested)
            if documented:
                documented_count += 1
            for hit in hits:
                src = str(hit.get("source_text") or "")
                if src and src not in matched_texts:
                    matched_texts.append(src)
            findings.append(
                {
                    "ingredient": ing,
                    "documented_in_tk": documented,
                    "matched_texts": [
                        str(h.get("source_text") or "") for h in hits
                    ],
                    "contested_cases": [c["case"] for c in contested],
                }
            )

        classical_match = bool(classical_text) and any(
            self.norm(classical_text) in self.norm(str(r.get("source_text") or ""))
            or self.norm(str(r.get("source_text") or "")) in self.norm(classical_text)
            for r in records
        )
        novelty_hits = [s for s in _NOVELTY_SIGNALS if s in combined]

        risk = self._risk_level(len(ings), documented_count, novelty_hits, classical_match)
        result = {
            "risk_level": risk,
            "ingredient_findings": findings,
            "matched_classical_texts": matched_texts,
            "recommendations": self._recommendations(risk, documented_count, ings),
            "disclaimer": (
                "Preliminary screen only — not a substitute for a "
                "professional prior-art search."
            ),
        }
        return self.llm_json(
            "Assess prior-art risk for:\n"
            f"ingredients={ings}\ndescription={desc}\n"
            f"classical_text={classical_text}\nrule_decision={result}",
            fallback=result,
        )

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def norm(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    @staticmethod
    def _ingredient_in_keywords(ingredient: str, keywords: str) -> bool:
        ing = ingredient.lower().split()[0] if ingredient else ""
        return bool(ing) and ing in keywords.split()

    def _records_for(self, ingredient: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        needle = self.norm(ingredient)
        if not needle:
            return []
        out: list[dict[str, Any]] = []
        for rec in records:
            hay_parts = [
                self.norm(str(x))
                for x in (
                    rec.get("canonical_ingredients"),
                    rec.get("source_text"),
                    rec.get("traditional_indication"),
                    rec.get("traditional_processing"),
                )
                if not isinstance(x, list)
            ]
            for item in rec.get("canonical_ingredients") or []:
                hay_parts.append(self.norm(str(item)))
            if any(needle in hay for hay in hay_parts):
                out.append(rec)
        return out

    @staticmethod
    def _risk_level(
        total: int,
        documented: int,
        novelty_hits: list[str],
        classical_match: bool,
    ) -> str:
        if classical_match:
            return "RED"
        if total > 0 and documented == total:
            return "AMBER" if novelty_hits else "RED"
        if documented > 0:
            return "AMBER"
        return "GREEN"

    @staticmethod
    def _recommendations(risk: str, documented: int, ings: list[str]) -> list[str]:
        if risk == "RED":
            return [
                "Section 3(p) bar is likely for verbatim classical knowledge — "
                "do not draft process/efficacy claims around known use.",
                "Cite TKDL references defensively in any filing narrative.",
                "Consider GI, trademark or trade-dress routes instead of patents.",
            ]
        if risk == "AMBER":
            return [
                "Argue inventive step on the specific combination/process/"
                "dosage form and demonstrate surprising synergy.",
                "Run a full professional prior-art search before drafting claims.",
                "Document the technical effect with data to survive examination.",
            ]
        return [
            "No TK match found — run a full professional prior-art search "
            "(global patent + non-patent literature) before filing.",
            "Preserve dated evidence of conception and development.",
            "Re-check ABS clearance if biological resources are involved.",
        ]
