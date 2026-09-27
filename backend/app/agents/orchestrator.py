"""Component 1 — Orchestrator (Router Agent), Master Prompt v7.0.0.

Traffic police for every user query: detects language + jurisdiction +
query type, builds the shared ``AgentContext``, and emits the JSON routing
decision defined in ``app/prompts/orchestrator_prompt.txt``.

Strategy: deterministic rule-based pre-pass (fast, testable, works with the
LLM provider off) with an optional LLM refinement pass when a real provider
(``gemini``/``openai``) is configured — the rule output is always the
fallback, so behaviour is identical in CI and offline demos.
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.base import AgentBase, AgentContext

# --- language -------------------------------------------------------------

_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_TAMIL_RE = re.compile(r"[\u0B80-\u0BFF]")
_BENGALI_RE = re.compile(r"[\u0980-\u09FF]")

# Transliterated-Hindi markers (Latin script) for code-switched queries.
_HI_LATIN_MARKERS = (
    "kar sakte",
    "kar sakte hain",
    "kya ",
    "kaise",
    "bataiye",
    "chahiye",
    "hota hai",
    "karna chahiye",
    "nahi hai",
    "mera ",
    "hum ",
)

# --- jurisdiction ---------------------------------------------------------

_FOREIGN_MARKERS = (
    "trips",
    "wipo",
    "pct",
    "epo",
    "uspto",
    "european patent",
    "international",
    "foreign",
    "export",
    "global market",
    "united states",
    "usa",
    "china",
    "japan",
)

_INDIA_MARKERS = (
    "india",
    "indian",
    "patents act",
    "section 3(p)",
    "dpiit",
    "nba",
    "ayush",
    "fssai",
    "kokila",
    "delhi high court",
)

# --- query type -----------------------------------------------------------

_OUT_OF_SCOPE_PATTERNS = (
    r"\bshould i sue\b",
    r"\bwill my patent be granted\b",
    r"\bwill i get (a )?patent\b",
    r"\b\d+\s?mg\b",
    r"\bdosage\b(?! form)",
    r"\bdose\b(?! form)",
    r"\bprescribe",
    r"\btreat my\b",
    r"\bcure for my\b",
    r"\bcourt strategy\b",
    r"\bpredict.*grant",
)

_ABS_MARKERS = (
    "access and benefit",
    "access & benefit",
    "benefit sharing",
    "benefit-sharing",
    "biological diversity act",
    "biological resources",
    "national biodiversity authority",
    "nba approval",
    "nba clearance",
    "abs approval",
    "abs compliance",
)

_PRIOR_ART_MARKERS = (
    "prior art",
    "patentable",
    "has someone patented",
    "has anyone patented",
    "anyone patented",
    "already patented",
    "novelty of",
    "anticipat",
    "patent search",
    "freedom to operate",
    "patent kar",
    "patent kara",
    "be patented",
    "patentability",
    "can i patent",
    "can we patent",
    "is x patented",
)

_PRODUCT_MARKERS = (
    "churna",
    "kwath",
    "arishta",
    "asava",
    "taila",
    "guggulu",
    "vati",
    "tablet",
    "capsule",
    "formulation",
    "composition",
    "product",
    "supplement",
    "cosmetic",
    "cream",
    "oil",
    "syrup",
    "granules",
    "lehya",
    "avaleha",
)

# Curated ingredient lexicon — Phase 3 classifier refines this via LLM.
_INGREDIENT_LEXICON = (
    "ashwagandha",
    "withania",
    "turmeric",
    "haldi",
    "curcumin",
    "neem",
    "giloy",
    "tinospora",
    "tulsi",
    "holy basil",
    "brahmi",
    "shatavari",
    "amla",
    "haritaki",
    "pippali",
    "ginger",
    "adrak",
    "safed musli",
    "karela",
    "bitter gourd",
    "jamun",
    "methi",
    "fenugreek",
    "sarpagandha",
    "guggulu",
    "boswellia",
    "licorice",
    "mulethi",
    "yastimadhu",
)

_CLASSICAL_TEXT_MARKERS = (
    "charaka",
    "sushruta",
    "susruta",
    "sharangadhara",
    "bhaishajya ratnavali",
    "ayurvedic formulary",
    "first schedule",
    "classical text",
)


class Orchestrator(AgentBase):
    """Component 1: routes every query, builds the shared AgentContext."""

    name = "orchestrator"
    prompt_file = "orchestrator_prompt.txt"

    # -- public API --------------------------------------------------------

    def route(
        self,
        query: str,
        jurisdiction: str | None = None,
        context: AgentContext | None = None,
    ) -> dict[str, Any]:
        """Return the JSON routing decision for one user query."""
        ctx = context or AgentContext()
        text = (query or "").strip()

        ctx.language = self._detect_language(text)
        ctx.jurisdiction = self._detect_jurisdiction(text, jurisdiction, ctx)
        ctx.query_type, ctx.needs_classifier = self._classify_query_type(text)
        ctx.product_name = self._detect_product_name(text)
        ctx.ingredients = self._detect_ingredients(text)

        decision = self._decision(ctx)
        # Optional LLM refinement only when a live provider is configured;
        # the rule-based decision is always the fallback.
        refined = self.llm_json(
            f"Query:\n{text}\n\nRule-based decision:\n{decision}",
            fallback=decision,
        )
        return self._merge_decision(decision, refined, ctx)

    # -- detection helpers -------------------------------------------------

    def _detect_language(self, query: str) -> str:
        if _DEVANAGARI_RE.search(query):
            return "hi"
        if _TAMIL_RE.search(query):
            return "ta"
        if _BENGALI_RE.search(query):
            return "bn"
        lowered = f" {query.lower()} "
        if any(marker in lowered for marker in _HI_LATIN_MARKERS):
            return "hi"
        return "en"

    def _detect_jurisdiction(
        self, query: str, toggle: str | None, ctx: AgentContext
    ) -> str:
        del ctx  # kept for signature symmetry with the other detectors
        lowered = query.lower()
        intl = any(marker in lowered for marker in _FOREIGN_MARKERS)
        india = any(marker in lowered for marker in _INDIA_MARKERS)
        toggle_norm = (toggle or "").strip().lower()
        if toggle_norm in ("india", "in"):
            india = True
        elif toggle_norm in ("international", "global"):
            intl = True
        if intl and india:
            return "both"
        if intl:
            return "international"
        if india:
            return "india"
        return "india"

    def _classify_query_type(self, query: str) -> tuple[str, bool]:
        lowered = query.lower()
        for pattern in _OUT_OF_SCOPE_PATTERNS:
            if re.search(pattern, lowered):
                return "OUT_OF_SCOPE", False
        if any(marker in lowered for marker in _ABS_MARKERS):
            return "ABS_QUESTION", False
        has_product = any(marker in lowered for marker in _PRODUCT_MARKERS)
        has_classical = any(marker in lowered for marker in _CLASSICAL_TEXT_MARKERS)
        has_ingredient = bool(self._detect_ingredients(query))
        names_a_formulation = "patent" in lowered and any(
            m in lowered for m in ("churna", "kwath", "arishta", "asava", "formulation")
        )
        if has_classical or (has_product and has_ingredient) or names_a_formulation:
            return "PRODUCT_SPECIFIC", True
        if any(marker in lowered for marker in _PRIOR_ART_MARKERS):
            return "PRIOR_ART_QUESTION", False
        return "GENERAL_LEGAL", False

    def _detect_product_name(self, query: str) -> str | None:
        words = query.split()
        for i, word in enumerate(words):
            cleaned = word.strip(",.?!")
            if cleaned.lower() in _PRODUCT_MARKERS and i > 0:
                return " ".join(words[max(0, i - 2) : i + 1]).strip(",.?!")
        return None

    def _detect_ingredients(self, query: str) -> list[str]:
        lowered = query.lower()
        found = [name for name in _INGREDIENT_LEXICON if name in lowered]
        # Deduplicate while preserving order (e.g., "turmeric" + "haldi").
        seen: set[str] = set()
        unique: list[str] = []
        for name in found:
            key = name.split()[0]
            if key not in seen:
                seen.add(key)
                unique.append(name)
        return unique

    # -- decision shape ----------------------------------------------------

    def _decision(self, ctx: AgentContext) -> dict[str, Any]:
        return {
            "language": ctx.language,
            "jurisdiction": ctx.jurisdiction,
            "query_type": ctx.query_type,
            "needs_classifier": ctx.needs_classifier,
            "context": {
                "ingredients": list(ctx.ingredients),
                "product_name": ctx.product_name,
            },
        }

    def _merge_decision(
        self,
        rule_decision: dict[str, Any],
        refined: dict[str, Any],
        ctx: AgentContext,
    ) -> dict[str, Any]:
        """LLM output may enrich context but can never flip a rule verdict
        to a less-safe routing (e.g. turning OUT_OF_SCOPE into GENERAL)."""
        merged = dict(rule_decision)
        merged_context = dict(rule_decision.get("context") or {})
        refined_context = refined.get("context")
        if isinstance(refined_context, dict):
            merged_context.update(
                {k: v for k, v in refined_context.items() if v not in (None, [], "")}
            )
        valid_types = (
            "PRODUCT_SPECIFIC",
            "ABS_QUESTION",
            "PRIOR_ART_QUESTION",
            "GENERAL_LEGAL",
            "OUT_OF_SCOPE",
        )
        if refined.get("query_type") in valid_types:
            refined_type = refined["query_type"]
            # OUT_OF_SCOPE is sticky: an LLM can add it, never remove it.
            if refined_type == "OUT_OF_SCOPE" or merged["query_type"] != "OUT_OF_SCOPE":
                merged["query_type"] = refined_type
                merged["needs_classifier"] = bool(
                    refined.get("needs_classifier", refined_type == "PRODUCT_SPECIFIC")
                )
        merged["language"] = refined.get("language") or merged["language"]
        if refined.get("jurisdiction") in ("india", "international", "both"):
            merged["jurisdiction"] = refined["jurisdiction"]
        merged["context"] = merged_context
        # Keep ctx in sync for callers that passed one in.
        ctx.language = str(merged["language"])
        ctx.jurisdiction = str(merged["jurisdiction"])
        ctx.query_type = str(merged["query_type"])
        ctx.needs_classifier = bool(merged["needs_classifier"])
        ctx.ingredients = list(merged_context.get("ingredients") or ctx.ingredients)
        ctx.product_name = merged_context.get("product_name") or ctx.product_name
        return merged
