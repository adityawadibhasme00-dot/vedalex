"""
Jurisdiction Router (VEDALEX | IP-SAKTI SAHAYAK).

The single, hard rule of IP-SAKTI: **India and International legal frameworks
must never be mixed.** This module decides, BEFORE retrieval, which legal
framework governs the answer and keeps every downstream layer (RAG, Rule
Engine, citation voting, response framing) inside that framework.

Two scopes are supported:

  India (default)          → India Code · IP India / CGPDTM · AYUSH · NBA · FSSAI
                             Rule engines: Patent Act Section 3(p), Biological
                             Diversity Act + ABS Rules, FSSAI / D&C Act.
  International            → WIPO · TRIPS · CBD · Nagoya Protocol · US FDA ·
                             Health Canada
                             Rule engines: PCT/WIPO, DSHEA (21 CFR 101.93),
                             Canada NHPR (NPN), CBD/Nagoya ABS.

Resolution priority:
  1. Explicit toggle — the UI always sends context.jurisdiction.
  2. Keyword cue in the question.
  3. Otherwise CLARIFY instead of guessing (safe-abstention for jurisdiction).

Every collected source is then gated by ``filter_sources_by_jurisdiction`` so
a source from the other regime (e.g. an Indian Patent Act passage in
International mode) is never cited — judged as evidence simply does not mix.
"""

from typing import Any, Dict, List, Optional

from app.services.copilot_orchestrator import JURISDICTION_KEYWORDS

INDIA_FRAMEWORK: Dict[str, Any] = {
    "mode": "India",
    "label": "India Laws Only",
    "emoji": "🇮🇳",
    "sources": [
        "India Code",
        "IP India / CGPDTM",
        "Ministry of AYUSH",
        "NBA (Biodiversity Act)",
        "FSSAI",
    ],
    "collections": [
        "regulations", "patents", "traditional_knowledge",
        "biodiversity", "quality_standards", "safety",
    ],
    "rule_engines": [
        "Patent Act · Section 3(p) Readiness",
        "Biological Diversity Act · ABS Rules",
        "FSSAI / D&C Act (Schedule T)",
    ],
    "allowed_jurisdictions": {"", "India", "International"},
    "retrieval_jurisdiction": "India",
}

INTERNATIONAL_FRAMEWORK: Dict[str, Any] = {
    "mode": "International",
    "label": "International Laws Only",
    "emoji": "🌍",
    "sources": [
        "WIPO",
        "TRIPS",
        "CBD / Nagoya Protocol",
        "US FDA (DSHEA)",
        "Health Canada (NHPR)",
        "WHO",
    ],
    "collections": [
        "wipo", "who", "safety", "quality_standards",
    ],
    "rule_engines": [
        "PCT / WIPO",
        "US DSHEA · 21 CFR 101.93",
        "Canada NHPR · NPN Licensing",
        "CBD / Nagoya ABS",
    ],
    "allowed_jurisdictions": {"", "International", "United States", "Canada"},
    "retrieval_jurisdiction": "International",
}

FRAMEWORKS: Dict[str, Dict[str, Any]] = {
    "India": INDIA_FRAMEWORK,
    "International": INTERNATIONAL_FRAMEWORK,
}

# Jurisdiction cues for keyword resolution when no explicit toggle is present.
_INTERNATIONAL_CUES: List[str] = (
    JURISDICTION_KEYWORDS.get("United States", [])
    + JURISDICTION_KEYWORDS.get("Canada", [])
    + JURISDICTION_KEYWORDS.get("International", [])
    + ["wipo", "trips", "cbd", "nagoya", "pct", "patentscope",
       "dshea", "nhpr", "npn", "health canada", "export market", "germany",
       "uk", "europe", "eu market", "united states"]
)

_INTERNATIONAL_CUES = sorted(set(c.lower() for c in _INTERNATIONAL_CUES))


