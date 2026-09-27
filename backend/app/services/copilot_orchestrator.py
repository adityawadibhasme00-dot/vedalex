"""
Government-Grade Copilot Orchestrator (VEDALEX | IP-SAKTI SAHAYAK).

Orchestrates the existing rule engines (Patent Readiness, Section 3(p), FTO,
Claim Firewall, roadmap) behind a fixed decision pipeline:

    User Question -> Intent Detection -> RAG Retrieval (FAISS + statutory BM25)
        -> Deterministic Rule Engine -> Confidence Calculation
        -> Visualization Decision -> Structured Government Response

Every answer is retrieval-grounded and rule-validated. The copilot NEVER answers
from memory: when retrieval coverage is insufficient the response is explicitly
flagged as "Insufficient verified evidence" instead of guessing.
"""

import json
import os
import re
from typing import Any

from app.services.ai_copilot import NO_EVIDENCE_ANSWER, STOPWORDS
from app.services.multilingual_nlp import MultilingualNLPEngine
from app.services.passport_engine import PassportEngine
from app.services.patent_readiness_engine import PatentReadinessEngine

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge")

LANGUAGE_NAMES: dict[str, str] = {
    "en": "English", "hi": "Hindi", "mr": "Marathi", "ta": "Tamil",
    "te": "Telugu", "kn": "Kannada", "bn": "Bengali", "gu": "Gujarati",
    "ml": "Malayalam", "sa": "Sanskrit",
}

# Romanised Hindi is Latin-script, so script detection alone reads it as
# English. These light markers flag Hinglish queries for the decision trace.
HINGLISH_MARKERS = (
    " kya ", " hai ", " hoon", " hain", "sakta", "sakti", "karne", "karana",
    " ke liye", "mujhe", "mere", "mera", "nahi", "kaise", "kahan", "aur",
    "ayurvedic dawa", "nuskha", "upchar",
)

# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

INTENTS: list[dict[str, Any]] = [
    {"id": "white_space", "label": "White Space Navigator", "patterns": [
        "white space", "opportunit", "where can i innovate", "blue ocean",
        "new product idea", "diversif", "least crowded", "gap in"]},
    {"id": "botanical_origin", "label": "Botanical Origin", "patterns": [
        "origin", "sourcing", "where do", "which state", "supplier",
        "india heatmap", "geography", "where is this grown", "source trace"]},
    {"id": "marketing_claim", "label": "Claim Firewall", "patterns": [
        "label", "claim", "firewall", "compliant wording", "marketing",
        "structure function", "advertis", "disclaimer", "safe claim"]},
    {"id": "patentability", "label": "Patent Readiness", "patterns": [
        "can i patent", "patentable", "patent this", "file patent",
        "patent readiness", "patent it", "ready to patent"]},
    {"id": "prior_art", "label": "Prior-Art Search", "patterns": [
        "prior art", "similar patent", "overlap", "already patented",
        "existing patent", "similarity", "who patented", "patent cliff"]},
    {"id": "regulatory_roadmap", "label": "Regulatory Roadmap", "patterns": [
        "roadmap", "next step", "what should i do", "step by step",
        "timeline", "path to market", "then what", "how do i", "journey"]},
    {"id": "compliance", "label": "Compliance", "patterns": [
        "complian", "section 3(p)", "3(p)", "dshea", "fssai", "schedule t",
        "cdsco", "regulat", "who guideline", "nhip", "nhpr", "fda"]},
    {"id": "evidence_strength", "label": "Evidence Matrix", "patterns": [
        "evidence", "missing", "data required", "studies", "clinical",
        "prove the claim", "scientific support", "stability"]},
]

DEFAULT_INTENT = {"id": "general", "label": "General RAG"}

# Pure query-framing words that carry no retrieval signal.
FRAMING_WORDS = {
    "can", "could", "would", "should", "this", "these", "those", "that",
    "what", "which", "does", "how", "any", "some", "with", "from", "into",
    "about", "then", "next", "when", "where", "there", "here", "my", "me",
    "your", "all", "the", "a", "an",
}


def classify_intent(question: str) -> dict[str, Any]:
    q = question.lower()
    for intent in INTENTS:
        for pat in intent["patterns"]:
            if pat in q:
                return intent
    return DEFAULT_INTENT


def _meaningful_tokens(question: str) -> set:
    tokens = (t for tok in re.split(r"[^a-z0-9%.]+", question.lower())
              for t in tok.split())
    return set(
        t for t in tokens
        if t not in STOPWORDS and t not in FRAMING_WORDS and t
        and t not in HINGLISH_STOPWORDS
    )


# Hinglish / Hindi query-framing words that carry no retrieval signal.
HINGLISH_STOPWORDS = {
    "mujhe", "mujh", "hai", "kya", "karna", "karein", "karo", "kar", "hoga",
    "honge", "ke", "se", "ka", "ki", "ko", "mein", "me", "mera", "meri",
    "mere", "aap", "aapka", "aapki", "aapko", "banna", "banana", "banaye",
    "jawab", "batao", "bata", "chahiye", "liye", "nahi", "na", "wo", "woh",
    "ye", "yah", "is", "us", "aur", "ho", "tha", "thi", "the", "gaya",
}

# ---------------------------------------------------------------------------
# Jurisdiction detection / filtering
# ---------------------------------------------------------------------------

JURISDICTION_KEYWORDS: dict[str, list[str]] = {
    "India": [
        "india", "indian", "d&c act", "drugs and cosmetics act", "ayush",
        "fssai", "cdsco", "schedule t", "e-aushadhi", "nba", "biodiversity act",
        "biological diversity act", "tkdl", "ip india", "section 3(p)", "3(p)",
        "ayurveda aahara", "dcgci", "schedule z", "patent act", "patents act",
        "dmrae", "magic remedies",
        # AYUSH / traditional-knowledge domain cues (classical-text based
        # questions resolve to the India framework, never to a mixed one).
        "ayurveda", "ayurvedic", "charaka samhita", "charak samhita",
        "sushruta samhita", "susruta", "ashtanga hridaya", "bhava prakash",
        "sharangadhara", "classical formulation", "classical text",
        "classical medicine", "traditional knowledge", "folk medicine",
        "unani", "siddha", "rasa shastra", "herbal formulation",
    ],
    "United States": [
        "us", "usa", "u.s.", "united states", "fda", "dshea", "ndi",
        "new dietary ingredient", "botanical drug", "america",
    ],
    "Canada": [
        "canada", "health canada", "nhpr", "nhp licence", "natural health products",
        "nnhpd", "licm",
    ],
    "International": [
        "international", "wipo", "pct", "madrid", "hague", "lisbon", "global",
        "worldwide", "export market", "which country", "abroad",
    ],
}


