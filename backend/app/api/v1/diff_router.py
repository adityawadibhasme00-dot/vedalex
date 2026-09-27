
from fastapi import APIRouter

from app.models.diff import RegulatoryDiffRecord
from app.services.regulatory_diff_service import RegulatoryDiffService

router = APIRouter(prefix="/regulatory-diff", tags=["Regulatory Diff & Alerts"])

@router.get("/updates", response_model=list[RegulatoryDiffRecord])
def get_regulatory_updates(case_id: str | None = None):
    if case_id:
        return RegulatoryDiffService.get_updates_for_case(case_id)
    return RegulatoryDiffService.get_all_updates()
