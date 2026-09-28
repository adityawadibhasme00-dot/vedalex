"""
Zero-Delay Multi-Layer AI Orchestration (VEDALEX | IP-SAKTI SAHAYAK).

Implements the judge-facing answer pipeline as a strict, priority-ordered
cascade. Every query is routed and every layer hands structured, fully
provenanced evidence to the next — citations are preserved from the moment a
document is touched until the answer is emitted:

    Layer 1 · Intent Router
              classify domain + surface intent + language + jurisdiction
              BEFORE any retrieval, and derive the ONLY collections allowed.
    Layer 2 · Hybrid RAG  (BM25 + BGE-M3 + Qdrant + BGE Reranker)
              hybrid retrieve restricted to intent-relevant collections.
    Layer 3 · Knowledge Graph fallback
              entity lookup across the canonical graph (monographs, Acts,
              authorities) when hybrid confidence is weak.
    Layer 4 · Rule Engine fallback
              deterministic rule engines (Patent Readiness, Claim Firewall,
              dataset-backed intents) when evidence is still weak.
    Layer 5 · MCP live retrieval
              official-website tools (IP India, TKDL, WIPO, AYUSH, FSSAI,
              CDSCO, NBA, FDA, WHO) bridge through a tool registry.
    Layer 6 · Citation Voting
              every candidate source votes on the answer; High Confidence
              requires at least TWO independent official sources.
    Layer 7 · LLM response generation
              grounded drafting ONLY from voted evidence, then claim-level
              verification; safe abstention when no verified evidence exists.

Enforced production rules:
  - Never answer from model memory: the LLM draft is only used after a
    hallucination guard pass and is blocked when evidence is insufficient.
  - Route queries before retrieval and search ONLY relevant collections.
  - Confidence thresholds auto-switch to the next fallback layer.
  - At least two supporting official sources are required for High Confidence.
  - Safe abstention (NO_EVIDENCE_ANSWER) when verified evidence cannot be
    established — not a guess dressed as an answer.
"""

import logging
import os
import re
from typing import Any

from app.services import copilot_orchestrator as co
from app.services.ai_copilot import NO_EVIDENCE_ANSWER
from app.services.copilot_orchestrator import (
    DISCLAIMER,
    HINGLISH_MARKERS,
    LANGUAGE_NAMES,
    _claim_firewall,
    _compliance_gauge,
    _compute_confidence,
    _evidence_donut,
    _executive_summary,
    _general_grounded_summary,
    _india_heatmap,
    _load_knowledge_json,
    _meaningful_tokens,
    _next_actions,
    _radar_chart,
    _rank_by_authority,
    _risk_matrix_chart,
    _similarity_chart,
    _source_display_name,
    _source_kind,
    _timeline_chart,
    _top_citation,
    _white_space_chart,
    classify_intent,
    detect_jurisdiction,
)
from app.services.intent_classifier import (
    PATENT_BAN_INSTRUCTION,
    classify_domain_intent,
    filter_sources_by_domain,
    strip_banned_patent_topics,
)
from app.services.jurisdiction_router import (
    filter_sources_by_jurisdiction,
    resolve_jurisdiction,
)
from app.services.multilingual_nlp import MultilingualNLPEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Layer gates / thresholds
# ---------------------------------------------------------------------------

#: Below this confidence the orchestrator MUST switch to the next fallback layer.
FALLBACK_THRESHOLD = float(os.environ.get("IPSAKTI_FALLBACK_THRESHOLD", "0.55"))

#: Minimum fraction of meaningful query tokens that must appear in evidence.
GROUNDING_MIN_COVERAGE = float(os.environ.get("IPSAKTI_MIN_COVERAGE", "0.5"))

#: Independent official sources needed to label an answer "High Confidence".
MIN_OFFICIAL_SOURCES_FOR_HIGH = int(
    os.environ.get("IPSAKTI_MIN_OFFICIAL_SOURCES", "2")
)

#: Highest confidence a given vote tier may reach.
CONFIDENCE_CAP_BY_VOTES = {0: 0.35, 1: 0.60, 2: 0.90}

HIGH_CONFIDENCE_BAR = 0.60

# Official evidence categories (from app/rag/kb.py folder metadata) that vote
# as "official" in the citation vote.
OFFICIAL_CATEGORIES = {
    "statutory", "official", "government", "regulatory", "patent statute",
    "pharmacopoeia", "tkdl", "international ip", "who",
}


# ---------------------------------------------------------------------------
# MCP tool registry — Layer 5 bridge to live official retrieval.
# ---------------------------------------------------------------------------

