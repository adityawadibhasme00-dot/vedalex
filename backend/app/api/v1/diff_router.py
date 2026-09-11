from fastapi import APIRouter
from typing import List, Optional
from app.models.diff import RegulatoryDiffRecord
from app.services.regulatory_diff_service import RegulatoryDiffService

router = APIRouter(prefix="/regulatory-diff", tags=["Regulatory Diff & Alerts"])

@router.get("/updates", response_model=List[RegulatoryDiffRecord])
async def get_regulatory_updates(case_id: Optional[str] = None):
    if case_id:
        return RegulatoryDiffService.get_updates_for_case(case_id)
    return RegulatoryDiffService.get_all_updates()
