"""
Production RAG API endpoints for VEDALEX | IP-SAKTI SAHAYAK.

Endpoints:
  POST /ask              — Full RAG query with citations and hallucination check
  POST /search-patent    — Patent-specific search with metadata filtering
  GET  /innovation-passport — Generate innovation passport with RAG context
  GET  /rag/status       — Pipeline health and statistics
  POST /rag/reindex      — Trigger full knowledge base reindex
"""

import logging
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth.jwt_auth import get_optional_user
from app.core.async_bridge import run_sync
from app.models.db_models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG Pipeline"])


# ============================================================================
# Request/Response Models
# ============================================================================

class AskRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=2000, description="User query about Ayurveda IP or regulation")
    filters: dict[str, Any] | None = Field(None, description="Metadata filters: category, jurisdiction, authority, patent_number, publication_year")
    jurisdiction: str | None = Field(None, description="Filter by jurisdiction: India, United States, Canada, International")
    category: str | None = Field(None, description="Filter by category: patent, tkdl, regulatory, pharmacopoeia, who, pubmed")
    top_k: int = Field(5, ge=1, le=20, description="Number of top sources to return")
    include_prompt: bool = Field(False, description="Include the generated LLM prompt in response")
    passport_id: str | None = Field(None, description="Innovation Passport ID for context enrichment")

class AskResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    confidence: float
    grounding: dict[str, Any]
    hallucination_check: dict[str, Any]
    retrieval_stats: dict[str, Any]
    intent: dict[str, str] | None = None
    charts: list[dict[str, Any]] = []
    llm_prompt: dict[str, str] | None = None
    verification_badge: str
    next_actions: list[str] = []
    verification: dict[str, Any] | None = None
    detected_language: str | None = None
    response_sections: dict[str, Any] | None = None


class PatentSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000, description="Patent search query")
    patent_number: str | None = Field(None, description="Search by specific patent number")
    jurisdiction: str | None = Field(None, description="Filter by jurisdiction")
    publication_year: int | None = Field(None, ge=1970, le=2030, description="Filter by publication year")
    section: str | None = Field(None, description="Filter by patent section: claims, abstract, description")
    top_k: int = Field(10, ge=1, le=50, description="Number of results")


class PatentSearchResponse(BaseModel):
    results: list[dict[str, Any]]
    total_found: int
    query: str
    filters_applied: dict[str, Any]
    retrieval_stats: dict[str, Any]


class BooleanSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000, description="Technical solution text to build boolean searches from")
    expression: str | None = Field(None, description="Raw boolean DSL to run directly (overrides generated searches)")
    jurisdiction: str | None = Field("IN", description="Target jurisdiction for the classification variant")
    top_k: int = Field(8, ge=1, le=50, description="Results per boolean search")


class BooleanSearchResponse(BaseModel):
    searches: list[dict[str, Any]]
    reference_list: list[dict[str, Any]]
    total_matched: int | None = None
    query: str
    note: str = ""


class InnovationPassportRequest(BaseModel):
    formulation_name: str = Field(..., min_length=2, max_length=200, description="Name of the Ayurvedic formulation")
    ingredients: list[str] = Field(..., min_length=1, description="List of ingredients")
    process_description: str | None = Field(None, description="Manufacturing process description")
    target_markets: list[str] = Field(default=["India"], description="Target market jurisdictions")
    claims: list[str] = Field(default_factory=list, description="Proposed patent claims")


