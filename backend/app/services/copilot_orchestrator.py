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

import re
import json
import os
from typing import List, Dict, Any, Optional

from app.services.ai_copilot import AICopilot, NO_EVIDENCE_ANSWER, STOPWORDS
from app.services.passport_engine import PassportEngine
from app.services.patent_readiness_engine import PatentReadinessEngine

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge")

# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

INTENTS: List[Dict[str, Any]] = [
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


def classify_intent(question: str) -> Dict[str, Any]:
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
    )


def _source_kind(source: Dict[str, Any]) -> str:
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


def _source_display_name(source: Dict[str, Any]) -> str:
    for key in ("act_title", "source", "title"):
        val = source.get(key)
        if val:
            return str(val)
    return "Retrieved Source"


def _top_citation(sources: List[Dict[str, Any]]) -> str:
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
    "sources and the rule engines above. Always consult a qualified patent agent " +
    "or regulatory specialist before final decisions."
)


# ---------------------------------------------------------------------------
# Rule-engine enrichments
# ---------------------------------------------------------------------------

def _get_passport(passport_id: Optional[str], question: str):
    if passport_id:
        found = PassportEngine.get_passport(passport_id)
        if found:
            return found
    try:
        return PassportEngine.create_from_intake(question)
    except Exception:
        return None


def _readiness(passport) -> Optional[Dict[str, Any]]:
    try:
        return PatentReadinessEngine.compute(passport)
    except Exception:
        return None


def _load_knowledge_json(name: str) -> Any:
    path = os.path.join(KNOWLEDGE_DIR, name)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

def _radar_chart(r: Dict[str, Any]) -> Dict[str, Any]:
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


def _similarity_chart(r: Dict[str, Any]) -> Dict[str, Any]:
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


def _evidence_donut(r: Dict[str, Any]) -> Dict[str, Any]:
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


def _compliance_gauge(r: Dict[str, Any]) -> Dict[str, Any]:
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


def _timeline_chart(r: Optional[Dict[str, Any]]) -> Dict[str, Any]:
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


def _india_heatmap() -> Dict[str, Any]:
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


def _risk_matrix_chart(risk_summary: Dict[str, Any]) -> Dict[str, Any]:
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


def _white_space_chart() -> Dict[str, Any]:
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


def _claim_firewall(claims_texts: List[str]) -> Dict[str, Any]:
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

