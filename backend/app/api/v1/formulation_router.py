import re

from fastapi import APIRouter
from pydantic import BaseModel

from app.models.canonical import CanonicalIngredient
from app.services.ingredient_resolver import IngredientResolverService
from app.services.multilingual_nlp import MultilingualNLPEngine

router = APIRouter(prefix="/formulation", tags=["Formulation Parsing"])

class FormulationParseRequest(BaseModel):
    text: str
    language: str | None = "auto"

class ParsedIngredient(BaseModel):
    raw_name: str
    detected_language: str
    canonical_id: str | None = None
    botanical_name: str | None = None
    api_monograph_id: str | None = None
    family: str | None = None
    plant_part: str | None = None
    confidence: float = 0.0
    status: str = "resolved"  # "resolved" | "unresolved" | "quantity_only"

class FormulationParseResponse(BaseModel):
    detected_language: str
    ingredients: list[ParsedIngredient]
    unresolved: list[str]
    raw_text: str

# Splits a formulation string into comma / semicolon / newline / '+' separated tokens.
_TOKEN_SPLIT_RE = re.compile(r"[,;\n+]+|\band\b", re.IGNORECASE)
# Trailing quantity + unit, e.g. "500mg", "10 g", "2.5 ml", "1 tsp", "20%".
_QUANTITY_RE = re.compile(
    r"\s*\d+(?:[.,]\d+)?\s*(?:mg|g|kg|mcg|µg|ug|ml|l|gm|%|tsp|tbsp|srv)?\b\s*$",
    re.IGNORECASE,
)
_PREP_WORD_RE = re.compile(r"\b(?:powder|extract|oil|syrup|tablet|vati|capsule|churna|kvatha|taila|asava|arista|svarasa|juice|per|to|of)\b[^,]*,?", re.IGNORECASE)
_TRIM_RE = re.compile(r"^[\s\-—–:()\[\];,']+|[\s\-—–:()\[\];,']+$")


def _tokenize_formulation(text: str) -> list[str]:
    """Splits a formulation string into individual ingredient mention tokens."""
    seen: set = set()
    tokens: list[str] = []
    for segment in _TOKEN_SPLIT_RE.split(text):
        token = segment
        token = _QUANTITY_RE.sub("", token)
        token = _PREP_WORD_RE.sub("", token)
        token = _TRIM_RE.sub("", token)
        if not token:
            continue
        lower = token.lower()
        if lower in seen:
            continue
        seen.add(lower)
        tokens.append(token)
    return tokens


def _ingredient_from_resolved(raw_token: str, lang: str, resolved: CanonicalIngredient) -> ParsedIngredient:
    return ParsedIngredient(
        raw_name=raw_token,
        detected_language=lang,
        canonical_id=resolved.canonical_id,
        botanical_name=resolved.accepted_botanical_name,
        api_monograph_id=resolved.api_monograph_id,
        family=resolved.family,
        plant_part=resolved.standard_plant_parts[0] if resolved.standard_plant_parts else None,
        confidence=resolved.resolution_confidence,
        status="resolved",
    )


@router.post("/parse", response_model=FormulationParseResponse)
def parse_formulation(req: FormulationParseRequest):
    detected_lang = MultilingualNLPEngine.detect_language(req.text)

    ingredients: list[ParsedIngredient] = []
    unresolved: list[str] = []
    matched_ids: set = set()

    # 1) Canonical matches from the synonym glossary (keeps original token spans).
    normalized = MultilingualNLPEngine.normalize_botanical_mentions(req.text)
    for raw_token, canonical_id, conf in normalized:
        resolved = IngredientResolverService.resolve(raw_token)
        if resolved:
            ingredients.append(_ingredient_from_resolved(raw_token, detected_lang, resolved))
            matched_ids.add(raw_token.lower())
        elif canonical_id:
            ingredients.append(ParsedIngredient(
                raw_name=raw_token,
                detected_language=detected_lang,
                canonical_id=canonical_id,
                confidence=conf,
                status="unresolved",
            ))
            unresolved.append(raw_token)

    # 2) Also scan raw tokens so entries the glossary missed are never silently dropped.
    for token in _tokenize_formulation(req.text):
        if token.lower() in matched_ids:
            continue
        resolved = IngredientResolverService.resolve(token)
        if resolved:
            ingredients.append(_ingredient_from_resolved(token, detected_lang, resolved))
            matched_ids.add(token.lower())
        else:
            if not any(x.raw_name.lower() == token.lower() for x in ingredients):
                # Skip pure dosage/process fragments that are clearly not plant names.
                if re.search(r"[\u0900-\u09FF\u0B00-\u0BFF\u0C00-\u0CFF\u0D00-\u0D7F\u0980-\u09FF\u0A80-\u0AFF]", token) or any(c.isalpha() for c in token):
                    ingredients.append(ParsedIngredient(
                        raw_name=token,
                        detected_language=detected_lang,
                        status="unresolved",
                    ))
                    unresolved.append(token)

    return FormulationParseResponse(
        detected_language=detected_lang,
        ingredients=ingredients,
        unresolved=sorted(set(unresolved)),
        raw_text=req.text,
    )