class InnovationPassportResponse(BaseModel):
    passport_id: str
    formulation_name: str
    ingredients: list[dict[str, Any]]
    prior_art_analysis: dict[str, Any]
    tkdl_overlap: dict[str, Any]
    section_3p_assessment: dict[str, Any]
    patent_readiness: dict[str, Any] | None
    regulatory_requirements: dict[str, Any]
    evidence_gaps: list[str]
    confidence: float
    sources: list[dict[str, Any]]


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/ask", response_model=AskResponse)
async def ask_query(
    req: AskRequest,
    current_user: User | None = Depends(get_optional_user),
):
    """
    Full RAG query with hybrid retrieval, reranking, and hallucination validation.

    Pipeline: Query -> Embed -> Qdrant + BM25 + Statutory -> Merge -> Rerank
              -> Hallucination Check -> Confidence -> Response
    """
    from app.agents.input_defenses import defend_query
    from app.rag.hallucination_guard import validate_answer
    from app.rag.prompt_templates import build_rag_prompt
    from app.rag.retrieval_pipeline import HybridRetriever
    from app.services.copilot_orchestrator import classify_intent
    from app.services.intent_classifier import (
        classify_domain_intent,
        filter_sources_by_domain,
    )

    # Security B1+B2: PII redacted and injection text neutralised before the
    # query reaches retrieval, classification or any LLM call.
    query = defend_query(req.query)["query"]

    # Step 1: Domain-intent classification BEFORE retrieval — only the
    # collections relevant to the query intent are searched and cited.
    domain_intent = classify_domain_intent(query)

    # Step 1b: Hybrid retrieval restricted to intent-relevant collections.
    # Embedding + BM25 + rerank is CPU/IO bound, so it runs on a worker thread.
    retrieval_result = await run_sync(
        HybridRetriever.retrieve,
        query=query,
        top_k=req.top_k,
        filters=req.filters,
        jurisdiction=req.jurisdiction,
        category=req.category,
        domains=domain_intent["collections"],
    )

    sources = filter_sources_by_domain(
        retrieval_result.get("sources", []), domain_intent["collections"]
    )
    confidence = retrieval_result.get("confidence", 0.05)
    grounding = retrieval_result.get("grounding", {})

    # Step 2: Intent classification (normalized to id/label; patterns are
    # internal matching data and must not leak into the API schema)
    raw_intent = classify_intent(query)
    intent = {
        "id": raw_intent.get("id", "general"),
        "label": raw_intent.get("label", "General RAG"),
        "domain": domain_intent["id"],
        "domain_label": domain_intent["label"],
    }

    # Step 3: Generate answer (using the zero-delay multi-layer orchestrator).
    # The sources retrieved above are passed in so the orchestrator does NOT
    # re-run the (embedding + rerank) hybrid pipeline a second time.
    from app.services.multi_layer_orchestrator import MultiLayerOrchestrator
    orchestrator_result = await run_sync(
        MultiLayerOrchestrator.run,
        query,
        req.passport_id,
        retrieved_sources=sources,
    )

    answer = orchestrator_result.get("answer", "")
    charts = orchestrator_result.get("charts", [])
    next_actions = orchestrator_result.get("next_actions", [])

    # Step 4: Post-generation hallucination validation
    hv = await run_sync(validate_answer, answer, sources, query, confidence)

    # Step 5: Generate LLM prompt (optional)
    llm_prompt = None
    if req.include_prompt:
        llm_prompt = build_rag_prompt(query, sources, intent=intent.get("id"))

    # Step 6: Verification badge (use the orchestrator's enriched badge,
    # which reflects claim-level verification, not just source grounding)
    verification_badge = orchestrator_result.get("analysis_card", {}).get(
        "verification_badge", "Insufficient Evidence"
    )

    return AskResponse(
        answer=answer,
        sources=sources[:req.top_k],
        confidence=confidence,
        grounding=grounding,
        hallucination_check={
            "risk_level": hv.risk_level.value,
            "grounded": hv.grounded,
            "coverage_ratio": hv.coverage_ratio,
            "citation_count": hv.citation_count,
            "violations": hv.violations,
            "recommendations": hv.recommendations,
        },
        retrieval_stats=retrieval_result.get("retrieval_stats", {}),
        intent=intent,
        charts=charts,
        llm_prompt=llm_prompt,
        verification_badge=verification_badge,
        next_actions=next_actions,
        verification=orchestrator_result.get("verification"),
        detected_language=orchestrator_result.get("detected_language"),
        response_sections=orchestrator_result.get("response_sections"),
    )


