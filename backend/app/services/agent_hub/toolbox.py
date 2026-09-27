"""IP-SAKTI Agent Hub — Tool Router toolbox.

The Tool Router decides *which* tool an agent uses.  Tools are the only way
agents touch corpus/knowledge data; RAG is just one tool in this kit.  Every
tool returns a plain dict so the Execution Controller can trace which tool
produced which step.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from typing import Any

from app.services.ingredient_resolver import IngredientResolverService
from app.services.retrieval_engine import HybridRetrievalEngine

_KB = os.path.join(os.path.dirname(__file__), "..", "..", "knowledge")


def _load_json(name: str) -> Any:
    import json as _json

    path = os.path.join(_KB, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return _json.load(f)


# --------------------------------------------------------------------------- #
# corpus tools
# --------------------------------------------------------------------------- #
def vec_search(query: str, jurisdiction: str | None = None, top_k: int = 4, min_score: float = 1.0) -> list[dict[str, Any]]:
    """Hybrid lexical + authority-ranked retrieval (RAG as a *tool*)."""
    if not query or not query.strip():
        return []
    try:
        out = []
        for c in HybridRetrievalEngine.search_passages(query, jurisdiction=jurisdiction, top_k=top_k, min_score=min_score):
            out.append(
                {
                    "act_title": getattr(c, "act_title", ""),
                    "section_reference": getattr(c, "section_reference", ""),
                    "authority": getattr(c, "authority", ""),
                    "effective_date": getattr(c, "effective_date", ""),
                    "exact_passage": (getattr(c, "exact_passage", "") or "")[:500],
                    "source_url": getattr(c, "source_url", ""),
                    "authority_rank": getattr(c, "authority_rank", 1),
                }
            )
        return out
    except Exception:
        return []


def bm25_rank(query: str, documents: list[str], top_k: int = 3) -> list[dict[str, Any]]:
    """Lightweight BM25-style lexical ranker over in-memory documents."""
    query_tokens = set(re.findall(r"\w+", query.lower()))
    if not query_tokens or not documents:
        return []
    scored = []
    for i, doc in enumerate(documents):
        toks = re.findall(r"\w+", doc.lower())
        df = len(query_tokens & set(toks))
        if df == 0:
            continue
        # simplified BM25 (idf-ish): score by term overlap / length
        score = (df * 2.0) / (1.0 + 0.75 * (len(toks) / max(1, len(query_tokens))))
        scored.append((score, i, doc[:500]))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"rank": i + 1, "index": idx, "score": round(sc, 3), "snippet": text} for i, (sc, idx, text) in enumerate(scored[:top_k])]


# --------------------------------------------------------------------------- #
# knowledge tools
# --------------------------------------------------------------------------- #
def knowledge_ingredient(name: str) -> dict[str, Any]:
    """Resolve one raw ingredient name to its API monograph + bioresource entry."""
    resolved = None
    try:
        resolved = IngredientResolverService.resolve(name)
    except Exception:
        resolved = None
    if resolved is None:
        return {"raw_name": name, "resolved": False}

    bio = {}
    for b in _load_json("bioresource.json") or []:
        if b.get("canonical_id") == getattr(resolved, "canonical_id", None):
            bio = b
            break
    return {
        "raw_name": name,
        "resolved": True,
        "canonical_id": getattr(resolved, "canonical_id", None),
        "api_monograph_id": getattr(resolved, "api_monograph_id", None),
        "botanical_name": getattr(resolved, "accepted_botanical_name", None),
        "family": getattr(resolved, "family", None),
        "classical_therapeutic_uses": getattr(resolved, "classical_therapeutic_uses", None),
        "fssai_aahara_status": getattr(resolved, "fssai_aahara_status", "permitted"),
        "us_fda_ndi_status": getattr(resolved, "us_fda_ndi_status", "old_dietary_ingredient"),
        "canada_nhpid_status": getattr(resolved, "canada_nhpid_status", "monographed"),
        "conservation_status": bio.get("conservation_status", ""),
        "resolution_confidence": getattr(resolved, "resolution_confidence", 0.9),
    }


def semantic_match(query: str, candidates: list[str]) -> list[dict[str, Any]]:
    """Token-overlap semantic similarity — deterministic substitute for an embedding retriever."""
    scores = []
    for cand in candidates:
        q = set(re.findall(r"\w+", query.lower()))
        c = set(re.findall(r"\w+", cand.lower()))
        union = q | c
        sim = len(q & c) / len(union) if union else 0.0
        scores.append((sim, cand))
    scores.sort(key=lambda x: x[0], reverse=True)
    return [{"similarity": round(s, 3), "text": t[:300]} for s, t in scores if s > 0]


# --------------------------------------------------------------------------- #
# analysis tools
# --------------------------------------------------------------------------- #
_FEATURE_PATTERNS = r"(comprising|consisting of|including|wherein|characterized in that|composed of)\s*[:;,]?\s*"

def extract_features(description: str) -> list[str]:
    """Deterministic technical-claim feature extraction (patent parser tool)."""
    features: list[str] = []
    if not description:
        return features
    for part in re.split(_FEATURE_PATTERNS, description):
        part = part.strip().strip(".,;")
        if not part or len(part) < 3:
            continue
        splat = re.split(r"[,;]+", part)
        for seg in splat:
            seg = seg.strip()
            if 3 <= len(seg) <= 120:
                features.append(seg)
    if not features:
        features = [seg.strip() for seg in re.split(r"[,;]+", description) if len(seg.strip()) >= 3][:8]
    return features[:12]


def rule_signal(claim_text: str) -> dict[str, bool]:
    """Rule-engine pre-signals for claim wording (regulatory parser tool)."""
    text = (claim_text or "").lower()
    return {
        "curative": bool(re.search(r"\b(cure|treat|heal|prevent|disease|therapeutic|medicine|remedy)\b", text)),
        "therapeutic_purpose": bool(re.search(r"\b(cognitive|memory|sleep|stress|anxiety|immunity|digestion|energy|pain relief)\b", text)),
        "solvent": bool(re.search(r"\b(solvent|water|honey|ghee|milk|alcohol|kwath|decoction|hydro-?alcoholic)\b", text)),
        "function_claim": bool(re.search(r"\b(supports|improves|promotes|maintains|enhances)\b", text)),
        "structure_claim": bool(re.search(r"\b(comprising|consisting|composed of|obtained by process)\b", text)),
    }


def knowledge_graph_links(entity: str) -> list[dict[str, str]]:
    """Knowledge-graph tool: botanical -> family -> source links from monographs."""
    links: list[dict[str, str]] = []
    for mono in (_load_json("api_monographs.json") or []):
        bot = mono.get("botanical_name", "")
        fam = mono.get("family", "")
        if entity.lower() in bot.lower() or entity.lower() in (mono.get("canonical_id", "") or "").lower():
            links.append({"node": bot, "predicate": "family", "value": fam})
            links.append({"node": bot, "predicate": "api_monograph", "value": mono.get("api_monograph_id", "")})
            uses = mono.get("classical_therapeutic_uses") or []
            if uses:
                links.append({"node": bot, "predicate": "classical_use", "value": ", ".join(uses[:2])})
    return links[:6]


def trend_analyze(texts: list[str], top_k: int = 8) -> list[dict[str, Any]]:
    """Trend engine tool: keywords + co-occurrence frequency across sources."""
    counts: Counter = Counter()
    for text in texts:
        for w in re.findall(r"\b[a-zA-Z][a-zA-Z-]{3,}\b", (text or "").lower()):
            if w not in {"this", "that", "with", "from", "have", "were", "when", "into", "their", "also", "says", "said"}:
                counts[w] += 1
    return [{"term": term, "occurrences": n} for term, n in counts.most_common(top_k)]


def document_entities(text: str) -> dict[str, list[str]]:
    """Document Analyzer tool: structured section/entity extraction from text."""
    sections = re.split(r"(?im)^(#{1,3}\s*|(?:section|step|part)\s*\d+\s*[:-])", text)
    heads = []
    for i, seg in enumerate(sections):
        seg = seg.strip()
        if seg and (i % 2 == 1 or sections[max(0, i - 1)].strip().startswith(("#", "section", "step", "part"))):
            heads.append(seg[:80])
    entities = sorted({w.capitalize() for w in re.findall(r"\b[A-Z][a-zA-Z]+(?:-[A-Z][a-zA-Z]+)?\b", text) if len(w) > 4})[:12]
    percentages = re.findall(r"\b\d+(?:\.\d+)?\s?%|\b\d+(?:\.\d+)?\s?(mg|g|ml|µg|mcg)\b", text, re.I)
    return {"sections": heads[:6], "entities": entities, "measures": percentages[:8]}


def normalize_document(text: str) -> str:
    """OCR tool stub: normalise whitespace/case for downstream parsing."""
    cleaned = re.sub(r"[\r\n\t]+", " ", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


TOOL_CATALOG = [
    {"name": "vec_search", "kind": "corpus", "desc": "Hybrid RAG vector search over IP-SAKTI KB"},
    {"name": "bm25_rank", "kind": "corpus", "desc": "Lexical BM25 ranker over in-memory documents"},
    {"name": "knowledge_ingredient", "kind": "knowledge", "desc": "API monograph + bioresource resolution"},
    {"name": "semantic_match", "kind": "analysis", "desc": "Token-overlap similarity"},
    {"name": "extract_features", "kind": "analysis", "desc": "Technical claim feature parser"},
    {"name": "rule_signal", "kind": "analysis", "desc": "Rule-engine claim-wording signals"},
    {"name": "knowledge_graph_links", "kind": "knowledge", "desc": "Botanical -> family -> source graph"},
    {"name": "trend_analyze", "kind": "analysis", "desc": "Keyword/trend frequency engine"},
    {"name": "document_entities", "kind": "analysis", "desc": "Document section/entity extractor"},
    {"name": "normalize_document", "kind": "pipeline", "desc": "OCR text normalisation"},
]


def route_tools(agent_slug: str) -> list[str]:
    """Tool Router: decide which tools an agent may use (first be only)."""
    table = {
        "triz": ["vec_search", "knowledge_graph_links", "semantic_match"],
        "quick_research": ["vec_search", "trend_analyze", "bm25_rank", "knowledge_ingredient", "knowledge_graph_links"],
        "find_solutions": ["vec_search", "knowledge_ingredient", "semantic_match"],
        "novelty_search": ["vec_search", "extract_features", "semantic_match", "bm25_rank"],
        "fto_search": ["vec_search", "extract_features", "semantic_match"],
        "design_fto": ["vec_search", "semantic_match"],
        "patent_drafting": ["extract_features", "vec_search", "rule_signal"],
        "invention_disclosure": ["document_entities", "normalize_document"],
        "office_action_response": ["vec_search", "rule_signal", "extract_features"],
        "essentiality_claim_chart": ["extract_features", "vec_search"],
        "tdoc_novelty_search": ["vec_search", "extract_features", "semantic_match"],
        "document_analyzer": ["normalize_document", "document_entities", "vec_search"],
        "lca_biotherapeutic": ["vec_search", "semantic_match"],
        "lca_small_molecule": ["vec_search", "semantic_match"],
        "sar_data_extraction": ["document_entities", "vec_search"],
        "antibody_target_predictor": ["vec_search", "semantic_match"],
        "markush_drafting": ["extract_features", "semantic_match"],
        "formulation": ["knowledge_ingredient", "vec_search", "knowledge_graph_links", "rule_signal"],
        "materials_find_solutions": ["vec_search", "knowledge_ingredient", "semantic_match"],
    }
    return table.get(agent_slug, ["vec_search"])