def is_official_explicit(context: Optional[Dict[str, Any]]) -> Optional[str]:
    """Read the jurisdiction toggle sent by the UI, if any."""
    if not context:
        return None
    val = str(context.get("jurisdiction") or "").strip()
    if val in FRAMEWORKS:
        return val
    if val.lower() in ("india", "ind"):
        return "India"
    if val.lower() in ("international", "global", "intl", "world"):
        return "International"
    return None


def _keyword_hint(question: str) -> Optional[str]:
    q = question.lower()
    found_intl = any(cue in q for cue in _INTERNATIONAL_CUES)
    found_ind = any(cue in q for cue in JURISDICTION_KEYWORDS.get("India", []))
    found_us_ca = any(
        cue in q for cue in (
            JURISDICTION_KEYWORDS.get("United States", [])
            + JURISDICTION_KEYWORDS.get("Canada", [])
        )
    )
    if found_us_ca or found_intl:
        return "International"
    if found_ind:
        return "India"
    return None


def resolve_jurisdiction(question: str,
                         context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Decide the governing legal framework.

    Returns a dict with ``mode`` ("India" | "International"),
    ``resolved_via`` (toggle | keyword | default | clarification),
    ``clarification_needed`` and the applicable framework spec.
    """
    explicit = is_official_explicit(context)
    if explicit:
        fw = FRAMEWORKS[explicit]
        return {
            "mode": explicit,
            "resolved_via": "jurisdiction toggle (explicit)",
            "clarification_needed": False,
            "cue": f"toggle → {explicit}",
            **fw,
        }

    hint = _keyword_hint(question or "")
    if hint:
        fw = FRAMEWORKS[hint]
        return {
            "mode": hint,
            "resolved_via": "keyword cue",
            "clarification_needed": False,
            "cue": "keyword match on question",
            **fw,
        }

    # Ambiguous and no toggle: never guess a legal framework the user did not
    # choose — ask, exactly like a careful legal assistant would.
    res: Dict[str, Any] = {
        **FRAMEWORKS["India"],
        "mode": None,
        "resolved_via": "clarification",
        "clarification_needed": True,
        "cue": "no jurisdiction signal",
        "clarification_question": (
            "Your question could fall under more than one legal framework. "
            "Kya aap iska answer India ke legal framework me chahte hain ya "
            "International? — please choose “🇮🇳 India” or “🌍 International” "
            "from the jurisdiction toggle so the answer stays legally consistent."
        ),
    }
    return res


def filter_sources_by_jurisdiction(sources: List[Dict[str, Any]],
                                   mode: str) -> List[Dict[str, Any]]:
    """
    Hard jurisdiction gate. Sources whose jurisdiction belongs to the OTHER
    regime are never cited — India and International law are never mixed.
    Sources with no jurisdiction marker are kept as neutral evidence.
    """
    if not sources:
        return sources
    fw = FRAMEWORKS.get(mode)
    if not fw:
        return sources
    allowed = fw["allowed_jurisdictions"]
    return [
        s for s in sources
        if str(s.get("jurisdiction") or "").strip() in allowed
    ]


def apply_rule_engines_for(mode: str,
                           passport) -> List[Dict[str, Any]]:
    """Run the jurisdiction-appropriate deterministic rule engine on a
    passport. Returns plain finding summaries (never raises)."""
    if not passport:
        return []
    try:
        from app.services.rule_engine import DeterministicRuleEngine
        if mode == "India":
            findings = DeterministicRuleEngine.evaluate_passport(
                passport, target_markets=["India"]
            )
        else:
            findings = DeterministicRuleEngine.evaluate_passport(
                passport, target_markets=["United States", "Canada"]
            )
        summaries = []
        for f in findings:
            summaries.append({
                "jurisdiction": f.jurisdiction,
                "category": f.pathway_category,
                "status": getattr(f.status, "value", str(f.status)),
                "confidence": f.confidence,
                "explanation": f.explanation_text,
                "next_steps": list(f.next_action_steps)[:4],
            })
        return summaries
    except Exception:
        return []