@router.post("/search-patent", response_model=PatentSearchResponse)
async def search_patent(
    req: PatentSearchRequest,
    current_user: User | None = Depends(get_optional_user),
):
    """
    Patent-specific search with metadata filtering.
    Searches patents, TKDL, and WIPO databases with section-aware chunking.
    """
    from app.rag.retrieval_pipeline import HybridRetriever

    # Build filters
    filters: dict[str, Any] = {}
    if req.patent_number:
        filters["patent_number"] = req.patent_number
    if req.jurisdiction:
        filters["jurisdiction"] = req.jurisdiction
    if req.publication_year:
        filters["publication_year"] = req.publication_year
    if req.section:
        filters["section_heading"] = req.section

    # Patent-focused retrieval
    retrieval_result = await run_sync(
        HybridRetriever.retrieve,
        query=req.query,
        top_k=req.top_k,
        filters=filters if filters else None,
        category="patents",
    )

    sources = retrieval_result.get("sources", [])

    # Also search statutory passages for patent law context
    statutory = await run_sync(HybridRetriever.statutory_search, req.query, top_k=3)

    # Merge patent + statutory results
    all_results = sources + statutory
    seen = set()
    deduped = []
    for r in all_results:
        key = (r.get("patent_number", ""), r.get("content", "")[:60])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    return PatentSearchResponse(
        results=deduped[:req.top_k],
        total_found=len(deduped),
        query=req.query,
        filters_applied=filters,
        retrieval_stats=retrieval_result.get("retrieval_stats", {}),
    )


@router.post("/boolean-search", response_model=BooleanSearchResponse)
async def boolean_search(
    req: BooleanSearchRequest,
    current_user: User | None = Depends(get_optional_user),
):
    """
    Eureka-style Boolean Search 1..5.

    Builds five deterministic boolean strategies (core-AND, synonym OR-groups,
    jurisdiction/classification, phrase, broad recall) from a technical
    description and evaluates them against the full local retrieval corpus.
    Use ``expression`` to run a raw DSL query instead, e.g.::

        ashwagandha AND formulation AND NOT year:2020
        "herbal cream" NEAR/6 extraction
    """
    from app.rag.boolean_search import (
        build_searches,
        merged_reference_list,
        search,
    )

    if req.expression and req.expression.strip():
        direct = await run_sync(search, req.expression, top_k=req.top_k)
        return BooleanSearchResponse(
            searches=[{
                "name": "Boolean Expression",
                "expression": req.expression,
                "matched": direct["matched"],
                "results": direct["results"],
                "leaf_terms": direct["leaf_terms"],
            }],
            reference_list=await run_sync(
                merged_reference_list, [direct], top_k=req.top_k
            ),
            total_matched=direct["matched"],
            query=req.query,
            note="Raw boolean expression executed directly over the local corpus.",
        )

    searches = await run_sync(
        build_searches,
        req.query,
        top_k=req.top_k,
        jurisdiction=req.jurisdiction,
    )
    reference_list = await run_sync(
        merged_reference_list, searches, top_k=req.top_k
    )
    total = sum(int(s.get("matched", 0)) for s in searches)

    return BooleanSearchResponse(
        searches=searches,
        reference_list=reference_list,
        total_matched=total,
        query=req.query,
        note=(
            f"{len(searches)} boolean strategies run over the local corpus; "
            "hits below are deterministic token/field matches, not semantic."
        ),
    )