def _mcp_fetch_official_sources(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """MCP tool: fetch live official-website passages (network-guarded)."""
    from app.rag.official_web_retriever import fetch_official_sources
    return fetch_official_sources(query, top_k=top_k) or []


MCP_TOOLS: dict[str, dict[str, Any]] = {
    "fetch_official_sources": {
        "name": "fetch_official_sources",
        "description": (
            "Live retrieve official government / intergovernmental passages "
            "from a whitelist of domains (IP India, TKDL, WIPO, AYUSH, FSSAI, "
            "CDSCO, NBA, PIB, FDA, Health Canada, WHO)."
        ),
        "call": _mcp_fetch_official_sources,
        "returns": "list of citable source dicts with provenance metadata",
    },
}

MCP_ENABLED = os.environ.get("IPSAKTI_ENABLE_LIVE_WEB", "0") == "1" or (
    os.environ.get("IPSAKTI_LIVE_WEB", "1").strip().lower()
    not in ("0", "false", "off", "no")
)


# ---------------------------------------------------------------------------
# Citation voting helpers (Layer 6)
# ---------------------------------------------------------------------------

def _is_official_source(source: dict[str, Any]) -> bool:
    """A source votes as 'official' when it is statutory / government /
    pharmacopoeia / TKDL / WHO material, carries a high-authority rank, or
    points at a whitelisted official domain."""
    if source.get("retrieval_method") == "statutory":
        return True
    if source.get("category") in OFFICIAL_CATEGORIES:
        return True
    try:
        level = int(source.get("authority_level") or source.get("authority_rank") or 3)
    except (TypeError, ValueError):
        level = 3
    if level <= 2:
        return True
    url = str(source.get("source_url") or "").lower()
    if url:
        try:
            from app.rag.official_web_retriever import OFFICIAL_SOURCES
            if any(src["domain"].lower() in url for src in OFFICIAL_SOURCES):
                return True
        except Exception:
            pass
    return False


def _source_identity(source: dict[str, Any]) -> str:
    """Identity of the underlying document — two chunks of the same document
    count as ONE independent source in the citation vote."""
    return (
        source.get("source_url")
        or source.get("source")
        or source.get("act_title")
        or source.get("title")
        or ""
    )


def _source_has_provenance(source: dict[str, Any]) -> bool:
    return bool(_source_identity(source)) and bool(
        source.get("content") or source.get("section")
    )


def vote_citations(sources: list[dict[str, Any]]) -> dict[str, Any]:
    """Run the citation vote over all candidate sources.

    Each source casts a ballot:
      accepted  — has full provenance AND is an official/statutory document
      secondary — has provenance but is not an official document
      rejected  — no usable provenance (cannot be cited)

    Returns the vote tally, the list of independent official authorities and
    the confidence cap implied by the official vote count.
    """
    rows: list[dict[str, Any]] = []
    official_identities: set = set()
    for s in sources:
        prov = _source_has_provenance(s)
        if not prov:
            vote, note = "rejected", "No usable citation provenance"
        elif _is_official_source(s):
            vote, note = "accepted", "Official / statutory source"
            official_identities.add(_source_identity(s))
        else:
            vote, note = "secondary", "Retrievable but not an official source"
        rows.append({
            "source": _source_identity(s) or (s.get("title") or s.get("act_title") or "unnamed"),
            "vote": vote,
            "is_official": _is_official_source(s),
            "authority": s.get("authority", ""),
            "jurisdiction": s.get("jurisdiction", ""),
            "note": note,
        })

    official_votes = len(official_identities)
    cap = CONFIDENCE_CAP_BY_VOTES.get(
        official_votes, min(CONFIDENCE_CAP_BY_VOTES.values())
    )
    # Two+ independent official sources are required to ever reach High.
    if official_votes >= MIN_OFFICIAL_SOURCES_FOR_HIGH:
        tier = "HIGH"
    elif official_votes == 1:
        tier = "MEDIUM"
    else:
        tier = "LOW"
    return {
        "tier": tier,
        "official_votes": official_votes,
        "required_for_high": MIN_OFFICIAL_SOURCES_FOR_HIGH,
        "independent_official_sources": sorted(official_identities)[:10],
        "confidence_cap": cap,
        "high_confidence": official_votes >= MIN_OFFICIAL_SOURCES_FOR_HIGH and cap >= HIGH_CONFIDENCE_BAR,
        "required_high_confidence": (
            official_votes >= MIN_OFFICIAL_SOURCES_FOR_HIGH and cap >= HIGH_CONFIDENCE_BAR
        ),
        "ballots": rows,
    }


# ---------------------------------------------------------------------------
# Layer 3 — Knowledge Graph retrieval fallback
# ---------------------------------------------------------------------------

GRAPH_OFFICIAL_CATEGORIES = {"regulation": "statutory", "monograph": "pharmacopoeia"}


def knowledge_graph_retrieve(question: str, limit: int = 6) -> list[dict[str, Any]]:
    """Resolve question entities against the canonical knowledge graph and
    return source-shaped evidence dicts (regulations, monographs, authorities)
    with the graph provenance carried in retrieval_method="knowledge_graph"."""
    try:
        from app.rag.knowledge_graph import build_graph
    except Exception:
        return []

    try:
        graph = build_graph(force=False)
    except Exception:
        return []

    question.lower()
    tokens = {
        t for t in _meaningful_tokens(question)
        if len(t) >= 3
    }
    if not tokens:
        return []

    sources: list[dict[str, Any]] = []
    seen_docs: set = set()

    for node in graph.get("nodes") or []:
        ntype = node.get("type", "")
        if ntype not in ("regulation", "monograph", "ingredient", "authority", "botanical"):
            continue
        hay = " ".join([node.get("name", ""), *node.get("aliases", [])]).lower()
        hit = any(tok in hay for tok in tokens)
        if not hit:
            continue
        name = node.get("name", "")
        identity = f"{ntype}:{name}"
        if identity in seen_docs:
            continue
        seen_docs.add(identity)

        attrs = node.get("attrs") or {}
        statuses = node.get("statuses") or []
        content_parts = [name]
        if attrs.get("family"):
            content_parts.append(str(attrs["family"]))
        if attrs.get("keywords"):
            content_parts.append(", ".join(attrs["keywords"]))
        if statuses:
            content_parts.append(
                "; ".join(
                    f"{st.get('market')} — {st.get('status')}"
                    for st in statuses[:4]
                )
            )
        content = ". ".join(p for p in content_parts if p).strip()

        authority = node.get("authority") or "IP-SAKTI Canonical Graph"
        jurisdiction = node.get("jurisdiction") or ""
        sources.append({
            "content": content[:1200],
            "source": name,
            "title": name,
            "source_url": "",
            "category": GRAPH_OFFICIAL_CATEGORIES.get(ntype, "official"),
            "collection": "",
            "act_title": name if ntype == "regulation" else str(attrs.get("api_monograph_id") or name),
            "section": attrs.get("section") or "",
            "effective_date": attrs.get("effective_date") or "",
            "authority": authority,
            "jurisdiction": jurisdiction,
            "authority_level": 2 if ntype in ("regulation", "monograph") else 3,
            "retrieval_method": "knowledge_graph",
            "score": 0.62,
        })
        if len(sources) >= limit:
            break

    return sources


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class MultiLayerOrchestrator:
    """Zero-Delay Multi-Layer AI Orchestrator — the chat entry point."""

    @classmethod
    def _dedupe(cls, sources: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
        return co.AICopilotOrchestrator._dedupe(sources, limit=limit)

    @classmethod
    def _get_legacy_fallback(cls, question: str) -> list[dict[str, Any]]:
        try:
            return co.AICopilotOrchestrator._get_fallback_sources(question)
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Layer 2 — Hybrid RAG
    # ------------------------------------------------------------------
    @classmethod
    def _layer_hybrid_rag(cls, question: str, domains: list[str],
                          jurisdiction: str | None) -> dict[str, Any]:
        from app.rag.retrieval_pipeline import HybridRetriever
        try:
            return HybridRetriever.retrieve(
                question,
                top_k=10,
                jurisdiction=jurisdiction,
                domains=domains or None,
            )
        except Exception as exc:
            logger.warning("Layer 2 Hybrid RAG failed: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Layer 4 — Rule engine fallback
    # ------------------------------------------------------------------
    @classmethod
    def _layer_rule_engine(cls, question: str, passport_id: str | None,
                           intent_id: str, domain_intent: dict[str, Any],
                           charts: list[dict[str, Any]]) -> dict[str, Any]:
        """Run the deterministic rule engines considered a fallback evidence
        layer. Mirrors the existing patent-readiness / claim-firewall /
        dataset-backed scoring so the multi-layer pipeline never invents data:
        a scored result is only trusted when anchored to a REAL passport."""
        passport = None
        r: dict[str, Any] | None = None
        claim: dict[str, Any] | None = None
        grounded = False

        from app.services.passport_engine import PassportEngine
        from app.services.patent_readiness_engine import PatentReadinessEngine

        patent_scoring_intents = ("patentability", "prior_art", "compliance",
                                  "evidence_strength", "regulatory_roadmap")
        if intent_id in patent_scoring_intents and domain_intent["run_patent_engine"]:
            if passport_id:
                try:
                    passport = PassportEngine.get_passport(passport_id)
                except Exception:
                    passport = None
            r = PatentReadinessEngine.compute(passport) if passport else None
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
            grounded = grounded or (r is not None and bool(passport_id))

        elif intent_id == "marketing_claim":
            claim_texts = []
            if passport_id:
                try:
                    from app.services.passport_engine import PassportEngine
                    p = PassportEngine.get_passport(passport_id)
                    if p:
                        claim_texts = list(p.proposed_claims)
                except Exception:
                    pass
            if claim_texts:
                claim = _claim_firewall(claim_texts)
                charts.append(_risk_matrix_chart(claim))
            grounded = grounded or (claim is not None and bool(passport_id))

        elif intent_id == "botanical_origin":
            if _load_knowledge_json("india_origin.json") is not None:
                charts.append(_india_heatmap())
                grounded = True
        elif intent_id == "white_space":
            ws = _white_space_chart()
            if ws:
                charts.append(ws)
                grounded = True

        return {
            "passport": passport,
            "readiness": r,
            "claim": claim,
            "engine_grounded": grounded,
            "charts": charts,
        }

    # ------------------------------------------------------------------
    # Layer 5 — MCP live retrieval
    # ------------------------------------------------------------------
    @classmethod
    def _layer_mcp_live(cls, question: str) -> dict[str, Any]:
        if not MCP_ENABLED:
            return {
                "sources": [], "enabled": False,
                "reason": "MCP live retrieval disabled (IPSAKTI_ENABLE_LIVE_WEB=0)",
            }
        try:
            tool = MCP_TOOLS["fetch_official_sources"]
            live = tool["call"](question, top_k=3)
            return {"sources": live, "enabled": True, "reason": ""}
        except Exception as exc:
            logger.warning("Layer 5 MCP live retrieval failed: %s", exc)
            return {"sources": [], "enabled": True, "reason": str(exc)[:200]}

    # ------------------------------------------------------------------
    # Grounding / confidence
    # ------------------------------------------------------------------
    @classmethod
    def _compute_grounding(cls, question: str,
                           sources: list[dict[str, Any]]) -> dict[str, Any]:
        meaningful = _meaningful_tokens(question)
        combined = " ".join(str(s.get("content", "")) for s in sources)
        cleaned = set(
            re.sub(r"[^a-z0-9%.]", " ", combined.lower()).split()
        ) if combined else set()
        coverage = len(meaningful.intersection(cleaned)) / max(1, len(meaningful))
        threshold = 1 if len(meaningful) <= 1 else (len(meaningful) + 1) // 2
        grounded = (
            len(meaningful) > 0
            and len(meaningful.intersection(cleaned)) >= threshold
        )
        boundary = max(1, len(meaningful))
        ratio_grounded = (
            len(meaningful.intersection(cleaned)) / boundary >= GROUNDING_MIN_COVERAGE
        )
        return {
            "meaningful": meaningful,
            "coverage": coverage,
            "threshold": threshold,
            "retrieval_grounded": grounded,
            "ratio_grounded": ratio_grounded,
        }

    # ------------------------------------------------------------------
    # STEP 2 · Product Classification Wizard + STEP 8 · Human Escalation
    # ------------------------------------------------------------------
    @classmethod
    def _assistant_enrichment(
        cls,
        question: str,
        passport_id: str | None,
        context: dict[str, Any] | None,
        confidence: float,
        risk_level: str,
    ) -> dict[str, Any]:
        """Run the Product Classification Wizard (STEP 2) and the Human
        Escalation recommendation (STEP 8) alongside the RAG answer.

        Classification inputs are drawn from the real Innovation Passport when
        one is attached; otherwise light hints (declared use, ingredients) are
        extracted from the question. A passport is never fabricated from the
        bare query — when nothing is declared the classifier returns the
        'unresolved' family rather than inventing product facts.
        """
        from app.services.escalation_service import should_escalate
        from app.services.product_classifier import ProductClassifier

        product_name = ""
        product_form = ""
        dosage_form = ""
        intended_use = ""
        claims: list[str] = []
        ingredients: list[str] = []
        process_description = ""

        # Attach real passport facts when available (never fabricated).
        if passport_id:
            try:
                from app.services.passport_engine import PassportEngine
                passport = PassportEngine.get_passport(passport_id)
                if passport is not None:
                    product_name = getattr(passport, "case_title", "") or ""
                    product_form = getattr(passport, "product_form", "") or ""
                    dosage_form = getattr(passport, "dosage_form", "") or ""
                    intended_use = getattr(passport, "intended_use", "") or ""
                    claims = list(getattr(passport, "proposed_claims", []) or [])
                    ingredients = [
                        ing.raw_name for ing in (getattr(passport, "ingredients", []) or [])
                    ]
                    process_description = getattr(passport, "process_description", "") or ""
            except Exception:
                pass

        # Light query hints only when no passport is attached — enough to run
        # the classifier's declared-use intent branch without inventing facts.
        declared_use = ""
        q = (question or "").lower()
        if not intended_use:
            if any(k in q for k in ("cosmetic", "बालों", "त्वचा", "skin", "beauty", "सौंदर्य")):
                declared_use = "cosmetic"
            elif any(k in q for k in ("food", "aahar", "आहार", "supplement", "सप्लीमेंट", "nutrition", "पोषण", "health drink")):
                declared_use = "dietary"
            elif any(k in q for k in ("treat", "cure", "medicine", "दवा", "रोग", "diabetes", "मधुमेह", "blood sugar", "syrup", "tablet")):
                declared_use = "medicine"
            elif any(k in q for k in ("wellness", "immunity", "प्रतिरक्षा", "tonic")):
                declared_use = "wellness"
        if not product_form:
            for form in ("syrup", "tonic", "tablet", "capsule", "vati", "churna", "powder",
                         "oil", "taila", "cream", "ointment", "gel", "softgel", "kwatha",
                         "kashayam", "ghrita", "avaleha", "lozenge", "drop", "elixir"):
                if form in q:
                    product_form = form
                    break
        if not ingredients:
            for herb in ("neem", "निंब", "haldi", "turmeric", "हल्दी", "ashwagandha", "अश्वगंधा",
                         "tulsi", "तुलसी", "amla", "आँवला", "giloy", "गिलोय", "brahmi", "brāhmī"):
                if herb in q:
                    ingredients.append(herb.split(" ")[0].title())
            ingredients = list(dict.fromkeys(ingredients))

        classification = None
        try:
            resp = ProductClassifier.classify(
                product_name=product_name,
                product_form=product_form,
                dosage_form=dosage_form,
                intended_use=intended_use,
                claims=claims,
                ingredients=ingredients,
                process_description=process_description,
                passport_id=passport_id,
                declared_use=declared_use,
            )
            try:
                classification = resp.model_dump()
            except AttributeError:
                classification = resp.dict()
        except Exception:
            classification = None

        # STEP 8 — Human escalation recommendation (bilingual reasons).
        escalation = None
        if classification:
            requires_human_review = False
            for c in (classification.get("rule_validation") or []):
                if isinstance(c, dict) and c.get("status") in ("NOT_SATISFIED", "INSUFFICIENT"):
                    requires_human_review = True
                    break
            has_bio_resources = bool(ingredients) or bool(
                classification.get("ingredients")
            )
            try:
                esc = should_escalate(
                    classification=classification,
                    confidence=confidence,
                    requires_human_review=requires_human_review,
                    risk_level=risk_level,
                    has_bio_resources=has_bio_resources,
                    is_patent_question=any(
                        k in q for k in ("patent", "पेटेंट", "patentable", "3(p)", "3(पी)")
                    ),
                )
                escalation = esc.to_dict()
            except Exception:
                escalation = None

        classification_bilingual = None
        if classification:
            try:
                from app.services.escalation_service import classification_bilingual as _bil
                classification_bilingual = _bil(classification)
            except Exception:
                classification_bilingual = classification

        # Both envelopes carry the bilingual labels so the UI can read either
        # `product_classification` or `product_classification_bilingual`.
        labeled = classification_bilingual or classification
        return {
            "classification": labeled,
            "classification_bilingual": labeled,
            "escalation": escalation,
            "declared_use": declared_use,
        }

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    @classmethod
    def run(cls, question: str, passport_id: str | None = None,
            context: dict[str, Any] | None = None,
            retrieved_sources: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        flow: list[dict[str, Any]] = []
        charts: list[dict[str, Any]] = []

        # ----------------------- LAYER 1 · INTENT ROUTER -----------------------
        domain_intent = classify_domain_intent(question)
        surface_intent = classify_intent(question)
        intent_id = surface_intent["id"]
        jurisdiction_info = detect_jurisdiction(question, context)

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

        # ----- Jurisdiction Router (golden rule: never mix legal frameworks) ----
        # The toggle/`context.jurisdiction` wins. When no toggle and no keyword
        # cue exists, we CLARIFY instead of guessing a legal framework.
        juris_resolved = resolve_jurisdiction(question, context or {})
        if juris_resolved.get("clarification_needed"):
            clarification_q = (
                juris_resolved.get("clarification_question")
                or "Please choose 🇮🇳 India or 🌍 International so a single legal "
                "framework is applied to your question."
            )
            flow.append({
                "layer": "1 · Intent Router · Jurisdiction",
                "status": "CLARIFY",
                "detail": "No jurisdiction toggle and no legal-framework cue — "
                          "safe clarification requested before retrieval.",
            })
            abstention_reason = "jurisdiction clarification required"
            flow.append({
                "layer": "8 · Safe Abstention (clarify)",
                "status": "HOLD",
                "detail": "Refusing to guess a legal framework. Waiting for the "
                          "user to pick India 🇮🇳 or International 🌍.",
            })
            return {
                "question": question,
                "answer": clarification_q + (
                    "\n\nNo legal framework has been applied yet — this prevents "
                    "mixing India and International law. No official source was "
                    "retrieved or cited."
                ),
                "sources": [],
                "confidence": 0.02,
                "images": [],
                "intent": {"id": intent_id, "label": surface_intent["label"]},
                "detected_language": detected_language,
                "response_sections": {
                    "direct_answer": clarification_q,
                    "clarification_needed": True,
                    "options": ["🇮🇳 India Laws Only",
                                "🌍 International Laws Only"],
                    "official_sources_used": [],
                    "confidence": 2,
                    "jurisdiction": None,
                    "next_recommended_action": "Select a jurisdiction toggle",
                    "why_it_matters": "India and International legal frameworks "
                                      "must never be mixed in one answer.",
                    "disclaimer": DISCLAIMER,
                },
                "analysis_card": {"verification_badge": "Clarification needed"},
                "decision_trace": {
                    "jurisdiction": {"detected": None,
                                     "cue": "none",
                                     "mode": juris_resolved.get("mode")},
                    "pipeline": {
                        "name": "Zero-Delay Multi-Layer AI Orchestration",
                        "layer_flow": flow,
                        "layers": ["1 · Intent Router", "2 · Hybrid RAG",
                                   "3 · Knowledge Graph", "4 · Rule Engine",
                                   "5 · MCP live retrieval",
                                   "6 · Citation Voting",
                                   "7 · LLM response generation"],
                    },
                },
            }
        mode = juris_resolved["mode"]
        jurisdiction_info["mode"] = mode
        jurisdiction_info["framework"] = juris_resolved.get("label", mode)
        jurisdiction_info["resolved_via"] = juris_resolved.get("resolved_via")

        # Bhashini translation: when the user writes in an Indic language and the
        # Bhashini API is configured, translate the query to English so the hybrid
        # RAG / KG / rule-engine layers retrieve against the English legal corpus.
        bhashini_status: dict[str, Any] = {"enabled": False, "query_translated": False}
        retrieval_query = question
        try:
            from app.services.bhashini_client import BhashiniClient
            bhashini_status["enabled"] = bool(BhashiniClient.is_enabled())
            if detected_language != "en" and bhashini_status["enabled"]:
                translated = BhashiniClient.translate_query_to_english(
                    question, detected_language
                )
                if translated and str(translated).strip():
                    retrieval_query = str(translated).strip()
                    bhashini_status["query_translated"] = True
        except Exception:
            bhashini_status = {"enabled": False, "query_translated": False}

        flow.append({
            "layer": "1 · Intent Router",
            "status": "PASS",
            "detail": (
                f"Domain “{domain_intent['label']}” → collections "
                f"{domain_intent['collections']}; surface intent “{surface_intent['label']}”; "
                f"jurisdiction {jurisdiction_info.get('detected')} (cue: "
                f"{jurisdiction_info.get('cue')}); language {language_label}. "
                "Routing completed BEFORE retrieval."
            ),
        })

        # ------------------------- LAYER 2 · HYBRID RAG -------------------------
        sources: list[dict[str, Any]] = []
        retrieval_result: dict[str, Any] = {}
        if retrieved_sources:
            sources = cls._dedupe(retrieved_sources)
            layer2_status = "PASS"
            layer2_detail = (
                f"{len(sources)} pre-retrieved candidate source(s) used "
                "(caller avoided re-embedding)."
            )
        else:
            retrieval_result = cls._layer_hybrid_rag(
                retrieval_query,
                domains=domain_intent["collections"],
                jurisdiction=jurisdiction_info.get("retrieval_jurisdiction"),
            )
            sources = cls._dedupe(retrieval_result.get("sources", []))
            stats = retrieval_result.get("retrieval_stats", {})
            layer2_status = "PASS" if sources else "SKIP"
            layer2_detail = (
                f"{stats.get('semantic_results', 0)} → {stats.get('bm25_results', 0)} "
                f"→ {stats.get('statutory_results', 0)} merged; rerank → "
                f"{stats.get('final_count', len(sources))} final ("
                f"{stats.get('total_time_ms', 0)}ms)."
                if sources else "No hybrid candidates — switching to fallback."
            )

        if not sources:
            sources = cls._dedupe(cls._get_legacy_fallback(retrieval_query))
        sources = filter_sources_by_domain(sources, domain_intent["collections"])
        flow.append({
            "layer": "2 · Hybrid RAG (BM25 + BGE-M3 + Qdrant)",
            "status": layer2_status,
            "detail": layer2_detail,
        })

        # Peak confidence BEFORE fallbacks decide whether the cascade jumps.
        grounding = cls._compute_grounding(retrieval_query, sources)
        meaningful = grounding["meaningful"]
        coverage = grounding["coverage"]
        confidence = retrieval_result.get("confidence", 0.0)
        if confidence <= 0.0:
            confidence = _compute_confidence(meaningful, sources, coverage, intent_id)
        weak = confidence < FALLBACK_THRESHOLD

        # -------------------- LAYER 3 · KNOWLEDGE GRAPH -------------------------
        kg_used = False
        if weak or not grounding["retrieval_grounded"]:
            kg_sources = knowledge_graph_retrieve(retrieval_query, limit=6)
            before = len(sources)
            sources = cls._dedupe(sources + kg_sources)
            kg_used = len(sources) > before
            if kg_used:
                grounding = cls._compute_grounding(retrieval_query, sources)
                coverage = grounding["coverage"]
                if confidence <= 0.0 or weak:
                    confidence = _compute_confidence(
                        meaningful, sources, coverage, intent_id
                    )
                weak = confidence < FALLBACK_THRESHOLD
            flow.append({
                "layer": "3 · Knowledge Graph fallback",
                "status": "PASS" if kg_used else "SKIP",
                "detail": (
                    f"{len(sources) - before} canonical entity evidence record(s) "
                    "added (monographs / Acts / authorities)."
                    if kg_used else "No entity-resolvable graph evidence; moved on."
                ),
            })
        else:
            flow.append({
                "layer": "3 · Knowledge Graph fallback",
                "status": "SKIP",
                "detail": "Baseline confidence above fallback gate — graph not needed.",
            })

        # ------------------- LAYER 4 · RULE ENGINE fallback ---------------------
        re_result = cls._layer_rule_engine(
            retrieval_query, passport_id, intent_id, domain_intent, charts
        )
        r = re_result["readiness"]
        claim = re_result["claim"]
        engine_grounded = re_result["engine_grounded"] or bool(r)
        rule_hits = bool(r) or bool(claim) or engine_grounded
        if weak and rule_hits:
            engine_api = "Patent Readiness / Claim Firewall / dataset-backed rules"
            flow.append({
                "layer": "4 · Rule Engine fallback",
                "status": "PASS",
                "detail": (
                    f"Deterministic rules fired ({engine_api}); "
                    + ("anchored to real passport." if re_result["engine_grounded"]
                       else "scored from dataset/claims.")
                ),
            })
        else:
            flow.append({
                "layer": "4 · Rule Engine fallback",
                "status": "PASS" if rule_hits else "SKIP",
                "detail": (
                    "Deterministic rules applied." if rule_hits
                    else "No rule fired for this intent/scope."
                ),
            })

        # ------------------- LAYER 5 · MCP LIVE retrieval ------------------------
        preliminary_vote = vote_citations(sources)
        need_mcp = (
            MCP_ENABLED
            and (weak or preliminary_vote["official_votes"] < MIN_OFFICIAL_SOURCES_FOR_HIGH)
            and not (engine_grounded and not weak)
        )
        mcp_used = False
        if need_mcp:
            mcp = cls._layer_mcp_live(retrieval_query)
            live = mcp.get("sources", [])
            before = len(sources)
            sources = cls._dedupe(sources + live)
            mcp_used = len(sources) > before
            if mcp_used:
                grounding = cls._compute_grounding(retrieval_query, sources)
                coverage = grounding["coverage"]
                if confidence <= 0.0:
                    confidence = _compute_confidence(
                        meaningful, sources, coverage, intent_id
                    )
            flow.append({
                "layer": "5 · MCP live retrieval",
                "status": "PASS" if mcp_used else "SKIP",
                "detail": (
                    f"{len(sources) - before} live official passage(s) fetched via "
                    f"the MCP tool registry ({'enabled' if mcp.get('enabled') else 'disabled'})."
                    if mcp_used
                    else ("MCP bridge skipped: "
                          + (mcp.get("reason") or "moved on to citation voting."))
                ),
            })
        else:
            flow.append({
                "layer": "5 · MCP live retrieval",
                "status": "SKIP",
                "detail": "Sufficient evidence / not enabled — MCP bridge unused.",
            })

        # ------- JURISDICTION GATE · no law mixing (enforced HERE) -------------
        # Every cross-layer merge is complete. Golden rule: India and
        # International sources must never be cited in the same answer. Drop
        # any passage belonging to the other legal regime BEFORE voting so the
        # no-mixing constraint is physical, not aspirational.
        _gate_before = len(sources)
        sources = filter_sources_by_jurisdiction(sources, juris_resolved["mode"])
        _gate_dropped = _gate_before - len(sources)
        if _gate_dropped:
            flow.append({
                "layer": "6 · No-Mixing Gate",
                "status": "PASS",
                "detail": (
                    f"Dropped {_gate_dropped} source(s) from the other legal regime "
                    f"before citation voting — only the “{juris_resolved['mode']}” "
                    "framework remains. India & International law are never mixed."
                ),
            })

        # --------------------- LAYER 6 · CITATION VOTING -------------------------
        voting = vote_citations(sources)
        confidence = min(confidence, voting["confidence_cap"])
        sources = _rank_by_authority(sources, jurisdiction_info.get("detected", "India"))
        flow.append({
            "layer": "6 · Citation Voting",
            "status": "PASS",
            "detail": (
                f"{voting['official_votes']} independent official source(s) vote "
                f"(need {MIN_OFFICIAL_SOURCES_FOR_HIGH} for High); tier {voting['tier']} "
                f"→ confidence capped at {voting['confidence_cap']:.2f}. "
                + ("HIGH confidence attained."
                   if voting["high_confidence"]
                   else "High Confidence not attained (fewer than two official sources).")
            ),
        })

        # ---------- PROVISION CROSS-REFERENCE GRAPH · exceptions & definitions ----
        # Runs AFTER citation voting on purpose. A cross-reference pointer is not
        # an independent official source, so letting it vote would manufacture
        # High Confidence out of a graph lookup. Here it is appended for the
        # drafting step only, and re-passes the no-mixing gate so a cross-border
        # edge can never pull foreign law into an answer.
        _graph_notes: list[str] = []
        _graph_stale: list[dict[str, Any]] = []
        _graph_xrefs: list[dict[str, Any]] = []
        try:
            from app.services import provision_graph as _pgraph
            _exp = _pgraph.expand_for_sources(sources) if _pgraph.available() else None
        except Exception:  # graph is additive; never break the answer
            _exp, _pgraph = None, None
        if _exp:
            _seen_pids = {
                pid for s in sources
                for pid in (s.get("provision_id") if isinstance(s.get("provision_id"), (list, tuple))
                            else [s.get("provision_id")])
                if isinstance(pid, str)
            }
            _linked_sources: list[dict[str, Any]] = []
            for _entry in _exp["linked"]:
                _pid = _entry["provision_id"]
                if _pid in _seen_pids:
                    continue
                if not _pgraph.is_current(_pid):
                    continue  # never cite superseded/withdrawn law as current
                _src = _pgraph.provision_to_source(_pid, _entry)
                if _src:
                    _linked_sources.append(_src)
            _linked_sources = filter_sources_by_jurisdiction(
                _linked_sources, juris_resolved["mode"]
            )
            _cross_blocked = len(_exp["linked"]) - len(_linked_sources)
            if _linked_sources:
                # Deliberately NOT appended to `sources`. `sources[:5]` is both
                # the LLM context and the user-visible citation list, so a graph
                # pointer injected there would be presented as a retrieved
                # document. They travel as cross-reference context instead.
                _graph_xrefs = _linked_sources
                _graph_notes.append(
                    f"Applied {len(_linked_sources)} provision cross-reference(s) "
                    f"({', '.join(sorted({s['graph_edge_type'] for s in _linked_sources}))}) "
                    f"as drafting context; not counted as independent votes."
                )
            if _cross_blocked > 0:
                _graph_notes.append(
                    f"Blocked {_cross_blocked} cross-reference(s) from the other legal "
                    f"regime under the no-mixing rule (mode={juris_resolved['mode']})."
                )
            _graph_stale = _exp["stale"]
        if _graph_notes or _graph_stale:
            _detail = " ".join(_graph_notes)
            if _graph_stale:
                _detail += (
                    f" {len(_graph_stale)} provision(s) resolved to non-current law "
                    f"({', '.join(s['provision_id'] for s in _graph_stale)}) and were "
                    "withheld from citation."
                )
            flow.append({
                "layer": "6 · Provision Cross-Reference Graph",
                "status": "PASS" if _graph_notes else "WARN",
                "detail": _detail,
            })

        # ----------------- LAYER 7 · RESPONSE GENERATION -------------------------
        dataset_intents = {"white_space", "botanical_origin"}
        dataset_ok = intent_id in dataset_intents and (
            _load_knowledge_json("white_space.json" if intent_id == "white_space"
                                 else "india_origin.json") is not None
        )
        scored = r is not None
        scored = scored and bool(passport_id)
        claim_ok = bool(claim) and bool(passport_id)
        engine_grounded = scored or dataset_ok or claim_ok

        grounded = grounding["retrieval_grounded"] or engine_grounded
        should_refuse = retrieval_result.get("should_refuse", False)
        retrieval_result.get("refusal_reason", "")
        # The retrieval pipeline refuses below its internal confidence bar.
        # That confidence is computed from the retriever's embedding provider
        # (hashing-fallback / cold Qdrant index) and can UNDERSTATE queries
        # whose token-level coverage is actually solid. A refusal must never
        # override deterministic grounding, so it is only honoured when
        # token-level coverage is genuinely low too — otherwise a perfectly
        # grounded, source-quoted answer would be suppressed into a refusal.
        low_coverage = (
            not grounding["retrieval_grounded"] and not grounding["ratio_grounded"]
        )
        hard_refuse = bool(should_refuse) and low_coverage
        if hard_refuse and not engine_grounded:
            grounded = False
        if not grounded:
            confidence = 0.08

        # Strict abstention gate: if the only evidence is low-coverage and no
        # official document voted, do NOT answer from memory.
        abstention_reason = ""
        if grounded and not engine_grounded and not grounding["retrieval_grounded"]:
            grounded = False
        if grounded and not engine_grounded and (
            not grounding["ratio_grounded"] or voting["official_votes"] == 0
        ):
            if coverage < GROUNDING_MIN_COVERAGE and voting["official_votes"] == 0:
                abstention_reason = (
                    "No verified official source voted and retrieval coverage is "
                    "below the grounding minimum — safe abstention applied."
                )
                grounded = False
                confidence = 0.06

        citation = _top_citation(sources)
        exec_summary = _executive_summary(intent_id, r, claim, citation)
        loose_used = False
        # Loose / closest-official-sources mode is only blocked when the
        # retriever refused AND the citation vote does not corroborate the
        # evidence. Two+ independent official sources mean the KB genuinely
        # covers the framework — the answer then labels the closest official
        # records instead of refusing, without ever inventing content.
        hard_block = hard_refuse and voting["official_votes"] < (
            MIN_OFFICIAL_SOURCES_FOR_HIGH
        )
        if not grounded and sources and not hard_block and not abstention_reason:
            loose = _general_grounded_summary(retrieval_query, sources, loose=True)
            if loose:
                exec_summary = loose
                loose_used = True
                grounded = True
                if confidence < 0.35:
                    confidence = _compute_confidence(
                        meaningful, sources, min(1.0, coverage + 0.2), intent_id
                    )
        if not grounded:
            exec_summary = NO_EVIDENCE_ANSWER

        answer = co.build_structured_answer(
            exec_summary,
            citation if grounded and citation else "",
            DISCLAIMER if grounded else "",
            sources,
            retrieval_query,
            intent_id=intent_id,
            r=r,
            claim=claim,
            include_bullets=not loose_used,
        )

        # ---- LLM draft (only over voted/verified evidence) -----------------
        llm_draft_meta: dict[str, Any] = {
            "generated": False, "provider": "off", "model": None,
            "reason": "not attempted",
        }
        draft_applied = False
        scored_intents = {"patentability", "prior_art", "compliance",
                          "evidence_strength", "regulatory_roadmap"}
        scored = intent_id in scored_intents and r is not None
        if grounded and sources and answer != NO_EVIDENCE_ANSWER and confidence >= 0.30:
            try:
                from app.rag.llm_adapter import generate_draft
                llm_draft_meta = generate_draft(
                    retrieval_query, sources, intent=intent_id, passport_context=context
                )
                draft_text = llm_draft_meta.get("text") or ""
                if llm_draft_meta.get("generated") and not scored and len(draft_text) >= 40:
                    try:
                        from app.rag.hallucination_guard import validate_answer
                        hv = validate_answer(draft_text, sources, retrieval_query, confidence)
                        ok = hv.risk_level.value != "critical"
                    except Exception:
                        ok = False
                    if ok:
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

        if not draft_applied and grounded and sources and answer != NO_EVIDENCE_ANSWER \
            and "\nWHAT THE RULES SAY\n" not in answer and "\nEVIDENCE CITED\n" not in answer:
            evidence_block = _general_grounded_summary(retrieval_query, sources)
            if evidence_block and evidence_block not in answer:
                answer = answer.rstrip() + "\n\n" + evidence_block

        # ---- Claim-level verification (citations validated in context) ------
        verification: dict[str, Any] = {}
        if grounded and answer and answer != NO_EVIDENCE_ANSWER:
            try:
                from app.rag.verification_orchestrator import run_verification
                rule_pass = r.get("patent_ready") if isinstance(r, dict) else None
                vr = run_verification(
                    answer=answer,
                    sources=sources,
                    query=retrieval_query,
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
                    },
                    "claim_verification": {
                        "total_claims": vr.verification_table.total_claims,
                        "supported": vr.verification_table.supported_count,
                        "contradicted": vr.verification_table.contradicted_count,
                        "not_enough": vr.verification_table.not_enough_count,
                        "support_ratio": vr.verification_table.support_ratio,
                        "all_supported": vr.verification_table.all_supported,
                    },
                    "citation_validity": {
                        "total_citations": vr.citation_report.total_citations,
                        "valid_citations": vr.citation_report.valid_citations,
                        "invalid_citations": vr.citation_report.invalid_citations,
                        "validity_ratio": vr.citation_report.validity_ratio,
                    },
                }
                if (
                    vr.final_answer
                    and "\nWHAT THE RULES SAY\n" not in answer
                    and "\nEVIDENCE CITED\n" not in answer
                ):
                    answer = vr.final_answer
            except Exception:
                pass

        if abstention_reason:
            verification["abstention"] = abstention_reason
        flow.append({
            "layer": "7 · LLM response generation",
            "status": "BLOCK" if not grounded else "PASS",
            "detail": (
                abstention_reason or
                ("Response generated from verified evidence; "
                 + ("LLM draft applied." if draft_applied
                    else "deterministic grounded builder used."))
            ),
        })

        # ---- Post-processing (patent-topic ban for non-patent domains) -------
        if domain_intent["ban_patent_topics"]:
            answer = strip_banned_patent_topics(answer)
            exec_summary = strip_banned_patent_topics(exec_summary)

        # ---- Bhashini answer translation -------------------------------------
        # Deliver the final answer in the user's own language whenever the query
        # arrived in an Indic language and the Bhashini API is configured.
        bhashini_status["answer_translated"] = False
        if detected_language != "en" and bhashini_status.get("enabled"):
            try:
                from app.services.bhashini_client import BhashiniClient
                translated_answer = BhashiniClient.translate_answer_to_lang(
                    answer, detected_language
                )
                if translated_answer and str(translated_answer).strip():
                    answer = str(translated_answer).strip()
                    bhashini_status["answer_translated"] = True
                translated_summary = BhashiniClient.translate_answer_to_lang(
                    exec_summary, detected_language
                )
                if translated_summary and str(translated_summary).strip():
                    exec_summary = str(translated_summary).strip()
            except Exception:
                pass

        if r:
            risk_level = ("Low" if r["overall_readiness"] >= 70
                          else ("Moderate" if r["overall_readiness"] >= 40 else "High"))
            patent_readiness = round(r["overall_readiness"])
        elif claim:
            risk_level = {"HIGH_RISK": "High", "WARNING": "Moderate", "SAFE": "Low"}[claim["overall"]]
            patent_readiness = None
        else:
            risk_level = "Moderate"
            patent_readiness = None

        if not grounded or abstention_reason:
            verification_badge = "Blocked — No Verified Evidence (Safe Abstention)" if abstention_reason else "Insufficient Evidence"
        elif draft_applied:
            verification_badge = "Verified — Source-Grounded LLM Draft"
        elif r is not None and intent_id in scored_intents:
            verification_badge = "Verified — Measured by Rule Engines"
        elif engine_grounded:
            verification_badge = "Verified — Measured by Rule Engines"
        else:
            verification_badge = "Grounded — Knowledge Base Cited"

        classify_out: dict[str, Any] = {}
        try:
            classify_out = cls._assistant_enrichment(
                question=question,
                passport_id=passport_id,
                context=context,
                confidence=float(confidence),
                risk_level=str(risk_level or "Moderate"),
            )
        except Exception:
            classify_out = {}

        evidence_used: list[dict[str, str]] = []
        seen = set()
        for s in sources:
            name = _source_display_name(s)
            if name in seen:
                continue
            seen.add(name)
            evidence_used.append({"name": name, "type": _source_kind(s)})

        next_actions = _next_actions(intent_id, r, claim) if grounded and not abstention_reason else [
            "Add the authoritative document to the knowledge base and re-index.",
            "Rephrase the question with formulation/passport context.",
            "Create an Innovation Passport so the rule engines can score it.",
        ]
        if abstention_reason:
            next_actions.insert(0, "Safe abstention: no verified official evidence could be established — verify the corpus offline or enable MCP live retrieval.")

        citation or (sources[0].get("source_url") or sources[0].get("source") or "") if sources else ""
        # Fixed 8-section schema (identical to the clarification path — the card
        # must never re-shape between jurisdiction/clarify/normal answers).
        response_sections = {
            "direct_answer": answer,
            "key_requirements": next_actions[:4][:3] if next_actions else [],
            "why_this_matters": (
                "This innovation sits inside the {} legal framework — India and "
                "International law are applied independently and never mixed.".format(
                    mode if mode in ("India", "International") else "selected"
                )
            ),
            "official_sources_used": [
                {
                    "authority": _source_display_name(s),
                    "category": s.get("category", ""),
                    "jurisdiction": s.get("jurisdiction", ""),
                    "collection": s.get("collection", ""),
                    "vote": next((b["vote"] for b in voting["ballots"]
                                  if b["is_official"] == _is_official_source(s)), "pending"),
                    "quote": (s.get("content") or "").strip()[:300],
                }
                for s in sources[:5]
                if (s.get("content") or "").strip()
            ],
            "confidence": round(confidence * 100),
            "next_recommended_action": next_actions[0] if next_actions else "",
            "jurisdiction": {
                "mode": mode if mode in ("India", "International") else None,
                "label": jurisdiction_info.get("framework") or mode,
                "detected": mode,
                "cue": jurisdiction_info.get("detected_cue") or juris_resolved.get("cue"),
                "resolved_via": juris_resolved.get("resolved_via"),
            },
            "disclaimer": DISCLAIMER,
        }

        decision_rules = list(flow) + [{
            "layer": "Bhashini Translation",
            "status": "PASS" if (bhashini_status.get("query_translated") or bhashini_status.get("answer_translated")) else ("AVAILABLE" if bhashini_status.get("enabled") else "N/A"),
            "detail": (
                "Query translated to English for retrieval."
                if bhashini_status.get("query_translated")
                else ("Query kept as-is (already English)."
                      if detected_language == "en"
                      else ("Bhashini enabled — retrieval ran on the original query."
                            if bhashini_status.get("enabled")
                            else "Bhashini not configured — regex/glossary fallback used."))
                + (
                    " Answer translated back to " + language_label + "."
                    if bhashini_status.get("answer_translated")
                    else ""
                )
            ),
        }, {
            "layer": "Grounding Threshold",
            "status": "PASS" if grounded else "BLOCK",
            "detail": (
                f"Answer covered {coverage * 100:.0f}% of meaningful terms "
                f"(min {GROUNDING_MIN_COVERAGE * 100:.0f}% for verified evidence); "
                f"citation vote tier {voting['tier']}."
            ),
        }]

        decision_trace: dict[str, Any] = {
            "question": question,
            "language": {"code": detected_language, "label": language_label},
            "bhashini": {
                "status": "PASS" if (bhashini_status.get("query_translated") or bhashini_status.get("answer_translated")) else ("AVAILABLE" if bhashini_status.get("enabled") else "N/A"),
                "enabled": bhashini_status.get("enabled", False),
                "query_translated": bhashini_status.get("query_translated", False),
                "answer_translated": bhashini_status.get("answer_translated", False),
            },
            "jurisdiction": jurisdiction_info,
            "intent": {
                "id": intent_id,
                "label": surface_intent["label"],
                "domain": domain_intent["id"],
                "domain_label": domain_intent["label"],
                "collections": domain_intent["collections"],
                "patent_engine_enabled": domain_intent["run_patent_engine"],
            },
            "pipeline": {
                "name": "Zero-Delay Multi-Layer AI Orchestration",
                "layers": [
                    "1 · Intent Router",
                    "2 · Hybrid RAG (BM25 + BGE-M3 + Qdrant + Reranker)",
                    "3 · Knowledge Graph fallback",
                    "4 · Rule Engine fallback",
                    "5 · MCP live retrieval",
                    "6 · Citation Voting",
                    "7 · LLM response generation",
                ],
                "layer_flow": flow,
                "rules_applied": decision_rules,
            },
            "knowledge_base": {
                "mode": "Pure RAG — answers drawn only from curated IP-SAKTI collections + voted citations",
                "selected_collections": domain_intent["collections"],
            },
            "retrieval": {
                "method": "Intent Router → Hybrid RAG → KG → Rule Engine → MCP → Citation Voting → LLM",
                "source_count": len(sources[:5]),
                "candidate_count": len(sources),
                "cross_reference_count": len(_graph_xrefs),
                "llm_draft": llm_draft_meta.get("generated", False),
                "llm_provider": llm_draft_meta.get("provider", "off"),
            },
            "citation_voting": voting,
            "confidence": round(confidence * 100),
            "verification_badge": verification_badge,
            "answer_preview": (answer or "")[:400],
        }

        llm_prompt: dict[str, Any] = {}
        try:
            from app.rag.prompt_templates import build_rag_prompt
            llm_prompt = build_rag_prompt(
                query=question,
                sources=sources[:5],
                intent=intent_id,
                passport_context=context,
                cross_references=_graph_xrefs,
            )
            if domain_intent["ban_patent_topics"] and isinstance(llm_prompt, dict):
                user_prompt = llm_prompt.get("user") or llm_prompt.get("query") or ""
                if user_prompt and PATENT_BAN_INSTRUCTION not in str(user_prompt):
                    llm_prompt["user"] = str(user_prompt) + PATENT_BAN_INSTRUCTION
        except Exception:
            pass

        return {
            "question": question,
            "answer": answer,
            "sources": sources[:5],
            "cross_references": [
                {
                    "provision_id": s.get("provision_id", ""),
                    "citation_locator": s.get("citation_locator", ""),
                    "title": s.get("title", ""),
                    "relation": s.get("graph_edge_type", ""),
                    "reached_from": s.get("graph_via", ""),
                    "jurisdiction": s.get("jurisdiction", ""),
                    "effective_from": s.get("effective_from", ""),
                    "verification_status": s.get("verification_status", ""),
                    "summary": s.get("content", ""),
                }
                for s in _graph_xrefs
            ],
            "superseded_provisions": _graph_stale,
            "confidence": confidence,
            "images": [],
            "intent": {"id": intent_id, "label": surface_intent["label"]},
            "detected_language": detected_language,
            "response_sections": response_sections,
            "product_classification": classify_out.get("classification"),
            "product_classification_bilingual": classify_out.get("classification_bilingual"),
            "escalation": classify_out.get("escalation"),
            "analysis_card": {
                "confidence_pct": round(confidence * 100),
                "patent_readiness": patent_readiness,
                "risk_level": risk_level,
                "verification_badge": verification_badge,
                "executive_summary": exec_summary,
                "citation_voting": voting,
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
            "jurisdiction": jurisdiction_info,
            "decision_trace": decision_trace,
            "next_actions": next_actions[:4],
            "charts": charts,
            "llm_prompt": llm_prompt,
        }