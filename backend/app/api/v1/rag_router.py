"""
Production RAG API endpoints for VEDALEX | IP-SAKTI SAHAYAK.

Endpoints:
  POST /ask              — Full RAG query with citations and hallucination check
  POST /search-patent    — Patent-specific search with metadata filtering
  GET  /innovation-passport — Generate innovation passport with RAG context
  GET  /rag/status       — Pipeline health and statistics
  POST /rag/reindex      — Trigger full knowledge base reindex
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.models.db_models import User
from app.auth.jwt_auth import get_optional_user

router = APIRouter(prefix="/rag", tags=["RAG Pipeline"])


# ============================================================================
# Request/Response Models
# ============================================================================

class AskRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=2000, description="User query about Ayurveda IP or regulation")
    filters: Optional[Dict[str, Any]] = Field(None, description="Metadata filters: category, jurisdiction, authority, patent_number, publication_year")
    jurisdiction: Optional[str] = Field(None, description="Filter by jurisdiction: India, United States, Canada, International")
    category: Optional[str] = Field(None, description="Filter by category: patent, tkdl, regulatory, pharmacopoeia, who, pubmed")
    top_k: int = Field(5, ge=1, le=20, description="Number of top sources to return")
    include_prompt: bool = Field(False, description="Include the generated LLM prompt in response")
    passport_id: Optional[str] = Field(None, description="Innovation Passport ID for context enrichment")

class AskResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    grounding: Dict[str, Any]
    hallucination_check: Dict[str, Any]
    retrieval_stats: Dict[str, Any]
    intent: Optional[Dict[str, str]] = None
    charts: List[Dict[str, Any]] = []
    llm_prompt: Optional[Dict[str, str]] = None
    verification_badge: str
    next_actions: List[str] = []
    verification: Optional[Dict[str, Any]] = None


class PatentSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000, description="Patent search query")
    patent_number: Optional[str] = Field(None, description="Search by specific patent number")
    jurisdiction: Optional[str] = Field(None, description="Filter by jurisdiction")
    publication_year: Optional[int] = Field(None, ge=1970, le=2030, description="Filter by publication year")
    section: Optional[str] = Field(None, description="Filter by patent section: claims, abstract, description")
    top_k: int = Field(10, ge=1, le=50, description="Number of results")


class PatentSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_found: int
    query: str
    filters_applied: Dict[str, Any]
    retrieval_stats: Dict[str, Any]


class InnovationPassportRequest(BaseModel):
    formulation_name: str = Field(..., min_length=2, max_length=200, description="Name of the Ayurvedic formulation")
    ingredients: List[str] = Field(..., min_items=1, description="List of ingredients")
    process_description: Optional[str] = Field(None, description="Manufacturing process description")
    target_markets: List[str] = Field(default=["India"], description="Target market jurisdictions")
    claims: List[str] = Field(default_factory=list, description="Proposed patent claims")


class InnovationPassportResponse(BaseModel):
    passport_id: str
    formulation_name: str
    ingredients: List[Dict[str, Any]]
    prior_art_analysis: Dict[str, Any]
    tkdl_overlap: Dict[str, Any]
    section_3p_assessment: Dict[str, Any]
    patent_readiness: Optional[Dict[str, Any]]
    regulatory_requirements: Dict[str, Any]
    evidence_gaps: List[str]
    confidence: float
    sources: List[Dict[str, Any]]


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/ask", response_model=AskResponse)
async def ask_query(
    req: AskRequest,
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Full RAG query with hybrid retrieval, reranking, and hallucination validation.

    Pipeline: Query -> Embed -> Qdrant + BM25 + Statutory -> Merge -> Rerank
              -> Hallucination Check -> Confidence -> Response
    """
    from app.rag.retrieval_pipeline import HybridRetriever
    from app.rag.hallucination_guard import validate_answer
    from app.rag.prompt_templates import build_rag_prompt
    from app.services.copilot_orchestrator import classify_intent

    # Step 1: Hybrid retrieval
    retrieval_result = HybridRetriever.retrieve(
        query=req.query,
        top_k=req.top_k,
        filters=req.filters,
        jurisdiction=req.jurisdiction,
        category=req.category,
    )

    sources = retrieval_result.get("sources", [])
    confidence = retrieval_result.get("confidence", 0.05)
    grounding = retrieval_result.get("grounding", {})

    # Step 2: Intent classification (normalized to id/label; patterns are
    # internal matching data and must not leak into the API schema)
    raw_intent = classify_intent(req.query)
    intent = {
        "id": raw_intent.get("id", "general"),
        "label": raw_intent.get("label", "General RAG"),
    }

    # Step 3: Generate answer (using existing orchestrator logic)
    from app.services.copilot_orchestrator import AICopilotOrchestrator
    orchestrator_result = AICopilotOrchestrator.run(req.query, req.passport_id)

    answer = orchestrator_result.get("answer", "")
    charts = orchestrator_result.get("charts", [])
    next_actions = orchestrator_result.get("next_actions", [])

    # Step 4: Post-generation hallucination validation
    hv = validate_answer(answer, sources, req.query, confidence)

    # Step 5: Generate LLM prompt (optional)
    llm_prompt = None
    if req.include_prompt:
        llm_prompt = build_rag_prompt(req.query, sources, intent=intent.get("id"))

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
    )


@router.post("/search-patent", response_model=PatentSearchResponse)
async def search_patent(
    req: PatentSearchRequest,
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Patent-specific search with metadata filtering.
    Searches patents, TKDL, and WIPO databases with section-aware chunking.
    """
    from app.rag.retrieval_pipeline import HybridRetriever

    # Build filters
    filters = {}
    if req.patent_number:
        filters["patent_number"] = req.patent_number
    if req.jurisdiction:
        filters["jurisdiction"] = req.jurisdiction
    if req.publication_year:
        filters["publication_year"] = req.publication_year
    if req.section:
        filters["section_heading"] = req.section

    # Patent-focused retrieval
    retrieval_result = HybridRetriever.retrieve(
        query=req.query,
        top_k=req.top_k,
        filters=filters if filters else None,
        category="patents",
    )

    sources = retrieval_result.get("sources", [])

    # Also search statutory passages for patent law context
    from app.rag.retrieval_pipeline import HybridRetriever
    statutory = HybridRetriever.statutory_search(req.query, top_k=3)

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


@router.get("/innovation-passport/{passport_id}")
async def get_innovation_passport(
    passport_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Generate a full innovation passport with RAG-enriched analysis.
    Combines rule engines with retrieved prior art, TKDL overlap, and regulatory context.
    """
    from app.services.passport_engine import PassportEngine
    from app.services.patent_readiness_engine import PatentReadinessEngine
    from app.rag.retrieval_pipeline import HybridRetriever

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
async def rag_status():
    """Pipeline health check with detailed statistics."""
    from app.rag.retrieval_pipeline import HybridRetriever
    return HybridRetriever.get_status()


@router.post("/reindex")
async def reindex_knowledge_base():
    """Trigger full knowledge base reindex into Qdrant + BM25."""
    from app.rag.retrieval_pipeline import HybridRetriever
    stats = HybridRetriever.reindex_all()
    return {
        "status": "completed",
        "stats": stats,
        "message": f"Reindexed {stats['total_documents']} documents in {stats['elapsed_seconds']}s",
    }
