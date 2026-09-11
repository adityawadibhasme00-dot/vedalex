from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.models.intelligence import (
    ClaimSafetyAnalysisResponse,
    EvidenceQualityIntelligenceResponse,
    BioResourceGraphResponse,
    ProductClassifierResponse,
    ExportReadinessResponse,
    TerminologyMapResponse,
)
from app.services.claim_safety_engine import ClaimSafetyEngine
from app.services.evidence_quality_engine import EvidenceQualityEngine
from app.services.passport_engine import PassportEngine
from app.services.bio_resource_engine import BioResourceEngine
from app.services.product_classifier import ProductClassifier
from app.services.export_readiness_engine import ExportReadinessEngine
from app.services.terminology_mapper import TerminologyMapper
from app.services.ingredient_resolver import IngredientResolverService

router = APIRouter(prefix="/intelligence", tags=["Intelligence Engines"])


class ClaimSafetyAnalyzeRequest(BaseModel):
    claims: Optional[List[str]] = None
    ingredients: Optional[List[str]] = None
    product_type: str = "ayurvedic_drug"
    target_markets: List[str] = ["India", "United States", "Canada"]
    passport_id: Optional[str] = None


@router.post("/claim-safety/analyze", response_model=ClaimSafetyAnalysisResponse)
async def analyze_claim_safety(req: ClaimSafetyAnalyzeRequest):
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
async def get_evidence_quality_intelligence(passport_id: str):
    return EvidenceQualityEngine.evaluate(passport_id)


@router.get("/bio-resource/{passport_id}", response_model=BioResourceGraphResponse)
async def get_bio_resource_intelligence(passport_id: str):
    return BioResourceEngine.build(passport_id)


class ProductClassifyRequest(BaseModel):
    passport_id: Optional[str] = None
    product_form: Optional[str] = None
    dosage_form: Optional[str] = None
    intended_use: Optional[str] = None
    claims: Optional[List[str]] = None
    ingredients: Optional[List[str]] = None
    process_description: Optional[str] = None
    label_disclaimer: Optional[str] = None


@router.post("/product-classify", response_model=ProductClassifierResponse)
async def classify_product(req: ProductClassifyRequest):
    if req.passport_id:
        return ProductClassifier.classify_passport(req.passport_id)
    return ProductClassifier.classify(
        product_form=req.product_form or "",
        dosage_form=req.dosage_form or "",
        intended_use=req.intended_use or "",
        claims=req.claims or [],
        ingredients=req.ingredients or [],
        process_description=req.process_description or "",
    )


@router.get("/export-readiness/{passport_id}", response_model=ExportReadinessResponse)
async def get_export_readiness(passport_id: str):
    return ExportReadinessEngine.evaluate(passport_id)


class TerminologyMapRequest(BaseModel):
    query: str
    source: Optional[str] = None


@router.post("/terminology/map", response_model=TerminologyMapResponse)
async def map_terminology(req: TerminologyMapRequest):
    return TerminologyMapper.map(req.query)