@router.get("/innovation-passport/{passport_id}")
def get_innovation_passport(
    passport_id: str,
    current_user: User | None = Depends(get_optional_user),
):
    """
    Generate a full innovation passport with RAG-enriched analysis.
    Combines rule engines with retrieved prior art, TKDL overlap, and regulatory context.
    """
    from app.rag.retrieval_pipeline import HybridRetriever
    from app.services.passport_engine import PassportEngine
    from app.services.patent_readiness_engine import PatentReadinessEngine

    # Get or create passport
    passport = PassportEngine.get_passport(passport_id)
    if not passport:
        return {"error": "Passport not found", "passport_id": passport_id}

    # Patent readiness score
    readiness = PatentReadinessEngine.compute(passport)

    # RAG-enriched prior art search
    ingredients_text = " ".join(
        f"{ing.botanical_name} {ing.raw_name}"
        for ing in passport.ingredients
    )
    prior_art = HybridRetriever.retrieve(
        query=f"prior art {ingredients_text} {passport.claimed_innovation or ''}",
        top_k=5,
        category="patents",
    )

    # TKDL overlap check
    tkdl_search = HybridRetriever.retrieve(
        query=f"traditional knowledge {ingredients_text}",
        top_k=3,
        category="tkdl",
    )

    # Regulatory requirements
    regulatory = HybridRetriever.retrieve(
        query=f"regulatory requirements Ayurveda formulation {' '.join(passport.target_markets or ['India'])}",
        top_k=3,
        category="regulatory",
    )

    return {
        "passport_id": passport_id,
        "formulation_name": passport.product_form or "Unnamed Formulation",
        "ingredients": [
            {"name": ing.raw_name, "botanical": ing.botanical_name}
            for ing in passport.ingredients
        ],
        "prior_art_analysis": {
            "sources": prior_art.get("sources", []),
            "overlap_count": len(prior_art.get("sources", [])),
            "confidence": prior_art.get("confidence", 0),
        },
        "tkdl_overlap": {
            "sources": tkdl_search.get("sources", []),
            "overlap_found": len(tkdl_search.get("sources", [])) > 0,
            "confidence": tkdl_search.get("confidence", 0),
        },
        "section_3p_assessment": {
            "risk": readiness.get("section3p_risk", "Unknown") if readiness else "Unknown",
            "score": readiness.get("components", [{}])[2].get("earned", 0) if readiness else 0,
        },
        "patent_readiness": readiness,
        "regulatory_requirements": {
            "sources": regulatory.get("sources", []),
            "confidence": regulatory.get("confidence", 0),
        },
        "evidence_gaps": readiness.get("missing_evidence", []) if readiness else [],
        "confidence": prior_art.get("confidence", 0),
        "sources": prior_art.get("sources", []) + tkdl_search.get("sources", []),
    }


@router.get("/status")
def rag_status():
    """Pipeline health check with detailed statistics."""
    from app.rag.retrieval_pipeline import HybridRetriever
    return HybridRetriever.get_status()


@router.post("/reindex")
def reindex_knowledge_base():
    """Trigger full knowledge base reindex into Qdrant + BM25."""
    from app.rag.retrieval_pipeline import HybridRetriever
    stats = HybridRetriever.reindex_all()
    return {
        "status": "completed",
        "stats": stats,
        "message": f"Reindexed {stats['total_documents']} documents in {stats['elapsed_seconds']}s",
    }


@router.get("/ingest/patent-corpus/status")
def patent_corpus_status():
    """Status of the curated IP India / NBA patent-legal corpus harvest."""
    from app.services.corpus_harvester import harvester_status
    return harvester_status()


@router.post("/ingest/patent-corpus")
def run_patent_corpus_harvest(
    limit: int | None = Query(None, ge=1, le=500, description="Max chunks embedded per document"),
    force: bool = Query(False, description="Ignore change-detection ledger and re-embed all"),
):
    """Fetch, chunk and embed the curated authoritative patent corpus into Qdrant."""
    from app.services.corpus_harvester import harvest_documents
    summary = harvest_documents(limit_per_doc=limit, force=force)
    from app.rag.retrieval_pipeline import HybridRetriever
    qdrant = HybridRetriever.get_status()
    summary["qdrant_total_points"] = (qdrant.get("qdrant") or {}).get("total_points", 0)
    return summary


