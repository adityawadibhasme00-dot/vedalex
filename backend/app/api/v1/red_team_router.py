from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
from app.services.passport_engine import PassportEngine
from app.services.red_team_module import RedTeamModule

router = APIRouter(prefix="/red-team", tags=["Red-Team Challenge"])

class RedTeamRequest(BaseModel):
    passport_id: str

@router.post("/challenge")
async def challenge_innovation(req: RedTeamRequest):
    passport = PassportEngine.get_passport(req.passport_id)
    if not passport:
        passport = PassportEngine.create_from_intake("Ashwagandha + Brahmi formulation")

    return RedTeamModule.challenge_innovation(passport)
