from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.passport import InnovationPassport
from app.services.passport_engine import PassportEngine
from app.services.patent_readiness_engine import PatentReadinessEngine

router = APIRouter(prefix="/analysis", tags=["Patent Analysis"])


@router.get("/readiness/{passport_id}")
def get_patent_readiness(passport_id: str, db: Session = Depends(get_db)):
    passport: InnovationPassport | None = PassportEngine.get_passport(passport_id)
    if not passport:
        raise HTTPException(status_code=404, detail="Passport not found")

    result: dict[str, Any] = PatentReadinessEngine.compute(passport, db=db)
    return result