@router.get("/ingest/status")
def ingestion_status():
    """Corpus ingestion state + scheduler health."""
    from app.ingestion.pipeline import get_ingestion_status
    from app.services.ingestion_scheduler import get_scheduler_status
    return {
        "ingestion": get_ingestion_status(),
        "scheduler": get_scheduler_status(),
    }


@router.post("/ingest")
def run_ingestion_endpoint(
    source_ids: list[str] | None = Query(None, description="Source ids or selectors (P0/P1/P2/P3/all/daily/weekly/monthly)"),
    mode: str = Query("update", pattern="^(update|full)$"),
    limit: int | None = Query(None, ge=1, le=1000),
    query: str | None = Query(None, max_length=200, description="Search query used to discover additional pages on public sources"),
):
    """Trigger a corpus ingestion pass (change-aware by default)."""
    from app.ingestion.pipeline import run_ingestion as run_pipeline
    summary = run_pipeline(
        source_ids=source_ids,
        mode=mode,
        include_local=True,
        include_seeds=True,
        query=query,
        limit_per_source=limit,
    )
    return summary


@router.get("/knowledge-graph/stats")
def knowledge_graph_stats(force: bool = False):
    """Entity/edge counts of the corpus knowledge graph (rebuild with ?force=true)."""
    from app.rag.knowledge_graph import get_graph_stats
    return get_graph_stats(force=force)


@router.get("/knowledge-graph/search")
def knowledge_graph_search(q: str = Query("", max_length=200), limit: int = Query(10, ge=1, le=50)):
    """Entity lookup across botanicals, ingredients, regulations and authorities."""
    from app.rag.knowledge_graph import search_entities
    return search_entities(q, limit=limit)


# ============================================================================
# Unified RAG search (Hybrid / Production / Graph / Agentic)
# ============================================================================

class UnifiedSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=2000, description="User query about Ayurveda IP or regulation")
    jurisdiction: str | None = Field(None, description="Filter by jurisdiction: India, United States, Canada, International")
    category: str | None = Field(None, description="Filter by category: patent, tkdl, regulatory, pharmacopoeia, who, pubmed")
    top_k: int = Field(10, ge=1, le=50, description="Number of top sources to return")
    rag_type: str | None = Field(None, description="RAG architecture: hybrid | production | graph | agentic | auto (auto = rule-based routing)")
    filters: dict[str, Any] | None = Field(None, description="Optional metadata filters (category, jurisdiction, patent_number, ...)")
    user_key: str | None = Field(None, max_length=100, description="Optional identifier for rate-limiting (defaults to user id / 'anonymous')")


class UnifiedSearchResponse(BaseModel):
    success: bool
    rag_type: str
    sources: list[dict[str, Any]]
    count: int
    latency_ms: float
    confidence: float
    grounding: dict[str, Any] = {}
    refusal: dict[str, Any] | None = None
    retrieval_stats: dict[str, Any] = {}
    meta: dict[str, Any] = {}


class ConfigureRequest(BaseModel):
    rag_type: str | None = Field(None, description="Default RAG type for /rag/search: hybrid | production | graph | agentic | auto")
    cache_ttl: int | None = Field(None, ge=0, le=86400, description="Result-cache lifetime in seconds (0 disables)")
    rate_limit: int | None = Field(None, ge=1, le=10000, description="Max searches per user per minute (ProductionRAG)")


class SearchStatsResponse(BaseModel):
    rag_types: list[str]
    default_rag_type: str
    config: dict[str, Any]
    per_type: dict[str, Any]


