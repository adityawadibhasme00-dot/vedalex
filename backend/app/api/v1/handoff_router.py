from fastapi import APIRouter, HTTPException
from app.models.handoff import ExpertHandoffRequest, ExpertHandoffResponse
from app.services.expert_handoff_service import ExpertHandoffService

router = APIRouter(prefix="/expert-handoff", tags=["Expert Handoff Bridge"])

@router.post("/dispatch", response_model=ExpertHandoffResponse)
async def dispatch_expert_handoff(req: ExpertHandoffRequest):
    if not req.explicit_dpdp_consent or not req.liability_boundary_acknowledged:
        raise HTTPException(
            status_code=400,
            detail="DPDP Act explicit consent and professional liability boundary acknowledgment are mandatory before routing case."
        )
    return ExpertHandoffService.dispatch_case(req)
