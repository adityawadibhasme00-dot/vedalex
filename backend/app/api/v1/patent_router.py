from fastapi import APIRouter, HTTPException, Depends
from typing import Any, Dict
from app.services.passport_engine import PassportEngine
from app.services.patent_readiness_engine import PatentReadinessEngine
from app.models.passport import InnovationPassport
from app.core.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/analysis", tags=["Patent Analysis"])


@router.get("/readiness/{passport_id}")
async def get_patent_readiness(passport_id: str, db: Session = Depends(get_db)):
    passport: InnovationPassport = PassportEngine.get_passport(passport_id)
    if not passport:
        raise HTTPException(status_code=404, detail="Passport not found")

    result: Dict[str, Any] = PatentReadinessEngine.compute(passport, db=db)
    return result