@router.post("/search", response_model=UnifiedSearchResponse)
async def unified_rag_search(
    req: UnifiedSearchRequest,
    current_user: User | None = Depends(get_optional_user),
):
    """
    Unified search across all four RAG architectures.

    ``rag_type``: hybrid (BM25 + dense + RRF + rerank), production (hybrid +
    cache + rate-limit), graph (hybrid + knowledge graph), agentic (parallel
    specialised agents). Defaults to ``IPSAKTI_RAG_DEFAULT`` (env or /rag/configure).
    """
    import time as _time

    from app.services.rag import get_rag
    from app.services.rag.auto_selector import AUTO, select_rag_type
    from app.services.rag.base_rag import RagResult
    from app.services.rag.config import get as cfg_get
    start = _time.perf_counter_ns()

    requested = (req.rag_type or str(cfg_get("default", "hybrid"))).strip().lower()
    auto_meta: dict[str, Any] = {}
    if requested == AUTO:
        selection = select_rag_type(req.query, default=str(cfg_get("default", "hybrid")))
        auto_meta = {
            "auto_resolved": selection["rag_type"],
            "auto_reason": selection["reason"],
        }
        requested = selection["rag_type"]

    identifier = "anonymous"
    if req.user_key:
        identifier = req.user_key[:100]
    elif current_user:
        identifier = cast(str, current_user.email)

    try:
        rag = get_rag(requested)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    try:
        result: RagResult = await run_sync(
            rag.search,
            query=req.query,
            filters=req.filters,
            jurisdiction=req.jurisdiction,
            category=req.category,
            top_k=req.top_k,
            user_key=identifier,
        )
    except Exception as exc:
        if requested == "hybrid":
            logger.error("unified search failed with no fallback available: %s", exc)
            raise HTTPException(503, "retrieval unavailable") from exc
        logger.warning("rag search %r failed, falling back to hybrid: %s", requested, exc)
        auto_meta["fallback_from"] = requested
        auto_meta["fallback_error"] = str(exc)
        try:
            result = await run_sync(
                get_rag("hybrid").search,
                query=req.query,
                filters=req.filters,
                jurisdiction=req.jurisdiction,
                category=req.category,
                top_k=req.top_k,
                user_key=identifier,
            )
        except Exception as fallback_exc:
            logger.error("hybrid fallback also failed: %s", fallback_exc)
            raise HTTPException(503, "retrieval unavailable") from fallback_exc

    return UnifiedSearchResponse(
        success=True,
        rag_type=result.rag_type,
        sources=result.sources[:req.top_k],
        count=len(result.sources[:req.top_k]),
        latency_ms=round((_time.perf_counter_ns() - start) / 1_000_000.0, 2),
        confidence=result.confidence,
        grounding=result.grounding,
        refusal=None
        if not result.should_refuse
        else {"blocked": True, "reason": result.refusal_reason},
        retrieval_stats=result.retrieval_stats,
        meta={**result.meta, **auto_meta},
    )


@router.get("/search/stats", response_model=SearchStatsResponse)
def unified_rag_stats():
    """Health + metrics for every RAG architecture."""
    from app.services.rag import get_rag
    from app.services.rag.config import RAG_TYPES, get, snapshot

    per_type: dict[str, Any] = {}
    for rag_type in RAG_TYPES:
        try:
            rag = get_rag(rag_type)
            per_type[rag_type] = rag.status()
        except Exception as exc:
            per_type[rag_type] = {"error": str(exc)}

    return SearchStatsResponse(
        rag_types=RAG_TYPES,
        default_rag_type=get("default", "hybrid"),
        config=snapshot(),
        per_type=per_type,
    )


@router.post("/configure")
def configure_rag(req: ConfigureRequest):
    """Update RAG runtime configuration (process-wide, resets on restart)."""
    from app.services.rag.config import RAG_TYPES, snapshot, update

    payload: dict[str, Any] = {}
    if req.rag_type is not None:
        if req.rag_type not in [*RAG_TYPES, "auto"]:
            raise HTTPException(400, f"rag_type must be one of {RAG_TYPES} or 'auto'")
        payload["default"] = req.rag_type
    if req.cache_ttl is not None:
        payload["cache_ttl"] = req.cache_ttl
    if req.rate_limit is not None:
        payload["rate_limit"] = req.rate_limit

    applied = update(payload)
    return {"status": "ok", "updated": applied, "config": snapshot()}
