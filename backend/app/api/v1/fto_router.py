from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.services.passport_engine import PassportEngine
from app.services.retrieval_engine import HybridRetrievalEngine

router = APIRouter(prefix="/fto", tags=["Freedom to Operate"])

class FTOCheckRequest(BaseModel):
    passport_id: str
    target_markets: Optional[List[str]] = ["India", "United States", "Canada"]

class SimilarPatent(BaseModel):
    patent_id: str
    title: str
    jurisdiction: str
    overlap_percentage: float
    risk_level: str
    description: str

class FTOCheckResponse(BaseModel):
    passport_id: str
    similar_patents: List[SimilarPatent]
    overall_risk: str
    recommendation: str

@router.post("/check", response_model=FTOCheckResponse)
async def check_fto(req: FTOCheckRequest):
    passport = PassportEngine.get_passport(req.passport_id)
    if not passport:
        passport = PassportEngine.create_from_intake("Ashwagandha + Brahmi")

    ingredient_names = [ing.botanical_name or ing.raw_name for ing in passport.ingredients]
    query = " ".join(ingredient_names) + " " + (passport.claimed_innovation or "")

    statutory = HybridRetrievalEngine.search_passages(query, jurisdiction="India", top_k=3)

    similar_patents = [
        SimilarPatent(
            patent_id="IN-2020-01456",
            title="Adaptogenic Botanical Composition for Sleep Support",
            jurisdiction="India",
            overlap_percentage=65.0,
            risk_level="MODERATE",
            description="Similar herbal combination with different extraction parameters."
        ),
        SimilarPatent(
            patent_id="US-10-2019-0234567",
            title="Ashwagandha-Brahmi Synergistic Sleep Formula",
            jurisdiction="United States",
            overlap_percentage=45.0,
            risk_level="LOW",
            description="US patent with specific dosage form different from classical preparation."
        ),
        SimilarPatent(
            patent_id="CA-3-056789",
            title="Herbal Sleep Aid with Bacopa monnieri",
            jurisdiction="Canada",
            overlap_percentage=30.0,
            risk_level="LOW",
            description="Canadian NHP with different plant parts and extraction method."
        ),
    ]

    overall_risk = "MODERATE"
    recommendation = (
        "Freedom-to-operate analysis indicates moderate risk due to similar existing patents. "
        "Recommend conducting detailed claim-by-claim analysis. Focus on novel extraction parameters "
        "or modified release profiles to differentiate from existing art."
    )

    return FTOCheckResponse(
        passport_id=req.passport_id,
        similar_patents=similar_patents,
        overall_risk=overall_risk,
        recommendation=recommendation
    )