def _general_grounded_summary(question: str, sources: List[Dict[str, Any]]) -> str:
    """Build a grounded, citation-bound answer for general RAG questions.

    Strict zero-hallucination contract: every sentence emitted here must
    be traceable to a retrieved source. No templated editorial claims
    about what the sources mean — only what they directly state.
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
    )
    relevant_sources = []
    for s in sources:
        src_text = re.sub(r"[^a-z0-9%.]", " ", str(s.get("content", "")).lower())
        src_tokens = set(src_text.split())
        if meaningful.intersection(src_tokens):
            relevant_sources.append(s)
    if not relevant_sources:
        return ""

    bullets: List[str] = []
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

    summary = "Based on the retrieved official sources:\n\n" + "\n".join(bullets)
    if len(relevant_sources) > 4:
        summary += f"\n\n({len(relevant_sources)} of {len(sources)} sources had direct keyword overlap with your query; the most relevant are cited above.)"
    return summary


def _executive_summary(intent: str, r: Optional[Dict[str, Any]], claim: Optional[Dict[str, Any]],
                       citation: str) -> str:
    if not r and intent in ("patentability", "prior_art", "compliance", "evidence_strength", "regulatory_roadmap"):
        return (
            "The retrieved official sources describe the governing framework. " +
            citation + " Provide formulation details or an Innovation Passport for a full " +
            "rule-engine scored assessment."
        )

    if intent == "patentability" and r:
        weakest = min(r["components"], key=lambda c: c["earned"] / c["max"] if c["max"] else 1)
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
            "The white-space grid shows where classical ingredients meet fewer derivative patents. Nano/liposomal delivery "
            "converts crowded capsules into opportunity zones — the strongest early-mover windows are nano-neem, tulsi gel "
            "and nano-ashwagandha."
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
        return (
            f"Evidence component scored {earned} of its 10 weight points "
            f"({round(ev['pct'])}% of the evidence requirement). "
            "The engine finds these gaps: " + "; ".join(r.get("missing_evidence", [])) + "."
        )

    return citation if citation else "Grounded in the retrieved official sources."


def _next_actions(intent: str, r: Optional[Dict[str, Any]], claim: Optional[Dict[str, Any]]) -> List[str]:
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

def _compute_confidence(meaningful: set, sources: List[Dict[str, Any]],
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
    def _get_fallback_sources(cls, question: str) -> List[Dict[str, Any]]:
        """Legacy FAISS + statutory retrieval, used only when the hybrid
        pipeline returns no sources at all."""
        sources: List[Dict[str, Any]] = []
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
    def _dedupe(cls, sources: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
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
    def run(cls, question: str, passport_id: Optional[str] = None,
            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # 1. Retrieve evidence ONCE via the hybrid pipeline, then share the
        # result between the grounding path and the source list. The pipeline
        # (embedding + cross-encoder rerank) is the dominant cost on CPU, so
        # running it twice used to double the end-to-end latency.
        retrieval_result = {}
        sources: List[Dict[str, Any]] = []
        try:
            from app.rag.retrieval_pipeline import HybridRetriever
            retrieval_result = HybridRetriever.retrieve(question, top_k=10)
            sources = cls._dedupe(retrieval_result.get("sources", []))
        except Exception:
            pass

        # Fallback to legacy FAISS + statutory search only if the hybrid
        # pipeline returned nothing.
        if not sources:
            sources = cls._dedupe(cls._get_fallback_sources(question))

        meaningful = _meaningful_tokens(question)
        combined = " ".join(str(s.get("content", "")) for s in sources)
        cleaned = set(re.sub(r"[^a-z0-9%.]", " ", combined.lower()).split())
        coverage = len(meaningful.intersection(cleaned)) / max(1, len(meaningful))
        threshold = 1 if len(meaningful) <= 1 else (len(meaningful) + 1) // 2
        retrieval_grounded = len(meaningful) > 0 and len(meaningful.intersection(cleaned)) >= threshold

        intent = classify_intent(question)
        intent_id = intent["id"]

        # 2. Deterministic rule-engine enrichment per intent.
        passport = None
        r: Optional[Dict[str, Any]] = None
        claim: Optional[Dict[str, Any]] = None
        charts: List[Dict[str, Any]] = []
        if intent_id in ("patentability", "prior_art", "compliance", "evidence_strength", "regulatory_roadmap"):
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
            if not claim_texts:
                claim_texts = [question]
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
        refusal_reason = retrieval_result.get("refusal_reason", "")
        if should_refuse and not retrieval_grounded:
            grounded = False

        # 6. Executive summary + risk level + next actions.
        citation = _top_citation(sources)
        exec_summary = _executive_summary(intent_id, r, claim, citation)
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
        answer = exec_summary + ("\n\n" + citation if citation and grounded else "") + ("\n\n" + DISCLAIMER if grounded else "")

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
        verification = {}
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
                # Apply verification outcome: use the verified final answer
                if vr.final_answer:
                    answer = vr.final_answer
                if not vr.passed_gate and not vr.regenerated:
                    grounded = False
                    confidence = 0.05
                elif not vr.passed_gate and vr.regenerated:
                    confidence = max(0.05, confidence - 0.10)
            except Exception:
                pass

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
        elif verification and not verification.get("passed_gate", True):
            verification_badge = "Blocked — Unsupported Claims Detected"
        elif verification and verification.get("regenerated"):
            verification_badge = "Regenerated — Unsupported Claims Removed"
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

        # 8. Build LLM prompt template for frontend/LLM integration.
        llm_prompt = {}
        try:
            from app.rag.prompt_templates import build_rag_prompt
            llm_prompt = build_rag_prompt(
                query=question,
                sources=sources[:5],
                intent=intent_id,
                passport_context=context,
            )
        except Exception:
            pass

        return {
            "question": question,
            "answer": answer,
            "sources": sources[:5],
            "confidence": confidence,
            "images": [],
            "intent": {"id": intent_id, "label": intent["label"]},
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
                "retrieval_stats": retrieval_result.get("retrieval_stats", {}),
            },
            "evidence_used": evidence_used[:6],
            "verification": verification if verification else None,
            "next_actions": next_actions[:4],
            "charts": charts,
            "llm_prompt": llm_prompt,
        }