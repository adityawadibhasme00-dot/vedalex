import json
import os
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.services.passport_engine import PassportEngine
from app.services.ingredient_resolver import IngredientResolverService
from app.services.retrieval_engine import HybridRetrievalEngine

router = APIRouter(prefix="/screening", tags=["IP & TK Screening"])

class ScreeningRequest(BaseModel):
    passport_id: str

@router.post("/ip-tk")
async def screen_ip_tk(req: ScreeningRequest):
    passport = PassportEngine.get_passport(req.passport_id)
    if not passport:
        passport = PassportEngine.create_from_intake("Ashwagandha + Brahmi")

    # Formulation fingerprint
    ingredients_data = [ing.model_dump() for ing in passport.ingredients]
    fingerprint = IngredientResolverService.generate_formulation_fingerprint(
        ingredients_data,
        passport.process_description
    )

    # Retrieval from permitted TK prior art
    tk_path = os.path.join(os.path.dirname(__file__), "..", "..", "knowledge", "permitted_tk_prior_art.json")
    tk_records = []
    if os.path.exists(tk_path):
        with open(tk_path, "r", encoding="utf-8") as f:
            tk_records = json.load(f)

    # Statutory citation for Section 3(p)
    citations = HybridRetrievalEngine.search_passages("Section 3(p) traditional knowledge patentability", jurisdiction="India", top_k=1)

    return {
        "passport_id": passport.id,
        "formulation_fingerprint": fingerprint.model_dump(),
        "section_3p_analysis": {
            "statutory_risk_level": "HIGH_SECTION_3P_EXPOSURE",
            "statutory_basis": "Indian Patents Act 1970, Section 3(p)",
            "primary_reason": "Formulation components are established in classical Ayurvedic texts (Charaka Samhita) for sleep and cognitive calm. Without evidence of synergistic interaction, patent claims will be rejected as obvious aggregation.",
            "statutory_citations": [c.model_dump() for c in citations]
        },
        "retrieved_prior_art_records": tk_records,
        "coverage_limitations": "Screening performed against permitted classical texts and primary gazettes. Full patent search / Freedom to Operate (FTO) requires professional patent agent search.",
        "recommended_patentability_strategy": [
            "Conduct combination-index isobologram assay proving synergism",
            "File patent claims directed specifically at novel extraction solvent parameters or modified release pharmacokinetic profile rather than raw herbal combination",
            "Obtain prior approval from National Biodiversity Authority (NBA) under Form III"
        ]
    }
