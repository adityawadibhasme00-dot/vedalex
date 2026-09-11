from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.database import get_db
from app.services.white_space_service import WhitespaceNavigator

router = APIRouter(prefix="/whitespace", tags=["White Space Navigator"])


class WhiteSpaceAnalyzeRequest(BaseModel):
    passport_id: str
    # Optional mutation for the Before vs After opportunity simulator.
    mutate: Optional[Dict[str, Any]] = None


@router.get("/{passport_id}")
async def get_whitespace_analysis(passport_id: str, db=Depends(get_db)):
    """Current opportunity analysis for a passport (refreshes on demand)."""
    try:
        return WhitespaceNavigator.analyze(passport_id, db=db)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"White space analysis failed: {exc}")


@router.post("/analyze")
async def analyze_whitespace(req: WhiteSpaceAnalyzeRequest, db=Depends(get_db)):
    """Full opportunity analysis; with `mutate` returns {before, after} for the simulator."""
    try:
        return WhitespaceNavigator.analyze(req.passport_id, db=db, mutate=req.mutate)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"White space analysis failed: {exc}")