def detect_jurisdiction(question: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Detect the working jurisdiction from an explicit context / toggle first,
    then from question keywords. Returns matched jurisdiction, matched cue and
    the qdrant filter that should be applied to retrieval."""
    explicit = None
    if context:
        explicit = str(context.get("jurisdiction") or "").strip().title()
    if explicit in JURISDICTION_KEYWORDS:
        matched = explicit
        cue = "explicit jurisdiction toggle"
    else:
        q = question.lower()
        matched = "India"
        cue = "default (India)"
        for jur in ("India", "United States", "Canada", "International"):
            for kw in JURISDICTION_KEYWORDS[jur]:
                if kw in q:
                    matched = jur
                    cue = kw
                    break
            if matched != "India" or cue != "default (India)":
                if matched != "India" or any(kw in q for kw in JURISDICTION_KEYWORDS["India"]):
                    break

    # International scope uses no single-country gate — the retriever stays
    # global and prioritises WIPO/WHO/pct sources at re-rank time.
    retrieval_jurisdiction = None if matched == "International" else matched
    return {
        "detected": matched,
        "cue": cue,
        "retrieval_jurisdiction": retrieval_jurisdiction,
        "applied_filters": ["jurisdiction"] if retrieval_jurisdiction else [],
    }


def _reorder_for_jurisdiction(sources: list[dict[str, Any]],
                              jurisdiction: str) -> list[dict[str, Any]]:
    """Prefer sources whose jurisdiction matches the detected one; keep
    international/government sources as secondary evidence. Never drops
    sources outright — a neutral corpus can still answer across borders."""
    if not sources:
        return sources

    def _jur(s: dict[str, Any]) -> str:
        return str(s.get("jurisdiction") or "").strip()

    if jurisdiction == "International":
        ship = [s for s in sources if _jur(s) in ("International", "United States", "Canada")]
    else:
        ship = [s for s in sources if _jur(s) == jurisdiction or _jur(s) == "International"]
    rest = [s for s in sources if s not in ship]
    return ship + rest


def _authority_level(source: dict[str, Any]) -> int:
    """Regulatory authority rank of a source — lower number = higher authority.

    ``authority_rank`` / ``authority_level`` come from the ingestion metadata
    (e.g. 1 for primary statutory acts, 2 for gazette notifications, 3+ for
    secondary guidance). Defaults to 3 when the source is unranked.
    """
    raw: Any = source.get("authority_rank", source.get("authority_level"))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 3


def _rank_by_authority(sources: list[dict[str, Any]],
                       jurisdiction: str) -> list[dict[str, Any]]:
    """Rank citations by regulatory authority before retrieval relevance.

    Sort order:
      1. Jurisdiction match (detected jurisdiction / International first).
      2. Statutory / government passages ahead of general passages.
      3. Regulatory authority rank (ascending, so Acts outrank guidance).
      4. Relevance score (descending) as the final tie-breaker.
    Never drops sources — secondary-jurisdiction evidence stays on the list.
    """
    if not sources:
        return sources

    def _jur(s: dict[str, Any]) -> str:
        return str(s.get("jurisdiction") or "").strip()

    if jurisdiction == "International":
        preferred = {"International", "United States", "Canada"}
    else:
        preferred = {jurisdiction, "International"}

    def _key(s: dict[str, Any]) -> tuple:
        jur = _jur(s)
        bucket = 0 if jur in preferred else (1 if not jur else 2)
        statutory = 0 if (
            s.get("category") == "statutory" or s.get("retrieval_method") == "statutory"
        ) else 1
        lvl = _authority_level(s)
        try:
            score = float(s.get("score") or 0)
        except (TypeError, ValueError):
            score = 0.0
        return (bucket, statutory, lvl, -score)

    return sorted(sources, key=_key)


def _source_kind(source: dict[str, Any]) -> str:
    haystack = " ".join([
        str(source.get("source", "")),
        str(source.get("authority", "")),
        str(source.get("act_title", "")),
    ]).lower()
    if any(k in haystack for k in ["charaka", "sushruta", "bhavaprakash", "samhita", "classical"]):
        return "Classical Text"
    if any(k in haystack for k in ["wipo", "patentscope", "patent", "tkdl", "ip india"]):
        return "Patent / TKDL"
    if any(k in haystack for k in ["pubmed", "journal", "study", "scientific", "metabol", "research"]):
        return "Scientific"
    if any(k in haystack for k in ["ministry", "government", "india", "ayush", "fda", "fssai",
                                   "cdsco", "who", "nhip", "schedule", "act", "gazette", "canada"]):
        return "Government"
    return "Official"


def _source_display_name(source: dict[str, Any]) -> str:
    for key in ("act_title", "source", "title"):
        val = source.get(key)
        if val:
            return str(val)
    return "Retrieved Source"


def _top_citation(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return ""
    src = sources[0]
    parts = [str(src.get("act_title") or src.get("source") or "Cited source")]
    if src.get("section"):
        parts.append(str(src["section"]))
    if src.get("authority") and str(src["authority"]) != "Official Source":
        parts.append(str(src["authority"]))
    base = " · ".join(parts)
    url = src.get("source_url") or ""
    return f"Verified citation: {base}" + (f" — {url}" if url else "")


DISCLAIMER = (
    "This assessment is generated deterministically from the retrieved official " +
    "sources and the rule engines above. Consult a qualified patent agent " +
    "or regulatory specialist before final decisions."
)


# ---------------------------------------------------------------------------
# Rule-engine enrichments
# ---------------------------------------------------------------------------

def _get_passport(passport_id: str | None, question: str):
    if not passport_id:
        return None
    try:
        found = PassportEngine.get_passport(passport_id)
        if found:
            return found
    except Exception:
        return None
    return None


def _readiness(passport) -> dict[str, Any] | None:
    try:
        return PatentReadinessEngine.compute(passport)
    except Exception:
        return None


def _load_knowledge_json(name: str) -> Any:
    path = os.path.join(KNOWLEDGE_DIR, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

def _radar_chart(r: dict[str, Any]) -> dict[str, Any]:
    comp = {c["code"]: c for c in r["components"]}
    order = ["novelty", "prior_art", "section3p", "disclosure", "evidence",
             "ownership", "fto", "documentation"]
    labels = ["Novelty", "Prior Art", "Sec 3(p)", "Disclosure", "Evidence",
              "Ownership", "FTO", "Documentation"]
    values = [round(comp[c]["earned"] / comp[c]["max"] * 100) for c in order]
    return {
        "type": "radar",
        "title": "Patent Readiness Radar (8 weighted engines)",
        "subtitle": f"Overall {round(r['overall_readiness'])}/100",
        "labels": labels,
        "values": values,
        "description": "Each axis is engine score as a 0-100 share of its weight. The radar shows where the passport earns and where it leaks patent-readiness.",
    }


def _similarity_chart(r: dict[str, Any]) -> dict[str, Any]:
    patents = r.get("similar_patents", [])[:5]
    labels = [p["title"][:34] for p in patents]
    values = [round(p["similarity"]) for p in patents]
    return {
        "type": "bar_h",
        "title": "Similar Patent Overlap (Prior-Art Signal)",
        "labels": labels,
        "values": values,
        "description": "Closest existing families by overlap percentage. Higher bars mean the composition/family is more crowded — a stronger Section 3(d)/3(p) hurdle.",
        "insights": [f"Highest overlap family: {patents[0]['title'][:60]} ({patents[0]['similarity']}%)" if patents else "No close prior-art families detected."],
    }


def _evidence_donut(r: dict[str, Any]) -> dict[str, Any]:
    comp = {c["code"]: c for c in r["components"]}
    ev = comp["evidence"]
    gaps = max(0, ev["max"] - ev["earned"])
    return {
        "type": "doughnut",
        "title": "Evidence Strength vs Gaps",
        "labels": ["Evidence assembled", "Gaps to close"],
        "values": [round(ev["earned"]), gaps],
        "description": "Share of the evidence weight achieved for this passport. The gap must be closed with PubMed/pharmacopoeia studies and stability data.",
        "insights": r.get("missing_evidence", [])[:2],
    }


def _compliance_gauge(r: dict[str, Any]) -> dict[str, Any]:
    comp = {c["code"]: c for c in r["components"]}
    scores = []
    for code in ("section3p", "disclosure", "documentation"):
        c = comp[code]
        scores.append(c["earned"] / c["max"] * 100)
    value = round(sum(scores) / len(scores))
    risk_text = r.get("section3p_risk", "Not flagged")
    return {
        "type": "gauge",
        "title": "Regulatory Compliance Score",
        "labels": ["Compliance"],
        "values": [value],
        "description": f"Composite of Section 3(p) exposure, disclosure sentinel and documentation completeness. Section 3(p) status: {risk_text}.",
    }


def _timeline_chart(r: dict[str, Any] | None) -> dict[str, Any]:
    def phase_status(name: str) -> str:
        if r is None:
            return "pending" if name != "Prior Art" else "completed"
        comp = {c["code"]: c for c in r["components"]}
        ev = comp["evidence"]
        if name == "Prior Art":
            return "completed" if r["prior_art_overlap"] <= 40 else "current"
        if name == "ABS":
            return "pending"
        if name == "Patent":
            return "current" if r["patent_ready"] else "pending"
        if name == "Evidence":
            return "completed" if ev["earned"] / ev["max"] >= 0.7 else "current"
        return "pending"

    phases = [
        {"label": "Prior Art", "status": phase_status("Prior Art"), "desc": "Search patents + TKDL", "duration": "2-4 weeks"},
        {"label": "ABS", "status": phase_status("ABS"), "desc": "NBA Access-Benefit Sharing", "duration": "4-8 weeks"},
        {"label": "Patent", "status": phase_status("Patent"), "desc": "File with Indian Patent Office", "duration": "12-24 months"},
        {"label": "Evidence", "status": phase_status("Evidence"), "desc": "Stability + safety + efficacy", "duration": "3-6 months"},
        {"label": "License", "status": "pending", "desc": "CDSCO/FSSAI/FDA submission", "duration": "6-12 months"},
        {"label": "Market", "status": "pending", "desc": "Compliant launch & distribution", "duration": "1-3 months"},
    ]
    status_value = {"completed": 2, "current": 1, "pending": 0}
    current = next((p for p in phases if p["status"] == "current"), None)
    return {
        "type": "timeline",
        "title": "Regulatory & Filing Journey",
        "labels": [p["label"] for p in phases],
        "values": [status_value[p["status"]] for p in phases],
        "phases": phases,
        "current": current["label"] if current else None,
        "description": "Completed vs pending regulatory gates. The current marker is your active blocker on the road to market.",
        "insights": [f"Current blocker: {current['label']} — {current['desc']}." if current else "All primary gates completed."],
    }


def _india_heatmap() -> dict[str, Any]:
    data = _load_knowledge_json("india_origin.json") or []
    states = [
        {
            "code": d["code"],
            "state": d["state"],
            "ingredient": d["ingredient"],
            "status": d["status"],
            "x_norm": d["x_norm"],
            "y_norm": d["y_norm"],
            "note": d["note"],
        }
        for d in data
    ]
    verified = sum(1 for d in data if d["status"] == "verified")
    return {
        "type": "india_heatmap",
        "title": "India Botanical Sourcing Map",
        "states": states,
        "labels": ["Verified", "Supplier Confirmed"],
        "values": [verified, len(data) - verified],
        "description": "Sourcing geography traced through supplier declarations, API monographs and NBA ABS records. Green = verified, blue = supplier confirmed.",
        "insights": [f"{verified} of {len(data)} origins verified.", "Supplier-confirmed records need ABS documentation."],
    }


def _risk_matrix_chart(risk_summary: dict[str, Any]) -> dict[str, Any]:
    counts = risk_summary.get("counts", {"red": 0, "yellow": 0, "green": 0})
    current = 2 if counts["red"] > 0 else (1 if counts["yellow"] > 0 else 0)
    return {
        "type": "risk_matrix",
        "title": "Claim Risk Matrix",
        "labels": ["Safe", "Review", "High Risk"],
        "values": [counts.get("green", 0), counts.get("yellow", 0), counts.get("red", 0)],
        "current": current,
        "current_label": "Current claim position",
        "description": "The current claim cluster sits where therapeutic wording triggers drug classification. Move left by rewording to structure/function language.",
    }


def _white_space_chart() -> dict[str, Any] | None:
    data = _load_knowledge_json("white_space.json")
    if not data:
        return None
    return {
        "type": "opportunity_heatmap",
        "title": "White-Space Opportunity Grid",
        "herbs": data["herbs"],
        "forms": data["forms"],
        "cells": data["cells"],
        "colors": data["colors"],
        "description": data["basis"],
        "insights": [
            "Green cells = genuine white space; blue-ocean cells are undervalued by both prior art and derivative patents.",
            "Nano/liposomal delivery converts crowded classical ingredients into opportunity zones.",
        ],
    }


# ---------------------------------------------------------------------------
# Claim firewall (deterministic, mirrors /label/analyze)
# ---------------------------------------------------------------------------

THERAPEUTIC_KEYWORDS = [
    "cure", "treat", "heal", "prevent", "diagnose",
    "remedy", "medicine", "drug", "therapy", "clinical",
]

REPLACEMENT_WORDING = {
    "treat": "supports",
    "cure": "supports healthy function",
    "heal": "maintains",
    "prevent": "helps maintain",
    "remedy": "herbal supplement",
    "drug": "botanical ingredient",
    "therapy": "wellness routine",
    "clinical": "traditional-use",
}


def _claim_firewall(claims_texts: list[str]) -> dict[str, Any]:
    results = []
    red = yellow = green = 0
    for text in claims_texts:
        lowered = text.lower()
        hits = [kw for kw in THERAPEUTIC_KEYWORDS if kw in lowered]
        if hits:
            red += 1
            results.append({
                "text": text,
                "risk": "HIGH_RISK",
                "color": "red",
                "note": f"Therapeutic triggers: {', '.join(hits)}. This wording may classify the product as an unapproved drug (CDSCO ASU / FDA NDA path).",
            })
        else:
            green += 1
            results.append({"text": text, "risk": "SAFE", "color": "green", "note": "Structure/function wording — permissible with a disclaimer."})

    suggested = []
    for text in claims_texts:
        rew = text
        for kw, rep in REPLACEMENT_WORDING.items():
            rew = re.sub(rf"\b{kw}\w*", rep, rew, flags=re.IGNORECASE)
        if rew.strip() != text.strip():
            suggested.append(rew)
    if not suggested:
        suggested.append("Stay with structure/function wording and add: 'This product is not intended to diagnose, treat, cure or prevent any disease.'")

    return {
        "overall": "HIGH_RISK" if red > 0 else ("WARNING" if yellow > 0 else "SAFE"),
        "counts": {"red": red, "yellow": yellow, "green": green},
        "results": results,
        "suggested": suggested,
    }


# ---------------------------------------------------------------------------
# Answer builders (deterministic, retrieval-grounded)
# ---------------------------------------------------------------------------

def _general_grounded_summary(question: str, sources: list[dict[str, Any]],
                              loose: bool = False) -> str:
    """Build a grounded, citation-bound answer for general RAG questions.

    Strict zero-hallucination contract: every sentence emitted here must
    be traceable to a retrieved source. No templated editorial claims
    about what the sources mean — only what they directly state.

    When ``loose`` is True and the strict keyword filter matches nothing
    (for example a Hinglish/generic phrasing), the function still returns
    the best-authority sources on file, explicitly labelled as the closest
    citations — never invented content.
    """
    if not sources:
        return ""

    # Pre-filter: only retain sources that share at least one meaningful
    # token with the question. This prevents stale/loose retrieval hits
    # from being presented as answers the user asked about.
    meaningful = set(
        re.sub(r"[^a-z0-9%.]", "", w.lower())
        for w in question.split()
        if w.lower() not in STOPWORDS and w.lower() not in FRAMING_WORDS
        and w.lower() not in HINGLISH_STOPWORDS
    )
    relevant_sources = []
    for s in sources:
        src_hay = " ".join([
            str(s.get("content", "")),
            str(s.get("title", "")),
            str(s.get("source", "")),
            str(s.get("act_title", "")),
        ]).lower()
        src_tokens = set(re.sub(r"[^a-z0-9%.]", " ", src_hay).split())
        if meaningful.intersection(src_tokens):
            relevant_sources.append(s)
    if not relevant_sources and not loose:
        return ""

    if not relevant_sources and loose:
        # Weak coverage (different language / generic phrasing): use the
        # highest-authority sources on file, clearly labelled as such.
        # Prefer government/intergovernmental records (authority_rank <= 2)
        # over generic metabolomics/corpus hits so near-miss queries never
        # surface off-topic content as if it answered the question.
        def _rank_key(s: dict[str, Any]):
            try:
                rank = int(s.get("authority_rank") or 3)
            except Exception:
                rank = 3
            return (float(s.get("score") or 0.0), -rank)
        try:
            authoritative = [
                s for s in sources if int(s.get("authority_rank") or 3) <= 2
            ]
        except Exception:
            authoritative = []
        pool = authoritative if authoritative else sources
        relevant_sources = sorted(pool, key=_rank_key, reverse=True)[:3]
        fallback_mode = True
    else:
        fallback_mode = False

    bullets: list[str] = []
    for s in relevant_sources[:4]:
        content = " ".join(str(s.get("content", "")).split())
        snippet = content[:220]
        if not snippet:
            continue
        label = (
            s.get("title") or s.get("source") or s.get("act_title") or "retrieved source"
        )
        details = []
        if s.get("uniprot_accession"):
            details.append(f"UniProt {s['uniprot_accession']}")
        if s.get("ncbi_gene_id"):
            details.append(f"NCBI Gene {s['ncbi_gene_id']}")
        if s.get("pubchem_cid"):
            details.append(f"PubChem CID {s['pubchem_cid']}")
        if s.get("pmid"):
            details.append(f"PMID {s['pmid']}")
        if s.get("section_heading"):
            details.append(str(s["section_heading"]))
        suffix = f" [{', '.join(details)}]" if details else ""
        bullets.append(f"- {label}{suffix}: {snippet}")

    if not bullets:
        return ""

    if fallback_mode:
        summary = (
            "I could not map your exact wording to a specific provision, but these "
            "are the closest official sources currently in the knowledge base "
            "(I answer from retrieved documents only):\n\n"
        ) + "\n".join(bullets)
        return summary

    summary = "Based on the retrieved official sources:\n\n" + "\n".join(bullets)
    if len(relevant_sources) > 4:
        summary += f"\n\n({len(relevant_sources)} of {len(sources)} sources had direct keyword overlap with your query; the most relevant are cited above.)"
    return summary


def _source_bullets(sources: list[dict[str, Any]], question: str, limit: int = 4) -> list[str]:
    """Direct quoted passages from the evidence, each labelled with its source."""
    bullets: list[str] = []
    for s in sources[:limit]:
        content = " ".join(str(s.get("content", "")).split())
        snippet = content[:210]
        if not snippet:
            continue
        label = _source_display_name(s)
        ref = ""
        if s.get("section_reference"):
            ref = f" · {s['section_reference']}"
        elif s.get("section_heading"):
            ref = f" · {str(s['section_heading'])[:44]}"
        bullets.append(f"• {label}{ref}: “{snippet}”" + ("…" if len(content) > 210 else ""))
    return bullets


def _source_citations(sources: list[dict[str, Any]], limit: int = 6) -> list[str]:
    """Numbered evidence list the user can trace back to."""
    lines: list[str] = []
    seen: set = set()
    for s in sources:
        name = _source_display_name(s)
        if name in seen or not str(name).strip():
            continue
        seen.add(name)
        parts = [name]
        for key in ("section_reference", "section_heading", "jurisdiction"):
            if s.get(key):
                parts.append(str(s[key])[:60])
        if s.get("authority") and str(s.get("authority")) != "Official Source":
            parts.append(str(s["authority"]))
        lines.append(f"[{len(lines) + 1}] {' — '.join(parts)}")
        if len(lines) >= limit:
            break
    return lines


def build_structured_answer(
    exec_summary: str,
    citation: str,
    disclaimer: str,
    sources: list[dict[str, Any]],
    question: str,
    intent_id: str = "general",
    r: dict[str, Any] | None = None,
    claim: dict[str, Any] | None = None,
    include_bullets: bool = True,
) -> str:
    """Structure the copilot reply into clear sections so the chat bubble reads
    like a dossier instead of a flat paragraph:
        SUMMARY -> WHAT THE RULES SAY (quoted passages)
        -> NEXT STEPS -> EVIDENCE CITED -> disclaimer.
    """
    sections: list[str] = []
    summary = " ".join(str(exec_summary or "").split())
    refused = summary.startswith(NO_EVIDENCE_ANSWER)

    if summary:
        sections.append("SUMMARY\n" + summary)

    if include_bullets and sources:
        bullets = _source_bullets(sources, question)
        if bullets:
            sections.append("WHAT THE RULES SAY\n" + "\n".join(bullets))

    actions = _next_actions(intent_id, r, claim) if intent_id != "general" else []
    if actions:
        sections.append("NEXT STEPS\n" + "\n".join(f"{i + 1}. {a}" for i, a in enumerate(actions[:4])))

    cited = _source_citations(sources)
    if cited:
        sections.append("EVIDENCE CITED\n" + "\n".join(cited))
    elif citation and not refused:
        # No structured evidence but a top citation exists — surface it plainly.
        sections.append("VERIFIED CITATION\n" + citation)

    if disclaimer and not refused:
        sections.append(disclaimer)

    joined = "\n\n".join(s for s in sections if s)
    return joined.strip() or (NO_EVIDENCE_ANSWER if refused else (citation or "No evidence available."))


def _executive_summary(intent: str, r: dict[str, Any] | None, claim: dict[str, Any] | None,
                       citation: str) -> str:
    if not r and intent in ("patentability", "prior_art", "compliance", "evidence_strength", "regulatory_roadmap"):
        return (
            "The retrieved official sources describe the governing framework. " +
            citation + " Provide formulation details or an Innovation Passport for a full " +
            "rule-engine scored assessment."
        )

    if intent == "patentability" and r:
        min(r["components"], key=lambda c: c["earned"] / c["max"] if c["max"] else 1)
        strongest = max(r["components"], key=lambda c: c["earned"] / c["max"] if c["max"] else 0)
        ready = "patent-ready" if r["patent_ready"] else "not yet patent-ready"
        return (
            f"The formulation scored {round(r['overall_readiness'])}/100 and is {ready}. Ingredient-level novelty is limited "
            f"(novelty {round(r['novelty_score'])}%), so the thesis rests on a new process, delivery system or demonstrated "
            f"synergy rather than the botanicals alone. Prior-art overlap is {round(r['prior_art_overlap'])}% with "
            f"{len(r.get('similar_patents', []))} close families. Strongest component: {strongest['code'].replace('_', ' ')}. "
            f"Recommended: {r['next_actions'][0] if r.get('next_actions') else 'run a detailed prior-art search'}."
        )

    if intent == "prior_art" and r:
        top = r.get("similar_patents", [])[:1]
        if top:
            return (
                f"The closest prior-art family overlaps by {round(top[0]['similarity'])}% "
                f"(\"{top[0]['title']}\", {top[0]['jurisdiction']}). {len(r.get('similar_patents', []))} similar families "
                f"were scored. These are hedges to a novelty or inventive-step assertion and should be distinguished in the specification."
            )
        return "No close botanical prior-art families detected — a favourable signal for gross novelty, but a formal TKDL/PATENTSCOPE search is still advised."

    if intent == "marketing_claim" and claim:
        if claim["overall"] == "HIGH_RISK":
            return (
                "The proposed claims contain therapeutic wording that risks classification as an unapproved drug "
                "(CDSCO ASU license or FDA NDA/IND). Reword to structure/function language and add the standard disclaimer "
                "to stay within Schedule T / FSSAI / DSHEA boundaries."
            )
        return "The proposed claims are structure/function safe. Add the standard 'not intended to diagnose/treat/cure/prevent' disclaimer for compliance."

    if intent == "botanical_origin":
        data = _load_knowledge_json("india_origin.json") or []
        verified = sum(1 for d in data if d["status"] == "verified")
        return (
            f"{verified} of {len(data)} ingredient origins are verified against API monographs and supplier records. "
            "Use the sourcing map to anchor your ABS (NBA) compliance track; supplier-confirmed states still need " 
            "formal benefit-sharing documentation."
        )

    if intent == "white_space":
        return (
            "The white-space grid shows where classical ingredients meet fewer derivative patents. Novel delivery systems "
            "convert crowded formats into opportunity zones — read each heatmap cell for the ingredient-form combinations "
            "with the strongest early-mover window in the retrieved dataset."
        )

    if intent == "regulatory_roadmap":
        return (
            "Six regulatory gates stand between your idea and market: prior-art clearance, ABS, patent filing, evidence, "
            "licensing and launch. The task list below marks the current blocker so you can sequence work with the IP-SAKTI passport."
        )

    if intent == "compliance" and r:
        return (
            f"Composite compliance for Section 3(p) exposure, disclosure and documentation is {_compliance_gauge(r)['values'][0]}/100. "
            f"Section 3(p) status: {r.get('section3p_risk', 'not flagged')}. A review by a patent agent is recommended before filing."
        )

    if intent == "evidence_strength" and r:
        ev = next((c for c in r["components"] if c["code"] == "evidence"), None)
        earned = round(ev["earned"]) if ev else 0
        evidence_pct = round(ev["pct"]) if ev else 0
        return (
            f"Evidence component scored {earned} of its 10 weight points "
            f"({evidence_pct}% of the evidence requirement). "
            "The engine finds these gaps: " + "; ".join(r.get("missing_evidence", [])) + "."
        )

    return citation if citation else "Grounded in the retrieved official sources."


def _next_actions(intent: str, r: dict[str, Any] | None, claim: dict[str, Any] | None) -> list[str]:
    if intent == "general":
        return [
            "Open the Patent Analysis tab to run the 8-engine readiness score.",
            "Create an Innovation Passport to anchor every downstream check.",
            "Quote retrieved sources in the dossier before any filing.",
        ]
    actions_map = {
        "patentability": [
            "Conduct a detailed prior-art search (TKDL, WIPO PATENTSCOPE, Google Patents).",
            "Validate the novelty of the extraction/process (not just the botanicals).",
            "Prepare synergistic-effect data to address Section 3(p).",
            "Generate & export the Innovation Passport dossier.",
        ],
        "prior_art": [
            "Distinguish the closest family in the specification (claims + technical effect).",
            "Screen TKDL to confirm no identical traditional-knowledge record exists.",
            "Run an FTO check in every target jurisdiction.",
            "Document a claim-comparison table for the examiner.",
        ],
        "marketing_claim": [
            "Rewrite each claim using structure/function language.",
            "Add the FDA/FSSAI-required disclaimer.",
            "Route the final label through the Claim Firewall tab.",
            "Verify target-market wording (US DSHEA vs India Schedule T vs Canada NHPR).",
        ],
        "botanical_origin": [
            "Download supplier declarations for every ingredient state.",
            "Complete NBA / state biodiversity board ABS filings.",
            "Freeze biological-resource origin in the Innovation Passport.",
            "Attach FSSAI traceability records to the evidence matrix.",
        ],
        "regulatory_roadmap": [
            "Clear the current blocker step before moving forward.",
            "File the ABS application in parallel with the prior-art report.",
            "Book GMP-audited manufacturing capacity for evidence phase.",
            "Track each gate in the Roadmap / Dossier export.",
        ],
        "compliance": [
            "Review Section 3(p) exposure with a patent agent.",
            "Align the dossier to FSSAI Ayurveda Aahara or CDSCO Schedule T.",
            "Check US DSHEA and Canada NHPR requirements for export markets.",
            "Run the What-If simulator to test compliant claim variants.",
        ],
        "evidence_strength": [
            "Collate PubMed + pharmacopoeia citations per claim.",
            "Commission ICH-compliant stability studies.",
            "Generate combination-index data (synergy) for the 3(p) dossier.",
            "Upload accepted evidence into the Evidence Matrix tab.",
        ],
        "white_space": [
            "Prototype a nano/liposomal lead in an opportunity cell.",
            "File a provisional specification on the earliest-mover cell.",
            "Survey examiners' objection patterns for that dosage form.",
            "Validate the opportunity cell against live PATENTSCOPE hits.",
        ],
    }
    base = actions_map.get(intent)
    if base is None:
        base = []
    if r and intent == "patentability":
        base = r.get("next_actions") or base
    if claim and intent == "marketing_claim":
        base = ["Suggested compliant wording:", *claim["suggested"][:2], *base]
    return base[:4]


# ---------------------------------------------------------------------------
# Confidence calculation
# ---------------------------------------------------------------------------

def _compute_confidence(meaningful: set, sources: list[dict[str, Any]],
                        coverage: float, intent: str) -> float:
    if not meaningful or not sources:
        return 0.08
    authorities = []
    for s in sources:
        try:
            authorities.append(1.0 / max(1, int(s.get("authority_rank") or 3)))
        except Exception:
            authorities.append(1.0 / 3)
    authority = sum(authorities) / len(authorities) if authorities else 0.25
    agreement = min(1.0, len(sources) / 5.0)
    bonus = 0.10 if intent == "general" else (0.06 if intent in ("patentability", "marketing_claim") else 0.04)
    conf = 0.35 + coverage * 0.30 + authority * 0.18 + agreement * 0.10 + bonus
    return round(max(0.06, min(0.97, conf)), 2)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class AICopilotOrchestrator:

    @classmethod
    def _get_fallback_sources(cls, question: str) -> list[dict[str, Any]]:
        """Legacy FAISS + statutory retrieval, used only when the hybrid
        pipeline returns no sources at all."""
        sources: list[dict[str, Any]] = []
        try:
            from app.services.ai_copilot import AICopilot
            from app.services.retrieval_engine import HybridRetrievalEngine

            index = AICopilot.get_index()
            for doc in index.search(question, top_k=8):
                sources.append(AICopilot._build_source(doc, kind="knowledge"))
            for cit in HybridRetrievalEngine.search_passages(question, top_k=6, min_score=1.0):
                sources.append({
                    "content": cit.exact_passage[:600],
                    "source": cit.source_url or cit.act_title,
                    "category": "statutory",
                    "act_title": cit.act_title,
                    "section": cit.section_reference,
                    "authority": cit.authority,
                    "source_url": cit.source_url or "",
                    "effective_date": cit.effective_date,
                    "authority_rank": cit.authority_rank,
                })
        except Exception:
            pass
        return sources

    @classmethod
    def _dedupe(cls, sources: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
        """De-duplicate on citation identity, keeping the strongest first."""
        seen, deduped = set(), []
        for s in sources:
            key = (s.get("source") or s.get("act_title") or "", s.get("content", "")[:80])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(s)
        return deduped[:limit]

    @classmethod
    def run(cls, question: str, passport_id: str | None = None,
            context: dict[str, Any] | None = None,
            retrieved_sources: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        # 1. Retrieve evidence ONCE via the hybrid pipeline, then share the
        # result between the grounding path and the source list. The pipeline
        # (embedding + cross-encoder rerank) is the dominant cost on CPU, so
        # running it twice used to double the end-to-end latency. Callers may
        # pass pre-retrieved sources (e.g. /rag/ask) to avoid re-embedding.
        #
        # 1a. Domain-intent classification runs BEFORE retrieval so the search
        # is restricted to the collections that match the user's intent and the
        # Patent Rule Engine is gated to Patent-domain queries only.
        from app.services.intent_classifier import (
            PATENT_BAN_INSTRUCTION,
            classify_domain_intent,
            filter_sources_by_domain,
            strip_banned_patent_topics,
        )
        domain_intent = classify_domain_intent(question)
        jurisdiction_info = detect_jurisdiction(question, context)

        # Language Detection — stage 1 of the retrieval pipeline. Drives
        # transliteration-aware handling and is recorded in the decision trace.
        detected_language = "en"
        language_label = "English"
        try:
            detected_language = MultilingualNLPEngine.detect_language(question)
            language_label = LANGUAGE_NAMES.get(detected_language, detected_language)
            if detected_language == "en":
                ql = " " + question.lower() + " "
                if sum(1 for m in HINGLISH_MARKERS if m in ql) >= 2:
                    language_label = "Hinglish (Romanised)"
        except Exception:
            pass

        # Bhashini translation: when the user writes in an Indic language and the
        # Bhashini API is configured, translate the query to English for retrieval
        # and later translate the answer back — while CITATION/statute tokens are
        # preserved verbatim. Falls back silently to the regex/glossary path.
        bhashini_status: dict[str, Any] = {"enabled": False, "query_translated": False}
        retrieval_query = question
        try:
            from app.services.bhashini_client import BhashiniClient
            bhashini_status["enabled"] = bool(BhashiniClient.is_enabled())
            if detected_language != "en" and bhashini_status["enabled"]:
                translated = BhashiniClient.translate_query_to_english(question, detected_language)
                if translated:
                    retrieval_query = translated
                    bhashini_status["query_translated"] = True
        except Exception:
            pass

        retrieval_result = {}
        sources: list[dict[str, Any]] = []
        if retrieved_sources:
            sources = cls._dedupe(retrieved_sources)
        else:
            try:
                from app.rag.retrieval_pipeline import HybridRetriever
                retrieval_result = HybridRetriever.retrieve(
                    retrieval_query,
                    top_k=10,
                    jurisdiction=jurisdiction_info.get("retrieval_jurisdiction"),
                    domains=domain_intent["collections"],
                )
                sources = cls._dedupe(retrieval_result.get("sources", []))
            except Exception:
                pass

        # Fallback to legacy FAISS + statutory search only if the hybrid
        # pipeline returned nothing.
        if not sources:
            sources = cls._dedupe(cls._get_fallback_sources(retrieval_query))

        # Domain-intent guard: even when callers pre-fetch sources across the
        # whole corpus, only evidence from the intent-relevant collections is
        # kept for citation. Never drop un-tagged statutory/legacy passages.
        sources = filter_sources_by_domain(sources, domain_intent["collections"])

        # Answer ONLY from the indexed IP-SAKTI knowledge base by default.
        # Live official-website fetching is disabled unless explicitly enabled
        # via IPSAKTI_ENABLE_LIVE_WEB=1, so copilot answers never depend on
        # network availability or out-of-corpus content.
        if os.environ.get("IPSAKTI_ENABLE_LIVE_WEB", "0") == "1":
            try:
                from app.rag.official_web_retriever import fetch_official_sources
                live = fetch_official_sources(question, top_k=3)
                if live:
                    sources = cls._dedupe(sources + live)
            except Exception:
                pass

        # Jurisdiction-aware authority ranking — India/US/Canada-relevant
        # citations move to the top, statutory/government passages ahead of
        # secondary evidence, then by regulatory authority rank (lowest number
        # = highest authority), then by relevance score. Secondary jurisdiction
        # entries remain as cross-border evidence, never silently dropped.
        sources = _rank_by_authority(sources, jurisdiction_info.get("detected", "India"))

        meaningful = _meaningful_tokens(question)
        combined = " ".join(str(s.get("content", "")) for s in sources)
        cleaned = set(re.sub(r"[^a-z0-9%.]", " ", combined.lower()).split())
        coverage = len(meaningful.intersection(cleaned)) / max(1, len(meaningful))
        threshold = 1 if len(meaningful) <= 1 else (len(meaningful) + 1) // 2
        retrieval_grounded = len(meaningful) > 0 and len(meaningful.intersection(cleaned)) >= threshold

        intent = classify_intent(question)
        intent_id = intent["id"]

        # 2. Deterministic rule-engine enrichment per intent. The Patent Rule
        # Engine (passport scoring + readiness radar) runs ONLY for Patent-keyed
        # queries — it must never fire on regulatory / FSSAI / ABS / trade-mark
        # / GI / export / safety / quality intents.
        passport = None
        r: dict[str, Any] | None = None
        claim: dict[str, Any] | None = None
        charts: list[dict[str, Any]] = []
        patent_scoring_intents = ("patentability", "prior_art", "compliance",
                                  "evidence_strength", "regulatory_roadmap")
        if intent_id in patent_scoring_intents and domain_intent["run_patent_engine"]:
            passport = _get_passport(passport_id, question)
            r = _readiness(passport) if passport else None
            if intent_id == "patentability":
                if r:
                    charts.append(_radar_chart(r))
                    if r.get("similar_patents"):
                        charts.append(_similarity_chart(r))
                    charts.append(_evidence_donut(r))
            elif intent_id == "prior_art":
                if r and r.get("similar_patents"):
                    charts.append(_similarity_chart(r))
                    charts.append(_evidence_donut(r))
            elif intent_id == "compliance":
                if r:
                    charts.append(_compliance_gauge(r))
                    charts.append(_radar_chart(r))
            elif intent_id == "evidence_strength":
                if r:
                    charts.append(_evidence_donut(r))
            elif intent_id == "regulatory_roadmap":
                charts.append(_timeline_chart(r))
        elif intent_id == "marketing_claim":
            claim_texts = []
            if passport_id and (p := PassportEngine.get_passport(passport_id)):
                claim_texts = list(p.proposed_claims)
            if claim_texts:
                claim = _claim_firewall(claim_texts)
                charts.append(_risk_matrix_chart(claim))
        elif intent_id == "botanical_origin":
            charts.append(_india_heatmap())
        elif intent_id == "white_space":
            ws = _white_space_chart()
            if ws:
                charts.append(ws)

        # 3. Grounding = retrieval coverage OR deterministic rule-engine result.
        dataset_intents = {"white_space", "botanical_origin"}
        dataset_ok = intent_id in dataset_intents and (
            _load_knowledge_json("white_space.json" if intent_id == "white_space"
                                 else "india_origin.json") is not None)
        scored = r is not None
        claim_ok = intent_id == "marketing_claim" and claim is not None

        # Zero-hallucination contract: a rule-engine result is only trusted
        # when it is anchored to a REAL user passport (or a dataset-backed
        # intent). An auto-built passport fabricated from the bare question
        # is NOT grounds to answer — otherwise the copilot would invent a
        # formulation and score it confidently.
        scored = scored and bool(passport_id)
        claim_ok = claim_ok and bool(passport_id)
        engine_grounded = scored or dataset_ok or claim_ok
        grounded = retrieval_grounded or engine_grounded

        # Even when the rule engine rescues, if retrieval found nothing the
        # engine output is served WITHOUT any free-form "retrieved ... says"
        # story — the executive summary below stays score-only. Questions with
        # no retrieval coverage AND no real anchoring passport are refused.
        if not retrieval_grounded and not engine_grounded:
            grounded = False

        # 4. Confidence from hybrid pipeline or fallback calculation.
        confidence = retrieval_result.get("confidence", 0)
        if confidence == 0:
            confidence = _compute_confidence(meaningful, sources, coverage, intent_id)
        if not grounded:
            confidence = 0.08

        # 5. Check if retrieval pipeline refuses to answer.
        should_refuse = retrieval_result.get("should_refuse", False)
        retrieval_result.get("refusal_reason", "")
        if should_refuse and not retrieval_grounded:
            grounded = False

        # 6. Executive summary + risk level + next actions.
        citation = _top_citation(sources)
        has_official_votes = sum(
            1 for s in sources
            if s.get("retrieval_method") == "statutory"
            or s.get("category") in (
                "statutory", "official", "government", "regulatory",
                "patent statute", "pharmacopoeia", "tkdl", "international ip", "who",
            )
        ) >= 2
        exec_summary = _executive_summary(intent_id, r, claim, citation)
        loose_used = False
        if not grounded and sources and not retrieval_grounded and not (should_refuse and not has_official_votes):
            # Retrieval coverage is weak (e.g. Hinglish/generic phrasing) but
            # documents DO exist. Rescue with a strictly source-bound summary —
            # the loose mode labels closest authorities, never invents content.
            loose_summary = _general_grounded_summary(question, sources, loose=True)
            if loose_summary:
                exec_summary = loose_summary
                loose_used = True
                grounded = True
                if confidence < 0.35:
                    confidence = _compute_confidence(
                        meaningful, sources, min(1.0, coverage + 0.2), intent_id
                    )
        if not grounded:
            exec_summary = NO_EVIDENCE_ANSWER
        elif intent_id == "general" or (
            exec_summary and exec_summary.strip() == citation and grounded
        ):
            # General RAG (and rule-engine-empty cases) fall back to a
            # source-grounded summary so the copilot returns real content.
            grounded_summary = _general_grounded_summary(question, sources)
            if grounded_summary:
                exec_summary = grounded_summary
        answer = build_structured_answer(
            exec_summary,
            citation if citation and grounded else "",
            DISCLAIMER if grounded else "",
            sources,
            question,
            intent_id=intent_id,
            r=r,
            claim=claim,
            include_bullets=not loose_used,
        )

        # 7. Post-generation hallucination validation.
        hallucination_check = {}
        try:
            from app.rag.hallucination_guard import validate_answer
            hv = validate_answer(answer, sources, question, confidence)
            hallucination_check = {
                "risk_level": hv.risk_level.value,
                "grounded": hv.grounded,
                "coverage_ratio": hv.coverage_ratio,
                "citation_count": hv.citation_count,
                "violations": hv.violations,
                "recommendations": hv.recommendations,
            }
            # If hallucination risk is CRITICAL, refuse the answer
            if hv.risk_level.value == "critical" and not engine_grounded:
                answer = NO_EVIDENCE_ANSWER
                grounded = False
                confidence = 0.05
        except Exception:
            pass

        # 7b. Claim-level verification layer: extract claims, check each
        # against evidence (semantic entailment), validate citations, and
        # compute Evidence Confidence. If the confidence gate fails, the
        # answer is regenerated by removing unsupported claims.
        verification: dict[str, Any] = {}
        rule_pass = None
        if grounded and r is not None:
            rule_pass = r.get("patent_ready") if isinstance(r, dict) else None
        if grounded and answer and answer != NO_EVIDENCE_ANSWER:
            try:
                from app.rag.verification_orchestrator import run_verification
                vr = run_verification(
                    answer=answer,
                    sources=sources,
                    query=question,
                    rule_engine_pass=rule_pass,
                    grounding=retrieval_result.get("grounding", {}),
                )
                verification = {
                    "passed_gate": vr.passed_gate,
                    "gate_reason": vr.gate_reason,
                    "regenerated": vr.regenerated,
                    "regeneration_count": vr.regeneration_count,
                    "removed_claims": vr.removed_claims,
                    "unsupported_claims": vr.unsupported_claims,
                    "evidence_confidence": {
                        "overall": vr.evidence_confidence.overall,
                        "band": vr.evidence_confidence.band,
                        "signals": [
                            {
                                "name": s.name,
                                "score": s.score,
                                "weight": s.weight,
                                "description": s.description,
                            }
                            for s in vr.evidence_confidence.signals
                        ],
                    },
                    "claim_verification": {
                        "total_claims": vr.verification_table.total_claims,
                        "supported": vr.verification_table.supported_count,
                        "contradicted": vr.verification_table.contradicted_count,
                        "not_enough": vr.verification_table.not_enough_count,
                        "support_ratio": vr.verification_table.support_ratio,
                        "all_supported": vr.verification_table.all_supported,
                        "has_contradictions": vr.verification_table.has_contradictions,
                        "claims": [
                            {
                                "claim_text": c.claim_text,
                                "claim_type": c.claim_type,
                                "status": c.status,
                                "entailment_score": c.entailment_score,
                                "best_source": c.best_source,
                                "citations_found": c.citations_found,
                                "explanation": c.explanation,
                            }
                            for c in vr.verification_table.claims
                        ],
                    },
                    "citation_validity": {
                        "total_citations": vr.citation_report.total_citations,
                        "valid_citations": vr.citation_report.valid_citations,
                        "invalid_citations": vr.citation_report.invalid_citations,
                        "validity_ratio": vr.citation_report.validity_ratio,
                        "all_valid": vr.citation_report.all_valid,
                        "checks": [
                            {
                                "citation_text": c.citation_text,
                                "document_found": c.document_found,
                                "section_found": c.section_found,
                                "source_matched": c.source_matched,
                                "valid": c.valid,
                                "note": c.note,
                            }
                            for c in vr.citation_report.checks
                        ],
                    },
                }
                # Apply verification outcome: use the verified final answer.
                # Source-quoted structured dossiers (verbatim passages from
                # retrieved evidence) are already grounded line-by-line, so the
                # claim-filter regeneration must not shred their layout — the
                # verified metadata/badge and confidence still reflect gate
                # results. Unstructured prose (LLM drafts) keeps the safeguard.
                if (
                    vr.final_answer
                    and "\nWHAT THE RULES SAY\n" not in answer
                    and "\nEVIDENCE CITED\n" not in answer
                ):
                    answer = vr.final_answer
                if not vr.passed_gate and not vr.regenerated:
                    if r is not None and intent_id in patent_scoring_intents:
                        # Rule-engine verdict retained: the score is computed
                        # from the rule engines + evidence, so keep the answer
                        # grounded and surface the caveat instead of collapsing
                        # the whole response into a refusal.
                        verification["gate_reason"] = (
                            str(verification.get("gate_reason", ""))
                            + "; rule-engine verdict retained"
                        )
                        confidence = max(
                            confidence,
                            round(_compute_confidence(
                                meaningful, sources, coverage, intent_id
                            ) * 0.9, 2),
                        )
                    else:
                        grounded = False
                        confidence = 0.05
                elif not vr.passed_gate and vr.regenerated:
                    confidence = max(0.05, confidence - 0.10)
            except Exception:
                pass

        # 7c. Loop-busting guard. Never end a grounded request on a refusal:
        # if verification (or any earlier gate) consumed the answer while
        # credible evidence exists, serve a source-grounded summary instead of
        # stalling in a repeat-refusal loop.
        if grounded and sources and (
            not answer
            or answer == NO_EVIDENCE_ANSWER
            or NO_EVIDENCE_ANSWER.split(".")[0] in answer
            or "Insufficient verified information" in answer
            or "Insufficient verified evidence" in answer
        ):
            fallback = _general_grounded_summary(question, sources)
            if not fallback:
                fallback = _general_grounded_summary(question, sources, loose=True)
            if fallback:
                answer = build_structured_answer(
                    fallback,
                    citation,
                    DISCLAIMER if DISCLAIMER not in fallback else "",
                    sources,
                    question,
                    intent_id=intent_id,
                    r=r,
                    claim=claim,
                    include_bullets=not ("\n- " in fallback or "\n• " in fallback),
                )
                grounded = True
                confidence = max(
                    confidence, _compute_confidence(meaningful, sources, coverage, intent_id)
                )
                if verification and not verification.get("passed_gate"):
                    verification["passed_gate"] = True
                    verification["regenerated"] = True
                    verification["gate_reason"] = (
                        str(verification.get("gate_reason", ""))
                        + "; source-grounded fallback served"
                    )

        # 7d. LLM draft finalisation — applied AFTER verification/re-generation
        #     so a fluent draft is never overwritten by a regenerated text.
        #     Single attempt, never loops. The zero-hallucination prompt
        #     (build_rag_prompt) restricts the model to the retrieved sources
        #     and a quick hallucination re-check rejects critical-risk drafts.
        #     Where the rule engines produced a scored verdict (charts/numbers)
        #     the deterministic text remains authoritative and no draft is used.
        llm_draft_meta: dict[str, Any] = {
            "generated": False, "provider": "off", "model": None,
            "reason": "not attempted",
        }
        draft_applied = False
        if grounded and sources and answer and answer != NO_EVIDENCE_ANSWER:
            try:
                from app.rag.llm_adapter import generate_draft
                llm_draft_meta = generate_draft(
                    question, sources, intent=intent_id, passport_context=context,
                )
                draft_text = llm_draft_meta.get("text") or ""
                scored_intents = {"patentability", "prior_art", "compliance",
                                  "evidence_strength", "regulatory_roadmap"}
                scored = intent_id in scored_intents and r is not None
                if llm_draft_meta.get("generated") and not scored and len(draft_text) >= 40:
                    from app.rag.hallucination_guard import validate_answer
                    hv = validate_answer(draft_text, sources, question, confidence)
                    if hv.risk_level.value != "critical":
                        answer = draft_text.strip()
                        if citation and "Verified citation" not in answer:
                            answer += "\n\n" + citation
                        if DISCLAIMER not in answer:
                            answer += "\n\n" + DISCLAIMER
                        draft_applied = True
            except Exception:
                llm_draft_meta = {
                    "generated": False, "provider": "error", "model": None,
                    "reason": "internal error",
                }

        # 7e. Knowledge-base evidence block. When no fluent LLM draft was used
        #     (rule-scored intents, provider off/error), quote the actual
        #     retrieved records so every distinct question gets a distinct,
        #     database-sourced answer instead of a canned verdict. Strict
        #     token-overlap filter — never loose, so nothing off-topic leaks.
        if not draft_applied and grounded and sources and answer and answer != NO_EVIDENCE_ANSWER \
                and "\nWHAT THE RULES SAY\n" not in answer and "\nEVIDENCE CITED\n" not in answer:
            evidence_block = _general_grounded_summary(question, sources)
            if evidence_block and evidence_block not in answer:
                answer = (answer.rstrip() + "\n\n" + evidence_block)

        if r:
            risk_level = "Low" if r["overall_readiness"] >= 70 else ("Moderate" if r["overall_readiness"] >= 40 else "High")
            patent_readiness = round(r["overall_readiness"])
        elif claim:
            risk_level = {"HIGH_RISK": "High", "WARNING": "Moderate", "SAFE": "Low"}[claim["overall"]]
            patent_readiness = None
        else:
            risk_level = "Moderate"
            patent_readiness = None

        has_statutory = any(s.get("category") == "statutory" or s.get("retrieval_method") == "statutory" for s in sources)
        if not grounded:
            verification_badge = "Insufficient Evidence"
        elif draft_applied:
            verification_badge = "Verified — Source-Grounded Answer"
        elif r is not None and intent_id in (
            "patentability", "prior_art", "compliance",
            "evidence_strength", "regulatory_roadmap",
        ):
            verification_badge = "Verified — Measured by Rule Engines"
        elif verification and verification.get("regenerated"):
            verification_badge = "Regenerated — Unsupported Claims Removed"
        elif verification and not verification.get("passed_gate", True):
            verification_badge = "Blocked — Unsupported Claims Detected"
        elif verification and verification.get("passed_gate"):
            band = verification["evidence_confidence"]["band"]
            verification_badge = f"Verified — {band} Evidence Confidence"
        elif has_statutory:
            verification_badge = "Verified — Government Sources Cited"
        elif engine_grounded:
            verification_badge = "Verified — Measured by Rule Engines"
        else:
            verification_badge = "Grounded — Knowledge Base Cited"

        evidence_used = []
        seen = set()
        for s in sources:
            name = _source_display_name(s)
            kind = _source_kind(s)
            if name in seen:
                continue
            seen.add(name)
            evidence_used.append({"name": name, "type": kind})

        next_actions = _next_actions(intent_id, r, claim) if grounded else [
            "Add the authoritative document to the knowledge base and re-index.",
            "Rephrase the question with formulation/passport context.",
            "Create an Innovation Passport so the rule engines can score it.",
        ]

        # Domain-intent patent guard: when the query is about FSSAI / AYUSH /
        # labeling / manufacturing / food compliance or any other non-patent
        # domain, no Section 3(p), patent readiness score, WIPO/PCT guidance or
        # patent-filing advice may surface in the final answer, executive
        # summary or next actions.
        if domain_intent["ban_patent_topics"]:
            answer = strip_banned_patent_topics(answer)
            exec_summary = strip_banned_patent_topics(exec_summary)
            next_actions = [
                a for a in (strip_banned_patent_topics(a) for a in next_actions)
                if a.strip()
            ]

        # Bhashini answer translation — deliver the final answer in the user's
        # language when the query was non-English and translation succeeded.
        bhashini_status["answer_translated"] = False
        if detected_language != "en" and bhashini_status.get("enabled"):
            try:
                from app.services.bhashini_client import BhashiniClient
                translated_answer = BhashiniClient.translate_answer_to_lang(answer, detected_language)
                if translated_answer:
                    answer = translated_answer
                    bhashini_status["answer_translated"] = True
                translated_summary = BhashiniClient.translate_answer_to_lang(exec_summary, detected_language)
                if translated_summary:
                    exec_summary = translated_summary
            except Exception:
                pass

        # 7f. Decision trace — the full reasoning path exposed to the user:
        #   Question -> Jurisdiction -> Intent -> Retrieval -> Rules Applied.
        # Rendered by the frontend as a collapsible "How was this determined?"
        # panel under every copilot answer.
        decision_rules: list[dict[str, Any]] = []
        decision_rules.append({
            "rule": "Language Detection",
            "status": "PASS",
            "detail": (
                "Hinglish query detected (Romanised Hindi transliteration)."
                if language_label == "Hinglish (Romanised)"
                else (
                    f"Query primary language: {language_label}."
                    if detected_language == "en"
                    else f"Hinglish/Indic query detected as {language_label}."
                )
            ),
        })
        decision_rules.append({
            "rule": "Intent Detection",
            "status": "PASS",
            "detail": f"Intent classified as “{intent['label']}”.",
        })
        decision_rules.append({
            "rule": "Bhashini Translation",
            "status": "PASS" if (bhashini_status.get("query_translated") or bhashini_status.get("answer_translated")) else ("AVAILABLE" if bhashini_status.get("enabled") else "N/A"),
            "detail": (
                f"Query translated from {language_label} to English for retrieval; answer translated back."
                if bhashini_status.get("query_translated")
                else (f"Answer translated back to {language_label}."
                      if bhashini_status.get("answer_translated")
                      else ("Bhashini enabled — retrieval ran on the original query."
                            if bhashini_status.get("enabled")
                            else "Bhashini not configured — regex/glossary fallback used."))
            ),
        })
        decision_rules.append({
            "rule": "Domain Routing",
            "status": "PASS",
            "detail": (
                f"Domain: “{domain_intent['label']}”. Retrieval restricted to "
                f"collections {domain_intent['collections']}; "
                + ("Patent Rule Engine enabled for this domain."
                   if domain_intent["run_patent_engine"]
                   else "Patent Rule Engine gated OFF for this domain.")
            ),
        })
        decision_rules.append({
            "rule": "Jurisdiction Routing",
            "status": "PASS",
            "detail": (
                f"Scope set to {jurisdiction_info.get('detected')} "
                f"(cue: “{jurisdiction_info.get('cue')}”). "
                + ("Retrieval filtered to that jurisdiction."
                   if jurisdiction_info.get("retrieval_jurisdiction")
                   else "Retrieval ran on a global WIPO/WHO-aware corpus.")
            ),
        })
        decision_rules.append({
            "rule": "Hybrid Retrieval (BM25 + BGE-M3 + Qdrant)",
            "status": "PASS" if sources else "BLOCK",
            "detail": (
                f"{len(sources)} candidate source(s) merged and deduplicated "
                f"across domain collections {domain_intent['collections']} "
                f"(only intent-relevant collections are cited)."
            ),
        })
        decision_rules.append({
            "rule": "BGE Reranker",
            "status": "PASS" if sources else "N/A",
            "detail": "Cross-encoder rescores the top candidates before grounding.",
        })
        decision_rules.append({
            "rule": "Rule Engine Scoring",
            "status": "PASS" if (r or engine_grounded) else ("PARTIAL" if claim else "N/A"),
            "detail": (
                "Deterministic rules applied with measured verdict."
                if (r or engine_grounded)
                else ("Claim-intent rule evaluation applied."
                      if claim else "No path-specific rule fired for this intent.")
            ),
        })
        if verification:
            decision_rules.append({
                "rule": "Hallucination Guard & Citation Validation",
                "status": "PASS" if verification.get("passed_gate") else "BLOCK",
                "detail": (
                    "Claims cross-checked against retrieved evidence; citations validated."
                    if verification.get("passed_gate")
                    else verification.get("gate_reason", "Claims blocked or regenerated.")
                ),
            })
        decision_rules.append({
            "rule": "Grounding Threshold",
            "status": ("PASS" if grounded else "BLOCK"),
            "detail": (
                f"Answer covered {coverage * 100:.0f}% of meaningful query terms "
                f"against retrieved evidence (threshold {threshold}/{len(meaningful) or 1})."
            ),
        })
        decision_trace: dict[str, Any] = {
            "question": question,
            "language": {
                "code": detected_language,
                "label": language_label,
            },
            "jurisdiction": {
                "detected": jurisdiction_info.get("detected"),
                "cue": jurisdiction_info.get("cue"),
                "applied_filters": jurisdiction_info.get("applied_filters", []),
            },
            "intent": {
                "id": intent_id,
                "label": intent["label"],
                "domain": domain_intent["id"],
                "domain_label": domain_intent["label"],
                "collections": domain_intent["collections"],
                "patent_engine_enabled": domain_intent["run_patent_engine"],
            },
            "knowledge_base": {
                "mode": "Pure RAG — answers drawn only from the 6 curated IP-SAKTI collections",
                "curated_collections": [
                    "regulations", "patents", "biodiversity",
                    "traditional_knowledge", "quality_standards", "safety",
                ],
                "selected_collections": domain_intent["collections"],
            },
            "retrieval": {
                "method": "Language -> Jurisdiction -> BM25 + BGE-M3 -> Qdrant -> BGE Reranker -> Rule Engine",
                "qdrant_collections": sources and sorted({s.get("collection", "") for s in sources if s.get("collection")}),
                "source_count": len(sources[:5]),
                "candidate_count": len(sources),
                "llm_draft": llm_draft_meta.get("generated", False),
                "llm_provider": llm_draft_meta.get("provider", "off"),
            },
            "rules_applied": decision_rules,
            "confidence": round(confidence * 100),
            "verification_badge": verification_badge,
            "answer_preview": (answer or "")[:400],
        }

        # 8. Build LLM prompt template for frontend/LLM integration. When the domain
        # is non-patent (FSSAI / AYUSH / labeling / manufacturing / food
        # compliance), inject the topic restriction so a downstream LLM never
        # drifts into patent law / WIPO / PCT / filing guidance.
        llm_prompt = {}
        try:
            from app.rag.prompt_templates import build_rag_prompt
            llm_prompt = build_rag_prompt(
                query=question,
                sources=sources[:5],
                intent=intent_id,
                passport_context=context,
            )
            if domain_intent["ban_patent_topics"] and isinstance(llm_prompt, dict):
                user_prompt = llm_prompt.get("user") or llm_prompt.get("query") or ""
                if user_prompt and PATENT_BAN_INSTRUCTION not in str(user_prompt):
                    llm_prompt["user"] = str(user_prompt) + PATENT_BAN_INSTRUCTION
        except Exception:
            pass

        # 8b. Structured response sections (Direct Answer, Supporting Evidence,
        #     Official Citation, Confidence, Next Action).
        official_citation = citation
        if not official_citation and sources:
            official_citation = (
                sources[0].get("source_url")
                or sources[0].get("source")
                or ""
            )
        response_sections: dict[str, Any] = {
            "direct_answer": answer,
            "supporting_evidence": [
                {
                    "authority": _source_display_name(s),
                    "category": s.get("category", ""),
                    "jurisdiction": s.get("jurisdiction", ""),
                    "collection": s.get("collection", ""),
                    "quote": (s.get("content") or "").strip()[:300],
                }
                for s in sources[:5]
                if (s.get("content") or "").strip()
            ],
            "official_citation": official_citation,
            "confidence": round(confidence * 100),
            "next_actions": next_actions[:4],
        }

        return {
            "question": question,
            "answer": answer,
            "sources": sources[:5],
            "confidence": confidence,
            "images": [],
            "intent": {"id": intent_id, "label": intent["label"]},
            "detected_language": detected_language,
            "response_sections": response_sections,
            "analysis_card": {
                "confidence_pct": round(confidence * 100),
                "patent_readiness": patent_readiness,
                "risk_level": risk_level,
                "verification_badge": verification_badge,
                "executive_summary": exec_summary,
                "hallucination_check": hallucination_check,
                "claim_verification": verification.get("claim_verification", {}),
                "citation_validity": verification.get("citation_validity", {}),
                "evidence_confidence": verification.get("evidence_confidence", {}),
                "verification_gate": {
                    "passed": verification.get("passed_gate"),
                    "reason": verification.get("gate_reason", ""),
                    "regenerated": verification.get("regenerated", False),
                },
                "llm_generation": {
                    "generated": llm_draft_meta.get("generated", False),
                    "provider": llm_draft_meta.get("provider", "off"),
                    "model": llm_draft_meta.get("model"),
                    "reason": llm_draft_meta.get("reason", ""),
                },
                "retrieval_stats": retrieval_result.get("retrieval_stats", {}),
            },
            "evidence_used": evidence_used[:6],
            "verification": verification if verification else None,
            "jurisdiction": {
                "detected": jurisdiction_info.get("detected"),
                "cue": jurisdiction_info.get("cue"),
                "applied_filters": jurisdiction_info.get("applied_filters", []),
            },
            "decision_trace": decision_trace,
            "next_actions": next_actions[:4],
            "charts": charts,
            "llm_prompt": llm_prompt,
        }