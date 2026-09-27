
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.diff import WhatIfSimulationResponse
from app.services.passport_engine import PassportEngine
from app.services.what_if_engine import WhatIfSimulatorEngine

router = APIRouter(prefix="/what-if", tags=["What-If Simulator"])

class WhatIfRequest(BaseModel):
    passport_id: str
    mutated_claims: list[str]

@router.post("/simulate", response_model=WhatIfSimulationResponse)
def simulate_what_if(req: WhatIfRequest):
    passport = PassportEngine.get_passport(req.passport_id)
    if not passport:
        raise HTTPException(status_code=404, detail="Passport not found")

    response = WhatIfSimulatorEngine.simulate_claim_mutation(passport, req.mutated_claims)
    return response
