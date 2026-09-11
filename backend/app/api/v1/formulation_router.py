from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.services.multilingual_nlp import MultilingualNLPEngine
from app.services.ingredient_resolver import IngredientResolverService
from app.models.canonical import CanonicalIngredient

router = APIRouter(prefix="/formulation", tags=["Formulation Parsing"])

class FormulationParseRequest(BaseModel):
    text: str
    language: Optional[str] = "auto"

class ParsedIngredient(BaseModel):
    raw_name: str
    detected_language: str
    canonical_id: Optional[str] = None
    botanical_name: Optional[str] = None
    api_monograph_id: Optional[str] = None
    family: Optional[str] = None
    plant_part: Optional[str] = None
    confidence: float = 0.0

class FormulationParseResponse(BaseModel):
    detected_language: str
    ingredients: List[ParsedIngredient]
    raw_text: str

@router.post("/parse", response_model=FormulationParseResponse)
async def parse_formulation(req: FormulationParseRequest):
    detected_lang = MultilingualNLPEngine.detect_language(req.text)
    normalized = MultilingualNLPEngine.normalize_botanical_mentions(req.text)

    ingredients = []
    for raw_token, canonical_id, conf in normalized:
        resolved = IngredientResolverService.resolve(raw_token)
        if resolved:
            ingredients.append(ParsedIngredient(
                raw_name=raw_token,
                detected_language=detected_lang,
                canonical_id=resolved.canonical_id,
                botanical_name=resolved.accepted_botanical_name,
                api_monograph_id=resolved.api_monograph_id,
                family=resolved.family,
                plant_part=resolved.standard_plant_parts[0] if resolved.standard_plant_parts else None,
                confidence=conf
            ))
        else:
            ingredients.append(ParsedIngredient(
                raw_name=raw_token,
                detected_language=detected_lang,
                canonical_id=canonical_id,
                confidence=conf
            ))

    return FormulationParseResponse(
        detected_language=detected_lang,
        ingredients=ingredients,
        raw_text=req.text
    )
