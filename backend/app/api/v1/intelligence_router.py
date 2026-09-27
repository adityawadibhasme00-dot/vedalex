
from fastapi import APIRouter
from pydantic import BaseModel

from app.models.intelligence import (
    ABSComplianceResponse,
    BioResourceGraphResponse,
    ClaimSafetyAnalysisResponse,
    EvidenceQualityIntelligenceResponse,
    ExportReadinessResponse,
    InnovationKnowledgeGraphResponse,
    ProductClassifierResponse,
    TerminologyMapResponse,
)
from app.services.abs_compliance_service import ABSComplianceEngine
from app.services.bio_resource_engine import BioResourceEngine
from app.services.claim_safety_engine import ClaimSafetyEngine
from app.services.evidence_quality_engine import EvidenceQualityEngine
from app.services.export_readiness_engine import ExportReadinessEngine
from app.services.innovation_graph_service import build_innovation_graph
from app.services.passport_engine import PassportEngine
from app.services.product_classifier import ProductClassifier
from app.services.terminology_mapper import TerminologyMapper

router = APIRouter(prefix="/intelligence", tags=["Intelligence Engines"])


class ClaimSafetyAnalyzeRequest(BaseModel):
    claims: list[str] | None = None
    ingredients: list[str] | None = None
    product_type: str = "ayurvedic_drug"
    target_markets: list[str] = ["India", "United States", "Canada"]
    passport_id: str | None = None


@router.post("/claim-safety/analyze", response_model=ClaimSafetyAnalysisResponse)
def analyze_claim_safety(req: ClaimSafetyAnalyzeRequest):
    claims = req.claims or []
    ingredients = req.ingredients or []
    passport_id = req.passport_id
    markets = req.target_markets or ["India"]

    if passport_id:
        passport = PassportEngine.get_passport(passport_id)
        if passport:
            if not claims:
                claims = passport.proposed_claims
            if not ingredients:
                ingredients = [ing.raw_name for ing in passport.ingredients]
            if not markets or markets == ["India"]:
                markets = passport.target_markets

    if not claims:
        claims = ["Supports healthy sleep"]

    return ClaimSafetyEngine.analyze(
        claims=claims,
        ingredients=ingredients,
        target_markets=markets,
        product_type=req.product_type,
        passport_id=passport_id,
    )


@router.get("/evidence-quality/{passport_id}", response_model=EvidenceQualityIntelligenceResponse)
def get_evidence_quality_intelligence(passport_id: str):
    return EvidenceQualityEngine.evaluate(passport_id)


@router.get("/bio-resource/{passport_id}", response_model=BioResourceGraphResponse)
def get_bio_resource_intelligence(passport_id: str):
    return BioResourceEngine.build(passport_id)


class ProductClassifyRequest(BaseModel):
    passport_id: str | None = None
    product_name: str | None = None
    product_form: str | None = None
    dosage_form: str | None = None
    intended_use: str | None = None
    claims: list[str] | None = None
    ingredients: list[str] | None = None
    process_description: str | None = None
    label_disclaimer: str | None = None
    first_schedule: bool | None = None
    new_ingredient: bool | None = None
    extraction_method: str | None = None
    novel_process: bool | None = None
    declared_use: str | None = None
    ab_user_type: str | None = None
    ab_turnover_inr: float | None = None
    ab_wild_collected: bool | None = None
    ab_commercial_use: bool = True


@router.post("/product-classify", response_model=ProductClassifierResponse)
def classify_product(req: ProductClassifyRequest):
    if req.passport_id:
        return ProductClassifier.classify_passport(req.passport_id)
    return ProductClassifier.classify(
        product_name=req.product_name or "",
        product_form=req.product_form or "",
        dosage_form=req.dosage_form or "",
        intended_use=req.intended_use or "",
        claims=req.claims or [],
        ingredients=req.ingredients or [],
        process_description=req.process_description or "",
        label_disclaimer=req.label_disclaimer,
        first_schedule=req.first_schedule,
        new_ingredient=req.new_ingredient,
        extraction_method=req.extraction_method or "",
        novel_process=req.novel_process,
        declared_use=req.declared_use or "",
        ab_user_type=req.ab_user_type or "",
        ab_turnover_inr=req.ab_turnover_inr,
        ab_wild_collected=req.ab_wild_collected,
        ab_commercial_use=req.ab_commercial_use,
    )


@router.get("/export-readiness/{passport_id}", response_model=ExportReadinessResponse)
def get_export_readiness(passport_id: str):
    return ExportReadinessEngine.evaluate(passport_id)


class ABSComplianceCheckRequest(BaseModel):
    ingredients: list[str] | None = None
    passport_id: str | None = None
    user_type: str | None = "company"
    turnover_inr: float | None = None
    codified_tk: bool | None = None
    wild_collected: bool | None = None
    commercial_use: bool = True


@router.post("/abs/check", response_model=ABSComplianceResponse)
def check_abs_compliance(req: ABSComplianceCheckRequest):
    ingredients = req.ingredients or []
    if req.passport_id:
        passport = PassportEngine.get_passport(req.passport_id)
        if passport and not ingredients:
            ingredients = [ing.raw_name for ing in passport.ingredients]
    return ABSComplianceEngine.check(
        ingredients=ingredients,
        user_type=req.user_type or "company",
        turnover_inr=req.turnover_inr,
        codified_tk=req.codified_tk,
        wild_collected=req.wild_collected,
        commercial_use=req.commercial_use,
    )


class TerminologyMapRequest(BaseModel):
    query: str
    source: str | None = None


@router.post("/terminology/map", response_model=TerminologyMapResponse)
def map_terminology(req: TerminologyMapRequest):
    return TerminologyMapper.map(req.query)


class InnovationGraphRequest(BaseModel):
    ingredients: list[str] | None = None
    innovation_title: str | None = None
    passport_id: str | None = None


@router.post("/knowledge-graph", response_model=InnovationKnowledgeGraphResponse)
def build_innovation_graph_ep(req: InnovationGraphRequest):
    """Dynamically compose a bio-resource knowledge graph for the selected
    innovation (single herb or polyherbal formulation) from the curated
    IP-SAKTI knowledge base. Nothing is hardcoded per herb."""
    return build_innovation_graph(
        ingredient_names=req.ingredients or [],
        innovation_title=req.innovation_title,
        passport_id=req.passport_id,
    )


@router.get("/knowledge-graph/{passport_id}", response_model=InnovationKnowledgeGraphResponse)
def get_innovation_graph(passport_id: str):
    """Compose the knowledge graph from an existing innovation passport."""
    return build_innovation_graph(
        ingredient_names=[],
        innovation_title=None,
        passport_id=passport_id,
    )