from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict
from app.services.multilingual_nlp import MultilingualNLPEngine
from app.services.ingredient_resolver import IngredientResolverService

router = APIRouter(prefix="/botanical", tags=["Botanical Canonicalization"])

class CanonicalizeRequest(BaseModel):
    raw_name: str
    source_language: Optional[str] = "auto"

class CanonicalizeResponse(BaseModel):
    raw_input: str
    detected_language: str
    canonical_id: Optional[str] = None
    botanical_name: Optional[str] = None
    api_monograph_id: Optional[str] = None
    family: Optional[str] = None
    plant_parts: List[str] = []
    therapeutic_uses: List[str] = []
    regulatory_status: Dict[str, str] = {}
    confidence: float = 0.0

@router.post("/canonicalize", response_model=CanonicalizeResponse)
async def canonicalize_botanical(req: CanonicalizeRequest):
    detected_lang = MultilingualNLPEngine.detect_language(req.raw_name)
    resolved = IngredientResolverService.resolve(req.raw_name)

    if resolved:
        return CanonicalizeResponse(
            raw_input=req.raw_name,
            detected_language=detected_lang,
            canonical_id=resolved.canonical_id,
            botanical_name=resolved.accepted_botanical_name,
            api_monograph_id=resolved.api_monograph_id,
            family=resolved.family,
            plant_parts=resolved.standard_plant_parts,
            therapeutic_uses=resolved.classical_therapeutic_uses,
            regulatory_status={
                "fssai_aahara": resolved.fssai_aahara_status,
                "us_fda_ndi": resolved.us_fda_ndi_status,
                "canada_nhpid": resolved.canada_nhpid_status,
            },
            confidence=resolved.resolution_confidence
        )

    normalized = MultilingualNLPEngine.normalize_botanical_mentions(req.raw_name)
    if normalized:
        return CanonicalizeResponse(
            raw_input=req.raw_name,
            detected_language=detected_lang,
            canonical_id=normalized[0][1],
            confidence=normalized[0][2]
        )

    return CanonicalizeResponse(
        raw_input=req.raw_name,
        detected_language=detected_lang,
        confidence=0.0
    )
